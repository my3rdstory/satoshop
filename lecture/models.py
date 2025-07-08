from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import EmailValidator, RegexValidator
from stores.models import Store
from decimal import Decimal
from django.core.cache import cache
import requests
import datetime
import uuid


class Category(models.Model):
    """강의 카테고리"""
    name = models.CharField(max_length=100, verbose_name="카테고리명")
    description = models.TextField(blank=True, verbose_name="설명")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    
    class Meta:
        verbose_name = "카테고리"
        verbose_name_plural = "카테고리"
        
    def __str__(self):
        return self.name


class Lecture(models.Model):
    """강의"""
    DIFFICULTY_CHOICES = [
        ('beginner', '초급'),
        ('intermediate', '중급'),
        ('advanced', '고급'),
    ]
    
    STATUS_CHOICES = [
        ('draft', '임시저장'),
        ('published', '게시됨'),
        ('closed', '마감'),
    ]
    
    title = models.CharField(max_length=200, verbose_name="강의명")
    description = models.TextField(verbose_name="강의 설명")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name="카테고리")
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="강사")
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, verbose_name="난이도")
    duration = models.PositiveIntegerField(verbose_name="강의 시간(분)")
    max_students = models.PositiveIntegerField(verbose_name="최대 수강인원")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="가격")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name="상태")
    start_date = models.DateTimeField(verbose_name="강의 시작일")
    end_date = models.DateTimeField(verbose_name="강의 종료일")
    thumbnail = models.ImageField(upload_to='lectures/thumbnails/', blank=True, null=True, verbose_name="썸네일")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")
    
    class Meta:
        verbose_name = "강의"
        verbose_name_plural = "강의"
        ordering = ['-created_at']
        
    def __str__(self):
        return self.title
    
    @property
    def enrolled_count(self):
        """등록된 수강생 수"""
        return self.enrollments.filter(status='active').count()
    
    @property
    def is_full(self):
        """수강 인원 마감 여부"""
        return self.enrolled_count >= self.max_students
    
    @property
    def is_active(self):
        """강의 진행 중 여부"""
        now = timezone.now()
        return self.start_date <= now <= self.end_date


class LectureEnrollment(models.Model):
    """강의 수강 등록"""
    STATUS_CHOICES = [
        ('active', '수강중'),
        ('completed', '수강완료'),
        ('cancelled', '취소'),
    ]
    
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE, related_name='enrollments', verbose_name="강의")
    student = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="수강생")
    enrolled_at = models.DateTimeField(auto_now_add=True, verbose_name="등록일")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name="상태")
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name="수강완료일")
    
    class Meta:
        verbose_name = "강의 수강 등록"
        verbose_name_plural = "강의 수강 등록"
        unique_together = ['lecture', 'student']  # 한 강의에 같은 학생이 중복 등록 불가
        
    def __str__(self):
        return f"{self.student.username} - {self.lecture.title}"


class LectureReview(models.Model):
    """강의 리뷰"""
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE, related_name='reviews', verbose_name="강의")
    student = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="수강생")
    rating = models.PositiveIntegerField(choices=[(i, i) for i in range(1, 6)], verbose_name="평점")
    comment = models.TextField(verbose_name="리뷰 내용")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="작성일")
    
    class Meta:
        verbose_name = "강의 리뷰"
        verbose_name_plural = "강의 리뷰"
        unique_together = ['lecture', 'student']  # 한 강의에 한 학생당 하나의 리뷰만
        
    def __str__(self):
        return f"{self.lecture.title} - {self.rating}점"


