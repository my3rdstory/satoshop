from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.shortcuts import render, get_object_or_404
from django.db import models
from django.db.models import Count, Q
from datetime import timedelta
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
    actions = ['cleanup_expired_reservations', 'export_participants', 'view_all_participants']
    
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
        """참가자 목록 보기 버튼"""
        participants_count = obj.orders.filter(status__in=['confirmed', 'completed']).count()
        if participants_count > 0:
            url = reverse('admin:meetup_participants', args=[obj.pk])
            return format_html(
                '<a href="{}" class="button" style="background-color: #007cba; color: white; text-decoration: none; padding: 5px 10px; border-radius: 3px;">'
                '<i class="fas fa-users"></i> 참가자 ({})명</a>',
                url, participants_count
            )
        else:
            return format_html('<span style="color: #999;">참가자 없음</span>')
    view_participants_button.short_description = '참가자 관리'
    view_participants_button.allow_tags = True
    
    def get_urls(self):
        """커스텀 URL 추가"""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:meetup_id>/participants/',
                self.admin_site.admin_view(self.meetup_participants_view),
                name='meetup_participants',
            ),
            path(
                '<int:meetup_id>/participants/csv/',
                self.admin_site.admin_view(self.export_meetup_participants_csv),
                name='export_meetup_participants_csv',
            ),
        ]
        return custom_urls + urls
    
    def meetup_participants_view(self, request, meetup_id):
        """밋업 참가자 목록 뷰"""
        meetup = get_object_or_404(Meetup, pk=meetup_id)
        
        # 참가자 목록 (확정된 주문만)
        participants = MeetupOrder.objects.filter(
            meetup=meetup,
            status__in=['confirmed', 'completed']
        ).select_related('user').prefetch_related('selected_options__option', 'selected_options__choice').order_by('-created_at')
        
        # 통계 계산
        total_participants = participants.count()
        total_revenue = sum(order.total_price for order in participants)
        attended_count = participants.filter(attended=True).count()
        attendance_rate = (attended_count / total_participants * 100) if total_participants > 0 else 0
        
        # 참석 체크 액션 처리
        if request.method == 'POST' and 'action' in request.POST:
            if request.POST['action'] == 'toggle_attendance':
                order_id = request.POST.get('order_id')
                try:
                    order = MeetupOrder.objects.get(id=order_id, meetup=meetup)
                    order.attended = not order.attended
                    if order.attended:
                        order.attended_at = timezone.now()
                    else:
                        order.attended_at = None
                    order.save()
                    messages.success(request, f'{order.participant_name}님의 참석 상태가 변경되었습니다.')
                except MeetupOrder.DoesNotExist:
                    messages.error(request, '해당 주문을 찾을 수 없습니다.')
                
                # 페이지 새로고침을 위해 리다이렉트
                return HttpResponseRedirect(request.path)
        
        context = {
            'title': f'{meetup.name} - 참가자 목록',
            'meetup': meetup,
            'participants': participants,
            'total_participants': total_participants,
            'total_revenue': total_revenue,
            'attended_count': attended_count,
            'attendance_rate': attendance_rate,
            'opts': self.model._meta,
            'has_change_permission': self.has_change_permission(request),
            'has_view_permission': self.has_view_permission(request),
            'original': meetup,
        }
        
        return render(request, 'admin/meetup/meetup_participants.html', context)
    
    def export_meetup_participants_csv(self, request, meetup_id):
        """특정 밋업의 참가자 정보 CSV 내보내기"""
        import csv
        from django.http import HttpResponse
        from django.utils import timezone
        
        meetup = get_object_or_404(Meetup, pk=meetup_id)
        
        # 참가자 목록 (확정된 주문만)
        participants = MeetupOrder.objects.filter(
            meetup=meetup,
            status__in=['confirmed', 'completed']
        ).select_related('user').prefetch_related('selected_options__option', 'selected_options__choice').order_by('-created_at')
        
        # CSV 응답 생성
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{meetup.name}_participants_{timezone.now().strftime("%Y%m%d_%H%M")}.csv"'
        response.write('\ufeff'.encode('utf8'))  # BOM for Excel
        
        writer = csv.writer(response)
        
        # 헤더 작성
        headers = [
            '밋업명', '스토어명', '참가자명', '이메일', '연락처', '주문번호',
            '상태', '기본참가비', '옵션금액', '총참가비', '원가격', '할인율', '조기등록여부',
            '결제해시', '결제일시', '참가신청일시', '참석여부', '참석체크일시',
            '선택옵션'
        ]
        writer.writerow(headers)
        
        # 데이터 작성
        for participant in participants:
            # 선택 옵션 정보 수집
            selected_options = []
            for selected_option in participant.selected_options.all():
                option_text = f"{selected_option.option.name}: {selected_option.choice.name}"
                if selected_option.additional_price > 0:
                    option_text += f" (+{selected_option.additional_price:,} sats)"
                selected_options.append(option_text)
            
            options_text = " | ".join(selected_options) if selected_options else "없음"
            
            # 상태 텍스트 변환
            status_text = {
                'confirmed': '참가확정',
                'completed': '밋업완료',
                'pending': '결제대기',
                'cancelled': '참가취소'
            }.get(participant.status, participant.status)
            
            row = [
                meetup.name,
                meetup.store.store_name,
                participant.participant_name,
                participant.participant_email,
                participant.participant_phone or '',
                participant.order_number,
                status_text,
                f"{participant.base_price:,}",
                f"{participant.options_price:,}",
                f"{participant.total_price:,}",
                f"{participant.original_price:,}" if participant.original_price else '',
                f"{participant.discount_rate}%" if participant.discount_rate else '',
                "예" if participant.is_early_bird else "아니오",
                participant.payment_hash or '',
                participant.paid_at.strftime('%Y-%m-%d %H:%M:%S') if participant.paid_at else '',
                participant.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                "참석" if participant.attended else "미참석",
                participant.attended_at.strftime('%Y-%m-%d %H:%M:%S') if participant.attended_at else '',
                options_text
            ]
            writer.writerow(row)
        
        return response
    
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
    
    def view_all_participants(self, request, queryset):
        """선택된 밋업들의 모든 참가자를 하나의 페이지에서 보기"""
        if queryset.count() == 1:
            # 밋업이 하나만 선택된 경우 해당 밋업의 참가자 페이지로 리다이렉트
            meetup = queryset.first()
            return HttpResponseRedirect(reverse('admin:meetup_participants', args=[meetup.pk]))
        elif queryset.count() > 1:
            # 여러 밋업이 선택된 경우 통합 뷰로 이동 (필요시 구현)
            self.message_user(request, '한 번에 하나의 밋업만 선택해주세요.')
        else:
            self.message_user(request, '밋업을 선택해주세요.')
    view_all_participants.short_description = '선택된 밋업의 참가자 목록 보기'
    
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





