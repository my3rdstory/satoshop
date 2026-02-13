import hashlib
import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.core.validators import URLValidator


User = get_user_model()


class ApiKey(models.Model):
    """외부 연동용 API 키 (해시 저장)"""

    AUTH_METHOD_API_KEY = "api_key"
    AUTH_METHOD_NOSTR = "nostr"
    AUTH_METHOD_CHOICES = (
        (AUTH_METHOD_API_KEY, "기존 API 키(Bearer)"),
        (AUTH_METHOD_NOSTR, "Nostr 공개키 서명"),
    )

    name = models.CharField(max_length=100, help_text="키 용도/대상 메모")
    channel_slug = models.SlugField(
        max_length=50,
        blank=True,
        help_text="채널 구분 슬러그(예: partner-a, ios-app). 주문/집계용",
    )
    key_prefix = models.CharField(
        max_length=16,
        db_index=True,
        help_text="키 앞 16자. 원문 키는 저장하지 않음.",
    )
    key_hash = models.CharField(
        max_length=128,
        unique=True,
        help_text="SHA256 해시. 원문 키는 저장하지 않음.",
    )
    scopes = models.CharField(
        max_length=200,
        default="stores:read",
        help_text="허용 스코프(콤마 구분). 기본은 stores:read",
    )
    auth_method = models.CharField(
        max_length=20,
        choices=AUTH_METHOD_CHOICES,
        default=AUTH_METHOD_API_KEY,
        db_index=True,
        help_text="인증 방식 선택. Nostr 선택 시 Bearer 키 대신 Nostr 서명 검증 사용",
    )
    nostr_pubkey = models.CharField(
        max_length=64,
        blank=True,
        default="",
        db_index=True,
        help_text="Nostr 인증용 공개키(32바이트 hex). auth_method=nostr 일 때 필수",
    )
    is_active = models.BooleanField(default=True, help_text="비활성화 시 403 반환")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_api_keys",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "API 키"
        verbose_name_plural = "API 키"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["key_prefix"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.key_prefix})"

    @property
    def uses_nostr_auth(self) -> bool:
        return self.auth_method == self.AUTH_METHOD_NOSTR

    def clean(self):
        super().clean()
        if self.uses_nostr_auth and not self.nostr_pubkey:
            raise ValidationError({"nostr_pubkey": "Nostr 인증을 선택하면 공개키 입력이 필요합니다."})

    @staticmethod
    def generate_raw_key() -> str:
        """원문 키를 생성 (URL-safe)."""
        return secrets.token_urlsafe(40)

    @staticmethod
    def hash_key(raw_key: str) -> str:
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def set_key(self, raw_key: str) -> None:
        """원문 키를 받아 prefix/해시 필드를 채운다."""
        if not raw_key:
            raise ValueError("빈 키는 저장할 수 없습니다.")
        self.key_prefix = raw_key[:16]
        self.key_hash = self.hash_key(raw_key)

    def check_key(self, raw_key: str) -> bool:
        """입력 키가 저장된 해시와 일치하는지 확인."""
        if not raw_key:
            return False
        return self.key_hash == self.hash_key(raw_key)

    def touch_last_used(self) -> None:
        """마지막 사용 시각 기록."""
        self.last_used_at = timezone.now()
        self.save(update_fields=["last_used_at", "updated_at"])


class ApiIpAllowlist(models.Model):
    """API 접근 허용 IP/CIDR"""

    name = models.CharField(max_length=100, help_text="설명용 이름")
    cidr = models.CharField(
        max_length=64,
        help_text="IPv4/IPv6 주소 또는 CIDR (예: 203.0.113.0/24)",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "API IP 허용 목록"
        verbose_name_plural = "API IP 허용 목록"
        ordering = ["cidr"]
        indexes = [
            models.Index(fields=["cidr"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.cidr})"


class ApiAllowedOrigin(models.Model):
    """API CORS 허용 Origin"""

    name = models.CharField(max_length=100, help_text="설명용 이름")
    origin = models.CharField(
        max_length=200,
        help_text="스킴 포함 Origin (예: https://example.com:8443)",
        validators=[URLValidator(schemes=["http", "https"])],
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "API 허용 Origin"
        verbose_name_plural = "API 허용 Origin"
        ordering = ["origin"]
        indexes = [
            models.Index(fields=["origin"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.origin})"
