from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.db import transaction
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Avg
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
from django.views.decorators.http import require_POST
from PIL import Image
import json
import uuid
import os
import logging

from stores.models import Store
from .models import Product, ProductImage, ProductOption, ProductOptionChoice
from stores.decorators import store_owner_required
from reviews.models import Review
from reviews.services import MAX_IMAGES_PER_REVIEW

logger = logging.getLogger(__name__)


def public_product_list(request, store_id):
    """일반 사용자용 상품 목록"""
    try:
        store = Store.objects.get(store_id=store_id, is_active=True, deleted_at__isnull=True)
    except Store.DoesNotExist:
        # 스토어가 존재하지 않는 경우
        context = {
            'store_id': store_id,
            'error_type': 'store_not_found'
        }
        return render(request, 'products/store_not_found.html', context, status=404)
    
    products = Product.objects.filter(store=store, is_active=True).order_by('-created_at')
    
    # 사용자의 장바구니 정보 가져오기 (로그인/비로그인 모두 지원)
    cart_items_count = 0
    cart_total_amount = 0
    try:
        from orders.services import CartService
        cart_service = CartService(request)
        cart_summary = cart_service.get_cart_summary()
        cart_items_count = cart_summary['total_items']
        cart_total_amount = cart_summary['total_amount']
    except Exception:
        pass
    
    context = {
        'store': store,
        'products': products,
        'cart_items_count': cart_items_count,
        'cart_total_amount': cart_total_amount,
        'is_public_view': True,
    }
    return render(request, 'products/product_list.html', context)


@login_required
@store_owner_required
def product_list(request, store_id):
    """상품 목록"""
    try:
        store = Store.objects.get(store_id=store_id, owner=request.user, deleted_at__isnull=True)
    except Store.DoesNotExist:
        # 스토어가 존재하지 않거나 소유자가 아닌 경우
        context = {
            'store_id': store_id,
            'error_type': 'store_not_found_or_not_owner'
        }
        return render(request, 'products/store_access_denied.html', context, status=404)
    
    # 관리자 뷰에서는 비활성화된 상품도 포함하여 표시
    products = Product.objects.filter(store=store).order_by('-created_at')
    
    context = {
        'store': store,
        'products': products,
        'is_public_view': False,  # 스토어 주인장의 관리 뷰
    }
    return render(request, 'products/product_list.html', context)


def product_detail(request, store_id, product_id):
    """상품 상세보기"""
    try:
        store = Store.objects.get(store_id=store_id, is_active=True, deleted_at__isnull=True)
    except Store.DoesNotExist:
        # 스토어가 존재하지 않는 경우
        context = {
            'store_id': store_id,
            'product_id': product_id,
            'error_type': 'store_not_found'
        }
        return render(request, 'products/store_not_found.html', context, status=404)
    
    try:
        product = Product.objects.get(id=product_id, store=store)
    except Product.DoesNotExist:
        # 상품이 존재하지 않는 경우
        context = {
            'store': store,
            'store_id': store_id,
            'product_id': product_id,
            'error_type': 'product_not_found'
        }
        return render(request, 'products/product_not_found.html', context, status=404)
    
    # 상품이 비활성화된 경우
    if not product.is_active:
        context = {
            'error_type': 'product_inactive'
        }
        return render(request, 'products/product_not_found.html', context, status=404)
    
    # 상품 이미지 가져오기
    product_images = product.images.all().order_by('order')

    # 상품 옵션 가져오기
    product_options = product.options.all().prefetch_related('choices').order_by('order')

    # 사용자의 장바구니 정보 가져오기 (CartService 사용)
    from orders.services import CartService
    cart_service = CartService(request)
    cart_summary = cart_service.get_cart_summary()
    cart_items = cart_service.get_cart_items()

    cart_items_count = cart_summary['total_items']
    cart_total_amount = cart_summary['total_amount']
    store_shipping = store.get_shipping_fee_display()

    product_shipping = store_shipping.copy()
    product_shipping['override_free'] = False
    if product.force_free_shipping and store_shipping['mode'] == 'flat':
        product_shipping = {
            **store_shipping,
            'sats': 0,
            'krw': 0 if store_shipping.get('krw') is not None else None,
            'override_free': True,
        }

    reviews_qs = (
        Review.objects.filter(product=product)
        .select_related('author')
        .prefetch_related('images')
        .order_by('-created_at', '-id')
    )

    paginator = Paginator(reviews_qs, 10)
    page_number = request.GET.get('page') or 1
    try:
        reviews_page = paginator.page(page_number)
    except PageNotAnInteger:
        reviews_page = paginator.page(1)
    except EmptyPage:
        reviews_page = paginator.page(paginator.num_pages)

    review_stats = reviews_qs.aggregate(avg_rating=Avg('rating'))
    average_rating = review_stats['avg_rating'] or 0
    total_reviews = paginator.count

    can_write_review = False

    if request.user.is_authenticated:
        can_write_review = True

        print(
            '[Reviews] user=', request.user.username,
            ' store_owner=', request.user == product.store.owner,
            ' product=', product.id,
            ' can_write=', can_write_review
        )

    context = {
        'store': store,
        'product': product,
        'product_images': product_images,
        'product_options': product_options,
        'cart_items_count': cart_items_count,
        'cart_total_amount': cart_total_amount,
        'cart_items': cart_items,
        'store_shipping': store_shipping,
        'product_shipping': product_shipping,
        'reviews_page': reviews_page,
        'review_average': average_rating,
        'review_total': total_reviews,
        'can_write_review': can_write_review,
        'max_review_images': MAX_IMAGES_PER_REVIEW,
    }
    return render(request, 'products/product_detail.html', context)


