from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count
from stores.models import Store
from ln_payment.models import (
    PaymentTransaction,
    ManualPaymentTransaction,
    PaymentStageLog,
    OrderItemReservation,
)
from ln_payment.admin import (
    PaymentTransactionAdmin as BasePaymentTransactionAdmin,
    ManualPaymentTransactionAdmin as BaseManualPaymentTransactionAdmin,
    PaymentStageLogAdmin as BasePaymentStageLogAdmin,
    OrderItemReservationAdmin as BaseOrderItemReservationAdmin,
)
from .models import (
    Cart, CartItem, Order, OrderItem, PurchaseHistory, Invoice
)

# 기존 등록 해제 (만약 있다면)
try:
    admin.site.unregister(Cart)
except admin.sites.NotRegistered:
    pass

try:
    admin.site.unregister(CartItem)
except admin.sites.NotRegistered:
    pass

try:
    admin.site.unregister(Order)
except admin.sites.NotRegistered:
    pass

try:
    admin.site.unregister(OrderItem)
except admin.sites.NotRegistered:
    pass

try:
    admin.site.unregister(PurchaseHistory)
except admin.sites.NotRegistered:
    pass


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('added_at', 'updated_at', 'unit_price', 'total_price', 'options_price', 'product_store', 'product_link')
    fields = ('product_link', 'product_store', 'quantity', 'selected_options', 'unit_price', 'options_price', 'total_price', 'added_at')
    
    def product_store(self, obj):
        if obj.product and obj.product.store:
            return obj.product.store.store_name
        return '-'
    product_store.short_description = '스토어'
    
    def product_link(self, obj):
        if obj.product:
            url = reverse('admin:products_product_change', args=[obj.product.pk])
            return format_html('<a href="{}" target="_blank">{}</a>', url, obj.product.title)
        return '-'
    product_link.short_description = '상품'


# @admin.register(Cart)  # 장바구니들 메뉴 제거
# class CartAdmin(admin.ModelAdmin):
#     list_display = ['user', 'total_items', 'total_amount', 'stores_count', 'last_updated', 'created_at']
#     list_filter = ['created_at', 'updated_at']
#     search_fields = ['user__username', 'user__email']
#     readonly_fields = ['created_at', 'updated_at', 'total_amount', 'total_items', 'stores_list']
#     list_per_page = 10
#     
#     fieldsets = (
#         ('장바구니 정보', {
#             'fields': ('user', 'total_items', 'total_amount', 'stores_list')
#         }),
#         ('메타 정보', {
#             'fields': ('created_at', 'updated_at'),
#             'classes': ('collapse',)
#         })
#     )
#     
#     inlines = [CartItemInline]
#     
#     def get_queryset(self, request):
#         return super().get_queryset(request).select_related('user').prefetch_related(
#             'items__product__store'
#         )
#     
#     def total_items(self, obj):
#         return obj.items.count()
#     total_items.short_description = '상품 수'
#     
#     def stores_count(self, obj):
#         stores = set()
#         for item in obj.items.all():
#             if item.product and item.product.store:
#                 stores.add(item.product.store.store_name)
#         return len(stores)
#     stores_count.short_description = '스토어 수'
#     
#     def stores_list(self, obj):
#         stores = set()
#         for item in obj.items.all():
#             if item.product and item.product.store:
#                 stores.add(item.product.store.store_name)
#         return ', '.join(sorted(stores)) if stores else '-'
#     stores_list.short_description = '포함된 스토어들'
#     
#     def last_updated(self, obj):
#         return obj.updated_at
#     last_updated.short_description = '마지막 수정'


