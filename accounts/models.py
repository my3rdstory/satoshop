import secrets
import string
import time

from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from stores.models import Store
from orders.models import Order
from meetup.models import MeetupOrder
from lecture.models import LiveLectureOrder
from file.models import FileOrder

PUBLIC_ID_ALPHABET = string.digits + string.ascii_lowercase


def _to_base36(number: int) -> str:
    if number == 0:
        return '0'

    digits = []
    while number:
        number, remainder = divmod(number, 36)
        digits.append(PUBLIC_ID_ALPHABET[remainder])
    return ''.join(reversed(digits))


def generate_public_id(length: int = 27) -> str:
    """
    URL-safe, 시간 축이 섞인 CUID 스타일 공개 ID 생성.
    내부 PK와 별개로 외부 노출용 식별자에 사용한다.
    """
    timestamp = int(time.time() * 1000)
    ts_part = _to_base36(timestamp)
    random_length = max(length - len(ts_part) - 1, 8)
    random_part = ''.join(secrets.choice(PUBLIC_ID_ALPHABET) for _ in range(random_length))
    return f"c{ts_part}{random_part}"[:length]


class LightningUser(models.Model):
    """라이트닝 사용자 - 공개키와 Django User 연결"""
    
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE, related_name='lightning_profile')
    public_key = models.CharField(max_length=66, unique=True, help_text="라이트닝 공개키 (hex)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'accounts_lightning_user'
        indexes = [
            models.Index(fields=['public_key']),
        ]
    
    def __str__(self):
        return f"{self.user.username} ({self.public_key[:16]}...)"
    
    def update_last_login(self):
        """마지막 로그인 시간 업데이트"""
        self.last_login_at = timezone.now()
        self.save(update_fields=['last_login_at'])
    
    @classmethod
    def get_or_create_from_pubkey(cls, public_key):
        """공개키로 사용자 조회 또는 생성"""
        try:
            lightning_user = cls.objects.get(public_key=public_key)
            lightning_user.update_last_login()
            return lightning_user.user, False  # 기존 사용자
        except cls.DoesNotExist:
            # 새 사용자 생성
            from django.contrib.auth.models import User
            
            # 공개키 앞 16자를 사용자명으로 사용 (중복 방지)
            base_username = f"ln_{public_key[:16]}"
            username = base_username
            counter = 1
            
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1
            
            user = User.objects.create_user(
                username=username,
                password=None  # 패스워드 없음
            )
            
            lightning_user = cls.objects.create(
                user=user,
                public_key=public_key
            )
            lightning_user.update_last_login()
            
            return user, True  # 새 사용자


from django.contrib.auth.models import User as DjangoUser


class UserPublicId(models.Model):
    """외부 노출용 공개 ID (CUID 스타일)"""

    user = models.OneToOneField(DjangoUser, on_delete=models.CASCADE, related_name='public_identity')
    public_id = models.CharField(max_length=27, unique=True, default=generate_public_id, help_text="외부 노출용 CUID")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'accounts_user_public_id'
        verbose_name = '사용자 공개 ID'
        verbose_name_plural = '사용자 공개 ID'

    def __str__(self):
        return f"{self.user.username} 공개 ID"

    @classmethod
    def ensure_for_user(cls, user: DjangoUser):
        """주어진 사용자에 대한 공개 ID가 없으면 생성 후 반환"""
        obj, _ = cls.objects.get_or_create(user=user, defaults={'public_id': generate_public_id()})
        return obj


class TemporaryPassword(models.Model):
    """어드민에서 설정하는 임시 비밀번호 정보를 저장"""

    user = models.OneToOneField(DjangoUser, on_delete=models.CASCADE, related_name='temporary_password_credential')
    password = models.CharField(max_length=128, blank=True, default='')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'accounts_temporary_password'
        verbose_name = '임시 비밀번호'
        verbose_name_plural = '임시 비밀번호'

    def __str__(self):
        return f"{self.user.username} 임시 비밀번호"

    def set_password(self, raw_password: str | None):
        """입력값을 해시로 저장하거나 비워 임시 비밀번호를 제거"""
        if raw_password:
            self.password = make_password(raw_password)
        else:
            self.password = ''

    def check_password(self, raw_password: str | None) -> bool:
        """입력값이 임시 비밀번호 해시와 일치하는지 확인"""
        if not raw_password or not self.password:
            return False
        return check_password(raw_password, self.password)

    def clear(self):
        self.password = ''


@receiver(post_save, sender=DjangoUser)
def create_public_id_profile(sender, instance, created, **kwargs):
    """새 사용자 생성 시 공개 ID를 자동 부여"""
    if created:
        UserPublicId.objects.get_or_create(user=instance)


class UserPurchaseHistory(DjangoUser):
    """사용자 구매 내역 조회용 Proxy 모델"""
    class Meta:
        proxy = True
        verbose_name = '사용자별 구매 내역'
        verbose_name_plural = '사용자별 구매 내역'


class UserMyPageHistory(DjangoUser):
    """마이페이지 이력 조회용 Proxy 모델"""
    class Meta:
        proxy = True
        verbose_name = '사용자 마이페이지 이력'
        verbose_name_plural = '사용자 마이페이지 이력'


class OrderCleanupProxy(Order):
    """어드민에서 주문 내역 정리용 Proxy"""

    class Meta:
        proxy = True
        verbose_name = '스토어 구입 이력'
        verbose_name_plural = '스토어 구입 이력'


class MeetupOrderCleanupProxy(MeetupOrder):
    """어드민에서 밋업 주문 정리용 Proxy"""

    class Meta:
        proxy = True
        verbose_name = '밋업 구입 이력'
        verbose_name_plural = '밋업 구입 이력'


class LiveLectureOrderCleanupProxy(LiveLectureOrder):
    """어드민에서 라이브 강의 주문 정리용 Proxy"""

    class Meta:
        proxy = True
        verbose_name = '라이브 강의 구입 이력'
        verbose_name_plural = '라이브 강의 구입 이력'


class FileOrderCleanupProxy(FileOrder):
    """어드민에서 디지털 파일 주문 정리용 Proxy"""

    class Meta:
        proxy = True
        verbose_name = '디지털 파일 구입 이력'
        verbose_name_plural = '디지털 파일 구입 이력'
