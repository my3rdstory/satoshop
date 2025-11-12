#!/usr/bin/env python
import os
import secrets
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "satoshop.settings")

import django  # noqa: E402

django.setup()

from expert.contract_flow import render_contract_pdf  # noqa: E402

DOCS_DIR = (BASE_DIR / "expert" / "docs")
DOCS_DIR.mkdir(parents=True, exist_ok=True)
WORKLOG_MD_PATH = DOCS_DIR / "sample_worklog.md"


class DummyDocument(SimpleNamespace):
    """간단한 계약 객체 Mock."""


def build_sample_document() -> DummyDocument:
    payload = {
        "title": "Blink 인보이스 연계 PoC",
        "role_display": "의뢰자 (Client)",
        "start_date": "2025-11-05",
        "end_date": "2025-11-20",
        "amount_sats": "150000",
        "payment_display": "분할 지급",
        "email_recipient": "creator@example.com",
        "performer_lightning_address": "performer@ln.example",
        "creator_lightning_id": "creator@ln.example",
        "counterparty_lightning_id": "counterparty@ln.example",
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
        "work_log_markdown": WORKLOG_MD_PATH.read_text(encoding="utf-8"),
    }
    return DummyDocument(
        payload=payload,
        slug="sample-contract",
        creator_hash="CREATOR-HASH-PLACEHOLDER",
        counterparty_hash="COUNTERPARTY-HASH-PLACEHOLDER",
        mediator_hash="MEDIATOR-HASH-PLACEHOLDER",
    )


def main():
    document = build_sample_document()
    contract_markdown = """
## 1. 목적

본 계약은 Blink API 연동 PoC를 위한 UI/결제 프로토타입 제작을 목적으로 한다.

## 2. 산출물

1. 모바일/데스크톱 공용 결제 위젯 디자인
2. LNURL-auth 가이드 문서
3. QA 체크리스트

## 3. 일정 및 커뮤니케이션

- 주 2회 진행 상황 공유 (화/목)
- 급한 이슈는 Mattermost expert-support 채널 이용

## 4. 비밀 유지

테스트에 사용된 Blink 자격 증명, 계약 초안은 외부 공유를 금지한다.
"""
    output = render_contract_pdf(document, contract_markdown)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    suffix = secrets.token_hex(3)
    output_path = DOCS_DIR / f"expert-worklog-sample-{timestamp}-{suffix}.pdf"
    with output_path.open("wb") as fp:
        fp.write(output.read())
    print(f"[✓] 샘플 계약 PDF 생성: {output_path}")


if __name__ == "__main__":
    main()
