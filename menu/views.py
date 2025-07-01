from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import PermissionDenied
from django.db import transaction, IntegrityError
from django.db import models
from django.utils import timezone
from django.core.paginator import Paginator
from stores.models import Store
from .models import Menu, MenuCategory, MenuOption, MenuImage, MenuOrder, MenuOrderItem
from .forms import MenuForm, MenuCategoryForm
import json
import logging

logger = logging.getLogger(__name__)

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
                
                # 카테고리 처리
                print(f"DEBUG: 전체 POST 데이터: {dict(request.POST)}")  # 디버깅용
                categories = request.POST.getlist('categories')
                print(f"DEBUG: 전송된 카테고리 데이터: {categories}")  # 디버깅용
                if categories:
                    # 카테고리 ID들이 해당 스토어의 카테고리인지 확인
                    valid_categories = MenuCategory.objects.filter(
                        id__in=categories, 
                        store=store
                    )
                    menu.categories.set(valid_categories)
                    print(f"DEBUG: 메뉴에 설정된 카테고리: {list(menu.categories.all())}")  # 디버깅용
                else:
                    menu.categories.clear()
                    print(f"DEBUG: 카테고리 모두 제거됨")  # 디버깅용
                
                # 이미지 처리
                images = request.FILES.getlist('images')
                if images:
                    # 메뉴당 1장만 허용
                    image_file = images[0]
                    try:
                        from storage.utils import upload_menu_image
                        result = upload_menu_image(image_file, menu, request.user)
                        
                        if result['success']:
                            logger.info(f"메뉴 이미지 업로드 성공: {image_file.name}")
                        else:
                            logger.warning(f"메뉴 이미지 업로드 실패: {image_file.name}, 오류: {result['error']}")
                            messages.warning(request, f'이미지 업로드 실패: {result["error"]}')
                    except Exception as e:
                        logger.error(f"메뉴 이미지 처리 오류: {e}", exc_info=True)
                        messages.warning(request, '이미지 업로드 중 오류가 발생했습니다.')
                
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
                print(f"DEBUG (edit_menu): 전체 POST 데이터: {dict(request.POST)}")  # 디버깅용
                categories = request.POST.getlist('categories')
                print(f"DEBUG (edit_menu): 전송된 카테고리 데이터: {categories}")  # 디버깅용
                if categories:
                    # 카테고리 ID들이 해당 스토어의 카테고리인지 확인
                    valid_categories = MenuCategory.objects.filter(
                        id__in=categories, 
                        store=store
                    )
                    print(f"DEBUG (edit_menu): 유효한 카테고리: {list(valid_categories)}")  # 디버깅용
                    menu.categories.set(valid_categories)
                    print(f"DEBUG (edit_menu): 메뉴에 설정된 카테고리: {list(menu.categories.all())}")  # 디버깅용
                else:
                    menu.categories.clear()
                    print(f"DEBUG (edit_menu): 카테고리 모두 제거됨")  # 디버깅용
                
                # 기존 이미지 삭제 처리
                for key, value in request.POST.items():
                    if key.startswith('keep_image_') and value == 'false':
                        image_id = key.replace('keep_image_', '')
                        try:
                            image = MenuImage.objects.get(id=image_id, menu=menu)
                            # S3에서 파일 삭제
                            from storage.utils import delete_file_from_s3
                            try:
                                delete_file_from_s3(image.file_path)
                            except Exception as e:
                                logger.warning(f"S3 파일 삭제 실패: {e}")
                            # DB에서 삭제
                            image.delete()
                            logger.info(f"메뉴 이미지 삭제: {image.original_name}")
                        except MenuImage.DoesNotExist:
                            pass
                
                # 새 이미지 처리
                images = request.FILES.getlist('images')
                if images:
                    # 기존 이미지가 있으면 삭제 (메뉴당 1장만 허용)
                    existing_images = menu.images.all()
                    if existing_images.exists():
                        for existing_image in existing_images:
                            # S3에서 파일 삭제
                            try:
                                from storage.utils import delete_file_from_s3
                                delete_file_from_s3(existing_image.file_path)
                            except Exception as e:
                                logger.warning(f"S3 파일 삭제 실패: {e}")
                            # DB에서 삭제
                            existing_image.delete()
                    
                    # 새 이미지 업로드 (첫 번째 이미지만)
                    image_file = images[0]
                    try:
                        from storage.utils import upload_menu_image
                        result = upload_menu_image(image_file, menu, request.user)
                        
                        if result['success']:
                            logger.info(f"메뉴 이미지 업로드 성공: {image_file.name}")
                        else:
                            logger.warning(f"메뉴 이미지 업로드 실패: {image_file.name}, 오류: {result['error']}")
                            messages.warning(request, f'이미지 업로드 실패: {result["error"]}')
                    except Exception as e:
                        logger.error(f"메뉴 이미지 처리 오류: {e}", exc_info=True)
                        messages.warning(request, '이미지 업로드 중 오류가 발생했습니다.')
                
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
@require_POST
def upload_menu_image(request, store_id, menu_id):
    """메뉴 이미지 업로드 (AJAX)"""
    try:
        store = get_store_or_404(store_id, request.user)
        menu = get_object_or_404(Menu, id=menu_id, store=store)
        
        if 'image' not in request.FILES:
            return JsonResponse({
                'success': False,
                'error': '이미지 파일이 필요합니다.'
            })
        
        image_file = request.FILES['image']
        
        # 파일 크기 제한 (10MB)
        if image_file.size > 10 * 1024 * 1024:
            return JsonResponse({
                'success': False,
                'error': '파일 크기는 10MB를 초과할 수 없습니다.'
            })
        
        # 이미지 파일 검증
        if not image_file.content_type.startswith('image/'):
            return JsonResponse({
                'success': False,
                'error': '이미지 파일만 업로드할 수 있습니다.'
            })
        
        # 메뉴당 1장만 허용 - 기존 이미지가 있으면 삭제
        existing_images = menu.images.all()
        if existing_images.exists():
            for existing_image in existing_images:
                # S3에서 파일 삭제
                try:
                    from storage.utils import delete_file_from_s3
                    delete_file_from_s3(existing_image.file_path)
                except Exception as e:
                    logger.warning(f"S3 파일 삭제 실패: {e}")
                # DB에서 삭제
                existing_image.delete()
        
        # 이미지 업로드
        from storage.utils import upload_menu_image
        result = upload_menu_image(image_file, menu, request.user)
        
        if result['success']:
            menu_image = result['menu_image']
            return JsonResponse({
                'success': True,
                'image': {
                    'id': menu_image.id,
                    'original_name': menu_image.original_name,
                    'file_url': menu_image.file_url,
                    'file_size': menu_image.file_size,
                    'width': menu_image.width,
                    'height': menu_image.height,
                    'order': menu_image.order,
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result['error']
            })
            
    except Exception as e:
        logger.error(f"메뉴 이미지 업로드 오류: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': '이미지 업로드 중 오류가 발생했습니다.'
        })

