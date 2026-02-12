import json
import logging

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .item_services import (
    ITEM_TYPE_DIGITAL_FILE,
    ITEM_TYPE_LIVE_LECTURE,
    ITEM_TYPE_MEETUP,
    ITEM_TYPE_PRODUCT,
    build_recent_items_lookup,
    get_recent_registered_items,
    get_recent_sold_items,
)
from .models import DiscordBot

logger = logging.getLogger(__name__)

DISCORD_PING = 1
DISCORD_APPLICATION_COMMAND = 2
DISCORD_MESSAGE_COMPONENT = 3

DISCORD_RESPONSE_PONG = 1
DISCORD_RESPONSE_MESSAGE = 4

DISCORD_EPHEMERAL = 1 << 6

COMMAND_RECENT_REGISTERED = "사토샵_최근등록상품"
COMMAND_RECENT_SOLD = "사토샵_최근판매상품"

SELECT_ID_RECENT_REGISTERED = "satoshop_recent_registered_select"
SELECT_ID_RECENT_SOLD = "satoshop_recent_sold_select"


def _json_response(payload: dict, status: int = 200) -> JsonResponse:
    return JsonResponse(payload, status=status, json_dumps_params={"ensure_ascii": False})


def _truncate(text: str, max_length: int) -> str:
    value = (text or "").strip()
    if len(value) <= max_length:
        return value
    if max_length <= 1:
        return value[:max_length]
    return f"{value[: max_length - 1]}…"


def _build_item_url(request, item: dict) -> str:
    item_type = item["item_type"]
    store_id = item["store_id"]
    item_id = item["item_id"]

    if item_type == ITEM_TYPE_PRODUCT:
        path = reverse("products:product_detail", kwargs={"store_id": store_id, "product_id": item_id})
    elif item_type == ITEM_TYPE_MEETUP:
        path = reverse("meetup:meetup_detail", kwargs={"store_id": store_id, "meetup_id": item_id})
    elif item_type == ITEM_TYPE_LIVE_LECTURE:
        path = reverse("lecture:live_lecture_detail", kwargs={"store_id": store_id, "live_lecture_id": item_id})
    elif item_type == ITEM_TYPE_DIGITAL_FILE:
        path = reverse("file:file_detail", kwargs={"store_id": store_id, "file_id": item_id})
    else:
        raise ValueError("지원하지 않는 아이템 타입입니다.")

    return request.build_absolute_uri(path)


def _decorate_items_with_url(request, items: list[dict]) -> list[dict]:
    decorated = []
    for item in items:
        cloned = dict(item)
        cloned["detail_url"] = _build_item_url(request, cloned)
        decorated.append(cloned)
    return decorated


def _build_select_component(items: list[dict], *, custom_id: str, placeholder: str) -> dict:
    options = []
    for item in items:
        sales_suffix = ""
        if item.get("sales_count", 0) > 1:
            sales_suffix = f" (판매: {item['sales_count']}건)"
        label = _truncate(f"{item['title']} / {item['price_text']}{sales_suffix}", 100)
        description = _truncate(f"{item['item_type_label']} · {item['store_id']}", 100)
        options.append(
            {
                "label": label,
                "description": description,
                "value": f"{item['item_type']}:{item['item_id']}",
            }
        )

    return {
        "type": 1,
        "components": [
            {
                "type": 3,
                "custom_id": custom_id,
                "placeholder": placeholder,
                "options": options,
                "min_values": 1,
                "max_values": 1,
            }
        ],
    }


def _build_webview_button(url: str, label: str) -> dict:
    return {
        "type": 1,
        "components": [
            {
                "type": 2,
                "style": 5,
                "label": label,
                "url": url,
            }
        ],
    }


def _build_item_button(url: str, label: str = "사토샵에서 보기") -> dict:
    return {
        "type": 1,
        "components": [
            {
                "type": 2,
                "style": 5,
                "label": label,
                "url": url,
            }
        ],
    }


def _interaction_message(content: str, *, components: list[dict] | None = None, ephemeral: bool = True) -> dict:
    data = {"content": content}
    if components:
        data["components"] = components
    if ephemeral:
        data["flags"] = DISCORD_EPHEMERAL
    return {
        "type": DISCORD_RESPONSE_MESSAGE,
        "data": data,
    }


def _verify_discord_signature(request, public_key_hex: str) -> bool:
    signature = request.headers.get("X-Signature-Ed25519", "")
    timestamp = request.headers.get("X-Signature-Timestamp", "")
    if not signature or not timestamp:
        return False

    try:
        verify_key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex.strip()))
        verify_key.verify(bytes.fromhex(signature), timestamp.encode("utf-8") + request.body)
        return True
    except (ValueError, InvalidSignature):
        return False


