"""Utilities for generating Expert contract preview payloads and documents."""
from __future__ import annotations

import copy
import secrets
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Optional

from django.utils import timezone

DEFAULT_CONTRACT_BODY = """## 1. 목적\n\n본 계약은 Blink API 연동 PoC를 위한 UI/결제 프로토타입 제작을 목적으로 합니다.\n\n## 2. 산출물\n\n1. 모바일/데스크톱 공용 결제 위젯 디자인\n2. LNURL-auth 가이드 문서\n3. QA 체크리스트\n\n## 3. 일정 및 커뮤니케이션\n\n- 주 2회 진행 상황 공유 (화/목)\n- 급한 이슈는 Mattermost expert-support 채널 이용\n\n## 4. 비밀 유지\n\n테스트에 사용된 Blink 자격 증명과 계약 초안은 외부 공유를 금지합니다.\n"""

DEFAULT_WORKLOG_FALLBACK = """# 계약서 (Agreement)\n\n---\n\n## 제1조 목적\n본 계약은 [계약의 목적 요약]을 위하여 계약 당사자 간의 권리와 의무를 명확히 규정함을 목적으로 한다.\n\n---\n\n## 제2조 계약 당사자\n- **갑 (계약자)**: [이름 / 상호]  \\n  주소: [주소]  \\n  연락처: [전화번호 / 이메일]\n\n- **을 (수행자)**: [이름 / 상호]  \\n  주소: [주소]  \\n  연락처: [전화번호 / 이메일]\n\n---\n\n## 제3조 계약 기간\n- 계약 기간: [시작일] ~ [종료일]  \\n- 연장 또는 해지는 상호 서면 합의에 따른다.\n\n---\n\n## 제4조 계약 금액 및 지급 조건\n- 총 계약금액: ₩[금액]  \\n- 지급 조건: [예: 선금 %, 중도금 %, 잔금 지급 시점 등]  \\n- 지급 방식: [계좌이체 / 비트코인 / 기타]\n\n---\n\n## 제5조 업무 범위\n- [업무 또는 용역의 구체적 내용 요약]\n- [제공물 및 납품 형태 명시 (예: 문서, 결과물, 코드 등)]\n\n---\n\n## 제6조 비밀유지\n계약 수행 중 취득한 모든 정보는 제3자에게 누설하거나 사용해서는 안 된다.\n\n---\n\n## 제7조 지적재산권\n성과물의 저작권 및 소유권은 [갑/을]에게 귀속된다. 단, 사전 서면 합의 시 예외를 둘 수 있다.\n\n---\n\n## 제8조 계약 해지\n다음 각 항에 해당하는 경우 일방은 계약을 해지할 수 있다.\n1. 계약 조건을 중대하게 위반한 경우  \\n2. 지급 지연이 [n일] 이상 지속된 경우  \\n3. 천재지변 등 불가항력 사유 발생 시\n\n---\n\n## 제9조 손해배상\n계약 위반으로 손해가 발생한 경우, 위반 당사자는 상대방에게 그 손해를 배상하여야 한다.\n\n---\n\n## 제10조 분쟁 해결\n분쟁 발생 시 상호 협의하되, 협의가 이루어지지 않을 경우 [관할 법원 명시]에 제소한다.\n\n---\n\n## 서명\n본 계약의 내용을 확인하고 이에 동의하여 서명한다.\n\n| 구분 | 성명(상호) | 서명(날인) | 날짜 |\n|------|-------------|-------------|-------|\n| 갑 | | | |\n| 을 | | | |\n\n---\n\n(작성일: [YYYY-MM-DD])"""

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
