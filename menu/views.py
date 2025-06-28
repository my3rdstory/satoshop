from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import PermissionDenied
from django.db import transaction, IntegrityError
from stores.models import Store
from .models import Menu, MenuCategory, MenuOption
from .forms import MenuForm, MenuCategoryForm
import json

def get_store_or_404(store_id, user):
    """스토어 조회 및 권한 확인"""
    store = get_object_or_404(Store, store_id=store_id, owner=user, deleted_at__isnull=True)
    return store

@login_required
def menu_list(request, store_id):
    """메뉴 목록 페이지"""
    store = get_store_or_404(store_id, request.user)
    menus = Menu.objects.filter(store=store).prefetch_related('categories')
    
    context = {
        'store': store,
        'menus': menus,
        'is_public_view': False,
    }
    return render(request, 'menu/menu_list.html', context)

@login_required
def add_menu(request, store_id):
    """메뉴 추가 페이지"""
    store = get_store_or_404(store_id, request.user)
    
    if request.method == 'POST':
        form = MenuForm(request.POST, request.FILES, store=store)
        if form.is_valid():
            with transaction.atomic():
                menu = form.save(commit=False)
                menu.store = store
                menu.save()
                form.save_m2m()  # ManyToMany 관계 저장
                

                
                # 옵션 처리
                option_counter = 1
                while f'option_{option_counter}_name' in request.POST:
                    option_name = request.POST.get(f'option_{option_counter}_name')
                    option_values = request.POST.get(f'option_{option_counter}_values')
                    
                    if option_name and option_values:
                        values_list = [v.strip() for v in option_values.split(',') if v.strip()]
                        if values_list:
                            option = MenuOption.objects.create(
                                menu=menu,
                                name=option_name,
                                order=option_counter
                            )
                            option.set_values_list(values_list)
                            option.save()
                    
                    option_counter += 1
                
                messages.success(request, f'"{menu.name}" 메뉴가 성공적으로 등록되었습니다.')
                return redirect('menu:menu_list', store_id=store.store_id)
    else:
        form = MenuForm(store=store)
    
    context = {
        'store': store,
        'form': form,
    }
    return render(request, 'menu/add_menu.html', context)

@login_required
def edit_menu(request, store_id, menu_id):
    """메뉴 수정 페이지"""
    store = get_store_or_404(store_id, request.user)
    menu = get_object_or_404(Menu, id=menu_id, store=store)
    
    if request.method == 'POST':
        form = MenuForm(request.POST, request.FILES, instance=menu, store=store)
        if form.is_valid():
            with transaction.atomic():
                menu = form.save()
                

                
                # 기존 옵션 삭제
                menu.options.all().delete()
                
                # 새 옵션 추가
                option_counter = 1
                while f'option_{option_counter}_name' in request.POST:
                    option_name = request.POST.get(f'option_{option_counter}_name')
                    option_values = request.POST.get(f'option_{option_counter}_values')
                    
                    if option_name and option_values:
                        values_list = [v.strip() for v in option_values.split(',') if v.strip()]
                        if values_list:
                            option = MenuOption.objects.create(
                                menu=menu,
                                name=option_name,
                                order=option_counter
                            )
                            option.set_values_list(values_list)
                            option.save()
                    
                    option_counter += 1
                
                messages.success(request, f'"{menu.name}" 메뉴가 성공적으로 수정되었습니다.')
                return redirect('menu:menu_list', store_id=store.store_id)
    else:
        form = MenuForm(instance=menu, store=store)
    
    context = {
        'store': store,
        'menu': menu,
        'form': form,
    }
    return render(request, 'menu/edit_menu.html', context)

@login_required
def menu_detail(request, store_id, menu_id):
    """메뉴 상세 페이지"""
    store = get_store_or_404(store_id, request.user)
    menu = get_object_or_404(Menu, id=menu_id, store=store)
    
    context = {
        'store': store,
        'menu': menu,
    }
    return render(request, 'menu/menu_detail.html', context)

