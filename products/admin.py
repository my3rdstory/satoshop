from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Product, ProductImage, ProductOption, ProductOptionChoice
)

# 기존 등록 해제 (만약 있다면)
try:
    admin.site.unregister(Product)
except admin.sites.NotRegistered:
    pass

try:
    admin.site.unregister(ProductImage)
except admin.sites.NotRegistered:
    pass

try:
    admin.site.unregister(ProductOption)
except admin.sites.NotRegistered:
    pass

try:
    admin.site.unregister(ProductOptionChoice)
except admin.sites.NotRegistered:
    pass


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    readonly_fields = ('uploaded_at', 'get_preview')
    fields = ('original_name', 'get_preview', 'order', 'uploaded_at')
    
    def get_preview(self, obj):
        if obj.file_url:
            return format_html(
                '<img src="{}" style="max-width: 100px; max-height: 100px;" />',
                obj.file_url
            )
        return "이미지 없음"
    get_preview.short_description = "미리보기"


class ProductOptionChoiceInline(admin.TabularInline):
    model = ProductOptionChoice
    extra = 0
    fields = ('name', 'price', 'order')


class ProductOptionInline(admin.TabularInline):
    model = ProductOption
    extra = 0
    fields = ('name', 'order', 'get_choices_display')
    readonly_fields = ('get_choices_display',)
    
    def get_choices_display(self, obj):
        """옵션의 선택지들을 표시"""
        if not obj.pk:
            return "저장 후 선택지 추가 가능"
        
        choices = obj.choices.all()
        if not choices:
            return "선택지 없음"
        
        choice_list = []
        for choice in choices:
            price_text = f" (+{choice.price})" if choice.price > 0 else ""
            choice_list.append(f"{choice.name}{price_text}")
        
        return ", ".join(choice_list)
    get_choices_display.short_description = '선택지들'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'store', 'get_price_display_korean', 'price', 'is_discounted', 'discounted_price', 
        'shipping_fee', 'is_active', 'get_options_summary', 'created_at'
    ]
    list_filter = ['is_active', 'is_discounted', 'price_display', 'store', 'created_at']
    search_fields = ['title', 'description', 'store__store_name']
    readonly_fields = ['created_at', 'updated_at', 'final_price', 'discount_rate', 'get_options_display']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('store', 'title', 'description')
        }),
        ('가격 정보', {
            'fields': ('price_display', 'price', 'price_krw', 'is_discounted', 'discounted_price', 'discounted_price_krw', 'final_price', 'discount_rate', 'shipping_fee', 'shipping_fee_krw')
        }),
        ('추가 설정', {
            'fields': ('completion_message', 'is_active')
        }),
        ('옵션 정보', {
            'fields': ('get_options_display',),
            'classes': ('collapse',)
        }),
        ('메타 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    inlines = [ProductImageInline, ProductOptionInline]
    
    def get_price_display_korean(self, obj):
        """가격 표시 방식을 한국어로 표시"""
        if obj.price_display == 'sats':
            return '사토시 고정'
        elif obj.price_display == 'krw':
            return '원화 비율 연동'
        return obj.price_display
    get_price_display_korean.short_description = '가격 표시 방식'
    get_price_display_korean.admin_order_field = 'price_display'  # 정렬 가능하게 설정
    
    def get_options_summary(self, obj):
        """상품 목록에서 옵션 요약 표시"""
        options = obj.options.all()
        if not options:
            return "옵션 없음"
        
        summary = []
        for option in options:
            choice_count = option.choices.count()
            summary.append(f"{option.name}({choice_count}개)")
        
        return ", ".join(summary)
    get_options_summary.short_description = '옵션 요약'
    
    def get_options_display(self, obj):
        """상품 상세에서 옵션과 선택지 전체 표시"""
        if not obj.pk:
            return "상품을 먼저 저장하세요"
        
        options = obj.options.all().prefetch_related('choices')
        if not options:
            return "설정된 옵션이 없습니다"
        
        html = "<div style='max-height: 300px; overflow-y: auto;'>"
        for option in options:
            html += f"<h4 style='margin: 10px 0 5px 0; color: #333;'>{option.name}</h4>"
            html += "<ul style='margin: 0; padding-left: 20px;'>"
            
            for choice in option.choices.all():
                price_text = f" (+{choice.price} sats)" if choice.price > 0 else ""
                html += f"<li>{choice.name}{price_text}</li>"
            
            if not option.choices.exists():
                html += "<li style='color: #999;'>선택지 없음</li>"
            
            html += "</ul>"
        html += "</div>"
        
        return format_html(html)
    get_options_display.short_description = '옵션 및 선택지'


@admin.register(ProductOption)
class ProductOptionAdmin(admin.ModelAdmin):
    list_display = ['product', 'name', 'get_choices_count', 'order', 'created_at']
    list_filter = ['product__store', 'created_at']
    search_fields = ['name', 'product__title']
    
    inlines = [ProductOptionChoiceInline]
    
    def get_choices_count(self, obj):
        """옵션의 선택지 개수 표시"""
        return obj.choices.count()
    get_choices_count.short_description = '선택지 개수'


# ProductOptionChoice는 별도 admin 메뉴로 등록하지 않음 (인라인으로만 관리)
class ProductOptionChoiceAdmin(admin.ModelAdmin):
    list_display = ['get_product', 'get_option_name', 'name', 'price', 'order', 'created_at']
    list_filter = ['option__product__store', 'created_at', 'option__name']
    search_fields = ['name', 'option__name', 'option__product__title']
    
    def get_product(self, obj):
        """상품명 표시"""
        return obj.option.product.title
    get_product.short_description = '상품'
    
    def get_option_name(self, obj):
        """옵션명 표시"""
        return obj.option.name
    get_option_name.short_description = '옵션'


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    """상품 이미지 어드민"""
    list_display = ('product', 'original_name', 'image_preview', 'file_size_display', 'width', 'height', 'order', 'uploaded_at')
    list_filter = ('uploaded_at', 'product__store')
    search_fields = ('product__title', 'product__store__store_name', 'original_name')
    readonly_fields = ('image_preview', 'file_url', 'file_path', 'file_size', 'width', 'height', 'uploaded_at', 'uploaded_by')
    ordering = ('product', 'order', 'uploaded_at')
    list_per_page = 20
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('product', 'original_name', 'order')
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
    
    def image_preview(self, obj):
        """이미지 미리보기 (큰 크기)"""
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


# Admin 사이트 커스터마이징
from django.contrib.admin.apps import AdminConfig

class ProductsAdminConfig(AdminConfig):
    default_site = 'products.admin.ProductsAdminSite'

class ProductsAdminSite(admin.AdminSite):
    # Admin 사이트 커스터마이징은 settings.py에서 통합 관리
    pass

# 모델의 Meta 클래스에서 verbose_name 설정
Product._meta.verbose_name = '상품'
Product._meta.verbose_name_plural = '상품들'
ProductOption._meta.verbose_name = '상품 옵션'
ProductOption._meta.verbose_name_plural = '상품 옵션들'
ProductOptionChoice._meta.verbose_name = '상품 옵션 선택지'
ProductOptionChoice._meta.verbose_name_plural = '상품 옵션 선택지들'
ProductImage._meta.verbose_name = '상품 이미지'
ProductImage._meta.verbose_name_plural = '상품 이미지들'

# 가상의 app_label 설정 (admin에서만 보이는 용도)
Product._meta.app_label = 'products'
ProductOption._meta.app_label = 'products'
ProductOptionChoice._meta.app_label = 'products'
ProductImage._meta.app_label = 'products'
