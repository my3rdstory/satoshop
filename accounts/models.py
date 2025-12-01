from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone


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
