from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum, Max
from django.utils import timezone
from stores.models import Store
from stores.decorators import store_owner_required
from .models import Menu, MenuCategory, MenuOrder, MenuOrderItem
from .forms import MenuForm, MenuCategoryForm
import logging
import json

from myshop.models import ExchangeRate
from storage import utils as storage_utils

logger = logging.getLogger(__name__)


def _apply_menu_pricing(menu, cleaned_data):
    """폼 데이터 기반으로 메뉴 가격 정보를 갱신합니다."""
    price_display = cleaned_data.get('price_display', menu.price_display)
    price = cleaned_data.get('price') or 0
    is_discounted = cleaned_data.get('is_discounted')
    discounted_price = cleaned_data.get('discounted_price')

    latest_rate = ExchangeRate.get_latest_rate()

    menu.price_display = price_display

    if price_display == 'krw':
        menu.price_krw = price
        if latest_rate:
            menu.price = latest_rate.get_sats_from_krw(price)
        elif menu.price is None:
            menu.price = 0

        if is_discounted and discounted_price:
            menu.discounted_price_krw = discounted_price
            if latest_rate:
                menu.discounted_price = latest_rate.get_sats_from_krw(discounted_price)
            else:
                menu.discounted_price = None
        else:
            menu.discounted_price = None
            menu.discounted_price_krw = None
    else:
        menu.price = price
        if latest_rate:
            menu.price_krw = latest_rate.get_krw_from_sats(price)
        else:
            menu.price_krw = None

        if is_discounted and discounted_price:
            menu.discounted_price = discounted_price
            if latest_rate:
                menu.discounted_price_krw = latest_rate.get_krw_from_sats(discounted_price)
            else:
                menu.discounted_price_krw = None
        else:
            menu.discounted_price = None
            menu.discounted_price_krw = None


def _delete_menu_image(menu_image):
    """S3와 DB에서 메뉴 이미지를 제거합니다."""
    try:
        delete_result = storage_utils.delete_file_from_s3(menu_image.file_path)
        if isinstance(delete_result, dict) and not delete_result.get('success', True):
            logger.warning(
                "메뉴 이미지 S3 삭제 실패 (id=%s): %s",
                menu_image.id,
                delete_result.get('error') or '알 수 없는 오류'
            )
    except Exception as exc:
        logger.warning("메뉴 이미지 S3 삭제 실패 (id=%s): %s", menu_image.id, exc)
    finally:
        menu_image.delete()


def _handle_menu_image_upload(menu, image_file, user):
    """메뉴 이미지 업로드를 처리합니다."""
    if not image_file:
        return None

    upload_result = storage_utils.upload_menu_image(image_file, menu, user)
    if not upload_result.get('success'):
        logger.warning("메뉴 이미지 업로드 실패: %s", upload_result.get('error'))
        return None
    return upload_result.get('menu_image')


def get_store_or_404(store_id, user):
    """스토어를 가져오거나 404 에러 반환 (권한 확인 포함)"""
    return get_object_or_404(Store, store_id=store_id, owner=user, deleted_at__isnull=True)


def menu_list(request, store_id):
    """메뉴 관리 목록 - 권한에 따라 다른 페이지 표시"""
    # 스토어 조회 (일단 활성화된 스토어인지만 확인)
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
    
    # 로그인하지 않았거나 스토어 주인이 아닌 경우
    if not request.user.is_authenticated or store.owner != request.user:
        # 일반 사용자는 디바이스 선택 페이지로
        context = {
            'store': store,
        }
        return render(request, 'menu/menu_device_select.html', context)
    
    # 스토어 주인은 기존 메뉴 관리 페이지로
    # 모든 메뉴 가져오기 (관리자는 모든 메뉴를 볼 수 있음)
    menus = Menu.objects.filter(store=store).prefetch_related('categories', 'images').order_by('-created_at')
    
    # 카테고리별 메뉴 목록 가져오기
    categories = MenuCategory.objects.filter(store=store).order_by('order', 'id')
    uncategorized_menus = Menu.objects.filter(store=store, categories__isnull=True).order_by('-created_at')
    
    context = {
        'store': store,
        'menus': menus,
        'categories': categories,
        'uncategorized_menus': uncategorized_menus,
        'is_public_view': False,  # 관리자 뷰임을 명시
    }
    
    return render(request, 'menu/menu_list.html', context)


