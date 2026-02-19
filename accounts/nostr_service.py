import binascii
import hashlib
import json
import secrets
import time
from dataclasses import dataclass

from django.contrib.auth.models import User
from django.core.cache import cache
from django.utils.http import url_has_allowed_host_and_scheme
from secp256k1 import PublicKey

from api.nostr_auth import NostrAuthError, normalize_nostr_pubkey
from .models import NostrUser


WEB_LOGIN_CACHE_KEY_PREFIX = "accounts:nostr:web-login"
WEB_LOGIN_RESULT_CACHE_KEY_PREFIX = "accounts:nostr:web-login:result"
WEB_LOGIN_PENDING_CACHE_KEY_PREFIX = "accounts:nostr:web-login:pending"
WEB_LOGIN_TTL_SECONDS = 300
WEB_LOGIN_EVENT_KIND = 22242


@dataclass(frozen=True)
class NostrWebLoginChallenge:
    challenge_id: str
    challenge: str
    domain: str
    kind: int
    expires_in_seconds: int


def create_nostr_login_challenge(*, request, raw_pubkey: str, next_url: str | None) -> NostrWebLoginChallenge:
    normalized_pubkey = normalize_nostr_pubkey(raw_pubkey) if (raw_pubkey or "").strip() else ""
    challenge_id = secrets.token_urlsafe(24)
    challenge = secrets.token_hex(32)
    domain = request.get_host()
    safe_next_url = _safe_next_url(request=request, next_url=next_url)
    cache.set(
        _cache_key(challenge_id),
        {
            "pubkey": normalized_pubkey,
            "challenge": challenge,
            "domain": domain,
            "next_url": safe_next_url,
            "issued_at": int(time.time()),
        },
        timeout=WEB_LOGIN_TTL_SECONDS,
    )
    return NostrWebLoginChallenge(
        challenge_id=challenge_id,
        challenge=challenge,
        domain=domain,
        kind=WEB_LOGIN_EVENT_KIND,
        expires_in_seconds=WEB_LOGIN_TTL_SECONDS,
    )


def verify_nostr_login_event(
    *,
    challenge_id: str,
    event_payload: dict,
    raw_pubkey: str,
    request_host: str,
) -> dict:
    challenge_data = cache.get(_cache_key(challenge_id))
    if not challenge_data:
        raise NostrAuthError("Nostr 챌린지가 없거나 만료되었습니다.")

    if challenge_data.get("domain") != request_host:
        raise NostrAuthError("요청 도메인이 챌린지 발급 도메인과 일치하지 않습니다.")

    normalized_pubkey = normalize_nostr_pubkey(raw_pubkey or event_payload.get("pubkey", ""))
    expected_pubkey = (challenge_data.get("pubkey") or "").strip().lower()
    if expected_pubkey and normalized_pubkey != expected_pubkey:
        raise NostrAuthError("챌린지의 공개키와 서명 공개키가 일치하지 않습니다.")

    event_pubkey = normalize_nostr_pubkey(event_payload.get("pubkey", ""))
    if event_pubkey != normalized_pubkey:
        raise NostrAuthError("이벤트 pubkey와 요청 pubkey가 일치하지 않습니다.")

    try:
        created_at = int(event_payload.get("created_at"))
    except (TypeError, ValueError):
        raise NostrAuthError("Nostr 이벤트 created_at 값이 올바르지 않습니다.")

    now_ts = int(time.time())
    if abs(now_ts - created_at) > WEB_LOGIN_TTL_SECONDS:
        raise NostrAuthError("Nostr 이벤트 생성 시간이 만료되었습니다. 다시 시도해주세요.")

    try:
        kind = int(event_payload.get("kind"))
    except (TypeError, ValueError):
        raise NostrAuthError("Nostr 이벤트 kind 값이 올바르지 않습니다.")
    if kind != WEB_LOGIN_EVENT_KIND:
        raise NostrAuthError("지원하지 않는 Nostr 이벤트 kind입니다.")

    tags = event_payload.get("tags")
    if not isinstance(tags, list):
        raise NostrAuthError("Nostr 이벤트 tags 형식이 올바르지 않습니다.")

    challenge_tag = _find_tag_value(tags, "challenge")
    if challenge_tag != challenge_data.get("challenge"):
        raise NostrAuthError("Nostr 이벤트 challenge 값이 일치하지 않습니다.")

    domain_tag = _find_tag_value(tags, "domain")
    if domain_tag != challenge_data.get("domain"):
        raise NostrAuthError("Nostr 이벤트 domain 값이 일치하지 않습니다.")

    content = event_payload.get("content", "")
    if not isinstance(content, str):
        raise NostrAuthError("Nostr 이벤트 content 형식이 올바르지 않습니다.")

    serialized_event = json.dumps(
        [0, event_pubkey, created_at, kind, tags, content],
        separators=(",", ":"),
        ensure_ascii=False,
    )
    expected_event_id = hashlib.sha256(serialized_event.encode("utf-8")).hexdigest()

    event_id = (event_payload.get("id") or "").strip().lower()
    if event_id != expected_event_id:
        raise NostrAuthError("Nostr 이벤트 해시가 유효하지 않습니다.")

    signature_hex = (event_payload.get("sig") or "").strip().lower()
    if signature_hex.startswith("0x"):
        signature_hex = signature_hex[2:]

    try:
        signature_bytes = binascii.unhexlify(signature_hex)
    except binascii.Error as exc:
        raise NostrAuthError("Nostr 서명은 64바이트 hex 형식이어야 합니다.") from exc

    if len(signature_bytes) != 64:
        raise NostrAuthError("Nostr 서명 길이는 64바이트여야 합니다.")

    try:
        pubkey_bytes = binascii.unhexlify(event_pubkey)
        event_id_bytes = binascii.unhexlify(event_id)
        pubkey = PublicKey(b"\x02" + pubkey_bytes, raw=True)
        is_valid_signature = pubkey.schnorr_verify(
            event_id_bytes,
            signature_bytes,
            None,
            raw=True,
        )
    except Exception as exc:
        raise NostrAuthError("Nostr 이벤트 서명 검증 중 오류가 발생했습니다.") from exc

    if not is_valid_signature:
        raise NostrAuthError("Nostr 이벤트 서명 검증에 실패했습니다.")

    cache.delete(_cache_key(challenge_id))
    return {
        "pubkey": normalized_pubkey,
        "next_url": challenge_data.get("next_url") or None,
    }