def menu_detail(request, store_id, menu_id):
    """메뉴 상세 페이지 (공개, 비회원 접근 가능)"""
    # 스토어 조회 (비회원도 접근 가능하므로 소유자 확인 안함)
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True, is_active=True)
    
    # 활성화된 메뉴만 조회
    menu = get_object_or_404(Menu, id=menu_id, store=store, is_active=True)
    
    # 카테고리 목록 조회 (사이드바 표시용)
    categories = MenuCategory.objects.filter(store=store).order_by('order', 'name')
    
    context = {
        'store': store,
        'menu': menu,
        'categories': categories,
        'is_public_view': True,
    }
    return render(request, 'menu/menu_detail.html', context)

def menu_detail_ajax(request, store_id, menu_id):
    """메뉴 상세 페이지 AJAX 버전 (SPA용)"""
    # 스토어 조회 (비회원도 접근 가능하므로 소유자 확인 안함)
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True, is_active=True)
    
    # 활성화된 메뉴만 조회
    menu = get_object_or_404(Menu, id=menu_id, store=store, is_active=True)
    
    # 카테고리 목록 조회 (사이드바 표시용)
    categories = MenuCategory.objects.filter(store=store).order_by('order', 'name')
    
    context = {
        'store': store,
        'menu': menu,
        'categories': categories,
        'is_public_view': True,
        'is_ajax': True,  # AJAX 요청임을 표시
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
                'id': category.id,  # 숫자로 반환
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
    """메뉴 일시품절 상태 토글"""
    try:
        store = get_store_or_404(store_id, request.user)
        menu = get_object_or_404(Menu, id=menu_id, store=store)
        
        # JSON 데이터가 있으면 사용, 없으면 현재 상태를 토글
        try:
            data = json.loads(request.body)
            is_temporarily_out_of_stock = data.get('is_temporarily_out_of_stock', False)
        except (json.JSONDecodeError, ValueError):
            # JSON 파싱 실패 시 현재 상태를 토글
            is_temporarily_out_of_stock = not menu.is_temporarily_out_of_stock
        
        menu.is_temporarily_out_of_stock = is_temporarily_out_of_stock
        menu.save()
        
        status_text = "일시품절" if is_temporarily_out_of_stock else "일시품절 해제"
        
        return JsonResponse({
            'success': True,
            'is_temporarily_out_of_stock': menu.is_temporarily_out_of_stock,
            'message': f'메뉴가 {status_text}되었습니다.'
        })
        
    except Exception as e:
        logger.error(f"일시품절 상태 변경 오류: {e}")
        return JsonResponse({'success': False, 'error': '서버 오류가 발생했습니다.'}, status=500)

@login_required
@require_http_methods(["POST"])
def toggle_menu_active(request, store_id, menu_id):
    """메뉴 활성화 상태 토글"""
    try:
        store = get_store_or_404(store_id, request.user)
        menu = get_object_or_404(Menu, id=menu_id, store=store)
        
        data = json.loads(request.body)
        is_active = data.get('is_active', False)
        
        menu.is_active = is_active
        menu.save()
        
        return JsonResponse({
            'success': True,
            'is_active': menu.is_active,
            'message': '메뉴 활성화 상태가 변경되었습니다.'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '잘못된 JSON 데이터입니다.'}, status=400)
    except Exception as e:
        logger.error(f"메뉴 활성화 상태 변경 오류: {e}")
        return JsonResponse({'success': False, 'error': '서버 오류가 발생했습니다.'}, status=500)

# === 기기별 메뉴판 뷰 함수들 ===

def menu_board_desktop(request, store_id):
    """데스크톱 메뉴판 화면 (공개, 비회원 접근 가능)"""
    # 스토어 조회 (비회원도 접근 가능하므로 소유자 확인 안함)
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True, is_active=True)
    
    # 활성화된 메뉴만 조회
    menus = Menu.objects.filter(
        store=store, 
        is_active=True
    ).prefetch_related('categories', 'images')
    
    # 카테고리 조회 (순서대로)
    categories = MenuCategory.objects.filter(store=store).order_by('order', 'name')
    
    context = {
        'store': store,
        'menus': menus,
        'categories': categories,
        'is_public_view': True,
        'is_menu_board': True,
        'device_type': 'desktop',
    }
    
    return render(request, 'menu/menu_board.html', context)

