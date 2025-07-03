from django.contrib import admin, messages
from django.http import HttpResponse
from django.urls import reverse
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Sum
from django.shortcuts import render, redirect
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
import csv
import io
import uuid
from ..models import Meetup, MeetupImage, MeetupOption, MeetupChoice, MeetupOrder
from .filters import HasParticipantsFilter


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
    # inlines = [MeetupImageInline, MeetupOptionInline]  # 밋업 이미지와 옵션 인라인 비활성화
    
    # 액션 추가
    actions = [
        'cleanup_expired_reservations', 'export_participants', 'view_all_participants', 'export_participants_csv',
        'download_participant_csv_sample', 'add_participants_csv'
    ]
    
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
            admin_url = reverse('admin:meetup_meetuporder_changelist')
            # 쿼리 파라미터로 밋업 필터 추가
            filter_url = f"{admin_url}?meetup__id__exact={obj.pk}"
            
            return format_html(
                '<a href="{}" class="button" style="background-color: #007cba; color: white; text-decoration: none; padding: 5px 10px; border-radius: 3px;">'
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

    def download_participant_csv_sample(self, request, queryset):
        """참가자 추가용 CSV 샘플 파일 다운로드"""
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="participant_sample.csv"'
        response.write('\ufeff'.encode('utf8'))  # BOM for Excel
        
        writer = csv.writer(response)
        
        # 헤더 작성
        headers = [
            '참가자명(필수)', '이메일(필수)', '연락처(선택)', '사용자명(선택)', '비고'
        ]
        writer.writerow(headers)
        
        # 샘플 데이터 작성
        sample_data = [
            ['홍길동', 'hong@example.com', '010-1234-5678', 'hong123', '수동 추가된 참가자'],
            ['김철수', 'kim@example.com', '010-9876-5432', '', '연락처만 있는 참가자'],
            ['이영희', 'lee@example.com', '', 'lee456', '최소 정보만 있는 참가자']
        ]
        
        for row in sample_data:
            writer.writerow(row)
        
        messages.success(request, 'CSV 샘플 파일이 다운로드되었습니다. 파일을 편집한 후 "CSV로 참가자 추가" 액션을 사용하세요.')
        return response
    download_participant_csv_sample.short_description = '📥 CSV 샘플 다운로드'

    def add_participants_csv(self, request, queryset):
        """CSV로 참가자 일괄 추가 - 새로운 페이지로 리다이렉트"""
        if queryset.count() != 1:
            messages.error(request, '참가자 추가는 한 번에 하나의 밋업에만 가능합니다.')
            return redirect(request.get_full_path())
        
        meetup = queryset.first()
        # 새로운 URL로 리다이렉트
        return redirect(f'/meetup/admin/csv-upload/{meetup.id}/')
    add_participants_csv.short_description = '📤 CSV로 참가자 추가' 