@login_required
def add_menu(request, store_id):
    """메뉴 추가"""
    store = get_store_or_404(store_id, request.user)
    
    if request.method == 'POST':
        form = MenuForm(request.POST, request.FILES, store=store)
        if form.is_valid():
            price_value = form.cleaned_data.get('price')
            if price_value is None or price_value <= 0:
                messages.error(request, '가격은 0보다 큰 값이어야 합니다.')
                return render(request, 'menu/add_menu.html', {'form': form, 'store': store})

            try:
                with transaction.atomic():
                    menu = form.save(commit=False)
                    menu.store = store
                    _apply_menu_pricing(menu, form.cleaned_data)
                    menu.save()
                    form.save_m2m()

                    image_file = request.FILES.get('images')
                    if image_file:
                        for existing_image in menu.images.all():
                            _delete_menu_image(existing_image)
                        uploaded_image = _handle_menu_image_upload(menu, image_file, request.user)
                        if not uploaded_image:
                            messages.warning(request, '이미지 업로드에 실패하여 메뉴는 이미지 없이 저장되었습니다.')

                messages.success(request, f'메뉴 "{menu.name}"이(가) 성공적으로 추가되었습니다.')
                return redirect('menu:menu_list', store_id=store_id)
            except Exception as exc:
                logger.error('메뉴 추가 중 오류 발생: %s', exc, exc_info=True)
                messages.error(request, '메뉴를 저장하는 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.')
    else:
        form = MenuForm(store=store)

    return render(request, 'menu/add_menu.html', {
        'form': form,
        'store': store,
    })


@login_required
def edit_menu(request, store_id, menu_id):
    """메뉴 수정"""
    store = get_store_or_404(store_id, request.user)
    menu = get_object_or_404(Menu, id=menu_id, store=store)
    
    if request.method == 'POST':
        form = MenuForm(request.POST, request.FILES, instance=menu, store=store)
        if form.is_valid():
            price_value = form.cleaned_data.get('price')
            if price_value is None or price_value <= 0:
                messages.error(request, '가격은 0보다 큰 값이어야 합니다.')
                return render(request, 'menu/edit_menu.html', {'form': form, 'store': store, 'menu': menu})

            try:
                with transaction.atomic():
                    menu = form.save(commit=False)
                    _apply_menu_pricing(menu, form.cleaned_data)
                    menu.save()
                    form.save_m2m()

                    new_image_file = request.FILES.get('images')
                    existing_images = list(menu.images.all())

                    if new_image_file:
                        uploaded_image = _handle_menu_image_upload(menu, new_image_file, request.user)
                        if uploaded_image:
                            for image in existing_images:
                                _delete_menu_image(image)
                        else:
                            messages.warning(request, '새 이미지 업로드에 실패했습니다. 기존 이미지를 유지했습니다.')
                    else:
                        for image in existing_images:
                            keep_flag = request.POST.get(f'keep_image_{image.id}', 'true')
                            if keep_flag.lower() == 'false':
                                _delete_menu_image(image)

                messages.success(request, f'메뉴 "{menu.name}"이(가) 성공적으로 수정되었습니다.')
                return redirect('menu:menu_list', store_id=store_id)
            except Exception as exc:
                logger.error('메뉴 수정 중 오류 발생: %s', exc, exc_info=True)
                messages.error(request, '메뉴를 수정하는 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.')
    else:
        form = MenuForm(instance=menu, store=store)

    return render(request, 'menu/edit_menu.html', {
        'form': form,
        'store': store,
        'menu': menu,
    })


@login_required
@require_POST
def upload_menu_image(request, store_id, menu_id):
    """메뉴 이미지 업로드 API"""
    store = get_store_or_404(store_id, request.user)
    menu = get_object_or_404(Menu, id=menu_id, store=store)
    
    if 'image' not in request.FILES:
        return JsonResponse({'success': False, 'error': '이미지 파일이 없습니다.'})
    
    image_file = request.FILES['image']
    
    # 파일 크기 체크 (10MB 제한)
    if image_file.size > 10 * 1024 * 1024:
        return JsonResponse({'success': False, 'error': '이미지 파일 크기는 10MB를 초과할 수 없습니다.'})
    
    # 파일 형식 체크
    allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    if image_file.content_type not in allowed_types:
        return JsonResponse({'success': False, 'error': '지원하지 않는 이미지 형식입니다.'})
    
    try:
        with transaction.atomic():
            for existing_image in menu.images.all():
                _delete_menu_image(existing_image)

            uploaded_image = _handle_menu_image_upload(menu, image_file, request.user)
            if not uploaded_image:
                return JsonResponse({'success': False, 'error': '이미지 업로드에 실패했습니다.'})

        return JsonResponse({
            'success': True,
            'image_url': uploaded_image.file_url if uploaded_image else None
        })
    except Exception as e:
        logger.error(f"이미지 업로드 실패: {str(e)}")
        return JsonResponse({'success': False, 'error': '이미지 업로드에 실패했습니다.'})


@login_required
def category_manage(request, store_id):
    """카테고리 관리 페이지"""
    store = get_store_or_404(store_id, request.user)
    categories = MenuCategory.objects.filter(store=store).order_by('order', 'id')
    
    context = {
        'store': store,
        'categories': categories,
    }
    
    return render(request, 'menu/category_manage.html', context)