def menu_board_mobile(request, store_id):
    """모바일 메뉴판 화면 (공개, 비회원 접근 가능)"""
    # 스토어 조회 (비회원도 접근 가능하므로 소유자 확인 안함)
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True, is_active=True)
    
    # 활성화된 메뉴만 조회
    menus = Menu.objects.filter(
        store=store, 
        is_active=True
    ).prefetch_related('categories', 'images')
    
    # 카테고리 조회 (순서대로)
    categories = MenuCategory.objects.filter(store=store).order_by('order', 'name')
    
    context = {
        'store': store,
        'menus': menus,
        'categories': categories,
        'is_public_view': True,
        'is_menu_board': True,
        'device_type': 'mobile',
    }
    
    return render(request, 'menu/menu_board_mobile.html', context)

def menu_board_auto_redirect(request, store_id):
    """기기에 따라 자동으로 적절한 메뉴판으로 리다이렉트 (하위 호환성)"""
    def is_mobile_device(request):
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        mobile_keywords = ['mobile', 'android', 'iphone', 'ipad', 'ipod', 'blackberry', 'webos']
        return any(keyword in user_agent for keyword in mobile_keywords)
    
    if is_mobile_device(request):
        return redirect('menu:menu_board_mobile', store_id=store_id)
    else:
        return redirect('menu:menu_board_desktop', store_id=store_id)

