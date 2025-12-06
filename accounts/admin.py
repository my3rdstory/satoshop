from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.utils.html import format_html
from django.urls import reverse
from django.db import models, transaction
from django.db.models import Sum, Count, Q, Max
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.http import HttpResponse, HttpResponseRedirect
import csv
import logging
from .models import (
    LightningUser,
    TemporaryPassword,
    UserPurchaseHistory,
    UserMyPageHistory,
    UserPublicId,
    StorePurchaseCleanupProxy,
)
from meetup.models import MeetupOrder
from lecture.models import LiveLectureOrder
from file.models import FileOrder
from orders.models import Order, PurchaseHistory
from stores.models import Store


def _format_local(dt, fmt='%Y-%m-%d %H:%M:%S', default=''):
    if not dt:
        return default
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return timezone.localtime(dt).strftime(fmt)


STORE_PURCHASE_DISPLAY_LIMIT = 300
KIND_LABELS = {
    'product': '상품',
    'meetup': '밋업',
    'live': '라이브 강의',
    'file': '디지털 파일',
    'all': '전체',
}

logger = logging.getLogger(__name__)


def _normalize_before(before_value):
    if before_value and timezone.is_naive(before_value):
        return timezone.make_aware(before_value, timezone.get_current_timezone())
    return before_value


def _build_store_purchase_entries(store, item_type='all', before=None):
    """스토어 기준(또는 전체) 구입 내역을 유형별로 통합 조회"""
    before = _normalize_before(before)
    entries = []

    def apply_time_filter(qs, paid_field='paid_at'):
        qs = qs.annotate(purchased_at=Coalesce(models.F(paid_field), models.F('created_at')))
        if before:
            qs = qs.filter(purchased_at__lte=before)
        return qs.order_by('purchased_at', 'id')

    def append_product_orders():
        qs = (
            Order.objects.filter(paid_at__isnull=False)
            .select_related('user')
            .prefetch_related('items')
        )
        if store:
            qs = qs.filter(store=store)
        qs = apply_time_filter(qs, 'paid_at')
        for order in qs:
            items = list(order.items.all())
            item_name = '상품 정보 없음'
            if items:
                item_name = items[0].product_title
                if len(items) > 1:
                    item_name = f"{item_name} 외 {len(items) - 1}개"

            entries.append({
                'id': f'product:{order.id}',
                'kind': 'product',
                'kind_label': KIND_LABELS['product'],
                'store': order.store,
                'store_name': order.store.store_name,
                'item_name': item_name,
                'price_sats': order.total_amount,
                'buyer_id': order.user.username if order.user else '비회원',
                'purchased_at': order.purchased_at,
            })

    def append_meetup_orders():
        qs = (
            MeetupOrder.objects.filter(
                meetup__store=store,
                paid_at__isnull=False,
                status__in=['confirmed', 'completed'],
            )
            .select_related('user', 'meetup')
        )
        qs = apply_time_filter(qs, 'paid_at')
        for order in qs:
            entries.append({
                'id': f'meetup:{order.id}',
                'kind': 'meetup',
                'kind_label': KIND_LABELS['meetup'],
                'store': order.meetup.store,
                'store_name': order.meetup.store.store_name,
                'item_name': order.meetup.name,
                'price_sats': order.total_price,
                'buyer_id': order.user.username if order.user else '비회원',
                'purchased_at': order.purchased_at,
            })

    def append_live_orders():
        qs = (
            LiveLectureOrder.objects.filter(
                live_lecture__store=store,
                paid_at__isnull=False,
                status__in=['confirmed', 'completed'],
            )
            .select_related('user', 'live_lecture')
        )
        qs = apply_time_filter(qs, 'paid_at')
        for order in qs:
            entries.append({
                'id': f'live:{order.id}',
                'kind': 'live',
                'kind_label': KIND_LABELS['live'],
                'store': order.live_lecture.store,
                'store_name': order.live_lecture.store.store_name,
                'item_name': order.live_lecture.name,
                'price_sats': order.price,
                'buyer_id': order.user.username if order.user else '비회원',
                'purchased_at': order.purchased_at,
            })

    def append_file_orders():
        qs = (
            FileOrder.objects.filter(
                digital_file__store=store,
                paid_at__isnull=False,
                status='confirmed',
            )
            .select_related('user', 'digital_file')
        )
        qs = apply_time_filter(qs, 'paid_at')
        for order in qs:
            entries.append({
                'id': f'file:{order.id}',
                'kind': 'file',
                'kind_label': KIND_LABELS['file'],
                'store': order.digital_file.store,
                'store_name': order.digital_file.store.store_name,
                'item_name': order.digital_file.name,
                'price_sats': order.price,
                'buyer_id': order.user.username if order.user else '비회원',
                'purchased_at': order.purchased_at,
            })

    if item_type in ('all', 'product'):
        append_product_orders()
    if item_type in ('all', 'meetup'):
        append_meetup_orders()
    if item_type in ('all', 'live'):
        append_live_orders()
    if item_type in ('all', 'file'):
        append_file_orders()

    entries.sort(key=lambda entry: entry['purchased_at'] or timezone.now())
    total_count = len(entries)
    return entries[:STORE_PURCHASE_DISPLAY_LIMIT], total_count


