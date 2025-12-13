import ipaddress
from dataclasses import dataclass
from typing import Optional

from django.conf import settings
from django.http import JsonResponse

from .models import ApiAllowedOrigin, ApiIpAllowlist


def _get_client_ip(request) -> Optional[str]:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def enforce_ip_allowlist(request) -> Optional[JsonResponse]:
    """허용 IP 목록이 등록된 경우에만 차단을 수행."""
    rules = ApiIpAllowlist.objects.filter(is_active=True)
    if not rules.exists():
        return None

    client_ip = _get_client_ip(request)
    if settings.DEBUG and client_ip in {"127.0.0.1", "::1"}:
        return None
    if not client_ip:
        return JsonResponse({"detail": "클라이언트 IP를 확인할 수 없습니다."}, status=403)

    try:
        ip_obj = ipaddress.ip_address(client_ip)
    except ValueError:
        return JsonResponse({"detail": "잘못된 클라이언트 IP입니다."}, status=403)

    for rule in rules:
        try:
            network = ipaddress.ip_network(rule.cidr, strict=False)
            if ip_obj in network:
                return None
        except ValueError:
            continue

    return JsonResponse({"detail": "허용되지 않은 IP 입니다."}, status=403)


@dataclass
class OriginCheckResult:
    allowed: bool
    origin: Optional[str] = None
    response: Optional[JsonResponse] = None


def enforce_origin_allowlist(request) -> OriginCheckResult:
    """Origin 허용 목록이 있을 때만 차단. Origin 헤더가 없으면 통과."""
    rules = ApiAllowedOrigin.objects.filter(is_active=True)
    origin_header = request.headers.get("Origin")

    if not rules.exists():
        # 허용 목록이 없으면 Origin 헤더를 그대로 반영하지 않고 통과
        return OriginCheckResult(allowed=True, origin=None, response=None)

    if not origin_header:
        return OriginCheckResult(allowed=True, origin=None, response=None)

    if settings.DEBUG:
        normalized_dev = origin_header.rstrip("/").lower()
        if normalized_dev.startswith("http://localhost:") or normalized_dev.startswith("http://127.0.0.1:"):
            return OriginCheckResult(allowed=True, origin=origin_header, response=None)

    normalized_header = origin_header.rstrip("/").lower()
    allowed_origins = {r.origin.rstrip("/").lower() for r in rules}

    if normalized_header in allowed_origins:
        return OriginCheckResult(allowed=True, origin=origin_header, response=None)

    return OriginCheckResult(
        allowed=False,
        response=JsonResponse({"detail": "허용되지 않은 Origin 입니다."}, status=403),
    )


def apply_cors_headers(response: JsonResponse, origin_result: OriginCheckResult) -> None:
    if origin_result.origin:
        response["Access-Control-Allow-Origin"] = origin_result.origin
        response["Vary"] = "Origin"