# === 기존 함수 (하위 호환성 유지) ===
def menu_board(request, store_id):
    """기존 메뉴판 화면 - 자동 리다이렉트로 변경"""
    return menu_board_auto_redirect(request, store_id)

def menu_cart(request, store_id):
    """장바구니 화면 (공개, 비회원 접근 가능)"""
    # 스토어 조회 (비회원도 접근 가능하므로 소유자 확인 안함)
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True, is_active=True)
    
    context = {
        'store': store,
        'is_public_view': True,
        'is_cart_view': True,  # 장바구니 화면임을 표시
        'view_type': 'full_page',  # 독립 페이지로 표시
    }
    return render(request, 'menu/menu_cart.html', context)

@login_required
def manage_menu(request, store_id, menu_id):
    """메뉴 관리 페이지"""
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
    
    if request.method == 'POST':
        menu_name = menu.name
        
        try:
            with transaction.atomic():
                # 관련 이미지 파일들 삭제
                for image in menu.images.all():
                    if image.file_path:
                        try:
                            from storage.utils import delete_file_from_s3
                            delete_file_from_s3(image.file_path)
                        except Exception as e:
                            logger.warning(f"S3 파일 삭제 실패: {e}")
                
                # 메뉴 완전 삭제 (관련 데이터도 CASCADE로 함께 삭제됨)
                menu.delete()
                
                messages.success(request, f'"{menu_name}" 메뉴가 완전히 삭제되었습니다.')
                
        except Exception as e:
            logger.error(f"메뉴 삭제 오류: {e}", exc_info=True)
            messages.error(request, '메뉴 삭제 중 오류가 발생했습니다.')
    
    return redirect('menu:menu_list', store_id=store_id)

