import uuid
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone
from django.core.files.storage import default_storage
from storage.backends import S3Storage

from myshop.models import SiteSettings
from .signature_assets import resolve_signature_url
from .utils import calculate_sha256_from_field_file


class ExpertHeroSlide(models.Model):
    """Expert 랜딩 페이지 캐러셀 슬라이드."""

    name = models.CharField(max_length=120, verbose_name="슬라이드 이름")
    content_html = models.TextField(
        verbose_name="콘텐츠 HTML",
        help_text="Django 템플릿 문법과 HTML을 함께 사용할 수 있습니다.",
    )
    background_css = models.TextField(
        blank=True,
        verbose_name="배경 CSS",
        help_text="background, gradient 등 CSS 선언 전체를 입력하세요.",
    )
    background_image = models.ImageField(
        upload_to="expert/hero/backgrounds/",
        blank=True,
        null=True,
        verbose_name="배경 이미지",
    )
    overlay_color = models.CharField(
        max_length=120,
        blank=True,
        verbose_name="오버레이 색상",
        help_text="rgba(2, 6, 23, 0.65) 와 같은 형식을 권장합니다.",
    )
    rotation_seconds = models.PositiveIntegerField(default=6, verbose_name="자동 전환 간격(초)")
    order = models.PositiveIntegerField(default=0, db_index=True, verbose_name="표시 순서")
    is_active = models.BooleanField(default=True, verbose_name="활성화")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")

    class Meta:
        ordering = ["order", "-updated_at"]
        verbose_name = "Expert 히어로 슬라이드"
        verbose_name_plural = "Expert 히어로 슬라이드"
        indexes = [
            models.Index(fields=["is_active", "order"], name="expert_hero_active_order"),
        ]

    def __str__(self):  # pragma: no cover - admin display helper
        return self.name

    @property
    def overlay_style(self) -> str:
        return self.overlay_color or "rgba(2, 6, 23, 0.65)"

    @property
    def background_style(self) -> str:
        declarations: list[str] = []
        if self.background_css:
            css = " ".join(part.strip() for part in self.background_css.splitlines() if part.strip())
            declarations.append(css if css.endswith(";") else f"{css};")
        if self.background_image:
            try:
                declarations.append(
                    "background-image: url('{url}'); background-size: cover; "
                    "background-position: center; background-repeat: no-repeat;".format(
                        url=self.background_image.url
                    )
                )
            except ValueError:
                pass
        if not declarations:
            declarations.append(
                "background: radial-gradient(circle at top left, rgba(255, 184, 0, 0.35), transparent 45%), "
                "radial-gradient(circle at bottom right, rgba(56, 189, 248, 0.25), transparent 50%), "
                "linear-gradient(135deg, #0f172a, #111827 55%, #020617 100%);"
            )
        return " ".join(declarations)

try:
    CONTRACT_FILE_STORAGE = S3Storage()
except Exception:  # pragma: no cover
    CONTRACT_FILE_STORAGE = default_storage

User = get_user_model()


