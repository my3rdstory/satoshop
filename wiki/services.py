from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, Sequence

from django.conf import settings
from django.db import transaction
from openai import OpenAI
from openai import OpenAIError
from pgvector.django import CosineDistance

from .models import WikiEmbedding, WikiEntry

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmbeddingResult:
    vector: Sequence[float]
    model: str
    provider: str


class EmbeddingClientError(RuntimeError):
    pass


class BaseEmbeddingClient:
    provider: str

    def embed(self, text: str) -> EmbeddingResult:
        raise NotImplementedError


class OpenAIEmbeddingClient(BaseEmbeddingClient):
    provider = "openai"

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model
        self._client = OpenAI(api_key=api_key)

    def embed(self, text: str) -> EmbeddingResult:
        try:
            response = self._client.embeddings.create(
                model=self._model,
                input=[text],
            )
        except OpenAIError as exc:  # pragma: no cover - network dependent
            logger.exception("OpenAI embedding 호출 중 오류가 발생했습니다.")
            raise EmbeddingClientError("임베딩 생성에 실패했습니다.") from exc

        data = response.data[0]
        model_name = getattr(response, "model", self._model)
        return EmbeddingResult(
            vector=data.embedding,
            model=model_name,
            provider=self.provider,
        )


def get_embedding_client() -> BaseEmbeddingClient:
    provider = getattr(settings, "WIKI_EMBEDDING_PROVIDER", "openai")
    if provider == "openai":
        api_key = getattr(settings, "WIKI_OPENAI_API_KEY", None)
        model = getattr(settings, "WIKI_OPENAI_EMBEDDING_MODEL", None)
        if not api_key:
            raise EmbeddingClientError("OpenAI API 키가 설정되지 않았습니다.")
        if not model:
            raise EmbeddingClientError("임베딩 모델이 설정되지 않았습니다.")
        return OpenAIEmbeddingClient(api_key=api_key, model=model)
    raise EmbeddingClientError(f"지원하지 않는 임베딩 제공자입니다: {provider}")


def build_entry_context(entry: WikiEntry) -> str:
    tags_line = ", ".join(entry.tags) if entry.tags else "없음"
    return (
        f"제목: {entry.title}\n"
        f"태그: {tags_line}\n"
        f"본문: {entry.content}"
    )


def refresh_entry_embedding(entry_id: int) -> None:
    """
    Generate or update embedding for a given wiki entry.
    """
    try:
        entry = WikiEntry.objects.get(pk=entry_id, is_published=True)
    except WikiEntry.DoesNotExist:
        logger.info("공개되지 않은 항목(%s)은 임베딩에서 제외합니다.", entry_id)
        delete_entry_embedding(entry_id)
        return

    try:
        client = get_embedding_client()
    except EmbeddingClientError as exc:
        logger.error("임베딩 클라이언트를 초기화하지 못했습니다: %s", exc)
        return

    payload = build_entry_context(entry)
    try:
        embedding_result = client.embed(payload)
    except EmbeddingClientError:
        return

    def _persist() -> None:
        WikiEmbedding.objects.update_or_create(
            entry=entry,
            defaults={
                "embedding": embedding_result.vector,
                "embedding_model": embedding_result.model,
                "provider": embedding_result.provider,
                "content_snapshot": payload,
            },
        )

    transaction.on_commit(_persist)


def delete_entry_embedding(entry_id: int) -> None:
    WikiEmbedding.objects.filter(entry_id=entry_id).delete()


class ChatClientError(RuntimeError):
    pass


class BaseChatClient:
    provider: str

    def complete(self, *, question: str, context: str, instructions: str) -> str:
        raise NotImplementedError


