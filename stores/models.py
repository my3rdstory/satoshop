from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from cryptography.fernet import Fernet
from django.conf import settings
from django.utils import timezone
import os
import base64


MAX_PROMOTION_IMAGES = 4
PROMOTION_STATUS_PENDING = 'pending'
PROMOTION_STATUS_SHIPPED = 'shipped'
PROMOTION_STATUS_CHOICES = [
    (PROMOTION_STATUS_PENDING, '발송예정'),
    (PROMOTION_STATUS_SHIPPED, '발송'),
]


class BahPromotionLinkSettings(models.Model):
    """BAH 홍보요청 화면에 노출할 가이드 링크 설정"""

    login_guide_url = models.URLField(
        blank=True,
        help_text='월오사 라이트닝 로그인 사용법 문서 링크'
    )
    usage_guide_url = models.URLField(
        blank=True,
        help_text='월오사 사용법 상세 문서 링크'
    )
    package_request_url = models.URLField(
        blank=True,
        help_text='홍보 패키지 신청 링크 (예: 사토샵 상품 페이지)'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'BAH 링크 설정'
        verbose_name_plural = 'BAH 링크 설정'

    def __str__(self):
        return 'BAH 링크 설정'

    @classmethod
    def get_solo(cls):
        instance = cls.objects.first()
        if instance is None:
            instance = cls.objects.create()
        return instance

class Store(models.Model):
    SHIPPING_FEE_MODE_CHOICES = [
        ('free', '무료 배송'),
        ('flat', '유료 고정 배송비'),
    ]

    # 1단계 - 스토어 기본 정보
    store_id = models.CharField(
        max_length=50, 
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z0-9_-]+$',
                message='스토어 아이디는 영문, 숫자, 하이픈(-), 언더스코어(_)만 사용 가능합니다.'
            )
        ],
        help_text="스토어 접속 경로로 사용됩니다. (예: mystore)"
    )
    
    # 2단계 - 스토어 정보
    store_name = models.CharField(max_length=100, help_text="스토어 이름")
    store_description = models.TextField(blank=True, help_text="스토어 설명 (Markdown 형식)")
    owner_name = models.CharField(max_length=50, help_text="주인장 이름")
    
    # 주인장 연락처 - 최소 하나는 필수
    owner_phone = models.CharField(max_length=20, blank=True, help_text="주인장 휴대전화")
    owner_email = models.EmailField(blank=True, help_text="주인장 이메일")
    
    # 사업자 정보 (선택사항)
    business_license_number = models.CharField(max_length=50, blank=True, help_text="사업자등록번호")
    telecommunication_sales_number = models.CharField(max_length=50, blank=True, help_text="통신판매업번호")
    
    chat_channel = models.URLField(help_text="대화채널 (오픈카톡, 텔레그램, 라인, 엑스 등)")
    
    # 3단계 - 블링크 API 정보 (암호화 저장)
    blink_api_info_encrypted = models.TextField(blank=True, help_text="암호화된 블링크 API 정보")
    blink_wallet_id_encrypted = models.TextField(blank=True, help_text="암호화된 블링크 월렛 ID")
    
    # 이메일 발송 설정 (암호화 저장)
    email_host_user = models.EmailField(blank=True, help_text="Gmail 이메일 주소")
    email_host_password_encrypted = models.TextField(blank=True, help_text="암호화된 Gmail 앱 비밀번호")
    email_from_name = models.CharField(max_length=100, blank=True, help_text="발신자 이름 (기본값: 스토어명)")
    email_enabled = models.BooleanField(default=False, help_text="이메일 발송 기능 활성화")
    
    # 스토어 테마 설정
    hero_color1 = models.CharField(max_length=7, default="#667eea", help_text="히어로 섹션 그라데이션 시작 색상")
    hero_color2 = models.CharField(max_length=7, default="#764ba2", help_text="히어로 섹션 그라데이션 끝 색상")
    hero_text_color = models.CharField(max_length=7, default="#ffffff", help_text="히어로 섹션 텍스트 색상")

    # 배송비 설정
    shipping_fee_mode = models.CharField(
        max_length=10,
        choices=SHIPPING_FEE_MODE_CHOICES,
        default='free',
        help_text="스토어 배송비 정책"
    )
    shipping_fee_sats = models.PositiveIntegerField(
        default=0,
        help_text="사토시 단위 고정 배송비"
    )
    shipping_fee_krw = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="원화 기준 배송비"
    )
    free_shipping_threshold_krw = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="원화 기준 무료 배송 조건"
    )
    free_shipping_threshold_sats = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="사토시 기준 무료 배송 조건"
    )

    # 스토어 결제완료 안내 메시지
    completion_message = models.TextField(blank=True, help_text="결제 완료 후 고객에게 보여줄 기본 안내 메시지")
    
    # 메타 정보
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stores')
    is_active = models.BooleanField(default=False, help_text="스토어 활성화 상태")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True, help_text="소프트 삭제 시간")
    
    class Meta:
        verbose_name = "스토어"
        verbose_name_plural = "스토어들"
        ordering = ['-created_at']
        # 성능 최적화를 위한 인덱스 추가
        indexes = [
            # Django 관리자 필터링용
            models.Index(fields=['is_active']),
            models.Index(fields=['deleted_at']),
            models.Index(fields=['created_at']),
            models.Index(fields=['updated_at']),
            
            # 스토어 조회 최적화
            models.Index(fields=['store_id', 'deleted_at']),  # store_detail 뷰용
            models.Index(fields=['owner', 'deleted_at']),     # 사용자별 스토어 조회용
            models.Index(fields=['is_active', 'deleted_at']), # 활성 스토어 조회용
            
            # 복합 인덱스
            models.Index(fields=['is_active', 'deleted_at', 'created_at']),  # 홈페이지 스토어 목록용
            models.Index(fields=['email_enabled']),
            models.Index(fields=['email_enabled', 'deleted_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['owner'],
                condition=models.Q(deleted_at__isnull=True),
                name='unique_active_store_per_owner'
            ),
            models.UniqueConstraint(
                fields=['store_id'],
                condition=models.Q(deleted_at__isnull=True),
                name='unique_active_store_id'
            )
        ]
    
    def __str__(self):
        return f"{self.store_name} ({self.store_id})"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        # 연락처 중 최소 하나는 필수
        if not self.owner_phone and not self.owner_email:
            raise ValidationError('주인장 연락처(휴대전화 또는 이메일) 중 최소 하나는 입력해야 합니다.')
        
        # 스토어 아이디 예약어 검증
        if self.store_id:
            try:
                # ReservedStoreId 모델이 정의된 후에만 확인
                if 'ReservedStoreId' in globals():
                    if ReservedStoreId.is_reserved(self.store_id):
                        raise ValidationError(f'"{self.store_id}"는 예약어로 사용할 수 없습니다.')
            except:
                # 예외 상황에서는 패스 (마이그레이션 등)
                pass
    
    def _get_encryption_key(self):
        """암호화 키 생성 또는 가져오기"""
        # 설정에서 키를 가져오거나 환경변수에서 가져오기
        key = getattr(settings, 'BLINK_ENCRYPTION_KEY', None)
        if not key:
            key = os.environ.get('BLINK_ENCRYPTION_KEY')
        
        if not key:
            # 개발 환경에서는 고정 키 사용 (실제 운영에서는 보안 위험!)
            key = "development_key_32_bytes_exactly_!"
            if settings.DEBUG:
                print("DEBUG: ⚠️ 개발용 고정 암호화 키 사용 중 - 운영 환경에서는 반드시 변경하세요!")
        
        # 키를 32바이트로 맞추기
        if isinstance(key, str):
            key = key.encode('utf-8')
        
        # 32바이트로 패딩 또는 자르기
        if len(key) < 32:
            key = key.ljust(32, b'0')
        elif len(key) > 32:
            key = key[:32]
        
        return base64.urlsafe_b64encode(key)
    
    def encrypt_data(self, data):
        """데이터 암호화"""
        if not data:
            return ""
        
        try:
            key = self._get_encryption_key()
            fernet = Fernet(key)
            encrypted_data = fernet.encrypt(data.encode('utf-8'))
            return encrypted_data.decode('utf-8')
        except Exception as e:
            if settings.DEBUG:
                print(f"DEBUG: 암호화 실패: {e}")
            raise ValueError(f"데이터 암호화에 실패했습니다: {str(e)}")
    
    def decrypt_data(self, encrypted_data):
        """데이터 복호화"""
        if not encrypted_data:
            return ""
        
        try:
            key = self._get_encryption_key()
            fernet = Fernet(key)
            decrypted_data = fernet.decrypt(encrypted_data.encode('utf-8'))
            return decrypted_data.decode('utf-8')
        except Exception as e:
            if settings.DEBUG:
                print(f"DEBUG: 복호화 실패: {e}")
                print(f"DEBUG: 시도한 데이터: {encrypted_data[:50]}...")
            raise ValueError(f"데이터 복호화에 실패했습니다: {str(e)}")
    
    def set_blink_api_info(self, api_info):
        """블링크 API 정보 암호화 저장"""
        self.blink_api_info_encrypted = self.encrypt_data(api_info)
    
    def get_blink_api_info(self):
        """블링크 API 정보 가져오기"""
        if not self.blink_api_info_encrypted:
            return ""
        
        # 암호화된 데이터인지 평문인지 확인
        try:
            # 암호화된 데이터라면 복호화 시도
            return self.decrypt_data(self.blink_api_info_encrypted)
        except:
            # 복호화 실패시 평문으로 간주하여 그대로 반환 (기존 데이터 호환성)
            if settings.DEBUG:
                print(f"DEBUG: API 정보 복호화 실패 - 평문으로 간주")
            return self.blink_api_info_encrypted
    
    def set_blink_wallet_id(self, wallet_id):
        """블링크 월렛 ID 암호화 저장"""
        self.blink_wallet_id_encrypted = self.encrypt_data(wallet_id)
    
    def get_blink_wallet_id(self):
        """블링크 월렛 ID 가져오기"""
        if not self.blink_wallet_id_encrypted:
            return ""
        
        # 암호화된 데이터인지 평문인지 확인
        try:
            # 암호화된 데이터라면 복호화 시도
            return self.decrypt_data(self.blink_wallet_id_encrypted)
        except:
            # 복호화 실패시 평문으로 간주하여 그대로 반환 (기존 데이터 호환성)
            if settings.DEBUG:
                print(f"DEBUG: 월렛 ID 복호화 실패 - 평문으로 간주")
            return self.blink_wallet_id_encrypted
    
    def set_email_host_password(self, password):
        """Gmail 앱 비밀번호 암호화 저장"""
        self.email_host_password_encrypted = self.encrypt_data(password)
    
    def get_email_host_password(self):
        """Gmail 앱 비밀번호 가져오기"""
        if not self.email_host_password_encrypted:
            return ""

        try:
            return self.decrypt_data(self.email_host_password_encrypted)
        except:
            # 복호화 실패시 평문으로 간주하여 그대로 반환 (기존 데이터 호환성)
            if settings.DEBUG:
                print(f"DEBUG: 이메일 비밀번호 복호화 실패 - 평문으로 간주")
            return self.email_host_password_encrypted

    # =====================
    # 배송비 관련 유틸
    # =====================

    def set_shipping_fees(self, mode, fee_krw=None, fee_sats=None, threshold_krw=None, threshold_sats=None):
        """배송비 설정을 일관되게 업데이트"""
        self.shipping_fee_mode = mode or 'free'

        if self.shipping_fee_mode != 'flat':
            self.shipping_fee_sats = 0
            self.shipping_fee_krw = 0
            self.free_shipping_threshold_krw = None
            self.free_shipping_threshold_sats = None
            return

        self.shipping_fee_krw = fee_krw or 0
        self.shipping_fee_sats = fee_sats or 0

        if threshold_krw:
            self.free_shipping_threshold_krw = threshold_krw
            self.free_shipping_threshold_sats = threshold_sats or 0
        else:
            self.free_shipping_threshold_krw = None
            self.free_shipping_threshold_sats = None

    def shipping_is_free(self):
        """현재 설정 기준으로 배송비가 무료인지 여부"""
        return self.shipping_fee_mode != 'flat' or (self.shipping_fee_sats or 0) == 0

    def get_shipping_fee_sats(self, subtotal_sats=None):
        """주문 합계(사토시)를 기준으로 배송비 계산"""
        if self.shipping_is_free():
            return 0

        threshold_sats = self.free_shipping_threshold_sats or 0
        if subtotal_sats is not None and threshold_sats and subtotal_sats >= threshold_sats:
            return 0

        return self.shipping_fee_sats or 0

    def get_shipping_fee_krw(self, subtotal_krw=None):
        """주문 합계(원화)를 기준으로 배송비 계산"""
        if self.shipping_is_free():
            return 0

        threshold_krw = self.free_shipping_threshold_krw or 0
        if subtotal_krw is not None and threshold_krw and subtotal_krw >= threshold_krw:
            return 0

        return self.shipping_fee_krw or 0

    def get_shipping_fee_display(self):
        """템플릿용 배송비 정보 반환"""
        return {
            'mode': self.shipping_fee_mode,
            'sats': 0 if self.shipping_is_free() else (self.shipping_fee_sats or 0),
            'krw': 0 if self.shipping_is_free() else (self.shipping_fee_krw or 0),
            'threshold_sats': self.free_shipping_threshold_sats,
            'threshold_krw': self.free_shipping_threshold_krw,
        }
    
    @property
    def email_from_display(self):
        """이메일 발신자 표시명 반환 (기본값: 스토어명)"""
        return self.email_from_name or self.store_name
    
    @property
    def store_url(self):
        """스토어 URL 반환"""
        return f"stores/{self.store_id}/"
    
    @property
    def hero_gradient_css(self):
        """히어로 섹션 그라데이션 CSS 반환"""
        return f"linear-gradient(135deg, {self.hero_color1} 0%, {self.hero_color2} 100%)"
    
    @property
    def is_deleted(self):
        """삭제된 스토어인지 확인"""
        return self.deleted_at is not None
    
    def soft_delete(self):
        """소프트 삭제 - 실제로 삭제하지 않고 deleted_at만 설정"""
        from django.utils import timezone
        self.deleted_at = timezone.now()
        self.is_active = False  # 삭제 시 비활성화도 함께
        self.save()
    
    def restore(self):
        """소프트 삭제된 스토어 복원"""
        self.deleted_at = None
        self.save()


class StoreCreationStep(models.Model):
    """스토어 생성 단계 추적"""
    store = models.OneToOneField(Store, on_delete=models.CASCADE, related_name='creation_step')
    current_step = models.IntegerField(default=1, help_text="현재 단계 (1-5)")
    step1_completed = models.BooleanField(default=False)
    step2_completed = models.BooleanField(default=False)
    step3_completed = models.BooleanField(default=False)
    step4_completed = models.BooleanField(default=False)
    step5_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "스토어 생성 단계"
        verbose_name_plural = "스토어 생성 단계들"
        # 성능 최적화를 위한 인덱스 추가
        indexes = [
            models.Index(fields=['store']),      # OneToOne 필드 최적화
            models.Index(fields=['current_step']), # 관리자 필터링용
            models.Index(fields=['created_at']),
            models.Index(fields=['updated_at']),
        ]
    
    def __str__(self):
        return f"{self.store.store_name} - 단계 {self.current_step}"


class ReservedStoreId(models.Model):
    """스토어 아이디 예약어 관리"""
    keyword = models.CharField(
        max_length=50,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z0-9_-]+$',
                message='예약어는 영문, 숫자, 하이픈(-), 언더스코어(_)만 사용 가능합니다.'
            )
        ],
        help_text="사용자가 스토어 아이디로 사용할 수 없는 예약어"
    )
    description = models.CharField(max_length=200, blank=True, help_text="예약어 설명")
    is_active = models.BooleanField(default=True, help_text="예약어 활성화 상태")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, help_text="등록한 관리자")
    
    class Meta:
        verbose_name = "스토어 아이디 예약어"
        verbose_name_plural = "스토어 아이디 예약어들"
        ordering = ['keyword']
        # 성능 최적화를 위한 인덱스 추가
        indexes = [
            models.Index(fields=['keyword']),    # 이미 unique이지만 조회 최적화용
            models.Index(fields=['is_active']),  # 관리자 필터링용
            models.Index(fields=['created_at']), # 관리자 필터링용
            models.Index(fields=['created_by']), # 관리자별 예약어 조회용
            models.Index(fields=['is_active', 'keyword']), # is_reserved 메서드 최적화용
        ]
    
    def __str__(self):
        return self.keyword
    
    @classmethod
    def is_reserved(cls, store_id):
        """주어진 store_id가 예약어인지 확인"""
        return cls.objects.filter(keyword__iexact=store_id, is_active=True).exists()
    
    @classmethod
    def get_reserved_keywords(cls):
        """활성화된 모든 예약어 목록 반환"""
        return list(cls.objects.filter(is_active=True).values_list('keyword', flat=True))


