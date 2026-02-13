import binascii
import secrets
from dataclasses import dataclass

import bech32
from django.core.cache import cache
from secp256k1 import PublicKey


CHALLENGE_CACHE_KEY_PREFIX = "api:nostr:challenge"
CHALLENGE_TTL_SECONDS = 300


class NostrAuthError(Exception):
    """Nostr 인증 실패 예외"""


@dataclass(frozen=True)
class NostrChallenge:
    challenge_id: str
    challenge: str
    expires_in_seconds: int


def normalize_nostr_pubkey(value: str) -> str:
    """npub 또는 32바이트 hex 공개키를 64자리 hex 문자열로 정규화."""
    if not value:
        raise NostrAuthError("Nostr 공개키가 비어 있습니다.")

    candidate = value.strip().lower()
    if candidate.startswith("npub1"):
        hrp, data = bech32.bech32_decode(candidate)
        if hrp != "npub" or data is None:
            raise NostrAuthError("유효한 npub 형식이 아닙니다.")
        decoded = bech32.convertbits(data, 5, 8, False)
        if decoded is None:
            raise NostrAuthError("npub 디코딩에 실패했습니다.")
        pubkey_bytes = bytes(decoded)
    else:
        if candidate.startswith("0x"):
            candidate = candidate[2:]
        try:
            pubkey_bytes = binascii.unhexlify(candidate)
        except binascii.Error as exc:
            raise NostrAuthError("Nostr 공개키는 64자리 hex 또는 npub 형식이어야 합니다.") from exc

    if len(pubkey_bytes) != 32:
        raise NostrAuthError("Nostr 공개키 길이는 32바이트여야 합니다.")

    try:
        # BIP340 x-only 공개키를 압축 공개키(짝수 y)로 가정해 검증에 사용
        PublicKey(b"\x02" + pubkey_bytes, raw=True)
    except Exception as exc:
        raise NostrAuthError("유효하지 않은 Nostr 공개키입니다.") from exc

    return pubkey_bytes.hex()


def issue_nostr_challenge(pubkey_hex: str) -> NostrChallenge:
    challenge_id = secrets.token_urlsafe(24)
    challenge = secrets.token_hex(32)
    cache.set(
        _challenge_cache_key(challenge_id),
        {
            "pubkey": pubkey_hex,
            "challenge": challenge,
        },
        timeout=CHALLENGE_TTL_SECONDS,
    )
    return NostrChallenge(
        challenge_id=challenge_id,
        challenge=challenge,
        expires_in_seconds=CHALLENGE_TTL_SECONDS,
    )


def verify_nostr_challenge_signature(
    *,
    pubkey_hex: str,
    challenge_id: str,
    signature_hex: str,
) -> None:
    cache_key = _challenge_cache_key(challenge_id)
    challenge_payload = cache.get(cache_key)
    if not challenge_payload:
        raise NostrAuthError("Nostr 챌린지가 없거나 만료되었습니다.")

    expected_pubkey = challenge_payload.get("pubkey")
    if expected_pubkey != pubkey_hex:
        raise NostrAuthError("챌린지의 공개키와 요청 공개키가 일치하지 않습니다.")

    challenge = challenge_payload.get("challenge")
    if not challenge:
        raise NostrAuthError("챌린지 데이터가 손상되었습니다.")

    sig_candidate = (signature_hex or "").strip().lower()
    if sig_candidate.startswith("0x"):
        sig_candidate = sig_candidate[2:]

    try:
        sig_bytes = binascii.unhexlify(sig_candidate)
    except binascii.Error as exc:
        raise NostrAuthError("Nostr 서명은 64바이트 hex 형식이어야 합니다.") from exc

    if len(sig_bytes) != 64:
        raise NostrAuthError("Nostr 서명 길이는 64바이트여야 합니다.")

    try:
        pubkey_bytes = binascii.unhexlify(pubkey_hex)
        pubkey = PublicKey(b"\x02" + pubkey_bytes, raw=True)
        is_valid = pubkey.schnorr_verify(
            binascii.unhexlify(challenge),
            sig_bytes,
            None,
            raw=True,
        )
    except Exception as exc:
        raise NostrAuthError("Nostr 서명 검증 중 오류가 발생했습니다.") from exc

    if not is_valid:
        raise NostrAuthError("Nostr 서명 검증에 실패했습니다.")

    cache.delete(cache_key)


def _challenge_cache_key(challenge_id: str) -> str:
    return f"{CHALLENGE_CACHE_KEY_PREFIX}:{challenge_id}"
