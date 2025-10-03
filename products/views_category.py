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


@login_required
@store_owner_required
@require_http_methods(["GET"])
def category_products_api(request, store_id):
    """카테고리 매칭용 상품 목록 API"""

    store = _get_store_for_owner(store_id, request.user)

    try:
        page = max(int(request.GET.get('page', 1)), 1)
    except (TypeError, ValueError):
        page = 1

    try:
        page_size = int(request.GET.get('page_size', 30))
    except (TypeError, ValueError):
        page_size = 30

    page_size = min(max(page_size, 10), 60)

    search = (request.GET.get('search') or '').strip()
    category_filter = request.GET.get('category_id')

    products = (
        Product.objects.filter(store=store)
        .select_related('category')
        .order_by('-created_at')
    )

    if search:
        products = products.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search)
        )

    if category_filter not in (None, '', 'null'):
        try:
            category_id = int(category_filter)
            products = products.filter(category_id=category_id)
        except (TypeError, ValueError):
            return JsonResponse({'success': False, 'error': '유효하지 않은 카테고리 필터입니다.'})

    total = products.count()
    offset = (page - 1) * page_size
    product_list = list(products[offset:offset + page_size])

    data = []
    for product in product_list:
        if product.price_display == 'krw' and product.price_krw is not None:
            price_label = f"{product.price_krw:,} 원"
        else:
            price_label = '무료' if product.price == 0 else f"{product.price:,} sats"

        data.append({
            'id': product.id,
            'title': product.title,
            'category_id': product.category_id,
            'category_name': product.category.name if product.category else DEFAULT_CATEGORY_NAME,
            'is_active': product.is_active,
            'is_temporarily_out_of_stock': product.is_temporarily_out_of_stock,
            'created_at_display': product.created_at.strftime('%Y-%m-%d'),
            'price_label': price_label,
        })

    has_next = offset + len(product_list) < total

    return JsonResponse({
        'success': True,
        'products': data,
        'total': total,
        'page': page,
        'page_size': page_size,
        'has_next': has_next,
    })


@login_required
@store_owner_required
@require_http_methods(["POST"])
def category_assign_api(request, store_id):
    """상품을 카테고리에 매칭"""

    store = _get_store_for_owner(store_id, request.user)

    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '잘못된 JSON 형식입니다.'})

    product_id = payload.get('product_id')
    category_id = payload.get('category_id')

    if not isinstance(product_id, int):
        return JsonResponse({'success': False, 'error': '상품 ID가 필요합니다.'})

    product = get_object_or_404(Product, id=product_id, store=store)

    if category_id in (None, '', 'null', 'default'):
        category = _get_default_category(store)
    else:
        try:
            category = ProductCategory.objects.get(id=int(category_id), store=store)
        except (ValueError, ProductCategory.DoesNotExist):
            return JsonResponse({'success': False, 'error': '카테고리를 찾을 수 없습니다.'})

    previous_category_id = product.category_id

    if previous_category_id == category.id:
        return JsonResponse({
            'success': True,
            'message': '이미 선택한 카테고리에 속해 있는 상품입니다.',
            'product': {
                'id': product.id,
                'category_id': product.category_id,
                'category_name': product.category.name if product.category else DEFAULT_CATEGORY_NAME,
            },
            'previous_category_id': previous_category_id,
        })

    product.category = category
    product.save(update_fields=['category', 'updated_at'])

    return JsonResponse({
        'success': True,
        'product': {
            'id': product.id,
            'category_id': product.category_id,
            'category_name': product.category.name if product.category else DEFAULT_CATEGORY_NAME,
        },
        'previous_category_id': previous_category_id,
    })