class StoreImage(models.Model):
    """스토어 이미지 모델"""
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='images')
    
    # 이미지 정보
    original_name = models.CharField(max_length=255, verbose_name='원본 파일명')
    file_path = models.CharField(max_length=500, verbose_name='파일 경로')
    file_url = models.URLField(max_length=800, verbose_name='파일 URL')  # S3 URL은 길 수 있음
    file_size = models.PositiveIntegerField(null=True, blank=True, verbose_name='파일 크기 (bytes)')
    
    # 이미지 크기 정보
    width = models.PositiveIntegerField(default=1000, verbose_name='이미지 너비')
    height = models.PositiveIntegerField(default=563, verbose_name='이미지 높이')  # 16:9 비율
    
    # 순서 정보 (이미지 정렬용)
    order = models.PositiveIntegerField(default=0, verbose_name='정렬 순서')
    
    # 메타 정보
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='업로드 시간')
    uploaded_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, verbose_name='업로드 사용자')
    
    class Meta:
        verbose_name = '스토어 이미지'
        verbose_name_plural = '스토어 이미지들'
        ordering = ['order', 'uploaded_at']
        indexes = [
            models.Index(fields=['store', 'order']),
            models.Index(fields=['uploaded_at']),
        ]
    
    def __str__(self):
        return f"{self.store.store_name} - {self.original_name}"
    
    def get_file_size_display(self):
        """파일 크기를 읽기 쉬운 형태로 반환"""
        if not self.file_size:
            return "크기 정보 없음"
        
        for unit in ['bytes', 'KB', 'MB', 'GB']:
            if self.file_size < 1024.0:
                return f"{self.file_size:.1f} {unit}"
            self.file_size /= 1024.0
        return f"{self.file_size:.1f} TB"