class LiveLecture(models.Model):
    """라이브 강의"""
    PRICE_DISPLAY_CHOICES = [
        ('free', '무료'),
        ('sats', '사토시 가격'),
        ('krw', '원화연동 가격'),
    ]
    
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='live_lectures')
    name = models.CharField(max_length=200, verbose_name="라이브 강의명")
    description = models.TextField(verbose_name="라이브 강의 설명", blank=True)
    
    # 라이브 강의 일시
    date_time = models.DateTimeField(verbose_name="라이브 강의 일시", null=True, blank=True)
    special_notes = models.TextField(verbose_name="특이사항", blank=True)
    
    # 강사 정보
    instructor_contact = models.CharField(
        max_length=20, 
        verbose_name="강사 연락처", 
        blank=True,
        validators=[RegexValidator(
            regex=r'^[\d\-\+\(\)\s]+$',
            message='올바른 연락처 형식이 아닙니다.',
        )]
    )
    instructor_email = models.EmailField(
        verbose_name="강사 이메일", 
        blank=True,
        validators=[EmailValidator()]
    )
    instructor_chat_channel = models.URLField(verbose_name="강사 소통채널", blank=True)
    
    # 정원
    max_participants = models.PositiveIntegerField(verbose_name="정원", null=True, blank=True)
    no_limit = models.BooleanField(default=False, verbose_name="정원 없음")
    
    # 가격 정보
    price_display = models.CharField(
        max_length=10,
        choices=PRICE_DISPLAY_CHOICES,
        default='free',
        verbose_name='가격 표시 방식'
    )
    price = models.PositiveIntegerField(verbose_name="참가비(satoshi)", default=0)
    price_krw = models.PositiveIntegerField(null=True, blank=True, verbose_name="원화 참가비", help_text="원화 단위")
    
    # 할인 정보
    is_discounted = models.BooleanField(default=False, verbose_name="할인 적용")
    discounted_price = models.PositiveIntegerField(verbose_name="할인가(satoshi)", null=True, blank=True)
    discounted_price_krw = models.PositiveIntegerField(null=True, blank=True, verbose_name="원화 할인가", help_text="원화 단위")
    early_bird_end_date = models.DateField(verbose_name="조기등록 종료일", null=True, blank=True)
    early_bird_end_time = models.TimeField(verbose_name="조기등록 종료시간", null=True, blank=True)
    
    # 상태
    is_active = models.BooleanField(default=True, verbose_name="활성화")
    is_temporarily_closed = models.BooleanField(default=False, verbose_name="일시중단")
    
    # 안내 메시지
    completion_message = models.TextField(verbose_name="참가완료 안내메시지", blank=True)
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "라이브 강의"
        verbose_name_plural = "라이브 강의"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['store']),
            models.Index(fields=['is_active']),
            models.Index(fields=['date_time']),
            models.Index(fields=['store', 'is_active']),
            models.Index(fields=['store', 'date_time']),
            models.Index(fields=['deleted_at']),
            models.Index(fields=['store', 'deleted_at']),
            models.Index(fields=['created_at']),
            models.Index(fields=['updated_at']),
            models.Index(fields=['is_temporarily_closed']),
            models.Index(fields=['price_display']),
        ]
    
    def __str__(self):
        return f"{self.store.store_name} - {self.name}"
    
    def clean(self):
        """모델 검증"""
        from django.core.exceptions import ValidationError
        
        # 연락처와 이메일 중 하나는 필수
        if not self.instructor_contact and not self.instructor_email:
            raise ValidationError("강사 연락처 또는 이메일 중 하나는 필수입니다.")
    
    @property
    def is_deleted(self):
        return self.deleted_at is not None
    
    @property
    def current_participants(self):
        """현재 참가자 수 (확정된 주문 기준)"""
        return self.orders.filter(status__in=['confirmed', 'completed']).count()
    
    @property
    def is_full(self):
        if self.no_limit or not self.max_participants:
            return False
        return self.current_participants >= self.max_participants
    
    @property
    def remaining_spots(self):
        """남은 자리 수"""
        if self.no_limit or not self.max_participants:
            return None
        return max(0, self.max_participants - self.current_participants)
    
    @property
    def current_price(self):
        """현재 적용되는 가격 (사토시 단위)"""
        if self.price_display == 'free':
            return 0
        
        # 할인 적용 중이면 할인가
        if self.is_discounted and self.is_early_bird_active:
            if self.price_display == 'krw':
                return self.public_discounted_price_krw or self.public_price_krw
            return self.discounted_price or self.price
        
        if self.price_display == 'krw':
            return self.public_price_krw
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
        if not self.is_discounted:
            return 0
        
        if self.price_display == 'krw':
            if not self.discounted_price_krw or not self.price_krw:
                return 0
            return int((1 - self.discounted_price_krw / self.price_krw) * 100)
        else:
            if not self.discounted_price or not self.price:
                return 0
            return int((1 - self.discounted_price / self.price) * 100)
    
    @property
    def is_expired(self):
        """라이브 강의 일정이 지났는지 확인"""
        if not self.date_time:
            return False
        return timezone.now() > self.date_time
    
    @property
    def can_participate(self):
        """참가 신청이 가능한지 확인"""
        if not self.is_active or self.is_temporarily_closed:
            return False
        
        if self.is_expired:
            return False
        
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
            return "마감"
        
        return "신청가능"
    
    @classmethod
    def get_btc_krw_rate(cls):
        """업비트 BTC/KRW 환율 조회 (캐시 60초)"""
        cache_key = 'btc_krw_rate'
        rate = cache.get(cache_key)
        
        if rate is None:
            try:
                response = requests.get('https://api.upbit.com/v1/ticker?markets=KRW-BTC')
                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        rate = Decimal(str(data[0]['trade_price']))
                        cache.set(cache_key, rate, 60)
            except Exception as e:
                print(f"환율 조회 실패: {e}")
                rate = Decimal('0')
        
        return rate
    
    @property
    def public_price_krw(self):
        """사용자용 원화연동 가격 (사토시 단위)"""
        if self.price_display == 'krw' and self.price_krw is not None:
            from myshop.models import ExchangeRate
            latest_rate = ExchangeRate.get_latest_rate()
            if latest_rate and latest_rate.btc_krw_rate > 0:
                btc_amount = self.price_krw / float(latest_rate.btc_krw_rate)
                sats_amount = btc_amount * 100_000_000
                return round(sats_amount)
        return self.price
    
    @property
    def public_discounted_price_krw(self):
        """사용자용 원화연동 할인가 (사토시 단위)"""
        if not self.is_discounted:
            return None
        
        if self.price_display == 'krw' and self.discounted_price_krw is not None:
            from myshop.models import ExchangeRate
            latest_rate = ExchangeRate.get_latest_rate()
            if latest_rate and latest_rate.btc_krw_rate > 0:
                btc_amount = self.discounted_price_krw / float(latest_rate.btc_krw_rate)
                sats_amount = btc_amount * 100_000_000
                return round(sats_amount)
        return self.discounted_price
    
    @property
    def display_price(self):
        """표시 가격 - 가격 표시 방식에 따라 원화 또는 사토시 반환"""
        if self.price_display == 'free':
            return 0
        if self.price_display == 'krw' and self.price_krw is not None:
            return self.price_krw
        return self.price
    
    @property
    def display_discounted_price(self):
        """표시 할인 가격 - 가격 표시 방식에 따라 원화 또는 사토시 반환"""
        if not self.is_discounted:
            return None
        if self.price_display == 'krw' and self.discounted_price_krw is not None:
            return self.discounted_price_krw
        return self.discounted_price
    
    @property
    def price_unit(self):
        """가격 단위 반환"""
        if self.price_display == 'free':
            return ''
        elif self.price_display == 'krw':
            return '원'
        return 'sats'