@login_required
@store_owner_required
def add_product(request, store_id):
    """상품 추가"""
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
    
    if request.method == 'POST':
        logger.info(f"상품 추가 POST 요청 받음")
        logger.info(f"POST 데이터: {dict(request.POST)}")
        logger.info(f"FILES 데이터: {list(request.FILES.keys())}")
        try:
            with transaction.atomic():
                # 가격 처리 - 새로운 규칙에 따라 처리
                price_display = request.POST.get('price_display', 'sats')

                force_free_shipping = request.POST.get('force_free_shipping') == 'on'
                if store.shipping_fee_mode != 'flat':
                    # 무료 배송 모드에서는 강제 옵션을 무시
                    force_free_shipping = False

                # 상품 생성을 위한 기본 데이터
                product_data = {
                    'store': store,
                    'title': request.POST.get('title', '').strip(),
                    'description': request.POST.get('description', '').strip(),
                    'price_display': price_display,
                    'is_discounted': request.POST.get('is_discounted') == 'on',
                    'completion_message': request.POST.get('completion_message', '').strip(),
                    'stock_quantity': int(request.POST.get('stock_quantity', 0)),
                    'shipping_fee': 0,
                    'shipping_fee_krw': None,
                    'force_free_shipping': force_free_shipping,
                }
                
                if price_display == 'krw':
                    # 원화 비율 연동: 원화 값을 저장하고 사토시는 JavaScript에서 계산된 값 사용
                    product_data['price_krw'] = int(request.POST.get('price_krw', 0))
                    product_data['price'] = int(request.POST.get('price_sats', 0))
                    
                    discounted_price_krw = request.POST.get('discounted_price_krw')
                    if discounted_price_krw:
                        product_data['discounted_price_krw'] = int(discounted_price_krw)
                        product_data['discounted_price'] = int(request.POST.get('discounted_price_sats', 0))
                else:
                    # 사토시 고정: 사토시 값을 저장하고 원화는 JavaScript에서 계산된 값 사용
                    product_data['price'] = int(request.POST.get('price_sats', 0))
                    product_data['price_krw'] = int(request.POST.get('price_krw', 0))
                    
                    discounted_price_sats = request.POST.get('discounted_price_sats')
                    if discounted_price_sats:
                        product_data['discounted_price'] = int(discounted_price_sats)
                        product_data['discounted_price_krw'] = int(request.POST.get('discounted_price_krw', 0))
                
                # 할인 설정 처리
                if not product_data['is_discounted']:
                    product_data['discounted_price'] = None
                    product_data['discounted_price_krw'] = None
                
                # 상품 생성
                product = Product.objects.create(**product_data)
                
                # 이미지 처리
                images = request.FILES.getlist('images')
                logger.info(f"받은 이미지 파일 개수: {len(images)}")
                for i, image_file in enumerate(images):
                    try:
                        logger.info(f"이미지 처리 시작: {image_file.name}, 크기: {image_file.size}")
                        # storage.utils의 함수 사용 (편집 모드와 동일한 방식)
                        from storage.utils import upload_product_image
                        result = upload_product_image(image_file, product, request.user)
                        
                        if result['success']:
                            logger.info(f"이미지 처리 성공: {image_file.name}")
                        else:
                            logger.warning(f"이미지 처리 실패: {image_file.name}, 오류: {result['error']}")
                    except Exception as e:
                        logger.error(f"이미지 처리 오류: {e}", exc_info=True)
                
                # 옵션 추가
                options_data = json.loads(request.POST.get('options', '[]'))
                for option_data in options_data:
                    if option_data.get('name'):
                        option = ProductOption.objects.create(
                            product=product,
                            name=option_data['name'],
                            order=option_data.get('order', 0)
                        )
                        
                        # 옵션 선택지 추가
                        for choice_data in option_data.get('choices', []):
                            if choice_data.get('name'):
                                ProductOptionChoice.objects.create(
                                    option=option,
                                    name=choice_data['name'],
                                    price=choice_data.get('price', 0),
                                    order=choice_data.get('order', 0)
                                )
                
                return redirect('products:product_list', store_id=store_id)

        except Exception as e:
            logger.error(f"상품 추가 오류: {e}", exc_info=True)
            messages.error(request, '상품 추가 중 오류가 발생했습니다.')

    context = {
        'store': store,
        'store_shipping': store.get_shipping_fee_display(),
    }
    return render(request, 'products/add_product.html', context)