# CartItem은 Cart의 인라인으로만 관리하므로 별도 어드민 등록하지 않음


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('unit_price_safe', 'total_price_safe', 'created_at', 'product_link', 'options_display')
    fields = ('product_link', 'product_title', 'quantity', 'product_price', 'options_display', 'options_price', 'unit_price_safe', 'total_price_safe')
    
    def product_link(self, obj):
        if obj and obj.product:
            try:
                url = reverse('admin:products_product_change', args=[obj.product.pk])
                return format_html('<a href="{}" target="_blank">{}</a>', url, obj.product.title)
            except:
                pass
        return obj.product_title if obj and obj.product_title else '-'
    product_link.short_description = '상품'
    
    def options_display(self, obj):
        if obj and obj.selected_options:
            options_list = []
            for option_name, choice_name in obj.selected_options.items():
                options_list.append(f"{option_name}: {choice_name}")
            return format_html('<br>'.join(options_list))
        return '-'
    options_display.short_description = '선택 옵션'
    
    def unit_price_safe(self, obj):
        """안전한 개당 가격 표시"""
        if obj and hasattr(obj, 'unit_price'):
            try:
                return f"{obj.unit_price:,} sats"
            except:
                return '0 sats'
        return '0 sats'
    unit_price_safe.short_description = '개당 가격'
    
    def total_price_safe(self, obj):
        """안전한 총 가격 표시"""
        if obj and hasattr(obj, 'total_price'):
            try:
                return f"{obj.total_price:,} sats"
            except:
                return '0 sats'
        return '0 sats'
    total_price_safe.short_description = '총 가격'