class LiveLectureImage(models.Model):
    """라이브 강의 이미지"""
    live_lecture = models.ForeignKey(LiveLecture, on_delete=models.CASCADE, related_name='images')
    
    # 이미지 정보
    original_name = models.CharField(max_length=255, verbose_name='원본 파일명')
    file_path = models.CharField(max_length=500, verbose_name='파일 경로')
    file_url = models.URLField(max_length=800, verbose_name='파일 URL')
    file_size = models.PositiveIntegerField(null=True, blank=True, verbose_name='파일 크기 (bytes)')
    
    # 이미지 크기 정보 (1:1 비율)
    width = models.PositiveIntegerField(default=500, verbose_name='이미지 너비')
    height = models.PositiveIntegerField(default=500, verbose_name='이미지 높이')
    
    # 순서 정보
    order = models.PositiveIntegerField(default=0, verbose_name='정렬 순서')
    
    # 메타 정보
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='업로드 시간')
    uploaded_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, verbose_name='업로드 사용자')
    
    class Meta:
        verbose_name = "라이브 강의 이미지"
        verbose_name_plural = "라이브 강의 이미지들"
        ordering = ['order', 'uploaded_at']
        indexes = [
            models.Index(fields=['live_lecture']),
            models.Index(fields=['order']),
            models.Index(fields=['uploaded_at']),
        ]
    
    def __str__(self):
        return f"{self.live_lecture.name} - {self.original_name}"
    
    def get_file_size_display(self):
        """파일 크기를 읽기 쉬운 형태로 반환"""
        if not self.file_size:
            return "알 수 없음"
        
        for unit in ['bytes', 'KB', 'MB', 'GB']:
            if self.file_size < 1024.0:
                return f"{self.file_size:.1f} {unit}"
            self.file_size /= 1024.0
        return f"{self.file_size:.1f} TB"


