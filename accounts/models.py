from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from datetime import timedelta
import uuid


class LNURLAuth(models.Model):
    """LNURL-auth 인증 세션"""
    
    # 세션 식별자
    k1 = models.CharField(max_length=64, unique=True, help_text="LNURL-auth k1 파라미터")
    session_id = models.UUIDField(default=uuid.uuid4, unique=True, help_text="세션 UUID")
    
    # 인증 데이터
    public_key = models.CharField(max_length=66, blank=True, help_text="사용자 공개키 (hex)")
    signature = models.CharField(max_length=128, blank=True, help_text="서명 (hex)")
    
    # 상태 관리
    is_verified = models.BooleanField(default=False, help_text="서명 검증 완료 여부")
    is_used = models.BooleanField(default=False, help_text="인증 사용 여부")
    
    # 사용자 정보 (인증 완료 후 설정됨)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, null=True, blank=True, help_text="인증된 사용자")
    
    # 시간 정보
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(help_text="만료 시간")
    verified_at = models.DateTimeField(null=True, blank=True, help_text="검증 완료 시간")
    used_at = models.DateTimeField(null=True, blank=True, help_text="인증 사용 시간")
    
    class Meta:
        db_table = 'accounts_lnurl_auth'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['k1']),
            models.Index(fields=['session_id']),
            models.Index(fields=['public_key']),
            models.Index(fields=['is_verified', 'is_used']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"LNURL Auth {self.session_id}"
    
    @property
    def is_expired(self):
        """만료 여부 확인"""
        return timezone.now() > self.expires_at
    
    @property
    def is_valid(self):
        """유효한 인증 세션인지 확인"""
        return self.is_verified and not self.is_used and not self.is_expired
    
    def mark_as_verified(self, public_key, signature):
        """검증 완료로 마킹"""
        self.public_key = public_key
        self.signature = signature
        self.is_verified = True
        self.verified_at = timezone.now()
        self.save(update_fields=['public_key', 'signature', 'is_verified', 'verified_at'])
    
    def mark_as_used(self):
        """인증 사용 완료로 마킹"""
        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=['is_used', 'used_at'])
    
    @classmethod
    def create_auth_session(cls, expires_in_minutes=10):
        """새로운 LNURL-auth 세션 생성"""
        import secrets
        
        k1 = secrets.token_hex(32)  # 64자 hex 문자열
        expires_at = timezone.now() + timedelta(minutes=expires_in_minutes)
        
        return cls.objects.create(
            k1=k1,
            expires_at=expires_at
        )
    
    @classmethod
    def cleanup_expired(cls):
        """만료된 인증 세션 정리"""
        expired_sessions = cls.objects.filter(
            expires_at__lt=timezone.now(),
            is_used=False
        )
        count = expired_sessions.count()
        expired_sessions.delete()
        return count


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