# process_product_image 함수는 storage.utils.upload_product_image로 대체됨


@login_required
@store_owner_required
def edit_product(request, store_id, product_id):
    """상품 수정"""
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
    product = get_object_or_404(Product, id=product_id, store=store)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # 상품 정보 업데이트
                product.title = request.POST.get('title', '').strip()
                product.description = request.POST.get('description', '').strip()
                product.price = int(request.POST.get('price', 0))
                product.price_display = request.POST.get('price_display', 'sats')
                product.is_discounted = request.POST.get('is_discounted') == 'on'
                product.discounted_price = int(request.POST.get('discounted_price', 0)) if request.POST.get('discounted_price') else None
                product.shipping_fee = 0
                product.shipping_fee_krw = None
                product.force_free_shipping = (
                    store.shipping_fee_mode == 'flat' and request.POST.get('force_free_shipping') == 'on'
                )
                product.completion_message = request.POST.get('completion_message', '').strip()
                product.stock_quantity = int(request.POST.get('stock_quantity', 0))
                product.save()
                
                # 상품 옵션 처리 (기존 옵션 삭제 후 새로 추가)
                _process_product_options(request, product)
                
                # 새 이미지 처리
                images = request.FILES.getlist('images')
                for i, image_file in enumerate(images):
                    try:
                        # storage.utils의 함수 사용 (편집 모드와 동일한 방식)
                        from storage.utils import upload_product_image
                        result = upload_product_image(image_file, product, request.user)
                        
                        if result['success']:
                            logger.info(f"이미지 처리 성공: {image_file.name}")
                        else:
                            logger.warning(f"이미지 처리 실패: {image_file.name}, 오류: {result['error']}")
                    except Exception as e:
                        logger.error(f"이미지 처리 오류: {e}", exc_info=True)
                
                return redirect('products:product_list', store_id=store_id)
                
        except Exception as e:
            logger.error(f"상품 수정 오류: {e}", exc_info=True)
            messages.error(request, '상품 수정 중 오류가 발생했습니다.')
    
    context = {
        'store': store,
        'product': product,
        'store_shipping': store.get_shipping_fee_display(),
    }
    return render(request, 'products/edit_product.html', context)