def _parse_raw_ids(raw_ids):
    parsed = {'product': [], 'meetup': [], 'live': [], 'file': []}
    for raw in raw_ids:
        if ':' not in raw:
            continue
        prefix, pk = raw.split(':', 1)
        if prefix in parsed:
            try:
                parsed[prefix].append(int(pk))
            except ValueError:
                continue
    return parsed


def _delete_store_purchase_records(store, parsed_ids, before=None):
    before = _normalize_before(before)
    deleted = {'product': 0, 'meetup': 0, 'live': 0, 'file': 0}

    def apply_time_constraint(qs, paid_field='paid_at'):
        qs = qs.annotate(purchased_at=Coalesce(models.F(paid_field), models.F('created_at')))
        if before:
            qs = qs.filter(purchased_at__lte=before)
        return qs

    with transaction.atomic():
        if parsed_ids.get('product'):
            qs = Order.objects.filter(
                paid_at__isnull=False,
                id__in=parsed_ids['product'],
            )
            if store:
                qs = qs.filter(store=store)
            qs = apply_time_constraint(qs, 'paid_at')
            deleted['product'] = qs.count()
            qs.delete()

        if parsed_ids.get('meetup'):
            qs = MeetupOrder.objects.filter(
                paid_at__isnull=False,
                status__in=['confirmed', 'completed'],
                id__in=parsed_ids['meetup'],
            )
            if store:
                qs = qs.filter(meetup__store=store)
            qs = apply_time_constraint(qs, 'paid_at')
            deleted['meetup'] = qs.count()
            qs.delete()

        if parsed_ids.get('live'):
            qs = LiveLectureOrder.objects.filter(
                paid_at__isnull=False,
                status__in=['confirmed', 'completed'],
                id__in=parsed_ids['live'],
            )
            if store:
                qs = qs.filter(live_lecture__store=store)
            qs = apply_time_constraint(qs, 'paid_at')
            deleted['live'] = qs.count()
            qs.delete()

        if parsed_ids.get('file'):
            qs = FileOrder.objects.filter(
                paid_at__isnull=False,
                status='confirmed',
                id__in=parsed_ids['file'],
            )
            if store:
                qs = qs.filter(digital_file__store=store)
            qs = apply_time_constraint(qs, 'paid_at')
            deleted['file'] = qs.count()
            qs.delete()

    return deleted


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


class TemporaryPasswordInlineForm(forms.ModelForm):
    raw_password = forms.CharField(
        label='임시 비밀번호',
        required=False,
        widget=forms.PasswordInput(render_value=True),
        help_text='입력 시 해시로 저장됩니다. 비워두면 기존 임시 비밀번호를 유지합니다.'
    )
    clear_password = forms.BooleanField(
        label='임시 비밀번호 삭제',
        required=False,
        help_text='선택하면 임시 비밀번호를 제거합니다.'
    )

    class Meta:
        model = TemporaryPassword
        fields = []

    def save(self, commit=True):
        instance = super().save(commit=False)
        raw_password = self.cleaned_data.get('raw_password')
        clear_password = self.cleaned_data.get('clear_password')

        if clear_password:
            instance.password = ''
        elif raw_password:
            instance.password = make_password(raw_password)

        if commit:
            instance.save()
        return instance


