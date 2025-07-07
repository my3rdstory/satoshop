from django.contrib import admin
from django.utils.html import format_html
from .models import MenuCategory, Menu, MenuOption, MenuImage, MenuOrder, MenuOrderItem

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

# @admin.register(MenuImage)
# class MenuImageAdmin(admin.ModelAdmin):
#     """메뉴 이미지 어드민"""
#     list_display = ('menu', 'original_name', 'view_image_button', 'file_size_display', 'width', 'height', 'order', 'uploaded_at')
#     list_filter = ('uploaded_at', 'menu__store')
#     search_fields = ('menu__name', 'menu__store__store_name', 'original_name')
#     readonly_fields = ('image_preview', 'file_url', 'file_path', 'file_size', 'width', 'height', 'uploaded_at', 'uploaded_by')
#     ordering = ('menu', 'order', 'uploaded_at')
#     list_per_page = 10
#     
#     fieldsets = (
#         ('기본 정보', {
#             'fields': ('menu', 'original_name', 'order')
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
#     def file_size_display(self, obj):
#         """파일 크기 표시"""
#         if obj:
#             return obj.get_file_size_display()
#         return ""
#     file_size_display.short_description = '파일 크기'
#     
#     def image_preview(self, obj):
#         """이미지 미리보기"""
#         if obj and obj.file_url:
#             return format_html(
#                 '<img src="{}" alt="{}" style="max-width: 200px; max-height: 200px; object-fit: contain;" onclick="showImageModal(\'{}\', \'{}\')" style="cursor: pointer;">',
#                 obj.file_url,
#                 obj.original_name,
#                 obj.file_url,
#                 obj.original_name
#             )
#         return "이미지 없음"
#     image_preview.short_description = '이미지 미리보기'

# @admin.register(MenuOption)
# class MenuOptionAdmin(admin.ModelAdmin):
#     list_display = ['menu', 'name', 'is_required', 'order', 'created_at']
#     list_filter = ['menu__store', 'is_required', 'created_at']
#     search_fields = ['menu__name', 'name']
#     readonly_fields = ['id', 'created_at']
#     ordering = ['menu', 'order']

class MenuOrderItemInline(admin.TabularInline):
    """메뉴 주문 아이템 인라인 어드민"""
    model = MenuOrderItem
    extra = 0
    readonly_fields = ('unit_price_display', 'total_price_display', 'created_at', 'options_display')
    fields = ('menu', 'menu_name', 'quantity', 'menu_price', 'options_display', 'options_price', 'unit_price_display', 'total_price_display')
    
    def options_display(self, obj):
        """선택된 옵션들 표시"""
        if obj and obj.selected_options:
            options_list = []
            for option_name, choice_value in obj.selected_options.items():
                options_list.append(f"{option_name}: {choice_value}")
            return format_html('<br>'.join(options_list))
        return '-'
    options_display.short_description = '선택 옵션'
    
    def unit_price_display(self, obj):
        """개당 가격 표시"""
        if obj:
            return f"{obj.unit_price:,} sats"
        return '0 sats'
    unit_price_display.short_description = '개당 가격'
    
    def total_price_display(self, obj):
        """총 가격 표시"""
        if obj:
            return f"{obj.total_price:,} sats"
        return '0 sats'
    total_price_display.short_description = '총 가격'


@admin.register(MenuOrder)
class MenuOrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_number_link', 'store', 'status_colored', 
        'items_count', 'total_amount_formatted', 'created_at', 'paid_at'
    ]
    list_filter = ['status', 'store', 'created_at', 'paid_at']
    search_fields = ['order_number', 'store__store_name', 'payment_hash']
    readonly_fields = ['order_number', 'created_at', 'updated_at', 'items_summary']
    list_per_page = 10
    
    fieldsets = (
        ('주문 정보', {
            'fields': ('order_number', 'store', 'status')
        }),
        ('결제 정보', {
            'fields': ('total_amount', 'payment_hash', 'paid_at')
        }),
        ('고객 정보', {
            'fields': ('customer_info',),
        }),
        ('주문 아이템 요약', {
            'fields': ('items_summary',),
        }),
        ('메타 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    inlines = [MenuOrderItemInline]
    
    def order_number_link(self, obj):
        """주문번호를 링크로 표시"""
        return obj.order_number or '(미생성)'
    order_number_link.short_description = '주문번호'
    order_number_link.admin_order_field = 'order_number'
    
    def status_colored(self, obj):
        """상태를 색상과 함께 표시"""
        colors = {
            'pending': '#f59e0b',
            'payment_pending': '#f59e0b',
            'paid': '#10b981',
            'cancelled': '#ef4444',
            'expired': '#6b7280',
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_colored.short_description = '주문 상태'
    status_colored.admin_order_field = 'status'
    
    def items_count(self, obj):
        """주문 아이템 개수"""
        return obj.items.count()
    items_count.short_description = '메뉴 수'
    
    def total_amount_formatted(self, obj):
        """총 금액을 포맷팅하여 표시"""
        return f"{obj.total_amount:,} sats"
    total_amount_formatted.short_description = '총 금액'
    total_amount_formatted.admin_order_field = 'total_amount'
    
    def items_summary(self, obj):
        """주문 아이템들의 요약 정보"""
        items = obj.items.all()
        if not items:
            return '주문 아이템이 없습니다.'
        
        html_parts = []
        html_parts.append('<div style="margin: 10px 0;">')
        html_parts.append('<table style="width: 100%; border-collapse: collapse; border: 1px solid #ddd;">')
        html_parts.append('''
            <thead style="background-color: #f8f9fa;">
                <tr>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">메뉴명</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: center;">수량</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: right;">메뉴가격</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: right;">옵션가격</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: right;">총가격</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">선택옵션</th>
                </tr>
            </thead>
            <tbody>
        ''')
        
        for item in items:
            # 선택된 옵션들 표시
            options_display = '-'
            if item.selected_options:
                options_list = []
                for option_name, choice_value in item.selected_options.items():
                    options_list.append(f"{option_name}: {choice_value}")
                options_display = '<br>'.join(options_list)
            
            html_parts.append(f'''
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;">{item.menu_name}</td>
                    <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">{item.quantity}</td>
                    <td style="border: 1px solid #ddd; padding: 8px; text-align: right;">{item.menu_price:,} sats</td>
                    <td style="border: 1px solid #ddd; padding: 8px; text-align: right;">{item.options_price:,} sats</td>
                    <td style="border: 1px solid #ddd; padding: 8px; text-align: right;"><strong>{item.total_price:,} sats</strong></td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{options_display}</td>
                </tr>
            ''')
        
        html_parts.append('</tbody></table>')
        html_parts.append('</div>')
        
        return format_html(''.join(html_parts))
    
    items_summary.short_description = '주문 아이템 상세'


# @admin.register(MenuOrderItem)
# class MenuOrderItemAdmin(admin.ModelAdmin):
#     list_display = ['order', 'menu_name', 'quantity', 'menu_price', 'options_price', 'total_price_display']
#     list_filter = ['order__store', 'created_at']
#     search_fields = ['order__order_number', 'menu_name']
#     readonly_fields = ['unit_price', 'total_price', 'created_at']
#     list_per_page = 10
#     
#     def total_price_display(self, obj):
#         """총 가격 표시"""
#         return f"{obj.total_price:,} sats"
#     total_price_display.short_description = '총 가격'