@login_required
@store_owner_required
def edit_product_unified(request, store_id, product_id):
    """통합 상품 수정"""
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
    product = get_object_or_404(Product, id=product_id, store=store)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # 기본 정보 업데이트
                product.title = request.POST.get('title', '').strip()
                product.description = request.POST.get('description', '').strip()
                
                # 가격 표시 방식 변경 여부 확인
                new_price_display = request.POST.get('price_display', 'sats')
                price_display_changed = product.price_display != new_price_display
                
                # 가격 처리
                if price_display_changed:
                    product.price_display = new_price_display
                    
                    if new_price_display == 'krw':
                        product.price_krw = int(request.POST.get('price', 0))
                        product.price = int(request.POST.get('price', 0))  # 임시로 같은 값 사용
                        
                        discounted_price = request.POST.get('discounted_price')
                        if discounted_price:
                            product.discounted_price_krw = int(discounted_price)
                            product.discounted_price = int(discounted_price)  # 임시로 같은 값 사용
                    else:
                        product.price = int(request.POST.get('price', 0))
                        product.price_krw = None  # 사토시 모드에서는 원화 가격 초기화
                        
                        discounted_price = request.POST.get('discounted_price')
                        if discounted_price:
                            product.discounted_price = int(discounted_price)
                            product.discounted_price_krw = None  # 사토시 모드에서는 원화 할인가 초기화
                else:
                    if product.price_display == 'krw':
                        # 원화 비율 연동: 원화 값을 저장하고 사토시는 JavaScript에서 계산된 값 사용
                        product.price_krw = int(request.POST.get('price_krw', 0))
                        product.price = int(request.POST.get('price_sats', 0))
                        
                        discounted_price_krw = request.POST.get('discounted_price_krw')
                        if discounted_price_krw:
                            product.discounted_price_krw = int(discounted_price_krw)
                            product.discounted_price = int(request.POST.get('discounted_price_sats', 0))
                    else:
                        product.price = int(request.POST.get('price', 0))
                        
                        discounted_price = request.POST.get('discounted_price')
                        if discounted_price:
                            product.discounted_price = int(discounted_price)
                
                # 할인 설정
                product.is_discounted = request.POST.get('is_discounted') == 'on'
                if not product.is_discounted:
                    product.discounted_price = None
                    product.discounted_price_krw = None

                # 완료 메시지
                product.completion_message = request.POST.get('completion_message', '').strip()
                product.shipping_fee = 0
                product.shipping_fee_krw = None
                product.force_free_shipping = (
                    store.shipping_fee_mode == 'flat' and request.POST.get('force_free_shipping') == 'on'
                )

                # 재고 수량
                product.stock_quantity = int(request.POST.get('stock_quantity', 0))

                product.save()
                
                # 상품 옵션 처리
                _process_product_options_form(request, product)
                
                return redirect('products:product_list', store_id=store_id)
                
        except Exception as e:
            logger.error(f"통합 상품 수정 오류: {e}", exc_info=True)
            messages.error(request, '상품 수정 중 오류가 발생했습니다.')
    
    context = {
        'store': store,
        'product': product,
        'store_shipping': store.get_shipping_fee_display(),
    }
    return render(request, 'products/edit_product_unified.html', context)


@login_required
@store_owner_required
def delete_product(request, store_id, product_id):
    """상품 삭제"""
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
    product = get_object_or_404(Product, id=product_id, store=store)
    
    if request.method == 'POST':
        product_title = product.title
        
        try:
            with transaction.atomic():
                # 관련 이미지 파일들 삭제
                for image in product.images.all():
                    if image.file_path and default_storage.exists(image.file_path):
                        default_storage.delete(image.file_path)
                
                # 상품 완전 삭제 (관련 데이터도 CASCADE로 함께 삭제됨)
                product.delete()
                
                messages.success(request, f'"{product_title}" 상품이 완전히 삭제되었습니다.')
                
        except Exception as e:
            logger.error(f"상품 삭제 오류: {e}", exc_info=True)
            messages.error(request, '상품 삭제 중 오류가 발생했습니다.')
    
    return redirect('products:product_list', store_id=store_id)