class TemporaryPasswordInline(admin.StackedInline):
    model = TemporaryPassword
    form = TemporaryPasswordInlineForm
    extra = 1
    max_num = 1
    can_delete = False
    verbose_name = '임시 비밀번호'
    verbose_name_plural = '임시 비밀번호'
    fields = ('raw_password', 'clear_password', 'updated_at_display')
    readonly_fields = ('updated_at_display',)

    def updated_at_display(self, obj):
        if not obj.pk:
            return '-'
        return _format_local(obj.updated_at)


class UserPublicIdInline(admin.StackedInline):
    model = UserPublicId
    extra = 0
    max_num = 1
    can_delete = False
    readonly_fields = ('public_id', 'created_at')
    fields = ('public_id', 'created_at')
    verbose_name = '공개 ID'
    verbose_name_plural = '공개 ID'


# User 어드민 확장
admin.site.unregister(User)

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    inlines = (LightningUserInline, TemporaryPasswordInline, UserPublicIdInline)
    list_per_page = 10  # 페이지당 10개씩 표시
    
    # 기존 list_display에 라이트닝 연동 상태 추가
    list_display = UserAdmin.list_display + ('lightning_status', 'public_id_display', 'meetup_participation_count')
    
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
    
    def public_id_display(self, obj):
        profile = getattr(obj, 'public_identity', None)
        return profile.public_id if profile else '-'
    public_id_display.short_description = '공개 ID'
    
    def get_queryset(self, request):
        """쿼리 최적화 - 라이트닝 프로필 정보를 미리 로드하고 밋업 참가 횟수 annotation"""
        qs = super().get_queryset(request).select_related('lightning_profile', 'public_identity')
        
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


class PurchaseHistoryInline(admin.TabularInline):
    model = PurchaseHistory
    fk_name = 'user'
    extra = 0
    can_delete = False
    show_change_link = False
    fields = ('order_link', 'store_name_display', 'total_amount_display', 'purchase_date_display')
    readonly_fields = fields
    verbose_name = '구매 내역'
    verbose_name_plural = '구매 내역'

    def order_link(self, obj):
        order = getattr(obj, 'order', None)
        if order:
            url = reverse('admin:orders_order_change', args=[order.pk])
            return format_html('<a href="{}">{}</a>', url, order.order_number)
        return '-'
    order_link.short_description = '주문번호'

    def store_name_display(self, obj):
        return obj.store_name or '-'
    store_name_display.short_description = '스토어'

    def total_amount_display(self, obj):
        return f"{obj.total_amount:,} sats"
    total_amount_display.short_description = '결제 금액'

    def purchase_date_display(self, obj):
        return _format_local(obj.purchase_date) if obj.purchase_date else '-'
    purchase_date_display.short_description = '구매 일시'

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('order', 'order__store').order_by('-purchase_date')


class MeetupOrderInline(admin.TabularInline):
    model = MeetupOrder
    fk_name = 'user'
    extra = 0
    can_delete = False
    show_change_link = False
    fields = ('order_link', 'meetup_info', 'status_display', 'total_price_display', 'confirmed_at_display')
    readonly_fields = fields
    verbose_name = '밋업 주문'
    verbose_name_plural = '밋업 주문'

    def order_link(self, obj):
        url = reverse('admin:meetup_meetuporder_change', args=[obj.pk])
        return format_html('<a href="{}">{}</a>', url, obj.order_number)
    order_link.short_description = '주문번호'

    def meetup_info(self, obj):
        meetup = obj.meetup
        if not meetup:
            return '-'
        store_name = meetup.store.store_name if meetup.store else ''
        return f"{store_name} / {meetup.name}"
    meetup_info.short_description = '밋업'

    def status_display(self, obj):
        return obj.get_status_display()
    status_display.short_description = '상태'

    def total_price_display(self, obj):
        return f"{obj.total_price:,} sats"
    total_price_display.short_description = '결제 금액'

    def confirmed_at_display(self, obj):
        return _format_local(obj.confirmed_at) if obj.confirmed_at else '-'
    confirmed_at_display.short_description = '확정 일시'

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('meetup', 'meetup__store').order_by('-created_at')


