from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from .authentication import authenticate_request
from .policies import apply_cors_headers, enforce_ip_allowlist, enforce_origin_allowlist
from .serializers import serialize_store_list, serialize_store_owner
from .services import get_active_stores_with_relations, get_store_owner


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