@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_number_link', 'buyer_name', 'store', 'status_colored', 
        'delivery_status_colored', 'courier_company', 'tracking_number', 'items_count', 
        'total_amount_formatted', 'created_at', 'paid_at'
    ]
    list_filter = ['status', 'delivery_status', 'store', 'created_at', 'paid_at']
    search_fields = ['order_number', 'buyer_name', 'buyer_email', 'buyer_phone']
    readonly_fields = ['order_number', 'created_at', 'updated_at', 'items_summary', 'courier_company', 'tracking_number']
    list_per_page = 10
    change_list_template = 'admin/orders/order/change_list.html'
    
    fieldsets = (
        ('주문 정보', {
            'fields': ('order_number', 'user', 'store', 'status', 'delivery_status')
        }),
        ('주문자 정보', {
            'fields': ('buyer_name', 'buyer_phone', 'buyer_email')
        }),
        ('배송 정보', {
            'fields': ('shipping_postal_code', 'shipping_address', 'shipping_detail_address', 'order_memo', 'courier_company', 'tracking_number')
        }),
        ('결제 정보', {
            'fields': ('subtotal', 'shipping_fee', 'total_amount', 'payment_id', 'paid_at')
        }),
        ('주문 아이템 요약', {
            'fields': ('items_summary',),
        }),
        ('메타 정보', {
            'fields': ('created_at', 'updated_at', 'personal_info_deleted_at'),
            'classes': ('collapse',)
        })
    )
    
    inlines = [OrderItemInline]
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request).select_related('user', 'store').prefetch_related('items')
        return queryset.annotate(items_count_db=Count('items', distinct=True))

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        store_qs = Store.objects.filter(deleted_at__isnull=True).order_by('store_name').only('id', 'store_name')
        store_list = list(store_qs)
        named_stores = []
        unnamed_stores = []
        for store in store_list:
            name = (store.store_name or '').strip()
            if name:
                named_stores.append(store)
            else:
                unnamed_stores.append(store)
        extra_context['store_dropdown_options'] = named_stores + unnamed_stores
        selected_store = request.GET.get('store__id__exact', '')
        extra_context['selected_store_id'] = selected_store
        preserved = []
        for key in request.GET.keys():
            if key == 'store__id__exact':
                continue
            values = request.GET.getlist(key)
            for value in values:
                preserved.append((key, value))
        extra_context['store_filter_preserved_query'] = preserved
        return super().changelist_view(request, extra_context=extra_context)
    
    def order_number_link(self, obj):
        """주문번호를 링크로 표시"""
        return obj.order_number
    order_number_link.short_description = '주문번호'
    order_number_link.admin_order_field = 'order_number'
    
    def status_colored(self, obj):
        """상태를 색상과 함께 표시"""
        colors = {
            'pending': '#f59e0b',
            'payment_pending': '#f59e0b',
            'paid': '#10b981',
            'shipped': '#3b82f6',
            'delivered': '#10b981',
            'cancelled': '#ef4444',
            'refunded': '#6b7280',
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_colored.short_description = '주문 상태'
    status_colored.admin_order_field = 'status'
    
    def delivery_status_colored(self, obj):
        """발송상태를 색상과 함께 표시"""
        colors = {
            'preparing': '#f59e0b',  # 황색 - 발송준비중
            'completed': '#3b82f6',  # 파란색 - 발송완료
            'pickup': '#8b5cf6',  # 보라색 - 현장 수령
        }
        color = colors.get(obj.delivery_status, '#6b7280')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_delivery_status_display()
        )
    delivery_status_colored.short_description = '발송 상태'
    delivery_status_colored.admin_order_field = 'delivery_status'
    
    def items_count(self, obj):
        """주문 아이템 개수"""
        return getattr(obj, 'items_count_db', obj.items.count())
    items_count.short_description = '상품 수'
    
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
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">상품명</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: center;">수량</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: right;">상품가격</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: right;">옵션가격</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: right;">총가격</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">선택옵션</th>
                </tr>
            </thead>
            <tbody>
        ''')
        
        for item in items:
            # 상품 링크 생성
            if item.product:
                try:
                    product_url = reverse('admin:products_product_change', args=[item.product.pk])
                    product_link = f'<a href="{product_url}" target="_blank">{item.product.title}</a>'
                except:
                    product_link = item.product.title
            else:
                product_link = item.product_title
            
            # 선택된 옵션들 표시
            options_display = '-'
            if item.selected_options:
                options_list = []
                for option_name, choice_name in item.selected_options.items():
                    options_list.append(f"{option_name}: {choice_name}")
                options_display = '<br>'.join(options_list)
            
            html_parts.append(f'''
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;">{product_link}</td>
                    <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">{item.quantity}</td>
                    <td style="border: 1px solid #ddd; padding: 8px; text-align: right;">{item.product_price:,} sats</td>
                    <td style="border: 1px solid #ddd; padding: 8px; text-align: right;">{item.options_price:,} sats</td>
                    <td style="border: 1px solid #ddd; padding: 8px; text-align: right;"><strong>{item.total_price:,} sats</strong></td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{options_display}</td>
                </tr>
            ''')
        
        html_parts.append('</tbody></table>')
        html_parts.append('</div>')
        
        return format_html(''.join(html_parts))
    
    items_summary.short_description = '주문 아이템 상세'


# @admin.register(OrderItem)
# class OrderItemAdmin(admin.ModelAdmin):
#     list_display = ['order', 'product_title', 'quantity', 'product_price', 'options_price', 'total_price']
#     list_filter = ['order__store', 'created_at']
#     search_fields = ['order__order_number', 'product_title']
#     readonly_fields = ['unit_price', 'total_price', 'created_at']
#     list_per_page = 10


# @admin.register(PurchaseHistory)
# class PurchaseHistoryAdmin(admin.ModelAdmin):
#     list_display = ['user', 'store_name', 'total_amount', 'purchase_date', 'auto_delete_at', 'order_link']
#     list_filter = ['purchase_date', 'auto_delete_at']
#     search_fields = ['user__username', 'store_name', 'order__order_number']
#     readonly_fields = ['purchase_date', 'auto_delete_at', 'order_link', 'order_items_display']
#     list_per_page = 10
#     
#     fieldsets = (
#         ('구매 정보', {
#             'fields': ('user', 'order_link', 'store_name', 'total_amount', 'purchase_date')
#         }),
#         ('주문 아이템들', {
#             'fields': ('order_items_display',),
#         }),
#         ('시스템 정보', {
#             'fields': ('auto_delete_at',),
#             'classes': ('collapse',)
#         })
#     )
#     
#     def order_link(self, obj):
#         """주문 링크"""
#         if obj.order:
#             url = reverse('admin:orders_order_change', args=[obj.order.id])
#             return format_html('<a href="{}">{}</a>', url, obj.order.order_number)
#         return '-'
#     order_link.short_description = '주문'
#     
#     def order_items_display(self, obj):
#         """주문 아이템들 표시"""
#         if not obj.order:
#             return '-'
#         
#         items = obj.order.items.all()
#         if not items:
#             return '주문 아이템이 없습니다.'
#         
#         html_parts = []
#         html_parts.append('<table style="width: 100%; border-collapse: collapse; margin-top: 10px;">')
#         html_parts.append('''
#             <thead>
#                 <tr style="background-color: #f8f9fa;">
#                     <th style="border: 1px solid #dee2e6; padding: 8px; text-align: left;">상품명</th>
#                     <th style="border: 1px solid #dee2e6; padding: 8px; text-align: center;">수량</th>
#                     <th style="border: 1px solid #dee2e6; padding: 8px; text-align: right;">상품가격</th>
#                     <th style="border: 1px solid #dee2e6; padding: 8px; text-align: right;">옵션가격</th>
#                     <th style="border: 1px solid #dee2e6; padding: 8px; text-align: right;">총가격</th>
#                     <th style="border: 1px solid #dee2e6; padding: 8px; text-align: left;">선택옵션</th>
#                 </tr>
#             </thead>
#             <tbody>
#         ''')
#         
#         for item in items:
#             # 상품 링크 생성
#             if item.product:
#                 try:
#                     product_url = reverse('admin:products_product_change', args=[item.product.pk])
#                     product_link = f'<a href="{product_url}">{item.product_title}</a>'
#                 except:
#                     product_link = item.product_title
#             else:
#                 product_link = item.product_title
#             
#             # 선택된 옵션들 표시
#             options_display = '-'
#             if item.selected_options:
#                 options_list = []
#                 for option_name, choice_name in item.selected_options.items():
#                     options_list.append(f"{option_name}: {choice_name}")
#                 options_display = '<br>'.join(options_list)
#             
#             html_parts.append(f'''
#                 <tr>
#                     <td style="border: 1px solid #dee2e6; padding: 8px;">{product_link}</td>
#                     <td style="border: 1px solid #dee2e6; padding: 8px; text-align: center;">{item.quantity}</td>
#                     <td style="border: 1px solid #dee2e6; padding: 8px; text-align: right;">{item.product_price:,} sats</td>
#                     <td style="border: 1px solid #dee2e6; padding: 8px; text-align: right;">{item.options_price:,} sats</td>
#                     <td style="border: 1px solid #dee2e6; padding: 8px; text-align: right;"><strong>{item.total_price:,} sats</strong></td>
#                     <td style="border: 1px solid #dee2e6; padding: 8px;">{options_display}</td>
#                 </tr>
#             ''')
#         
#         html_parts.append('</tbody></table>')
#         
#         return format_html(''.join(html_parts))
#     
#     order_items_display.short_description = '주문 아이템들'


