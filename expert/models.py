import uuid
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from myshop.models import SiteSettings

User = get_user_model()


class Contract(models.Model):
    """전자 계약 기본 정보."""

    STATUS_CHOICES = [
        ("draft", "작성 중"),
        ("pending_counterparty", "상대방 확인 대기"),
        ("awaiting_signature", "서명 대기"),
        ("signed", "서명 완료"),
        ("payment_pending", "지급 진행 중"),
        ("completed", "완료"),
        ("cancelled", "취소"),
    ]

    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    title = models.CharField(max_length=150)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="draft")
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="contracts_created",
    )
    chat_archive = models.FileField(
        upload_to="contracts/chat_archives/",
        blank=True,
        null=True,
        help_text="채팅 기록을 PDF로 저장한 파일",
    )
    archive_generated_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    @property
    def channel_group_name(self) -> str:
        return f"contract-chat-{self.public_id}"

    def mark_archive_generated(self, file_path: str):
        self.chat_archive.name = file_path
        self.archive_generated_at = timezone.now()
        self.save(update_fields=["chat_archive", "archive_generated_at", "updated_at"])


class ContractParticipant(models.Model):
    """계약 참여자(의뢰자/수행자)."""

    ROLE_CHOICES = [
        ("client", "의뢰자"),
        ("performer", "수행자"),
    ]

    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name="participants",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="expert_contract_participations",
    )
    role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    lightning_identifier = models.CharField(
        max_length=128,
        help_text="라이트닝 인증 결과(아이디 등)를 저장",
    )
    is_confirmed = models.BooleanField(default=False)
    signed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("contract", "user")

    def __str__(self):
        return f"{self.contract.title} - {self.get_role_display()} ({self.user})"


class ContractMessage(models.Model):
    """계약별 실시간 채팅 메시지."""

    MESSAGE_TYPE_CHOICES = [
        ("text", "텍스트"),
        ("system", "시스템"),
    ]

    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contract_messages",
    )
    sender_role = models.CharField(
        max_length=16,
        choices=ContractParticipant.ROLE_CHOICES,
        blank=True,
    )
    message_type = models.CharField(
        max_length=16,
        choices=MESSAGE_TYPE_CHOICES,
        default="text",
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        prefix = self.sender or "시스템"
        return f"[{self.created_at}] {prefix}: {self.content[:40]}"


class ContractEmailLog(models.Model):
    """계약과 관련된 이메일 발송 내역을 기록."""

    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name="email_logs",
    )
    recipients = models.TextField(help_text="쉼표로 구분된 수신자 이메일")
    subject = models.CharField(max_length=140)
    message = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-sent_at"]

    def __str__(self):
        return f"{self.contract.title} - {self.subject} ({self.sent_at:%Y-%m-%d %H:%M})"


class ExpertEmailSettings(SiteSettings):
    """SiteSettings를 Expert 카테고리에서 관리하기 위한 프록시 모델."""

    class Meta:
        proxy = True
        app_label = "expert"
        verbose_name = "Expert 계약 이메일 설정"
        verbose_name_plural = "Expert 계약 이메일 설정"

# Create your models here.
