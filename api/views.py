from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .authentication import authenticate_request
from .policies import apply_cors_headers, enforce_ip_allowlist, enforce_origin_allowlist
from .serializers import serialize_store_list
from .services import get_active_stores_with_relations


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
