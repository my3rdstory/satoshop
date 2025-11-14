#!/usr/bin/env python
import os
import secrets
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "satoshop.settings")

import django  # noqa: E402

django.setup()

from expert.contract_flow import render_contract_pdf  # noqa: E402
from expert.pdf_preview import (  # noqa: E402
    DEFAULT_CONTRACT_BODY,
    build_preview_document,
    build_preview_payload,
)

DOCS_DIR = (BASE_DIR / "expert" / "docs")
DOCS_DIR.mkdir(parents=True, exist_ok=True)


def main():
    payload = build_preview_payload()
    document = build_preview_document(payload)
    contract_markdown = DEFAULT_CONTRACT_BODY
    output = render_contract_pdf(document, contract_markdown)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    suffix = secrets.token_hex(3)
    output_path = DOCS_DIR / f"expert-worklog-sample-{timestamp}-{suffix}.pdf"
    with output_path.open("wb") as fp:
        fp.write(output.read())
    print(f"[✓] 샘플 계약 PDF 생성: {output_path}")


if __name__ == "__main__":
    main()
