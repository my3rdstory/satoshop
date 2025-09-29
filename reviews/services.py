import html
import io
import logging
import re
import uuid
from dataclasses import dataclass
from typing import Iterable, List, Optional

import bleach
import requests

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Avg
from django.urls import reverse
from PIL import Image, ImageOps

from orders.models import OrderItem, PurchaseHistory
from storage.utils import delete_file_from_s3, upload_file_to_s3

from .models import Review, ReviewImage


logger = logging.getLogger(__name__)


def _log(message: str, level: int = logging.INFO, **params) -> None:
    """로깅 + 콘솔 출력 헬퍼"""
    if params:
        logger.log(level, f"{message} | {params}")
        try:
            print(f"[reviews] {message}: {params}")
        except Exception:  # pragma: no cover - print failure should not break flow
            pass
    else:
        logger.log(level, message)
        try:
            print(f"[reviews] {message}")
        except Exception:  # pragma: no cover
            pass


QUALIFIED_ORDER_STATUSES = {'paid', 'shipped', 'delivered'}
MAX_IMAGES_PER_REVIEW = 5
MAX_REVIEW_IMAGE_WIDTH = 1000
WEBP_QUALITY = 85
REVIEWS_PER_PAGE = 5
X_POST_URL_RE = re.compile(
    r'https?://(?:www\.)?(?:twitter\.com|x\.com)/[A-Za-z0-9_]+/status/\d+(?:\?[^\s]*)?',
    re.IGNORECASE,
)
X_OEMBED_ENDPOINT = 'https://publish.twitter.com/oembed'
X_OEMBED_TIMEOUT = 5


def normalize_x_post_url(url: str) -> str:
    """주어진 URL에서 불필요한 공백과 후행 구두점을 제거하고 https로 표준화."""
    if not url:
        return ''

    trimmed = url.strip()
    if trimmed.lower().startswith('http://'):
        trimmed = 'https://' + trimmed[7:]

    # 문장부호로 닫힌 경우 제거 (예: https://x.com/...)).
    normalized = trimmed.rstrip(').,')
    return normalized


def _extract_text_from_oembed(html_fragment: str) -> str:
    if not html_fragment:
        return ''

    cleaned = bleach.clean(html_fragment, tags=[], strip=True)
    # 연속 공백을 단일 공백으로 축약하고 HTML 엔티티를 복원.
    text = re.sub(r'\s+', ' ', html.unescape(cleaned)).strip()
    return text


def find_x_post_url(text: str) -> Optional[str]:
    if not text:
        return None

    match = X_POST_URL_RE.search(text)
    if not match:
        return None

    return normalize_x_post_url(match.group(0)) or None