def store_nostr_login_result(*, challenge_id: str, user_id: int, username: str, is_new: bool, next_url: str | None):
    cache.set(
        _result_cache_key(challenge_id),
        {
            "user_id": user_id,
            "username": username,
            "is_new": is_new,
            "next_url": next_url or "",
        },
        timeout=WEB_LOGIN_TTL_SECONDS,
    )


def pop_nostr_login_result(challenge_id: str) -> dict | None:
    result_key = _result_cache_key(challenge_id)
    payload = cache.get(result_key)
    if payload:
        cache.delete(result_key)
    return payload


def save_nostr_pending_session(*, token: str, payload: dict):
    cache.set(
        _pending_cache_key(token),
        payload,
        timeout=WEB_LOGIN_TTL_SECONDS,
    )


def get_nostr_pending_session(token: str) -> dict | None:
    return cache.get(_pending_cache_key(token))


def clear_nostr_pending_session(token: str):
    cache.delete(_pending_cache_key(token))


def authenticate_or_create_nostr_user(pubkey_hex: str) -> tuple[User, bool]:
    try:
        nostr_user = NostrUser.objects.get(public_key=pubkey_hex)
        nostr_user.update_last_login()
        return nostr_user.user, False
    except NostrUser.DoesNotExist:
        base_username = f"ns_{pubkey_hex[:16]}"
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1

        user = User.objects.create_user(
            username=username,
            password=None,
        )
        nostr_user = NostrUser.objects.create(
            user=user,
            public_key=pubkey_hex,
        )
        nostr_user.update_last_login()
        return user, True


def _find_tag_value(tags: list, tag_name: str) -> str:
    for tag in tags:
        if not isinstance(tag, list):
            continue
        if len(tag) < 2:
            continue
        if tag[0] != tag_name:
            continue
        if not isinstance(tag[1], str):
            continue
        return tag[1]
    return ""


def _safe_next_url(*, request, next_url: str | None) -> str:
    if not next_url:
        return ""
    if url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return ""


def _cache_key(challenge_id: str) -> str:
    return f"{WEB_LOGIN_CACHE_KEY_PREFIX}:{challenge_id}"


def _result_cache_key(challenge_id: str) -> str:
    return f"{WEB_LOGIN_RESULT_CACHE_KEY_PREFIX}:{challenge_id}"


def _pending_cache_key(token: str) -> str:
    return f"{WEB_LOGIN_PENDING_CACHE_KEY_PREFIX}:{token}"
