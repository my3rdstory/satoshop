from django.db import models
from django.utils import timezone
from django.core.validators import EmailValidator, RegexValidator
from django.contrib.auth.models import User
from stores.models import Store
import datetime
import uuid

class Meetup(models.Model):
    """밋업"""
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='meetups')
    name = models.CharField(max_length=200, verbose_name="밋업명")
    description = models.TextField(verbose_name="설명", blank=True)
    
    # 밋업 일시 및 장소 정보
    date_time = models.DateTimeField(verbose_name="밋업 일시", null=True, blank=True)
    location_postal_code = models.CharField(max_length=10, verbose_name="우편번호", blank=True)
    location_address = models.CharField(max_length=200, verbose_name="기본주소", blank=True)
    location_detail_address = models.CharField(max_length=200, verbose_name="상세주소", blank=True)
    location_tbd = models.BooleanField(default=False, verbose_name="장소 추후 공지")
    special_notes = models.TextField(verbose_name="특이사항", blank=True)
    
    # 주최자 정보
    organizer_contact = models.CharField(
        max_length=20, 
        verbose_name="주최자 연락처", 
        blank=True,
        validators=[RegexValidator(
            regex=r'^[\d\-\+\(\)\s]+$',
            message='올바른 연락처 형식이 아닙니다.',
        )]
    )
    organizer_email = models.EmailField(
        verbose_name="주최자 이메일", 
        blank=True,
        validators=[EmailValidator()]
    )
    organizer_chat_channel = models.URLField(verbose_name="주최자 소통채널", blank=True)
    
    # 가격 정보
    is_free = models.BooleanField(default=False, verbose_name="무료 밋업")
    price = models.PositiveIntegerField(verbose_name="참가비(satoshi)", default=0)
    is_discounted = models.BooleanField(default=False, verbose_name="할인 적용")
    discounted_price = models.PositiveIntegerField(verbose_name="할인가(satoshi)", null=True, blank=True)
    early_bird_end_date = models.DateField(verbose_name="조기등록 종료일", null=True, blank=True)
    early_bird_end_time = models.TimeField(verbose_name="조기등록 종료시간", null=True, blank=True)
    
    # 상태
    is_active = models.BooleanField(default=True, verbose_name="활성화")
    is_temporarily_closed = models.BooleanField(default=False, verbose_name="일시중단")
    max_participants = models.PositiveIntegerField(verbose_name="최대 참가자", null=True, blank=True)
    
    # 안내 메시지
    completion_message = models.TextField(verbose_name="참가완료 안내메시지", blank=True)
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "밋업"
        verbose_name_plural = "밋업"
        ordering = ['-created_at']
        # 성능 최적화를 위한 인덱스 추가
        indexes = [
            models.Index(fields=['store']),                    # 스토어별 밋업 조회용
            models.Index(fields=['is_active']),               # 활성 밋업 필터링용
            models.Index(fields=['date_time']),               # 날짜별 정렬용
            models.Index(fields=['store', 'is_active']),      # 스토어의 활성 밋업 조회용
            models.Index(fields=['store', 'date_time']),      # 스토어별 날짜 정렬용
            models.Index(fields=['deleted_at']),              # 소프트 삭제 조회용
            models.Index(fields=['store', 'deleted_at']),     # 스토어별 활성 밋업용
            models.Index(fields=['created_at']),              # 정렬용
            models.Index(fields=['updated_at']),              # 관리자 정렬용
            models.Index(fields=['is_temporarily_closed']),   # 일시중단 밋업 조회용
        ]
    
    def __str__(self):
        return f"{self.store.store_name} - {self.name}"
    
    def clean(self):
        """모델 검증"""
        from django.core.exceptions import ValidationError
        
        # 연락처와 이메일 중 하나는 필수
        if not self.organizer_contact and not self.organizer_email:
            raise ValidationError("주최자 연락처 또는 이메일 중 하나는 필수입니다.")
    
    @property
    def location_full_address(self):
        """전체 주소 반환"""
        address_parts = []
        if self.location_postal_code:
            address_parts.append(f"({self.location_postal_code})")
        if self.location_address:
            address_parts.append(self.location_address)
        if self.location_detail_address:
            address_parts.append(self.location_detail_address)
        return " ".join(address_parts)
    
    @property
    def is_deleted(self):
        return self.deleted_at is not None
    
    @property
    def current_participants(self):
        """현재 참가자 수 (확정된 주문 기준)"""
        return self.orders.filter(status__in=['confirmed', 'completed']).count()
    
    @property
    def is_full(self):
        if not self.max_participants:
            return False
        return self.current_participants >= self.max_participants
    
    @property
    def remaining_spots(self):
        """남은 자리 수"""
        if not self.max_participants:
            return None
        return max(0, self.max_participants - self.current_participants)
    
    @property
    def current_price(self):
        """현재 적용되는 가격"""
        # 무료 밋업이면 항상 0
        if self.is_free:
            return 0
        # 할인 적용 중이면 할인가
        if self.is_discounted and self.is_early_bird_active:
            return self.discounted_price or self.price
        return self.price
    
    @property
    def early_bird_end_datetime(self):
        """조기등록 종료 날짜시간"""
        if not self.early_bird_end_date:
            return None
            
        end_datetime = timezone.datetime.combine(
            self.early_bird_end_date,
            self.early_bird_end_time or timezone.time(23, 59)
        )
        return timezone.make_aware(end_datetime)
    
    @property
    def is_early_bird_active(self):
        """조기등록 할인이 활성화되어 있는지"""
        if not self.early_bird_end_date:
            return False
            
        now = timezone.now()
        end_datetime = self.early_bird_end_datetime
        
        return now <= end_datetime if end_datetime else False
    
    @property
    def public_discount_rate(self):
        """공개용 할인율"""
        if not self.is_discounted or not self.discounted_price:
            return 0
        return int((1 - self.discounted_price / self.price) * 100)
    
    @property
    def is_expired(self):
        """밋업 일정이 지났는지 확인"""
        if not self.date_time:
            return False
        return timezone.now() > self.date_time
    
    @property
    def can_participate(self):
        """참가 신청이 가능한지 확인"""
        # 활성화되지 않았거나 일시중단된 경우
        if not self.is_active or self.is_temporarily_closed:
            return False
        
        # 일정이 지난 경우
        if self.is_expired:
            return False
        
        # 정원이 찬 경우
        if self.is_full:
            return False
        
        return True
    
    @property
    def status_display(self):
        """상태 표시용 문자열"""
        if not self.is_active:
            return "비활성화"
        
        if self.is_temporarily_closed:
            return "일시중단"
        
        if self.is_expired:
            return "종료"
        
        if self.is_full:
            return "정원마감"
        
        if self.remaining_spots and self.remaining_spots <= 5:
            return f"마감임박 ({self.remaining_spots}자리)"
        
        return "참가가능"