class LiveLectureOrderInline(admin.TabularInline):
    model = LiveLectureOrder
    fk_name = 'user'
    extra = 0
    can_delete = False
    show_change_link = False
    fields = ('order_link', 'lecture_info', 'status_display', 'price_display', 'confirmed_at_display')
    readonly_fields = fields
    verbose_name = '라이브 강의 주문'
    verbose_name_plural = '라이브 강의 주문'

    def order_link(self, obj):
        url = reverse('admin:lecture_livelectureorder_change', args=[obj.pk])
        return format_html('<a href="{}">{}</a>', url, obj.order_number)
    order_link.short_description = '주문번호'

    def lecture_info(self, obj):
        lecture = obj.live_lecture
        if not lecture:
            return '-'
        store_name = lecture.store.store_name if lecture.store else ''
        return f"{store_name} / {lecture.name}"
    lecture_info.short_description = '라이브 강의'

    def status_display(self, obj):
        return obj.get_status_display()
    status_display.short_description = '상태'

    def price_display(self, obj):
        return f"{obj.price:,} sats"
    price_display.short_description = '결제 금액'

    def confirmed_at_display(self, obj):
        return _format_local(obj.confirmed_at) if obj.confirmed_at else '-'
    confirmed_at_display.short_description = '확정 일시'

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('live_lecture', 'live_lecture__store').order_by('-created_at')


class FileOrderInline(admin.TabularInline):
    model = FileOrder
    fk_name = 'user'
    extra = 0
    can_delete = False
    show_change_link = False
    fields = ('order_link', 'file_info', 'status_display', 'price_display', 'confirmed_at_display')
    readonly_fields = fields
    verbose_name = '파일 주문'
    verbose_name_plural = '파일 주문'

    def order_link(self, obj):
        url = reverse('admin:file_fileorder_change', args=[obj.pk])
        return format_html('<a href="{}">{}</a>', url, obj.order_number)
    order_link.short_description = '주문번호'

    def file_info(self, obj):
        digital_file = obj.digital_file
        if not digital_file:
            return '-'
        store_name = digital_file.store.store_name if digital_file.store else ''
        return f"{store_name} / {digital_file.name}"
    file_info.short_description = '디지털 파일'

    def status_display(self, obj):
        return obj.get_status_display()
    status_display.short_description = '상태'

    def price_display(self, obj):
        return f"{obj.price:,} sats"
    price_display.short_description = '결제 금액'

    def confirmed_at_display(self, obj):
        return _format_local(obj.confirmed_at) if obj.confirmed_at else '-'
    confirmed_at_display.short_description = '확정 일시'

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('digital_file', 'digital_file__store').order_by('-created_at')


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
                _format_local(user.date_joined),
                total_orders,
                total_amount,
                _format_local(last_purchase_date, default='-')
            ])
        
        return response
    
    export_as_csv.short_description = 'CSV로 내보내기'

    def changelist_view(self, request, extra_context=None):
        """리스트 뷰에 추가 버튼 표시"""
        extra_context = extra_context or {}
        
        # 전체 다운로드 URL 추가
        extra_context['has_export_all'] = True
        
        return super().changelist_view(request, extra_context)

    def has_module_permission(self, request):
        return request.user.has_module_perms('accounts')


class StorePurchaseCleanupForm(forms.Form):
    ITEM_CHOICES = [
        ('all', '전체'),
        ('product', '상품'),
        ('meetup', '밋업'),
        ('live', '라이브 강의'),
        ('file', '디지털 파일'),
    ]

    store = forms.ModelChoiceField(
        queryset=Store.objects.filter(deleted_at__isnull=True).order_by('store_name'),
        label='스토어',
        required=False,
        empty_label='전체',
    )
    item_type = forms.ChoiceField(
        choices=ITEM_CHOICES,
        required=False,
        initial='all',
        label='아이템 종류',
    )
    before = forms.DateTimeField(
        required=False,
        label='이 날짜/시간 이전 결제분',
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        input_formats=['%Y-%m-%dT%H:%M', '%Y-%m-%dT%H:%M:%S'],
        help_text='지정 시 해당 시점(포함) 이전에 결제 완료된 건만 조회/삭제합니다. 비워두면 모든 결제 완료분을 대상으로 합니다.',
    )


