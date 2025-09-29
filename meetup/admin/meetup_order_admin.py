from django.contrib import admin, messages
from django.http import HttpResponse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.db.models import Case, When, Value, BooleanField
from ..models import MeetupOrder, MeetupOrderOption
from .filters import PaymentHashFilter


def _format_local(dt, fmt='%Y-%m-%d %H:%M:%S', default=''):
    if not dt:
        return default
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return timezone.localtime(dt).strftime(fmt)


class MeetupOrderOptionInline(admin.TabularInline):
    """밋업 주문 옵션 인라인 어드민"""
    model = MeetupOrderOption
    extra = 0
    readonly_fields = ['option', 'choice', 'additional_price']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(MeetupOrder)
class MeetupOrderAdmin(admin.ModelAdmin):
    """밋업 주문 어드민"""
    list_display = [
        'order_number', 'meetup_name_display', 'store_display', 'participant_name', 
        'order_status_display', 'payment_status_display', 'invoice_display', 'attended_status_display',
        'total_price_display', 'reservation_status_display', 'created_at_display'
    ]
    list_filter = [
        'meetup__store', 'meetup', 'status', 'attended', 'is_early_bird', 
        'is_temporary_reserved', PaymentHashFilter, 'created_at'
    ]
    search_fields = [
        'order_number', 'participant_name', 'participant_email', 
        'meetup__name', 'participant_phone', 'payment_hash'
    ]
    readonly_fields = [
        'order_number', 'meetup', 'user', 'participant_name', 'participant_email', 
        'participant_phone', 'base_price', 'options_price', 'total_price', 
        'original_price', 'discount_rate', 'is_early_bird', 'payment_hash', 
        'paid_at', 'is_temporary_reserved', 'reservation_expires_at', 
        'reservation_time_left', 'auto_cancelled_reason', 'created_at', 'updated_at',
        'invoice_data_display'
    ]
    ordering = ['-created_at']
    list_per_page = 10
    inlines = [MeetupOrderOptionInline]
    
    # 액션 추가
    actions = [
        'export_orders_csv', 'export_all_orders_csv',
        'mark_as_attended', 'mark_as_not_attended'
    ]

    def get_queryset(self, request):
        """queryset에 결제해시 유무 어노테이션 추가 및 쿼리 최적화"""
        queryset = super().get_queryset(request)
        
        # select_related로 meetup과 store 정보 미리 로드
        queryset = queryset.select_related('meetup', 'meetup__store', 'user')
        
        # prefetch_related로 옵션 정보 미리 로드
        queryset = queryset.prefetch_related('selected_options')
        
        queryset = queryset.annotate(
            has_payment_hash=Case(
                When(payment_hash__isnull=True, then=Value(False)),
                When(payment_hash='', then=Value(False)),
                default=Value(True),
                output_field=BooleanField()
            )
        )
        return queryset
    
    def meetup_name_display(self, obj):
        """밋업명 표시"""
        return format_html(
            '<strong style="color: #495057;">{}</strong>',
            obj.meetup.name
        )
    meetup_name_display.short_description = '밋업명'
    meetup_name_display.admin_order_field = 'meetup__name'
    
    def store_display(self, obj):
        """스토어명 표시"""
        return obj.meetup.store.store_name
    store_display.short_description = '스토어'
    store_display.admin_order_field = 'meetup__store__store_name'
    
    def order_status_display(self, obj):
        """주문 상태 표시"""
        status_colors = {
            'pending': '#f39c12',     # 주황색
            'confirmed': '#27ae60',   # 초록색
            'completed': '#3498db',   # 파란색
            'cancelled': '#e74c3c',   # 빨간색
        }
        status_labels = {
            'pending': '결제 대기',
            'confirmed': '참가 확정',
            'completed': '밋업 완료',
            'cancelled': '참가 취소',
        }
        color = status_colors.get(obj.status, '#95a5a6')
        label = status_labels.get(obj.status, obj.status)
        
        # 취소된 경우 취소 사유도 표시
        if obj.status == 'cancelled' and obj.auto_cancelled_reason:
            return format_html(
                '<span style="color: {}; font-weight: bold;">● {}</span><br>'
                '<small style="color: #6c757d;">{}</small>',
                color, label, obj.auto_cancelled_reason
            )
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">● {}</span>',
            color, label
        )
    order_status_display.short_description = '상태'
    order_status_display.admin_order_field = 'status'
    
    def payment_status_display(self, obj):
        """결제 상태 표시"""
        if obj.total_price == 0:
            return format_html('<span style="color: #28a745;">무료</span>')
        elif obj.payment_hash:
            return format_html('<span style="color: #28a745;">✓ 결제완료</span>')
        else:
            return format_html('<span style="color: #ffc107;">미결제</span>')
    payment_status_display.short_description = '결제 상태'
    
    def attended_status_display(self, obj):
        """참석 상태 표시"""
        if obj.attended:
            return format_html(
                '<span style="color: #27ae60; font-weight: bold; background: #d4edda; padding: 4px 8px; border-radius: 4px;">✓ 참석</span>'
            )
        else:
            return format_html(
                '<span style="color: #6c757d; background: #f8f9fa; padding: 4px 8px; border-radius: 4px;">미참석</span>'
            )
    attended_status_display.short_description = '참석 상태'
    attended_status_display.admin_order_field = 'attended'
    
    def created_at_display(self, obj):
        """신청일시 표시"""
        return timezone.localtime(obj.created_at).strftime('%Y.%m.%d %H:%M')
    created_at_display.short_description = '신청일시'
    created_at_display.admin_order_field = 'created_at'
    
    def status_display(self, obj):
        """상태 표시"""
        status_colors = {
            'pending': '#f39c12',     # 주황색
            'confirmed': '#27ae60',   # 초록색
            'completed': '#3498db',   # 파란색
            'cancelled': '#e74c3c',   # 빨간색
        }
        status_labels = {
            'pending': '결제 대기',
            'confirmed': '참가 확정',
            'completed': '밋업 완료',
            'cancelled': '참가 취소',
        }
        color = status_colors.get(obj.status, '#95a5a6')
        label = status_labels.get(obj.status, obj.status)
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, label
        )
    status_display.short_description = '상태'
    
    def payment_hash_display(self, obj):
        """결제해시 표시"""
        if obj.payment_hash and obj.payment_hash.strip():
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">✓ 있음</span><br>'
                '<small style="font-family: monospace; color: #6c757d;">{}</small>',
                obj.payment_hash[:16] + '...' if len(obj.payment_hash) > 16 else obj.payment_hash
            )
        else:
            return format_html('<span style="color: #6c757d;">없음</span>')
    payment_hash_display.short_description = '결제해시'
    payment_hash_display.admin_order_field = 'has_payment_hash'
    
    def reservation_status_display(self, obj):
        """예약 상태 표시 (임시 예약 및 만료 시간 포함)"""
        now = timezone.now()
        
        if not obj.is_temporary_reserved:
            if obj.status == 'confirmed':
                return format_html('<span style="color: #27ae60; font-weight: bold;">✓ 확정</span>')
            elif obj.status == 'cancelled':
                if obj.auto_cancelled_reason:
                    return format_html(
                        '<span style="color: #e74c3c;">취소</span><br>'
                        '<small style="color: #7f8c8d;">{}</small>',
                        obj.auto_cancelled_reason
                    )
                return format_html('<span style="color: #e74c3c;">취소</span>')
            return format_html('<span style="color: #95a5a6;">-</span>')
        
        if obj.reservation_expires_at:
            if now > obj.reservation_expires_at:
                return format_html(
                    '<span style="color: #e74c3c; font-weight: bold;">⏱ 만료</span><br>'
                    '<small style="color: #7f8c8d;">{}</small>',
                    _format_local(obj.reservation_expires_at, "%m/%d %H:%M")
                )
            else:
                time_left = obj.reservation_expires_at - now
                minutes_left = int(time_left.total_seconds() / 60)
                if minutes_left < 5:
                    color = '#e74c3c'  # 빨간색 (위험)
                elif minutes_left < 15:
                    color = '#f39c12'  # 주황색 (주의)
                else:
                    color = '#27ae60'  # 초록색 (안전)
                    
                return format_html(
                    '<span style="color: {}; font-weight: bold;">⏳ 임시예약</span><br>'
                    '<small style="color: {};">{} 남음 ({}분)</small>',
                    color,
                    color,
                    _format_local(obj.reservation_expires_at, "%m/%d %H:%M"),
                    minutes_left
                )
        
        return format_html('<span style="color: #f39c12; font-weight: bold;">⏳ 임시예약</span>')
    reservation_status_display.short_description = '예약 상태'
    
    def reservation_time_left(self, obj):
        """예약 남은 시간"""
        if not obj.is_temporary_reserved or not obj.reservation_expires_at:
            return "-"
        
        now = timezone.now()
        
        if now > obj.reservation_expires_at:
            return format_html('<span style="color: #e74c3c;">만료됨</span>')
        
        time_left = obj.reservation_expires_at - now
        minutes_left = int(time_left.total_seconds() / 60)
        seconds_left = int(time_left.total_seconds() % 60)
        
        if minutes_left < 5:
            color = '#e74c3c'
        elif minutes_left < 15:
            color = '#f39c12'
        else:
            color = '#27ae60'
            
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}분 {}초</span>',
            color, minutes_left, seconds_left
        )
    reservation_time_left.short_description = '예약 남은 시간'
    
    def attended_display(self, obj):
        """참석 여부 표시"""
        if obj.attended:
            if obj.attended_at:
                return mark_safe(
                    f'<span style="color: #27ae60; font-weight: bold;">✓ 참석</span><br>'
                    f'<small style="color: #7f8c8d;">{_format_local(obj.attended_at, "%m/%d %H:%M")}</small>'
                )
            else:
                return mark_safe('<span style="color: #27ae60; font-weight: bold;">✓ 참석</span>')
        else:
            return mark_safe('<span style="color: #95a5a6;">미참석</span>')
    attended_display.short_description = '참석 여부'
    
    def total_price_display(self, obj):
        """총 가격 표시"""
        if obj.is_early_bird and obj.original_price:
            return format_html(
                '<span style="text-decoration: line-through; color: #999;">{} sats</span><br>'
                '<span style="color: #e74c3c; font-weight: bold;">{} sats</span><br>'
                '<small style="color: #27ae60;">할인 {}%</small>',
                f"{obj.original_price:,}",
                f"{obj.total_price:,}",
                obj.discount_rate
            )
        return f"{obj.total_price:,} sats"
    total_price_display.short_description = '결제금액'
    
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
    
    # 커스텀 액션들

    def mark_as_attended(self, request, queryset):
        """선택된 주문들의 참가자를 참석으로 표시"""
        updated_count = 0
        for order in queryset:
            if not order.attended:
                order.attended = True
                order.attended_at = timezone.now()
                order.save()
                updated_count += 1
        
        self.message_user(request, f'{updated_count}개의 주문이 참석으로 표시되었습니다.')
    
    mark_as_attended.short_description = '선택된 주문을 참석으로 표시'
    
    def mark_as_not_attended(self, request, queryset):
        """선택된 주문들의 참가자를 미참석으로 표시"""
        updated_count = 0
        for order in queryset:
            if order.attended:
                order.attended = False
                order.attended_at = None
                order.save()
                updated_count += 1
        
        self.message_user(request, f'{updated_count}개의 주문이 미참석으로 표시되었습니다.')
    
    mark_as_not_attended.short_description = '선택된 주문을 미참석으로 표시'

    def export_orders_csv(self, request, queryset):
        """선택된 밋업 주문들을 CSV로 다운로드"""
        import csv
        
        # CSV 응답 생성
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        generated_at = timezone.localtime(timezone.now())
        response['Content-Disposition'] = f'attachment; filename="meetup_orders_{generated_at.strftime("%Y%m%d_%H%M")}.csv"'
        response.write('\ufeff'.encode('utf8'))  # BOM for Excel
        
        writer = csv.writer(response)
        
        # 헤더 작성
        headers = [
            '주문번호', '밋업명', '스토어명', '참가자명', '이메일', '연락처', 
            '상태', '기본참가비', '옵션금액', '총참가비', '원가격', '할인율', '조기등록여부',
            '결제해시', '결제일시', '참가신청일시', '참가확정일시', '참석여부', '참석체크일시',
            '임시예약여부', '예약만료시간', '자동취소사유', '선택옵션'
        ]
        writer.writerow(headers)
        
        # 데이터 작성
        orders = queryset.select_related('meetup', 'meetup__store').prefetch_related('selected_options__option', 'selected_options__choice')
        
        for order in orders:
            # 선택 옵션 정보 수집
            selected_options = []
            for selected_option in order.selected_options.all():
                option_text = f"{selected_option.option.name}: {selected_option.choice.name}"
                if selected_option.additional_price > 0:
                    option_text += f" (+{selected_option.additional_price:,} sats)"
                elif selected_option.additional_price < 0:
                    option_text += f" ({selected_option.additional_price:,} sats)"
                selected_options.append(option_text)
            
            options_text = " | ".join(selected_options) if selected_options else "없음"
            
            # 상태 텍스트 변환
            status_text = {
                'confirmed': '참가확정',
                'completed': '밋업완료',
                'pending': '결제대기',
                'cancelled': '참가취소'
            }.get(order.status, order.status)
            
            row = [
                order.order_number,
                order.meetup.name,
                order.meetup.store.store_name,
                order.participant_name,
                order.participant_email,
                order.participant_phone or '',
                status_text,
                f"{order.base_price:,}",
                f"{order.options_price:,}",
                f"{order.total_price:,}",
                f"{order.original_price:,}" if order.original_price else '',
                f"{order.discount_rate}%" if order.discount_rate else '',
                "예" if order.is_early_bird else "아니오",
                order.payment_hash or '',
                _format_local(order.paid_at),
                _format_local(order.created_at),
                _format_local(order.confirmed_at),
                "참석" if order.attended else "미참석",
                _format_local(order.attended_at),
                "예" if order.is_temporary_reserved else "아니오",
                _format_local(order.reservation_expires_at),
                order.auto_cancelled_reason or '',
                options_text
            ]
            writer.writerow(row)
        
        # 메시지 표시
        self.message_user(request, f'{queryset.count()}개의 주문이 CSV로 다운로드되었습니다.')
        return response
    
    export_orders_csv.short_description = '선택된 주문을 CSV로 다운로드'

    def export_all_orders_csv(self, request, queryset):
        """전체 밋업 주문을 CSV로 다운로드 (필터 적용)"""
        import csv
        
        # 현재 적용된 필터를 기반으로 전체 주문 조회
        all_orders = self.get_queryset(request)
        
        # CSV 응답 생성
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        generated_at = timezone.localtime(timezone.now())
        response['Content-Disposition'] = f'attachment; filename="all_meetup_orders_{generated_at.strftime("%Y%m%d_%H%M")}.csv"'
        response.write('\ufeff'.encode('utf8'))  # BOM for Excel
        
        writer = csv.writer(response)
        
        # 헤더 작성
        headers = [
            '주문번호', '밋업명', '스토어명', '참가자명', '이메일', '연락처', 
            '상태', '기본참가비', '옵션금액', '총참가비', '원가격', '할인율', '조기등록여부',
            '결제해시', '결제일시', '참가신청일시', '참가확정일시', '참석여부', '참석체크일시',
            '임시예약여부', '예약만료시간', '자동취소사유', '선택옵션'
        ]
        writer.writerow(headers)
        
        # 데이터 작성
        orders = all_orders.select_related('meetup', 'meetup__store').prefetch_related('selected_options__option', 'selected_options__choice')
        
        for order in orders:
            # 선택 옵션 정보 수집
            selected_options = []
            for selected_option in order.selected_options.all():
                option_text = f"{selected_option.option.name}: {selected_option.choice.name}"
                if selected_option.additional_price > 0:
                    option_text += f" (+{selected_option.additional_price:,} sats)"
                elif selected_option.additional_price < 0:
                    option_text += f" ({selected_option.additional_price:,} sats)"
                selected_options.append(option_text)
            
            options_text = " | ".join(selected_options) if selected_options else "없음"
            
            # 상태 텍스트 변환
            status_text = {
                'confirmed': '참가확정',
                'completed': '밋업완료',
                'pending': '결제대기',
                'cancelled': '참가취소'
            }.get(order.status, order.status)
            
            row = [
                order.order_number,
                order.meetup.name,
                order.meetup.store.store_name,
                order.participant_name,
                order.participant_email,
                order.participant_phone or '',
                status_text,
                f"{order.base_price:,}",
                f"{order.options_price:,}",
                f"{order.total_price:,}",
                f"{order.original_price:,}" if order.original_price else '',
                f"{order.discount_rate}%" if order.discount_rate else '',
                "예" if order.is_early_bird else "아니오",
                order.payment_hash or '',
                _format_local(order.paid_at),
                _format_local(order.created_at),
                _format_local(order.confirmed_at),
                "참석" if order.attended else "미참석",
                _format_local(order.attended_at),
                "예" if order.is_temporary_reserved else "아니오",
                _format_local(order.reservation_expires_at),
                order.auto_cancelled_reason or '',
                options_text
            ]
            writer.writerow(row)
        
        # 메시지 표시
        self.message_user(request, f'전체 {orders.count()}개의 주문이 CSV로 다운로드되었습니다.')
        return response
    
    export_all_orders_csv.short_description = '전체 주문을 CSV로 다운로드 (필터 적용)'

    fieldsets = (
        ('주문 정보', {
            'fields': ('order_number', 'meetup', 'status')
        }),
        ('참가자 정보', {
            'fields': ('participant_name', 'participant_email', 'participant_phone')
        }),
        ('임시 예약 정보', {
            'fields': ('is_temporary_reserved', 'reservation_expires_at', 'reservation_time_left', 'auto_cancelled_reason'),
            'description': '밋업 신청 과정에서의 임시 예약 상태를 확인할 수 있습니다.'
        }),
        ('참석 정보', {
            'fields': ('attended', 'attended_at'),
            'description': '밋업 당일 참석 여부를 확인할 수 있습니다.'
        }),
        ('가격 정보', {
            'fields': ('base_price', 'options_price', 'total_price', 'original_price', 'discount_rate', 'is_early_bird')
        }),
        ('결제 정보', {
            'fields': ('payment_hash', 'paid_at')
        }),
        ('인보이스 데이터', {
            'fields': ('invoice_data_display',),
            'classes': ('collapse',)
        }),
        ('메타 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """추가 권한 없음 (결제를 통해서만 생성)"""
        return False


# @admin.register(MeetupOrderOption)
# class MeetupOrderOptionAdmin(admin.ModelAdmin):
#     list_display = ['order', 'option', 'choice', 'additional_price_display']
#     list_filter = ['order__meetup__store', 'option', 'order__created_at']
#     search_fields = ['order__order_number', 'order__participant_name', 'option__name', 'choice__name']
#     readonly_fields = ['order', 'option', 'choice', 'additional_price']
#     
#     def additional_price_display(self, obj):
#         """추가요금 표시"""
#         if obj.additional_price > 0:
#             return f"+{obj.additional_price:,} sats"
#         elif obj.additional_price < 0:
#             return f"{obj.additional_price:,} sats"
#         return "무료"
#     additional_price_display.short_description = '추가요금'
#     
#     def has_add_permission(self, request):
#         """추가 권한 없음"""
#         return False
#     
#     def has_change_permission(self, request, obj=None):
#         """수정 권한 없음"""
#         return False 
