from collections import OrderedDict

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, NoReverseMatch
from django.utils.safestring import mark_safe
from django.db.models import Count
from .models import (
    Product, ProductImage, ProductOption, ProductOptionChoice, ProductCategory
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
    readonly_fields = ('uploaded_at', 'get_view_button')
    fields = ('original_name', 'get_view_button', 'order', 'uploaded_at')
    
    def get_view_button(self, obj):
        if obj and obj.file_url:
            return format_html(
                '<button type="button" onclick="showImageModal(\'{}\', \'{}\')" style="background-color: #007cba; color: white; border: none; padding: 3px 8px; border-radius: 3px; cursor: pointer; font-size: 11px;">'
                '<i class="fas fa-eye"></i> 보기'
                '</button>',
                obj.file_url,
                obj.original_name
            )
        return "이미지 없음"
    get_view_button.short_description = "이미지 보기"


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
        'stock_quantity', 'is_temporarily_out_of_stock', 'get_stock_status', 'is_active', 'category', 'get_options_summary', 'created_at'
    ]
    list_filter = ['is_active', 'is_discounted', 'is_temporarily_out_of_stock', 'price_display', 'store', 'category', 'created_at', 'stock_quantity']
    search_fields = ['title', 'description', 'store__store_name']
    readonly_fields = ['created_at', 'updated_at', 'final_price', 'discount_rate', 'get_options_display']
    list_per_page = 10  # 페이지당 항목 수 제한으로 성능 개선
    list_select_related = ['store']  # 스토어 정보 미리 로드
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('store', 'title', 'description')
        }),
        ('가격 정보', {
            'fields': ('price_display', 'price', 'price_krw', 'is_discounted', 'discounted_price', 'discounted_price_krw', 'final_price', 'discount_rate')
        }),
        ('재고 관리', {
            'fields': ('stock_quantity', 'is_temporarily_out_of_stock')
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
    
    class Media:
        js = ('admin/js/product_image_modal.js',)
        css = {
            'all': ('admin/css/product_image_modal.css',)
        }
    
    def get_queryset(self, request):
        """관리자 쿼리셋 최적화"""
        return super().get_queryset(request).select_related('store').prefetch_related('options__choices')
    
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
        """옵션 요약 표시"""
        options_count = obj.options.count()
        if options_count == 0:
            return "옵션 없음"
        return f"{options_count}개 옵션"
    get_options_summary.short_description = '옵션'
    
    def get_stock_status(self, obj):
        """재고 상태 표시 (일시품절 고려)"""
        if obj.is_temporarily_out_of_stock:
            return format_html('<span style="color: purple; font-weight: bold;">일시 품절</span>')
        elif obj.stock_quantity == 0:
            return format_html('<span style="color: red; font-weight: bold;">품절</span>')
        elif obj.stock_quantity <= 5:
            return format_html('<span style="color: orange; font-weight: bold;">재고 부족 ({}개)</span>', obj.stock_quantity)
        else:
            return format_html('<span style="color: green;">재고 있음 ({}개)</span>', obj.stock_quantity)
    get_stock_status.short_description = '재고 상태'
    
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


# @admin.register(ProductOption)
# class ProductOptionAdmin(admin.ModelAdmin):
#     list_display = ['product', 'name', 'get_choices_count', 'order', 'created_at']
#     list_filter = ['product__store', 'created_at']
#     search_fields = ['name', 'product__title']
#     list_per_page = 10
#     
#     inlines = [ProductOptionChoiceInline]
#     
#     def get_choices_count(self, obj):
#         """옵션의 선택지 개수 표시"""
#         return obj.choices.count()
#     get_choices_count.short_description = '선택지 개수'


# ProductOptionChoice는 별도 admin 메뉴로 등록하지 않음 (인라인으로만 관리)
class ProductOptionChoiceAdmin(admin.ModelAdmin):
    list_display = ['get_product', 'get_option_name', 'name', 'price', 'order', 'created_at']
    list_filter = ['option__product__store', 'created_at', 'option__name']
    search_fields = ['name', 'option__name', 'option__product__title']
    list_per_page = 10
    
    def get_product(self, obj):
        """상품명 표시"""
        return obj.option.product.title
    get_product.short_description = '상품'
    
    def get_option_name(self, obj):
        """옵션명 표시"""
        return obj.option.name
    get_option_name.short_description = '옵션'


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    change_list_template = 'admin/products/productcategory/change_list.html'

    list_display = ('name', 'store_link', 'order', 'product_count', 'view_products_link', 'created_at')
    list_display_links = ('name',)
    list_filter = ('store',)
    search_fields = ('name', 'store__store_name', 'store__store_id')
    ordering = ('store', 'order', 'name')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {
            'fields': ('store', 'name', 'order')
        }),
        ('메타 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request).select_related('store')
        return queryset.annotate(_product_count=Count('products'))

    def store_link(self, obj):
        store = obj.store
        try:
            url = reverse(f"admin:{store._meta.app_label}_{store._meta.model_name}_change", args=[store.pk])
            return format_html('<a href="{}">{}</a>', url, store.store_name)
        except NoReverseMatch:
            return store.store_name

    store_link.short_description = '스토어'
    store_link.admin_order_field = 'store__store_name'

    def product_count(self, obj):
        return getattr(obj, '_product_count', obj.products.count())

    product_count.short_description = '상품 수'

    def view_products_link(self, obj):
        url = reverse('admin:products_product_changelist')
        count = self.product_count(obj)
        return format_html(
            '<a href="{}?category__id__exact={}" target="_blank">상품 목록 ({})</a>',
            url,
            obj.pk,
            count,
        )

    view_products_link.short_description = '상품 보기'

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        response = super().changelist_view(request, extra_context=extra_context)

        if hasattr(response, 'context_data') and 'cl' in response.context_data:
            cl = response.context_data['cl']
            queryset = cl.queryset.select_related('store').annotate(_product_count=Count('products')).order_by('store__store_name', 'order', 'name')

            store_groups = OrderedDict()
            for category in queryset:
                store = category.store
                store_groups.setdefault(store, []).append(category)

            group_data = []
            for store, categories in store_groups.items():
                try:
                    store_url = reverse(f"admin:{store._meta.app_label}_{store._meta.model_name}_change", args=[store.pk])
                except NoReverseMatch:
                    store_url = ''

                group_data.append({
                    'store': store,
                    'store_url': store_url,
                    'categories': categories,
                    'category_count': len(categories),
                })

            response.context_data['store_groups'] = group_data

        return response


# @admin.register(ProductImage)
# class ProductImageAdmin(admin.ModelAdmin):
#     """상품 이미지 어드민"""
#     list_display = ('product', 'original_name', 'view_image_button', 'file_size_display', 'width', 'height', 'order', 'uploaded_at')
#     list_filter = ('uploaded_at', 'product__store')
#     search_fields = ('product__title', 'product__store__store_name', 'original_name')
#     readonly_fields = ('image_preview', 'file_url', 'file_path', 'file_size', 'width', 'height', 'uploaded_at', 'uploaded_by')
#     ordering = ('product', 'order', 'uploaded_at')
#     list_per_page = 10
#     
#     fieldsets = (
#         ('기본 정보', {
#             'fields': ('product', 'original_name', 'order')
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
#     
#     class Media:
#         js = ('admin/js/product_image_modal.js',)
#         css = {
#             'all': ('admin/css/product_image_modal.css',)
#         }


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