class ContractTemplate(models.Model):
    """거래 계약서 버전을 저장하고 하나만 노출 대상으로 선택."""

    title = models.CharField(max_length=120, help_text="계약서 이름 (예: 표준 직거래 계약서)")
    version_label = models.CharField(
        max_length=80,
        help_text="버전/개정 정보 (예: 2024.05 신의성실 개정판)",
    )
    content = models.TextField(help_text="계약 본문을 마크다운(MD) 형식으로 작성합니다.")
    is_selected = models.BooleanField(
        default=False,
        help_text="계약 조건 입력 화면에서 노출할 계약서라면 체크하세요. 동시에 하나만 선택됩니다.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "거래 계약서"
        verbose_name_plural = "거래 계약서"
        constraints = [
            models.UniqueConstraint(
                fields=["is_selected"],
                condition=Q(is_selected=True),
                name="expert_single_selected_contract_template",
            )
        ]

    def __str__(self):
        return f"{self.title} ({self.version_label})"

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.is_selected:
                ContractTemplate.objects.exclude(pk=self.pk).filter(is_selected=True).update(is_selected=False)
            super().save(*args, **kwargs)


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


def default_email_delivery():
    return {"creator": None, "counterparty": None}


class DirectContractDocument(models.Model):
    """직접 계약 생성 플로우에서 사용되는 계약 문서."""

    STATUS_CHOICES = [
        ("pending_counterparty", "상대방 입력 대기"),
        ("counterparty_in_progress", "상대방 진행 중"),
        ("completed", "계약 완료"),
    ]

    slug = models.SlugField(max_length=32, unique=True)
    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="direct_contracts_created",
    )
    payload = models.JSONField(help_text="계약 입력값 전체 스냅샷(JSON).")
    payment_meta = models.JSONField(default=dict, blank=True, help_text="단계별 라이트닝 결제 정보")
    creator_role = models.CharField(max_length=16, choices=ContractParticipant.ROLE_CHOICES)
    counterparty_role = models.CharField(max_length=16, choices=ContractParticipant.ROLE_CHOICES)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="pending_counterparty", db_index=True)
    creator_email = models.EmailField(blank=True)
    counterparty_email = models.EmailField(blank=True)
    counterparty_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="direct_contracts_signed",
    )
    creator_signature = models.ImageField(
        upload_to="contracts/signatures/",
        blank=True,
        storage=CONTRACT_FILE_STORAGE,
    )
    counterparty_signature = models.ImageField(
        upload_to="contracts/signatures/",
        blank=True,
        storage=CONTRACT_FILE_STORAGE,
    )
    creator_signed_at = models.DateTimeField(blank=True, null=True)
    counterparty_signed_at = models.DateTimeField(blank=True, null=True)
    creator_hash = models.CharField(max_length=64, blank=True)
    counterparty_hash = models.CharField(max_length=64, blank=True)
    mediator_hash = models.CharField(max_length=64, blank=True)
    creator_hash_meta = models.JSONField(default=dict, blank=True)
    counterparty_hash_meta = models.JSONField(default=dict, blank=True)
    mediator_hash_meta = models.JSONField(default=dict, blank=True)
    creator_lightning_id = models.CharField(max_length=160, blank=True, db_index=True)
    counterparty_lightning_id = models.CharField(max_length=160, blank=True, db_index=True)
    email_delivery = models.JSONField(default=default_email_delivery, blank=True)
    final_pdf = models.FileField(
        upload_to="expert/contracts/final_pdfs/",
        blank=True,
        storage=CONTRACT_FILE_STORAGE,
    )
    final_pdf_generated_at = models.DateTimeField(blank=True, null=True)
    final_pdf_hash = models.CharField(max_length=64, blank=True)
    signature_assets = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["creator", "-created_at"], name="doc_creator_created_idx"),
            models.Index(fields=["counterparty_user", "-created_at"], name="doc_counterparty_created_idx"),
        ]

    def __str__(self):
        return f"{self.payload.get('title', '계약')} ({self.slug})"

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("expert:direct-invite", kwargs={"slug": self.slug})

    def set_signature_asset(self, role: str, asset: dict, save: bool = True):
        assets = {**(self.signature_assets or {})}
        assets[role] = asset
        self.signature_assets = assets
        if save:
            self.save(update_fields=["signature_assets", "updated_at"])

    def get_signature_asset(self, role: str) -> dict:
        return (self.signature_assets or {}).get(role, {})

    def get_signature_url(self, role: str) -> str:
        asset = self.get_signature_asset(role)
        url = resolve_signature_url(asset)
        return url or ""

    def clear_signature_file(self, role: str, save: bool = True):
        field_name = "creator_signature" if role == "creator" else "counterparty_signature"
        file_field = getattr(self, field_name, None)
        if file_field and file_field.name:
            file_field.delete(save=False)
        setattr(self, field_name, "")
        if save:
            self.save(update_fields=[field_name, "updated_at"])

    def refresh_final_pdf_hash(self, save: bool = True) -> str:
        """Recompute the stored final PDF hash from the file storage."""

        self.final_pdf_hash = calculate_sha256_from_field_file(self.final_pdf)
        if save:
            self.save(update_fields=["final_pdf_hash", "updated_at"])
        return self.final_pdf_hash

    def get_finalized_at(self):
        """가장 최근 서명/최종 PDF 생성 시각을 리턴."""

        timestamps = []
        for value in (
            self.final_pdf_generated_at,
            self.counterparty_signed_at,
            self.creator_signed_at,
        ):
            if not value:
                continue
            localized = timezone.localtime(value) if timezone.is_aware(value) else value
            timestamps.append(localized)
        return max(timestamps) if timestamps else None


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

class DirectContractStageLog(models.Model):
    """직접 계약 진행 단계 로그."""

    STAGE_CHOICES = [
        ("draft", "드래프트"),
        ("role_one", "역할 1 서명"),
        ("role_two", "역할 2 서명"),
        ("completed", "계약 완료"),
    ]

    document = models.ForeignKey(
        DirectContractDocument,
        on_delete=models.CASCADE,
        related_name="stage_logs",
        null=True,
        blank=True,
    )
    token = models.CharField(max_length=64, blank=True, db_index=True)
    stage = models.CharField(max_length=32, choices=STAGE_CHOICES)
    started_at = models.DateTimeField(auto_now_add=True)
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["started_at"]
        verbose_name = "직접 계약 단계 로그"
        verbose_name_plural = "직접 계약 단계 로그"

    def __str__(self):
        target = self.document.slug if self.document else self.token or "-"
        return f"{self.get_stage_display()} @ {target}"


class ContractPricingSetting(models.Model):
    """직접 계약 유료화 정책(사토시 금액)을 저장."""

    name = models.CharField(
        max_length=50,
        unique=True,
        default="default",
        help_text="여러 설정을 둘 수 있도록 식별자(기본값은 'default').",
    )
    enabled = models.BooleanField(
        default=False,
        help_text="활성화 시 계약 진행 전에 설정된 금액 결제가 필요하다는 정책을 안내합니다.",
    )
    client_fee_sats = models.PositiveIntegerField(
        default=0,
        help_text="의뢰자가 부담해야 하는 사토시 금액. 0이면 무료.",
    )
    performer_fee_sats = models.PositiveIntegerField(
        default=0,
        help_text="수행자가 부담해야 하는 사토시 금액. 0이면 무료.",
    )


class ExpertBlinkRevenueStats(DirectContractDocument):
    class Meta:
        proxy = True
        verbose_name = "Blink 수수료 통계"
        verbose_name_plural = "Blink 수수료 통계"


class ExpertUsageStats(DirectContractDocument):
    class Meta:
        proxy = True
        verbose_name = "Expert 사용 통계"
        verbose_name_plural = "Expert 사용 통계"
