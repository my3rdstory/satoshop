from django.contrib import admin
from django.utils.html import format_html
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
    list_display = ['order_number', 'user', 'digital_file', 'status', 'price', 'invoice_display', 'download_status', 'created_at']
    list_filter = ['status', 'is_discounted', 'download_clicked', 'created_at']
    search_fields = ['order_number', 'user__username', 'digital_file__name', 'payment_hash']
    readonly_fields = ['order_number', 'download_clicked_at', 'created_at', 'updated_at']
    
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
        ('다운로드 추적', {
            'fields': ('download_clicked', 'download_clicked_at', 'download_click_count'),
            'description': '구매자가 다운로드 버튼을 클릭했는지 추적합니다.'
        }),
        ('타임스탬프', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def download_status(self, obj):
        """다운로드 상태 표시"""
        if obj.status != 'confirmed':
            return '미구매'
        elif obj.download_clicked:
            return f'✅ 다운로드 ({obj.download_click_count}회)'
        else:
            return '❌ 미다운로드'
    
    download_status.short_description = '다운로드 상태'
    
    def invoice_display(self, obj):
        """인보이스 표시"""
        if obj.payment_hash:
            # 인보이스의 일부만 표시 (앞 10자, 뒤 10자)
            if len(obj.payment_hash) > 25:
                display_text = f"{obj.payment_hash[:10]}...{obj.payment_hash[-10:]}"
            else:
                display_text = obj.payment_hash
            
            return format_html(
                '<span title="{}" style="font-family: monospace; font-size: 0.85em;">{}</span>',
                obj.payment_hash,
                display_text
            )
        return '-'
    
    invoice_display.short_description = '인보이스'


@admin.register(FileDownloadLog)
class FileDownloadLogAdmin(admin.ModelAdmin):
    list_display = ['order', 'ip_address', 'downloaded_at']
    list_filter = ['downloaded_at']
    search_fields = ['order__order_number', 'ip_address']
    readonly_fields = ['downloaded_at']