def fetch_x_post_preview(url: str) -> dict:
    normalized_url = normalize_x_post_url(url)
    if not normalized_url or not X_POST_URL_RE.fullmatch(normalized_url):
        raise ValueError('X(트위터) 게시글 주소만 미리보기 할 수 있습니다.')

    try:
        response = requests.get(
            X_OEMBED_ENDPOINT,
            params={
                'url': normalized_url,
                'omit_script': 'true',
                'hide_thread': 'true',
            },
            timeout=X_OEMBED_TIMEOUT,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError('X 게시글 정보를 불러오지 못했습니다.') from exc

    try:
        payload = response.json()
    except ValueError as exc:  # pragma: no cover - requests already validates JSON
        raise RuntimeError('X 게시글 정보를 불러오지 못했습니다.') from exc

    text = _extract_text_from_oembed(payload.get('html'))
    if not text:
        raise RuntimeError('X 게시글 본문을 찾을 수 없습니다.')

    return {
        'url': normalized_url,
        'text': text,
        'author_name': payload.get('author_name'),
        'author_url': payload.get('author_url'),
        'provider_name': payload.get('provider_name'),
        'provider_url': payload.get('provider_url'),
        'thumbnail_url': payload.get('thumbnail_url'),
    }


@dataclass
class ProcessedImage:
    original_name: str
    file: ContentFile
    width: int
    height: int


def user_has_purchased_product(user, product) -> bool:
    """사용자가 해당 상품을 구매했는지 확인"""
    if not user.is_authenticated:
        return False

    qualified_statuses = tuple(QUALIFIED_ORDER_STATUSES)
    purchase_qs = OrderItem.objects.filter(
        product=product,
        order__user=user,
        order__status__in=qualified_statuses,
    )
    if purchase_qs.exists():
        return True

    return PurchaseHistory.objects.filter(
        user=user,
        order__items__product=product,
        order__status__in=qualified_statuses,
    ).exists()


def get_paginated_reviews(product, page_number=None):
    """리뷰 목록과 통계 정보를 페이지네이션과 함께 반환"""
    reviews_qs = (
        Review.objects.filter(product=product)
        .select_related('author')
        .prefetch_related('images')
        .order_by('-created_at', '-id')
    )

    paginator = Paginator(reviews_qs, REVIEWS_PER_PAGE)
    reviews_page = paginator.get_page(page_number or 1)

    stats = reviews_qs.aggregate(avg_rating=Avg('rating'))
    average_rating = stats.get('avg_rating') or 0
    total_reviews = paginator.count

    return {
        'reviews_page': reviews_page,
        'review_average': average_rating,
        'review_total': total_reviews,
    }


def build_reviews_url(store_id: str, product_id: int, page_number=None) -> dict:
    """리뷰 앵커 페이지로 이동하기 위한 URL 정보를 구성"""
    base_url = reverse('products:product_detail', args=[store_id, product_id])

    try:
        page_int = int(page_number) if page_number is not None else 1
    except (TypeError, ValueError):
        page_int = 1

    if page_int > 1:
        base_url = f"{base_url}?page={page_int}"

    return {
        'path': base_url,
        'anchor': f"{base_url}#reviews",
        'page': max(page_int, 1),
    }


def process_image(uploaded_file: UploadedFile) -> ProcessedImage:
    """업로드된 이미지를 webp로 변환하며 사이즈 조정"""
    _log(
        "이미지 처리 시작",
        file_name=uploaded_file.name,
        file_size=getattr(uploaded_file, 'size', None),
        content_type=getattr(uploaded_file, 'content_type', None),
    )
    try:
        image = Image.open(uploaded_file)
    except Exception as exc:  # pragma: no cover - Pillow raises various errors
        _log("이미지 열기 실패", level=logging.ERROR, file_name=uploaded_file.name, error=str(exc))
        raise ValidationError(f"이미지 파일을 열 수 없습니다: {exc}") from exc

    image = ImageOps.exif_transpose(image)

    if image.mode not in ('RGB', 'RGBA'):
        image = image.convert('RGB')

    width, height = image.size
    if width > MAX_REVIEW_IMAGE_WIDTH:
        ratio = MAX_REVIEW_IMAGE_WIDTH / width
        new_size = (
            MAX_REVIEW_IMAGE_WIDTH,
            int(round(height * ratio)),
        )
        image = image.resize(new_size, Image.Resampling.LANCZOS)
        width, height = image.size
        _log("이미지 리사이즈", file_name=uploaded_file.name, width=width, height=height)

    output = io.BytesIO()
    image.save(output, format='WEBP', quality=WEBP_QUALITY, method=6)
    output.seek(0)

    filename = f"{uuid.uuid4().hex}.webp"
    processed_file = ContentFile(output.getvalue(), name=filename)

    _log(
        "이미지 처리 완료",
        original_name=uploaded_file.name,
        processed_name=filename,
        width=width,
        height=height,
    )

    return ProcessedImage(
        original_name=uploaded_file.name,
        file=processed_file,
        width=width,
        height=height,
    )


def upload_review_images(files: Iterable[UploadedFile], product, existing_count: int = 0) -> List[dict]:
    """후기 이미지 업로드 처리"""
    files = list(files)

    if existing_count + len(files) > MAX_IMAGES_PER_REVIEW:
        raise ValidationError(f"이미지는 최대 {MAX_IMAGES_PER_REVIEW}개까지 업로드할 수 있습니다.")

    uploaded: List[dict] = []
    _log(
        "이미지 업로드 시작",
        product_id=getattr(product, 'id', None),
        file_count=len(files),
        existing_count=existing_count,
    )
    try:
        for uploaded_file in files:
            _log(
                "이미지 처리 준비",
                file_name=uploaded_file.name,
                size=getattr(uploaded_file, 'size', None),
            )
            processed = process_image(uploaded_file)
            upload_result = upload_file_to_s3(
                processed.file,
                prefix=f"reviews/{product.id}",
            )
            if not upload_result.get('success'):
                _log(
                    "이미지 업로드 실패",
                    level=logging.ERROR,
                    file_name=uploaded_file.name,
                    error=upload_result.get('error'),
                )
                raise ValidationError(upload_result.get('error', '이미지 업로드에 실패했습니다.'))

            uploaded.append(
                {
                    'original_name': processed.original_name,
                    'file_path': upload_result['file_path'],
                    'file_url': upload_result['file_url'],
                    'width': processed.width,
                    'height': processed.height,
                }
            )
            _log(
                "이미지 업로드 성공",
                file_name=processed.original_name,
                file_path=upload_result['file_path'],
            )
    except Exception as exc:
        _log("이미지 업로드 예외", level=logging.ERROR, error=str(exc))
        for data in uploaded:
            delete_file_from_s3(data['file_path'])
        if isinstance(exc, ValidationError):
            raise
        raise ValidationError('이미지 업로드 처리 중 오류가 발생했습니다.') from exc

    return uploaded


def create_review_images(review: Review, uploaded_images: List[dict]) -> List[ReviewImage]:
    """ReviewImage 레코드 생성"""
    review_images: List[ReviewImage] = []
    start_order = review.images.count()

    for index, data in enumerate(uploaded_images, start=start_order):
        review_images.append(
            ReviewImage.objects.create(
                review=review,
                original_name=data['original_name'],
                file_path=data['file_path'],
                file_url=data['file_url'],
                width=data.get('width'),
                height=data.get('height'),
                order=index,
            )
        )
        _log(
            "ReviewImage 레코드 생성",
            review_id=review.id,
            image_path=data['file_path'],
            order=index,
        )

    return review_images


def delete_review_image(review_image: ReviewImage) -> None:
    """ReviewImage 삭제와 스토리지에서 제거"""
    if review_image.file_path:
        delete_file_from_s3(review_image.file_path)
    review_image.delete()
