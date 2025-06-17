from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Store, StoreCreationStep, ReservedStoreId, StoreImage
)


class StoreImageInline(admin.TabularInline):
    """스토어 이미지 인라인 어드민"""
    model = StoreImage
    extra = 0  # 빈 폼 0개
    readonly_fields = ('view_image_button', 'file_size_display', 'uploaded_at', 'uploaded_by')
    fields = ('view_image_button', 'original_name', 'file_size_display', 'width', 'height', 'order', 'uploaded_at', 'uploaded_by')
    ordering = ('order', 'uploaded_at')
    
    def view_image_button(self, obj):
        """이미지 보기 버튼 (모달 방식) - 아이콘만 표시"""
        if obj and obj.file_url:
            return format_html(
                '<button type="button" class="button" onclick="showImageModal(\'{}\', \'{}\')" style="background-color: #007cba; color: white; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer;" title="이미지 보기">'
                '<i class="fas fa-eye"></i>'
                '</button>',
                obj.file_url,
                obj.original_name
            )
        return "이미지 없음"
    view_image_button.short_description = '이미지'
    
    def file_size_display(self, obj):
        """파일 크기 표시"""
        if obj:
            return obj.get_file_size_display()
        return ""
    file_size_display.short_description = '파일 크기'


@admin.register(StoreImage)
class StoreImageAdmin(admin.ModelAdmin):
    """스토어 이미지 어드민"""
    list_display = ('store', 'original_name', 'view_image_button', 'file_size_display', 'width', 'height', 'order', 'uploaded_at')
    list_filter = ('uploaded_at', 'store')
    search_fields = ('store__store_name', 'store__store_id', 'original_name')
    readonly_fields = ('image_preview', 'file_url', 'file_path', 'file_size', 'width', 'height', 'uploaded_at', 'uploaded_by')
    ordering = ('store', 'order', 'uploaded_at')
    list_per_page = 10
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('store', 'original_name', 'order')
        }),
        ('이미지 정보', {
            'fields': ('image_preview', 'width', 'height', 'file_size_display')
        }),
        ('파일 정보', {
            'fields': ('file_url', 'file_path'),
            'classes': ('collapse',)
        }),
        ('메타 정보', {
            'fields': ('uploaded_at', 'uploaded_by'),
            'classes': ('collapse',)
        }),
    )
    
    def view_image_button(self, obj):
        """이미지 보기 버튼 (모달 방식) - 아이콘만 표시"""
        if obj and obj.file_url:
            return format_html(
                '<button type="button" class="button" onclick="showImageModal(\'{}\', \'{}\')" style="background-color: #007cba; color: white; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer;" title="이미지 보기">'
                '<i class="fas fa-eye"></i>'
                '</button>',
                obj.file_url,
                obj.original_name
            )
        return "이미지 없음"
    view_image_button.short_description = '이미지'
    
    def image_preview(self, obj):
        """이미지 미리보기 (상세 페이지에서만 사용)"""
        if obj and obj.file_url:
            return format_html(
                '<img src="{}" style="max-width: 300px; max-height: 200px; object-fit: contain; border-radius: 6px; border: 1px solid #ddd;" />',
                obj.file_url
            )
        return "이미지 없음"
    image_preview.short_description = '이미지 미리보기'
    
    def file_size_display(self, obj):
        """파일 크기 표시"""
        if obj:
            return obj.get_file_size_display()
        return ""
    file_size_display.short_description = '파일 크기'


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = [
        'store_name', 'store_id', 'owner_name', 'owner', 
        'is_active', 'created_at', 'get_store_link'
    ]
    list_filter = ['is_active', 'created_at', 'deleted_at']
    search_fields = ['store_name', 'store_id', 'owner_name', 'owner__username']
    readonly_fields = ['created_at', 'updated_at', 'get_store_link', 'hero_gradient_css']
    list_per_page = 10  # 페이지당 항목 수 제한으로 성능 개선
    list_select_related = ['owner']  # 사용자 정보 미리 로드
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('store_id', 'store_name', 'store_description', 'owner')
        }),
        ('주인장 정보', {
            'fields': ('owner_name', 'owner_phone', 'owner_email', 'chat_channel')
        }),
        ('API 설정', {
            'fields': ('blink_api_info_encrypted', 'blink_wallet_id_encrypted'),
            'classes': ('collapse',)
        }),
        ('테마 설정', {
            'fields': ('hero_color1', 'hero_color2', 'hero_text_color', 'hero_gradient_css')
        }),
        ('상태', {
            'fields': ('is_active', 'deleted_at')
        }),
        ('메타 정보', {
            'fields': ('created_at', 'updated_at', 'get_store_link'),
            'classes': ('collapse',)
        })
    )
    
    inlines = [StoreImageInline]
    
    def get_queryset(self, request):
        """관리자 쿼리셋 최적화"""
        return super().get_queryset(request).select_related('owner')
    
    def get_store_link(self, obj):
        if obj.store_id:
            url = reverse('stores:store_detail', args=[obj.store_id])
            return format_html('<a href="{}" target="_blank">스토어 보기</a>', url)
        return "-"
    get_store_link.short_description = "스토어 링크"