@csrf_exempt
@require_POST
def create_cart_invoice(request, store_id):
    """장바구니 결제용 인보이스 생성"""
    try:
        # 스토어 조회 (비회원도 접근 가능)
        store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True, is_active=True)
        
        # 요청 본문 파싱
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            return JsonResponse({'success': False, 'error': f'JSON 파싱 오류: {str(e)}'}, status=400)
        
        cart_items = data.get('cart_items', [])
        if not cart_items:
            return JsonResponse({'success': False, 'error': '장바구니가 비어있습니다.'}, status=400)
        
        # 디버깅을 위한 로그
        logger.debug(f"장바구니 결제 요청 - 스토어: {store.store_name}, 아이템 수: {len(cart_items)}")
        for i, item in enumerate(cart_items):
            logger.debug(f"아이템 {i+1}: {item}")
        
        # 메뉴 데이터 검증 및 총 금액 계산
        total_amount = 0
        memo_items = []
        validated_items = []
        
        for item in cart_items:
            try:
                # 메뉴 ID 검증 및 정리
                menu_id_raw = item.get('id')
                if not menu_id_raw:
                    return JsonResponse({'success': False, 'error': '메뉴 ID가 없습니다.'}, status=400)
                
                # 메뉴 ID에서 언더스코어와 그 뒤의 문자들 제거 (옵션 식별자 제거)
                if isinstance(menu_id_raw, str) and '_' in menu_id_raw:
                    menu_id = menu_id_raw.split('_')[0]
                else:
                    menu_id = menu_id_raw
                
                try:
                    menu_id = int(menu_id)
                except (ValueError, TypeError):
                    logger.error(f"메뉴 ID 파싱 실패: menu_id_raw={menu_id_raw}, menu_id={menu_id}")
                    return JsonResponse({'success': False, 'error': f'올바르지 않은 메뉴 ID입니다: {menu_id_raw}'}, status=400)
                
                menu = Menu.objects.get(id=menu_id, store=store, is_active=True)
                
                # 수량 검증 및 파싱
                quantity_raw = item.get('quantity', 1)
                if isinstance(quantity_raw, str):
                    try:
                        quantity = int(quantity_raw)
                    except ValueError:
                        logger.error(f"수량 파싱 실패: quantity_raw={quantity_raw}, type={type(quantity_raw)}")
                        return JsonResponse({'success': False, 'error': f'올바르지 않은 수량 형식입니다: {quantity_raw}'}, status=400)
                elif isinstance(quantity_raw, (int, float)):
                    quantity = int(quantity_raw)
                else:
                    logger.error(f"수량 타입 오류: quantity_raw={quantity_raw}, type={type(quantity_raw)}")
                    return JsonResponse({'success': False, 'error': f'올바르지 않은 수량 타입입니다: {type(quantity_raw)}'}, status=400)
                
                if quantity <= 0:
                    return JsonResponse({'success': False, 'error': '수량은 1개 이상이어야 합니다.'}, status=400)
                
                # 메뉴 가격 계산 (현재 가격 기준)
                menu_price = menu.public_discounted_price if menu.is_discounted else menu.public_price
                options_price = 0
                
                # 옵션 가격 계산 (현재는 단순히 전달받은 값 사용)
                item_total_price = item.get('totalPrice', menu_price)
                if isinstance(item_total_price, str):
                    try:
                        item_total_price = int(float(item_total_price))
                    except ValueError:
                        item_total_price = menu_price
                
                # 검증된 아이템 정보 저장
                validated_items.append({
                    'menu': menu,
                    'menu_name': menu.name,
                    'menu_price': menu_price,
                    'quantity': quantity,
                    'selected_options': item.get('options', {}),
                    'options_price': options_price,
                    'total_price': item_total_price * quantity
                })
                
                total_amount += item_total_price * quantity
                memo_items.append(f"{menu.name} x{quantity}")
                
                logger.debug(f"아이템 검증 완료: {menu.name}, 수량: {quantity}, 가격: {item_total_price}")
                
            except Menu.DoesNotExist:
                return JsonResponse({'success': False, 'error': f'메뉴를 찾을 수 없습니다: {item.get("name", "알 수 없음")}'}, status=400)
            except Exception as e:
                logger.error(f"아이템 처리 중 오류: {str(e)}, 아이템: {item}")
                return JsonResponse({'success': False, 'error': f'아이템 처리 중 오류가 발생했습니다: {str(e)}'}, status=400)
        
        if total_amount <= 0:
            return JsonResponse({'success': False, 'error': '결제 금액이 올바르지 않습니다.'}, status=400)
        
        # 메모 생성
        memo = ', '.join(memo_items[:3])
        if len(memo_items) > 3:
            memo += f" 외 {len(memo_items) - 3}개"
        
        # BlinkAPIService 초기화
        try:
            from ln_payment.blink_service import get_blink_service_for_store
            blink_service = get_blink_service_for_store(store)
        except Exception as e:
            logger.error(f"BlinkAPIService 초기화 실패: {str(e)}")
            return JsonResponse({'success': False, 'error': f'결제 서비스 초기화 실패: {str(e)}'}, status=500)
        
        # 인보이스 생성
        result = blink_service.create_invoice(
            amount_sats=int(total_amount),
            memo=memo,
            expires_in_minutes=15  # 15분 유효
        )
        
        if not result['success']:
            return JsonResponse({
                'success': False,
                'error': result['error']
            }, status=500)
        
        # 메뉴 주문 생성 (결제 대기 상태)
        with transaction.atomic():
            menu_order = MenuOrder.objects.create(
                store=store,
                status='payment_pending',
                total_amount=total_amount,
                payment_hash=result['payment_hash'],
                customer_info={
                    'user_id': request.user.id if request.user.is_authenticated else None,
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'ip_address': request.META.get('REMOTE_ADDR', ''),
                    'created_via': 'menu_board'
                }
            )
            
            # 메뉴 주문 아이템들 생성
            for item_data in validated_items:
                MenuOrderItem.objects.create(
                    order=menu_order,
                    menu=item_data['menu'],
                    menu_name=item_data['menu_name'],
                    menu_price=item_data['menu_price'],
                    quantity=item_data['quantity'],
                    selected_options=item_data['selected_options'],
                    options_price=item_data['options_price']
                )
        
        # 응답 데이터 준비
        response_data = {
            'success': True,
            'payment_hash': result['payment_hash'],
            'invoice': result['invoice'],
            'amount': total_amount,
            'memo': memo,
            'order_number': menu_order.order_number,
            'expires_at': result['expires_at'].isoformat() if result.get('expires_at') else None,
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"장바구니 인보이스 생성 오류: {str(e)}")
        return JsonResponse({'success': False, 'error': f'인보이스 생성 중 오류가 발생했습니다: {str(e)}'}, status=500)


