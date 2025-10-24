from __future__ import annotations

import json
import logging
from typing import Any, Optional

from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey

from wiki.services import (
    ChatClientError,
    EmbeddingClientError,
    RAGResult,
    run_rag_pipeline,
)

logger = logging.getLogger(__name__)


def _verify_discord_signature(request: HttpRequest) -> bool:
    public_key = getattr(settings, "WIKI_DISCORD_PUBLIC_KEY", "")
    if not public_key:
        logger.error("Discord 공개 키가 설정되어 있지 않습니다.")
        return False

    signature = request.META.get("HTTP_X_SIGNATURE_ED25519")
    timestamp = request.META.get("HTTP_X_SIGNATURE_TIMESTAMP")

    if not signature or not timestamp:
        logger.warning("요청 헤더에 디스코드 시그니처가 없습니다.")
        return False

    try:
        verify_key = VerifyKey(bytes.fromhex(public_key))
        verify_key.verify(timestamp.encode() + request.body, bytes.fromhex(signature))
    except (BadSignatureError, ValueError) as exc:
        logger.warning("디스코드 시그니처 검증 실패: %s", exc)
        return False

    return True


def _build_ephemeral_message(content: str) -> JsonResponse:
    return JsonResponse(
        {
            "type": 4,
            "data": {
                "content": content,
                "flags": 64,  # ephemeral
            },
        }
    )


def _format_sources(result: RAGResult) -> str:
    if not result.sources:
        return "관련 위키 문서를 찾지 못했습니다."

    lines = ["관련 위키 문서:"]
    for idx, source in enumerate(result.sources, start=1):
        similarity = f"{source.similarity:.2f}"
        tags = ", ".join(source.tags) if source.tags else "태그 없음"
        lines.append(f"{idx}. {source.title} (유사도 {similarity}, {tags})")
    return "\n".join(lines)


def _compose_response_message(result: RAGResult) -> str:
    sections = [result.answer.strip() or "답변을 생성하지 못했습니다."]
    sections.append("")
    sections.append(_format_sources(result))
    message = "\n".join(sections).strip()
    return _truncate_for_discord(message)


def _truncate_for_discord(message: str, limit: int = 1900) -> str:
    if len(message) <= limit:
        return message
    logger.warning("디스코드 응답이 길어 잘라냅니다. 길이: %s", len(message))
    return f"{message[:limit]}..."


def _extract_question(payload: dict[str, Any]) -> Optional[str]:
    data = payload.get("data", {})
    options = data.get("options") or []
    if not options:
        return None
    first_option = options[0]
    return first_option.get("value")


@csrf_exempt
@require_http_methods(["POST"])
def discord_interaction_view(request: HttpRequest) -> JsonResponse:
    if not _verify_discord_signature(request):
        return JsonResponse({"error": "signature verification failed"}, status=401)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid payload"}, status=400)

    if payload.get("type") == 1:
        # Discord PING
        return JsonResponse({"type": 1})

    if payload.get("type") != 2:
        return JsonResponse({"error": "unsupported interaction type"}, status=400)

    command_name = payload.get("data", {}).get("name")
    expected_command = getattr(settings, "WIKI_DISCORD_COMMAND_NAME", "qna")
    if command_name != expected_command:
        return _build_ephemeral_message(f"지원하지 않는 명령입니다: {command_name}")

    question = _extract_question(payload)
    if not question:
        return _build_ephemeral_message("질문 내용을 찾을 수 없습니다. 다시 시도해주세요.")

    try:
        result = run_rag_pipeline(question)
    except (EmbeddingClientError, ChatClientError) as exc:
        logger.error("RAG 파이프라인 처리 중 오류: %s", exc)
        return _build_ephemeral_message("위키 검색 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")

    response_content = _compose_response_message(result)
    return _build_ephemeral_message(response_content)
