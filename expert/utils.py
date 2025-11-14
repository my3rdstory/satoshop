import base64
import hashlib
import io
import logging
import os
import tempfile
from functools import lru_cache
from typing import BinaryIO

from django.conf import settings
from django.core.files.base import ContentFile

try:  # Optional dependency guard (pyHanko is installed but keep fallback for safety)
    from pyhanko.sign import signers
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
except ImportError:  # pragma: no cover - optional dependency may be missing in some envs
    signers = None
    IncrementalPdfFileWriter = None


logger = logging.getLogger(__name__)


class PDFSigningError(Exception):
    """Raised when PDF signing fails."""


def calculate_sha256_from_fileobj(file_obj: BinaryIO, *, chunk_size: int = 1024 * 1024) -> str:
    """Return the SHA-256 hex digest for a file-like object while preserving the cursor."""

    try:
        file_obj.seek(0)
    except (AttributeError, OSError):  # pragma: no cover - some streamed objects might not support seek
        pass
    digest = hashlib.sha256()
    for chunk in iter(lambda: file_obj.read(chunk_size), b""):
        if not chunk:
            break
        digest.update(chunk)
    try:
        file_obj.seek(0)
    except (AttributeError, OSError):  # pragma: no cover
        pass
    return digest.hexdigest()


def calculate_sha256_from_field_file(field_file) -> str:
    """Open a Django FileField/File and compute its SHA-256 value."""

    if not field_file:
        return ""
    field_file.open("rb")
    try:
        return calculate_sha256_from_fileobj(field_file)
    finally:
        field_file.close()


def pdf_signing_enabled() -> bool:
    cert_path = getattr(settings, "EXPERT_SIGNER_CERT_PATH", "")
    cert_base64 = getattr(settings, "EXPERT_SIGNER_CERT_BASE64", "")
    return bool(signers and (cert_path or cert_base64))


@lru_cache(maxsize=1)
def _load_signer():  # pragma: no cover - heavy IO, tested via integration
    if not pdf_signing_enabled():
        raise RuntimeError("PDF 서명 기능이 비활성화되었습니다.")
    password = getattr(settings, "EXPERT_SIGNER_CERT_PASSWORD", "")
    cert_path = getattr(settings, "EXPERT_SIGNER_CERT_PATH", "")
    cert_base64 = getattr(settings, "EXPERT_SIGNER_CERT_BASE64", "")
    passphrase = password.encode() if password else None
    if cert_path:
        return signers.SimpleSigner.load_pkcs12(cert_path, passphrase=passphrase)
    if cert_base64:
        pkcs12_bytes = base64.b64decode(cert_base64)
        tmp_file = tempfile.NamedTemporaryFile(delete=False)
        try:
            tmp_file.write(pkcs12_bytes)
            tmp_file.flush()
            tmp_file.close()
            return signers.SimpleSigner.load_pkcs12(tmp_file.name, passphrase=passphrase)
        finally:
            try:
                os.unlink(tmp_file.name)
            except OSError:  # pragma: no cover - best effort cleanup
                pass
    raise RuntimeError("서명용 인증서를 찾을 수 없습니다.")


def sign_contract_pdf(content_file: ContentFile) -> ContentFile:
    """Attach a digital signature to the PDF if signing is enabled."""

    if not pdf_signing_enabled() or not signers or not IncrementalPdfFileWriter:
        content_file.seek(0)
        return content_file

    try:
        content_file.seek(0)
        buffer = io.BytesIO(content_file.read())
        buffer.seek(0)
        writer = IncrementalPdfFileWriter(buffer)
        signer = _load_signer()
        metadata = signers.PdfSignatureMetadata(
            field_name="ExpertSignature",
            reason="SatoShop Expert 계약 위변조 방지",
        )
        signed_output = signers.sign_pdf(
            writer,
            signer=signer,
            signature_meta=metadata,
        )
        if hasattr(signed_output, "getvalue"):
            signed_bytes = signed_output.getvalue()
        elif hasattr(signed_output, "getbuffer"):
            signed_bytes = signed_output.getbuffer().tobytes()
        else:  # pragma: no cover - fallback for unexpected return types
            signed_bytes = bytes(signed_output)
        return ContentFile(signed_bytes, name=content_file.name)
    except Exception as exc:  # noqa: BLE001
        logger.warning("PDF 전자서명에 실패했습니다: %s", exc, exc_info=True)
        raise PDFSigningError(str(exc)) from exc