def _handle_application_command(request, payload: dict) -> dict:
    command_name = ((payload.get("data") or {}).get("name") or "").strip()

    if command_name == COMMAND_RECENT_REGISTERED:
        items = _decorate_items_with_url(request, get_recent_registered_items(limit=20))
        if not items:
            return _interaction_message("최근 등록된 아이템이 없습니다.")

        select = _build_select_component(
            items,
            custom_id=SELECT_ID_RECENT_REGISTERED,
            placeholder="최근 등록 아이템을 선택하세요",
        )
        webview_url = request.build_absolute_uri(reverse("satoshop_bot:recent_registered_items_webview"))
        return _interaction_message(
            "최근 등록 아이템 20개입니다. 항목을 선택하면 상세 링크를 띄웁니다.",
            components=[select, _build_webview_button(webview_url, "등록 목록 웹뷰 열기")],
        )

    if command_name == COMMAND_RECENT_SOLD:
        items = _decorate_items_with_url(request, get_recent_sold_items(limit=20))
        if not items:
            return _interaction_message("최근 판매된 아이템이 없습니다.")

        select = _build_select_component(
            items,
            custom_id=SELECT_ID_RECENT_SOLD,
            placeholder="최근 판매 아이템을 선택하세요",
        )
        webview_url = request.build_absolute_uri(reverse("satoshop_bot:recent_sold_items_webview"))
        return _interaction_message(
            "최근 판매 아이템 20개입니다. 다중 판매 항목은 '(판매: N건)'으로 표시됩니다.",
            components=[select, _build_webview_button(webview_url, "판매 목록 웹뷰 열기")],
        )

    return _interaction_message("지원하지 않는 명령어입니다.")


def _resolve_selected_item(request, *, select_id: str, selected_value: str) -> dict | None:
    if select_id == SELECT_ID_RECENT_REGISTERED:
        items = _decorate_items_with_url(request, get_recent_registered_items(limit=20))
    elif select_id == SELECT_ID_RECENT_SOLD:
        items = _decorate_items_with_url(request, get_recent_sold_items(limit=20))
    else:
        return None

    lookup = build_recent_items_lookup(items)
    return lookup.get(selected_value)


def _handle_message_component(request, payload: dict) -> dict:
    data = payload.get("data") or {}
    select_id = data.get("custom_id", "")
    values = data.get("values") or []
    if not values:
        return _interaction_message("선택한 항목이 없습니다.")

    selected_value = values[0]
    item = _resolve_selected_item(
        request,
        select_id=select_id,
        selected_value=selected_value,
    )
    if not item:
        return _interaction_message("선택한 아이템 정보를 찾을 수 없습니다.")

    content = f"{item['title']} / {item['price_text']}"
    if select_id == SELECT_ID_RECENT_SOLD and item.get("sales_count", 0) > 1:
        content = f"{content} (판매: {item['sales_count']}건)"
    return _interaction_message(content, components=[_build_item_button(item["detail_url"])])


@csrf_exempt
@require_POST
def discord_interactions(request):
    active_bot = DiscordBot.get_active_bot()
    if not active_bot:
        return _json_response({"detail": "활성 디스코드 봇이 없습니다."}, status=503)
    if not active_bot.public_key:
        return _json_response({"detail": "디스코드 공개키가 설정되지 않았습니다."}, status=503)

    if not _verify_discord_signature(request, active_bot.public_key):
        return _json_response({"detail": "서명 검증 실패"}, status=401)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _json_response({"detail": "JSON 파싱 실패"}, status=400)

    interaction_type = payload.get("type")
    if interaction_type == DISCORD_PING:
        return _json_response({"type": DISCORD_RESPONSE_PONG})
    if interaction_type == DISCORD_APPLICATION_COMMAND:
        return _json_response(_handle_application_command(request, payload))
    if interaction_type == DISCORD_MESSAGE_COMPONENT:
        return _json_response(_handle_message_component(request, payload))

    logger.info("미지원 디스코드 인터랙션 type=%s", interaction_type)
    return _json_response(_interaction_message("지원하지 않는 인터랙션입니다."))


@require_GET
def recent_registered_items_webview(request):
    items = _decorate_items_with_url(request, get_recent_registered_items(limit=20))
    context = {
        "page_title": "사토샵 최근 등록 아이템",
        "page_description": "전체 스토어의 최근 등록 아이템 20개",
        "items": items,
        "is_sold_list": False,
    }
    return render(request, "satoshop_bot/recent_items_webview.html", context)


@require_GET
def recent_sold_items_webview(request):
    items = _decorate_items_with_url(request, get_recent_sold_items(limit=20))
    context = {
        "page_title": "사토샵 최근 판매 아이템",
        "page_description": "전체 스토어의 최근 판매 아이템 20개",
        "items": items,
        "is_sold_list": True,
    }
    return render(request, "satoshop_bot/recent_items_webview.html", context)