class LiveLectureOrder(models.Model):
    """라이브 강의 참가 주문"""
    STATUS_CHOICES = [
        ('pending', '결제 대기'),
        ('confirmed', '참가 확정'),
        ('cancelled', '참가 취소'),
        ('completed', '강의 완료'),
    ]
    
    # 기본 정보
    live_lecture = models.ForeignKey(LiveLecture, on_delete=models.CASCADE, related_name='orders')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='live_lecture_orders')
    
    # 주문 정보
    order_number = models.CharField(max_length=100, unique=True, verbose_name="주문번호")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="상태")
    
    # 임시 예약 정보
    is_temporary_reserved = models.BooleanField(default=True, verbose_name="임시 예약 상태")
    reservation_expires_at = models.DateTimeField(null=True, blank=True, verbose_name="예약 만료 시간")
    auto_cancelled_reason = models.CharField(max_length=100, blank=True, verbose_name="자동 취소 사유")
    
    # 가격 정보
    price = models.PositiveIntegerField(verbose_name="참가비(satoshi)")
    
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
        verbose_name = "라이브 강의 주문"
        verbose_name_plural = "라이브 강의 주문"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['live_lecture']),
            models.Index(fields=['user']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['live_lecture', 'user']),
            models.Index(fields=['live_lecture', 'status']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['order_number']),
            models.Index(fields=['payment_hash']),
            models.Index(fields=['is_temporary_reserved']),
            models.Index(fields=['reservation_expires_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.live_lecture.name}"
    
    def save(self, *args, **kwargs):
        # 주문번호 자동 생성
        if not self.order_number:
            date_str = self.live_lecture.date_time.strftime('%Y%m%d') if self.live_lecture.date_time else timezone.now().strftime('%Y%m%d')
            unique_id = str(uuid.uuid4())[:8]
            self.order_number = f"{self.live_lecture.store.store_id}-lecture-live-{date_str}-{unique_id}"
        
        super().save(*args, **kwargs)
    
    @property
    def is_paid(self):
        """결제 완료 여부"""
        return self.paid_at is not None
    
    @property
    def is_confirmed(self):
        """참가 확정 여부"""
        return self.status == 'confirmed'
    
    @property
    def discount_amount(self):
        """할인 금액"""
        if self.original_price:
            return self.original_price - self.price
        return 0
