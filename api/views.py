from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction, models
from django.contrib.auth import get_user_model
from boards.models import Notice

from .authentication import authenticate_request
from .policies import apply_cors_headers, enforce_ip_allowlist, enforce_origin_allowlist
from .serializers import (
    serialize_digital_file,
    serialize_live_lecture,
    serialize_meetup,
    serialize_product,
    serialize_store_item_payload,
    serialize_store_list,
    serialize_store_owner,
    serialize_notice_summary,
    serialize_notice_detail,
)
from .services import (
    get_active_digital_files,
    get_active_live_lectures,
    get_active_meetups,
    get_active_products,
    get_active_stores_with_relations,
    get_store_owner,
    get_active_notices,
    issue_store_lightning_invoice,
)
from orders.models import Order, OrderItem
from products.models import Product
from django.utils import timezone
import json


User = get_user_model()


@require_GET
def store_feed(request):
    """활성 스토어 및 연관 리소스 목록을 반환."""
    ip_block = enforce_ip_allowlist(request)
    if ip_block:
        return ip_block

    origin_check = enforce_origin_allowlist(request)
    if origin_check.response:
        return origin_check.response

    auth_result = authenticate_request(request)
    if not auth_result.is_authenticated:
        return auth_result.response

    stores = get_active_stores_with_relations()
    payload = serialize_store_list(stores)
    response = JsonResponse(payload, status=200, json_dumps_params={"ensure_ascii": False})
    apply_cors_headers(response, origin_check)
    return response


@require_GET
def store_owner_info(request, store_id: str):
    """스토어별 주인장 공개 정보를 반환."""
    ip_block = enforce_ip_allowlist(request)
    if ip_block:
        return ip_block

    origin_check = enforce_origin_allowlist(request)
    if origin_check.response:
        return origin_check.response

    auth_result = authenticate_request(request)
    if not auth_result.is_authenticated:
        return auth_result.response

    store = get_store_owner(store_id)
    if not store:
        return JsonResponse({"detail": "스토어를 찾을 수 없습니다."}, status=404)

    payload = serialize_store_owner(store)
    response = JsonResponse(payload, status=200, json_dumps_params={"ensure_ascii": False})
    apply_cors_headers(response, origin_check)
    return response


def _store_item_response(request, store_id: str, fetch_fn, serializer_fn):
    ip_block = enforce_ip_allowlist(request)
    if ip_block:
        return ip_block

    origin_check = enforce_origin_allowlist(request)
    if origin_check.response:
        return origin_check.response

    auth_result = authenticate_request(request)
    if not auth_result.is_authenticated:
        return auth_result.response

    store = get_store_owner(store_id)
    if not store:
        return JsonResponse({"detail": "스토어를 찾을 수 없습니다."}, status=404)

    api_key = auth_result.api_key
    channel_value = ""
    if api_key:
        channel_value = api_key.channel_slug or f"api-{api_key.key_prefix}"

    items = fetch_fn(store)
    payload = serialize_store_item_payload(store, items, serializer_fn)
    response = JsonResponse(payload, status=200, json_dumps_params={"ensure_ascii": False})
    apply_cors_headers(response, origin_check)
    return response


@require_GET
def store_products(request, store_id: str):
    return _store_item_response(request, store_id, get_active_products, serialize_product)


@require_GET
def store_meetups(request, store_id: str):
    return _store_item_response(request, store_id, get_active_meetups, serialize_meetup)


@require_GET
def store_live_lectures(request, store_id: str):
    return _store_item_response(request, store_id, get_active_live_lectures, serialize_live_lecture)


@require_GET
def store_digital_files(request, store_id: str):
    return _store_item_response(request, store_id, get_active_digital_files, serialize_digital_file)


@require_GET
def notice_list(request):
    """공지사항 목록을 반환."""
    ip_block = enforce_ip_allowlist(request)
    if ip_block:
        return ip_block

    origin_check = enforce_origin_allowlist(request)
    if origin_check.response:
        return origin_check.response

    auth_result = authenticate_request(request)
    if not auth_result.is_authenticated:
        return auth_result.response

    notices = get_active_notices()
    payload = {"notices": [serialize_notice_summary(notice) for notice in notices]}
    response = JsonResponse(payload, status=200, json_dumps_params={"ensure_ascii": False})
    apply_cors_headers(response, origin_check)
    return response