class OpenAIChatClient(BaseChatClient):
    provider = "openai"

    def __init__(self, api_key: str, model: str) -> None:
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def complete(self, *, question: str, context: str, instructions: str) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                temperature=0.1,
                messages=[
                    {
                        "role": "system",
                        "content": instructions,
                    },
                    {
                        "role": "user",
                        "content": (
                            "질문에 아래 위키 자료를 참고해 답변하세요.\n\n"
                            f"위키 자료:\n{context}\n\n질문: {question}"
                        ),
                    },
                ],
            )
        except OpenAIError as exc:  # pragma: no cover - network dependent
            logger.exception("OpenAI 대화형 모델 호출 중 오류가 발생했습니다.")
            raise ChatClientError("답변 생성에 실패했습니다.") from exc

        choice = response.choices[0]
        message = choice.message
        content = getattr(message, "content", "") if message else ""
        return content.strip()


def get_chat_client() -> BaseChatClient:
    provider = getattr(settings, "WIKI_CHAT_PROVIDER", "openai")
    if provider == "openai":
        api_key = getattr(settings, "WIKI_OPENAI_API_KEY", None)
        model = getattr(settings, "WIKI_OPENAI_COMPLETION_MODEL", None)
        if not api_key:
            raise ChatClientError("OpenAI API 키가 설정되지 않았습니다.")
        if not model:
            raise ChatClientError("대화형 모델이 설정되지 않았습니다.")
        return OpenAIChatClient(api_key=api_key, model=model)
    raise ChatClientError(f"지원하지 않는 챗봇 제공자입니다: {provider}")


@dataclass(frozen=True)
class RAGSource:
    entry_id: int
    title: str
    content: str
    tags: list[str]
    similarity: float


@dataclass(frozen=True)
class RAGResult:
    answer: str
    sources: list[RAGSource]


def retrieve_similar_entries(vector: Sequence[float], limit: int) -> list[RAGSource]:
    queryset = (
        WikiEmbedding.objects.select_related("entry")
        .filter(entry__is_published=True)
        .annotate(distance=CosineDistance("embedding", vector))
        .order_by("distance")[:limit]
    )

    sources: list[RAGSource] = []
    for embedding in queryset:
        entry = embedding.entry
        distance = getattr(embedding, "distance", 1.0)
        similarity = max(0.0, 1.0 - float(distance))
        sources.append(
            RAGSource(
                entry_id=entry.id,
                title=entry.title,
                content=entry.content,
                tags=list(entry.tags),
                similarity=similarity,
            )
        )
    return sources


def build_context_block(sources: Iterable[RAGSource]) -> str:
    lines: list[str] = []
    for source in sources:
        tags_line = ", ".join(source.tags) if source.tags else "태그 없음"
        lines.append(
            f"- 제목: {source.title}\n  태그: {tags_line}\n  내용: {source.content}"
        )
    return "\n".join(lines)


def run_rag_pipeline(question: str) -> RAGResult:
    try:
        embedding_client = get_embedding_client()
    except EmbeddingClientError as exc:
        logger.error("질문 임베딩 생성 실패: %s", exc)
        raise

    try:
        vector_result = embedding_client.embed(question)
    except EmbeddingClientError as exc:
        logger.error("질문 임베딩 생성 중 오류: %s", exc)
        raise

    limit = getattr(settings, "WIKI_MAX_CONTEXT_ITEMS", 3)
    sources = retrieve_similar_entries(vector_result.vector, limit=limit)

    context = build_context_block(sources) if sources else "관련 문서가 없습니다."
    custom_prompt = getattr(settings, "WIKI_SYSTEM_PROMPT", "").strip()
    instructions = custom_prompt or (
        "너는 사토샵 디스코드의 지식 베이스 위키를 기반으로 답변하는 조력자다. "
        "답변은 자연스럽고 간결하게 작성하되, 제공된 위키 자료에 근거해야 한다. "
        "근거가 없다면 모른다고 답하고, 허구의 정보를 만들어내지 않는다."
    )

    try:
        chat_client = get_chat_client()
    except ChatClientError as exc:
        logger.error("챗봇 클라이언트를 초기화하지 못했습니다: %s", exc)
        raise

    try:
        answer = chat_client.complete(
            question=question,
            context=context,
            instructions=instructions,
        )
    except ChatClientError as exc:
        logger.error("답변 생성 실패: %s", exc)
        raise

    return RAGResult(answer=answer, sources=sources)
