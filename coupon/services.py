"""임시 쿠폰 페이지에서 라이트닝 인보이스를 발행하기 위한 유틸리티."""

from dataclasses import dataclass
from typing import List

from django.conf import settings

from ln_payment.blink_service import BlinkAPIService


SERVICE_FEE_SATS = 5
MAX_COUPON_AMOUNT = 10_000
PRESET_AMOUNTS: List[int] = [5, 10, 21, 103, 210]


class BlinkCredentialError(RuntimeError):
    """Blink API 자격 정보 누락 시 발생하는 예외."""


@dataclass(frozen=True)
class CouponInvoiceConfig:
    """템플릿에서 사용할 쿠폰 기본 설정."""

    service_fee: int = SERVICE_FEE_SATS
    max_amount: int = MAX_COUPON_AMOUNT
    presets: List[int] = None

    def __post_init__(self):
        if self.presets is None:
            object.__setattr__(self, "presets", PRESET_AMOUNTS)


def get_coupon_blink_service() -> BlinkAPIService:
    """환경 변수 기반 Blink API 서비스 생성."""
    api_key = getattr(settings, "COUPON_BLINK_API_KEY", None)
    wallet_id = getattr(settings, "COUPON_BLINK_WALLET_ID", None)

    if not api_key or not wallet_id:
        raise BlinkCredentialError("Blink API 자격 정보를 찾을 수 없습니다.")

    return BlinkAPIService(
        api_key=api_key,
        wallet_id=wallet_id,
        api_url=settings.BLINK_API_URL,
    )


def clamp_amount(amount: int) -> int:
    """입력된 수량을 허용 범위 내로 제한."""
    return max(1, min(amount, MAX_COUPON_AMOUNT))


def calculate_invoice_amount(requested_amount: int) -> int:
    """쿠폰 수량에 수수료를 더한 인보이스 실결제 금액 계산."""
    return clamp_amount(requested_amount) + SERVICE_FEE_SATS
