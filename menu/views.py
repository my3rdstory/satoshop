from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import PermissionDenied
from django.db import transaction, IntegrityError
from django.db import models
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
                
                # 가격 처리 - 가격 표시 방식에 따라 적절한 필드에 저장
                price_display = request.POST.get('price_display', 'sats')
                menu.price_display = price_display
                
                if price_display == 'krw':
                    # 원화 비율 연동: 원화 값을 저장하고 사토시는 JavaScript에서 계산된 값 사용
                    menu.price_krw = int(request.POST.get('price', 0))
                    # 환율 변환된 사토시 가격은 public_price 프로퍼티에서 계산
                    
                    if request.POST.get('is_discounted'):
                        discounted_price = request.POST.get('discounted_price')
                        if discounted_price:
                            menu.discounted_price_krw = int(discounted_price)
                else:
                    # 사토시 고정: 사토시 값을 저장
                    menu.price = int(request.POST.get('price', 0))
                    
                    if request.POST.get('is_discounted'):
                        discounted_price = request.POST.get('discounted_price')
                        if discounted_price:
                            menu.discounted_price = int(discounted_price)
                
                menu.save()
                form.save_m2m()  # ManyToMany 관계 저장
                
                # 카테고리 처리 (새로운 옵션 형식)
                categories = request.POST.getlist('categories')
                if categories:
                    menu.categories.set(categories)
                
                # 옵션 처리 (새로운 형식)
                options_data = {}
                for key, value in request.POST.items():
                    if key.startswith('options[') and value.strip():
                        # options[0][name], options[0][choices][0][name], options[0][choices][0][price] 형식 파싱
                        parts = key.replace('options[', '').replace(']', '').split('[')
                        if len(parts) >= 2:
                            option_index = int(parts[0])
                            if option_index not in options_data:
                                options_data[option_index] = {'name': '', 'choices': {}}
                            
                            if parts[1] == 'name':
                                options_data[option_index]['name'] = value.strip()
                            elif parts[1] == 'choices' and len(parts) >= 4:
                                choice_index = int(parts[2])
                                if choice_index not in options_data[option_index]['choices']:
                                    options_data[option_index]['choices'][choice_index] = {}
                                
                                if parts[3] == 'name':
                                    options_data[option_index]['choices'][choice_index]['name'] = value.strip()
                                elif parts[3] == 'price':
                                    try:
                                        options_data[option_index]['choices'][choice_index]['price'] = float(value) if value else 0
                                    except ValueError:
                                        options_data[option_index]['choices'][choice_index]['price'] = 0

                # 옵션 생성
                for option_index, option_data in options_data.items():
                    if option_data['name'] and option_data['choices']:
                        option = MenuOption.objects.create(
                            menu=menu,
                            name=option_data['name'],
                            order=option_index
                        )
                        
                        # 옵션 선택지들을 values_list 형태로 변환
                        values_list = []
                        for choice_data in option_data['choices'].values():
                            if choice_data.get('name'):
                                choice_name = choice_data['name']
                                choice_price = choice_data.get('price', 0)
                                if choice_price > 0:
                                    values_list.append(f"{choice_name}(+{choice_price})")
                                else:
                                    values_list.append(choice_name)
                        
                        if values_list:
                            option.set_values_list(values_list)
                            option.save()
                
                # 기존 옵션 처리 (하위 호환성)
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
                                order=option_counter + 1000  # 새로운 형식과 구분하기 위해 큰 수 사용
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
                # 가격 처리 - 가격 표시 방식에 따라 적절한 필드에 저장
                price_display = menu.price_display  # 메뉴 수정에서는 가격 표시 방식 변경 불가
                
                if price_display == 'krw':
                    # 원화 비율 연동: 원화 값을 저장
                    menu.price_krw = int(request.POST.get('price', 0))
                    
                    if request.POST.get('is_discounted'):
                        discounted_price = request.POST.get('discounted_price')
                        if discounted_price:
                            menu.discounted_price_krw = int(discounted_price)
                        else:
                            menu.discounted_price_krw = None
                    else:
                        menu.discounted_price_krw = None
                else:
                    # 사토시 고정: 사토시 값을 저장
                    menu.price = int(request.POST.get('price', 0))
                    
                    if request.POST.get('is_discounted'):
                        discounted_price = request.POST.get('discounted_price')
                        if discounted_price:
                            menu.discounted_price = int(discounted_price)
                        else:
                            menu.discounted_price = None
                    else:
                        menu.discounted_price = None
                
                # 폼의 나머지 필드들 저장
                menu.name = request.POST.get('name', menu.name)
                menu.description = request.POST.get('description', menu.description)
                menu.is_discounted = bool(request.POST.get('is_discounted'))
                menu.save()
                
                # 카테고리 처리
                categories = request.POST.getlist('categories')
                if categories:
                    menu.categories.set(categories)
                else:
                    menu.categories.clear()
                
                # 기존 옵션 삭제
                menu.options.all().delete()
                
                # 옵션 처리 (새로운 형식)
                options_data = {}
                for key, value in request.POST.items():
                    if key.startswith('options[') and value.strip():
                        # options[0][name], options[0][choices][0][name], options[0][choices][0][price] 형식 파싱
                        parts = key.replace('options[', '').replace(']', '').split('[')
                        if len(parts) >= 2:
                            option_index = int(parts[0])
                            if option_index not in options_data:
                                options_data[option_index] = {'name': '', 'choices': {}}
                            
                            if parts[1] == 'name':
                                options_data[option_index]['name'] = value.strip()
                            elif parts[1] == 'choices' and len(parts) >= 4:
                                choice_index = int(parts[2])
                                if choice_index not in options_data[option_index]['choices']:
                                    options_data[option_index]['choices'][choice_index] = {}
                                
                                if parts[3] == 'name':
                                    options_data[option_index]['choices'][choice_index]['name'] = value.strip()
                                elif parts[3] == 'price':
                                    try:
                                        options_data[option_index]['choices'][choice_index]['price'] = float(value) if value else 0
                                    except ValueError:
                                        options_data[option_index]['choices'][choice_index]['price'] = 0

                # 옵션 생성
                for option_index, option_data in options_data.items():
                    if option_data['name'] and option_data['choices']:
                        option = MenuOption.objects.create(
                            menu=menu,
                            name=option_data['name'],
                            order=option_index
                        )
                        
                        # 옵션 선택지들을 values_list 형태로 변환
                        values_list = []
                        for choice_data in option_data['choices'].values():
                            if choice_data.get('name'):
                                choice_name = choice_data['name']
                                choice_price = choice_data.get('price', 0)
                                if choice_price > 0:
                                    values_list.append(f"{choice_name}(+{choice_price})")
                                else:
                                    values_list.append(choice_name)
                        
                        if values_list:
                            option.set_values_list(values_list)
                            option.save()
                
                # 기존 옵션 처리 (하위 호환성)
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
                                order=option_counter + 1000  # 새로운 형식과 구분하기 위해 큰 수 사용
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
    categories = MenuCategory.objects.filter(store=store).order_by('order', 'name')
    
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
    categories = MenuCategory.objects.filter(store=store).order_by('order', 'name')
    
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
        
        # 새 카테고리의 순서를 마지막으로 설정
        max_order = MenuCategory.objects.filter(store=store).aggregate(
            max_order=models.Max('order')
        )['max_order'] or 0
        
        category = MenuCategory.objects.create(
            store=store,
            name=name,
            order=max_order + 1
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
def category_reorder_api(request, store_id):
    """카테고리 순서 변경 API"""
    store = get_store_or_404(store_id, request.user)
    
    try:
        data = json.loads(request.body)
        category_orders = data.get('category_orders', [])
        
        if not category_orders:
            return JsonResponse({
                'success': False,
                'error': '카테고리 순서 데이터가 없습니다.'
            })
        
        # 각 카테고리의 순서 업데이트
        for item in category_orders:
            category_id = item.get('id')
            order = item.get('order')
            
            if category_id and order is not None:
                try:
                    category = MenuCategory.objects.get(id=category_id, store=store)
                    category.order = order
                    category.save(update_fields=['order'])
                except MenuCategory.DoesNotExist:
                    continue
        
        return JsonResponse({
            'success': True,
            'message': '카테고리 순서가 변경되었습니다.'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '잘못된 요청 형식입니다.'
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
