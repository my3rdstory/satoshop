import base64
import hashlib
import io
import json
import secrets
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, Tuple, List

from django.core.files.base import ContentFile
from django.utils import timezone

from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

BASE_DIR = Path(__file__).resolve().parent
FONT_BUNDLE_DIR = BASE_DIR / "fonts"


def _bundle_font_candidates() -> List[Path]:
    if not FONT_BUNDLE_DIR.exists():
        return []
    candidates: List[Path] = []
    for pattern in ("*.ttf", "*.otf"):
        candidates.extend(sorted(FONT_BUNDLE_DIR.glob(pattern)))
    return candidates


FONT_CANDIDATES = _bundle_font_candidates() + [
    Path("/usr/share/fonts/truetype/noto/NotoSansCJKkr-Regular.otf"),
    Path("/usr/share/fonts/truetype/noto/NotoSansKR-Regular.ttf"),
]

CID_FONT_CANDIDATES = [
    "HYSMyeongJo-Medium",
    "HYGoThic-Medium",
]

LATIN_FONT_CANDIDATES = [
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
]


@dataclass
class HashResult:
    value: str
    meta: Dict[str, str]


def generate_share_slug(length: int = 16) -> str:
    """공유 URL로 사용할 짧은 슬러그 생성."""
    raw = secrets.token_urlsafe(length)
    return raw.replace("-", "").replace("_", "")[:length]


def decode_signature_data(data_url: str, filename_prefix: str) -> ContentFile:
    """dataURL 형식의 서명 이미지를 ContentFile로 변환."""
    header, data = data_url.split(",", 1)
    extension = "png"
    if ";base64" in header:
        mime = header.split(";")[0]
        if "/" in mime:
            extension = mime.split("/")[1]
    binary = base64.b64decode(data)
    timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
    filename = f"{filename_prefix}-{timestamp}.{extension}"
    return ContentFile(binary, name=filename)


def _build_hash_payload(base_payload: Dict[str, str]) -> Tuple[str, Dict[str, str]]:
    timestamp = timezone.now()
    payload = {
        **base_payload,
        "timestamp": timestamp.isoformat(),
        "salt": secrets.token_hex(16),
    }
    base_string = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha256(base_string.encode("utf-8")).hexdigest()
    payload["hash"] = digest
    return digest, payload


def build_creator_hash(contract_payload: Dict, user_agent: str) -> HashResult:
    digest, meta = _build_hash_payload(
        {
            "stage": "creator",
            "payload": contract_payload,
            "user_agent": user_agent or "unknown",
        }
    )
    return HashResult(value=digest, meta=meta)


def build_counterparty_hash(creator_hash: str, user_agent: str) -> HashResult:
    digest, meta = _build_hash_payload(
        {
            "stage": "counterparty",
            "creator_hash": creator_hash,
            "user_agent": user_agent or "unknown",
        }
    )
    return HashResult(value=digest, meta=meta)


def build_mediator_hash(counterparty_hash: str) -> HashResult:
    digest, meta = _build_hash_payload(
        {
            "stage": "mediator",
            "counterparty_hash": counterparty_hash,
            "evidence": "final_pdf",
        }
    )
    return HashResult(value=digest, meta=meta)


@lru_cache(maxsize=None)
def resolve_contract_pdf_font(default: str = "Helvetica") -> str:
    for path in FONT_CANDIDATES:
        if not path.exists():
            continue
        font_name = f"SatoContract-{path.stem}"
        try:
            pdfmetrics.getFont(font_name)
            return font_name
        except KeyError:
            try:
                pdfmetrics.registerFont(TTFont(font_name, str(path)))
                return font_name
            except Exception:
                continue
        except Exception:
            continue

    for cid_font in CID_FONT_CANDIDATES:
        try:
            pdfmetrics.getFont(cid_font)
            return cid_font
        except KeyError:
            try:
                pdfmetrics.registerFont(UnicodeCIDFont(cid_font))
                return cid_font
            except Exception:
                continue
        except Exception:
            continue

    for path in LATIN_FONT_CANDIDATES:
        if not path.exists():
            continue
        font_name = f"SatoContract-{path.stem}"
        try:
            pdfmetrics.getFont(font_name)
            return font_name
        except KeyError:
            try:
                pdfmetrics.registerFont(TTFont(font_name, str(path)))
                return font_name
            except Exception:
                continue
        except Exception:
            continue

    return default


def render_contract_pdf(document, contract_markdown: str) -> ContentFile:
    """ReportLab을 활용해 간단한 계약서 PDF를 생성."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 18 * mm
    text_object = pdf.beginText(margin, height - margin)
    font_name = resolve_contract_pdf_font()
    text_object.setFont(font_name, 11)
    payload = document.payload or {}

    header_lines = [
        "SatoShop Expert - 전자 계약서",
        f"제목: {payload.get('title', '-')}",
        f"공유 ID: {document.slug}",
        "",
        "===== 계약 개요 =====",
        json.dumps(payload, ensure_ascii=False, indent=2),
        "의뢰자 라이트닝 주소: {}".format(payload.get("client_lightning_address") or "-"),
        "수행자 라이트닝 주소: {}".format(payload.get("performer_lightning_address") or "-"),
        "",
        "===== 계약 일반 사항 =====",
    ]

    for line in header_lines:
        text_object.textLine(line)

    for line in contract_markdown.splitlines():
        text_object.textLine(line)
        if text_object.getY() <= margin:
            pdf.drawText(text_object)
            pdf.showPage()
            text_object = pdf.beginText(margin, height - margin)
            text_object.setFont(font_name, 11)

    milestones = payload.get("milestones") or []
    if milestones:
        text_object.textLine("")
        text_object.textLine("===== 분할 지급 내역 =====")
        for index, milestone in enumerate(milestones, start=1):
            amount = milestone.get("amount_sats") or milestone.get("amount") or 0
            due_date = milestone.get("due_date") or "미정"
            condition = milestone.get("condition") or "지급 조건 미입력"
            text_object.textLine(f"{index}. {amount} sats / 지급일: {due_date} / 조건: {condition}")
            if text_object.getY() <= margin:
                pdf.drawText(text_object)
                pdf.showPage()
                text_object = pdf.beginText(margin, height - margin)
                text_object.setFont(font_name, 11)

    if payload.get("payment_type") == "one_time":
        text_object.textLine("")
        text_object.textLine("===== 일괄 지급 내역 =====")
        text_object.textLine(f"지급일: {payload.get('one_time_due_date') or '미정'}")
        text_object.textLine(f"지급 조건: {payload.get('one_time_condition') or '지급 조건 미입력'}")

    footer_lines = [
        "",
        "===== 서명/해시 =====",
        f"의뢰자 서명 해시: {document.creator_hash or '-'}",
        f"수행자 서명 해시: {document.counterparty_hash or '-'}",
        f"사토샵 서명 해시: {document.mediator_hash or '-'}",
        "",
        f"PDF 생성 시각: {timezone.localtime(timezone.now()).strftime('%Y-%m-%d %H:%M:%S')}",
    ]
    for line in footer_lines:
        text_object.textLine(line)

    pdf.drawText(text_object)
    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    filename = f"direct-contract-{document.slug}.pdf"
    return ContentFile(buffer.getvalue(), name=filename)
