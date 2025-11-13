import base64
import hashlib
import json
import secrets
import os
import shutil
import subprocess
import tempfile
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont

BASE_DIR = Path(__file__).resolve().parent
FONT_BUNDLE_DIR = BASE_DIR / "fonts"
logger = logging.getLogger(__name__)


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

BASE_FONT_OPTION_VARIABLES = (
    "mainfontoptions",
    "sansfontoptions",
    "monofontoptions",
)

CJK_FONT_OPTION_VARIABLES = (
    "CJKmainfontoptions",
    "CJKsansfontoptions",
)

EMOJI_RANGES: Tuple[Tuple[int, int], ...] = (
    (0x1F300, 0x1F5FF),
    (0x1F600, 0x1F64F),
    (0x1F680, 0x1F6FF),
    (0x1F900, 0x1F9FF),
    (0x1FA70, 0x1FAFF),
    (0x2600, 0x26FF),
    (0x2700, 0x27BF),
)

_emoji_range_pattern = "".join(f"\\U{start:08X}-\\U{end:08X}" for start, end in EMOJI_RANGES)
EMOJI_PATTERN = re.compile(f"[{_emoji_range_pattern}]", flags=re.UNICODE)
VARIATION_PATTERN = re.compile("[\\uFE0E\\uFE0F\\u200D]")
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


def _find_font_variant(font_dir: Path, keywords: List[str]) -> Optional[str]:
    lowered_keywords = [keyword.lower() for keyword in keywords]
    for pattern in ("*.ttf", "*.otf"):
        for candidate in sorted(font_dir.glob(pattern)):
            name_lower = candidate.name.lower()
            if all(keyword in name_lower for keyword in lowered_keywords):
                return candidate.name
    return None


def _tokenize_font_name(value: str) -> List[str]:
    if not value:
        return []
    tokens = re.split(r"[\s\-_]+", value.strip())
    return [token for token in tokens if token]


def _build_font_option_payload(font_dir: str, configured_family: str) -> Tuple[Optional[str], Optional[str]]:
    if not font_dir:
        return None, None
    base_path = Path(font_dir).expanduser()
    if not base_path.exists():
        return None, None
    resolved = base_path.resolve()
    available_files = []
    for pattern in ("*.ttf", "*.otf"):
        available_files.extend(sorted(resolved.glob(pattern)))
    if not available_files:
        return None, None
    option_parts = []
    path_value = resolved.as_posix()
    if not path_value.endswith("/"):
        path_value += "/"
    option_parts.append(f"Path={path_value}")
    bold_font = _find_font_variant(resolved, ["bold"]) or _find_font_variant(resolved, ["medium"])
    italic_font = _find_font_variant(resolved, ["italic"])
    regular_font = _find_font_variant(resolved, ["regular"]) or _find_font_variant(resolved, ["book"])
    primary_font = None
    preferred_tokens = _tokenize_font_name(configured_family)
    if preferred_tokens:
        primary_font = _find_font_variant(resolved, preferred_tokens + ["regular"]) or _find_font_variant(
            resolved, preferred_tokens
        )
    if not primary_font:
        primary_font = regular_font
    if not primary_font and available_files:
        primary_font = available_files[0].name
    if bold_font:
        option_parts.append(f"BoldFont={bold_font}")
    if italic_font:
        option_parts.append(f"ItalicFont={italic_font}")
    elif regular_font:
        option_parts.append(f"ItalicFont={regular_font}")
    if primary_font:
        suffix = Path(primary_font).suffix
        if suffix:
            option_parts.append(f"Extension={suffix}")
    option_string = ",".join(part for part in option_parts if part)
    return option_string, primary_font


def _build_font_option_args(option_string: Optional[str], include_cjk: bool) -> List[str]:
    if not option_string:
        return []
    args: List[str] = []
    variables = list(BASE_FONT_OPTION_VARIABLES)
    if include_cjk:
        variables.extend(CJK_FONT_OPTION_VARIABLES)
    for variable in variables:
        args.extend(["-V", f"{variable}:{option_string}"])
    return args


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


def _resolve_pandoc_binary() -> str:
    configured = getattr(settings, "EXPERT_PANDOC_PATH", "pandoc")
    candidate = Path(configured)
    if candidate.is_file():
        return str(candidate)
    resolved = shutil.which(configured)
    if resolved:
        return resolved
    raise RuntimeError(
        f"Pandoc 실행 파일({configured})을 찾을 수 없습니다. EXPERT_PANDOC_PATH 설정을 확인해주세요."
    )


