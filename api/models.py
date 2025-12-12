import hashlib
import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone


User = get_user_model()


class ApiKey(models.Model):
    """외부 연동용 API 키 (해시 저장)"""

    name = models.CharField(max_length=100, help_text="키 용도/대상 메모")
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
