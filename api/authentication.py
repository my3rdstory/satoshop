from dataclasses import dataclass
from typing import Optional, Tuple

from django.http import JsonResponse

from .models import ApiKey


@dataclass
class AuthResult:
    is_authenticated: bool
    api_key: Optional[ApiKey] = None
    response: Optional[JsonResponse] = None


def _extract_bearer_token(authorization_header: str) -> Optional[str]:
    if not authorization_header:
        return None
    if not authorization_header.lower().startswith("bearer "):
        return None
    token = authorization_header.split(" ", 1)[1].strip()
    return token or None


def authenticate_request(request) -> AuthResult:
    raw_header = request.headers.get("Authorization", "")
    token = _extract_bearer_token(raw_header)
    if not token:
        return AuthResult(
            is_authenticated=False,
            response=JsonResponse({"detail": "인증 토큰이 필요합니다."}, status=401),
        )

    key = ApiKey.objects.filter(key_hash=ApiKey.hash_key(token)).first()
    if not key:
        return AuthResult(
            is_authenticated=False,
            response=JsonResponse({"detail": "유효하지 않은 API 키입니다."}, status=401),
        )

    if not key.is_active:
        return AuthResult(
            is_authenticated=False,
            response=JsonResponse({"detail": "비활성화된 API 키입니다."}, status=403),
        )

    key.touch_last_used()
    return AuthResult(is_authenticated=True, api_key=key)