@login_required
def category_manage(request, store_id):
    """카테고리 관리 페이지"""
    store = get_store_or_404(store_id, request.user)
    categories = MenuCategory.objects.filter(store=store).order_by('name')
    
    context = {
        'store': store,
        'categories': categories,
    }
    return render(request, 'menu/category_manage.html', context)

# === 카테고리 관리 API ===

@login_required
@require_http_methods(["GET"])
def category_list_api(request, store_id):
    """카테고리 목록 API"""
    store = get_store_or_404(store_id, request.user)
    categories = MenuCategory.objects.filter(store=store).order_by('name')
    
    data = {
        'success': True,
        'categories': [
            {
                'id': str(category.id),
                'name': category.name,
                'created_at': category.created_at.isoformat()
            }
            for category in categories
        ]
    }
    return JsonResponse(data)

@login_required
@require_http_methods(["POST"])
def category_create_api(request, store_id):
    """카테고리 생성 API"""
    store = get_store_or_404(store_id, request.user)
    
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        
        if not name:
            return JsonResponse({
                'success': False,
                'error': '카테고리명을 입력해주세요.'
            })
        
        # 중복 체크
        if MenuCategory.objects.filter(store=store, name=name).exists():
            return JsonResponse({
                'success': False,
                'error': '이미 존재하는 카테고리명입니다.'
            })
        
        category = MenuCategory.objects.create(
            store=store,
            name=name
        )
        
        return JsonResponse({
            'success': True,
            'category': {
                'id': str(category.id),
                'name': category.name,
                'created_at': category.created_at.isoformat()
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '잘못된 요청 형식입니다.'
        })
    except IntegrityError:
        return JsonResponse({
            'success': False,
            'error': '데이터베이스 제약조건 위반: 이미 존재하는 카테고리명입니다.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

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
            return JsonResponse({
                'success': False,
                'error': '카테고리명을 입력해주세요.'
            })
        
        # 중복 체크 (자기 자신 제외)
        if MenuCategory.objects.filter(store=store, name=name).exclude(id=category.id).exists():
            return JsonResponse({
                'success': False,
                'error': '이미 존재하는 카테고리명입니다.'
            })
        
        category.name = name
        category.save()
        
        return JsonResponse({
            'success': True,
            'category': {
                'id': str(category.id),
                'name': category.name,
                'updated_at': category.updated_at.isoformat()
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '잘못된 요청 형식입니다.'
        })
    except IntegrityError:
        return JsonResponse({
            'success': False,
            'error': '데이터베이스 제약조건 위반: 이미 존재하는 카테고리명입니다.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
@require_http_methods(["DELETE"])
def category_delete_api(request, store_id, category_id):
    """카테고리 삭제 API"""
    store = get_store_or_404(store_id, request.user)
    category = get_object_or_404(MenuCategory, id=category_id, store=store)
    
    try:
        category_name = category.name
        category.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'"{category_name}" 카테고리가 삭제되었습니다.'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
@require_http_methods(["POST"])
def toggle_temporary_out_of_stock(request, store_id, menu_id):
    """일시품절 상태 토글 API"""
    store = get_store_or_404(store_id, request.user)
    menu = get_object_or_404(Menu, id=menu_id, store=store)
    
    try:
        menu.is_temporarily_out_of_stock = not menu.is_temporarily_out_of_stock
        menu.save()
        
        status = "일시품절" if menu.is_temporarily_out_of_stock else "주문 가능"
        action = "설정" if menu.is_temporarily_out_of_stock else "해제"
        
        return JsonResponse({
            'success': True,
            'message': f'"{menu.name}" 메뉴의 일시품절이 {action}되었습니다.',
            'is_temporarily_out_of_stock': menu.is_temporarily_out_of_stock,
            'status': status
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