@login_required
@store_owner_required
def upload_product_image(request, store_id, product_id):
    """상품 이미지 업로드 (AJAX)"""
    try:
        store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
        product = get_object_or_404(Product, id=product_id, store=store)
        
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
        
        # 현재 이미지 개수 확인 (최대 10개)
        current_count = product.images.count()
        if current_count >= 10:
            return JsonResponse({
                'success': False,
                'error': '상품당 최대 10개의 이미지만 업로드할 수 있습니다.'
            })
        
        # S3에 이미지 업로드
        from storage.utils import upload_product_image
        result = upload_product_image(image_file, product, request.user)
        
        if result['success']:
            product_image = result['product_image']
            return JsonResponse({
                'success': True,
                'image': {
                    'id': product_image.id,
                    'original_name': product_image.original_name,
                    'file_url': product_image.file_url,
                    'file_size': product_image.file_size,
                    'width': product_image.width,
                    'height': product_image.height,
                    'order': product_image.order,
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result['error']
            })
            
    except Exception as e:
        logger.error(f"상품 이미지 업로드 오류: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': '이미지 업로드 중 오류가 발생했습니다.'
        })


@login_required
@store_owner_required
def delete_product_image(request, store_id, product_id, image_id):
    """상품 이미지 삭제"""
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
    product = get_object_or_404(Product, id=product_id, store=store)
    image = get_object_or_404(ProductImage, id=image_id, product=product)
    
    if request.method in ['DELETE', 'POST']:
        try:
            # 파일 삭제
            if image.file_path and default_storage.exists(image.file_path):
                default_storage.delete(image.file_path)
            
            image.delete()
            
            return JsonResponse({'success': True})
            
        except Exception as e:
            logger.error(f"이미지 삭제 오류: {e}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': '이미지 삭제 중 오류가 발생했습니다.'
            })
    
    return JsonResponse({'success': False, 'error': '잘못된 요청입니다.'})


def _process_product_options(request, product):
    """상품 옵션 처리 (기존 add_product 로직에서 분리)"""
    # 기존 옵션 삭제
    product.options.all().delete()
    
    # 새 옵션 추가
    options_data = json.loads(request.POST.get('options', '[]'))
    for option_data in options_data:
        if option_data.get('name'):
            option = ProductOption.objects.create(
                product=product,
                name=option_data['name'],
                order=option_data.get('order', 0)
            )
            
            # 옵션 선택지 추가
            for choice_data in option_data.get('choices', []):
                if choice_data.get('name'):
                    ProductOptionChoice.objects.create(
                        option=option,
                        name=choice_data['name'],
                        price=choice_data.get('price', 0),
                        order=choice_data.get('order', 0)
                    )
        

# 섹션별 상품 편집 뷰들
@login_required
@store_owner_required
def manage_product(request, store_id, product_id):
    """상품 관리 메인 페이지"""
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
    product = get_object_or_404(Product, id=product_id, store=store)
    
    context = {
        'store': store,
        'product': product,
    }
    return render(request, 'products/manage_product.html', context)