@login_required
@require_http_methods(["GET"])
def category_list_api(request, store_id):
    """카테고리 목록 API"""
    store = get_store_or_404(store_id, request.user)
    categories = MenuCategory.objects.filter(store=store).order_by('order', 'id')
    
    data = []
    for category in categories:
        data.append({
            'id': category.id,
            'name': category.name,
            'order': category.order,
            'menu_count': category.menus.all().count()
        })
    
    return JsonResponse({'success': True, 'categories': data})


@login_required
@require_http_methods(["POST"])
def category_create_api(request, store_id):
    """카테고리 생성 API"""
    store = get_store_or_404(store_id, request.user)
    
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        
        if not name:
            return JsonResponse({'success': False, 'error': '카테고리 이름을 입력해주세요.'})
        
        # 중복 체크
        if MenuCategory.objects.filter(store=store, name=name).exists():
            return JsonResponse({'success': False, 'error': '이미 존재하는 카테고리 이름입니다.'})
        
        # 순서 계산
        max_order = MenuCategory.objects.filter(store=store).aggregate(
            max_order=Max('order')
        )['max_order'] or 0
        
        category = MenuCategory.objects.create(
            store=store,
            name=name,
            order=max_order + 1
        )
        
        return JsonResponse({
            'success': True,
            'category': {
                'id': category.id,
                'name': category.name,
                'order': category.order,
                'menu_count': 0
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '잘못된 JSON 형식입니다.'})
    except Exception as e:
        logger.error(f"카테고리 생성 오류: {str(e)}")
        return JsonResponse({'success': False, 'error': '카테고리 생성에 실패했습니다.'})


@login_required
@require_http_methods(["PUT"])
def category_update_api(request, store_id, category_id):
    """카테고리 수정 API"""
    store = get_store_or_404(store_id, request.user)
    category = get_object_or_404(MenuCategory, id=category_id, store=store)
    
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        
        if not name:
            return JsonResponse({'success': False, 'error': '카테고리 이름을 입력해주세요.'})
        
        # 중복 체크 (자기 자신 제외)
        if MenuCategory.objects.filter(store=store, name=name).exclude(id=category_id).exists():
            return JsonResponse({'success': False, 'error': '이미 존재하는 카테고리 이름입니다.'})
        
        category.name = name
        category.save()
        
        return JsonResponse({
            'success': True,
            'category': {
                'id': category.id,
                'name': category.name,
                'order': category.order,
                'menu_count': category.menus.all().count()
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '잘못된 JSON 형식입니다.'})
    except Exception as e:
        logger.error(f"카테고리 수정 오류: {str(e)}")
        return JsonResponse({'success': False, 'error': '카테고리 수정에 실패했습니다.'})


@login_required
@require_http_methods(["DELETE"])
def category_delete_api(request, store_id, category_id):
    """카테고리 삭제 API"""
    store = get_store_or_404(store_id, request.user)
    category = get_object_or_404(MenuCategory, id=category_id, store=store)
    
    try:
        # 해당 카테고리의 메뉴들을 uncategorized로 이동
        menus = Menu.objects.filter(categories=category)
        menus.update(categories=None)
        
        category.delete()
        
        return JsonResponse({'success': True, 'message': '카테고리가 삭제되었습니다.'})
        
    except Exception as e:
        logger.error(f"카테고리 삭제 오류: {str(e)}")
        return JsonResponse({'success': False, 'error': '카테고리 삭제에 실패했습니다.'})


@login_required
@require_http_methods(["POST"])
def category_reorder_api(request, store_id):
    """카테고리 순서 변경 API"""
    store = get_store_or_404(store_id, request.user)
    
    try:
        data = json.loads(request.body)
        category_orders = data.get('orders', [])
        
        with transaction.atomic():
            for item in category_orders:
                category_id = item.get('id')
                order = item.get('order')
                
                MenuCategory.objects.filter(
                    id=category_id, 
                    store=store
                ).update(order=order)
        
        return JsonResponse({'success': True, 'message': '카테고리 순서가 변경되었습니다.'})
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '잘못된 JSON 형식입니다.'})
    except Exception as e:
        logger.error(f"카테고리 순서 변경 오류: {str(e)}")
        return JsonResponse({'success': False, 'error': '카테고리 순서 변경에 실패했습니다.'})


@login_required
@require_http_methods(["POST"])
def toggle_temporary_out_of_stock(request, store_id, menu_id):
    """메뉴 일시품절 상태 토글"""
    store = get_store_or_404(store_id, request.user)
    menu = get_object_or_404(Menu, id=menu_id, store=store)
    
    try:
        menu.is_temporarily_out_of_stock = not menu.is_temporarily_out_of_stock
        menu.save()
        
        status = "일시품절" if menu.is_temporarily_out_of_stock else "판매중"
        
        return JsonResponse({
            'success': True,
            'is_temporarily_out_of_stock': menu.is_temporarily_out_of_stock,
            'message': f'"{menu.name}" 상태가 "{status}"으로 변경되었습니다.'
        })
        
    except Exception as e:
        logger.error(f"메뉴 상태 변경 오류: {str(e)}")
        return JsonResponse({'success': False, 'error': '상태 변경에 실패했습니다.'})


