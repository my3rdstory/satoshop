import json
import logging
import mimetypes
import os
from typing import Iterable, List, Tuple
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import FileSystemStorage
from django.utils import timezone

from stores.models import BahPromotionRequest

from .models import DiscordBot
from storage.backends import S3Storage

logger = logging.getLogger(__name__)

DISCORD_API_BASE = "https://discord.com/api/v10"
DISCORD_MESSAGE_LIMIT = 1900
DISCORD_MAX_ATTACHMENTS = 10


def _split_message(text: str, max_length: int = DISCORD_MESSAGE_LIMIT) -> List[str]:
    if len(text) <= max_length:
        return [text]

    lines = text.splitlines()
    chunks: List[str] = []
    current = ''

    for line in lines:
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) > max_length:
            if current:
                chunks.append(current)
                current = line
            else:
                while len(line) > max_length:
                    chunks.append(line[:max_length])
                    line = line[max_length:]
                current = line
        else:
            current = candidate

    if current:
        chunks.append(current)

    return chunks


def _build_bah_promotion_message(
    promotion_request: BahPromotionRequest,
    *,
    is_new: bool,
) -> Tuple[str, List[str]]:
    status = '신규' if is_new else '수정'
    created_at = timezone.localtime(promotion_request.updated_at).strftime('%Y-%m-%d %H:%M:%S')
    address_parts = [
        promotion_request.postal_code,
        promotion_request.address,
        promotion_request.address_detail,
    ]
    address_text = ' '.join([part for part in address_parts if part])

    lines = [
        f'BAH 홍보요청 {status} 접수',
        '',
        f'요청 종류: {status}',
        f'요청 ID: {promotion_request.id}',
        f'신청 저장 시각: {created_at}',
        '',
        '매장 정보',
        f'- 매장명: {promotion_request.store_name}',
        f'- 전화번호: {promotion_request.phone_number}',
        f'- 이메일: {promotion_request.email}',
        f'- 주소: {address_text}',
        f'- 라이트닝 인증: {"완료" if promotion_request.has_lightning_verification else "미완료"}',
    ]

    if promotion_request.lightning_public_key:
        lines.append(f'- 라이트닝 공개키: {promotion_request.lightning_public_key}')

    lines.extend([
        '',
        '소개 내용',
        promotion_request.introduction or '',
    ])

    image_urls = list(
        promotion_request.images.order_by('order', 'uploaded_at').values_list('file_url', flat=True)
    )
    if image_urls:
        lines.extend(['', '이미지 링크'] + [f'- {url}' for url in image_urls])

    return '\n'.join(lines), image_urls


def _build_image_embeds(image_urls: Iterable[str]) -> List[dict]:
    embeds: List[dict] = []
    for index, url in enumerate(image_urls):
        if not url:
            continue
        normalized = _normalize_image_url(url)
        if not normalized:
            logger.warning('디스코드 임베드 이미지 URL 무시됨: %s', url)
            continue
        embeds.append({
            'title': f'첨부 이미지 {index + 1}',
            'image': {'url': normalized},
        })
    return embeds


def _normalize_image_url(url: str) -> str | None:
    candidate = url.strip()
    if not candidate:
        return None
    if candidate.startswith('//'):
        candidate = f'https:{candidate}'
    parsed = urlparse(candidate)
    if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
        return None
    return candidate


def _get_storage():
    s3_ready = all([
        getattr(settings, 'S3_ACCESS_KEY_ID', None),
        getattr(settings, 'S3_SECRET_ACCESS_KEY', None),
        getattr(settings, 'S3_BUCKET_NAME', None),
        getattr(settings, 'S3_ENDPOINT_URL', None),
    ])
    if s3_ready:
        try:
            return S3Storage()
        except ImproperlyConfigured:
            logger.warning('S3Storage 초기화 실패, 로컬 스토리지를 사용합니다.')
    return FileSystemStorage(location=settings.MEDIA_ROOT)


def _load_image_attachment(image, storage) -> Tuple[str, bytes, str] | None:
    file_path = getattr(image, 'file_path', '')
    if not file_path:
        return None

    try:
        with storage.open(file_path, 'rb') as file_obj:
            data = file_obj.read()
    except Exception:
        logger.exception('디스코드 첨부용 이미지 읽기 실패: %s', file_path)
        return None

    if not data:
        logger.warning('디스코드 첨부용 이미지 데이터가 비었습니다: %s', file_path)
        return None

    filename = image.original_name or os.path.basename(file_path) or f"bah-image-{image.id}.bin"
    content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
    return filename, data, content_type


def _send_discord_message(
    bot_token: str,
    *,
    channel_id: str,
    content: str,
    embeds: List[dict] | None = None,
    attachments: List[Tuple[str, bytes, str]] | None = None,
) -> bool:
    if not bot_token or not channel_id:
        return False

    payload = {'content': content}
    if embeds:
        payload['embeds'] = embeds

    try:
        url = f"{DISCORD_API_BASE}/channels/{channel_id}/messages"
        headers = {'Authorization': f'Bot {bot_token}'}
        if attachments:
            attachment_files = attachments[:DISCORD_MAX_ATTACHMENTS]
            files = {}
            payload_attachments = []
            for index, (filename, data, content_type) in enumerate(attachment_files):
                files[f'files[{index}]'] = (filename, data, content_type)
                payload_attachments.append({'id': index, 'filename': filename})
            payload['attachments'] = payload_attachments
            response = requests.post(
                url,
                data={'payload_json': json.dumps(payload, ensure_ascii=False)},
                files=files,
                headers=headers,
                timeout=10,
            )
        else:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=10,
            )
        if response.status_code >= 400:
            logger.warning(
                '디스코드 메시지 전송 실패 (status=%s, channel=%s): %s',
                response.status_code,
                channel_id,
                response.text,
            )
            return False
    except Exception:
        logger.exception('디스코드 메시지 전송 중 예외 발생 (channel=%s)', channel_id)
        return False

    return True


def notify_bah_promotion_request(
    promotion_request: BahPromotionRequest,
    *,
    is_new: bool,
) -> None:
    bot = DiscordBot.get_active_bot()
    if not bot or not bot.token:
        logger.info('디스코드 봇 설정이 없어 알림을 건너뜁니다.')
        return

    channels = list(bot.channels.filter(is_active=True))
    if not channels:
        logger.info('디스코드 채널 설정이 없어 알림을 건너뜁니다.')
        return

    message_text, image_urls = _build_bah_promotion_message(promotion_request, is_new=is_new)
    message_chunks = _split_message(message_text)
    embeds = _build_image_embeds(image_urls)
    images = list(promotion_request.images.order_by('order', 'uploaded_at'))
    storage = _get_storage()
    attachments: List[Tuple[str, bytes, str]] = []
    for image in images:
        attachment = _load_image_attachment(image, storage)
        if attachment:
            attachments.append(attachment)

    for channel in channels:
        for idx, chunk in enumerate(message_chunks):
            _send_discord_message(
                bot.token,
                channel_id=channel.channel_id,
                content=chunk,
                embeds=embeds if idx == 0 else None,
            )
        if attachments:
            total = len(attachments)
            for idx, attachment in enumerate(attachments, start=1):
                _send_discord_message(
                    bot.token,
                    channel_id=channel.channel_id,
                    content=f'첨부 이미지 {idx}/{total}',
                    attachments=[attachment],
                )
