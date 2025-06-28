from django.contrib import admin
from django.utils.html import format_html
from .models import MenuCategory, Menu, MenuOption, MenuImage

@admin.register(MenuCategory)
class MenuCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'store', 'created_at']
    list_filter = ['store', 'created_at']
    search_fields = ['name', 'store__store_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['store', 'name']

class MenuImageInline(admin.TabularInline):
    """메뉴 이미지 인라인 어드민"""
    model = MenuImage
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

class MenuOptionInline(admin.TabularInline):
    model = MenuOption
    extra = 1
    readonly_fields = ['id', 'created_at']

@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ['name', 'store', 'get_categories', 'price', 'price_display', 'is_active', 'is_discounted', 'created_at']
    list_filter = ['store', 'categories', 'price_display', 'is_active', 'is_discounted', 'is_temporarily_out_of_stock', 'created_at']
    search_fields = ['name', 'description', 'store__store_name', 'categories__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    filter_horizontal = ['categories']
    inlines = [MenuImageInline, MenuOptionInline]
    
    def get_categories(self, obj):
        """메뉴의 카테고리들을 콤마로 구분하여 표시"""
        categories = obj.categories.all()
        if categories:
            return ', '.join([category.name for category in categories])
        return '-'
    get_categories.short_description = '카테고리'
    get_categories.admin_order_field = 'categories'
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('store', 'name', 'description', 'image', 'categories')
        }),
        ('가격 정보', {
            'fields': ('price_display', 'price', 'is_discounted', 'discounted_price')
        }),
        ('상태 정보', {
            'fields': ('is_active', 'is_temporarily_out_of_stock')
        }),
        ('메타 정보', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(MenuImage)
class MenuImageAdmin(admin.ModelAdmin):
    """메뉴 이미지 어드민"""
    list_display = ('menu', 'original_name', 'view_image_button', 'file_size_display', 'width', 'height', 'order', 'uploaded_at')
    list_filter = ('uploaded_at', 'menu__store')
    search_fields = ('menu__name', 'menu__store__store_name', 'original_name')
    readonly_fields = ('image_preview', 'file_url', 'file_path', 'file_size', 'width', 'height', 'uploaded_at', 'uploaded_by')
    ordering = ('menu', 'order', 'uploaded_at')
    list_per_page = 10
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('menu', 'original_name', 'order')
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
    
    def file_size_display(self, obj):
        """파일 크기 표시"""
        if obj:
            return obj.get_file_size_display()
        return ""
    file_size_display.short_description = '파일 크기'
    
    def image_preview(self, obj):
        """이미지 미리보기"""
        if obj and obj.file_url:
            return format_html(
                '<img src="{}" alt="{}" style="max-width: 200px; max-height: 200px; object-fit: contain;" onclick="showImageModal(\'{}\', \'{}\')" style="cursor: pointer;">',
                obj.file_url,
                obj.original_name,
                obj.file_url,
                obj.original_name
            )
        return "이미지 없음"
    image_preview.short_description = '이미지 미리보기'

@admin.register(MenuOption)
class MenuOptionAdmin(admin.ModelAdmin):
    list_display = ['menu', 'name', 'is_required', 'order', 'created_at']
    list_filter = ['menu__store', 'is_required', 'created_at']
    search_fields = ['menu__name', 'name']
    readonly_fields = ['id', 'created_at']
    ordering = ['menu', 'order']
