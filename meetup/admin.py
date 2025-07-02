from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.shortcuts import render
from django.db import models
from django.db.models import Count, Q
from datetime import timedelta
from .models import Meetup, MeetupImage, MeetupOption, MeetupChoice, MeetupOrder, MeetupOrderOption, Store

# 임시예약 전용 프록시 모델
class TemporaryReservation(MeetupOrder):
    """임시예약 전용 프록시 모델"""
    class Meta:
        proxy = True
        verbose_name = "임시 예약"
        verbose_name_plural = "임시 예약 관리"

class MeetupImageInline(admin.TabularInline):
    """밋업 이미지 인라인 어드민"""
    model = MeetupImage
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

class MeetupChoiceInline(admin.TabularInline):
    """밋업 선택지 인라인 어드민"""
    model = MeetupChoice
    extra = 1
    readonly_fields = ['created_at']
    fields = ('name', 'additional_price', 'order', 'created_at')

class MeetupOptionInline(admin.TabularInline):
    """밋업 옵션 인라인 어드민"""
    model = MeetupOption
    extra = 1
    readonly_fields = ['created_at']
    fields = ('name', 'is_required', 'order', 'created_at')

@admin.register(Meetup)
class MeetupAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'store', 'price_display', 'is_free', 'is_active', 'is_discounted', 
        'participants_display', 'remaining_spots_display', 'reservation_stats_display', 'created_at'
    ]
    list_filter = ['store', 'is_free', 'is_active', 'is_discounted', 'is_temporarily_closed', 'created_at']
    search_fields = ['name', 'description', 'store__store_name']
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'current_price', 'is_early_bird_active', 
        'public_discount_rate', 'current_participants', 'reserved_participants', 
        'actual_remaining_spots', 'pending_reservations_count'
    ]
    inlines = [MeetupImageInline, MeetupOptionInline]
    
    # 액션 추가
    actions = ['cleanup_expired_reservations', 'export_participants']
    
    def price_display(self, obj):
        """가격 표시"""
        if obj.is_free:
            return format_html('<span style="color: #27ae60; font-weight: bold;">무료</span>')
        elif obj.is_discounted and obj.discounted_price:
            return format_html(
                '<span style="text-decoration: line-through; color: #999;">{} sats</span><br>'
                '<span style="color: #e74c3c; font-weight: bold;">{} sats</span>',
                f"{obj.price:,}",
                f"{obj.discounted_price:,}"
            )
        return f"{obj.price:,} sats"
    price_display.short_description = '참가비'
    
    def participants_display(self, obj):
        """참가자 현황 표시"""
        if obj.max_participants:
            confirmed = obj.current_participants
            reserved = obj.reserved_participants
            max_participants = obj.max_participants
            
            # 확정된 참가자 / 총 예약 (임시 포함) / 최대 정원
            return format_html(
                '<strong>{}</strong> / {} / {}<br>'
                '<small style="color: #7f8c8d;">확정 / 예약 / 정원</small>',
                confirmed, reserved, max_participants
            )
        else:
            confirmed = obj.current_participants
            reserved = obj.reserved_participants
            return format_html(
                '<strong>{}</strong> / {}<br>'
                '<small style="color: #7f8c8d;">확정 / 예약 (무제한)</small>',
                confirmed, reserved
            )
    participants_display.short_description = '참가자 현황'
    
    def remaining_spots_display(self, obj):
        """남은 자리 표시"""
        if obj.max_participants:
            remaining = obj.remaining_spots
            if remaining is not None:
                if remaining == 0:
                    return format_html('<span style="color: #e74c3c; font-weight: bold;">🔴 마감</span>')
                elif remaining <= 5:
                    return format_html('<span style="color: #f39c12; font-weight: bold;">🟡 {} 자리</span>', str(remaining))
                else:
                    return format_html('<span style="color: #27ae60; font-weight: bold;">🟢 {} 자리</span>', str(remaining))
        return format_html('<span style="color: #3498db;">♾️ 무제한</span>')
    remaining_spots_display.short_description = '남은 자리'
    
    def reservation_stats_display(self, obj):
        """예약 통계 표시"""
        from django.utils import timezone
        
        # 대기 중인 임시 예약 수
        pending_reservations = obj.orders.filter(
            status='pending',
            is_temporary_reserved=True,
            reservation_expires_at__gt=timezone.now()
        ).count()
        
        # 만료된 예약 수
        expired_reservations = obj.orders.filter(
            status='pending',
            is_temporary_reserved=True,
            reservation_expires_at__lt=timezone.now()
        ).count()
        
        # 취소된 주문 수
        cancelled_orders = obj.orders.filter(status='cancelled').count()
        
        if pending_reservations > 0 or expired_reservations > 0 or cancelled_orders > 0:
            return format_html(
                '<div style="font-size: 11px;">'
                '⏳ 대기: <strong style="color: #f39c12;">{}</strong><br>'
                '⏱ 만료: <strong style="color: #e74c3c;">{}</strong><br>'
                '❌ 취소: <strong style="color: #95a5a6;">{}</strong>'
                '</div>',
                pending_reservations, expired_reservations, cancelled_orders
            )
        return format_html('<span style="color: #27ae60;">✨ 깔끔</span>')
    reservation_stats_display.short_description = '예약 통계'
    
    def pending_reservations_count(self, obj):
        """대기 중인 임시 예약 수"""
        from django.utils import timezone
        
        return obj.orders.filter(
            status='pending',
            is_temporary_reserved=True,
            reservation_expires_at__gt=timezone.now()
        ).count()
    pending_reservations_count.short_description = '대기 중인 임시 예약'
    
    # 커스텀 액션들
    def cleanup_expired_reservations(self, request, queryset):
        """선택된 밋업의 만료된 예약들을 정리"""
        from django.utils import timezone
        from .services import cancel_expired_reservations
        
        total_cancelled = 0
        for meetup in queryset:
            # 해당 밋업의 만료된 예약만 취소
            cancelled_count = meetup.orders.filter(
                status='pending',
                is_temporary_reserved=True,
                reservation_expires_at__lt=timezone.now()
            ).count()
            
            if cancelled_count > 0:
                meetup.orders.filter(
                    status='pending',
                    is_temporary_reserved=True,
                    reservation_expires_at__lt=timezone.now()
                ).update(
                    status='cancelled',
                    auto_cancelled_reason='관리자 정리 - 예약 시간 만료',
                    is_temporary_reserved=False
                )
                total_cancelled += cancelled_count
        
        self.message_user(request, f'{total_cancelled}개의 만료된 예약이 정리되었습니다.')
    cleanup_expired_reservations.short_description = '선택된 밋업의 만료된 예약 정리'
    
    def export_participants(self, request, queryset):
        """참가자 명단 내보내기 (CSV)"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="meetup_participants.csv"'
        response.write('\ufeff'.encode('utf8'))  # BOM for Excel
        
        writer = csv.writer(response)
        writer.writerow([
            '밋업명', '스토어', '참가자명', '이메일', '연락처', '주문번호', 
            '상태', '참가비', '참가일시', '참석여부'
        ])
        
        for meetup in queryset:
            for order in meetup.orders.filter(status__in=['confirmed', 'completed']).order_by('-created_at'):
                writer.writerow([
                    meetup.name,
                    meetup.store.store_name,
                    order.participant_name,
                    order.participant_email,
                    order.participant_phone or '-',
                    order.order_number,
                    '참가확정' if order.status == 'confirmed' else '밋업완료',
                    f'{order.total_price:,} sats',
                    order.created_at.strftime('%Y-%m-%d %H:%M'),
                    '참석' if order.attended else '미참석'
                ])
        
        return response
    export_participants.short_description = '선택된 밋업의 참가자 명단 CSV 내보내기'
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('store', 'name', 'description')
        }),
        ('일시 및 장소', {
            'fields': ('date_time', 'location_postal_code', 'location_address', 'location_detail_address', 'location_tbd', 'special_notes'),
            'description': '밋업 일시와 장소 정보를 설정합니다.'
        }),
        ('주최자 정보', {
            'fields': ('organizer_contact', 'organizer_email', 'organizer_chat_channel'),
            'description': '참가자들이 연락할 수 있는 주최자 정보를 입력합니다.'
        }),
        ('가격 정보', {
            'fields': ('is_free', 'price', 'is_discounted', 'discounted_price', 'early_bird_end_date', 'early_bird_end_time', 'current_price', 'public_discount_rate'),
            'description': '무료 밋업 체크 시 가격 및 할인 설정이 비활성화됩니다.'
        }),
        ('참가자 관리', {
            'fields': ('max_participants', 'current_participants', 'reserved_participants', 'actual_remaining_spots', 'pending_reservations_count', 'completion_message'),
            'description': '정원 관리와 참가 완료 후 안내 메시지를 설정합니다.'
        }),
        ('상태 정보', {
            'fields': ('is_active', 'is_temporarily_closed', 'is_early_bird_active'),
            'description': '밋업의 활성화 상태를 관리합니다.'
        }),
        ('메타 정보', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': '시스템 정보입니다.'
        }),
    )

@admin.register(MeetupImage)
class MeetupImageAdmin(admin.ModelAdmin):
    """밋업 이미지 어드민"""
    list_display = ('meetup', 'original_name', 'view_image_button', 'file_size_display', 'width', 'height', 'order', 'uploaded_at')
    list_filter = ('uploaded_at', 'meetup__store')
    search_fields = ('meetup__name', 'meetup__store__store_name', 'original_name')
    readonly_fields = ('image_preview', 'file_url', 'file_path', 'file_size', 'width', 'height', 'uploaded_at', 'uploaded_by')
    ordering = ('meetup', 'order', 'uploaded_at')
    list_per_page = 10
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('meetup', 'original_name', 'order')
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
    
    def image_preview(self, obj):
        """이미지 미리보기"""
        if obj and obj.file_url:
            return format_html(
                '<img src="{}" alt="{}" style="max-width: 200px; max-height: 200px; object-fit: contain; cursor: pointer;" onclick="showImageModal(\'{}\', \'{}\')" title="클릭하여 크게 보기">',
                obj.file_url,
                obj.original_name,
                obj.file_url,
                obj.original_name
            )
        return "이미지 없음"
    image_preview.short_description = '이미지 미리보기'

@admin.register(MeetupOption)
class MeetupOptionAdmin(admin.ModelAdmin):
    list_display = ['meetup', 'name', 'is_required', 'choices_count', 'order', 'created_at']
    list_filter = ['meetup__store', 'is_required', 'created_at']
    search_fields = ['meetup__name', 'name']
    readonly_fields = ['created_at']
    ordering = ['meetup', 'order']
    inlines = [MeetupChoiceInline]
    
    def choices_count(self, obj):
        """선택지 수"""
        return obj.choices.count()
    choices_count.short_description = '선택지 수'

@admin.register(MeetupChoice)
class MeetupChoiceAdmin(admin.ModelAdmin):
    list_display = ['option', 'name', 'additional_price_display', 'order', 'created_at']
    list_filter = ['option__meetup__store', 'created_at']
    search_fields = ['option__meetup__name', 'option__name', 'name']
    readonly_fields = ['created_at']
    ordering = ['option', 'order']
    
    def additional_price_display(self, obj):
        """추가요금 표시"""
        if obj.additional_price > 0:
            return f"+{obj.additional_price:,} sats"
        elif obj.additional_price < 0:
            return f"{obj.additional_price:,} sats"
        return "무료"
    additional_price_display.short_description = '추가요금'

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
        'reservation_status_display', 'attended_display', 'total_price_display', 
        'is_early_bird', 'created_at'
    ]
    list_filter = [
        'status', 'is_temporary_reserved', 'attended', 'meetup__store', 
        'is_early_bird', 'created_at', 'paid_at', 'attended_at',
        'reservation_expires_at'
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
    actions = ['mark_as_confirmed', 'cancel_expired_reservations', 'extend_reservations']
    
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
    
    def reservation_status_display(self, obj):
        """예약 상태 표시 (임시 예약 및 만료 시간 포함)"""
        from django.utils import timezone
        
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
            now = timezone.now()
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
        
        from django.utils import timezone
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
    def mark_as_confirmed(self, request, queryset):
        """선택된 주문들을 확정 상태로 변경"""
        from .services import confirm_reservation
        
        confirmed_count = 0
        for order in queryset.filter(status='pending', is_temporary_reserved=True):
            if confirm_reservation(order):
                confirmed_count += 1
        
        self.message_user(request, f'{confirmed_count}개의 주문이 확정되었습니다.')
    mark_as_confirmed.short_description = '선택된 임시예약을 확정으로 변경'
    
    def cancel_expired_reservations(self, request, queryset):
        """만료된 예약들을 취소"""
        from .services import cancel_expired_reservations
        
        cancelled_count = cancel_expired_reservations()
        self.message_user(request, f'{cancelled_count}개의 만료된 예약이 취소되었습니다.')
    cancel_expired_reservations.short_description = '만료된 예약 자동 취소'
    
    def extend_reservations(self, request, queryset):
        """선택된 예약들의 시간을 연장"""
        from .services import extend_reservation
        
        extended_count = 0
        for order in queryset.filter(status='pending', is_temporary_reserved=True):
            if extend_reservation(order):
                extended_count += 1
        
        self.message_user(request, f'{extended_count}개의 예약 시간이 연장되었습니다.')
    extend_reservations.short_description = '선택된 예약 시간 연장 (180초)'
    
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

# 임시예약 전용 어드민
@admin.register(TemporaryReservation)
class TemporaryReservationAdmin(admin.ModelAdmin):
    """임시예약 전용 관리 어드민"""
    
    def get_queryset(self, request):
        """임시예약만 표시"""
        return super().get_queryset(request).filter(
            is_temporary_reserved=True,
            status='pending'
        )
    
    list_display = [
        'order_number', 'meetup', 'participant_name', 'reservation_status_display', 
        'reservation_time_left', 'created_at', 'age_display'
    ]
    
    list_filter = [
        'meetup__store', 'created_at', 'reservation_expires_at',
        ('reservation_expires_at', admin.DateFieldListFilter),
        ('created_at', admin.DateFieldListFilter),
    ]
    
    search_fields = [
        'order_number', 'participant_name', 'participant_email', 
        'meetup__name', 'meetup__store__store_name'
    ]
    
    readonly_fields = [
        'order_number', 'meetup', 'participant_name', 'participant_email', 
        'participant_phone', 'status', 'base_price', 'total_price', 
        'created_at', 'updated_at', 'reservation_expires_at', 'reservation_time_left',
        'age_display', 'is_expired'
    ]
    
    ordering = ['-created_at']
    
    # 액션 추가
    actions = [
        'delete_old_reservations', 
        'extend_selected_reservations', 
        'confirm_selected_reservations',
        'cancel_selected_reservations'
    ]
    
    def reservation_status_display(self, obj):
        """예약 상태 표시"""
        from django.utils import timezone
        
        if not obj.reservation_expires_at:
            return format_html('<span style="color: #f39c12; font-weight: bold;">⏳ 임시예약 (시간 없음)</span>')
        
        now = timezone.now()
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
                status = '⚠️ 곧 만료'
            elif minutes_left < 15:
                color = '#f39c12'  # 주황색 (주의)
                status = '⏳ 임시예약'
            else:
                color = '#27ae60'  # 초록색 (안전)
                status = '⏳ 임시예약'
                
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span><br>'
                '<small style="color: {};">{} ({}분 남음)</small>',
                color, status, color,
                obj.reservation_expires_at.strftime("%m/%d %H:%M"),
                minutes_left
            )
    reservation_status_display.short_description = '예약 상태'
    
    def reservation_time_left(self, obj):
        """예약 남은 시간"""
        if not obj.reservation_expires_at:
            return format_html('<span style="color: #95a5a6;">-</span>')
        
        from django.utils import timezone
        now = timezone.now()
        
        if now > obj.reservation_expires_at:
            return format_html('<span style="color: #e74c3c; font-weight: bold;">만료됨</span>')
        
        time_left = obj.reservation_expires_at - now
        hours = int(time_left.total_seconds() // 3600)
        minutes = int((time_left.total_seconds() % 3600) // 60)
        seconds = int(time_left.total_seconds() % 60)
        
        if hours > 0:
            time_str = f"{hours}시간 {minutes}분"
        elif minutes > 0:
            time_str = f"{minutes}분 {seconds}초"
        else:
            time_str = f"{seconds}초"
        
        if time_left.total_seconds() < 300:  # 5분 미만
            color = '#e74c3c'
        elif time_left.total_seconds() < 900:  # 15분 미만
            color = '#f39c12'
        else:
            color = '#27ae60'
            
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, time_str
        )
    reservation_time_left.short_description = '남은 시간'
    
    def age_display(self, obj):
        """생성된 지 얼마나 되었는지 표시"""
        from django.utils import timezone
        
        now = timezone.now()
        age = now - obj.created_at
        
        days = age.days
        hours = int(age.total_seconds() // 3600)
        minutes = int((age.total_seconds() % 3600) // 60)
        
        if days > 0:
            age_str = f"{days}일 전"
            color = '#e74c3c' if days >= 1 else '#f39c12'
        elif hours > 0:
            age_str = f"{hours}시간 전"
            color = '#f39c12' if hours >= 12 else '#3498db'
        else:
            age_str = f"{minutes}분 전"
            color = '#27ae60'
        
        return format_html(
            '<span style="color: {};">{}</span>',
            color, age_str
        )
    age_display.short_description = '생성된 지'
    
    def is_expired(self, obj):
        """만료 여부"""
        if not obj.reservation_expires_at:
            return False
        
        from django.utils import timezone
        return timezone.now() > obj.reservation_expires_at
    is_expired.short_description = '만료됨'
    is_expired.boolean = True
    
    # 커스텀 액션들
    def delete_old_reservations(self, request, queryset):
        """하루 이상 된 임시예약 일괄 삭제"""
        from django.utils import timezone
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        
        one_day_ago = timezone.now() - timedelta(days=1)
        
        # 전체 임시예약에서 하루 이상 된 것들 찾기 (queryset 무시하고 전체에서)
        old_reservations = self.get_queryset(request).filter(created_at__lt=one_day_ago)
        
        if not old_reservations.exists():
            self.message_user(request, '하루 이상 된 임시예약이 없습니다.', level=messages.WARNING)
            return HttpResponseRedirect(request.get_full_path())
        
        count = old_reservations.count()
        
        # 삭제 확인 페이지 표시
        if request.POST.get('confirm_delete'):
            # 실제 삭제 실행
            deleted_count = 0
            for order in old_reservations:
                order.delete()
                deleted_count += 1
            
            message = f'{deleted_count}개의 하루 이상 된 임시예약을 삭제했습니다.'
            self.message_user(request, message, level=messages.SUCCESS)
            return HttpResponseRedirect(reverse('admin:meetup_temporaryreservation_changelist'))
        
        # 삭제 확인 페이지 렌더링
        context = {
            'title': '하루 이상 된 임시예약 일괄 삭제',
            'orders': list(old_reservations.select_related('meetup', 'meetup__store')[:20]),  # 미리보기용 20개만
            'total_count': count,
            'action_url': request.get_full_path(),
            'action_name': 'delete_old_reservations',
        }
        
        return render(request, 'admin/meetup/confirm_delete_reservations.html', context)
    
    delete_old_reservations.short_description = '하루 이상 된 임시예약 일괄 삭제'
    
    def extend_selected_reservations(self, request, queryset):
        """선택된 예약들의 시간을 연장"""
        from .services import extend_reservation
        
        # 유효한 임시예약만 필터링
        valid_reservations = queryset.filter(
            is_temporary_reserved=True,
            status='pending'
        )
        
        extended_count = 0
        for order in valid_reservations:
            if extend_reservation(order):
                extended_count += 1
        
        if extended_count > 0:
            self.message_user(request, f'{extended_count}개의 예약 시간이 180초 연장되었습니다.', level=messages.SUCCESS)
        else:
            self.message_user(request, '연장할 수 있는 유효한 예약이 없습니다.', level=messages.WARNING)
    
    extend_selected_reservations.short_description = '선택된 예약 시간 연장 (180초)'
    
    def confirm_selected_reservations(self, request, queryset):
        """선택된 임시예약을 확정으로 변경"""
        from .services import confirm_reservation
        
        valid_reservations = queryset.filter(
            is_temporary_reserved=True,
            status='pending'
        )
        
        confirmed_count = 0
        for order in valid_reservations:
            if confirm_reservation(order):
                confirmed_count += 1
        
        if confirmed_count > 0:
            self.message_user(request, f'{confirmed_count}개의 임시예약이 확정되었습니다.', level=messages.SUCCESS)
        else:
            self.message_user(request, '확정할 수 있는 유효한 임시예약이 없습니다.', level=messages.WARNING)
    
    confirm_selected_reservations.short_description = '선택된 임시예약을 확정으로 변경'
    
    def cancel_selected_reservations(self, request, queryset):
        """선택된 임시예약을 취소"""
        from .services import release_reservation
        
        valid_reservations = queryset.filter(
            is_temporary_reserved=True,
            status='pending'
        )
        
        cancelled_count = 0
        for order in valid_reservations:
            if release_reservation(order, "관리자 수동 취소"):
                cancelled_count += 1
        
        if cancelled_count > 0:
            self.message_user(request, f'{cancelled_count}개의 임시예약이 취소되었습니다.', level=messages.SUCCESS)
        else:
            self.message_user(request, '취소할 수 있는 유효한 임시예약이 없습니다.', level=messages.WARNING)
    
    cancel_selected_reservations.short_description = '선택된 임시예약을 취소'
    
    fieldsets = (
        ('주문 정보', {
            'fields': ('order_number', 'meetup', 'status')
        }),
        ('참가자 정보', {
            'fields': ('participant_name', 'participant_email', 'participant_phone')
        }),
        ('임시 예약 정보', {
            'fields': ('reservation_expires_at', 'reservation_time_left', 'is_expired', 'age_display'),
            'description': '임시 예약의 상태와 시간 정보를 확인할 수 있습니다.'
        }),
        ('가격 정보', {
            'fields': ('base_price', 'total_price'),
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
    
    def has_change_permission(self, request, obj=None):
        """수정 권한 제한"""
        return False