def _render_markdown_via_pandoc(markdown_text: str, document_title: str) -> bytes:
    pandoc_binary = _resolve_pandoc_binary()
    pdf_engine = (getattr(settings, "EXPERT_PANDOC_PDF_ENGINE", "") or "").strip()
    extra_args = list(getattr(settings, "EXPERT_PANDOC_EXTRA_ARGS", None) or [])
    geometry = (getattr(settings, "EXPERT_PANDOC_GEOMETRY", "") or "").strip()
    header_includes = list(getattr(settings, "EXPERT_PANDOC_HEADER_INCLUDES", None) or [])
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        pdf_path = tmpdir_path / "contract.pdf"
        command: List[str] = [
            pandoc_binary,
            "--from=gfm",
            "-o",
            str(pdf_path),
        ]
    font_family = getattr(settings, "EXPERT_PANDOC_FONT_FAMILY", "").strip()
    font_dir_setting = (getattr(settings, "EXPERT_FONT_DIR", "") or "").strip()
    enable_cjk_fonts = bool(getattr(settings, "EXPERT_PANDOC_ENABLE_CJK", False))
    font_option_string, primary_font_override = _build_font_option_payload(font_dir_setting, font_family)
    effective_font = primary_font_override or font_family
    if effective_font:
        font_args = [
            "-V",
            f"mainfont:{effective_font}",
            "-V",
            f"sansfont:{effective_font}",
            "-V",
            f"monofont:{effective_font}",
        ]
        if enable_cjk_fonts:
            font_args.extend(
                [
                    "-V",
                    f"CJKmainfont:{effective_font}",
                    "-V",
                    f"CJKsansfont:{effective_font}",
                ]
            )
        command.extend(font_args)
        command.extend(_build_font_option_args(font_option_string, enable_cjk_fonts))
        title = document_title or "SatoShop Expert 계약"
        command.extend(["--metadata", f"title={title}"])
        if pdf_engine:
            command.extend(["--pdf-engine", pdf_engine])
        geometry_override = False
        for index, token in enumerate(extra_args):
            if not isinstance(token, str):
                continue
            if token in {"-V", "--variable"}:
                next_index = index + 1
                if next_index < len(extra_args):
                    next_token = extra_args[next_index]
                    if isinstance(next_token, str) and next_token.startswith("geometry:"):
                        geometry_override = True
                        break
            if token.startswith("--variable=") and token.partition("=")[2].startswith("geometry:"):
                geometry_override = True
                break
            if token.startswith("-Vgeometry:"):
                geometry_override = True
                break
        if geometry and not geometry_override:
            command.extend(["-V", f"geometry:{geometry}"])
        if header_includes:
            for snippet in header_includes:
                command.extend(["-V", f"header-includes:{snippet}"])
        if extra_args:
            command.extend(extra_args)
        env = os.environ.copy()
        tinytex_bin = getattr(settings, "EXPERT_TINYTEX_BIN_DIR", "")
        if tinytex_bin:
            env_path = env.get("PATH", "")
            env["PATH"] = f"{tinytex_bin}:{env_path}" if env_path else tinytex_bin
        if font_dir_setting:
            existing_font_dir = env.get("OSFONTDIR")
            env["OSFONTDIR"] = (
                f"{font_dir_setting}:{existing_font_dir}" if existing_font_dir else font_dir_setting
            )
        try:
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                env=env,
                input=markdown_text.encode("utf-8"),
            )
        except subprocess.CalledProcessError as exc:  # pragma: no cover - external binary
            stderr = (exc.stderr or b"").decode("utf-8", errors="ignore").strip()
            message = "Pandoc을 사용해 계약 PDF를 생성하지 못했습니다."
            if stderr:
                message += f" (stderr: {stderr})"
            logger.exception("Pandoc 변환 실패: %s", stderr or exc)
            raise RuntimeError(message) from exc
        if not pdf_path.exists():
            raise RuntimeError("Pandoc 실행 후 PDF 파일을 찾을 수 없습니다.")
        return pdf_path.read_bytes()


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
    """Pandoc을 활용해 계약서 Markdown을 PDF로 변환."""
    payload = document.payload or {}
    raw_markdown = _compose_contract_markdown(document, contract_markdown or "")
    markdown_text = _sanitize_markdown(raw_markdown)
    title = payload.get("title") or "SatoShop Expert 계약"
    pdf_bytes = _render_markdown_via_pandoc(markdown_text, title)
    timestamp = timezone.localtime(timezone.now()).strftime("%Y%m%d%H%M%S")
    filename = f"direct-contract-{document.slug}-{timestamp}.pdf"
    return ContentFile(pdf_bytes, name=filename)


def _sanitize_markdown(text: str) -> str:
    if not text:
        return ""
    sanitized = VARIATION_PATTERN.sub("", text)
    sanitized = EMOJI_PATTERN.sub("", sanitized)
    return sanitized
