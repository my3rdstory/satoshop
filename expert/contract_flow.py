import base64
import hashlib
import html
import io
import json
import secrets
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Dict, Tuple, List
from xml.etree import ElementTree as ET

import markdown
from django.core.files.base import ContentFile
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ListStyle, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
)

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


def _build_pdf_styles(font_name: str) -> Dict[str, ParagraphStyle]:
    base_color = colors.HexColor("#1F2937")
    muted_color = colors.HexColor("#4B5563")
    accent_color = colors.HexColor("#2563EB")
    base = ParagraphStyle(
        name="ContractBase",
        fontName=font_name,
        fontSize=11,
        leading=16,
        textColor=base_color,
        spaceBefore=0,
        spaceAfter=6,
        alignment=TA_LEFT,
    )
    styles = {
        "Base": base,
        "DocumentTitle": ParagraphStyle(
            name="ContractTitle",
            parent=base,
            fontSize=16,
            leading=22,
            spaceAfter=4,
        ),
        "Subtitle": ParagraphStyle(
            name="ContractSubtitle",
            parent=base,
            fontSize=11,
            textColor=muted_color,
            spaceAfter=2,
        ),
        "Meta": ParagraphStyle(
            name="ContractMeta",
            parent=base,
            fontSize=10,
            textColor=muted_color,
            spaceAfter=10,
        ),
        "SectionHeading": ParagraphStyle(
            name="ContractSectionHeading",
            parent=base,
            fontSize=12,
            leading=18,
            textColor=accent_color,
            spaceBefore=12,
            spaceAfter=6,
        ),
        "PrimaryHeading": ParagraphStyle(
            name="ContractPrimaryHeading",
            parent=base,
            fontSize=14,
            leading=22,
            textColor=colors.HexColor("#1D4ED8"),
            spaceBefore=16,
            spaceAfter=10,
        ),
        "Body": ParagraphStyle(
            name="ContractBody",
            parent=base,
        ),
        "BlockQuote": ParagraphStyle(
            name="ContractBlockQuote",
            parent=base,
            textColor=base_color,
        ),
        "Footer": ParagraphStyle(
            name="ContractFooter",
            parent=base,
            fontSize=10,
            textColor=muted_color,
            spaceBefore=10,
            spaceAfter=0,
        ),
        "TableHeader": ParagraphStyle(
            name="ContractTableHeader",
            parent=base,
            textColor=muted_color,
            spaceAfter=4,
        ),
        "TableCell": ParagraphStyle(
            name="ContractTableCell",
            parent=base,
        ),
        "CodeBlock": ParagraphStyle(
            name="ContractCode",
            parent=base,
            fontName="Courier",
            fontSize=10,
            leading=14,
            backColor=colors.HexColor("#F3F4F6"),
            leftIndent=6,
            rightIndent=6,
            spaceBefore=4,
            spaceAfter=8,
        ),
    }
    styles["List"] = ListStyle(
        "ContractList",
        leftIndent=14,
        rightIndent=0,
        bulletFontName=font_name,
        bulletFontSize=11,
        bulletIndent=4,
    )
    return styles


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


def _build_intro_section(document, payload: Dict, styles: Dict[str, ParagraphStyle]) -> List:
    contract_title = payload.get("title") or "SatoShop Expert 계약"
    created_label = _format_generated_at(payload)
    return [
        Paragraph(contract_title, styles["DocumentTitle"]),
        Paragraph("SatoShop Expert - 전자 계약서", styles["Subtitle"]),
        Paragraph(f"공유 ID: {document.slug}", styles["Meta"]),
        Paragraph(f"생성 시각: {created_label}", styles["Meta"]),
        Spacer(1, 10),
    ]