@csrf_exempt
@require_POST
def check_cart_payment(request, store_id):
    """장바구니 결제 상태 확인"""
    try:
        # 스토어 조회 (비회원도 접근 가능)
        store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True, is_active=True)
        
        # 요청 본문 파싱
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            return JsonResponse({'success': False, 'error': f'JSON 파싱 오류: {str(e)}'}, status=400)
        
        payment_hash = data.get('payment_hash')
        if not payment_hash:
            return JsonResponse({'success': False, 'error': 'payment_hash가 필요합니다.'}, status=400)
        
        # 메뉴 주문 조회
        try:
            menu_order = MenuOrder.objects.get(payment_hash=payment_hash, store=store)
        except MenuOrder.DoesNotExist:
            return JsonResponse({'success': False, 'error': '주문을 찾을 수 없습니다.'}, status=404)
        
        # BlinkAPIService 초기화
        try:
            from ln_payment.blink_service import get_blink_service_for_store
            blink_service = get_blink_service_for_store(store)
        except Exception as e:
            logger.error(f"BlinkAPIService 초기화 실패: {str(e)}")
            return JsonResponse({'success': False, 'error': f'결제 서비스 초기화 실패: {str(e)}'}, status=500)
        
        # 결제 상태 확인
        result = blink_service.check_invoice_status(payment_hash)
        
        if not result['success']:
            return JsonResponse({
                'success': False,
                'error': result['error']
            }, status=500)
        
        # 주문 상태 업데이트
        with transaction.atomic():
            if result['status'] == 'paid' and menu_order.status != 'paid':
                menu_order.status = 'paid'
                menu_order.paid_at = timezone.now()
                menu_order.save()
                
                logger.info(f"메뉴 주문 결제 완료: {menu_order.order_number}, 금액: {menu_order.total_amount} sats")
                
            elif result['status'] == 'expired' and menu_order.status not in ['paid', 'expired']:
                menu_order.status = 'expired'
                menu_order.save()
        
        response_data = {
            'success': True,
            'status': result['status'],  # 'pending', 'paid', 'expired'
            'payment_hash': payment_hash,
            'order_number': menu_order.order_number,
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"장바구니 결제 상태 확인 오류: {str(e)}")
        return JsonResponse({'success': False, 'error': f'결제 상태 확인 중 오류가 발생했습니다: {str(e)}'}, status=500)


