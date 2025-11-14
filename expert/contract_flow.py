import base64
import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Tuple

import markdown
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
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


def _register_bold_variant(font_name: str, font_path: Path):
    """가능한 경우 동일 경로의 Bold 폰트를 함께 등록."""
    candidates: List[Path] = []
    stem = font_path.stem
    suffix = font_path.suffix
    if "Regular" in stem:
        candidates.append(font_path.with_name(stem.replace("Regular", "Bold") + suffix))
    if "Medium" in stem:
        candidates.append(font_path.with_name(stem.replace("Medium", "Bold") + suffix))
    candidates.append(font_path.with_name(stem + "-Bold" + suffix))
    for candidate in candidates:
        if not candidate.exists():
            continue
        bold_name = f"{font_name}-Bold"
        try:
            pdfmetrics.registerFont(TTFont(bold_name, str(candidate)))
        except Exception:
            continue
        else:
            break




def _format_generated_at(payload: Dict) -> str:
    generated_at = payload.get("generated_at")
    if isinstance(generated_at, datetime):
        timestamp = generated_at
    elif generated_at:
        try:
            timestamp = datetime.fromisoformat(str(generated_at))
        except ValueError:
            return str(generated_at)
    else:
        timestamp = timezone.now()
    if timezone.is_naive(timestamp):
        timestamp = timezone.make_aware(timestamp, timezone.get_current_timezone())
    return timezone.localtime(timestamp).strftime("%Y-%m-%d %H:%M:%S")


def _escape_table_value(value: str) -> str:
    if value in (None, ""):
        return "-"
    text = str(value).replace("\r", "").replace("\n", "<br>")
    return text.replace("|", r"\|")