class MeetupImage(models.Model):
    """밋업 이미지"""
    meetup = models.ForeignKey(Meetup, on_delete=models.CASCADE, related_name='images')
    
    # 이미지 정보
    original_name = models.CharField(max_length=255, verbose_name='원본 파일명')
    file_path = models.CharField(max_length=500, verbose_name='파일 경로')
    file_url = models.URLField(max_length=800, verbose_name='파일 URL')  # S3 URL은 길 수 있음
    file_size = models.PositiveIntegerField(null=True, blank=True, verbose_name='파일 크기 (bytes)')
    
    # 이미지 크기 정보
    width = models.PositiveIntegerField(default=500, verbose_name='이미지 너비')
    height = models.PositiveIntegerField(default=500, verbose_name='이미지 높이')  # 1:1 비율
    
    # 순서 정보 (이미지 정렬용)
    order = models.PositiveIntegerField(default=0, verbose_name='정렬 순서')
    
    # 메타 정보
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='업로드 시간')
    uploaded_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, verbose_name='업로드 사용자')
    
    class Meta:
        verbose_name = "밋업 이미지"
        verbose_name_plural = "밋업 이미지들"
        ordering = ['order', 'uploaded_at']
        indexes = [
            models.Index(fields=['meetup', 'order']),
            models.Index(fields=['uploaded_at']),
        ]
    
    def __str__(self):
        return f"{self.meetup.name} - {self.original_name}"
    
    def get_file_size_display(self):
        """파일 크기를 읽기 쉬운 형태로 반환"""
        if not self.file_size:
            return "크기 정보 없음"
        
        size = self.file_size
        for unit in ['bytes', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

class MeetupOption(models.Model):
    """밋업 옵션 (참가 유형, 식사 옵션 등)"""
    meetup = models.ForeignKey(Meetup, on_delete=models.CASCADE, related_name='options')
    name = models.CharField(max_length=100, verbose_name="옵션명")
    is_required = models.BooleanField(default=False, verbose_name="필수 선택")
    order = models.PositiveIntegerField(default=0, verbose_name="정렬순서")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "밋업 옵션"
        verbose_name_plural = "밋업 옵션"
        ordering = ['order']
        # 성능 최적화를 위한 인덱스 추가
        indexes = [
            models.Index(fields=['meetup']),            # 밋업별 옵션 조회용
            models.Index(fields=['order']),             # 정렬용
            models.Index(fields=['meetup', 'order']),   # 밋업 옵션 정렬용
            models.Index(fields=['is_required']),       # 필수 옵션 조회용
            models.Index(fields=['created_at']),        # 관리자 필터링용
        ]
    
    def __str__(self):
        return f"{self.meetup.name} - {self.name}"

class MeetupChoice(models.Model):
    """밋업 옵션 선택지"""
    option = models.ForeignKey(MeetupOption, on_delete=models.CASCADE, related_name='choices')
    name = models.CharField(max_length=100, verbose_name="선택지명")
    additional_price = models.IntegerField(default=0, verbose_name="추가요금(satoshi)")
    order = models.PositiveIntegerField(default=0, verbose_name="정렬순서")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "밋업 선택지"
        verbose_name_plural = "밋업 선택지"
        ordering = ['order']
        # 성능 최적화를 위한 인덱스 추가
        indexes = [
            models.Index(fields=['option']),             # 옵션별 선택지 조회용
            models.Index(fields=['order']),              # 정렬용
            models.Index(fields=['option', 'order']),    # 옵션 선택지 정렬용
            models.Index(fields=['additional_price']),   # 가격 기반 조회용
            models.Index(fields=['created_at']),         # 관리자 필터링용
        ]
    
    def __str__(self):
        return f"{self.option.name} - {self.name}"

class MeetupOrder(models.Model):
    """밋업 참가 주문"""
    STATUS_CHOICES = [
        ('pending', '결제 대기'),
        ('confirmed', '참가 확정'),
        ('cancelled', '참가 취소'),
        ('completed', '밋업 완료'),
    ]
    
    # 기본 정보
    meetup = models.ForeignKey(Meetup, on_delete=models.CASCADE, related_name='orders')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='meetup_orders', null=True, blank=True)
    
    # 참가자 정보 (비회원도 참가 가능)
    participant_name = models.CharField(max_length=100, verbose_name="참가자 이름")
    participant_email = models.EmailField(verbose_name="참가자 이메일")
    participant_phone = models.CharField(max_length=20, verbose_name="참가자 연락처", blank=True)
    
    # 주문 정보
    order_number = models.CharField(max_length=100, unique=True, verbose_name="주문번호")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="상태")
    
    # 임시 예약 정보 (정원 오버북킹 방지용)
    is_temporary_reserved = models.BooleanField(default=True, verbose_name="임시 예약 상태")
    reservation_expires_at = models.DateTimeField(null=True, blank=True, verbose_name="예약 만료 시간")
    auto_cancelled_reason = models.CharField(max_length=100, blank=True, verbose_name="자동 취소 사유")
    
    # 가격 정보
    base_price = models.PositiveIntegerField(verbose_name="기본 참가비(satoshi)")
    options_price = models.PositiveIntegerField(default=0, verbose_name="옵션 추가비(satoshi)")
    total_price = models.PositiveIntegerField(verbose_name="총 참가비(satoshi)")
    
    # 할인 정보
    is_early_bird = models.BooleanField(default=False, verbose_name="조기등록 할인 적용")
    discount_rate = models.PositiveIntegerField(default=0, verbose_name="할인율(%)")
    original_price = models.PositiveIntegerField(null=True, blank=True, verbose_name="원래 가격(satoshi)")
    
    # 결제 정보
    payment_hash = models.CharField(max_length=255, blank=True, verbose_name="결제 해시")
    payment_request = models.TextField(blank=True, verbose_name="결제 요청(인보이스)")
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name="결제 완료 시간")
    
    # 참가 확정 정보
    confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name="참가 확정 시간")
    confirmation_message_sent = models.BooleanField(default=False, verbose_name="확정 안내 발송 여부")
    
    # 참석 여부
    attended = models.BooleanField(default=False, verbose_name="참석 여부")
    attended_at = models.DateTimeField(null=True, blank=True, verbose_name="참석 체크 시간")
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "밋업 주문"
        verbose_name_plural = "밋업 주문"
        ordering = ['-created_at']
        indexes = [
            # 기존 인덱스들
            models.Index(fields=['meetup', 'status']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['order_number']),
            models.Index(fields=['payment_hash']),
            
            # 밋업 참가자 목록 조회 최적화를 위한 추가 인덱스들
            models.Index(fields=['status', 'user']),           # 상태별 사용자 조회용
            models.Index(fields=['user', 'created_at']),       # 사용자별 참가 내역 시간순 조회용
            models.Index(fields=['status', 'created_at']),     # 상태별 시간순 조회용
            models.Index(fields=['user', 'status', 'created_at']), # 복합 쿼리 최적화
            models.Index(fields=['meetup', '-created_at'], name='meetup_meet_meetup__276e50_idx'),    # 밋업별 최신 주문 조회용

            # 관리자 페이지 성능 최적화
            models.Index(fields=['is_temporary_reserved']),    # 임시예약 필터링용
            models.Index(fields=['attended']),                # 참석 여부 필터링용
            models.Index(fields=['reservation_expires_at']),  # 예약 만료 조회용
            models.Index(fields=['paid_at']),                 # 결제일시 필터링용
            models.Index(fields=['confirmed_at']),            # 확정일시 필터링용
            models.Index(fields=['attended_at']),             # 참석체크일시 필터링용
            
            # 집계 쿼리 최적화
            models.Index(fields=['user', 'total_price']),     # 사용자별 총 지출 집계용
            models.Index(fields=['meetup', 'user']),          # 밋업별 참가자 조회용
        ]
    
    def __str__(self):
        return f"{self.meetup.name} - {self.participant_name} ({self.order_number})"
    
    def save(self, *args, **kwargs):
        # 주문번호 자동 생성: store_id-ticket-YYYYMMDD-해시값 (밋업 진행일 기준)
        if not self.order_number:
            # 밋업 진행일을 기준으로 하되, 없으면 현재 날짜 사용
            if self.meetup and self.meetup.date_time:
                base_date = self.meetup.date_time
            else:
                base_date = datetime.datetime.now()
                
            store_id = self.meetup.store.store_id
            date_str = base_date.strftime('%Y%m%d')  # 20250606 형식
            hash_value = str(uuid.uuid4())[:8].upper()
            
            self.order_number = f"{store_id}-ticket-{date_str}-{hash_value}"
        
        super().save(*args, **kwargs)
    
    @property
    def is_paid(self):
        """결제 완료 여부"""
        return self.status in ['confirmed', 'completed'] and self.paid_at is not None
    
    @property
    def is_confirmed(self):
        """참가 확정 여부"""
        return self.status in ['confirmed', 'completed']
    
    @property
    def discount_amount(self):
        """할인 금액 계산"""
        if self.is_early_bird and self.original_price:
            return self.original_price - self.total_price
        return 0

class MeetupOrderOption(models.Model):
    """밋업 주문의 선택된 옵션"""
    order = models.ForeignKey(MeetupOrder, on_delete=models.CASCADE, related_name='selected_options')
    option = models.ForeignKey(MeetupOption, on_delete=models.CASCADE)
    choice = models.ForeignKey(MeetupChoice, on_delete=models.CASCADE)
    additional_price = models.IntegerField(verbose_name="추가요금(satoshi)")
    
    class Meta:
        verbose_name = "밋업 주문 옵션"
        verbose_name_plural = "밋업 주문 옵션"
        unique_together = ['order', 'option']  # 한 주문에서 같은 옵션은 하나만 선택 가능
    
    def __str__(self):
        return f"{self.order.order_number} - {self.option.name}: {self.choice.name}"
