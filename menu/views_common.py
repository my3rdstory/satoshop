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
import os
from django.conf import settings

logger = logging.getLogger(__name__)


def get_store_or_404(store_id, user):
    """스토어를 가져오거나 404 에러 반환 (권한 확인 포함)"""
    return get_object_or_404(Store, store_id=store_id, owner=user, deleted_at__isnull=True)


@login_required
def menu_list(request, store_id):
    """메뉴 관리 목록"""
    store = get_store_or_404(store_id, request.user)
    
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
            menu = form.save(commit=False)
            menu.store = store
            
            # 가격 검증
            if menu.public_price <= 0:
                messages.error(request, '가격은 0보다 큰 값이어야 합니다.')
                return render(request, 'menu/add_menu.html', {'form': form, 'store': store})
            
            # 메뉴 저장
            menu.save()
            
            # 이미지 업로드 처리
            if 'images' in request.FILES:
                for image in request.FILES.getlist('images'):
                    # 이미지 저장 로직 (필요시 구현)
                    pass
            
            messages.success(request, f'메뉴 "{menu.name}"이(가) 성공적으로 추가되었습니다.')
            return redirect('menu:menu_list', store_id=store_id)
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
            # 가격 검증
            if form.cleaned_data['public_price'] <= 0:
                messages.error(request, '가격은 0보다 큰 값이어야 합니다.')
                return render(request, 'menu/edit_menu.html', {'form': form, 'store': store, 'menu': menu})
            
            menu = form.save()
            messages.success(request, f'메뉴 "{menu.name}"이(가) 성공적으로 수정되었습니다.')
            return redirect('menu:menu_list', store_id=store_id)
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
    
    # 파일 크기 체크 (5MB 제한)
    if image_file.size > 5 * 1024 * 1024:
        return JsonResponse({'success': False, 'error': '이미지 파일 크기는 5MB를 초과할 수 없습니다.'})
    
    # 파일 형식 체크
    allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    if image_file.content_type not in allowed_types:
        return JsonResponse({'success': False, 'error': '지원하지 않는 이미지 형식입니다.'})
    
    try:
        # 기존 이미지 삭제
        if menu.image:
            old_image_path = menu.image.path
            if os.path.exists(old_image_path):
                os.remove(old_image_path)
        
        # 새 이미지 저장
        menu.image = image_file
        menu.save()
        
        return JsonResponse({
            'success': True,
            'image_url': menu.image.url if menu.image else None
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