def _build_overview_table(payload: Dict, styles: Dict[str, ParagraphStyle], width: float) -> List:
    role = payload.get("role_display") or "-"
    start = _normalize_value(payload.get("start_date"), "미정")
    end = _normalize_value(payload.get("end_date"), "미정")
    total = _format_sats(payload.get("amount_sats"))
    payment_type = payload.get("payment_display") or "-"
    performer_ln = payload.get("performer_lightning_address") or "-"
    overview_data = [
        ("역할", role),
        ("계약 기간", f"{start} ~ {end}"),
        ("총 금액", total),
        ("지급 방식", payment_type),
        ("수행자 라이트닝 주소", performer_ln),
    ]
    table_data = [
        [
            Paragraph(f"<b>{key}</b>", styles["TableHeader"]),
            Paragraph(value, styles["TableCell"]),
        ]
        for key, value in overview_data
    ]
    table = Table(
        table_data,
        colWidths=[width * 0.28, width * 0.72],
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.whitesmoke, colors.white]),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E5E7EB")),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#CBD5F5")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    return [
        Paragraph("<b>Ⅰ. 계약 개요</b>", styles["PrimaryHeading"]),
        table,
        Spacer(1, 10),
    ]


def _build_worklog_section(payload: Dict, styles: Dict[str, ParagraphStyle], width: float) -> List:
    work_log = (payload or {}).get("work_log_markdown")
    if not work_log:
        return []
    flow = [Paragraph("수행 내역", styles["SectionHeading"])]
    flowables = _markdown_to_flowables(work_log, styles, width)
    if not flowables:
        return []
    flow.extend(flowables)
    flow.append(Spacer(1, 6))
    return flow


def _build_payment_section(payload: Dict, styles: Dict[str, ParagraphStyle], width: float) -> List:
    flow: List = []
    milestones = payload.get("milestones") or []
    if milestones:
        table_data = [
            [
                Paragraph("<b>#</b>", styles["TableHeader"]),
                Paragraph("<b>금액</b>", styles["TableHeader"]),
                Paragraph("<b>지급일</b>", styles["TableHeader"]),
                Paragraph("<b>조건</b>", styles["TableHeader"]),
            ]
        ]
        for index, milestone in enumerate(milestones, start=1):
            amount = _format_sats(milestone.get("amount_sats") or milestone.get("amount"))
            due_date = _normalize_value(milestone.get("due_date"), "미정")
            condition = _normalize_value(milestone.get("condition"), "지급 조건 미입력")
            table_data.append(
                [
                    Paragraph(str(index), styles["TableCell"]),
                    Paragraph(amount, styles["TableCell"]),
                    Paragraph(due_date, styles["TableCell"]),
                    Paragraph(condition, styles["TableCell"]),
                ]
            )
        widths = [width * 0.1, width * 0.2, width * 0.2, width * 0.5]
        table = Table(table_data, colWidths=widths, hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E5E7EB")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                    ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#CBD5F5")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D1D5DB")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        flow.extend(
            [
                Paragraph("분할 지급 내역", styles["SectionHeading"]),
                table,
                Spacer(1, 10),
            ]
        )
    elif payload.get("payment_type") == "one_time":
        value = payload.get("one_time_due_date") or "미정"
        condition = payload.get("one_time_condition") or "지급 조건 미입력"
        table = Table(
            [
                [
                    Paragraph("<b>일괄 지급일</b>", styles["TableHeader"]),
                    Paragraph(value, styles["TableCell"]),
                ],
                [
                    Paragraph("<b>지급 조건</b>", styles["TableHeader"]),
                    Paragraph(condition, styles["TableCell"]),
                ],
            ],
            colWidths=[width * 0.28, width * 0.72],
            hAlign="LEFT",
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
                    ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D1D5DB")),
                    ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#CBD5F5")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        flow.extend(
            [
                Paragraph("일괄 지급 내역", styles["SectionHeading"]),
                table,
                Spacer(1, 10),
            ]
        )
    return flow


def _format_lightning_value(value: str) -> str:
    if not value:
        return "일반 로그인 계정 (라이트닝 ID 없음)"
    return value


