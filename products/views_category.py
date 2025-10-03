import json
import logging

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Max
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from stores.decorators import store_owner_required
from stores.models import Store

from .models import Product, ProductCategory


logger = logging.getLogger(__name__)

DEFAULT_CATEGORY_NAME = '카테고리 없음'


def _get_store_for_owner(store_id, user):
    """스토어 소유자 권한이 있는지 확인하고 스토어 반환."""

    return get_object_or_404(
        Store,
        store_id=store_id,
        owner=user,
        deleted_at__isnull=True,
    )


def _get_default_category(store):
    """스토어의 기본 카테고리(카테고리 없음)를 반환. 필요 시 생성."""

    category, _created = ProductCategory.objects.get_or_create(
        store=store,
        name=DEFAULT_CATEGORY_NAME,
        defaults={'order': 0},
    )
    return category


def _serialize_category(category):
    return {
        'id': category.id,
        'name': category.name,
        'order': category.order,
        'product_count': getattr(category, 'product_count', category.products.count()),
        'is_default': category.name == DEFAULT_CATEGORY_NAME,
    }


@login_required
@store_owner_required
def category_manage(request, store_id):
    """상품 카테고리 관리 페이지"""

    store = _get_store_for_owner(store_id, request.user)
    categories_qs = ProductCategory.objects.filter(store=store).order_by('order', 'created_at')
    categories = list(categories_qs)

    context = {
        'store': store,
        'categories': categories,
        'category_data': [_serialize_category(category) for category in categories],
    }

    return render(request, 'products/product_category_manage.html', context)


@login_required
@store_owner_required
@require_http_methods(["GET"])
def category_list_api(request, store_id):
    """카테고리 목록 조회 API"""

    store = _get_store_for_owner(store_id, request.user)
    categories = (
        ProductCategory.objects.filter(store=store)
        .annotate(product_count=Count('products'))
        .order_by('order', 'created_at')
    )

    data = [_serialize_category(category) for category in categories]
    return JsonResponse({'success': True, 'categories': data})


@login_required
@store_owner_required
@require_http_methods(["POST"])
def category_create_api(request, store_id):
    """카테고리 생성 API"""

    store = _get_store_for_owner(store_id, request.user)

    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '잘못된 JSON 형식입니다.'})

    name = (payload.get('name') or '').strip()
    if not name:
        return JsonResponse({'success': False, 'error': '카테고리 이름을 입력해주세요.'})

    if ProductCategory.objects.filter(store=store, name=name).exists():
        return JsonResponse({'success': False, 'error': '이미 존재하는 카테고리 이름입니다.'})

    max_order = (
        ProductCategory.objects
        .filter(store=store)
        .exclude(name=DEFAULT_CATEGORY_NAME)
        .aggregate(max_order=Max('order'))
        .get('max_order')
        or 0
    )

    category = ProductCategory.objects.create(
        store=store,
        name=name,
        order=max_order + 1,
    )

    return JsonResponse({'success': True, 'category': _serialize_category(category)})


@login_required
@store_owner_required
@require_http_methods(["PUT", "PATCH"])
def category_update_api(request, store_id, category_id):
    """카테고리 이름 수정 API"""

    store = _get_store_for_owner(store_id, request.user)
    category = get_object_or_404(ProductCategory, id=category_id, store=store)

    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '잘못된 JSON 형식입니다.'})

    name = (payload.get('name') or '').strip()
    if not name:
        return JsonResponse({'success': False, 'error': '카테고리 이름을 입력해주세요.'})

    if category.name == DEFAULT_CATEGORY_NAME:
        return JsonResponse({'success': False, 'error': '기본 카테고리는 이름을 변경할 수 없습니다.'})

    if (
        ProductCategory.objects.filter(store=store, name=name)
        .exclude(id=category_id)
        .exists()
    ):
        return JsonResponse({'success': False, 'error': '이미 존재하는 카테고리 이름입니다.'})

    category.name = name
    category.save(update_fields=['name'])

    category.product_count = category.products.count()
    return JsonResponse({'success': True, 'category': _serialize_category(category)})


@login_required
@store_owner_required
@require_http_methods(["DELETE"])
def category_delete_api(request, store_id, category_id):
    """카테고리 삭제 API"""

    store = _get_store_for_owner(store_id, request.user)
    category = get_object_or_404(ProductCategory, id=category_id, store=store)

    if category.name == DEFAULT_CATEGORY_NAME:
        return JsonResponse({'success': False, 'error': '기본 카테고리는 삭제할 수 없습니다.'})

    default_category = _get_default_category(store)

    try:
        with transaction.atomic():
            Product.objects.filter(category=category).update(category=default_category)
            category.delete()
    except Exception as exc:
        logger.error("카테고리 삭제 오류: %s", exc, exc_info=True)
        return JsonResponse({'success': False, 'error': '카테고리 삭제에 실패했습니다.'})

    return JsonResponse({'success': True, 'message': '카테고리가 삭제되었습니다.'})


@login_required
@store_owner_required
@require_http_methods(["POST"])
def category_reorder_api(request, store_id):
    """카테고리 정렬 순서 변경 API"""

    store = _get_store_for_owner(store_id, request.user)

    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '잘못된 JSON 형식입니다.'})

    orders = payload.get('orders') or []
    if not isinstance(orders, list):
        return JsonResponse({'success': False, 'error': 'orders 형식이 올바르지 않습니다.'})

    default_category = _get_default_category(store)

    try:
        with transaction.atomic():
            for item in orders:
                category_id = item.get('id')
                order_value = item.get('order')

                if not isinstance(category_id, int) or not isinstance(order_value, int):
                    continue

                if category_id == default_category.id:
                    # 기본 카테고리는 항상 0으로 유지
                    ProductCategory.objects.filter(id=category_id, store=store).update(order=0)
                    continue

                ProductCategory.objects.filter(id=category_id, store=store).update(order=order_value)
    except Exception as exc:
        logger.error("카테고리 순서 변경 오류: %s", exc, exc_info=True)
        return JsonResponse({'success': False, 'error': '카테고리 순서 변경에 실패했습니다.'})

    return JsonResponse({'success': True, 'message': '카테고리 순서가 변경되었습니다.'})
