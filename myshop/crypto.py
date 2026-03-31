import hashlib

from ecdsa import BadSignatureError, MalformedPointError, SECP256k1, VerifyingKey, ellipticcurve, util


_CURVE = SECP256k1.curve
_GENERATOR = SECP256k1.generator
_FIELD_SIZE = _CURVE.p()
_CURVE_ORDER = SECP256k1.order
_POINT_AT_INFINITY = ellipticcurve.INFINITY


def validate_bip340_pubkey(pubkey_bytes: bytes) -> None:
    if len(pubkey_bytes) != 32:
        raise ValueError("BIP340 공개키 길이는 32바이트여야 합니다.")

    _lift_x_even_y(pubkey_bytes)


def verify_bip340_signature(*, pubkey_bytes: bytes, signature_bytes: bytes, message: bytes) -> bool:
    if len(pubkey_bytes) != 32 or len(signature_bytes) != 64:
        return False

    try:
        pubkey_point = _lift_x_even_y(pubkey_bytes)
    except ValueError:
        return False

    r = int.from_bytes(signature_bytes[:32], "big")
    s = int.from_bytes(signature_bytes[32:], "big")
    if r >= _FIELD_SIZE or s >= _CURVE_ORDER:
        return False

    challenge = int.from_bytes(
        _tagged_hash("BIP0340/challenge", signature_bytes[:32] + pubkey_bytes + message),
        "big",
    ) % _CURVE_ORDER
    point_r = (_GENERATOR * s) + (pubkey_point * ((_CURVE_ORDER - challenge) % _CURVE_ORDER))

    if point_r == _POINT_AT_INFINITY:
        return False

    return point_r.y() % 2 == 0 and point_r.x() == r


def verify_secp256k1_ecdsa_digest(*, public_key_bytes: bytes, signature_bytes: bytes, digest: bytes) -> bool:
    try:
        verifying_key = VerifyingKey.from_string(
            public_key_bytes,
            curve=SECP256k1,
            valid_encodings=("compressed", "uncompressed"),
        )
        return verifying_key.verify_digest(
            signature_bytes,
            digest,
            sigdecode=util.sigdecode_string,
            allow_truncate=False,
        )
    except (BadSignatureError, MalformedPointError, ValueError):
        return False


def _lift_x_even_y(pubkey_bytes: bytes) -> ellipticcurve.Point:
    x_coord = int.from_bytes(pubkey_bytes, "big")
    if x_coord >= _FIELD_SIZE:
        raise ValueError("공개키 x 좌표가 유효 범위를 벗어났습니다.")

    alpha = (pow(x_coord, 3, _FIELD_SIZE) + 7) % _FIELD_SIZE
    beta = pow(alpha, (_FIELD_SIZE + 1) // 4, _FIELD_SIZE)
    if pow(beta, 2, _FIELD_SIZE) != alpha:
        raise ValueError("공개키가 secp256k1 곡선 위에 있지 않습니다.")

    y_coord = beta if beta % 2 == 0 else _FIELD_SIZE - beta
    return ellipticcurve.Point(_CURVE, x_coord, y_coord, _CURVE_ORDER)


def _tagged_hash(tag: str, payload: bytes) -> bytes:
    tag_hash = hashlib.sha256(tag.encode("utf-8")).digest()
    return hashlib.sha256(tag_hash + tag_hash + payload).digest()