@login_required
def menu_orders(request, store_id):
    """메뉴 판매 현황 페이지"""
    store = get_store_or_404(store_id, request.user)
    
    # 메뉴별 판매 통계 계산
    menus_with_orders = []
    menus = Menu.objects.filter(store=store).prefetch_related('images')
    
    for menu in menus:
        # 결제 완료된 주문 아이템만 집계
        paid_items = MenuOrderItem.objects.filter(
            menu=menu,
            order__status='paid'
        )
        
        total_orders = paid_items.values('order').distinct().count()
        total_quantity = paid_items.aggregate(
            total=models.Sum('quantity')
        )['total'] or 0
        total_revenue = paid_items.aggregate(
            total=models.Sum(models.F('menu_price') + models.F('options_price'))
        )['total'] or 0
        
        # 통계가 있는 메뉴만 추가하거나 모든 메뉴 표시
        menu.total_orders = total_orders
        menu.total_quantity = total_quantity
        menu.total_revenue = total_revenue
        menus_with_orders.append(menu)
    
    # 매출 순으로 정렬
    menus_with_orders.sort(key=lambda x: x.total_revenue, reverse=True)
    
    # 전체 통계
    total_menu_orders = MenuOrder.objects.filter(store=store, status='paid').count()
    total_menu_revenue = MenuOrder.objects.filter(store=store, status='paid').aggregate(
        total=models.Sum('total_amount')
    )['total'] or 0
    total_menu_items = MenuOrderItem.objects.filter(
        order__store=store, order__status='paid'
    ).aggregate(
        total=models.Sum('quantity')
    )['total'] or 0
    
    context = {
        'store': store,
        'menus_with_orders': menus_with_orders,
        'total_menu_orders': total_menu_orders,
        'total_menu_revenue': total_menu_revenue,
        'total_menu_items': total_menu_items,
    }
    
    return render(request, 'menu/menu_orders.html', context)


@login_required
def menu_orders_detail(request, store_id, menu_id):
    """메뉴별 판매 현황 상세 페이지"""
    store = get_store_or_404(store_id, request.user)
    menu = get_object_or_404(Menu, id=menu_id, store=store)
    
    # 해당 메뉴의 주문 아이템들 (결제 완료된 것만)
    order_items = MenuOrderItem.objects.filter(
        menu=menu,
        order__status='paid'
    ).select_related('order').order_by('-order__created_at')
    
    # 페이지네이션
    paginator = Paginator(order_items, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 통계 계산
    total_orders = order_items.values('order').distinct().count()
    total_quantity = order_items.aggregate(
        total=models.Sum('quantity')
    )['total'] or 0
    total_revenue = order_items.aggregate(
        total=models.Sum(models.F('menu_price') + models.F('options_price'))
    )['total'] or 0
    
    context = {
        'store': store,
        'menu': menu,
        'page_obj': page_obj,
        'total_orders': total_orders,
        'total_quantity': total_quantity,
        'total_revenue': total_revenue,
    }
    
    return render(request, 'menu/menu_orders_detail.html', context)

# === 기기별 메뉴 상세 뷰 ===

def menu_detail_desktop(request, store_id, menu_id):
    """데스크톱 메뉴 상세 페이지 (공개, 비회원 접근 가능)"""
    # 스토어 조회 (비회원도 접근 가능하므로 소유자 확인 안함)
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True, is_active=True)
    
    # 활성화된 메뉴만 조회
    menu = get_object_or_404(Menu, id=menu_id, store=store, is_active=True)
    
    # 카테고리 목록 조회 (사이드바 표시용)
    categories = MenuCategory.objects.filter(store=store).order_by('order', 'name')
    
    context = {
        'store': store,
        'menu': menu,
        'categories': categories,
        'is_public_view': True,
        'device_type': 'desktop',
    }
    return render(request, 'menu/menu_detail.html', context)