def _build_signature_section(document, styles: Dict[str, ParagraphStyle], width: float) -> List:
    payload = document.payload or {}
    rows = [
        ("의뢰자 서명 해시", document.creator_hash or "-"),
        ("의뢰자 라이트닝 ID", _format_lightning_value(payload.get("creator_lightning_id", ""))),
        ("수행자 서명 해시", document.counterparty_hash or "-"),
        ("수행자 라이트닝 ID", _format_lightning_value(payload.get("counterparty_lightning_id", ""))),
        ("중개자(시스템) 서명 해시", document.mediator_hash or "-"),
    ]
    table = Table(
        [
            [
                Paragraph(f"<b>{label}</b>", styles["TableHeader"]),
                Paragraph(value, styles["TableCell"]),
            ]
            for label, value in rows
        ],
        colWidths=[width * 0.4, width * 0.6],
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#CBD5F5")),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E5E7EB")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    timestamp = timezone.localtime(timezone.now()).strftime("%Y-%m-%d %H:%M:%S")
    return [
        Spacer(1, 14),
        Paragraph("<b>Ⅲ. 서명 및 해시</b>", styles["PrimaryHeading"]),
        table,
        Paragraph(f"PDF 생성 시각: {timestamp}", styles["Footer"]),
    ]


def _collect_inline_markup(element) -> str:
    parts: List[str] = []
    if element.text:
        parts.append(html.escape(element.text))
    for child in list(element):
        tag = child.tag.lower()
        if tag in {"strong", "b"}:
            parts.append(f"<b>{_collect_inline_markup(child)}</b>")
        elif tag in {"em", "i"}:
            parts.append(f"<i>{_collect_inline_markup(child)}</i>")
        elif tag == "code":
            code_text = html.escape("".join(child.itertext()))
            parts.append(f'<font name="Courier">{code_text}</font>')
        elif tag == "br":
            parts.append("<br/>")
        else:
            parts.append(_collect_inline_markup(child))
        if child.tail:
            parts.append(html.escape(child.tail))
    return "".join(parts)


def _build_list_flowable(element, styles: Dict[str, ParagraphStyle], ordered: bool) -> ListFlowable:
    items = []
    for li in element.findall("li"):
        text = _collect_inline_markup(li).strip()
        if not text:
            text = "&nbsp;"
        items.append(ListItem(Paragraph(text, styles["Body"])))
    bullet_type = "1" if ordered else "bullet"
    start = int(element.attrib.get("start", 1)) if ordered else None
    return ListFlowable(
        items,
        bulletType=bullet_type,
        start=start,
        leftIndent=14 if ordered else 14,
        bulletFontName=styles["Body"].fontName,
        bulletFontSize=styles["Body"].fontSize,
        bulletOffsetY=0,
    )


def _build_blockquote_table(element, styles: Dict[str, ParagraphStyle], width: float) -> Table:
    paragraphs: List[str] = []
    if element.text and element.text.strip():
        paragraphs.append(html.escape(element.text.strip()))
    for child in list(element):
        text = _collect_inline_markup(child)
        if text:
            paragraphs.append(text)
        if child.tail and child.tail.strip():
            paragraphs.append(html.escape(child.tail.strip()))
    content = "<br/>".join(paragraphs)
    para = Paragraph(content, styles["BlockQuote"])
    table = Table([[para]], colWidths=[width], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#93C5FD")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EFF6FF")),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def _build_html_table_flowable(element, styles: Dict[str, ParagraphStyle], width: float) -> List[Table]:
    rows: List[List[Paragraph]] = []
    header_count = 0
    for child in list(element):
        tag = child.tag.lower()
        if tag == "thead":
            for tr in child.findall("tr"):
                row = [
                    Paragraph(_collect_inline_markup(cell) or "", styles["TableHeader"])
                    for cell in list(tr)
                ]
                rows.append(row)
                header_count += 1
        elif tag in {"tbody", "tfoot"}:
            for tr in child.findall("tr"):
                row = [
                    Paragraph(_collect_inline_markup(cell) or "", styles["TableCell"])
                    for cell in list(tr)
                ]
                rows.append(row)
        elif tag == "tr":
            row = [
                Paragraph(_collect_inline_markup(cell) or "", styles["TableCell"])
                for cell in list(child)
            ]
            rows.append(row)
    if not rows:
        return []
    column_count = max(len(row) for row in rows)
    col_width = width / max(column_count, 1)
    table = Table(rows, colWidths=[col_width] * column_count, hAlign="LEFT")
    table_style_commands = [
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5F5")),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5E7EB")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    if header_count:
        table_style_commands.append(("BACKGROUND", (0, 0), (-1, header_count - 1), colors.HexColor("#E5E7EB")))
    table.setStyle(TableStyle(table_style_commands))
    return [table]


def _markdown_to_flowables(markdown_text: str, styles: Dict[str, ParagraphStyle], width: float) -> List:
    if not markdown_text:
        return []
    html_text = markdown.markdown(
        markdown_text,
        extensions=[
            "markdown.extensions.fenced_code",
            "markdown.extensions.tables",
            "markdown.extensions.nl2br",
            "markdown.extensions.sane_lists",
        ],
        output_format="html5",
    )
    wrapped_html = f"<root>{html_text}</root>"
    try:
        root = ET.fromstring(wrapped_html)
    except ET.ParseError:
        return [Paragraph(markdown_text, styles["Body"])]
    flowables: List = []
    for child in list(root):
        flowables.extend(_element_to_flowables(child, styles, width))
        flowables.append(Spacer(1, 6))
    if flowables and isinstance(flowables[-1], Spacer):
        flowables.pop()
    return flowables


def _element_to_flowables(element, styles: Dict[str, ParagraphStyle], width: float) -> List:
    tag = element.tag.lower()
    if tag in {"h1", "h2", "h3", "h4"}:
        heading_map = {
            "h1": ("DocumentTitle", 4),
            "h2": ("SectionHeading", 4),
            "h3": ("SectionHeading", 2),
            "h4": ("SectionHeading", 2),
        }
        style_name, spacer_height = heading_map.get(tag, ("SectionHeading", 2))
        text = _collect_inline_markup(element)
        if not text.strip():
            return []
        flow = [Paragraph(text, styles.get(style_name, styles["Body"]))]
        if spacer_height:
            flow.append(Spacer(1, spacer_height))
        return flow
    if tag == "p":
        text = _collect_inline_markup(element)
        if not text.strip():
            return []
        return [Paragraph(text, styles["Body"])]
    if tag == "ul":
        return [_build_list_flowable(element, styles, ordered=False)]
    if tag == "ol":
        return [_build_list_flowable(element, styles, ordered=True)]
    if tag == "blockquote":
        return [_build_blockquote_table(element, styles, width)]
    if tag == "pre":
        code_node = element.find("code")
        if code_node is not None:
            text = "".join(code_node.itertext())
        else:
            text = "".join(element.itertext())
        return [Preformatted(text.strip("\n"), styles["CodeBlock"])]
    if tag == "table":
        return _build_html_table_flowable(element, styles, width)
    if tag == "hr":
        line = Table(
            [[""]],
            colWidths=[width],
            style=TableStyle(
                [
                    ("LINEBELOW", (0, 0), (-1, -1), 0.7, colors.HexColor("#CBD5F5")),
                ]
            ),
        )
        return [line]
    if tag == "div":
        flowables: List = []
        for child in list(element):
            flowables.extend(_element_to_flowables(child, styles, width))
        return flowables
    if tag in {"section", "article", "aside", "header", "footer", "main", "nav"}:
        flowables: List = []
        if element.text and element.text.strip():
            flowables.append(Paragraph(html.escape(element.text.strip()), styles["Body"]))
        for child in list(element):
            flowables.extend(_element_to_flowables(child, styles, width))
            if child.tail and child.tail.strip():
                flowables.append(Paragraph(html.escape(child.tail.strip()), styles["Body"]))
        return flowables
    text = _collect_inline_markup(element)
    if text.strip():
        return [Paragraph(text, styles["Body"])]
    return []


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
    """ReportLab Platypus를 활용해 스타일링된 계약서 PDF를 생성."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )
    payload = document.payload or {}
    font_name = resolve_contract_pdf_font()
    styles = _build_pdf_styles(font_name)
    story: List = []

    story.extend(_build_intro_section(document, payload, styles))
    story.extend(_build_overview_table(payload, styles, doc.width))

    payment_flow = _build_payment_section(payload, styles, doc.width)
    if payment_flow:
        story.extend(payment_flow)

    worklog_flow = _build_worklog_section(payload, styles, doc.width)
    if worklog_flow:
        story.extend(worklog_flow)

    contract_flow = _markdown_to_flowables(contract_markdown, styles, doc.width)
    if contract_flow:
        story.append(Paragraph("<b>Ⅱ. 계약 본문</b>", styles["PrimaryHeading"]))
        story.extend(contract_flow)

    story.extend(_build_signature_section(document, styles, doc.width))

    doc.build(story)
    buffer.seek(0)
    filename = f"direct-contract-{document.slug}.pdf"
    return ContentFile(buffer.getvalue(), name=filename)