class ProductPaymentTransaction(PaymentTransaction):
    class Meta:
        proxy = True
        app_label = 'orders'
        verbose_name = '결제 트랜잭션'
        verbose_name_plural = '결제 트랜잭션'


@admin.register(ProductPaymentTransaction)
class ProductPaymentTransactionAdmin(BasePaymentTransactionAdmin):
    """상품 주문과 연결된 결제 트랜잭션."""

    def get_queryset(self, request):
        return super().get_queryset(request).filter(order__isnull=False)


class ProductManualPaymentTransaction(ManualPaymentTransaction):
    class Meta:
        proxy = True
        app_label = 'orders'
        verbose_name = '수동 저장 결제'
        verbose_name_plural = '수동 저장 결제'


@admin.register(ProductManualPaymentTransaction)
class ProductManualPaymentTransactionAdmin(BaseManualPaymentTransactionAdmin):
    """상품 주문 대상 수동 저장 결제."""

    def get_queryset(self, request):
        return super().get_queryset(request).filter(order__isnull=False)


class ProductPaymentStageLog(PaymentStageLog):
    class Meta:
        proxy = True
        app_label = 'orders'
        verbose_name = '결제 단계 로그'
        verbose_name_plural = '결제 단계 로그'


@admin.register(ProductPaymentStageLog)
class ProductPaymentStageLogAdmin(BasePaymentStageLogAdmin):
    """상품 주문 결제 단계 로그."""

    def get_queryset(self, request):
        return super().get_queryset(request).filter(transaction__order__isnull=False)


