"""Utilities for generating Expert contract preview payloads and documents."""
from __future__ import annotations

import copy
import secrets
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Optional

from django.utils import timezone

DEFAULT_CONTRACT_BODY = """## 1. 목적\n\n본 계약은 Blink API 연동 PoC를 위한 UI/결제 프로토타입 제작을 목적으로 합니다.\n\n## 2. 산출물\n\n1. 모바일/데스크톱 공용 결제 위젯 디자인\n2. LNURL-auth 가이드 문서\n3. QA 체크리스트\n\n## 3. 일정 및 커뮤니케이션\n\n- 주 2회 진행 상황 공유 (화/목)\n- 급한 이슈는 Mattermost expert-support 채널 이용\n\n## 4. 비밀 유지\n\n테스트에 사용된 Blink 자격 증명과 계약 초안은 외부 공유를 금지합니다.\n"""

DEFAULT_WORKLOG_FALLBACK = """[2025-11-05] Blink 위젯 연동 범위와 대상 화면을 확정했습니다.
- 모바일/데스크톱 공용 위젯 필수 단계 정의
- 잔여 이슈: 결제 실패 플로우 문구 확정



[2025-11-07] 1차 UI 시안을 전달하고 수정 라운드를 진행했습니다.
* 전달물: Figma 링크, 모션 가이드 초안
* 요청 사항: CTA 문구 2안 비교 및 확정



[2025-11-10] Blink API 테스트 자격 증명을 수령해 연동 검증을 시작했습니다.
- 위젯 ↔ 백엔드 송수신 로그 점검
- QA 체크리스트 초안 작성 착수"""

DEFAULT_PAYLOAD: Dict[str, Any] = {
    "title": "Blink 인보이스 연계 PoC",
    "role_display": "의뢰자 (Client)",
    "start_date": "2025-11-05",
    "end_date": "2025-11-20",
    "amount_sats": "150000",
    "payment_display": "분할 지급",
    "performer_lightning_address": "performer@ln.example",
    "creator_lightning_id": "creator@ln.example",
    "counterparty_lightning_id": "counterparty@ln.example",
    "email_recipient": "creator@example.com",
    "milestones": [
        {
            "amount_sats": "50000",
            "due_date": "2025-11-07",
            "condition": "UI/UX 시안 전달",
        },
        {
            "amount_sats": "100000",
            "due_date": "2025-11-15",
            "condition": "테스트용 인보이스 발행 및 설명서 전달",
        },
    ],
    "work_log_markdown": DEFAULT_WORKLOG_FALLBACK,
}





def _sample_worklog_text() -> str:
    docs_path = Path(__file__).resolve().parent / "docs" / "sample_worklog.md"
    if docs_path.exists():
        try:
            return docs_path.read_text(encoding="utf-8")
        except Exception:  # pragma: no cover - fallback when file unreadable
            return DEFAULT_WORKLOG_FALLBACK
    return DEFAULT_WORKLOG_FALLBACK


def build_preview_payload(overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload = copy.deepcopy(DEFAULT_PAYLOAD)
    payload.setdefault("work_log_markdown", _sample_worklog_text())
    if overrides:
        payload.update(overrides)
        if "work_log_markdown" not in overrides:
            payload.setdefault("work_log_markdown", _sample_worklog_text())
    return payload


def build_preview_document(payload: Optional[Dict[str, Any]] = None):
    final_payload = payload or build_preview_payload()
    slug = final_payload.get("slug") or f"preview-{secrets.token_hex(4)}"
    now_hash = timezone.now().strftime("%Y%m%d%H%M%S")
    return SimpleNamespace(
        payload=final_payload,
        slug=slug,
        creator_hash=final_payload.get("creator_hash") or f"CREATOR-{now_hash}",
        creator_lightning_id=final_payload.get("creator_lightning_id") or final_payload.get("performer_lightning_address"),
        counterparty_hash=final_payload.get("counterparty_hash") or f"COUNTERPARTY-{now_hash}",
        counterparty_lightning_id=final_payload.get("counterparty_lightning_id") or final_payload.get("performer_lightning_address"),
        mediator_hash=final_payload.get("mediator_hash") or f"SYSTEM-{now_hash}",
    )

__all__ = [
    "DEFAULT_CONTRACT_BODY",
    "build_preview_payload",
    "build_preview_document",
]
