from django.db import models
from django.utils import timezone
from django.core.validators import EmailValidator, RegexValidator
from stores.models import Store

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
    def is_full(self):
        if not self.max_participants:
            return False
        # 추후 참가자 수 계산 로직 추가
        current_participants = 0  # 실제 참가자 수로 교체 필요
        return current_participants >= self.max_participants
    
    @property
    def remaining_spots(self):
        """남은 자리 수"""
        if not self.max_participants:
            return None
        # 추후 참가자 수 계산 로직 추가
        current_participants = 0  # 실제 참가자 수로 교체 필요
        return max(0, self.max_participants - current_participants)
    
    @property
    def current_price(self):
        """현재 적용되는 가격"""
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
    
    def __str__(self):
        return f"{self.option.name} - {self.name}"
