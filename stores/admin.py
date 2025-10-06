from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Store,
    StoreCreationStep,
    ReservedStoreId,
    StoreImage,
    BahPromotionRequest,
    BahPromotionImage,
    BahPromotionAdmin,
    PROMOTION_STATUS_SHIPPED,
    BahPromotionLinkSettings,
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


class BahPromotionImageInline(admin.TabularInline):
    """BAH 홍보 이미지 인라인 관리"""

    model = BahPromotionImage
    extra = 0
    readonly_fields = ('preview_image', 'file_size_display', 'uploaded_at', 'uploaded_by')
    fields = ('preview_image', 'original_name', 'file_size_display', 'order', 'uploaded_at', 'uploaded_by')
    ordering = ('order', 'uploaded_at')

    def preview_image(self, obj):
        if obj and obj.file_url:
            return format_html('<img src="{}" style="max-height: 120px; border-radius: 6px;" />', obj.file_url)
        return '미리보기 없음'

    preview_image.short_description = '미리보기'

    def file_size_display(self, obj):
        if obj:
            return obj.get_file_size_display()
        return ''

    file_size_display.short_description = '파일 크기'


# @admin.register(StoreImage)  # 스토어 이미지들 메뉴 제거
# class StoreImageAdmin(admin.ModelAdmin):
#     """스토어 이미지 어드민"""
#     list_display = ('store', 'original_name', 'view_image_button', 'file_size_display', 'width', 'height', 'order', 'uploaded_at')
#     list_filter = ('uploaded_at', 'store')
#     search_fields = ('store__store_name', 'store__store_id', 'original_name')
#     readonly_fields = ('image_preview', 'file_url', 'file_path', 'file_size', 'width', 'height', 'uploaded_at', 'uploaded_by')
#     ordering = ('store', 'order', 'uploaded_at')
#     list_per_page = 10
#     
#     fieldsets = (
#         ('기본 정보', {
#             'fields': ('store', 'original_name', 'order')
#         }),
#         ('이미지 정보', {
#             'fields': ('image_preview', 'width', 'height', 'file_size_display')
#         }),
#         ('파일 정보', {
#             'fields': ('file_url', 'file_path'),
#             'classes': ('collapse',)
#         }),
#         ('메타 정보', {
#             'fields': ('uploaded_at', 'uploaded_by'),
#             'classes': ('collapse',)
#         }),
#     )
#     
#     def view_image_button(self, obj):
#         """이미지 보기 버튼 (모달 방식) - 아이콘만 표시"""
#         if obj and obj.file_url:
#             return format_html(
#                 '<button type="button" class="button" onclick="showImageModal(\'{}\', \'{}\')" style="background-color: #007cba; color: white; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer;" title="이미지 보기">'
#                 '<i class="fas fa-eye"></i>'
#                 '</button>',
#                 obj.file_url,
#                 obj.original_name
#             )
#         return "이미지 없음"
#     view_image_button.short_description = '이미지'
#     
#     def image_preview(self, obj):
#         """이미지 미리보기 (상세 페이지에서만 사용)"""
#         if obj and obj.file_url:
#             return format_html(
#                 '<img src="{}" style="max-width: 300px; max-height: 200px; object-fit: contain; border-radius: 6px; border: 1px solid #ddd;" />',
#                 obj.file_url
#             )
#         return "이미지 없음"
#     image_preview.short_description = '이미지 미리보기'
#     
#     def file_size_display(self, obj):
#         """파일 크기 표시"""
#         if obj:
#             return obj.get_file_size_display()
#         return ""
#     file_size_display.short_description = '파일 크기'


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = [
        'store_name', 'store_id', 'owner_name', 'owner', 
        'is_active', 'email_status_display', 'created_at', 'get_store_link'
    ]
    list_filter = ['is_active', 'email_enabled', 'created_at', 'deleted_at']
    search_fields = ['store_name', 'store_id', 'owner_name', 'owner__username']
    readonly_fields = ['created_at', 'updated_at', 'get_store_link', 'hero_gradient_css']
    list_per_page = 10  # 페이지당 항목 수 제한으로 성능 개선
    list_select_related = ['owner']  # 사용자 정보 미리 로드
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('store_id', 'store_name', 'store_description', 'owner')
        }),
        ('주인장 정보', {
            'fields': ('owner_name', 'owner_phone', 'owner_email', 'business_license_number', 'telecommunication_sales_number', 'chat_channel')
        }),
        ('API 설정', {
            'fields': ('blink_api_info_encrypted', 'blink_wallet_id_encrypted'),
            'classes': ('collapse',)
        }),
        ('이메일 발송 설정', {
            'fields': ('email_enabled', 'email_host_user', 'email_host_password_encrypted', 'email_from_name'),
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
            # 여러 관리 페이지 링크 제공
            management_url = reverse('stores:manage_store', args=[obj.store_id]) + "?admin_access=true"
            products_url = reverse('stores:product_list', args=[obj.store_id]) + "?admin_access=true"
            orders_url = reverse('orders:order_management', args=[obj.store_id]) + "?admin_access=true"
            meetups_url = reverse('meetup:meetup_list', args=[obj.store_id]) + "?admin_access=true"
            
            return format_html(
                '<div style="white-space: nowrap;">'
                '<a href="{}" target="_blank" style="color: #007cba; font-weight: bold; margin-right: 8px;">관리</a>'
                '<a href="{}" target="_blank" style="color: #28a745; margin-right: 8px;">상품</a>'
                '<a href="{}" target="_blank" style="color: #dc3545; margin-right: 8px;">주문</a>'
                '<a href="{}" target="_blank" style="color: #6f42c1;">밋업</a>'
                '</div>',
                management_url, products_url, orders_url, meetups_url
            )
        return "-"
    get_store_link.short_description = "관리자 접속"
    
    def email_status_display(self, obj):
        """이메일 발송 설정 상태 표시"""
        if not obj.email_enabled:
            return format_html('<span style="color: #666;">비활성화</span>')
        
        # 이메일 주소와 비밀번호 설정 확인
        has_email = bool(obj.email_host_user)
        has_password = bool(obj.email_host_password_encrypted)
        
        if has_email and has_password:
            return format_html('<span style="color: #28a745;">✓ 발송 가능</span>')
        elif has_email:
            return format_html('<span style="color: #ffc107;">⚠ 비밀번호 미설정</span>')
        else:
            return format_html('<span style="color: #dc3545;">✗ 설정 필요</span>')
    
    email_status_display.short_description = "이메일 상태"


@admin.register(BahPromotionRequest)
class BahPromotionRequestAdmin(admin.ModelAdmin):
    """BAH 홍보 요청 관리"""

    list_display = (
        'store_name',
        'user',
        'phone_number',
        'email',
        'shipping_status_badge',
        'lightning_public_key_short',
        'created_at',
    )
    search_fields = ('store_name', 'user__username', 'phone_number', 'email')
    list_filter = ('created_at', 'shipping_status')
    readonly_fields = ('lightning_public_key', 'lightning_verified_at', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    inlines = [BahPromotionImageInline]
    date_hierarchy = 'created_at'

    fieldsets = (
        ('매장 기본 정보', {
            'fields': ('store_name', 'postal_code', 'address', 'address_detail')
        }),
        ('연락처', {
            'fields': ('phone_number', 'email')
        }),
        ('소개', {
            'fields': ('introduction',)
        }),
        ('라이트닝 인증', {
            'fields': ('user', 'lightning_public_key', 'lightning_verified_at'),
            'classes': ('collapse',)
        }),
        ('기록', {
            'fields': ('shipping_status', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def lightning_public_key_short(self, obj):
        if obj.lightning_public_key:
            return f"{obj.lightning_public_key[:12]}…"
        return '-'

    lightning_public_key_short.short_description = '라이트닝 키'

    def shipping_status_badge(self, obj):
        color = '#f59e0b'
        label = '발송예정'
        if obj.shipping_status == PROMOTION_STATUS_SHIPPED:
            color = '#10b981'
            label = '발송'
        return format_html('<span style="color:{}; font-weight:600;">{}</span>', color, label)

    shipping_status_badge.short_description = '발송 상태'


@admin.register(BahPromotionAdmin)
class BahPromotionAdminAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at')
    search_fields = ('user__username', 'user__email')
    autocomplete_fields = ['user']


@admin.register(BahPromotionLinkSettings)
class BahPromotionLinkSettingsAdmin(admin.ModelAdmin):
    list_display = ('login_guide_url', 'usage_guide_url', 'email_store_id', 'updated_at')

    def has_add_permission(self, request):
        if BahPromotionLinkSettings.objects.exists():
            return False
        return super().has_add_permission(request)

class DeletedStoreAdmin(admin.ModelAdmin):
    """삭제된 스토어만 보여주는 어드민"""
    list_display = ('store_name', 'store_id', 'owner', 'deleted_at')
    list_filter = ('deleted_at', 'is_active', 'created_at')
    search_fields = ('store_name', 'store_id', 'owner__username')
    readonly_fields = ('store_id', 'store_name', 'store_description', 'owner_name', 
                      'owner_phone', 'owner_email', 'business_license_number', 'telecommunication_sales_number', 'chat_channel', 'owner', 
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
            'fields': ('owner_name', 'owner_phone', 'owner_email', 'business_license_number', 'telecommunication_sales_number', 'chat_channel')
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
