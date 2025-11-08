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


def _format_sats(value) -> str:
    try:
        amount = int(value)
    except (TypeError, ValueError):
        return "-"
    return f"{amount:,} sats"


def _normalize_value(value, default: str = "-") -> str:
    if value in (None, "", []):
        return default
    return str(value)


def _build_contract_overview(payload: Dict) -> List[str]:
    lines = ["===== 계약 개요 ====="]
    lines.append(f"역할: {payload.get('role_display') or '-'}")
    start = _normalize_value(payload.get("start_date"), "미정")
    end = _normalize_value(payload.get("end_date"), "미정")
    lines.append(f"계약 기간: {start} ~ {end}")
    lines.append(f"총 금액: {_format_sats(payload.get('amount_sats'))}")
    lines.append(f"지급 방식: {payload.get('payment_display') or '-'}")
    lines.append(f"의뢰자 라이트닝 주소: {payload.get('client_lightning_address') or '-'}")
    lines.append(f"수행자 라이트닝 주소: {payload.get('performer_lightning_address') or '-'}")
    work_log = payload.get("work_log_markdown")
    if work_log:
        lines.append("")
        lines.append("작업 메모")
        for note_line in _markdown_to_text_lines(work_log):
            lines.append(f"  {note_line}" if note_line else "")
    return lines


def _build_milestone_lines(payload: Dict) -> List[str]:
    lines: List[str] = []
    milestones = payload.get("milestones") or []
    if milestones:
        lines.append("")
        lines.append("===== 분할 지급 내역 =====")
        for index, milestone in enumerate(milestones, start=1):
            amount = _format_sats(milestone.get("amount_sats") or milestone.get("amount"))
            due_date = _normalize_value(milestone.get("due_date"), "미정")
            condition = _normalize_value(milestone.get("condition"), "지급 조건 미입력")
            lines.append(f"{index}. {amount} / 지급일: {due_date}")
            lines.append(f"   조건: {condition}")
    elif payload.get("payment_type") == "one_time":
        lines.append("")
        lines.append("===== 일괄 지급 내역 =====")
        lines.append(f"지급일: {payload.get('one_time_due_date') or '미정'}")
        lines.append(f"지급 조건: {payload.get('one_time_condition') or '지급 조건 미입력'}")
    return lines


def _markdown_to_text_lines(markdown_text: str) -> List[str]:
    if not markdown_text:
        return []
    lines: List[str] = []
    in_code_block = False
    for raw_line in markdown_text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if not stripped:
            lines.append("")
            continue
        if in_code_block:
            lines.append(f"    {line}")
            continue
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
            if heading:
                lines.append(heading)
                lines.append("-" * len(heading))
            continue
        if stripped[0].isdigit():
            parts = stripped.split(".", 1)
            if len(parts) > 1 and parts[0].isdigit():
                lines.append(f"{parts[0]}. {parts[1].strip()}")
                continue
        if stripped[0] in {"-", "*", "+"}:
            lines.append(f"• {stripped[1:].strip()}")
            continue
        if stripped.startswith(">"):
            lines.append(f"> {stripped.lstrip('> ').strip()}")
            continue
        lines.append(line.strip())
    return lines


def _write_lines(pdf, text_object, lines: List[str], font_name: str, margin, height):
    for line in lines:
        text_object.textLine(line)
        if text_object.getY() <= margin:
            pdf.drawText(text_object)
            pdf.showPage()
            text_object = pdf.beginText(margin, height - margin)
            text_object.setFont(font_name, 11)
    return text_object


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

    intro_lines = [
        "SatoShop Expert - 전자 계약서",
        f"제목: {payload.get('title', '-')}",
        f"공유 ID: {document.slug}",
        "",
    ]
    text_object = _write_lines(pdf, text_object, intro_lines, font_name, margin, height)

    overview_lines = _build_contract_overview(payload)
    text_object = _write_lines(pdf, text_object, overview_lines, font_name, margin, height)

    contract_lines = _markdown_to_text_lines(contract_markdown)
    if contract_lines:
        text_object = _write_lines(
            pdf,
            text_object,
            ["", "===== 계약 본문 ====="],
            font_name,
            margin,
            height,
        )
        text_object = _write_lines(pdf, text_object, contract_lines, font_name, margin, height)

    milestone_lines = _build_milestone_lines(payload)
    if milestone_lines:
        text_object = _write_lines(pdf, text_object, milestone_lines, font_name, margin, height)

    footer_lines = [
        "",
        "===== 서명/해시 =====",
        f"의뢰자 서명 해시: {document.creator_hash or '-'}",
        f"수행자 서명 해시: {document.counterparty_hash or '-'}",
        f"사토샵 서명 해시: {document.mediator_hash or '-'}",
        "",
        f"PDF 생성 시각: {timezone.localtime(timezone.now()).strftime('%Y-%m-%d %H:%M:%S')}",
    ]
    text_object = _write_lines(pdf, text_object, footer_lines, font_name, margin, height)

    pdf.drawText(text_object)
    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    filename = f"direct-contract-{document.slug}.pdf"
    return ContentFile(buffer.getvalue(), name=filename)
