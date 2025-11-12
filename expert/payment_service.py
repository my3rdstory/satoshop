from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.text import slugify

from ln_payment.blink_service import BlinkAPIService

from .constants import DIRECT_CONTRACT_SESSION_PREFIX, ROLE_LABELS
from .models import ContractPricingSetting, DirectContractDocument, DirectContractStageLog

SESSION_KEY = "expert_payment_states"
PAYMENT_EXPIRE_SECONDS = 60


class ExpertPaymentError(Exception):
    """기본 결제 오류."""


class ExpertPaymentConfigurationError(ExpertPaymentError):
    """환경 변수나 자격 정보가 누락된 경우."""


@dataclass
class PaymentState:
    status: str = "idle"
    amount_sats: int = 0
    payment_hash: str = ""
    payment_request: str = ""
    expires_at: Optional[timezone.datetime] = None
    message: str = ""
    last_error: str = ""
    paid_at: Optional[timezone.datetime] = None

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> "PaymentState":
        if not data:
            return cls()
        expires_at = _parse_dt(data.get("expires_at"))
        paid_at = _parse_dt(data.get("paid_at"))
        return cls(
            status=data.get("status", "idle"),
            amount_sats=int(data.get("amount_sats", 0) or 0),
            payment_hash=data.get("payment_hash", ""),
            payment_request=data.get("payment_request", ""),
            expires_at=expires_at,
            message=data.get("message", ""),
            last_error=data.get("last_error", ""),
            paid_at=paid_at,
        )

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "amount_sats": self.amount_sats,
            "payment_hash": self.payment_hash,
            "payment_request": self.payment_request,
            "expires_at": _format_dt(self.expires_at),
            "message": self.message,
            "last_error": self.last_error,
            "paid_at": _format_dt(self.paid_at),
        }


@dataclass
class PaymentWidgetContext:
    dom_id: str
    context_type: str
    identifier: str
    role: str
    role_label: str
    pricing: Optional[ContractPricingSetting]
    required_amount: int
    requires_payment: bool
    state: PaymentState

    @property
    def countdown_seconds(self) -> int:
        if not self.state.expires_at:
            return 0
        remaining = int((self.state.expires_at - timezone.now()).total_seconds())
        return max(0, remaining)

    @property
    def status_message(self) -> str:
        if not self.requires_payment:
            return "현재 정책에서는 결제가 필요하지 않습니다."
        if self.state.status == "paid":
            return "결제가 완료되었습니다."
        if self.state.status == "invoice":
            return self.state.message or "인보이스를 생성했습니다. 결제를 진행해 주세요."
        if self.state.status == "expired":
            return "인보이스가 만료되었습니다. 다시 생성해 주세요."
        if self.state.status == "error":
            return self.state.last_error or "결제를 준비하는 중 문제가 발생했습니다."
        if self.state.status == "cancelled":
            return "인보이스를 취소했습니다. 다시 시도할 수 있습니다."
        return "결제 시작 버튼을 누르면 QR이 생성됩니다."

    @property
    def widget_urls(self) -> dict:
        return {
            "start": reverse("expert:direct-payment-start"),
            "cancel": reverse("expert:direct-payment-cancel"),
            "status": reverse("expert:direct-payment-status"),
            "refresh": reverse("expert:direct-payment-widget"),
        }


def get_active_pricing() -> Optional[ContractPricingSetting]:
    return ContractPricingSetting.objects.filter(enabled=True).order_by("-pk").first()


def get_required_amount(pricing: Optional[ContractPricingSetting], role: str) -> int:
    if not pricing or not pricing.enabled:
        return 0
    if role == "performer":
        return pricing.performer_fee_sats
    return pricing.client_fee_sats


def requires_payment(pricing: Optional[ContractPricingSetting], role: str) -> bool:
    return get_required_amount(pricing, role) > 0


def get_role_label(role: str) -> str:
    return ROLE_LABELS.get(role, role)


def build_dom_id(context_type: str, identifier: str, role: str) -> str:
    safe_identifier = slugify(identifier) or "ref"
    return f"lightning-payment-{context_type}-{role}-{safe_identifier}"[:64]


def build_payment_key(context_type: str, identifier: str, role: str) -> str:
    return f"{context_type}:{identifier}:{role}"


def get_payment_state(request, context_type: str, identifier: str, role: str) -> PaymentState:
    key = build_payment_key(context_type, identifier, role)
    return PaymentState.from_dict(request.session.get(SESSION_KEY, {}).get(key))


def store_payment_state(request, context_type: str, identifier: str, role: str, state: PaymentState) -> None:
    key = build_payment_key(context_type, identifier, role)
    payload = request.session.get(SESSION_KEY, {})
    payload[key] = state.to_dict()
    request.session[SESSION_KEY] = payload
    request.session.modified = True