@require_GET
def notice_detail(request, notice_id: int):
    """공지사항 단건 상세를 반환."""
    ip_block = enforce_ip_allowlist(request)
    if ip_block:
        return ip_block

    origin_check = enforce_origin_allowlist(request)
    if origin_check.response:
        return origin_check.response

    auth_result = authenticate_request(request)
    if not auth_result.is_authenticated:
        return auth_result.response

    try:
        notice = get_active_notices().get(id=notice_id)
    except Notice.DoesNotExist:
        return JsonResponse({"detail": "공지사항을 찾을 수 없습니다."}, status=404)

    payload = serialize_notice_detail(notice)
    response = JsonResponse(payload, status=200, json_dumps_params={"ensure_ascii": False})
    apply_cors_headers(response, origin_check)
    return response


@require_POST
@transaction.atomic
@csrf_exempt
def store_create_order(request, store_id: str):
    """스토어별 상품 주문 생성 (장바구니 없이 단일 호출)."""
    ip_block = enforce_ip_allowlist(request)
    if ip_block:
        return ip_block

    origin_check = enforce_origin_allowlist(request)
    if origin_check.response:
        return origin_check.response

    auth_result = authenticate_request(request)
    if not auth_result.is_authenticated:
        return auth_result.response

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"detail": "JSON 형식이 아닙니다."}, status=400)

    required_fields = [
        "buyer_name",
        "buyer_phone",
        "buyer_email",
        "shipping_postal_code",
        "shipping_address",
        "shipping_detail_address",
        "items",
    ]
    missing = [f for f in required_fields if not payload.get(f)]
    if missing:
        return JsonResponse({"detail": f"필수 필드 누락: {', '.join(missing)}"}, status=400)

    items_data = payload.get("items") or []
    if not isinstance(items_data, list) or not items_data:
        return JsonResponse({"detail": "items 는 비어 있을 수 없습니다."}, status=400)

    store = get_store_owner(store_id)
    if not store:
        return JsonResponse({"detail": "스토어를 찾을 수 없습니다."}, status=404)

    product_ids = []
    quantities = {}
    for item in items_data:
        pid = item.get("product_id")
        qty = item.get("quantity", 0)
        if not pid or qty <= 0:
            return JsonResponse({"detail": "product_id와 quantity는 필수이며 수량은 1 이상이어야 합니다."}, status=400)
        product_ids.append(pid)
        quantities[pid] = qty

    products = list(
        Product.objects.filter(
            id__in=product_ids,
            store=store,
            is_active=True,
            is_temporarily_out_of_stock=False,
        )
    )
    if len(products) != len(set(product_ids)):
        return JsonResponse({"detail": "유효하지 않은 상품이 포함되어 있습니다."}, status=400)

    subtotal = 0
    order_items_data = []
    for product in products:
        qty = quantities[product.id]
        if product.stock_quantity is not None and product.stock_quantity < qty:
            return JsonResponse({"detail": f"{product.title} 재고 부족"}, status=400)
        unit_price = product.public_discounted_price if product.public_discounted_price else product.public_price
        order_items_data.append(
            {
                "product": product,
                "title": product.title,
                "unit_price": unit_price,
                "quantity": qty,
            }
        )
        subtotal += unit_price * qty

    shipping_fee = store.get_shipping_fee_sats(subtotal_sats=subtotal) if hasattr(store, "get_shipping_fee_sats") else 0
    total_amount = subtotal + (shipping_fee or 0)

    system_user, _ = User.objects.get_or_create(
        username="api_order_user",
        defaults={"email": "api@satoshop.local", "first_name": "API", "last_name": "User"},
    )

    api_key = auth_result.api_key
    channel_value = ""
    if api_key:
        channel_value = api_key.channel_slug or f"api-{api_key.key_prefix}"

    status = "paid" if payload.get("mark_as_paid") else "pending"
    paid_at = timezone.now() if status == "paid" else None

    order = Order.objects.create(
        user=system_user,
        store=store,
        status=status,
        delivery_status="preparing",
        channel=channel_value,
        buyer_name=payload["buyer_name"],
        buyer_phone=payload["buyer_phone"],
        buyer_email=payload["buyer_email"],
        shipping_postal_code=payload["shipping_postal_code"],
        shipping_address=payload["shipping_address"],
        shipping_detail_address=payload["shipping_detail_address"],
        order_memo=payload.get("order_memo", ""),
        subtotal=subtotal,
        shipping_fee=shipping_fee or 0,
        total_amount=total_amount,
        payment_id=payload.get("payment_id", ""),
        paid_at=paid_at,
    )

    for item in order_items_data:
        OrderItem.objects.create(
            order=order,
            product=item["product"],
            product_title=item["title"],
            product_price=item["unit_price"],
            quantity=item["quantity"],
            selected_options={},
            options_price=0,
        )
        # 재고 차감
        if item["product"].stock_quantity is not None:
            Product.objects.filter(id=item["product"].id).update(
                stock_quantity=models.F("stock_quantity") - item["quantity"]
            )

    response_payload = {
        "order_id": order.id,
        "order_number": order.order_number,
        "status": order.status,
        "subtotal": subtotal,
        "shipping_fee": shipping_fee or 0,
        "total_amount": total_amount,
        "paid_at": paid_at.isoformat() if paid_at else None,
        "items": [
            {
                "product_id": item["product"].id,
                "title": item["title"],
                "unit_price": item["unit_price"],
                "quantity": item["quantity"],
                "line_total": item["unit_price"] * item["quantity"],
            }
            for item in order_items_data
        ],
    }

    response = JsonResponse(response_payload, status=201, json_dumps_params={"ensure_ascii": False})
    apply_cors_headers(response, origin_check)
    return response


