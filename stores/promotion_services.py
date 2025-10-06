from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, List

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from PIL import Image

from storage.utils import delete_file_from_s3, upload_file_to_s3

from .models import BahPromotionImage, BahPromotionRequest

logger = logging.getLogger(__name__)


@dataclass
class PromotionImagePayload:
    original_name: str
    file: UploadedFile
    width: int
    height: int
    file_size: int


def _prepare_image(uploaded_file: UploadedFile) -> PromotionImagePayload:
    """원본 이미지를 그대로 업로드하면서 메타데이터를 추출한다."""
    try:
        uploaded_file.seek(0)
    except (AttributeError, OSError):
        pass

    width = 0
    height = 0

    try:
        image = Image.open(uploaded_file)
        width, height = image.size
    except Exception as exc:  # pragma: no cover - Pillow가 다양한 예외 발생
        logger.warning("BAH 홍보 이미지 메타데이터 추출 실패: %s", exc)
    finally:
        try:
            uploaded_file.seek(0)
        except (AttributeError, OSError):
            pass

    return PromotionImagePayload(
        original_name=uploaded_file.name,
        file=uploaded_file,
        width=width,
        height=height,
        file_size=getattr(uploaded_file, 'size', None) or 0,
    )


def save_promotion_images(
    promotion_request: BahPromotionRequest,
    files: Iterable[UploadedFile],
    *,
    uploaded_by,
) -> List[BahPromotionImage]:
    """홍보 요청 이미지 업로드와 모델 생성 처리"""
    files = list(files)
    if not files:
        return []

    created_images: List[BahPromotionImage] = []
    uploaded_payloads = []

    current_count = promotion_request.images.count()

    try:
        for index, uploaded_file in enumerate(files, start=1):
            prepared = _prepare_image(uploaded_file)
            prefix = f"bah-promotion/{promotion_request.id}"
            try:
                prepared.file.seek(0)
            except (AttributeError, OSError):
                pass

            upload_result = upload_file_to_s3(prepared.file, prefix=prefix)
            if not upload_result.get('success'):
                raise ValidationError(upload_result.get('error', '이미지 업로드에 실패했습니다.'))

            uploaded_payloads.append(upload_result)

            bah_image = BahPromotionImage.objects.create(
                promotion_request=promotion_request,
                original_name=prepared.original_name,
                file_path=upload_result['file_path'],
                file_url=upload_result['file_url'],
                file_size=upload_result.get('file_size') or prepared.file_size,
                width=prepared.width,
                height=prepared.height,
                order=current_count + index,
                uploaded_by=uploaded_by,
            )
            created_images.append(bah_image)
            logger.info(
                "BAH 홍보 이미지 업로드 완료",
                extra={'request_id': promotion_request.id, 'file_path': upload_result['file_path']},
            )
    except Exception as exc:
        logger.error("BAH 홍보 이미지 처리 실패", exc_info=True)
        for payload in uploaded_payloads:
            delete_file_from_s3(payload.get('file_path'))
        for image in created_images:
            image.delete()
        if isinstance(exc, ValidationError):
            raise
        raise ValidationError('이미지 업로드 처리 중 오류가 발생했습니다.') from exc

    return created_images


def delete_promotion_images(promotion_request: BahPromotionRequest, image_ids: Iterable[int]) -> int:
    """선택한 홍보 이미지를 삭제한다."""
    ids = [int(pk) for pk in image_ids if str(pk).isdigit()]
    if not ids:
        return 0

    images = list(promotion_request.images.filter(id__in=ids))
    deleted_count = 0

    with transaction.atomic():
        for image in images:
            delete_file_from_s3(image.file_path)
            image.delete()
            deleted_count += 1

        # order 재정렬
        remaining = promotion_request.images.order_by('order', 'uploaded_at')
        for idx, image in enumerate(remaining, start=1):
            if image.order != idx:
                image.order = idx
                image.save(update_fields=['order'])

    return deleted_count
