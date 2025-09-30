from django.contrib import admin, messages
from django.http import HttpResponse
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Sum, Count
from django.contrib.auth.models import User
from ..models import MeetupOrder
from .filters import HasPendingOrdersFilter, HasAttendedMeetupsFilter


def _format_local(dt, fmt='%Y-%m-%d %H:%M:%S', default=''):
    if not dt:
        return default
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return timezone.localtime(dt).strftime(fmt)


# 밋업 참가자만 보는 별도 어드민 클래스 추가
class MeetupParticipant(User):
    """밋업 참가 내역이 있는 사용자들만 보여주는 프록시 모델"""
    class Meta:
        proxy = True
        verbose_name = "밋업 참가자"
        verbose_name_plural = "밋업 참가자 목록"


# 밋업별 참가자 관리를 위한 새로운 모델
class MeetupParticipantEntry(MeetupOrder):
    """밋업별 참가자 항목을 위한 프록시 모델"""
    class Meta:
        proxy = True
        verbose_name = "밋업 참가자 항목"
        verbose_name_plural = "밋업 참가자 관리"


@admin.register(MeetupParticipantEntry)
class MeetupParticipantEntryAdmin(admin.ModelAdmin):
    """밋업별 참가자 관리 어드민 - 모든 상태의 주문 데이터 기반으로 참가자 목록 관리 (pending, confirmed, cancelled, completed 모두 포함)"""
    list_display = [
        'participant_name', 'participant_email', 'meetup_name_display', 
        'store_display', 'order_status_display', 'attended', 'attendance_status_display',
        'participant_phone_display', 'created_at_display', 'payment_status_display'
    ]
    list_filter = [
        'meetup__store', 'meetup', 'status', 'attended', 
        'is_early_bird', 'created_at', 'attended_at'
    ]
    search_fields = [
        'participant_name', 'participant_email', 'participant_phone',
        'meetup__name', 'order_number', 'user__username'
    ]
    list_editable = ['attended']  # 참석 여부를 목록에서 바로 수정 가능
    
    fieldsets = (
        ('밋업 정보', {
            'fields': ('meetup', 'order_number')
        }),
        ('참가자 정보', {
            'fields': ('participant_name', 'participant_email', 'participant_phone', 'user')
        }),
        ('주문 상태', {
            'fields': ('status', 'payment_hash', 'paid_at', 'created_at')
        }),
        ('참석 관리', {
            'fields': ('attended', 'attended_at'),
            'description': '밋업 당일 참석 여부를 관리할 수 있습니다.'
        }),
        ('가격 정보', {
            'fields': ('base_price', 'options_price', 'total_price'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = [
        'meetup', 'order_number', 'user', 'base_price', 'options_price', 
        'total_price', 'payment_hash', 'paid_at', 'created_at'
    ]
    
    ordering = ['-created_at']
    list_per_page = 10
    
    # 액션 추가
    actions = ['export_participant_entries_csv', 'mark_as_attended', 'mark_as_not_attended']
    
    def get_queryset(self, request):
        """모든 상태의 주문을 조회 (참가자 목록 - pending, confirmed, cancelled, completed 모두 포함)"""
        # 모든 상태의 주문을 포함하도록 필터링 제거
        return super().get_queryset(request).select_related(
            'meetup', 'meetup__store', 'user'
        )
    
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
            'pending': '#f39c12',     # 주황색 (결제 대기)
            'confirmed': '#27ae60',   # 초록색 (참가 확정)
            'completed': '#3498db',   # 파란색 (밋업 완료)
            'cancelled': '#e74c3c',   # 빨간색 (참가 취소)
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
    order_status_display.short_description = '주문 상태'
    order_status_display.admin_order_field = 'status'
    
    def attendance_status_display(self, obj):
        """참석 상태 표시"""
        if obj.attended:
            return format_html(
                '<span style="color: #27ae60; font-weight: bold; background: #d4edda; padding: 4px 8px; border-radius: 4px;">✓ 참석</span>'
            )
        else:
            return format_html(
                '<span style="color: #6c757d; background: #f8f9fa; padding: 4px 8px; border-radius: 4px;">미참석</span>'
            )
    attendance_status_display.short_description = '참석 상태'
    attendance_status_display.admin_order_field = 'attended'
    
    def participant_phone_display(self, obj):
        """참가자 연락처 표시"""
        return obj.participant_phone or '-'
    participant_phone_display.short_description = '연락처'
    
    def created_at_display(self, obj):
        """신청일시 표시"""
        return timezone.localtime(obj.created_at).strftime('%Y.%m.%d %H:%M')
    created_at_display.short_description = '신청일시'
    created_at_display.admin_order_field = 'created_at'
    
    def payment_status_display(self, obj):
        """결제 상태 표시"""
        if obj.total_price == 0:
            return format_html('<span style="color: #28a745;">무료</span>')
        elif obj.payment_hash:
            return format_html('<span style="color: #28a745;">✓ 결제완료</span>')
        else:
            return format_html('<span style="color: #ffc107;">미결제</span>')
    payment_status_display.short_description = '결제 상태'
    
    def save_model(self, request, obj, form, change):
        """참석 상태 변경시 attended_at 자동 설정"""
        if change and 'attended' in form.changed_data:
            if obj.attended:
                if not obj.attended_at:
                    obj.attended_at = timezone.now()
            else:
                obj.attended_at = None
        
        super().save_model(request, obj, form, change)
    
    def has_add_permission(self, request):
        """추가 권한 없음 (주문을 통해서만 생성)"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """삭제 권한 없음"""
        return False
    
    def export_participant_entries_csv(self, request, queryset):
        """선택된 참가자 항목들을 CSV로 다운로드"""
        import csv
        
        # CSV 응답 생성
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        generated_at = timezone.localtime(timezone.now())
        response['Content-Disposition'] = f'attachment; filename="meetup_participant_entries_{generated_at.strftime("%Y%m%d_%H%M")}.csv"'
        response.write('\ufeff'.encode('utf8'))  # BOM for Excel
        
        writer = csv.writer(response)
        
        # 헤더 작성
        headers = [
            '참가자명', '이메일', '연락처', '밋업명', '스토어명', 
            '주문번호', '주문상태', '참석여부', '참석체크일시',
            '기본참가비', '옵션금액', '총참가비', '결제상태', '결제해시',
            '신청일시', '확정일시', '결제일시', '조기등록여부',
            '사용자ID', '선택옵션'
        ]
        writer.writerow(headers)
        
        # 데이터 작성
        orders = queryset.select_related(
            'meetup', 'meetup__store', 'user'
        ).prefetch_related(
            'selected_options__option', 'selected_options__choice'
        )
        
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
            
            # 결제 상태
            if order.total_price == 0:
                payment_status = '무료'
            elif order.payment_hash:
                payment_status = '결제완료'
            else:
                payment_status = '미결제'
            
            row = [
                order.participant_name,
                order.participant_email,
                order.participant_phone or '',
                order.meetup.name,
                order.meetup.store.store_name,
                order.order_number,
                status_text,
                "참석" if order.attended else "미참석",
                _format_local(order.attended_at),
                f"{order.base_price:,}",
                f"{order.options_price:,}",
                f"{order.total_price:,}",
                payment_status,
                order.payment_hash or '',
                _format_local(order.created_at),
                _format_local(order.confirmed_at),
                _format_local(order.paid_at),
                "예" if order.is_early_bird else "아니오",
                order.user.username if order.user else '비회원',
                options_text
            ]
            writer.writerow(row)
        
        # 메시지 표시
        self.message_user(request, f'{queryset.count()}개의 참가자 항목이 CSV로 다운로드되었습니다.')
        return response
    
    export_participant_entries_csv.short_description = '선택된 참가자 항목을 CSV로 다운로드'
    
    def mark_as_attended(self, request, queryset):
        """선택된 참가자들을 참석으로 표시"""
        updated_count = 0
        for order in queryset:
            if not order.attended:
                order.attended = True
                order.attended_at = timezone.now()
                order.save()
                updated_count += 1
        
        self.message_user(request, f'{updated_count}명의 참가자가 참석으로 표시되었습니다.')
    
    mark_as_attended.short_description = '선택된 참가자를 참석으로 표시'
    
    def mark_as_not_attended(self, request, queryset):
        """선택된 참가자들을 미참석으로 표시"""
        updated_count = 0
        for order in queryset:
            if order.attended:
                order.attended = False
                order.attended_at = None
                order.save()
                updated_count += 1
        
        self.message_user(request, f'{updated_count}명의 참가자가 미참석으로 표시되었습니다.')
    
    mark_as_not_attended.short_description = '선택된 참가자를 미참석으로 표시'


@admin.register(MeetupParticipant)
class MeetupParticipantAdmin(admin.ModelAdmin):
    """밋업 신청 내역이 있는 사용자들만 관리하는 어드민"""
    list_display = [
        'username', 'email', 'first_name', 'last_name', 
        'meetup_count', 'has_pending_orders', 'has_attended_meetups', 
        'latest_meetup', 'total_meetup_spent', 'date_joined', 'last_login'
    ]
    list_filter = ['date_joined', 'last_login', 'is_active', HasPendingOrdersFilter, HasAttendedMeetupsFilter]
    search_fields = ['username', 'email', 'first_name', 'last_name']
    readonly_fields = [
        'username', 'email', 'first_name', 'last_name', 
        'date_joined', 'last_login', 'meetup_orders_detail'
    ]
    list_per_page = 10
    
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
        """밋업 신청 내역이 있는 사용자만 조회 (모든 상태 포함)"""
        # 모든 상태의 밋업 주문이 있는 사용자들 조회 (인덱스 최적화된 쿼리)
        user_ids_with_meetups = MeetupOrder.objects.values_list('user_id', flat=True).distinct()
        
        # prefetch_related를 사용하여 밋업 주문 정보를 미리 로드 (모든 상태 포함)
        return super().get_queryset(request).filter(
            id__in=user_ids_with_meetups
        ).prefetch_related(
            'meetup_orders__meetup__store'
        )
    
    def meetup_count(self, obj):
        """밋업 신청 횟수 (모든 상태 포함)"""
        count = obj.meetup_orders.count()
        return format_html(
            '<span style="color: #007cba; font-weight: bold;">{} 회</span>',
            count
        )
    meetup_count.short_description = '신청 횟수'
    
    def has_pending_orders(self, obj):
        """결제 대기 중인 주문이 있는지 여부"""
        pending_count = obj.meetup_orders.filter(status='pending').count()
        
        if pending_count > 0:
            return format_html(
                '<span style="color: #f39c12; font-weight: bold;">🟡 {}개</span>',
                pending_count
            )
        return format_html('<span style="color: #95a5a6;">없음</span>')
    has_pending_orders.short_description = '미결제 주문'
    
    def has_attended_meetups(self, obj):
        """실제 참석한 밋업이 있는지 여부"""
        attended_count = obj.meetup_orders.filter(
            status__in=['confirmed', 'completed'],
            attended=True
        ).count()
        
        if attended_count > 0:
            return format_html(
                '<span style="color: #27ae60; font-weight: bold;">✅ {}회</span>',
                attended_count
            )
        return format_html('<span style="color: #95a5a6;">없음</span>')
    has_attended_meetups.short_description = '실제 참석'
    
    def latest_meetup(self, obj):
        """최근 신청한 밋업"""
        latest_order = obj.meetup_orders.select_related('meetup', 'meetup__store').order_by('-created_at').first()
        
        if latest_order:
            # 상태에 따른 색상 설정
            status_colors = {
                'pending': '#f39c12',     # 주황색
                'confirmed': '#27ae60',   # 초록색
                'completed': '#3498db',   # 파란색
                'cancelled': '#e74c3c',   # 빨간색
            }
            status_labels = {
                'pending': '결제대기',
                'confirmed': '참가확정',
                'completed': '밋업완료',
                'cancelled': '참가취소',
            }
            status_color = status_colors.get(latest_order.status, '#95a5a6')
            status_label = status_labels.get(latest_order.status, latest_order.status)
            
            return format_html(
                '<div style="max-width: 200px;">'
                '<div style="font-weight: bold; color: #495057;">{}</div>'
                '<div style="font-size: 12px; color: #6c757d;">{}</div>'
                '<div style="font-size: 11px; color: {};">● {} ({})</div>'
                '</div>',
                latest_order.meetup.name[:25] + ('...' if len(latest_order.meetup.name) > 25 else ''),
                latest_order.meetup.store.store_name,
                status_color,
                status_label,
                timezone.localtime(latest_order.created_at).strftime('%Y.%m.%d')
            )
        return '-'
    latest_meetup.short_description = '최근 신청 밋업'
    
    def total_meetup_spent(self, obj):
        """총 밋업 참가비 지출 (확정/완료된 주문만)"""
        total = obj.meetup_orders.filter(
            status__in=['confirmed', 'completed']
        ).aggregate(total=Sum('total_price'))['total'] or 0
        
        if total > 0:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">{} sats</span>',
                f"{total:,}"
            )
        return format_html('<span style="color: #6c757d;">0 sats</span>')
    total_meetup_spent.short_description = '총 지출'
    
    def meetup_orders_detail(self, obj):
        """밋업 주문 상세 내역 (모든 상태 포함)"""
        orders = obj.meetup_orders.select_related('meetup', 'meetup__store').order_by('-created_at')
        
        if not orders:
            return '신청 내역이 없습니다.'
        
        html_parts = [
            '<table style="width: 100%; border-collapse: collapse; font-size: 12px;">',
            '<thead>',
            '<tr style="background-color: #f8f9fa; border-bottom: 2px solid #dee2e6;">',
            '<th style="padding: 8px; text-align: left; border: 1px solid #dee2e6;">밋업명</th>',
            '<th style="padding: 8px; text-align: left; border: 1px solid #dee2e6;">스토어</th>',
            '<th style="padding: 8px; text-align: left; border: 1px solid #dee2e6;">참가자명</th>',
            '<th style="padding: 8px; text-align: center; border: 1px solid #dee2e6;">상태</th>',
            '<th style="padding: 8px; text-align: right; border: 1px solid #dee2e6;">참가비</th>',
            '<th style="padding: 8px; text-align: center; border: 1px solid #dee2e6;">신청일시</th>',
            '</tr>',
            '</thead>',
            '<tbody>'
        ]
        
        # 상태별 색상 설정
        status_colors = {
            'pending': '#f39c12',     # 주황색
            'confirmed': '#27ae60',   # 초록색
            'completed': '#3498db',   # 파란색
            'cancelled': '#e74c3c',   # 빨간색
        }
        
        status_labels = {
            'pending': '결제대기',
            'confirmed': '참가확정',
            'completed': '밋업완료',
            'cancelled': '참가취소',
        }
        
        for order in orders:
            status_color = status_colors.get(order.status, '#95a5a6')
            status_label = status_labels.get(order.status, order.status)
            price_display = f'{order.total_price:,} sats' if order.total_price > 0 else '무료'
            
            html_parts.append(
                f'<tr style="border-bottom: 1px solid #dee2e6;">'
                f'<td style="padding: 8px; border: 1px solid #dee2e6; font-weight: bold; color: #495057;">{order.meetup.name}</td>'
                f'<td style="padding: 8px; border: 1px solid #dee2e6; color: #6c757d;">{order.meetup.store.store_name}</td>'
                f'<td style="padding: 8px; border: 1px solid #dee2e6; color: #6c757d;">{order.participant_name}</td>'
                f'<td style="padding: 8px; border: 1px solid #dee2e6; text-align: center;">'
                f'<span style="color: {status_color}; font-weight: bold;">● {status_label}</span></td>'
                f'<td style="padding: 8px; border: 1px solid #dee2e6; text-align: right; font-weight: bold; color: #28a745;">{price_display}</td>'
                f'<td style="padding: 8px; border: 1px solid #dee2e6; text-align: center; color: #868e96;">{timezone.localtime(order.created_at).strftime("%Y.%m.%d %H:%M")}</td>'
                f'</tr>'
            )
        
        html_parts.extend(['</tbody>', '</table>'])
        
        return format_html(''.join(html_parts))
    meetup_orders_detail.short_description = '신청 내역 상세'
    
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
        
        # CSV 응답 생성
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        generated_at = timezone.localtime(timezone.now())
        response['Content-Disposition'] = f'attachment; filename="meetup_participants_{generated_at.strftime("%Y%m%d_%H%M")}.csv"'
        response.write('\ufeff'.encode('utf8'))  # BOM for Excel
        
        writer = csv.writer(response)
        
        # 헤더 작성
        headers = [
            '사용자명', '이메일', '이름', '성', '가입일', '최종로그인',
            '미결제주문수', '실제참석횟수', '총참가횟수',
            '밋업명', '스토어명', '참가자명', '참가자이메일', '참가자연락처',
            '주문번호', '상태', '기본참가비', '옵션금액', '총참가비', 
            '원가격', '할인율', '조기등록여부', '결제해시', '결제일시',
            '참가신청일시', '참가확정일시', '참석여부', '참석체크일시',
            '임시예약여부', '예약만료시간', '자동취소사유', '선택옵션'
        ]
        writer.writerow(headers)
        
        # 데이터 작성
        for participant in queryset:
            # 사용자별 통계 정보 계산
            pending_orders_count = participant.meetup_orders.filter(
                status='pending'
            ).count()
            
            attended_count = participant.meetup_orders.filter(
                status__in=['confirmed', 'completed'],
                attended=True
            ).count()
            
            total_confirmed_count = participant.meetup_orders.filter(
                status__in=['confirmed', 'completed']
            ).count()
            
            # 각 참가자의 모든 밋업 주문 조회 (모든 상태 포함)
            orders = participant.meetup_orders.select_related(
                'meetup', 'meetup__store'
            ).prefetch_related(
                'selected_options__option', 'selected_options__choice'
            ).order_by('-created_at')
            
            if not orders.exists():
                # 신청 내역이 없는 경우에도 사용자 정보는 포함
                row = [
                    participant.username,
                    participant.email,
                    participant.first_name or '',
                    participant.last_name or '',
                    _format_local(participant.date_joined),
                    _format_local(participant.last_login),
                    pending_orders_count,
                    attended_count,
                    total_confirmed_count,
                    '신청 내역 없음', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', ''
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
                        _format_local(participant.date_joined),
                        _format_local(participant.last_login),
                        pending_orders_count,
                        attended_count,
                        total_confirmed_count,
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
                        _format_local(order.paid_at),
                        _format_local(order.created_at),
                        _format_local(order.confirmed_at),
                        "참석" if order.attended else "미참석",
                        _format_local(order.attended_at),
                        options_text
                    ]
                    writer.writerow(row)
        
        # 메시지 표시
        total_participants = queryset.count()
        total_orders = MeetupOrder.objects.filter(
            user__in=queryset
        ).count()
        
        self.message_user(
            request, 
            f'{total_participants}명의 참가자와 {total_orders}개의 신청 내역이 CSV로 다운로드되었습니다.',
            level=messages.SUCCESS
        )
        return response
    
    export_participants_csv.short_description = '선택된 참가자들의 밋업 신청 내역을 CSV로 다운로드' 
