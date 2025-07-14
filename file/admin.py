from django.contrib import admin
from .models import DigitalFile, FileOrder, FileDownloadLog


@admin.register(DigitalFile)
class DigitalFileAdmin(admin.ModelAdmin):
    list_display = ['name', 'store', 'price_display', 'price', 'is_active', 'created_at']
    list_filter = ['store', 'price_display', 'is_active', 'is_discounted']
    search_fields = ['name', 'description', 'store__name']
    readonly_fields = ['file_hash', 'file_size', 'original_filename', 'created_at', 'updated_at']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('store', 'name', 'description')
        }),
        ('파일 정보', {
            'fields': ('file', 'preview_image', 'original_filename', 'file_size', 'file_hash')
        }),
        ('가격 정보', {
            'fields': ('price_display', 'price', 'price_krw')
        }),
        ('할인 정보', {
            'fields': ('is_discounted', 'discounted_price', 'discounted_price_krw', 'discount_end_date', 'discount_end_time')
        }),
        ('판매 설정', {
            'fields': ('max_downloads', 'download_expiry_days')
        }),
        ('상태', {
            'fields': ('is_active', 'is_temporarily_closed', 'purchase_message')
        }),
        ('타임스탬프', {
            'fields': ('created_at', 'updated_at', 'deleted_at')
        }),
    )


@admin.register(FileOrder)
class FileOrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'user', 'digital_file', 'status', 'price', 'created_at']
    list_filter = ['status', 'is_discounted', 'created_at']
    search_fields = ['order_number', 'user__username', 'digital_file__name']
    readonly_fields = ['order_number', 'created_at', 'updated_at']
    
    fieldsets = (
        ('주문 정보', {
            'fields': ('order_number', 'digital_file', 'user', 'status')
        }),
        ('가격 정보', {
            'fields': ('price', 'is_discounted', 'discount_rate', 'original_price')
        }),
        ('결제 정보', {
            'fields': ('payment_hash', 'payment_request', 'paid_at')
        }),
        ('예약 정보', {
            'fields': ('is_temporary_reserved', 'reservation_expires_at', 'auto_cancelled_reason')
        }),
        ('확정 정보', {
            'fields': ('confirmed_at', 'confirmation_message_sent', 'download_expires_at')
        }),
        ('타임스탬프', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(FileDownloadLog)
class FileDownloadLogAdmin(admin.ModelAdmin):
    list_display = ['order', 'ip_address', 'downloaded_at']
    list_filter = ['downloaded_at']
    search_fields = ['order__order_number', 'ip_address']
    readonly_fields = ['downloaded_at']