@login_required
@store_owner_required
def edit_basic_info(request, store_id, product_id):
    """상품 기본 정보 편집"""
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
    product = get_object_or_404(Product, id=product_id, store=store)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # 기본 정보 업데이트
                product.title = request.POST.get('title', '').strip()
                product.description = request.POST.get('description', '').strip()
                
                # 가격 표시 방식 변경 여부 확인
                new_price_display = request.POST.get('price_display', 'sats')
                price_display_changed = product.price_display != new_price_display
                
                # 가격 처리 - 새로운 규칙에 따라 처리
                if price_display_changed:
                    # 가격 표시 방식이 변경된 경우: 새로운 방식에 맞게 저장
                    product.price_display = new_price_display
                    
                    if new_price_display == 'krw':
                        # 원화 비율 연동으로 변경: 원화 값을 저장하고 사토시는 JavaScript에서 계산된 값 사용
                        product.price_krw = int(request.POST.get('price_krw', 0))
                        product.price = int(request.POST.get('price_sats', 0))
                        
                        discounted_price_krw = request.POST.get('discounted_price_krw')
                        if discounted_price_krw:
                            product.discounted_price_krw = int(discounted_price_krw)
                            product.discounted_price = int(request.POST.get('discounted_price_sats', 0))
                    else:
                        # 사토시 고정으로 변경: 사토시 값을 저장하고 원화는 JavaScript에서 계산된 값 사용
                        product.price = int(request.POST.get('price_sats', 0))
                        product.price_krw = int(request.POST.get('price_krw', 0))
                        
                        discounted_price_sats = request.POST.get('discounted_price_sats')
                        if discounted_price_sats:
                            product.discounted_price = int(discounted_price_sats)
                            product.discounted_price_krw = int(request.POST.get('discounted_price_krw', 0))
                else:
                    # 가격 표시 방식이 변경되지 않은 경우: 기존 방식에 맞게 저장
                    if product.price_display == 'krw':
                        # 기존이 원화 비율 연동: 원화 값을 저장하고 사토시는 JavaScript에서 계산된 값 사용
                        product.price_krw = int(request.POST.get('price_krw', 0))
                        product.price = int(request.POST.get('price_sats', 0))
                        
                        discounted_price_krw = request.POST.get('discounted_price_krw')
                        if discounted_price_krw:
                            product.discounted_price_krw = int(discounted_price_krw)
                            product.discounted_price = int(request.POST.get('discounted_price_sats', 0))
                    else:
                        # 기존이 사토시 고정: 사토시 값을 저장하고 원화는 JavaScript에서 계산된 값 사용
                        product.price = int(request.POST.get('price_sats', 0))
                        product.price_krw = int(request.POST.get('price_krw', 0))
                        
                        discounted_price_sats = request.POST.get('discounted_price_sats')
                        if discounted_price_sats:
                            product.discounted_price = int(discounted_price_sats)
                            product.discounted_price_krw = int(request.POST.get('discounted_price_krw', 0))
                
                # 할인 설정
                product.is_discounted = request.POST.get('is_discounted') == 'on'
                if not product.is_discounted:
                    product.discounted_price = None
                    product.discounted_price_krw = None
                
                # 재고 수량
                product.stock_quantity = int(request.POST.get('stock_quantity', 0))
                product.shipping_fee = 0
                product.shipping_fee_krw = None

                product.save()
                
                return redirect('products:manage_product', store_id=store_id, product_id=product_id)
                
        except Exception as e:
            logger.error(f"기본 정보 수정 오류: {e}", exc_info=True)
            messages.error(request, '기본 정보 수정 중 오류가 발생했습니다.')
    
    context = {
        'store': store,
        'product': product,
    }
    return render(request, 'products/edit_basic_info.html', context)


@login_required
@store_owner_required
def edit_options(request, store_id, product_id):
    """상품 옵션 편집"""
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
    product = get_object_or_404(Product, id=product_id, store=store)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                _process_product_options_form(request, product)
                return redirect('products:manage_product', store_id=store_id, product_id=product_id)
                
        except Exception as e:
            logger.error(f"옵션 수정 오류: {e}", exc_info=True)
            messages.error(request, '옵션 수정 중 오류가 발생했습니다.')
    
    context = {
        'store': store,
        'product': product,
    }
    return render(request, 'products/edit_options.html', context)


@login_required
@store_owner_required
def edit_images(request, store_id, product_id):
    """상품 이미지 편집"""
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
    product = get_object_or_404(Product, id=product_id, store=store)
    
    context = {
        'store': store,
        'product': product,
    }
    return render(request, 'products/edit_images.html', context)