class ProductOrderItemReservation(OrderItemReservation):
    class Meta:
        proxy = True
        app_label = 'orders'
        verbose_name = '재고 예약'
        verbose_name_plural = '재고 예약'


@admin.register(ProductOrderItemReservation)
class ProductOrderItemReservationAdmin(BaseOrderItemReservationAdmin):
    """상품 주문과 연결된 재고 예약."""

    def get_queryset(self, request):
        return super().get_queryset(request).filter(transaction__order__isnull=False)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        'payment_hash_short', 'user', 'store', 'amount_sats', 
        'status_colored', 'created_at', 'expires_at', 'paid_at', 'order_link'
    ]
    list_filter = ['status', 'store', 'created_at', 'expires_at']
    search_fields = ['payment_hash', 'user__username', 'user__email', 'store__store_name', 'memo']
    readonly_fields = [
        'payment_hash', 'invoice_string_display', 'created_at', 'updated_at', 
        'is_expired', 'status_display_color'
    ]
    list_per_page = 10
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('payment_hash', 'amount_sats', 'memo', 'status')
        }),
        ('관련 정보', {
            'fields': ('user', 'store', 'order')
        }),
        ('인보이스 데이터', {
            'fields': ('invoice_string_display',),
            'classes': ('collapse',)
        }),
        ('시간 정보', {
            'fields': ('created_at', 'expires_at', 'paid_at', 'updated_at', 'is_expired'),
            'classes': ('collapse',)
        })
    )
    
    def payment_hash_short(self, obj):
        """결제 해시 축약 표시"""
        return f"{obj.payment_hash[:8]}...{obj.payment_hash[-8:]}" if len(obj.payment_hash) > 16 else obj.payment_hash
    payment_hash_short.short_description = '결제 해시'
    
    def status_colored(self, obj):
        """상태를 색상과 함께 표시"""
        color = obj.status_display_color
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_colored.short_description = '상태'
    
    def order_link(self, obj):
        """주문 링크"""
        if obj.order:
            url = reverse('admin:orders_order_change', args=[obj.order.id])
            return format_html('<a href="{}">{}</a>', url, obj.order.order_number)
        return '-'
    order_link.short_description = '주문'
    
    def invoice_string_display(self, obj):
        """인보이스 문자열 표시 (축약)"""
        if len(obj.invoice_string) > 100:
            return format_html(
                '<textarea readonly style="width: 100%; height: 100px; font-family: monospace; font-size: 0.8em;">{}</textarea>',
                obj.invoice_string
            )
        return obj.invoice_string
    invoice_string_display.short_description = '인보이스 문자열'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'store', 'order')


# Admin 사이트 커스터마이징은 settings.py에서 통합 관리

# 모델의 Meta 클래스에서 verbose_name 설정
Cart._meta.verbose_name = '장바구니'
Cart._meta.verbose_name_plural = '장바구니들'
# CartItem은 인라인으로만 표시되므로 verbose_name만 설정
CartItem._meta.verbose_name = '상품'
CartItem._meta.verbose_name_plural = '상품들'
Order._meta.verbose_name = '주문'
Order._meta.verbose_name_plural = '주문들'
OrderItem._meta.verbose_name = '주문 아이템'
OrderItem._meta.verbose_name_plural = '주문 아이템들'
PurchaseHistory._meta.verbose_name = '구매 내역'
PurchaseHistory._meta.verbose_name_plural = '구매 내역들'
Invoice._meta.verbose_name = '인보이스'
Invoice._meta.verbose_name_plural = '인보이스들'

# 가상의 app_label 설정 (admin에서만 보이는 용도)
Cart._meta.app_label = 'orders'
CartItem._meta.app_label = 'orders'
Order._meta.app_label = 'orders'
OrderItem._meta.app_label = 'orders'
PurchaseHistory._meta.app_label = 'orders'
Invoice._meta.app_label = 'orders'
