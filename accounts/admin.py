from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import LNURLAuth, LightningUser


@admin.register(LNURLAuth)
class LNURLAuthAdmin(admin.ModelAdmin):
    list_display = [
        'session_id', 'k1', 'public_key', 'user', 
        'is_verified', 'is_used', 'created_at', 'expires_at'
    ]
    list_filter = ['is_verified', 'is_used', 'created_at']
    search_fields = ['session_id', 'k1', 'public_key', 'user__username']
    readonly_fields = [
        'session_id', 'k1', 'public_key', 'signature', 'created_at', 
        'verified_at', 'used_at'
    ]
    list_per_page = 10
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('session_id', 'k1', 'user')
        }),
        ('인증 정보', {
            'fields': ('public_key', 'signature')
        }),
        ('상태', {
            'fields': ('is_verified', 'is_used')
        }),
        ('시간 정보', {
            'fields': ('created_at', 'expires_at', 'verified_at', 'used_at')
        }),
    )
    
    def has_add_permission(self, request):
        return False  # 수동 생성 방지
    
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser  # 관리자만 수정 가능


# Django 기본 User 모델 어드민 커스터마이징
class CustomUserAdmin(UserAdmin):
    list_per_page = 10
    list_display = UserAdmin.list_display + ('lightning_status',)
    
    def lightning_status(self, obj):
        """라이트닝 연동 상태 표시"""
        try:
            lightning_user = obj.lightning_profile
            return "⚡ 연동됨"
        except LightningUser.DoesNotExist:
            return "❌ 미연동"
    lightning_status.short_description = "라이트닝 연동"

# 기본 User 어드민을 언등록하고 커스터마이징된 것으로 재등록
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(LightningUser)
class LightningUserAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'public_key_short', 'created_at', 'last_login_at'
    ]
    list_filter = ['created_at', 'last_login_at']
    search_fields = ['user__username', 'public_key']
    readonly_fields = ['public_key', 'created_at', 'last_login_at']
    list_per_page = 10
    
    fieldsets = (
        ('사용자 정보', {
            'fields': ('user',)
        }),
        ('라이트닝 정보', {
            'fields': ('public_key',)
        }),
        ('시간 정보', {
            'fields': ('created_at', 'last_login_at')
        }),
    )
    
    def public_key_short(self, obj):
        """공개키 앞 16자만 표시"""
        return f"{obj.public_key[:16]}..." if obj.public_key else ""
    public_key_short.short_description = "공개키 (축약)"
    
    def has_add_permission(self, request):
        return False  # 수동 생성 방지