@login_required
@store_owner_required
def edit_completion_message(request, store_id, product_id):
    """결제 완료 메시지 편집"""
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
    product = get_object_or_404(Product, id=product_id, store=store)
    
    if request.method == 'POST':
        try:
            product.completion_message = request.POST.get('completion_message', '').strip()
            product.save()
            
            return redirect('products:manage_product', store_id=store_id, product_id=product_id)
            
        except Exception as e:
            logger.error(f"완료 메시지 수정 오류: {e}", exc_info=True)
            messages.error(request, '완료 메시지 수정 중 오류가 발생했습니다.')
    
    context = {
        'store': store,
        'product': product,
    }
    return render(request, 'products/edit_completion_message.html', context)


def _process_product_options_form(request, product):
    """상품 옵션 처리 (폼 데이터 방식)"""
    try:
        # 기존 옵션들 삭제
        product.options.all().delete()
        
        # 새로운 옵션들 추가
        option_index = 0
        while f'options[{option_index}][name]' in request.POST:
            option_name = request.POST.get(f'options[{option_index}][name]', '').strip()
            
            if option_name:
                option = ProductOption.objects.create(
                    product=product,
                    name=option_name,
                    order=option_index
                )
                
                # 옵션 선택지들 추가
                choice_index = 0
                while f'options[{option_index}][choices][{choice_index}][name]' in request.POST:
                    choice_name = request.POST.get(f'options[{option_index}][choices][{choice_index}][name]', '').strip()
                    choice_price = request.POST.get(f'options[{option_index}][choices][{choice_index}][price]', 0)
                    
                    if choice_name:
                        # 가격 표시 방식에 따라 적절한 필드에 저장
                        choice_data = {
                            'option': option,
                            'name': choice_name,
                            'order': choice_index
                        }
                        
                        if choice_price:
                            price_value = int(choice_price)
                            if product.price_display == 'krw':
                                # 원화연동: 입력된 값을 원화 필드에 저장, 사토시는 0으로 설정 (runtime에서 계산)
                                choice_data['price_krw'] = price_value
                                choice_data['price'] = 0  # runtime에서 public_price 속성으로 계산됨
                            else:
                                # 사토시 고정: 입력된 값을 사토시 필드에 저장
                                choice_data['price'] = price_value
                                choice_data['price_krw'] = None
                        else:
                            choice_data['price'] = 0
                            choice_data['price_krw'] = None
                        
                        ProductOptionChoice.objects.create(**choice_data)
                    
                    choice_index += 1
            
            option_index += 1
            
    except Exception as e:
        logger.error(f"옵션 처리 오류: {e}", exc_info=True)
        raise


@login_required
@store_owner_required
@require_POST
def toggle_product_status(request, store_id, product_id):
    """상품 활성화/비활성화 토글"""
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
    product = get_object_or_404(Product, id=product_id, store=store)
    
    try:
        product.is_active = not product.is_active
        product.save()
        
        status = "활성화" if product.is_active else "비활성화"
        return JsonResponse({
            'success': True,
            'message': f'상품이 {status}되었습니다.',
            'is_active': product.is_active
        })
    except Exception as e:
        logger.error(f"상품 상태 변경 오류: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': '상품 상태 변경 중 오류가 발생했습니다.'
        })


@login_required
@store_owner_required
@require_POST
def toggle_temporary_out_of_stock(request, store_id, product_id):
    """상품 일시품절 토글"""
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
    product = get_object_or_404(Product, id=product_id, store=store)
    
    try:
        product.is_temporarily_out_of_stock = not product.is_temporarily_out_of_stock
        product.save()
        
        status = "일시품절" if product.is_temporarily_out_of_stock else "일시품절 해제"
        return JsonResponse({
            'success': True,
            'message': f'상품이 {status}되었습니다.',
            'is_temporarily_out_of_stock': product.is_temporarily_out_of_stock,
            'stock_status': product.stock_status
        })
    except Exception as e:
        logger.error(f"일시품절 상태 변경 오류: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': '일시품절 상태 변경 중 오류가 발생했습니다.'
        })
