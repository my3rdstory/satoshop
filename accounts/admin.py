from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import reverse
from django.db import models
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.http import HttpResponse
import csv
from .models import LightningUser, UserPurchaseHistory


@admin.register(LightningUser)
class LightningUserAdmin(admin.ModelAdmin):
    list_display = ['user', 'public_key_short', 'created_at', 'last_login_at']
    list_filter = ['created_at', 'last_login_at']
    search_fields = ['user__username', 'public_key']
    readonly_fields = ['created_at', 'last_login_at']
    list_per_page = 10
    
    def public_key_short(self, obj):
        return f"{obj.public_key[:16]}..."
    public_key_short.short_description = '공개키 (축약)'
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('user', 'public_key')
        }),
        ('시간 정보', {
            'fields': ('created_at', 'last_login_at')
        }),
    )
    
    def has_add_permission(self, request):
        return False  # 수동 생성 방지
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
    
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser  # 관리자만 수정 가능


# 기본 User 모델에 라이트닝 정보 추가
class LightningUserInline(admin.StackedInline):
    model = LightningUser
    extra = 0
    readonly_fields = ('public_key', 'last_login_at', 'created_at')
    
    fieldsets = (
        ('라이트닝 정보', {
            'fields': ('public_key', 'last_login_at', 'created_at'),
        }),
    )
    
    def has_add_permission(self, request, obj=None):
        """수동으로 라이트닝 프로필 추가는 불가능"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """라이트닝 프로필 변경은 불가능"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """삭제는 가능 (계정 연동 해제용)"""
        return True


# User 어드민 확장
admin.site.unregister(User)

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    inlines = (LightningUserInline,)
    list_per_page = 10  # 페이지당 10개씩 표시
    
    # 기존 list_display에 라이트닝 연동 상태 추가
    list_display = UserAdmin.list_display + ('lightning_status', 'meetup_participation_count')
    
    def lightning_status(self, obj):
        """라이트닝 연동 상태 표시"""
        try:
            lightning_user = obj.lightning_profile
            if lightning_user:
                return "⚡ 연동됨"
            else:
                return "❌ 미연동"
        except LightningUser.DoesNotExist:
            return "❌ 미연동"
    
    lightning_status.short_description = '라이트닝 연동'
    lightning_status.admin_order_field = 'lightning_profile'
    
    def meetup_participation_count(self, obj):
        """밋업 참가 횟수 표시"""
        # get_queryset에서 annotation으로 처리하면 더 효율적
        count = getattr(obj, '_meetup_count', None)
        if count is None:
            from meetup.models import MeetupOrder
            count = MeetupOrder.objects.filter(
                user=obj,
                status__in=['confirmed', 'completed']
            ).count()
        if count > 0:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">📅 {}회</span>',
                count
            )
        return format_html('<span style="color: #6c757d;">참가 내역 없음</span>')
    
    meetup_participation_count.short_description = '밋업 참가'
    
    def get_queryset(self, request):
        """쿼리 최적화 - 라이트닝 프로필 정보를 미리 로드하고 밋업 참가 횟수 annotation"""
        qs = super().get_queryset(request).select_related('lightning_profile')
        
        # list view일 때만 meetup count annotation 추가
        # changelist view인지 확인하는 더 안전한 방법
        if request.resolver_match and request.resolver_match.url_name == 'auth_user_changelist':
            from django.db.models import Count, Q
            from meetup.models import MeetupOrder
            
            return qs.annotate(
                _meetup_count=Count(
                    'meetup_orders',
                    filter=Q(meetup_orders__status__in=['confirmed', 'completed'])
                )
            )
            
        return qs


class OrderInline(admin.TabularInline):
    """주문 내역 인라인"""
    from orders.models import Order
    model = Order
    fk_name = 'user'
    extra = 0
    can_delete = False
    show_change_link = False  # 변경 링크 제거
    
    fields = ('order_number_link', 'buyer_info', 'store_name', 'status', 'total_amount_display', 'created_at', 'paid_at')
    readonly_fields = fields
    
    def order_number_link(self, obj):
        if obj.order_number:
            url = reverse('admin:orders_order_change', args=[obj.pk])
            return format_html(
                '<a href="{}" style="word-break: break-all; display: inline-block; max-width: 250px;">{}</a>',
                url, obj.order_number
            )
        return '-'
    order_number_link.short_description = '주문번호'
    order_number_link.admin_order_field = 'order_number'
    
    def buyer_info(self, obj):
        if obj.user and obj.buyer_name:
            return f"{obj.user.username} / {obj.buyer_name}"
        elif obj.user:
            return obj.user.username
        elif obj.buyer_name:
            return obj.buyer_name
        return '-'
    buyer_info.short_description = '주문자 아이디/이름'
    
    def store_name(self, obj):
        return obj.store.store_name if obj.store else '-'
    store_name.short_description = '스토어'
    
    def total_amount_display(self, obj):
        return f"{obj.total_amount:,} sats" if obj.total_amount else "0 sats"
    total_amount_display.short_description = '결제 금액'
    
    def has_add_permission(self, request, obj=None):
        return False
        
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('store').order_by('-created_at')


class HasOrdersFilter(admin.SimpleListFilter):
    """주문 보유 여부 필터"""
    title = '주문 보유'
    parameter_name = 'has_orders'
    
    def lookups(self, request, model_admin):
        return (
            ('yes', '주문 있음'),
            ('no', '주문 없음'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(orders__status='paid').distinct()
        elif self.value() == 'no':
            return queryset.exclude(orders__status='paid').distinct()
        return queryset


@admin.register(UserPurchaseHistory)
class UserPurchaseHistoryAdmin(admin.ModelAdmin):
    """사용자별 구매 내역 조회"""
    
    class Media:
        css = {
            'all': ('admin/css/user_purchase_history.css',)
        }
    
    # 리스트 뷰는 사용하지 않고 바로 검색창으로
    list_display = ['username', 'email', 'total_orders', 'total_spent', 'date_joined']
    list_filter = [HasOrdersFilter]
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['-id']
    
    def get_ordering(self, request):
        """정렬 옵션 제공"""
        ordering = super().get_ordering(request)
        # URL 파라미터로 정렬 옵션 확인
        if request.GET.get('o'):
            return ordering
        # 기본값 또는 커스텀 정렬
        return ordering
    list_per_page = 20
    actions = ['export_as_csv']
    
    # 인라인으로 주문 내역 표시
    inlines = [OrderInline]
    
    def get_model_perms(self, request):
        """메뉴 표시 권한"""
        return {
            'add': False,
            'change': True,
            'delete': False,
            'view': True,
        }
    
    def has_add_permission(self, request):
        return False
        
    def has_delete_permission(self, request, obj=None):
        return False
    
    def total_orders(self, obj):
        """총 주문 수"""
        # annotate로 미리 계산된 값이 있으면 사용
        if hasattr(obj, 'order_count'):
            count = obj.order_count or 0
        else:
            count = obj.orders.filter(status='paid').count()
        return format_html('<span style="font-weight: bold;">{}</span>', count)
    total_orders.short_description = '총 주문 수'
    total_orders.admin_order_field = 'order_count'
    total_orders.empty_value_display = '0'
    
    def total_spent(self, obj):
        """총 구매 금액"""
        # annotate로 미리 계산된 값이 있으면 사용
        if hasattr(obj, 'total_spent_amount'):
            total = obj.total_spent_amount or 0
        else:
            total = obj.orders.filter(status='paid').aggregate(
                total=Sum('total_amount')
            )['total'] or 0
        return format_html('<span style="color: #28a745; font-weight: bold;">{} sats</span>', f"{total:,}")
    total_spent.short_description = '총 구매 금액'
    total_spent.admin_order_field = 'total_spent_amount'
    total_spent.empty_value_display = '0 sats'
    
    def get_queryset(self, request):
        """User 모델을 사용 - 쿼리 최적화"""
        qs = User.objects.all()
        
        # list view일 때만 orders count를 prefetch
        if hasattr(request, 'resolver_match') and request.resolver_match.url_name == 'accounts_userpurchasehistory_changelist':
            from django.db.models import Count, Sum, Q
            qs = qs.annotate(
                order_count=Count('orders', filter=Q(orders__status='paid')),
                total_spent_amount=Sum('orders__total_amount', filter=Q(orders__status='paid'))
            )
        
        return qs
    
    fieldsets = (
        ('사용자 정보', {
            'fields': ('username', 'email', 'first_name', 'last_name', 'is_active', 'date_joined', 'last_login'),
            'classes': ('wide',),
        }),
        ('구매 통계', {
            'fields': (),
            'description': '아래에서 주문 내역을 확인할 수 있습니다.',
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        """모든 필드를 읽기 전용으로"""
        return [f.name for f in User._meta.fields]
    
    def export_as_csv(self, request, queryset):
        """선택된 사용자들의 구매 내역을 CSV로 내보내기"""
        meta = self.model._meta
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = 'attachment; filename=user_purchase_history.csv'
        response.write('\ufeff')  # UTF-8 BOM 추가
        
        writer = csv.writer(response)
        
        # 헤더 작성
        writer.writerow([
            '사용자명', '이메일', '이름', '가입일', 
            '총 주문 수', '총 구매 금액(sats)', '마지막 구매일'
        ])
        
        # 데이터 작성
        for user in queryset:
            orders = user.orders.filter(status='paid')
            total_orders = orders.count()
            total_amount = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            last_purchase = orders.order_by('-paid_at').first()
            last_purchase_date = last_purchase.paid_at if last_purchase else None
            
            writer.writerow([
                user.username,
                user.email,
                f"{user.first_name} {user.last_name}".strip() or '-',
                user.date_joined.strftime('%Y-%m-%d %H:%M:%S'),
                total_orders,
                total_amount,
                last_purchase_date.strftime('%Y-%m-%d %H:%M:%S') if last_purchase_date else '-'
            ])
        
        return response
    
    export_as_csv.short_description = 'CSV로 내보내기'
    
    def changelist_view(self, request, extra_context=None):
        """리스트 뷰에 추가 버튼 표시"""
        extra_context = extra_context or {}
        
        # 전체 다운로드 URL 추가
        extra_context['has_export_all'] = True
        
        return super().changelist_view(request, extra_context)



