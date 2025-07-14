from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator, EmailValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
import hashlib
from stores.models import Store


def validate_file_size(value):
    """파일 크기 제한 - 100MB"""
    file_size = value.size
    if file_size > 104857600:  # 100MB
        raise ValidationError('파일 크기는 100MB를 초과할 수 없습니다.')


class DigitalFile(models.Model):
    """디지털 파일"""
    PRICE_DISPLAY_CHOICES = [
        ('free', '무료'),
        ('sats', '사토시 가격'),
        ('krw', '원화연동 가격'),
    ]
    
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='digital_files')
    name = models.CharField(max_length=200, verbose_name="파일명")
    description = models.TextField(verbose_name="파일 설명", blank=True)
    
    # 파일 정보
    file = models.FileField(
        upload_to='digital_files/%Y/%m/%d/', 
        verbose_name="파일",
        validators=[validate_file_size]
    )
    original_filename = models.CharField(max_length=255, verbose_name="원본 파일명", blank=True)
    file_size = models.PositiveIntegerField(verbose_name="파일 크기(bytes)", null=True, blank=True)
    file_hash = models.CharField(max_length=64, verbose_name="파일 해시", blank=True, editable=False)
    
    # 미리보기 이미지 (선택사항)
    preview_image = models.ImageField(
        upload_to='digital_files/previews/%Y/%m/%d/',
        verbose_name="미리보기 이미지",
        blank=True,
        null=True
    )
    
    # 가격 정보
    price_display = models.CharField(
        max_length=10,
        choices=PRICE_DISPLAY_CHOICES,
        default='free',
        verbose_name='가격 표시 방식'
    )
    price = models.PositiveIntegerField(verbose_name="가격(satoshi)", default=0)
    price_krw = models.PositiveIntegerField(null=True, blank=True, verbose_name="원화 가격", help_text="원화 단위")
    
    # 할인 정보
    is_discounted = models.BooleanField(default=False, verbose_name="할인 적용")
    discounted_price = models.PositiveIntegerField(verbose_name="할인가(satoshi)", null=True, blank=True)
    discounted_price_krw = models.PositiveIntegerField(null=True, blank=True, verbose_name="원화 할인가", help_text="원화 단위")
    discount_end_date = models.DateField(verbose_name="할인 종료일", null=True, blank=True)
    discount_end_time = models.TimeField(verbose_name="할인 종료시간", null=True, blank=True)
    
    # 판매 설정
    max_downloads = models.PositiveIntegerField(
        verbose_name="최대 다운로드 횟수", 
        null=True, 
        blank=True,
        help_text="비워두면 무제한"
    )
    download_expiry_days = models.PositiveIntegerField(
        verbose_name="다운로드 유효기간(일)", 
        null=True, 
        blank=True,
        help_text="구매 후 다운로드 가능 기간, 비워두면 무제한"
    )
    
    # 상태
    is_active = models.BooleanField(default=True, verbose_name="활성화")
    is_temporarily_closed = models.BooleanField(default=False, verbose_name="일시중단")
    
    # 안내 메시지
    purchase_message = models.TextField(verbose_name="구매완료 안내메시지", blank=True)
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "디지털 파일"
        verbose_name_plural = "디지털 파일"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['store']),
            models.Index(fields=['is_active']),
            models.Index(fields=['created_at']),
            models.Index(fields=['store', 'is_active']),
            models.Index(fields=['deleted_at']),
            models.Index(fields=['store', 'deleted_at']),
        ]
    
    def __str__(self):
        return f"[{self.store.name}] {self.name}"
    
    def save(self, *args, **kwargs):
        if self.file:
            # 원본 파일명 저장
            if not self.original_filename:
                self.original_filename = self.file.name.split('/')[-1]
            
            # 파일 크기 저장
            if not self.file_size:
                self.file_size = self.file.size
            
            # 파일 해시 생성 (중복 파일 체크용)
            if not self.file_hash:
                hasher = hashlib.sha256()
                for chunk in self.file.chunks():
                    hasher.update(chunk)
                self.file_hash = hasher.hexdigest()
        
        super().save(*args, **kwargs)
    
    @property
    def is_discount_active(self):
        """할인이 현재 활성화되어 있는지 확인"""
        if not self.is_discounted:
            return False
        
        if not self.discount_end_date:
            return True
        
        now = timezone.now()
        if self.discount_end_time:
            end_datetime = timezone.datetime.combine(
                self.discount_end_date, 
                self.discount_end_time,
                tzinfo=now.tzinfo
            )
        else:
            end_datetime = timezone.datetime.combine(
                self.discount_end_date,
                timezone.datetime.max.time(),
                tzinfo=now.tzinfo
            )
        
        return now <= end_datetime
    
    @property
    def current_price(self):
        """현재 적용 가격 (할인 적용)"""
        if self.price_display == 'free':
            return 0
        
        if self.is_discount_active:
            if self.price_display == 'krw':
                return self.discounted_price_krw or self.price_krw
            return self.discounted_price or self.price
        
        if self.price_display == 'krw':
            return self.price_krw
        return self.price
    
    @property
    def current_price_sats(self):
        """현재 가격 (사토시 단위로 변환)"""
        if self.price_display == 'free':
            return 0
        
        current = self.current_price
        
        if self.price_display == 'krw' and current is not None:
            from myshop.models import ExchangeRate
            latest_rate = ExchangeRate.get_latest_rate()
            if latest_rate and latest_rate.btc_krw_rate > 0:
                btc_amount = current / float(latest_rate.btc_krw_rate)
                sats_amount = btc_amount * 100_000_000
                return round(sats_amount)
        
        return current
    
    @property
    def price_unit(self):
        """가격 단위 반환"""
        if self.price_display == 'free':
            return ''
        elif self.price_display == 'krw':
            return '원'
        return 'sats'
    
    @property
    def available_downloads(self):
        """판매 가능한 다운로드 수"""
        if not self.max_downloads:
            return None  # 무제한
        
        sold_count = self.orders.filter(status='confirmed').count()
        return max(0, self.max_downloads - sold_count)
    
    @property
    def is_sold_out(self):
        """매진 여부"""
        if not self.max_downloads:
            return False
        return self.available_downloads <= 0
    
    @property
    def download_count(self):
        """총 다운로드 횟수"""
        return FileDownloadLog.objects.filter(
            order__digital_file=self
        ).count()
    
    @property
    def sales_count(self):
        """판매 횟수"""
        return self.orders.filter(status='confirmed').count()
    
    def get_file_size_display(self):
        """파일 크기를 읽기 쉬운 형태로 반환"""
        if not self.file_size:
            return "알 수 없음"
        
        size = self.file_size
        for unit in ['bytes', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"


class FileOrder(models.Model):
    """파일 구매 주문"""
    STATUS_CHOICES = [
        ('pending', '결제 대기'),
        ('confirmed', '구매 확정'),
        ('cancelled', '구매 취소'),
    ]
    
    # 기본 정보
    digital_file = models.ForeignKey(DigitalFile, on_delete=models.CASCADE, related_name='orders')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='file_orders')
    
    # 주문 정보
    order_number = models.CharField(max_length=100, unique=True, verbose_name="주문번호")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="상태")
    
    # 임시 예약 정보
    is_temporary_reserved = models.BooleanField(default=True, verbose_name="임시 예약 상태")
    reservation_expires_at = models.DateTimeField(null=True, blank=True, verbose_name="예약 만료 시간")
    auto_cancelled_reason = models.CharField(max_length=100, blank=True, verbose_name="자동 취소 사유")
    
    # 가격 정보
    price = models.PositiveIntegerField(verbose_name="구매가(satoshi)")
    
    # 할인 정보
    is_discounted = models.BooleanField(default=False, verbose_name="할인 적용")
    discount_rate = models.PositiveIntegerField(default=0, verbose_name="할인율(%)")
    original_price = models.PositiveIntegerField(null=True, blank=True, verbose_name="원래 가격(satoshi)")
    
    # 결제 정보
    payment_hash = models.CharField(max_length=255, blank=True, verbose_name="결제 해시")
    payment_request = models.TextField(blank=True, verbose_name="결제 요청(인보이스)")
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name="결제 완료 시간")
    
    # 구매 확정 정보
    confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name="구매 확정 시간")
    confirmation_message_sent = models.BooleanField(default=False, verbose_name="확정 안내 발송 여부")
    
    # 다운로드 만료일
    download_expires_at = models.DateTimeField(null=True, blank=True, verbose_name="다운로드 만료일")
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "파일 주문"
        verbose_name_plural = "파일 주문"
        ordering = ['-created_at']
        # 동일한 사용자가 동일한 파일에 중복 구매 방지
        constraints = [
            models.UniqueConstraint(
                fields=['digital_file', 'user'],
                condition=models.Q(status='confirmed'),
                name='unique_confirmed_file_order_per_user'
            )
        ]
        indexes = [
            models.Index(fields=['digital_file']),
            models.Index(fields=['user']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['digital_file', 'user']),
            models.Index(fields=['digital_file', 'status']),
            models.Index(fields=['user', 'status']),
        ]
    
    def __str__(self):
        return f"{self.order_number} - {self.user.username}"
    
    def save(self, *args, **kwargs):
        # 주문번호 생성
        if not self.order_number:
            import uuid
            self.order_number = f"FILE-{timezone.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        
        # 임시 예약 만료 시간 설정 (15분)
        if self.is_temporary_reserved and not self.reservation_expires_at:
            self.reservation_expires_at = timezone.now() + timedelta(minutes=15)
        
        # 다운로드 만료일 설정
        if self.status == 'confirmed' and not self.download_expires_at:
            if self.digital_file.download_expiry_days:
                self.download_expires_at = timezone.now() + timedelta(days=self.digital_file.download_expiry_days)
        
        super().save(*args, **kwargs)
    
    @property
    def is_download_expired(self):
        """다운로드 기간 만료 여부"""
        if not self.download_expires_at:
            return False
        return timezone.now() > self.download_expires_at
    
    @property
    def can_download(self):
        """다운로드 가능 여부"""
        return (
            self.status == 'confirmed' and 
            not self.is_download_expired and
            self.digital_file.is_active
        )
    
    @property
    def remaining_downloads(self):
        """남은 다운로드 횟수"""
        # 파일의 최대 다운로드 횟수가 설정되어 있지 않으면 무제한
        if not self.digital_file.max_downloads:
            return None
        
        # 현재 사용자의 다운로드 횟수
        download_count = FileDownloadLog.objects.filter(order=self).count()
        
        # 보통 구매당 1회 다운로드로 제한
        return max(0, 1 - download_count)


class FileDownloadLog(models.Model):
    """파일 다운로드 로그"""
    order = models.ForeignKey(FileOrder, on_delete=models.CASCADE, related_name='download_logs')
    ip_address = models.GenericIPAddressField(verbose_name="IP 주소")
    user_agent = models.TextField(verbose_name="User Agent", blank=True)
    downloaded_at = models.DateTimeField(auto_now_add=True, verbose_name="다운로드 시간")
    
    class Meta:
        verbose_name = "다운로드 로그"
        verbose_name_plural = "다운로드 로그"
        ordering = ['-downloaded_at']
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['downloaded_at']),
        ]
    
    def __str__(self):
        return f"{self.order.order_number} - {self.downloaded_at}"
