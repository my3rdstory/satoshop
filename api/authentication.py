from dataclasses import dataclass
from typing import Optional

from django.http import JsonResponse

from .models import ApiKey
from .nostr_auth import NostrAuthError, normalize_nostr_pubkey, verify_nostr_challenge_signature


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


def _extract_nostr_header(request, header_name: str) -> str:
    return (request.headers.get(header_name, "") or "").strip()


def _authenticate_with_bearer(token: str) -> AuthResult:
    key = ApiKey.objects.filter(key_hash=ApiKey.hash_key(token)).first()
    if not key:
        return AuthResult(
            is_authenticated=False,
            response=JsonResponse({"detail": "유효하지 않은 API 키입니다."}, status=401),
        )

    if key.uses_nostr_auth:
        return AuthResult(
            is_authenticated=False,
            response=JsonResponse(
                {"detail": "해당 API 키는 Nostr 인증 전용입니다. Nostr 서명 헤더를 사용하세요."},
                status=401,
            ),
        )

    if not key.is_active:
        return AuthResult(
            is_authenticated=False,
            response=JsonResponse({"detail": "비활성화된 API 키입니다."}, status=403),
        )

    key.touch_last_used()
    return AuthResult(is_authenticated=True, api_key=key)


def _authenticate_with_nostr(request) -> AuthResult:
    pubkey_header = _extract_nostr_header(request, "X-Nostr-Pubkey")
    challenge_id = _extract_nostr_header(request, "X-Nostr-Challenge-Id")
    signature = _extract_nostr_header(request, "X-Nostr-Signature")

    if not (pubkey_header or challenge_id or signature):
        return AuthResult(
            is_authenticated=False,
            response=JsonResponse({"detail": "인증 토큰이 필요합니다."}, status=401),
        )

    if not (pubkey_header and challenge_id and signature):
        return AuthResult(
            is_authenticated=False,
            response=JsonResponse(
                {
                    "detail": (
                        "Nostr 인증 헤더가 누락되었습니다. "
                        "X-Nostr-Pubkey, X-Nostr-Challenge-Id, X-Nostr-Signature를 모두 전달하세요."
                    )
                },
                status=401,
            ),
        )

    try:
        normalized_pubkey = normalize_nostr_pubkey(pubkey_header)
    except NostrAuthError as exc:
        return AuthResult(
            is_authenticated=False,
            response=JsonResponse({"detail": str(exc)}, status=401),
        )

    key = ApiKey.objects.filter(auth_method=ApiKey.AUTH_METHOD_NOSTR, nostr_pubkey=normalized_pubkey).first()
    if not key:
        return AuthResult(
            is_authenticated=False,
            response=JsonResponse({"detail": "등록되지 않은 Nostr 인증 키입니다."}, status=401),
        )

    if not key.is_active:
        return AuthResult(
            is_authenticated=False,
            response=JsonResponse({"detail": "비활성화된 API 키입니다."}, status=403),
        )

    try:
        verify_nostr_challenge_signature(
            pubkey_hex=normalized_pubkey,
            challenge_id=challenge_id,
            signature_hex=signature,
        )
    except NostrAuthError as exc:
        return AuthResult(
            is_authenticated=False,
            response=JsonResponse({"detail": str(exc)}, status=401),
        )

    key.touch_last_used()
    return AuthResult(is_authenticated=True, api_key=key)


def authenticate_request(request) -> AuthResult:
    raw_header = request.headers.get("Authorization", "")
    token = _extract_bearer_token(raw_header)
    if token:
        return _authenticate_with_bearer(token)
    return _authenticate_with_nostr(request)
