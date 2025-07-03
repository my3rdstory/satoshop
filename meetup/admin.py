from django.contrib import admin, messages
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.shortcuts import render, get_object_or_404
from django.db import models
from django.db.models import Count, Q, Sum
from datetime import timedelta
from django.contrib.auth.models import User
from .models import Meetup, MeetupImage, MeetupOption, MeetupChoice, MeetupOrder, MeetupOrderOption, Store


class HasParticipantsFilter(admin.SimpleListFilter):
    """참가자 유무 필터"""
    title = '참가자 유무'
    parameter_name = 'has_participants'

    def lookups(self, request, model_admin):
        return (
            ('yes', '참가자 있음'),
            ('no', '참가자 없음'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(orders__status__in=['confirmed', 'completed']).distinct()
        if self.value() == 'no':
            return queryset.exclude(orders__status__in=['confirmed', 'completed']).distinct()


class PaymentHashFilter(admin.SimpleListFilter):
    """결제해시 유무 필터"""
    title = '결제해시 유무'
    parameter_name = 'payment_hash_exists'

    def lookups(self, request, model_admin):
        return (
            ('yes', '결제해시 있음'),
            ('no', '결제해시 없음'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.exclude(payment_hash__isnull=True).exclude(payment_hash='')
        if self.value() == 'no':
            return queryset.filter(Q(payment_hash__isnull=True) | Q(payment_hash=''))


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
        'participants_display', 'remaining_spots_display', 'cancelled_orders_count', 
        'view_participants_button', 'created_at'
    ]
    list_filter = ['store', 'is_free', 'is_active', 'is_discounted', 'is_temporarily_closed', HasParticipantsFilter, 'created_at']
    search_fields = ['name', 'description', 'store__store_name']
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'current_price', 'is_early_bird_active', 
        'public_discount_rate', 'current_participants'
    ]
    inlines = [MeetupImageInline, MeetupOptionInline]
    
    # 액션 추가
    actions = ['cleanup_expired_reservations', 'export_participants', 'view_all_participants', 'export_participants_csv']
    
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
            max_participants = obj.max_participants
            
            # 확정된 참가자 / 최대 정원
            return format_html(
                '<strong>{}</strong> / {}<br>'
                '<small style="color: #7f8c8d;">확정 / 정원</small>',
                confirmed, max_participants
            )
        else:
            confirmed = obj.current_participants
            return format_html(
                '<strong>{}</strong><br>'
                '<small style="color: #7f8c8d;">확정 (무제한)</small>',
                confirmed
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
    
    def cancelled_orders_count(self, obj):
        """취소된 주문 수"""
        return obj.orders.filter(status='cancelled').count()
    cancelled_orders_count.short_description = '취소된 주문'
    
    def view_participants_button(self, obj):
        """참가자 목록 보기 버튼 - 어드민 내에서 밋업 주문 목록으로 이동"""
        participants_count = obj.orders.filter(status__in=['confirmed', 'completed']).count()
        if participants_count > 0:
            # 장고 어드민의 MeetupOrder 목록으로 이동하면서 현재 밋업 필터 적용
            from django.urls import reverse
            admin_url = reverse('admin:meetup_meetuporder_changelist')
            # 쿼리 파라미터로 밋업 필터 추가
            filter_url = f"{admin_url}?meetup__id__exact={obj.pk}"
            
            return format_html(
                '<a href="{}" class="button" style="background-color: #007cba; color: white; text-decoration: none; padding: 5px 10px; border-radius: 3px;" target="_blank">'
                '<i class="fas fa-users"></i> 참가자 ({})명</a>',
                filter_url, participants_count
            )
        else:
            return format_html('<span style="color: #999;">참가자 없음</span>')
    view_participants_button.short_description = '참가자 관리'
    view_participants_button.allow_tags = True
    


    
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
            'fields': ('max_participants', 'current_participants', 'completion_message'),
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
    
    def export_participants_csv(self, request, queryset):
        """선택된 밋업들의 참가자 목록을 CSV로 다운로드"""
        import csv
        from django.http import HttpResponse
        from django.utils import timezone
        
        # CSV 응답 생성
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="meetup_participants_{timezone.now().strftime("%Y%m%d_%H%M")}.csv"'
        response.write('\ufeff'.encode('utf8'))  # BOM for Excel
        
        writer = csv.writer(response)
        
        # 헤더 작성
        headers = [
            '밋업명', '스토어명', '밋업일시', '사용자명', '이메일', '가입일',
            '참가자명', '참가자이메일', '참가자연락처', '주문번호', '상태',
            '기본참가비', '옵션금액', '총참가비', '원가격', '할인율', '조기등록여부',
            '결제해시', '결제일시', '참가신청일시', '참가확정일시',
            '참석여부', '참석체크일시', '선택옵션'
        ]
        writer.writerow(headers)
        
        # 선택된 밋업들의 모든 주문 조회
        orders = MeetupOrder.objects.filter(
            meetup__in=queryset,
            status__in=['confirmed', 'completed']
        ).select_related(
            'meetup', 'meetup__store', 'user'
        ).prefetch_related(
            'selected_options__option', 'selected_options__choice'
        ).order_by('meetup__name', '-created_at')
        
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
                order.meetup.name,
                order.meetup.store.store_name,
                order.meetup.date_time.strftime('%Y-%m-%d %H:%M') if order.meetup.date_time else '미정',
                order.user.username if order.user else '비회원',
                order.user.email if order.user else '',
                order.user.date_joined.strftime('%Y-%m-%d') if order.user else '',
                order.participant_name,
                order.participant_email,
                order.participant_phone or '',
                order.order_number,
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
                options_text
            ]
            writer.writerow(row)
        
        # 메시지 표시
        total_orders = orders.count()
        total_meetups = queryset.count()
        
        self.message_user(
            request, 
            f'{total_meetups}개 밋업의 {total_orders}개 참가 내역이 CSV로 다운로드되었습니다.',
            level=messages.SUCCESS
        )
        return response
    
    export_participants_csv.short_description = '선택된 밋업의 참가자들을 CSV로 다운로드'

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
        from django.db.models import Case, When, Value, BooleanField
        
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
    def confirm_paid_reservations(self, request, queryset):
        """결제해시가 있는 결제대기 주문들을 참가확정으로 변경"""
        from django.utils import timezone
        
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

    def export_orders_csv(self, request, queryset):
        """선택된 밋업 주문들을 CSV로 다운로드"""
        import csv
        from django.http import HttpResponse
        from django.utils import timezone
        
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
        from django.http import HttpResponse
        from django.utils import timezone
        
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


# 밋업 참가자만 보는 별도 어드민 클래스 추가
class MeetupParticipant(User):
    """밋업 참가 내역이 있는 사용자들만 보여주는 프록시 모델"""
    class Meta:
        proxy = True
        verbose_name = "밋업 참가자"
        verbose_name_plural = "밋업 참가자 목록"


@admin.register(MeetupParticipant)
class MeetupParticipantAdmin(admin.ModelAdmin):
    """밋업 신청 내역이 있는 사용자들만 관리하는 어드민"""
    list_display = [
        'username', 'email', 'first_name', 'last_name', 
        'meetup_count', 'latest_meetup', 'total_meetup_spent', 
        'date_joined', 'last_login'
    ]
    list_filter = ['date_joined', 'last_login', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    readonly_fields = [
        'username', 'email', 'first_name', 'last_name', 
        'date_joined', 'last_login', 'meetup_orders_detail'
    ]
    list_per_page = 20
    
    # 액션 추가
    actions = ['export_participants_csv']
    
    fieldsets = (
        ('사용자 정보', {
            'fields': ('username', 'email', 'first_name', 'last_name')
        }),
        ('계정 정보', {
            'fields': ('date_joined', 'last_login', 'is_active')
        }),
        ('밋업 참가 내역', {
            'fields': ('meetup_orders_detail',),
        }),
    )
    
    def get_queryset(self, request):
        """밋업 참가 내역이 있는 사용자만 조회"""
        # 확정된 밋업 주문이 있는 사용자들만 조회 (인덱스 최적화된 쿼리)
        user_ids_with_meetups = MeetupOrder.objects.filter(
            status__in=['confirmed', 'completed']
        ).values_list('user_id', flat=True).distinct()
        
        # prefetch_related를 사용하여 밋업 주문 정보를 미리 로드
        return super().get_queryset(request).filter(
            id__in=user_ids_with_meetups
        ).select_related('lightning_profile').prefetch_related(
            models.Prefetch(
                'meetup_orders',
                queryset=MeetupOrder.objects.filter(
                    status__in=['confirmed', 'completed']
                ).select_related('meetup', 'meetup__store').order_by('-created_at')
            )
        )
    
    def meetup_count(self, obj):
        """밋업 참가 횟수"""
        # prefetch된 데이터 활용하여 추가 DB 쿼리 방지
        if hasattr(obj, '_prefetched_objects_cache') and 'meetup_orders' in obj._prefetched_objects_cache:
            count = len(obj._prefetched_objects_cache['meetup_orders'])
        else:
            count = MeetupOrder.objects.filter(
                user=obj,
                status__in=['confirmed', 'completed']
            ).count()
        return format_html(
            '<span style="color: #007cba; font-weight: bold;">{} 회</span>',
            count
        )
    meetup_count.short_description = '참가 횟수'
    
    def latest_meetup(self, obj):
        """최근 참가한 밋업"""
        # prefetch된 데이터 활용하여 추가 DB 쿼리 방지
        if hasattr(obj, '_prefetched_objects_cache') and 'meetup_orders' in obj._prefetched_objects_cache:
            orders = obj._prefetched_objects_cache['meetup_orders']
            latest_order = orders[0] if orders else None
        else:
            latest_order = MeetupOrder.objects.filter(
                user=obj,
                status__in=['confirmed', 'completed']
            ).select_related('meetup', 'meetup__store').order_by('-created_at').first()
        
        if latest_order:
            return format_html(
                '<div style="max-width: 200px;">'
                '<div style="font-weight: bold; color: #495057;">{}</div>'
                '<div style="font-size: 12px; color: #6c757d;">{}</div>'
                '<div style="font-size: 11px; color: #868e96;">{}</div>'
                '</div>',
                latest_order.meetup.name[:30] + ('...' if len(latest_order.meetup.name) > 30 else ''),
                latest_order.meetup.store.store_name,
                latest_order.created_at.strftime('%Y.%m.%d')
            )
        return '-'
    latest_meetup.short_description = '최근 참가 밋업'
    
    def total_meetup_spent(self, obj):
        """총 밋업 참가비 지출"""
        # prefetch된 데이터 활용하여 추가 DB 쿼리 방지
        if hasattr(obj, '_prefetched_objects_cache') and 'meetup_orders' in obj._prefetched_objects_cache:
            orders = obj._prefetched_objects_cache['meetup_orders']
            total = sum(order.total_price for order in orders)
        else:
            total = MeetupOrder.objects.filter(
                user=obj,
                status__in=['confirmed', 'completed']
            ).aggregate(total=Sum('total_price'))['total'] or 0
        
        if total > 0:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">{} sats</span>',
                f"{total:,}"
            )
        return format_html('<span style="color: #6c757d;">무료 참가</span>')
    total_meetup_spent.short_description = '총 지출'
    
    def meetup_orders_detail(self, obj):
        """밋업 주문 상세 내역"""
        # prefetch된 데이터 활용하여 추가 DB 쿼리 방지
        if hasattr(obj, '_prefetched_objects_cache') and 'meetup_orders' in obj._prefetched_objects_cache:
            orders = obj._prefetched_objects_cache['meetup_orders']
        else:
            orders = MeetupOrder.objects.filter(
                user=obj,
                status__in=['confirmed', 'completed']
            ).select_related('meetup', 'meetup__store').order_by('-created_at')
        
        if not orders:
            return '참가 내역이 없습니다.'
        
        html_parts = [
            '<table style="width: 100%; border-collapse: collapse; font-size: 12px;">',
            '<thead>',
            '<tr style="background-color: #f8f9fa; border-bottom: 2px solid #dee2e6;">',
            '<th style="padding: 8px; text-align: left; border: 1px solid #dee2e6;">밋업명</th>',
            '<th style="padding: 8px; text-align: left; border: 1px solid #dee2e6;">스토어</th>',
            '<th style="padding: 8px; text-align: left; border: 1px solid #dee2e6;">참가자명</th>',
            '<th style="padding: 8px; text-align: center; border: 1px solid #dee2e6;">상태</th>',
            '<th style="padding: 8px; text-align: right; border: 1px solid #dee2e6;">참가비</th>',
            '<th style="padding: 8px; text-align: center; border: 1px solid #dee2e6;">참가일시</th>',
            '</tr>',
            '</thead>',
            '<tbody>'
        ]
        
        for order in orders:
            status_color = '#28a745' if order.status == 'completed' else '#007cba'
            price_display = f'{order.total_price:,} sats' if order.total_price > 0 else '무료'
            
            html_parts.append(
                f'<tr style="border-bottom: 1px solid #dee2e6;">'
                f'<td style="padding: 8px; border: 1px solid #dee2e6; font-weight: bold; color: #495057;">{order.meetup.name}</td>'
                f'<td style="padding: 8px; border: 1px solid #dee2e6; color: #6c757d;">{order.meetup.store.store_name}</td>'
                f'<td style="padding: 8px; border: 1px solid #dee2e6; color: #6c757d;">{order.participant_name}</td>'
                f'<td style="padding: 8px; border: 1px solid #dee2e6; text-align: center;">'
                f'<span style="color: {status_color}; font-weight: bold;">● {order.get_status_display()}</span></td>'
                f'<td style="padding: 8px; border: 1px solid #dee2e6; text-align: right; font-weight: bold; color: #28a745;">{price_display}</td>'
                f'<td style="padding: 8px; border: 1px solid #dee2e6; text-align: center; color: #868e96;">{order.created_at.strftime("%Y.%m.%d %H:%M")}</td>'
                f'</tr>'
            )
        
        html_parts.extend(['</tbody>', '</table>'])
        
        return format_html(''.join(html_parts))
    meetup_orders_detail.short_description = '참가 내역 상세'
    
    def has_add_permission(self, request):
        """추가 권한 없음 (기존 사용자만 조회)"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """수정 권한 제한 (읽기 전용)"""
        return True
    
    def has_delete_permission(self, request, obj=None):
        """삭제 권한 없음"""
        return False
    
    def export_participants_csv(self, request, queryset):
        """밋업 참가자들의 상세 참가 내역을 CSV로 다운로드"""
        import csv
        from django.http import HttpResponse
        from django.utils import timezone
        
        # CSV 응답 생성
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="meetup_participants_{timezone.now().strftime("%Y%m%d_%H%M")}.csv"'
        response.write('\ufeff'.encode('utf8'))  # BOM for Excel
        
        writer = csv.writer(response)
        
        # 헤더 작성
        headers = [
            '사용자명', '이메일', '이름', '성', '가입일', '최종로그인',
            '밋업명', '스토어명', '참가자명', '참가자이메일', '참가자연락처',
            '주문번호', '상태', '기본참가비', '옵션금액', '총참가비', 
            '원가격', '할인율', '조기등록여부', '결제해시', '결제일시',
            '참가신청일시', '참가확정일시', '참석여부', '참석체크일시',
            '임시예약여부', '예약만료시간', '자동취소사유', '선택옵션'
        ]
        writer.writerow(headers)
        
        # 데이터 작성
        for participant in queryset.select_related('lightning_profile'):
            # 각 참가자의 모든 밋업 주문 조회
            orders = MeetupOrder.objects.filter(
                user=participant,
                status__in=['confirmed', 'completed']
            ).select_related(
                'meetup', 'meetup__store'
            ).prefetch_related(
                'selected_options__option', 'selected_options__choice'
            ).order_by('-created_at')
            
            if not orders.exists():
                # 참가 내역이 없는 경우에도 사용자 정보는 포함
                row = [
                    participant.username,
                    participant.email,
                    participant.first_name or '',
                    participant.last_name or '',
                    participant.date_joined.strftime('%Y-%m-%d %H:%M:%S'),
                    participant.last_login.strftime('%Y-%m-%d %H:%M:%S') if participant.last_login else '',
                    '참가 내역 없음', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', ''
                ]
                writer.writerow(row)
            else:
                # 각 밋업 참가 내역별로 행 생성
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
                        participant.username,
                        participant.email,
                        participant.first_name or '',
                        participant.last_name or '',
                        participant.date_joined.strftime('%Y-%m-%d %H:%M:%S'),
                        participant.last_login.strftime('%Y-%m-%d %H:%M:%S') if participant.last_login else '',
                        order.meetup.name,
                        order.meetup.store.store_name,
                        order.participant_name,
                        order.participant_email,
                        order.participant_phone or '',
                        order.order_number,
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
        total_participants = queryset.count()
        total_orders = MeetupOrder.objects.filter(
            user__in=queryset,
            status__in=['confirmed', 'completed']
        ).count()
        
        self.message_user(
            request, 
            f'{total_participants}명의 참가자와 {total_orders}개의 참가 내역이 CSV로 다운로드되었습니다.',
            level=messages.SUCCESS
        )
        return response
    
    export_participants_csv.short_description = '선택된 참가자들의 밋업 참가 내역을 CSV로 다운로드'