@login_required
@require_http_methods(["POST"])
def toggle_menu_active(request, store_id, menu_id):
    """메뉴 활성/비활성 상태 토글"""
    store = get_store_or_404(store_id, request.user)
    menu = get_object_or_404(Menu, id=menu_id, store=store)
    
    try:
        menu.is_active = not menu.is_active
        menu.save()
        
        status = "활성" if menu.is_active else "비활성"
        
        return JsonResponse({
            'success': True,
            'is_active': menu.is_active,
            'message': f'"{menu.name}" 상태가 "{status}"으로 변경되었습니다.'
        })
        
    except Exception as e:
        logger.error(f"메뉴 활성 상태 변경 오류: {str(e)}")
        return JsonResponse({'success': False, 'error': '상태 변경에 실패했습니다.'})


@login_required
def manage_menu(request, store_id, menu_id):
    """메뉴 개별 관리 페이지"""
    store = get_store_or_404(store_id, request.user)
    menu = get_object_or_404(Menu, id=menu_id, store=store)
    
    context = {
        'store': store,
        'menu': menu,
    }
    
    return render(request, 'menu/manage_menu.html', context)


@login_required
@require_POST
def delete_menu(request, store_id, menu_id):
    """메뉴 삭제"""
    store = get_store_or_404(store_id, request.user)
    menu = get_object_or_404(Menu, id=menu_id, store=store)
    
    menu_name = menu.name
    # 실제 삭제
    menu.delete()
    
    messages.success(request, f'메뉴 "{menu_name}"이(가) 삭제되었습니다.')
    return redirect('menu:menu_list', store_id=store_id)


@login_required
def menu_orders(request, store_id):
    """메뉴 판매 현황"""
    store = get_store_or_404(store_id, request.user)
    
    # 메뉴별 판매 통계 계산
    from django.db.models import F
    
    menus = Menu.objects.filter(store=store).annotate(
        total_orders=Count('menuorderitem__order', distinct=True, filter=Q(menuorderitem__order__status='paid')),
        total_quantity=Sum('menuorderitem__quantity', filter=Q(menuorderitem__order__status='paid')),
        total_revenue=Sum(F('menuorderitem__menu_price') * F('menuorderitem__quantity'), filter=Q(menuorderitem__order__status='paid'))
    ).filter(total_orders__gt=0).order_by('-total_revenue')
    
    # 전체 통계
    total_menu_orders = MenuOrderItem.objects.filter(
        order__store=store,
        order__status='paid'
    ).values('order').distinct().count()
    
    total_menu_items = MenuOrderItem.objects.filter(
        order__store=store,
        order__status='paid'
    ).aggregate(total=Sum('quantity'))['total'] or 0
    
    total_menu_revenue = MenuOrderItem.objects.filter(
        order__store=store,
        order__status='paid'
    ).aggregate(
        total=Sum(F('menu_price') * F('quantity'))
    )['total'] or 0
    
    context = {
        'store': store,
        'menus_with_orders': menus,
        'total_menu_orders': total_menu_orders,
        'total_menu_items': total_menu_items,
        'total_menu_revenue': total_menu_revenue,
    }
    
    return render(request, 'menu/menu_orders.html', context)


@login_required
def menu_orders_detail(request, store_id, menu_id):
    """특정 메뉴의 주문 현황"""
    from django.db.models import F
    
    store = get_store_or_404(store_id, request.user)
    menu = get_object_or_404(Menu, id=menu_id, store=store)
    
    # 해당 메뉴가 포함된 주문들
    order_items = MenuOrderItem.objects.filter(
        menu=menu,
        order__store=store
    ).select_related('order').order_by('-order__created_at')
    
    # 페이지네이션
    paginator = Paginator(order_items, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 통계
    total_quantity = MenuOrderItem.objects.filter(
        menu=menu,
        order__store=store,
        order__status='paid'
    ).aggregate(total=Sum('quantity'))['total'] or 0
    
    total_revenue = MenuOrderItem.objects.filter(
        menu=menu,
        order__store=store,
        order__status='paid'
    ).aggregate(
        total=Sum(F('menu_price') * F('quantity'))
    )['total'] or 0
    
    context = {
        'store': store,
        'menu': menu,
        'page_obj': page_obj,
        'total_quantity': total_quantity,
        'total_revenue': total_revenue,
    }
    
    return render(request, 'menu/menu_orders_detail.html', context)
