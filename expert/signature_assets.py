import logging
from typing import Dict, Optional, Tuple

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import ContentFile
from django.utils import timezone

from storage.backends import S3Storage
from storage.utils import upload_file_to_s3

from .contract_flow import decode_signature_data

logger = logging.getLogger(__name__)

SIGNATURE_UPLOAD_PREFIX = "expert/contracts/signatures"


def signature_media_fallback_enabled() -> bool:
    """
    Returns whether we are allowed to fall back to MEDIA storage.
    Defaults to True in DEBUG (developer) mode unless explicitly disabled.
    """

    default = getattr(settings, "DEBUG", False)
    return getattr(settings, "EXPERT_SIGNATURE_MEDIA_FALLBACK", default)


def _build_asset_payload(upload_result: Dict) -> Dict:
    return {
        "path": upload_result.get("file_path"),
        "url": upload_result.get("file_url"),
        "size": upload_result.get("file_size"),
        "original_name": upload_result.get("original_name"),
        "storage": upload_result.get("storage", "s3"),
        "uploaded_at": timezone.now().isoformat(),
    }


def store_signature_asset_from_data(data_url: str, filename_prefix: str) -> Tuple[Optional[Dict], Optional[str], ContentFile]:
    """
    Convert a data URL into a ContentFile and attempt to upload it.
    Returns (asset, error_message, file_obj). Caller is responsible for handling fallback.
    """

    signature_file = decode_signature_data(data_url, filename_prefix)
    asset, error = store_signature_asset_from_file(signature_file)
    return asset, error, signature_file


def store_signature_asset_from_file(file_obj: ContentFile) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Attempt to upload the provided file to S3 storage.
    Returns (asset, error_message). File pointer is reset before returning.
    """

    file_obj.seek(0)
    upload_result = upload_file_to_s3(file_obj, prefix=SIGNATURE_UPLOAD_PREFIX)
    file_obj.seek(0)
    if not upload_result.get("success"):
        error = upload_result.get("error") or "서명 이미지를 객체 스토리지에 업로드하지 못했습니다."
        logger.warning("Failed to upload signature asset: %s", error)
        return None, error
    return _build_asset_payload(upload_result), None


def resolve_signature_url(asset: Dict) -> Optional[str]:
    """
    Resolve a displayable URL for the stored asset.
    Prefers the stored URL, but regenerates via storage backend if necessary.
    """

    if not asset:
        return None
    if asset.get("url"):
        return asset["url"]
    path = asset.get("path")
    if not path:
        return None
    try:
        storage = S3Storage()
        return storage.url(path)
    except ImproperlyConfigured:
        logger.error("S3Storage is not configured; cannot build signature URL for %s", path)
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Failed to build signature URL for %s: %s", path, exc)
    return None
