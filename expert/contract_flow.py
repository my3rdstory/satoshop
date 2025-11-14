import base64
import hashlib
import html as html_utils
import json
import secrets
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from html import unescape
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import markdown
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from fpdf import FPDF

BASE_DIR = Path(__file__).resolve().parent
FONT_BUNDLE_DIR = (Path(settings.BASE_DIR) / "expert" / "static" / "expert" / "fonts").resolve()


@dataclass
class FontConfig:
    family: str
    regular_path: Optional[Path]
    bold_path: Optional[Path]


def _bundle_font_candidates() -> List[Path]:
    if not FONT_BUNDLE_DIR.exists():
        return []
    candidates: List[Path] = []
    for pattern in ("*.ttf", "*.otf"):
        candidates.extend(sorted(FONT_BUNDLE_DIR.glob(pattern)))
    return candidates


def _font_weight_priority(path: Path) -> Tuple[int, str]:
    name = path.stem.lower()
    if any(keyword in name for keyword in ("regular", "book", "text", "normal")):
        priority = 0
    elif any(keyword in name for keyword in ("medium", "demi")):
        priority = 1
    elif any(keyword in name for keyword in ("light", "thin", "extra", "ultra")):
        priority = 2
    elif any(keyword in name for keyword in ("bold", "black", "heavy")):
        priority = 3
    else:
        priority = 4
    return (priority, str(path))


def _sort_fonts_by_weight(paths: List[Path]) -> List[Path]:
    return sorted(paths, key=_font_weight_priority)


FONT_CANDIDATES = _sort_fonts_by_weight(
    _bundle_font_candidates()
    + [
        Path("/usr/share/fonts/truetype/noto/NotoSansCJKkr-Regular.otf"),
        Path("/usr/share/fonts/truetype/noto/NotoSansKR-Regular.ttf"),
    ]
)

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


def _find_bold_variant(font_path: Path) -> Optional[Path]:
    """가능한 경우 동일 경로의 Bold 폰트 파일 경로를 찾는다."""
    candidates: List[Path] = []
    stem = font_path.stem
    suffix = font_path.suffix
    if "Regular" in stem:
        candidates.append(font_path.with_name(stem.replace("Regular", "Bold") + suffix))
    if "Medium" in stem:
        candidates.append(font_path.with_name(stem.replace("Medium", "Bold") + suffix))
    candidates.append(font_path.with_name(stem + "-Bold" + suffix))
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None




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


CONTRACT_DIVIDER_MARKER = "[[CONTRACT_DIVIDER]]"


def _normalize_multiline_text(value: str) -> str:
    if value is None:
        return ""
    text = str(value)
    replacements = [
        ("\r\n", "\n"),
        ("\\r\\n", "\n"),
        ("\r", "\n"),
        ("\\n", "\n"),
    ]
    for source, target in replacements:
        text = text.replace(source, target)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _format_plaintext_paragraphs(value: str) -> str:
    normalized = _normalize_multiline_text(value or "")
    stripped = normalized.strip()
    if not stripped:
        return ""

    paragraphs: List[str] = []
    buffer: List[str] = []

    def flush_buffer():
        if buffer:
            safe = html_utils.escape("\n".join(buffer)).replace("\n", "<br/>")
            paragraphs.append(f"<p>{safe}</p>")
            buffer.clear()

    for line in normalized.split("\n"):
        if line.strip():
            buffer.append(line.rstrip())
        else:
            flush_buffer()
            paragraphs.append("<p>&nbsp;</p>")

    flush_buffer()

    # 제거된 끝 공백에서 생긴 빈 줄 제거
    while paragraphs and paragraphs[-1] == "<p>&nbsp;</p>":
        paragraphs.pop()
    if not paragraphs:
        paragraphs.append("<p>-</p>")

    return "\n".join(paragraphs)


def _format_worklog_block(value: str) -> str:
    normalized = _normalize_multiline_text(value or "")
    if not normalized.strip():
        return "-"
    return normalized.strip()


