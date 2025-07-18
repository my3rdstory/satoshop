from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import DigitalFile, FileOrder, FileDownloadLog


class DeletedListFilter(admin.SimpleListFilter):
    """삭제 상태 필터"""
    title = _('삭제 상태')
    parameter_name = 'deleted_status'
    
    def lookups(self, request, model_admin):
        return (
            ('active', _('활성 (삭제되지 않음)')),
            ('deleted', _('삭제됨')),
            ('all', _('모두 보기')),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'active':
            return queryset.filter(deleted_at__isnull=True)
        elif self.value() == 'deleted':
            return queryset.filter(deleted_at__isnull=False)
        return queryset
    
    def choices(self, changelist):
        # 기본값을 'active'로 설정
        value = self.value() or 'active'
        for lookup, title in self.lookup_choices:
            yield {
                'selected': value == str(lookup),
                'query_string': changelist.get_query_string({self.parameter_name: lookup}),
                'display': title,
            }


@admin.register(DigitalFile)
class DigitalFileAdmin(admin.ModelAdmin):
    list_display = ['name', 'store', 'price_display', 'price_with_krw', 'is_active', 'is_deleted', 'total_downloads', 'created_at']
    list_filter = [DeletedListFilter, 'store', 'price_display', 'is_active', 'is_discounted']
    search_fields = ['name', 'description', 'store__store_name']
    readonly_fields = ['file_hash', 'file_size', 'original_filename', 'created_at', 'updated_at', 'deleted_at', 'total_downloads_display']
    
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
        ('통계', {
            'fields': ('total_downloads_display',)
        }),
        ('타임스탬프', {
            'fields': ('created_at', 'updated_at', 'deleted_at')
        }),
    )
    
    def total_downloads(self, obj):
        """총 다운로드 수 표시 (리스트용)"""
        count = FileDownloadLog.objects.filter(order__digital_file=obj).count()
        return format_html('<span style="font-weight: bold;">{}</span>', count)
    
    total_downloads.short_description = '총 다운로드'
    
    def total_downloads_display(self, obj):
        """총 다운로드 수 상세 표시 (상세보기용)"""
        total = FileDownloadLog.objects.filter(order__digital_file=obj).count()
        unique_users = FileDownloadLog.objects.filter(
            order__digital_file=obj
        ).values('order__user').distinct().count()
        
        return format_html(
            '<div style="font-size: 14px;">'
            '<strong>총 다운로드 수:</strong> {}회<br>'
            '<strong>다운로드한 사용자 수:</strong> {}명'
            '</div>',
            total,
            unique_users
        )
    
    total_downloads_display.short_description = '다운로드 통계'
    
    def is_deleted(self, obj):
        """삭제 여부 표시"""
        if obj.deleted_at:
            return format_html(
                '<span style="color: red;">✗ 삭제됨</span>'
            )
        return format_html(
            '<span style="color: green;">✓ 활성</span>'
        )
    
    is_deleted.short_description = '삭제 상태'
    
    def price_with_krw(self, obj):
        """가격 표시 (원화연동인 경우 사토시 변환)"""
        if obj.price_display == 'free':
            return format_html('<span style="color: green;">무료</span>')
        elif obj.price_display == 'krw':
            # 원화연동인 경우 사토시로 변환
            sats_price = obj.current_price_sats
            krw_price = obj.price_krw
            if sats_price and krw_price:
                return format_html(
                    '<span style="font-weight: bold;">{} sats</span><br>'
                    '<span style="color: gray; font-size: 0.85em;">({}원)</span>',
                    f'{sats_price:,}',
                    f'{krw_price:,.0f}'
                )
            return '-'
        else:
            # 사토시 가격
            if obj.price:
                return format_html(
                    '<span style="font-weight: bold;">{} sats</span>',
                    f'{obj.price:,}'
                )
            return '-'
    
    price_with_krw.short_description = '가격'
    
    def get_queryset(self, request):
        """기본 쿼리셋"""
        qs = super().get_queryset(request)
        # 필터가 설정되지 않은 경우 기본적으로 삭제되지 않은 항목만 표시
        if not request.GET.get('deleted_status'):
            return qs.filter(deleted_at__isnull=True)
        return qs
    
    def hard_delete_selected(self, request, queryset):
        """선택한 파일들을 완전 삭제 (오브젝트 스토리지 포함)"""
        count = 0
        for obj in queryset:
            # delete() 메서드가 오브젝트 스토리지에서도 삭제함
            obj.delete()
            count += 1
        
        self.message_user(
            request,
            f"{count}개의 파일이 완전히 삭제되었습니다. (오브젝트 스토리지 포함)"
        )
    
    hard_delete_selected.short_description = "선택한 파일 완전 삭제 (오브젝트 스토리지 포함)"
    
    actions = ['hard_delete_selected']


@admin.register(FileOrder)
class FileOrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'user', 'digital_file', 'status', 'price', 'invoice_display', 'download_status', 'created_at']
    list_filter = ['status', 'is_discounted', 'download_clicked', 'created_at']
    search_fields = ['order_number', 'user__username', 'digital_file__name', 'payment_hash']
    readonly_fields = ['order_number', 'download_clicked_at', 'created_at', 'updated_at', 'invoice_data_display']
    
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
        ('인보이스 데이터', {
            'fields': ('invoice_data_display',),
            'classes': ('collapse',)
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
    
    def invoice_data_display(self, obj):
        """인보이스 전체 데이터 표시"""
        if obj.payment_request:
            return format_html(
                '<textarea readonly style="width: 100%; height: 100px; font-family: monospace; font-size: 0.8em;">{}</textarea>',
                obj.payment_request
            )
        return '-'
    
    invoice_data_display.short_description = '인보이스 문자열'


@admin.register(FileDownloadLog)
class FileDownloadLogAdmin(admin.ModelAdmin):
    list_display = ['order', 'store_name', 'file_name', 'user', 'ip_address', 'downloaded_at']
    list_filter = ['downloaded_at']
    search_fields = ['order__order_number', 'ip_address', 'order__digital_file__name', 'order__digital_file__store__store_name']
    readonly_fields = ['downloaded_at']
    
    def store_name(self, obj):
        """스토어명 표시"""
        return obj.order.digital_file.store.store_name
    
    store_name.short_description = '스토어'
    store_name.admin_order_field = 'order__digital_file__store__store_name'
    
    def file_name(self, obj):
        """파일명 표시"""
        return obj.order.digital_file.name
    
    file_name.short_description = '파일명'
    file_name.admin_order_field = 'order__digital_file__name'
    
    def user(self, obj):
        """사용자 표시"""
        return obj.order.user.username
    
    user.short_description = '사용자'
    user.admin_order_field = 'order__user__username'