def _markdown_table(headers: List[str], rows: List[List[str]]) -> str:
    if not rows:
        return ""
    header_line = "| " + " | ".join(_escape_table_value(h) for h in headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    body = [
        "| " + " | ".join(_escape_table_value(cell) for cell in row) + " |"
        for row in rows
    ]
    return "\n".join([header_line, separator, *body])


def _build_intro_markdown(document, payload: Dict) -> str:
    contract_title = payload.get("title") or "SatoShop Expert 계약"
    created_label = _format_generated_at(payload)
    lines = [
        f"# {contract_title}",
        "_SatoShop Expert - 전자 계약서_",
        "",
        f"- **공유 ID**: `{document.slug}`",
        f"- **생성 시각**: {created_label}",
    ]
    return "\n".join(lines).strip()


def _build_overview_markdown(payload: Dict) -> str:
    role = payload.get("role_display") or "-"
    start = _normalize_value(payload.get("start_date"), "미정")
    end = _normalize_value(payload.get("end_date"), "미정")
    total = _format_sats(payload.get("amount_sats"))
    payment_type = payload.get("payment_display") or "-"
    performer_ln = payload.get("performer_lightning_address") or "-"
    rows = [
        ["역할", role],
        ["계약 기간", f"{start} ~ {end}"],
        ["총 금액", total],
        ["지급 방식", payment_type],
        ["수행자 라이트닝 주소", performer_ln],
    ]
    table = _markdown_table(["항목", "내용"], rows)
    return "\n\n".join(["## Ⅰ. 계약 개요", table]).strip()


def _format_milestones_markdown(payload: Dict) -> str:
    milestones = payload.get("milestones") or []
    if not milestones:
        return ""
    rows: List[List[str]] = []
    for index, milestone in enumerate(milestones, start=1):
        amount = _format_sats(milestone.get("amount_sats") or milestone.get("amount"))
        due_date = _normalize_value(milestone.get("due_date"), "미정")
        condition = _normalize_value(milestone.get("condition"), "지급 조건 미입력")
        rows.append([str(index), amount, due_date, condition])
    return _markdown_table(["#", "금액", "지급일", "조건"], rows)


def _format_one_time_payment_markdown(payload: Dict) -> str:
    if payload.get("payment_type") != "one_time":
        return ""
    value = payload.get("one_time_due_date") or "미정"
    condition = payload.get("one_time_condition") or "지급 조건 미입력"
    rows = [
        ["일괄 지급일", value],
        ["지급 조건", condition],
    ]
    return _markdown_table(["항목", "내용"], rows)


def _build_payment_markdown(payload: Dict) -> str:
    milestone_table = _format_milestones_markdown(payload)
    onetime_table = _format_one_time_payment_markdown(payload)
    sections: List[str] = []
    if milestone_table:
        sections.append("### 분할 지급 내역\n\n" + milestone_table)
    if (not milestone_table) and onetime_table:
        sections.append("### 일괄 지급 내역\n\n" + onetime_table)
    if not sections:
        return ""
    return "## 지급 정보\n\n" + "\n\n".join(sections)


def _build_worklog_markdown(payload: Dict) -> str:
    work_log = (payload or {}).get("work_log_markdown")
    if not work_log:
        return ""
    return "## 수행 내역\n\n" + work_log.strip()


def _build_contract_body_markdown(contract_markdown: str) -> str:
    if not contract_markdown:
        return ""
    body = contract_markdown.strip()
    if not body:
        return ""
    return "## Ⅱ. 계약 본문\n\n" + body


def _build_signature_markdown(document) -> str:
    payload = document.payload or {}
    rows = [
        ["의뢰자 서명 해시", document.creator_hash or "-"],
        ["의뢰자 라이트닝 ID", _format_lightning_value(document.creator_lightning_id or payload.get("creator_lightning_id", ""))],
        ["수행자 서명 해시", document.counterparty_hash or "-"],
        ["수행자 라이트닝 ID", _format_lightning_value(document.counterparty_lightning_id or payload.get("counterparty_lightning_id", ""))],
        ["중개자(시스템) 서명 해시", document.mediator_hash or "-"],
    ]
    table = _markdown_table(["항목", "값"], rows)
    timestamp = timezone.localtime(timezone.now()).strftime("%Y-%m-%d %H:%M:%S")
    return "\n\n".join(
        [
            "## Ⅲ. 서명 및 해시",
            table,
            f"PDF 생성 시각: {timestamp}",
        ]
    ).strip()


def _compose_contract_markdown(document, contract_markdown: str) -> str:
    payload = document.payload or {}
    sections = [
        _build_intro_markdown(document, payload),
        _build_overview_markdown(payload),
        _build_payment_markdown(payload),
        _build_worklog_markdown(payload),
        _build_contract_body_markdown(contract_markdown or ""),
        _build_signature_markdown(document),
    ]
    content = "\n\n".join(section.strip() for section in sections if section and section.strip())
    return content.strip() + "\n"


def _collect_text_content(element) -> str:
    parts: List[str] = []
    if element.text:
        parts.append(element.text)
    for child in element:
        if child.tag.lower() == "br":
            parts.append("\n")
        else:
            parts.append(_collect_text_content(child))
        if child.tail:
            parts.append(child.tail)
    return "".join(parts)


def _build_paragraph_styles(font_name: str) -> Dict[str, ParagraphStyle]:
    styles = getSampleStyleSheet()
    base = styles["Normal"]
    base.fontName = font_name
    base.fontSize = 11
    base.leading = 16

    def bold_name() -> str:
        bold_candidate = f"{font_name}-Bold"
        try:
            pdfmetrics.getFont(bold_candidate)
            return bold_candidate
        except KeyError:
            return "Helvetica-Bold"

    custom_styles = {
        "Title": ParagraphStyle(
            "ContractTitle",
            parent=base,
            fontName=bold_name(),
            fontSize=18,
            leading=22,
            spaceAfter=6,
        ),
        "Meta": ParagraphStyle(
            "ContractMeta",
            parent=base,
            fontSize=10,
            textColor=colors.grey,
            spaceAfter=12,
        ),
        "Heading1": ParagraphStyle(
            "Heading1",
            parent=base,
            fontName=bold_name(),
            fontSize=16,
            leading=20,
            spaceBefore=12,
            spaceAfter=6,
        ),
        "Heading2": ParagraphStyle(
            "Heading2",
            parent=base,
            fontName=bold_name(),
            fontSize=14,
            leading=18,
            spaceBefore=10,
            spaceAfter=4,
        ),
        "Heading3": ParagraphStyle(
            "Heading3",
            parent=base,
            fontName=bold_name(),
            fontSize=12,
            leading=16,
            spaceBefore=8,
            spaceAfter=4,
        ),
        "Body": ParagraphStyle(
            "ContractBody",
            parent=base,
        ),
        "List": ParagraphStyle(
            "ContractList",
            parent=base,
            leftIndent=12,
        ),
        "Quote": ParagraphStyle(
            "ContractQuote",
            parent=base,
            textColor=colors.HexColor("#374151"),
            leftIndent=12,
            borderColor=colors.HexColor("#94a3b8"),
            borderPadding=6,
            borderLeft=2,
        ),
        "Code": ParagraphStyle(
            "ContractCode",
            parent=base,
            fontName="Courier",
            backColor=colors.whitesmoke,
            leftIndent=4,
            rightIndent=4,
        ),
    }
    return custom_styles


def _element_to_flowables(element, styles: Dict[str, ParagraphStyle]) -> List:
    tag = element.tag.lower()
    blocks: List = []

    if tag.startswith("h") and len(tag) == 2 and tag[1].isdigit():
        level = int(tag[1])
        text = _collect_text_content(element).strip()
        if text:
            style_key = f"Heading{min(level, 3)}"
            blocks.append(Paragraph(text, styles[style_key]))
        return blocks

    if tag == "p":
        text = _collect_text_content(element).strip()
        if text:
            blocks.append(Paragraph(text, styles["Body"]))
        return blocks

    if tag in {"ul", "ol"}:
        ordered = tag == "ol"
        index = 1
        for li in element.findall("li"):
            item_text = _collect_text_content(li).strip()
            if not item_text:
                continue
            prefix = f"{index}. " if ordered else "• "
            blocks.append(Paragraph(prefix + item_text, styles["List"]))
            index += 1
        return blocks

    if tag == "blockquote":
        text = _collect_text_content(element).strip()
        if text:
            blocks.append(Paragraph(text, styles["Quote"]))
        return blocks

    if tag == "pre":
        code_text = _collect_text_content(element).strip().replace(" ", "&nbsp;")
        safe = code_text.replace("<", "&lt;").replace(">", "&gt;")
        blocks.append(Paragraph(f'<font face="Courier">{safe}</font>', styles["Code"]))
        return blocks

    if tag == "table":
        data: List[List[str]] = []
        header_row: List[str] = []

        thead = element.find("thead")
        if thead is not None:
            header_cells = [
                _collect_text_content(th).strip()
                for rows in thead.findall("tr")
                for th in rows.findall("th")
            ]
            if header_cells:
                header_row = header_cells

        tbody = element.find("tbody")
        row_parent = tbody if tbody is not None else element
        for tr in row_parent.findall("tr"):
            cells = tr.findall("td")
            if not cells:
                continue
            data.append([_collect_text_content(td).strip() for td in cells])

        if header_row:
            data.insert(0, header_row)

        if data:
            table = Table(data, hAlign="LEFT")
            table_style = TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f2f4f7")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5f5")),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTNAME", (0, 0), (-1, -1), styles["Body"].fontName),
                    ("FONTSIZE", (0, 0), (-1, -1), 10.5),
                ]
            )
            table.setStyle(table_style)
            blocks.append(table)
        return blocks

    return blocks


