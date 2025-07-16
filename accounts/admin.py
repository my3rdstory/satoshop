from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import reverse
from django.db import models
from .models import LightningUser


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
        if not self.get_changelist_instance(request):
            return qs
            
        from django.db.models import Count, Q
        from meetup.models import MeetupOrder
        
        return qs.annotate(
            _meetup_count=Count(
                'meetuporder',
                filter=Q(meetuporder__status__in=['confirmed', 'completed'])
            )
        )



