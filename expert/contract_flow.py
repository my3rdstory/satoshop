import base64
import hashlib
import json
import mimetypes
import secrets
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Tuple

import markdown
from django.conf import settings
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.utils import timezone
from weasyprint import HTML, CSS

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

PDF_TEMPLATE_NAME = "expert/contract_pdf.html"
PDF_STYLESHEET_PATH = BASE_DIR / "static" / "expert" / "css" / "contract_pdf.css"
FONT_FAMILY_NAME = "ContractSans"
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


def _markdown_to_html(text: str) -> str:
    if not text:
        return ""
    md = markdown.Markdown(
        extensions=[
            "markdown.extensions.fenced_code",
            "markdown.extensions.tables",
            "markdown.extensions.nl2br",
            "markdown.extensions.codehilite",
            "markdown.extensions.sane_lists",
            "markdown.extensions.extra",
        ],
        extension_configs={
            "markdown.extensions.codehilite": {
                "guess_lang": False,
                "noclasses": True,
            }
        },
        output_format="html5",
    )
    return md.convert(text)


@lru_cache(maxsize=1)
def _build_font_face_css() -> str:
    font_dir = Path(getattr(settings, "EXPERT_FONT_DIR", "") or "")
    if not font_dir.exists():
        return ""

    css_chunks: List[str] = []

    def register_face(weight: int, filename: str):
        target = font_dir / filename
        if not target.exists():
            return

        font_bytes = target.read_bytes()
        b64_payload = base64.b64encode(font_bytes).decode("ascii")
        mime = mimetypes.guess_type(target.name)[0] or "font/ttf"
        suffix = target.suffix.lower()
        format_hint = "opentype" if suffix == ".otf" else "truetype"

        css_chunks.append(
            "@font-face {{ font-family: '{family}'; src: url('data:{mime};base64,{payload}') format('{fmt}'); font-weight: {weight}; font-style: normal; font-display: swap; }}".format(
                family=FONT_FAMILY_NAME,
                mime=mime,
                payload=b64_payload,
                fmt=format_hint,
                weight=weight,
            )
        )

    register_face(400, "NotoSansKR-Regular.ttf")
    register_face(700, "NotoSansKR-Bold.ttf")

    if not css_chunks:
        return ""

    css_chunks.append(
        "body {{ font-family: '{family}', 'Noto Sans KR', 'Noto Sans', sans-serif; }}".format(
            family=FONT_FAMILY_NAME
        )
    )
    return "\n".join(css_chunks)


def _render_contract_via_weasyprint(document, markdown_text: str, title: str) -> bytes:
    contract_html = _markdown_to_html(markdown_text)
    context = {
        "document": document,
        "payload": document.payload or {},
        "contract_html": contract_html,
        "title": title,
        "generated_at": timezone.localtime(timezone.now()),
    }
    html_string = render_to_string(PDF_TEMPLATE_NAME, context)
    stylesheets: List[CSS] = []
    if PDF_STYLESHEET_PATH.exists():
        stylesheets.append(CSS(filename=str(PDF_STYLESHEET_PATH)))
    font_css = _build_font_face_css()
    if font_css:
        stylesheets.append(CSS(string=font_css))
    return HTML(string=html_string, base_url=str(settings.BASE_DIR)).write_pdf(stylesheets=stylesheets)


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
    """WeasyPrint를 활용해 계약서 Markdown을 PDF로 변환."""
    payload = document.payload or {}
    markdown_text = _compose_contract_markdown(document, contract_markdown or "")
    title = payload.get("title") or "SatoShop Expert 계약"
    pdf_bytes = _render_contract_via_weasyprint(document, markdown_text, title)
    timestamp = timezone.localtime(timezone.now()).strftime("%Y%m%d%H%M%S")
    filename = f"direct-contract-{document.slug}-{timestamp}.pdf"
    return ContentFile(pdf_bytes, name=filename)