def clear_payment_state(request, context_type: str, identifier: str, role: str) -> None:
    key = build_payment_key(context_type, identifier, role)
    payload = request.session.get(SESSION_KEY, {})
    if key in payload:
        payload.pop(key)
        request.session[SESSION_KEY] = payload
        request.session.modified = True


def mark_payment_paid(request, context_type: str, identifier: str, role: str) -> PaymentState:
    state = get_payment_state(request, context_type, identifier, role)
    state.status = "paid"
    state.message = "결제를 확인했습니다."
    state.paid_at = timezone.now()
    store_payment_state(request, context_type, identifier, role, state)
    _persist_payment_receipt(
        context_type=context_type,
        identifier=identifier,
        role=role,
        receipt_state=state,
    )
    return state


def build_widget_context(
    request,
    *,
    context_type: str,
    identifier: str,
    role: str,
    role_label: Optional[str] = None,
) -> PaymentWidgetContext:
    pricing = get_active_pricing()
    amount = get_required_amount(pricing, role)
    state = get_payment_state(request, context_type, identifier, role)
    needs_payment = bool(pricing and pricing.enabled and amount > 0)
    if not needs_payment:
        state.status = "paid"
    else:
        receipt = _load_persisted_payment_receipt(context_type, identifier, role)
        if receipt and state.status != "paid":
            state.status = "paid"
            state.message = "결제를 확인했습니다."
            state.payment_hash = receipt.get("payment_hash", "")
            state.paid_at = _parse_dt(receipt.get("paid_at")) or timezone.now()
    dom_id = build_dom_id(context_type, identifier, role)
    return PaymentWidgetContext(
        dom_id=dom_id,
        context_type=context_type,
        identifier=identifier,
        role=role,
        role_label=role_label or get_role_label(role),
        pricing=pricing,
        required_amount=amount,
        requires_payment=needs_payment,
        state=state,
    )


def get_blink_service() -> BlinkAPIService:
    api_key = getattr(settings, "EXPERT_BLINK_API_KEY", None)
    wallet_id = getattr(settings, "EXPERT_BLINK_WALLET_ID", None)
    if not api_key or not wallet_id:
        raise ExpertPaymentConfigurationError("Blink API 자격 정보가 설정되지 않았습니다.")
    return BlinkAPIService(api_key=api_key, wallet_id=wallet_id, api_url=settings.BLINK_API_URL)


def _parse_dt(value: Optional[str]) -> Optional[timezone.datetime]:
    if not value:
        return None
    dt = parse_datetime(value)
    if not dt:
        return None
    if timezone.is_naive(dt):
        return timezone.make_aware(dt, timezone=timezone.utc)
    return dt


def _format_dt(value: Optional[timezone.datetime]) -> Optional[str]:
    if not value:
        return None
    if timezone.is_naive(value):
        value = timezone.make_aware(value, timezone=timezone.utc)
    return value.isoformat()


def ensure_draft_payload(request, token: str) -> Optional[dict]:
    session_key = f"{DIRECT_CONTRACT_SESSION_PREFIX}:{token}"
    return request.session.get(session_key)


def _persist_payment_receipt(*, context_type: str, identifier: str, role: str, receipt_state: PaymentState) -> None:
    if receipt_state.status != "paid":
        return
    receipt = {
        "amount_sats": receipt_state.amount_sats,
        "paid_at": _format_dt(receipt_state.paid_at) or _format_dt(timezone.now()),
        "payment_hash": receipt_state.payment_hash,
        "payment_request": receipt_state.payment_request,
    }
    if context_type == "draft":
        log = (
            DirectContractStageLog.objects.filter(stage="draft", token=identifier)
            .order_by("started_at")
            .first()
        )
        if log:
            meta = log.meta or {}
            existing = meta.get("payment", {})
            if existing != receipt:
                meta["payment"] = receipt
                log.meta = meta
                log.save(update_fields=["meta"])
        return
    if context_type == "invite":
        document = DirectContractDocument.objects.filter(slug=identifier).first()
        if not document:
            return
        payment_meta = document.payment_meta or {}
        if payment_meta.get(role) == receipt:
            return
        payment_meta[role] = receipt
        document.payment_meta = payment_meta
        document.save(update_fields=["payment_meta", "updated_at"])


def _load_persisted_payment_receipt(context_type: str, identifier: str, role: str) -> Optional[dict]:
    if context_type == "draft":
        log = (
            DirectContractStageLog.objects.filter(stage="draft", token=identifier)
            .order_by("started_at")
            .first()
        )
        if log:
            return (log.meta or {}).get("payment")
        return None
    document = DirectContractDocument.objects.filter(slug=identifier).first()
    if not document:
        return None
    return (document.payment_meta or {}).get(role)
