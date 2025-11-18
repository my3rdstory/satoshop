import json

from django.http import JsonResponse
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.views import View
from django.views.generic import TemplateView

from .services import (
    BlinkCredentialError,
    CouponInvoiceConfig,
    calculate_invoice_amount,
    clamp_amount,
    get_coupon_blink_service,
    SERVICE_FEE_SATS,
)


class CouponGeneratorView(TemplateView):
    """임시 사토시 쿠폰을 생성하는 독립 페이지."""

    template_name = "coupon/coupon_generator.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        config = CouponInvoiceConfig()
        context["coupon_config"] = config
        config_payload = {
            "service_fee": config.service_fee,
            "max_amount": config.max_amount,
            "presets": config.presets,
        }
        context["coupon_config_json"] = mark_safe(json.dumps(config_payload))
        context["service_fee"] = SERVICE_FEE_SATS
        return context


class CouponInvoiceView(View):
    """라이트닝 인보이스 발행 API."""

    def post(self, request, *args, **kwargs):
        try:
            payload = self._get_payload(request)
            requested_amount = self._parse_amount(payload)
        except ValueError as exc:
            return JsonResponse({"success": False, "error": str(exc)}, status=400)

        try:
            blink_service = get_coupon_blink_service()
        except BlinkCredentialError as exc:
            return JsonResponse({"success": False, "error": str(exc)}, status=500)

        total_amount = calculate_invoice_amount(requested_amount)
        memo = f"SatoShop 임시 쿠폰 보관금 {requested_amount} sats (fee {SERVICE_FEE_SATS} sats)"

        invoice_response = blink_service.create_invoice(
            amount_sats=total_amount,
            memo=memo,
            expires_in_minutes=15,
        )
        if not invoice_response.get("success"):
            return JsonResponse(
                {"success": False, "error": invoice_response.get("error", "인보이스 생성에 실패했습니다.")},
                status=502,
            )

        expires_at = invoice_response.get("expires_at")
        expires_at_iso = (
            timezone.localtime(expires_at).isoformat()
            if expires_at
            else None
        )

        return JsonResponse(
            {
                "success": True,
                "invoice": invoice_response.get("invoice"),
                "payment_hash": invoice_response.get("payment_hash"),
                "coupon_amount_sats": requested_amount,
                "service_fee_sats": SERVICE_FEE_SATS,
                "total_amount_sats": total_amount,
                "expires_at": expires_at_iso,
                "memo": memo,
            }
        )

    def _get_payload(self, request):
        if request.content_type == "application/json":
            try:
                return json.loads(request.body.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                return {}
        return request.POST

    def _parse_amount(self, data):
        raw_amount = data.get("amount") or data.get("amount_sats")
        if raw_amount in (None, ""):
            raise ValueError("수량을 입력해 주세요.")
        try:
            amount = int(raw_amount)
        except (TypeError, ValueError):
            raise ValueError("수량은 숫자로 입력해 주세요.")
        if amount <= 0:
            raise ValueError("수량은 최소 1 사토시 이상이어야 합니다.")
        return clamp_amount(amount)


class CouponInvoiceStatusView(View):
    """발행된 인보이스의 결제 상태를 조회한다."""

    def get(self, request, payment_hash, *args, **kwargs):
        payment_hash = (payment_hash or "").strip()
        if not payment_hash:
            return JsonResponse(
                {"success": False, "error": "유효한 결제 해시가 필요합니다."},
                status=400,
            )

        try:
            blink_service = get_coupon_blink_service()
        except BlinkCredentialError as exc:
            return JsonResponse({"success": False, "error": str(exc)}, status=500)

        status_response = blink_service.check_invoice_status(payment_hash)
        if not status_response.get("success"):
            return JsonResponse(
                {"success": False, "error": status_response.get("error", "결제 상태 조회에 실패했습니다.")},
                status=502,
            )

        return JsonResponse(
            {
                "success": True,
                "status": status_response.get("status"),
                "raw_status": status_response.get("raw_status"),
            }
        )