@admin.register(StorePurchaseCleanupProxy)
class StorePurchaseCleanupAdmin(admin.ModelAdmin):
    """스토어별 구입 이력 일괄 삭제"""

    change_list_template = 'admin/accounts/store_purchase_cleanup.html'
    list_display = []
    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return request.user.has_module_perms('accounts')

    def get_queryset(self, request):
        return Store.objects.none()

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        is_post = request.method == 'POST'
        form_data = request.POST if is_post else request.GET
        filter_form = StorePurchaseCleanupForm(request.GET or None)
        logger.debug(
            "[STORE_PURCHASE_CLEANUP] incoming form_data=%s is_post=%s",
            dict(form_data),
            is_post,
        )

        entries = []
        total_count = 0
        selected_store = None
        selected_kind = 'all'
        before = None
        selected_kind_label = KIND_LABELS['all']
        store_label = '전체'
        filter_applied = False

        if filter_form.is_valid():
            selected_store = filter_form.cleaned_data['store']
            selected_kind = filter_form.cleaned_data.get('item_type') or 'all'
            before = filter_form.cleaned_data.get('before')
            selected_kind_label = KIND_LABELS.get(selected_kind, KIND_LABELS['all'])
            store_label = selected_store.store_name if selected_store else '전체'
            filter_applied = True
            entries, total_count = _build_store_purchase_entries(
                selected_store,
                selected_kind,
                before,
            )
            logger.info(
                "[STORE_PURCHASE_CLEANUP] filter applied store=%s kind=%s before=%s total_count=%s",
                store_label,
                selected_kind,
                before,
                total_count,
            )

            if is_post:
                raw_ids = request.POST.getlist('selected_ids')
                parsed_ids = _parse_raw_ids(raw_ids)

                if not any(parsed_ids.values()):
                    messages.warning(request, '삭제할 구입 내역을 선택해주세요.')
                    logger.warning("[STORE_PURCHASE_CLEANUP] delete skipped: no ids selected")
                else:
                    deleted = _delete_store_purchase_records(selected_store, parsed_ids, before)
                    deleted_count = sum(deleted.values())
                    messages.success(
                        request,
                        f"{deleted_count}건 삭제 (상품 {deleted['product']}건 / 밋업 {deleted['meetup']}건 / 라이브 강의 {deleted['live']}건 / 디지털 파일 {deleted['file']}건)",
                    )
                    logger.info(
                        "[STORE_PURCHASE_CLEANUP] deleted total=%s detail=%s",
                        deleted_count,
                        deleted,
                    )

                    params = request.GET.copy()
                    if selected_store:
                        params['store'] = selected_store.id
                    else:
                        params.pop('store', None)
                    params['item_type'] = selected_kind
                    if before:
                        params['before'] = _normalize_before(before).strftime('%Y-%m-%dT%H:%M')
                    else:
                        params.pop('before', None)
                    redirect_url = reverse('admin:accounts_storepurchasecleanupproxy_changelist')
                    if params:
                        redirect_url = f"{redirect_url}?{params.urlencode()}"
                    return HttpResponseRedirect(redirect_url)
        else:
            if filter_form.errors:
                logger.warning(
                    "[STORE_PURCHASE_CLEANUP] filter invalid errors=%s data=%s",
                    filter_form.errors.as_json(),
                    dict(form_data),
                )
            else:
                logger.debug(
                    "[STORE_PURCHASE_CLEANUP] filter not applied (is_post=%s valid=%s)",
                    is_post,
                    filter_form.is_valid(),
                )

        extra_context.update({
            'title': '스토어 구입 이력 삭제',
            'filter_form': filter_form,
            'entries': entries,
            'total_count': total_count,
            'selected_store': selected_store,
            'selected_kind': selected_kind,
            'selected_kind_label': selected_kind_label,
            'store_label': store_label,
            'before': before,
            'display_limit': STORE_PURCHASE_DISPLAY_LIMIT,
            'filter_applied': filter_applied,
        })

        response = super().changelist_view(request, extra_context=extra_context)
        try:
            status = getattr(response, 'status_code', 'unknown')
            location = response.get('Location')
            logger.debug(
                "[STORE_PURCHASE_CLEANUP] response status=%s location=%s filter_applied=%s entries=%s",
                status,
                location,
                filter_applied,
                len(entries),
            )
        except Exception:
            logger.exception("[STORE_PURCHASE_CLEANUP] response logging failed")
        return response


