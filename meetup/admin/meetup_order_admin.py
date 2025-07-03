from django.contrib import admin, messages
from django.http import HttpResponse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.db.models import Case, When, Value, BooleanField
from ..models import MeetupOrder, MeetupOrderOption
from .filters import PaymentHashFilter


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
    list_display = [
        'order_number', 'meetup', 'participant_name', 'status_display', 
        'payment_hash_display', 'reservation_status_display', 'attended_display', 'total_price_display', 
        'is_early_bird', 'created_at'
    ]
    list_filter = [
        'status', 'is_temporary_reserved', 'attended', 'meetup__store', 
        'is_early_bird', 'created_at', 'paid_at', 'attended_at',
        'reservation_expires_at', PaymentHashFilter
    ]
    search_fields = [
        'order_number', 'participant_name', 'participant_email', 
        'meetup__name', 'auto_cancelled_reason'
    ]
    readonly_fields = [
        'order_number', 'meetup', 'participant_name', 'participant_email', 
        'participant_phone', 'base_price', 'options_price', 'total_price', 
        'original_price', 'discount_rate', 'is_early_bird', 'payment_hash', 
        'paid_at', 'created_at', 'updated_at', 'reservation_time_left'
    ]
    ordering = ['-created_at']
    inlines = [MeetupOrderOptionInline]
    
    # 액션 추가
    actions = ['confirm_paid_reservations', 'mark_as_confirmed', 'cancel_expired_reservations', 'extend_reservations', 'export_orders_csv', 'export_all_orders_csv']

    def get_queryset(self, request):
        """queryset에 결제해시 유무 어노테이션 추가"""
        queryset = super().get_queryset(request)
        
        queryset = queryset.annotate(
            has_payment_hash=Case(
                When(payment_hash__isnull=True, then=Value(False)),
                When(payment_hash='', then=Value(False)),
                default=Value(True),
                output_field=BooleanField()
            )
        )
        return queryset
    
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
                    obj.reservation_expires_at.strftime("%m/%d %H:%M")
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
                    obj.reservation_expires_at.strftime("%m/%d %H:%M"),
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
                    f'<small style="color: #7f8c8d;">{obj.attended_at.strftime("%m/%d %H:%M")}</small>'
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
    
    # 커스텀 액션들
    def confirm_paid_reservations(self, request, queryset):
        """결제해시가 있는 결제대기 주문들을 참가확정으로 변경"""
        # 결제해시가 있는 pending 상태 주문들만 필터링
        eligible_orders = queryset.filter(
            status='pending'
        ).exclude(
            payment_hash__isnull=True
        ).exclude(
            payment_hash=''
        )
        
        if not eligible_orders.exists():
            self.message_user(request, '결제해시가 있는 결제대기 주문이 없습니다.', level=messages.WARNING)
            return
        
        confirmed_count = 0
        failed_count = 0
        
        for order in eligible_orders:
            try:
                # 상태를 confirmed로 변경
                order.status = 'confirmed'
                order.is_temporary_reserved = False
                order.confirmed_at = timezone.now()
                order.paid_at = timezone.now()
                order.reservation_expires_at = None  # 확정되면 만료시간 제거
                order.save()
                confirmed_count += 1
            except Exception as e:
                failed_count += 1
        
        if confirmed_count > 0:
            self.message_user(
                request, 
                f'{confirmed_count}개의 주문이 참가확정으로 변경되었습니다.',
                level=messages.SUCCESS
            )
        
        if failed_count > 0:
            self.message_user(
                request,
                f'{failed_count}개의 주문 처리 중 오류가 발생했습니다.',
                level=messages.ERROR
            )
    
    confirm_paid_reservations.short_description = '결제해시가 있는 결제대기 주문을 참가확정으로 변경'
    
    def mark_as_confirmed(self, request, queryset):
        """선택된 주문들을 확정 상태로 변경"""
        # services 모듈이 있다면 사용, 없다면 직접 처리
        try:
            from ..services import confirm_reservation
            confirmed_count = 0
            for order in queryset.filter(status='pending', is_temporary_reserved=True):
                if confirm_reservation(order):
                    confirmed_count += 1
        except ImportError:
            confirmed_count = 0
            for order in queryset.filter(status='pending'):
                order.status = 'confirmed'
                order.is_temporary_reserved = False
                order.confirmed_at = timezone.now()
                order.save()
                confirmed_count += 1
        
        self.message_user(request, f'{confirmed_count}개의 주문이 확정되었습니다.')
    mark_as_confirmed.short_description = '선택된 임시예약을 확정으로 변경'
    
    def cancel_expired_reservations(self, request, queryset):
        """만료된 예약들을 취소"""
        try:
            from ..services import cancel_expired_reservations
            cancelled_count = cancel_expired_reservations()
        except ImportError:
            # services 모듈이 없으면 직접 처리
            now = timezone.now()
            expired_orders = MeetupOrder.objects.filter(
                status='pending',
                is_temporary_reserved=True,
                reservation_expires_at__lt=now
            )
            cancelled_count = expired_orders.count()
            expired_orders.update(
                status='cancelled',
                auto_cancelled_reason='예약 시간 만료로 자동 취소'
            )
        
        self.message_user(request, f'{cancelled_count}개의 만료된 예약이 취소되었습니다.')
    cancel_expired_reservations.short_description = '만료된 예약 자동 취소'
    
    def extend_reservations(self, request, queryset):
        """선택된 예약들의 시간을 연장"""
        try:
            from ..services import extend_reservation
            extended_count = 0
            for order in queryset.filter(status='pending', is_temporary_reserved=True):
                if extend_reservation(order):
                    extended_count += 1
        except ImportError:
            # services 모듈이 없으면 직접 처리
            extended_count = 0
            for order in queryset.filter(status='pending', is_temporary_reserved=True):
                if order.reservation_expires_at:
                    order.reservation_expires_at = timezone.now() + timezone.timedelta(seconds=180)
                    order.save()
                    extended_count += 1
        
        self.message_user(request, f'{extended_count}개의 예약 시간이 연장되었습니다.')
    extend_reservations.short_description = '선택된 예약 시간 연장 (180초)'

    def export_orders_csv(self, request, queryset):
        """선택된 밋업 주문들을 CSV로 다운로드"""
        import csv
        
        # CSV 응답 생성
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="meetup_orders_{timezone.now().strftime("%Y%m%d_%H%M")}.csv"'
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
                order.paid_at.strftime('%Y-%m-%d %H:%M:%S') if order.paid_at else '',
                order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                order.confirmed_at.strftime('%Y-%m-%d %H:%M:%S') if order.confirmed_at else '',
                "참석" if order.attended else "미참석",
                order.attended_at.strftime('%Y-%m-%d %H:%M:%S') if order.attended_at else '',
                "예" if order.is_temporary_reserved else "아니오",
                order.reservation_expires_at.strftime('%Y-%m-%d %H:%M:%S') if order.reservation_expires_at else '',
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
        response['Content-Disposition'] = f'attachment; filename="all_meetup_orders_{timezone.now().strftime("%Y%m%d_%H%M")}.csv"'
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
                order.paid_at.strftime('%Y-%m-%d %H:%M:%S') if order.paid_at else '',
                order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                order.confirmed_at.strftime('%Y-%m-%d %H:%M:%S') if order.confirmed_at else '',
                "참석" if order.attended else "미참석",
                order.attended_at.strftime('%Y-%m-%d %H:%M:%S') if order.attended_at else '',
                "예" if order.is_temporary_reserved else "아니오",
                order.reservation_expires_at.strftime('%Y-%m-%d %H:%M:%S') if order.reservation_expires_at else '',
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
        ('메타 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """추가 권한 없음 (결제를 통해서만 생성)"""
        return False


@admin.register(MeetupOrderOption)
class MeetupOrderOptionAdmin(admin.ModelAdmin):
    list_display = ['order', 'option', 'choice', 'additional_price_display']
    list_filter = ['order__meetup__store', 'option', 'order__created_at']
    search_fields = ['order__order_number', 'order__participant_name', 'option__name', 'choice__name']
    readonly_fields = ['order', 'option', 'choice', 'additional_price']
    
    def additional_price_display(self, obj):
        """추가요금 표시"""
        if obj.additional_price > 0:
            return f"+{obj.additional_price:,} sats"
        elif obj.additional_price < 0:
            return f"{obj.additional_price:,} sats"
        return "무료"
    additional_price_display.short_description = '추가요금'
    
    def has_add_permission(self, request):
        """추가 권한 없음"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """수정 권한 없음"""
        return False 