class BahPromotionRequest(models.Model):
    """BAH 스토어 홍보 요청 정보"""

    user = models.OneToOneField(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='bah_promotion_request',
    )
    store_name = models.CharField(max_length=120, help_text="매장 이름")
    postal_code = models.CharField(max_length=10, blank=True, help_text="우편번호")
    address = models.CharField(max_length=255, help_text="매장 주소")
    address_detail = models.CharField(max_length=255, blank=True, help_text="상세 주소")
    phone_number = models.CharField(max_length=30, help_text="매장 연락처")
    email = models.EmailField(help_text="홍보 관련 연락 이메일")
    introduction = models.TextField(help_text="매장 소개")
    lightning_public_key = models.CharField(max_length=66, blank=True, help_text="라이트닝 인증 공개키")
    lightning_verified_at = models.DateTimeField(null=True, blank=True, help_text="라이트닝 인증 시각")
    shipping_status = models.CharField(
        max_length=16,
        choices=PROMOTION_STATUS_CHOICES,
        default=PROMOTION_STATUS_PENDING,
        help_text="홍보 패키지 발송 상태",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'BAH 홍보 요청'
        verbose_name_plural = 'BAH 홍보 요청'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['updated_at']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"{self.store_name} ({self.user.username})"

    @property
    def has_lightning_verification(self) -> bool:
        return bool(self.lightning_public_key and self.lightning_verified_at)

    def mark_lightning_verified(self, public_key: str) -> None:
        self.lightning_public_key = public_key
        self.lightning_verified_at = timezone.now()
        self.save(update_fields=['lightning_public_key', 'lightning_verified_at', 'updated_at'])

    def toggle_shipping_status(self) -> None:
        self.shipping_status = (
            PROMOTION_STATUS_SHIPPED
            if self.shipping_status == PROMOTION_STATUS_PENDING
            else PROMOTION_STATUS_PENDING
        )
        self.save(update_fields=['shipping_status', 'updated_at'])


class BahPromotionImage(models.Model):
    """BAH 홍보 요청 이미지"""

    promotion_request = models.ForeignKey(
        BahPromotionRequest,
        on_delete=models.CASCADE,
        related_name='images',
    )
    original_name = models.CharField(max_length=255, verbose_name='원본 파일명')
    file_path = models.CharField(max_length=500, verbose_name='파일 경로')
    file_url = models.URLField(max_length=800, verbose_name='파일 URL')
    file_size = models.PositiveIntegerField(null=True, blank=True, verbose_name='파일 크기 (bytes)')
    width = models.PositiveIntegerField(default=1000, verbose_name='이미지 너비')
    height = models.PositiveIntegerField(default=563, verbose_name='이미지 높이')
    order = models.PositiveIntegerField(default=0, verbose_name='정렬 순서')
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='업로드 시간')
    uploaded_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='업로드 사용자',
    )

    class Meta:
        verbose_name = 'BAH 홍보 이미지'
        verbose_name_plural = 'BAH 홍보 이미지'
        ordering = ['order', 'uploaded_at']
        indexes = [
            models.Index(fields=['promotion_request', 'order']),
            models.Index(fields=['uploaded_at']),
        ]

    def __str__(self):
        return f"{self.promotion_request.store_name} - {self.original_name}"

    def get_file_size_display(self):
        if not self.file_size:
            return "크기 정보 없음"

        size = float(self.file_size)
        for unit in ['bytes', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"


class BahPromotionAdmin(models.Model):
    """BAH 홍보요청 관리자 지정"""

    user = models.OneToOneField('auth.User', on_delete=models.CASCADE, related_name='bah_admin_profile')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'BAH 관리자'
        verbose_name_plural = 'BAH 관리자'

    def __str__(self):
        return self.user.username