def _markdown_to_story(markdown_text: str, styles: Dict[str, ParagraphStyle]) -> List:
    md = markdown.Markdown(
        extensions=[
            "markdown.extensions.fenced_code",
            "markdown.extensions.tables",
            "markdown.extensions.nl2br",
            "markdown.extensions.sane_lists",
        ]
    )
    root = md.parser.parseDocument(markdown_text.splitlines()).getroot()
    story: List = []
    for element in root:
        flowables = _element_to_flowables(element, styles)
        if not flowables:
            continue
        story.extend(flowables)
        story.append(Spacer(1, 8))
    return story


def _render_contract_via_reportlab(document, markdown_text: str, title: str) -> bytes:
    font_name = resolve_contract_pdf_font()
    styles = _build_paragraph_styles(font_name)
    story: List = []
    story.extend(_markdown_to_story(markdown_text, styles))

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=48,
        bottomMargin=48,
    )
    doc.build(story)
    return buffer.getvalue()


def _format_lightning_value(value: str) -> str:
    if not value:
        return "일반 로그인 계정 (라이트닝 ID 없음)"
    return value




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
                _register_bold_variant(font_name, path)
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
                _register_bold_variant(font_name, path)
                return font_name
            except Exception:
                continue
        except Exception:
            continue

    return default


def render_contract_pdf(document, contract_markdown: str) -> ContentFile:
    """Markdown을 ReportLab 기반 PDF로 변환."""
    payload = document.payload or {}
    markdown_text = _compose_contract_markdown(document, contract_markdown or "")
    title = payload.get("title") or "SatoShop Expert 계약"
    pdf_bytes = _render_contract_via_reportlab(document, markdown_text, title)
    timestamp = timezone.localtime(timezone.now()).strftime("%Y%m%d%H%M%S")
    filename = f"direct-contract-{document.slug}-{timestamp}.pdf"
    return ContentFile(pdf_bytes, name=filename)