def _build_intro_markdown(document, payload: Dict) -> str:
    contract_title = payload.get("title") or "SatoShop Expert 계약"
    created_label = _format_generated_at(payload)
    lines = [
        f"# {contract_title}",
        "_SatoShop Expert Digital Contact_",
        "",
        f"- 공유 ID: {document.slug}",
        f"- 생성 시각: {created_label}",
        "",
        CONTRACT_DIVIDER_MARKER,
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
    content = _format_worklog_block(work_log)
    return "\n\n".join([CONTRACT_DIVIDER_MARKER, "## 수행 내역", content]).strip()


def _build_contract_body_markdown(contract_markdown: str) -> str:
    if not contract_markdown:
        return ""
    body = contract_markdown.strip()
    if not body:
        return ""
    return "\n\n".join([CONTRACT_DIVIDER_MARKER, "## Ⅱ. 계약 본문", body]).strip()


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
            CONTRACT_DIVIDER_MARKER, 
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


def _element_inner_html(element) -> str:
    parts: List[str] = []
    if element.text:
        parts.append(element.text)
    for child in element:
        parts.append(ET.tostring(child, encoding="unicode", method="html"))
        if child.tail:
            parts.append(child.tail)
    return "".join(parts)


def _sanitize_inline_markup(value: str) -> str:
    if not value:
        return ""
    replacements = {
        "<strong>": "<b>",
        "</strong>": "</b>",
        "<em>": "<i>",
        "</em>": "</i>",
        "<code>": '<font face="Courier">',
        "</code>": "</font>",
        "<tt>": '<font face="Courier">',
        "</tt>": "</font>",
        "<br>": "<br/>",
        "<br />": "<br/>",
    }
    sanitized = value
    for source, target in replacements.items():
        sanitized = sanitized.replace(source, target)
    return sanitized


@dataclass
class InlineStyle:
    bold: bool = False
    italic: bool = False
    font: Optional[str] = None


class InlineHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tokens: List[Dict[str, Any]] = []
        self._stack: List[InlineStyle] = [InlineStyle()]

    def handle_starttag(self, tag, attrs):
        style = InlineStyle(
            bold=self._stack[-1].bold,
            italic=self._stack[-1].italic,
            font=self._stack[-1].font,
        )
        tag = tag.lower()
        if tag in {"b", "strong"}:
            style.bold = True
        elif tag in {"i", "em"}:
            style.italic = True
        elif tag == "font":
            attr_map = {name: value for name, value in attrs}
            if attr_map.get("face"):
                style.font = attr_map["face"]
        elif tag == "br":
            self.tokens.append({"type": "br"})
        self._stack.append(style)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "br":
            return
        if len(self._stack) > 1:
            self._stack.pop()

    def handle_data(self, data):
        if not data:
            return
        text = data.replace("\xa0", " ")
        if not text:
            return
        self.tokens.append({"type": "text", "text": text, "style": self._stack[-1]})


def _parse_inline_html(html_fragment: str) -> List[Dict[str, Any]]:
    parser = InlineHTMLParser()
    parser.feed(html_fragment or "")
    parser.close()
    return parser.tokens


def _html_to_plain_text(value: str) -> str:
    if not value:
        return "-"
    text = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text)
    cleaned = "\n".join(line.rstrip() for line in text.splitlines())
    cleaned = cleaned.strip()
    return cleaned or "-"