@admin.register(UserMyPageHistory)
class UserMyPageHistoryAdmin(admin.ModelAdmin):
    """사용자 마이페이지 이력 조회"""

    class Media:
        css = {
            'all': ('admin/css/user_purchase_history.css',)
        }

    list_display = [
        'username',
        'email',
        'purchase_count_display',
        'meetup_count_display',
        'live_lecture_count_display',
        'file_order_count_display',
        'last_activity_display',
    ]
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['-id']
    list_per_page = 20
    inlines = [
        PurchaseHistoryInline,
        MeetupOrderInline,
        LiveLectureOrderInline,
        FileOrderInline,
    ]
    fieldsets = (
        ('사용자 정보', {
            'fields': ('username', 'email', 'first_name', 'last_name', 'is_active', 'date_joined', 'last_login'),
            'classes': ('wide',),
        }),
        ('참여 통계', {
            'fields': (
                'purchase_count_display',
                'meetup_count_display',
                'live_lecture_count_display',
                'file_order_count_display',
                'last_activity_display',
            ),
        }),
    )
    readonly_fields = (
        'username',
        'email',
        'first_name',
        'last_name',
        'is_active',
        'date_joined',
        'last_login',
        'purchase_count_display',
        'meetup_count_display',
        'live_lecture_count_display',
        'file_order_count_display',
        'last_activity_display',
    )

    def get_model_perms(self, request):
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

    def get_queryset(self, request):
        qs = User.objects.all()
        return qs.annotate(
            mypage_purchase_count=Count('purchase_history', distinct=True),
            mypage_meetup_count=Count(
                'meetup_orders',
                filter=Q(meetup_orders__status__in=['confirmed', 'completed']),
                distinct=True,
            ),
            mypage_live_count=Count(
                'live_lecture_orders',
                filter=Q(live_lecture_orders__status__in=['confirmed', 'completed']),
                distinct=True,
            ),
            mypage_file_count=Count(
                'file_orders',
                filter=Q(file_orders__status='confirmed'),
                distinct=True,
            ),
            last_purchase_activity=Max('purchase_history__purchase_date'),
            last_meetup_activity=Max(
                'meetup_orders__confirmed_at',
                filter=Q(meetup_orders__status__in=['confirmed', 'completed']),
            ),
            last_live_activity=Max(
                'live_lecture_orders__confirmed_at',
                filter=Q(live_lecture_orders__status__in=['confirmed', 'completed']),
            ),
            last_file_activity=Max(
                'file_orders__confirmed_at',
                filter=Q(file_orders__status='confirmed'),
            ),
        )

    def purchase_count_display(self, obj):
        count = getattr(obj, 'mypage_purchase_count', None)
        if count is None:
            count = obj.purchase_history.count()
        return format_html('<span style="font-weight: bold;">{}건</span>', count)
    purchase_count_display.short_description = '구매 내역'

    def meetup_count_display(self, obj):
        count = getattr(obj, 'mypage_meetup_count', None)
        if count is None:
            count = obj.meetup_orders.filter(status__in=['confirmed', 'completed']).count()
        return format_html('<span style="font-weight: bold;">{}건</span>', count)
    meetup_count_display.short_description = '밋업'

    def live_lecture_count_display(self, obj):
        count = getattr(obj, 'mypage_live_count', None)
        if count is None:
            count = obj.live_lecture_orders.filter(status__in=['confirmed', 'completed']).count()
        return format_html('<span style="font-weight: bold;">{}건</span>', count)
    live_lecture_count_display.short_description = '라이브 강의'

    def file_order_count_display(self, obj):
        count = getattr(obj, 'mypage_file_count', None)
        if count is None:
            count = obj.file_orders.filter(status='confirmed').count()
        return format_html('<span style="font-weight: bold;">{}건</span>', count)
    file_order_count_display.short_description = '파일'

    def last_activity_display(self, obj):
        candidates = [
            getattr(obj, 'last_purchase_activity', None),
            getattr(obj, 'last_meetup_activity', None),
            getattr(obj, 'last_live_activity', None),
            getattr(obj, 'last_file_activity', None),
        ]
        latest = max((dt for dt in candidates if dt), default=None)
        return _format_local(latest) if latest else '-'
    last_activity_display.short_description = '최근 활동'

    def has_module_permission(self, request):
        return request.user.has_module_perms('accounts')