def menu_detail_mobile(request, store_id, menu_id):
    """모바일 메뉴 상세 페이지 (공개, 비회원 접근 가능)"""
    # 스토어 조회 (비회원도 접근 가능하므로 소유자 확인 안함)
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True, is_active=True)
    
    # 활성화된 메뉴만 조회
    menu = get_object_or_404(Menu, id=menu_id, store=store, is_active=True)
    
    # 카테고리 목록 조회 (사이드바 표시용)
    categories = MenuCategory.objects.filter(store=store).order_by('order', 'name')
    
    context = {
        'store': store,
        'menu': menu,
        'categories': categories,
        'is_public_view': True,
        'device_type': 'mobile',
    }
    return render(request, 'menu/menu_detail_mobile.html', context)

def menu_detail_ajax_desktop(request, store_id, menu_id):
    """데스크톱 메뉴 상세 페이지 AJAX 버전 (SPA용)"""
    # 스토어 조회 (비회원도 접근 가능하므로 소유자 확인 안함)
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True, is_active=True)
    
    # 활성화된 메뉴만 조회
    menu = get_object_or_404(Menu, id=menu_id, store=store, is_active=True)
    
    # 카테고리 목록 조회 (사이드바 표시용)
    categories = MenuCategory.objects.filter(store=store).order_by('order', 'name')
    
    context = {
        'store': store,
        'menu': menu,
        'categories': categories,
        'is_public_view': True,
        'is_ajax': True,  # AJAX 요청임을 표시
        'device_type': 'desktop',
    }
    return render(request, 'menu/menu_detail.html', context)

def menu_detail_ajax_mobile(request, store_id, menu_id):
    """모바일 메뉴 상세 페이지 AJAX 버전 (SPA용)"""
    # 스토어 조회 (비회원도 접근 가능하므로 소유자 확인 안함)
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True, is_active=True)
    
    # 활성화된 메뉴만 조회
    menu = get_object_or_404(Menu, id=menu_id, store=store, is_active=True)
    
    # 카테고리 목록 조회 (사이드바 표시용)
    categories = MenuCategory.objects.filter(store=store).order_by('order', 'name')
    
    context = {
        'store': store,
        'menu': menu,
        'categories': categories,
        'is_public_view': True,
        'is_ajax': True,  # AJAX 요청임을 표시
        'device_type': 'mobile',
    }
    return render(request, 'menu/menu_detail_mobile.html', context)

# === 기기별 장바구니 뷰 ===

def menu_cart_desktop(request, store_id):
    """데스크톱 장바구니 화면 (공개, 비회원 접근 가능)"""
    # 스토어 조회 (비회원도 접근 가능하므로 소유자 확인 안함)
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True, is_active=True)
    
    context = {
        'store': store,
        'is_public_view': True,
        'is_cart_view': True,  # 장바구니 화면임을 표시
        'view_type': 'full_page',  # 독립 페이지로 표시
        'device_type': 'desktop',
    }
    return render(request, 'menu/menu_cart.html', context)

def menu_cart_mobile(request, store_id):
    """모바일 장바구니 화면 (공개, 비회원 접근 가능)"""
    # 스토어 조회 (비회원도 접근 가능하므로 소유자 확인 안함)
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True, is_active=True)
    
    context = {
        'store': store,
        'is_public_view': True,
        'is_cart_view': True,  # 장바구니 화면임을 표시
        'view_type': 'full_page',  # 독립 페이지로 표시
        'device_type': 'mobile',
    }
    return render(request, 'menu/menu_cart_mobile.html', context)
