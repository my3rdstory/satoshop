from django.contrib import admin
from django.utils.html import format_html
from .models import LiveLecture, LiveLectureImage, LiveLectureOrder




class LiveLectureImageInline(admin.TabularInline):
    model = LiveLectureImage
    extra = 0
    readonly_fields = ['file_size', 'width', 'height', 'uploaded_at', 'uploaded_by']


@admin.register(LiveLecture)
class LiveLectureAdmin(admin.ModelAdmin):
    list_display = ['name', 'store', 'price_display', 'display_price', 'max_participants', 'current_participants', 'is_active', 'date_time']
    list_filter = ['price_display', 'is_active', 'is_temporarily_closed', 'created_at', 'store']
    search_fields = ['name', 'store__store_name', 'instructor_email']
    ordering = ['-created_at']
    readonly_fields = ['current_participants', 'created_at', 'updated_at']
    inlines = [LiveLectureImageInline]
    list_per_page = 10
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('store', 'name', 'description', 'date_time', 'special_notes')
        }),
        ('강사 정보', {
            'fields': ('instructor_contact', 'instructor_email', 'instructor_chat_channel')
        }),
        ('정원 설정', {
            'fields': ('max_participants', 'no_limit', 'current_participants')
        }),
        ('가격 설정', {
            'fields': ('price_display', 'price', 'price_krw')
        }),
        ('할인 설정', {
            'fields': ('is_discounted', 'discounted_price', 'discounted_price_krw', 'early_bird_end_date', 'early_bird_end_time'),
            'classes': ('collapse',)
        }),
        ('상태', {
            'fields': ('is_active', 'is_temporarily_closed')
        }),
        ('안내 메시지', {
            'fields': ('completion_message',),
            'classes': ('collapse',)
        }),
        ('시스템 정보', {
            'fields': ('created_at', 'updated_at', 'deleted_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """삭제된 라이브 강의는 목록에서 제외"""
        return super().get_queryset(request).filter(deleted_at__isnull=True).select_related('store')
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # 수정 시
            return self.readonly_fields + ['store']
        return self.readonly_fields


@admin.register(LiveLectureOrder)
class LiveLectureOrderAdmin(admin.ModelAdmin):
    list_display = ['live_lecture', 'user', 'status', 'price', 'invoice_display', 'is_early_bird', 'paid_at', 'created_at']
    list_filter = ['status', 'is_early_bird', 'created_at', 'live_lecture__store']
    search_fields = ['live_lecture__name', 'user__username', 'user__email', 'order_number', 'payment_hash']
    ordering = ['-created_at']
    readonly_fields = ['order_number', 'created_at', 'updated_at', 'paid_at', 'confirmed_at']
    list_per_page = 10
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('live_lecture', 'live_lecture__store', 'user')
    
    fieldsets = (
        ('주문 정보', {
            'fields': ('live_lecture', 'user', 'order_number', 'status')
        }),
        ('가격 정보', {
            'fields': ('price', 'is_early_bird', 'discount_rate', 'original_price')
        }),
        ('결제 정보', {
            'fields': ('payment_hash', 'payment_request', 'paid_at'),
            'classes': ('collapse',)
        }),
        ('참가 정보', {
            'fields': ('confirmed_at', 'confirmation_message_sent', 'attended', 'attended_at')
        }),
        ('임시 예약', {
            'fields': ('is_temporary_reserved', 'reservation_expires_at', 'auto_cancelled_reason'),
            'classes': ('collapse',)
        }),
        ('시스템 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # 수정 시
            return self.readonly_fields + ['live_lecture', 'user']
        return self.readonly_fields
    
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