def _element_to_blocks(element) -> List[Dict[str, Any]]:
    tag = element.tag.lower()
    blocks: List[Dict[str, Any]] = []

    if tag.startswith("h") and len(tag) == 2 and tag[1].isdigit():
        level = int(tag[1])
        html = _sanitize_inline_markup(_element_inner_html(element)).strip()
        if html:
            blocks.append({"type": "heading", "level": level, "html": html})
        return blocks

    if tag == "p":
        html = _sanitize_inline_markup(_element_inner_html(element)).strip()
        if html == CONTRACT_DIVIDER_MARKER:
            blocks.append({"type": "divider"})
            return blocks
        if not html or html == "&nbsp;":
            blocks.append({"type": "spacer", "size": 4})
            return blocks
        blocks.append({"type": "paragraph", "html": html})
        return blocks

    if tag in {"ul", "ol"}:
        ordered = tag == "ol"
        index = 1
        for li in element.findall("li"):
            item_html = _sanitize_inline_markup(_element_inner_html(li)).strip()
            if not item_html:
                continue
            while item_html.startswith("<p>") and item_html.endswith("</p>"):
                item_html = item_html[3:-4].strip()
            bullet_text = f"{index}. " if ordered else "• "
            blocks.append({"type": "list_item", "html": item_html, "bullet": bullet_text})
            index += 1
        return blocks

    if tag == "blockquote":
        html = _sanitize_inline_markup(_element_inner_html(element)).strip()
        if html:
            blocks.append({"type": "blockquote", "html": html})
        return blocks

    if tag == "pre":
        code_text = _collect_text_content(element).rstrip("\n")
        blocks.append({"type": "code", "text": code_text})
        return blocks

    if tag == "hr":
        blocks.append({"type": "divider"})
        return blocks

    if tag == "table":
        data: List[List[str]] = []
        header_row: List[str] = []

        thead = element.find("thead")
        if thead is not None:
            header_cells = [
                _sanitize_inline_markup(_element_inner_html(th)).strip()
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
            row = [_sanitize_inline_markup(_element_inner_html(td)).strip() for td in cells]
            data.append(row)

        has_header = False
        if header_row:
            data.insert(0, header_row)
            has_header = True

        if data:
            blocks.append({"type": "table", "rows": data, "has_header": has_header})
        return blocks

    return blocks


def _markdown_to_blocks(markdown_text: str) -> List[Dict[str, Any]]:
    md = markdown.Markdown(
        extensions=[
            "markdown.extensions.fenced_code",
            "markdown.extensions.tables",
            "markdown.extensions.nl2br",
            "markdown.extensions.sane_lists",
        ]
    )
    root = md.parser.parseDocument(markdown_text.splitlines()).getroot()
    blocks: List[Dict[str, Any]] = []
    for element in root:
        items = _element_to_blocks(element)
        if not items:
            continue
        blocks.extend(items)
        blocks.append({"type": "gap", "size": 4})
    if blocks and blocks[-1].get("type") == "gap":
        blocks.pop()
    return blocks


class ContractPDF(FPDF):
    def __init__(self, font_config: FontConfig, title: str):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.font_config = font_config
        self.title_text = title
        self.body_font = self._register_fonts(font_config)
        self.set_margins(15, 18, 15)
        self.set_auto_page_break(auto=True, margin=18)

    def _register_fonts(self, config: FontConfig) -> str:
        family = config.family or "Helvetica"
        if config.regular_path:
            self.add_font(family, "", str(config.regular_path), uni=True)
            bold_path = config.bold_path or config.regular_path
            self.add_font(family, "B", str(bold_path), uni=True)
        return family

    def footer(self):
        self.set_y(-15)
        self.set_font(self.body_font, "B", 9)
        text = f"-{self.page_no()}/{{nb}}-"
        self.cell(0, 10, text, 0, 0, "C")


def _render_rich_text(pdf: ContractPDF, html_content: str, font_size: int = 11, indent: float = 0):
    tokens = _parse_inline_html(html_content or "")
    line_height = 5
    pdf.set_x(pdf.l_margin + indent)
    for token in tokens:
        if token.get("type") == "br":
            pdf.ln(line_height)
            pdf.set_x(pdf.l_margin + indent)
            continue
        text = token.get("text", "")
        if not text:
            continue
        style = token["style"]
        font_family = pdf.body_font
        if style.font and style.font.lower().startswith("courier"):
            font_family = "Courier"
        font_style = ""
        if style.bold:
            font_style += "B"
        if style.italic:
            font_style += "I"
        pdf.set_font(font_family, font_style, font_size)
        pdf.write(line_height, text)
    pdf.ln(line_height)


def _render_code_block(pdf: ContractPDF, content: str):
    line_height = 5
    pdf.set_fill_color(245, 245, 245)
    pdf.set_font("Courier", "", 10)
    text = content.replace("\t", "    ").rstrip("\n") or "-"
    pdf.multi_cell(0, line_height, text, border=0, fill=True)
    pdf.set_fill_color(255, 255, 255)
    pdf.ln(2)


def _render_table_block(pdf: ContractPDF, block: Dict[str, Any]):
    rows: List[List[str]] = block.get("rows") or []
    if not rows:
        return
    col_count = max(len(row) for row in rows)
    if col_count == 0:
        return
    available_width = pdf.w - pdf.l_margin - pdf.r_margin
    col_width = available_width / col_count
    line_height = 5
    header_bg = (242, 244, 247)
    border_color = (203, 213, 245)

    for idx, row in enumerate(rows):
        cell_texts: List[str] = []
        line_counts: List[int] = []
        for cell in row:
            text = _html_to_plain_text(cell)
            lines = pdf.multi_cell(col_width, line_height, text, split_only=True)
            line_counts.append(max(1, len(lines)))
            cell_texts.append(text)

        max_count = max(line_counts) if line_counts else 1
        max_height = max_count * line_height
        y_start = pdf.get_y()
        x_start = pdf.l_margin
        pdf.set_draw_color(*border_color)

        for col, text in enumerate(cell_texts):
            pdf.set_xy(x_start + col * col_width, y_start)
            fill = idx == 0 and block.get("has_header")
            pdf.set_fill_color(*(header_bg if fill else (255, 255, 255)))
            pdf.set_font(pdf.body_font, "B" if fill else "", 10)
            pad_lines = max_count - line_counts[col]
            padded_text = text + ("\n" * pad_lines)
            pdf.multi_cell(col_width, line_height, padded_text, border=1, align="L", fill=fill)
        pdf.set_y(y_start + max_height)
    pdf.ln(2)


def _render_block(pdf: ContractPDF, block: Dict[str, Any]):
    kind = block.get("type")
    if kind == "heading":
        level = min(block.get("level", 1), 3)
        size_map = {1: 18, 2: 14, 3: 12}
        text = _html_to_plain_text(block.get("html"))
        pdf.set_font(pdf.body_font, "B", size_map.get(level, 12))
        pdf.multi_cell(0, 6, text)
        pdf.ln(1)
    elif kind == "paragraph":
        _render_rich_text(pdf, block.get("html", ""))
    elif kind == "list_item":
        bullet = block.get("bullet", "")
        html_content = f"{bullet} {block.get('html', '')}"
        _render_rich_text(pdf, html_content, indent=4)
    elif kind == "blockquote":
        pdf.set_text_color(55, 65, 81)
        _render_rich_text(pdf, block.get("html", ""), indent=4)
        pdf.set_text_color(0, 0, 0)
    elif kind == "code":
        _render_code_block(pdf, block.get("text", ""))
    elif kind == "table":
        _render_table_block(pdf, block)
    elif kind == "divider":
        y = pdf.get_y()
        pdf.set_draw_color(203, 213, 245)
        pdf.set_line_width(0.4)
        pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
        pdf.ln(4)
    elif kind in {"spacer", "gap"}:
        pdf.ln(block.get("size", 4))


def _render_contract_via_fpdf(document, markdown_text: str, title: str) -> bytes:
    font_config = resolve_contract_pdf_font()
    pdf = ContractPDF(font_config, title)
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_font(pdf.body_font, "", 11)
    blocks = _markdown_to_blocks(markdown_text)
    for block in blocks:
        _render_block(pdf, block)
    rendered = pdf.output(dest="S")
    if isinstance(rendered, str):
        return rendered.encode("latin1")
    return bytes(rendered)


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
def resolve_contract_pdf_font(default: str = "Helvetica") -> FontConfig:
    for path in FONT_CANDIDATES:
        if not path.exists():
            continue
        font_name = f"SatoContract-{path.stem}"
        return FontConfig(font_name, path, _find_bold_variant(path))

    for path in LATIN_FONT_CANDIDATES:
        if not path.exists():
            continue
        font_name = f"SatoContract-{path.stem}"
        return FontConfig(font_name, path, _find_bold_variant(path))

    return FontConfig(default, None, None)


def render_contract_pdf(document, contract_markdown: str) -> ContentFile:
    """Markdown을 fpdf2 기반 PDF로 변환."""
    payload = document.payload or {}
    markdown_text = _compose_contract_markdown(document, contract_markdown or "")
    title = payload.get("title") or "SatoShop Expert 계약"
    pdf_bytes = _render_contract_via_fpdf(document, markdown_text, title)
    timestamp = timezone.localtime(timezone.now()).strftime("%Y%m%d%H%M%S")
    filename = f"direct-contract-{document.slug}-{timestamp}.pdf"
    return ContentFile(pdf_bytes, name=filename)