@require_POST
@csrf_exempt
def store_create_lightning_invoice(request, store_id: str):
    """스토어 주인장용 BOLT11 인보이스 발행 API."""
    ip_block = enforce_ip_allowlist(request)
    if ip_block:
        return ip_block

    origin_check = enforce_origin_allowlist(request)
    if origin_check.response:
        return origin_check.response

    auth_result = authenticate_request(request)
    if not auth_result.is_authenticated:
        return auth_result.response

    store = get_store_owner(store_id)
    if not store:
        return JsonResponse({"detail": "스토어를 찾을 수 없습니다."}, status=404)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"detail": "JSON 형식이 아닙니다."}, status=400)

    amount_sats = payload.get("amount_sats")
    if not isinstance(amount_sats, int) or amount_sats < 1:
        return JsonResponse({"detail": "amount_sats는 1 이상의 정수여야 합니다."}, status=400)

    memo = payload.get("memo") or "외부 앱 결제"
    if not isinstance(memo, str):
        return JsonResponse({"detail": "memo는 문자열이어야 합니다."}, status=400)
    if len(memo) > 120:
        return JsonResponse({"detail": "memo는 최대 120자까지 허용됩니다."}, status=400)

    expires_in_minutes = payload.get("expires_in_minutes", 15)
    if not isinstance(expires_in_minutes, int) or expires_in_minutes < 1:
        return JsonResponse({"detail": "expires_in_minutes는 1 이상의 정수여야 합니다."}, status=400)

    try:
        result = issue_store_lightning_invoice(
            store,
            amount_sats=amount_sats,
            memo=memo,
            expires_in_minutes=expires_in_minutes,
        )
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    except RuntimeError as exc:
        return JsonResponse({"detail": str(exc)}, status=502)

    payment_request = result.get("invoice") or ""
    expires_at = result.get("expires_at")
    if expires_at and timezone.is_naive(expires_at):
        expires_at = timezone.make_aware(expires_at)

    response_payload = {
        "store_id": store.store_id,
        "amount_sats": result.get("amount_sats") or amount_sats,
        "payment_request": payment_request,
        "invoice_uri": f"lightning:{payment_request}" if payment_request else "",
        "payment_hash": result.get("payment_hash") or "",
        "expires_at": expires_at.isoformat() if expires_at else None,
    }
    response = JsonResponse(response_payload, status=201, json_dumps_params={"ensure_ascii": False})
    apply_cors_headers(response, origin_check)
    return response


@require_GET
def api_index(request):
    """사용 가능한 API 엔드포인트 목록 안내."""
    ip_block = enforce_ip_allowlist(request)
    if ip_block:
        return ip_block

    origin_check = enforce_origin_allowlist(request)
    if origin_check.response:
        return origin_check.response

    payload = {
        "version": "v1",
        "endpoints": [
            {"path": "/api/v1/stores/", "method": "GET", "description": "활성 스토어와 공개 데이터 목록"},
            {"path": "/api/v1/stores/<store_id>/lightning-invoices/", "method": "POST", "description": "스토어 라이트닝 인보이스 발행"},
        ],
    }
    response = JsonResponse(payload, status=200, json_dumps_params={"ensure_ascii": False})
    apply_cors_headers(response, origin_check)
    return response


def api_docs(request):
    """Swagger UI 기반 문서 페이지."""
    return render(
        request,
        "api/swagger_ui.html",
        {
            "openapi_url": request.build_absolute_uri("/static/api/openapi-v1.json"),
        },
    )