class DeletedStoreAdmin(admin.ModelAdmin):
    """삭제된 스토어만 보여주는 어드민"""
    list_display = ('store_name', 'store_id', 'owner', 'deleted_at')
    list_filter = ('deleted_at', 'is_active', 'created_at')
    search_fields = ('store_name', 'store_id', 'owner__username')
    readonly_fields = ('store_id', 'store_name', 'store_description', 'owner_name', 
                      'owner_phone', 'owner_email', 'chat_channel', 'owner', 
                      'is_active', 'created_at', 'updated_at', 'deleted_at',
                      'blink_api_info_encrypted', 'blink_wallet_id_encrypted')
    list_per_page = 10
    
    def get_queryset(self, request):
        """삭제된 스토어만 표시"""
        return Store.objects.filter(deleted_at__isnull=False)
    
    def has_add_permission(self, request):
        """삭제된 스토어는 새로 추가할 수 없음"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """실제 삭제는 불가능하도록"""
        return False
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('store_id', 'store_name', 'store_description', 'owner', 'is_active')
        }),
        ('주인장 정보', {
            'fields': ('owner_name', 'owner_phone', 'owner_email', 'chat_channel')
        }),
        ('블링크 정보', {
            'fields': ('blink_api_info_encrypted', 'blink_wallet_id_encrypted'),
            'classes': ('collapse',)
        }),
        ('메타 정보', {
            'fields': ('created_at', 'updated_at', 'deleted_at'),
            'classes': ('collapse',)
        }),
    )


# 삭제된 스토어 proxy 모델 생성
class DeletedStore(Store):
    class Meta:
        proxy = True
        verbose_name = '삭제된 스토어'
        verbose_name_plural = '삭제된 스토어들'

# 삭제된 스토어를 별도로 등록
admin.site.register(DeletedStore, DeletedStoreAdmin)

@admin.register(StoreCreationStep)
class StoreCreationStepAdmin(admin.ModelAdmin):
    list_display = ['store', 'current_step', 'step1_completed', 'step2_completed', 'step3_completed', 'step4_completed', 'step5_completed']
    list_filter = ['current_step', 'step1_completed', 'step2_completed', 'step3_completed', 'step4_completed', 'step5_completed']
    search_fields = ['store__store_name', 'store__store_id']
    list_per_page = 10

@admin.register(ReservedStoreId)
class ReservedStoreIdAdmin(admin.ModelAdmin):
    list_display = ['keyword', 'description', 'is_active', 'created_at', 'created_by']
    list_filter = ['is_active', 'created_at']
    search_fields = ['keyword', 'description']
    list_per_page = 10


# Admin 사이트 커스터마이징은 settings.py에서 통합 관리

# 주의: Product, Order 관련 모델들은 각각 products, orders 앱에서 별도로 관리됩니다.

# 스토어 관련 모델들의 verbose_name 설정
Store._meta.verbose_name = '스토어'
Store._meta.verbose_name_plural = '스토어들'
StoreImage._meta.verbose_name = '스토어 이미지'
StoreImage._meta.verbose_name_plural = '스토어 이미지들'
StoreCreationStep._meta.verbose_name = '스토어 생성 단계'
StoreCreationStep._meta.verbose_name_plural = '스토어 생성 단계들'
ReservedStoreId._meta.verbose_name = '예약된 스토어 ID'
ReservedStoreId._meta.verbose_name_plural = '예약된 스토어 ID들'

# Django Auth 앱의 verbose_name 변경 (순서 조정)
from django.contrib.auth.models import User, Group
from django.apps import apps

# Auth 앱의 verbose_name을 기본 스타일로 변경
auth_app = apps.get_app_config('auth')
auth_app.verbose_name = '인증 및 권한'

# Auth 모델들의 verbose_name도 한국어로 변경
User._meta.verbose_name = '사용자'
User._meta.verbose_name_plural = '사용자들'
Group._meta.verbose_name = '그룹'
Group._meta.verbose_name_plural = '그룹들'

