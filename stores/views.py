from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, Http404, HttpResponse
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError
from django.db import transaction, models
from django.utils import timezone
from django.db.models import Q, Max
import json
import qrcode
import io
import base64
import logging
import csv
from datetime import datetime, timedelta
from .models import (
    Store, StoreCreationStep, ReservedStoreId, StoreImage
)
from products.models import (
    Product, ProductImage, ProductOption, ProductOptionChoice
)
from orders.models import (
    Cart, CartItem, Order, OrderItem, PurchaseHistory
)
from django.conf import settings
from django.template.loader import render_to_string
from storage.utils import upload_store_image, delete_file_from_s3
from myshop.services import UpbitExchangeService
from reviews.services import (
    MAX_IMAGES_PER_REVIEW,
    build_reviews_url,
    get_paginated_reviews,
    user_has_purchased_product,
)

from .cache_utils import get_store_browse_cache, set_store_browse_cache

# 로거 설정
logger = logging.getLogger(__name__)

def browse_stores(request):
    """스토어 탐색 페이지"""
    search_query = request.GET.get('q', '').strip()

    # 활성화된 스토어만 가져오기
    active_stores = Store.objects.filter(
        is_active=True, 
        deleted_at__isnull=True
    ).select_related('owner')
    
    # 검색 쿼리가 있으면 필터링
    if search_query:
        stores = active_stores.filter(
            Q(store_name__icontains=search_query) |
            Q(store_description__icontains=search_query) |
            Q(owner_name__icontains=search_query)
        ).order_by('-created_at')[:16]  # 검색 결과는 16개까지
        
        context = {
            'stores': stores,
            'search_query': search_query,
            'total_count': len(stores),
            'recent_stores': None,
            'active_stores': None,
            'live_lectures': None,
        }
    else:
        cached_context = get_store_browse_cache()
        if cached_context is not None:
            return render(request, 'stores/browse_stores.html', cached_context)

        # 최근 개설된 스토어 5개 (생성일 기준)
        recent_stores = active_stores.order_by('-created_at')[:5]
        
        # 주문이 활발한 스토어 5개 (모든 주문 유형을 반영한 최근 주문 기준)
        from orders.models import Order
        from meetup.models import MeetupOrder
        from lecture.models import LiveLectureOrder
        from django.db.models import Max, Q as Q_model
        from myshop.models import SiteSettings
        
        # 최근 30일 내 주문이 있는 스토어들을 최근 주문일 순으로 정렬
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        # 제외할 스토어 ID 목록 가져오기
        site_settings = SiteSettings.get_settings()
        excluded_store_ids = []
        if site_settings.excluded_active_store_ids:
            excluded_store_ids = [
                store_id.strip() 
                for store_id in site_settings.excluded_active_store_ids.split(',')
                if store_id.strip()
            ]
        
        # 각 스토어별로 가장 최근 주문일을 구하기 (상품, 밋업, 라이브강의 주문 모두 포함)
        active_order_stores = active_stores.filter(
            Q_model(orders__created_at__gte=thirty_days_ago) |  # 상품 주문
            Q_model(meetups__orders__created_at__gte=thirty_days_ago) |  # 밋업 주문  
            Q_model(live_lectures__orders__created_at__gte=thirty_days_ago)  # 라이브강의 주문
        ).exclude(
            store_id__in=excluded_store_ids
        ).annotate(
            latest_product_order=Max('orders__created_at'),
            latest_meetup_order=Max('meetups__orders__created_at'),
            latest_live_lecture_order=Max('live_lectures__orders__created_at')
        ).distinct()
        
        # Python에서 최종 정렬 (각 스토어의 가장 최근 주문일 기준)
        active_order_stores_list = []
        for store in active_order_stores:
            latest_dates = []
            if store.latest_product_order:
                latest_dates.append(store.latest_product_order)
            if store.latest_meetup_order:
                latest_dates.append(store.latest_meetup_order)
            if store.latest_live_lecture_order:
                latest_dates.append(store.latest_live_lecture_order)
            
            if latest_dates:
                store.overall_latest_order = max(latest_dates)
                active_order_stores_list.append(store)
        
        # 최근 주문일 기준으로 정렬하고 5개만 선택
        active_order_stores_list.sort(key=lambda x: x.overall_latest_order, reverse=True)
        active_order_stores_final = active_order_stores_list[:5]
        
        # 최신 라이브 강의 5개 (활성화되고 삭제되지 않은 것, 제외 스토어 필터링)
        from lecture.models import LiveLecture
        live_lectures = LiveLecture.objects.filter(
            is_active=True,
            deleted_at__isnull=True,
            store__is_active=True,
            store__deleted_at__isnull=True
        ).exclude(
            store__store_id__in=excluded_store_ids
        ).select_related('store').order_by('-created_at')[:5]
        
        # 최근 판매된 디지털 파일 5개 (제외 스토어 필터링)
        from file.models import FileOrder
        recent_file_orders = FileOrder.objects.filter(
            status='confirmed',
            digital_file__is_active=True,
            digital_file__deleted_at__isnull=True,
            digital_file__store__is_active=True,
            digital_file__store__deleted_at__isnull=True
        ).exclude(
            digital_file__store__store_id__in=excluded_store_ids
        ).select_related(
            'digital_file', 
            'digital_file__store',
            'user'
        ).order_by('-confirmed_at')[:5]
        
        # 최근 주문된 상품 목록 5개 (제외 스토어 필터링)
        from orders.models import OrderItem
        recent_ordered_products = OrderItem.objects.filter(
            product__is_active=True,
            product__store__is_active=True,
            product__store__deleted_at__isnull=True,
            order__status='paid'
        ).exclude(
            product__store__store_id__in=excluded_store_ids
        ).select_related('product', 'product__store').order_by('-order__created_at')[:5]
        
        # 최근 신청된 밋업 목록 5개 (제외 스토어 필터링)
        from meetup.models import MeetupOrder
        recent_meetup_orders = MeetupOrder.objects.filter(
            meetup__is_active=True,
            meetup__deleted_at__isnull=True,
            meetup__store__is_active=True,
            meetup__store__deleted_at__isnull=True,
            status__in=['confirmed', 'completed']
        ).exclude(
            meetup__store__store_id__in=excluded_store_ids
        ).select_related('meetup', 'meetup__store').order_by('-created_at')[:5]
        
        context = {
            'stores': None,
            'search_query': search_query,
            'total_count': 0,
            'recent_stores': list(recent_stores),
            'active_stores': list(active_order_stores_final),
            'live_lectures': list(live_lectures),
            'recent_file_orders': list(recent_file_orders),
            'recent_ordered_products': list(recent_ordered_products),
            'recent_meetup_orders': list(recent_meetup_orders),
        }

        set_store_browse_cache(context)

    return render(request, 'stores/browse_stores.html', context)


def browse_recent_stores(request):
    """최근 개설된 스토어 전체보기"""
    # 활성화된 스토어만 가져오기
    stores = Store.objects.filter(
        is_active=True, 
        deleted_at__isnull=True
    ).select_related('owner').order_by('-created_at')
    
    # 페이지네이션
    from django.core.paginator import Paginator
    paginator = Paginator(stores, 15)  # 한 페이지에 15개씩
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'page_title': '최근 개설된 스토어',
        'page_description': '새롭게 문을 연 스토어들을 모두 확인해보세요',
        'store_type': 'recent',
    }
    
    return render(request, 'stores/browse_stores_list.html', context)


def browse_active_stores(request):
    """주문이 활발한 스토어 전체보기"""
    from orders.models import Order
    from meetup.models import MeetupOrder
    from lecture.models import LiveLectureOrder
    from django.db.models import Max, Q as Q_model
    from myshop.models import SiteSettings
    
    # 활성화된 스토어만 가져오기
    active_stores = Store.objects.filter(
        is_active=True, 
        deleted_at__isnull=True
    ).select_related('owner')
    
    # 최근 30일 내 주문이 있는 스토어들을 최근 주문일 순으로 정렬
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    # 제외할 스토어 ID 목록 가져오기
    site_settings = SiteSettings.get_settings()
    excluded_store_ids = []
    if site_settings.excluded_active_store_ids:
        excluded_store_ids = [
            store_id.strip() 
            for store_id in site_settings.excluded_active_store_ids.split(',')
            if store_id.strip()
        ]
    
    # 각 스토어별로 가장 최근 주문일을 구하기 (상품, 밋업, 라이브강의 주문 모두 포함)
    active_order_stores = active_stores.filter(
        Q_model(orders__created_at__gte=thirty_days_ago) |  # 상품 주문
        Q_model(meetups__orders__created_at__gte=thirty_days_ago) |  # 밋업 주문  
        Q_model(live_lectures__orders__created_at__gte=thirty_days_ago)  # 라이브강의 주문
    ).exclude(
        store_id__in=excluded_store_ids
    ).annotate(
        latest_product_order=Max('orders__created_at'),
        latest_meetup_order=Max('meetups__orders__created_at'),
        latest_live_lecture_order=Max('live_lectures__orders__created_at')
    ).distinct()
    
    # Python에서 최종 정렬 (각 스토어의 가장 최근 주문일 기준)
    active_order_stores_list = []
    for store in active_order_stores:
        latest_dates = []
        if store.latest_product_order:
            latest_dates.append(store.latest_product_order)
        if store.latest_meetup_order:
            latest_dates.append(store.latest_meetup_order)
        if store.latest_live_lecture_order:
            latest_dates.append(store.latest_live_lecture_order)
        
        if latest_dates:
            store.overall_latest_order = max(latest_dates)
            active_order_stores_list.append(store)
    
    # 최근 주문일 기준으로 정렬
    active_order_stores_list.sort(key=lambda x: x.overall_latest_order, reverse=True)
    
    # 페이지네이션
    from django.core.paginator import Paginator
    paginator = Paginator(active_order_stores_list, 16)  # 한 페이지에 16개씩
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'page_title': '주문이 활발한 스토어',
        'page_description': '최근 주문이 많은 인기 스토어들을 모두 만나보세요',
        'store_type': 'active',
    }
    
    return render(request, 'stores/browse_stores_list.html', context)

@login_required
def create_store(request):
    """스토어 생성 시작 페이지"""
    # 이미 활성화된 스토어가 있는지 확인 (1인 1스토어 제한)
    existing_store = Store.objects.filter(owner=request.user, deleted_at__isnull=True).first()
    if existing_store:
        if existing_store.is_active:
            messages.warning(request, '이미 활성화된 스토어가 있습니다. 계정당 하나의 스토어만 운영할 수 있습니다.')
            return redirect('stores:store_detail', store_id=existing_store.store_id)
        else:
            # 진행 중인 스토어가 있으면 해당 단계로 이동
            step = getattr(existing_store, 'creation_step', None)
            if step:
                return redirect('stores:create_store_step', step=step.current_step)
    
    return render(request, 'stores/create_start.html')

@login_required
def create_store_step(request, step):
    """단계별 스토어 생성"""
    if step < 1 or step > 5:
        messages.error(request, '잘못된 단계입니다.')
        return redirect('stores:create_store')
    
    # 이미 활성화된 스토어가 있는지 확인 (1인 1스토어 제한)
    store = Store.objects.filter(owner=request.user, deleted_at__isnull=True).first()
    if store and store.is_active:
        messages.warning(request, '이미 활성화된 스토어가 있습니다. 계정당 하나의 스토어만 운영할 수 있습니다.')
        return redirect('stores:store_detail', store_id=store.store_id)
    
    if not store and step > 1:
        messages.error(request, '먼저 1단계부터 진행해주세요.')
        return redirect('stores:create_store_step', step=1)
    
    if request.method == 'POST':
        return handle_store_creation_step(request, store, step)
    
    context = {
        'step': step,
        'store': store,
    }
    
    # 3단계에서 블링크 API 문서 링크 추가
    if step == 3:
        from myshop.models import SiteSettings
        site_settings = SiteSettings.get_settings()
        context['blink_api_doc_url'] = site_settings.blink_api_doc_url
    
    return render(request, f'stores/create_step{step}.html', context)

def handle_store_creation_step(request, store, step):
    """각 단계별 POST 요청 처리"""
    try:
        with transaction.atomic():
            if step == 1:
                return handle_step1(request, store)
            elif step == 2:
                return handle_step2(request, store)
            elif step == 3:
                return handle_step3(request, store)
            elif step == 4:
                return handle_step4(request, store)
            elif step == 5:
                return handle_step5(request, store)
    except ValidationError as e:
        messages.error(request, str(e))
        return redirect('stores:create_store_step', step=step)

def handle_step1(request, store):
    """1단계: 스토어 아이디 설정"""
    store_id = request.POST.get('store_id', '').strip()
    
    if not store_id:
        raise ValidationError('스토어 아이디를 입력해주세요.')
    
    # 예약어 검증
    if ReservedStoreId.is_reserved(store_id):
        raise ValidationError(f'"{store_id}"는 예약어로 사용할 수 없습니다.')
    
    # 중복 체크 (삭제된 스토어 제외, 현재 스토어 제외)
    query = Store.objects.filter(store_id=store_id, deleted_at__isnull=True)
    if store:
        query = query.exclude(id=store.id)
    
    if query.exists():
        raise ValidationError('이미 사용 중인 스토어 아이디입니다.')
    
    # 새 스토어 생성 또는 업데이트
    if not store:
        store = Store.objects.create(
            store_id=store_id,
            owner=request.user,
            store_name='',  # 임시값
            owner_name='',  # 임시값
            chat_channel='https://example.com',  # 임시값
        )
        StoreCreationStep.objects.create(
            store=store,
            current_step=1,
            step1_completed=True
        )
    else:
        store.store_id = store_id
        store.save()
        store.creation_step.step1_completed = True
        store.creation_step.current_step = 2
        store.creation_step.save()
    
    return redirect('stores:create_store_step', step=2)

def handle_step2(request, store):
    """2단계: 스토어 정보 입력"""
    store_name = request.POST.get('store_name', '').strip()
    store_description = request.POST.get('store_description', '').strip()
    owner_name = request.POST.get('owner_name', '').strip()
    owner_phone = request.POST.get('owner_phone', '').strip()
    owner_email = request.POST.get('owner_email', '').strip()
    business_license_number = request.POST.get('business_license_number', '').strip()
    telecommunication_sales_number = request.POST.get('telecommunication_sales_number', '').strip()
    chat_channel = request.POST.get('chat_channel', '').strip()
    
    if not store_name:
        raise ValidationError('스토어 이름을 입력해주세요.')
    if not owner_name:
        raise ValidationError('주인장 이름을 입력해주세요.')
    if not chat_channel:
        raise ValidationError('대화채널을 입력해주세요.')
    if not owner_phone and not owner_email:
        raise ValidationError('휴대전화 또는 이메일 중 하나는 반드시 입력해야 합니다.')
    
    store.store_name = store_name
    store.store_description = store_description
    store.owner_name = owner_name
    store.owner_phone = owner_phone
    store.owner_email = owner_email
    store.business_license_number = business_license_number
    store.telecommunication_sales_number = telecommunication_sales_number
    store.chat_channel = chat_channel
    store.save()
    
    store.creation_step.step2_completed = True
    store.creation_step.current_step = 3
    store.creation_step.save()
    
    return redirect('stores:create_store_step', step=3)

def handle_step3(request, store):
    """3단계: 블링크 API 정보 입력"""
    blink_api_info = request.POST.get('blink_api_info', '').strip()
    blink_wallet_id = request.POST.get('blink_wallet_id', '').strip()
    
    if not blink_api_info:
        raise ValidationError('블링크 API 정보를 입력해주세요.')
    if not blink_wallet_id:
        raise ValidationError('블링크 월렛 ID를 입력해주세요.')
    
    # 🔐 암호화해서 저장
    store.set_blink_api_info(blink_api_info)
    store.set_blink_wallet_id(blink_wallet_id)
    store.save()
    
    store.creation_step.step3_completed = True
    store.creation_step.current_step = 4
    store.creation_step.save()
    
    return redirect('stores:create_store_step', step=4)

def handle_step4(request, store):
    """4단계: 테스트 결제 확인"""
    test_completed = request.POST.get('test_completed')
    
    if test_completed:
        store.creation_step.step4_completed = True
        store.creation_step.current_step = 5
        store.creation_step.save()
        return redirect('stores:create_store_step', step=5)
    
    return redirect('stores:create_store_step', step=4)

def handle_step5(request, store):
    """5단계: 최종 확인 및 스토어 활성화"""
    confirm = request.POST.get('confirm')
    
    if confirm:
        store.is_active = True
        store.save()
        
        store.creation_step.step5_completed = True
        store.creation_step.save()
        
        return redirect('stores:store_detail', store_id=store.store_id)
    
    return redirect('stores:create_store_step', step=5)

@require_POST
def check_store_id(request):
    """스토어 아이디 중복 확인 AJAX"""
    store_id = request.POST.get('store_id', '').strip()
    current_store_id = request.POST.get('current_store_id', '').strip()
    
    if not store_id:
        return JsonResponse({'available': False, 'message': '스토어 아이디를 입력해주세요.'})
    
    # 예약어 검증
    if ReservedStoreId.is_reserved(store_id):
        return JsonResponse({'available': False, 'message': f'"{store_id}"는 예약어로 사용할 수 없습니다.'})
    
    # 중복 검증 (삭제된 스토어 제외, 현재 생성 중인 스토어 제외)
    query = Store.objects.filter(store_id=store_id, deleted_at__isnull=True)
    
    # 현재 생성 중인 스토어 아이디가 있다면 해당 스토어는 제외
    if current_store_id:
        query = query.exclude(store_id=current_store_id)
    
    if query.exists():
        return JsonResponse({'available': False, 'message': '이미 사용 중인 스토어 아이디입니다.'})
    
    return JsonResponse({'available': True, 'message': '사용 가능한 스토어 아이디입니다.'})

def generate_test_qr_code(store):
    """테스트용 QR 코드 생성"""
    test_data = {
        'store_id': store.store_id,
        'amount': 1000,  # 테스트용 1000원
        'currency': 'KRW',
        'description': f'{store.store_name} 테스트 결제'
    }
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(json.dumps(test_data))
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    
    img_base64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{img_base64}"

@login_required
def test_payment(request):
    """테스트 결제 처리"""
    if request.method == 'POST':
        # 실제로는 블링크 API를 통해 결제 처리
        # 여기서는 단순히 성공 응답
        return JsonResponse({
            'success': True,
            'message': '테스트 결제가 성공적으로 완료되었습니다!'
        })
    
    return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})

@login_required
def my_stores(request):
    """내 스토어 관리"""
    store = Store.objects.filter(owner=request.user, deleted_at__isnull=True).select_related('owner').first()
    
    return render(request, 'stores/my_stores.html', {'store': store})

@login_required
def edit_store(request, store_id):
    """스토어 편집"""
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
    
    if request.method == 'POST':
        try:
            # 스토어 기본 정보 업데이트
            store_name = request.POST.get('store_name', '').strip()
            store_description = request.POST.get('store_description', '').strip()
            owner_name = request.POST.get('owner_name', '').strip()
            owner_phone = request.POST.get('owner_phone', '').strip()
            owner_email = request.POST.get('owner_email', '').strip()
            business_license_number = request.POST.get('business_license_number', '').strip()
            telecommunication_sales_number = request.POST.get('telecommunication_sales_number', '').strip()
            chat_channel = request.POST.get('chat_channel', '').strip()
            is_active = request.POST.get('is_active') == 'on'
            
            # 필수 필드 검증
            if not store_name:
                raise ValidationError('스토어 이름을 입력해주세요.')
            if not owner_name:
                raise ValidationError('주인장 이름을 입력해주세요.')
            if not chat_channel:
                raise ValidationError('대화채널을 입력해주세요.')
            if not owner_phone and not owner_email:
                raise ValidationError('휴대전화 또는 이메일 중 하나는 반드시 입력해야 합니다.')
            
            # 기본 정보 저장
            store.store_name = store_name
            store.store_description = store_description
            store.owner_name = owner_name
            store.owner_phone = owner_phone
            store.owner_email = owner_email
            store.business_license_number = business_license_number
            store.telecommunication_sales_number = telecommunication_sales_number
            store.chat_channel = chat_channel
            store.is_active = is_active
            
            # 블링크 API 정보 업데이트 (값이 입력된 경우에만)
            blink_api_info = request.POST.get('blink_api_info', '').strip()
            blink_wallet_id = request.POST.get('blink_wallet_id', '').strip()
            
            if blink_api_info:
                store.set_blink_api_info(blink_api_info)
            
            if blink_wallet_id:
                store.set_blink_wallet_id(blink_wallet_id)
            
            # 히어로 섹션 색상 업데이트
            hero_color1 = request.POST.get('hero_color1', '').strip()
            hero_color2 = request.POST.get('hero_color2', '').strip()
            hero_text_color = request.POST.get('hero_text_color', '').strip()
            
            if hero_color1 and hero_color1.startswith('#') and len(hero_color1) == 7:
                store.hero_color1 = hero_color1
            if hero_color2 and hero_color2.startswith('#') and len(hero_color2) == 7:
                store.hero_color2 = hero_color2
            if hero_text_color and hero_text_color.startswith('#') and len(hero_text_color) == 7:
                store.hero_text_color = hero_text_color
            
            store.save()
            
            return redirect('stores:store_detail', store_id=store.store_id)
            
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'스토어 정보 업데이트 중 오류가 발생했습니다: {str(e)}')
    
    return render(request, 'stores/edit_store.html', {'store': store})

def store_detail(request, store_id):
    """스토어 상세 페이지 (고객용)"""
    try:
        store = Store.objects.get(store_id=store_id, deleted_at__isnull=True)
    except Store.DoesNotExist:
        # 스토어 자체가 존재하지 않거나 삭제된 경우 친절한 안내 페이지 표시
        return render(request, 'stores/store_not_found.html', {
            'store_id': store_id,
        }, status=404)
    
    if store.is_active:
        # 활성화된 스토어는 정상적으로 표시
        # 상품 목록도 함께 가져오기 (최대 8개만)
        products = store.products.filter(is_active=True).order_by('-created_at')[:8]
        
        # 밋업 목록도 함께 가져오기 (최대 8개만)
        from meetup.models import Meetup
        meetups = Meetup.objects.filter(
            store=store, 
            is_active=True
        ).order_by('-created_at')[:8]
        
        # 라이브 강의 목록도 함께 가져오기 (최대 8개만)
        from lecture.models import LiveLecture
        live_lectures = LiveLecture.objects.filter(
            store=store,
            is_active=True,
            deleted_at__isnull=True
        ).order_by('-created_at')[:8]
        
        # 디지털 파일 목록도 함께 가져오기 (최대 8개만)
        from file.models import DigitalFile
        digital_files = DigitalFile.objects.filter(
            store=store,
            is_active=True,
            deleted_at__isnull=True
        ).order_by('-created_at')[:8]
        
        return render(request, 'stores/store_detail.html', {
            'store': store,
            'products': products,
            'meetups': meetups,
            'live_lectures': live_lectures,
            'digital_files': digital_files,
        })
    else:
        # 비활성화된 스토어는 안내 페이지 표시
        return render(request, 'stores/store_inactive.html', {
            'store': store,
        }, status=503)  # Service Unavailable

# =========================
# 분리된 편집 기능들
# =========================

@login_required
def edit_basic_info(request, store_id):
    """기본 정보 편집"""
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
    
    if request.method == 'POST':
        store_name = request.POST.get('store_name', '').strip()
        store_description = request.POST.get('store_description', '').strip()
        owner_name = request.POST.get('owner_name', '').strip()
        owner_phone = request.POST.get('owner_phone', '').strip()
        owner_email = request.POST.get('owner_email', '').strip()
        business_license_number = request.POST.get('business_license_number', '').strip()
        telecommunication_sales_number = request.POST.get('telecommunication_sales_number', '').strip()
        chat_channel = request.POST.get('chat_channel', '').strip()
        
        # 유효성 검증
        if not store_name:
            messages.error(request, '스토어 이름을 입력해주세요.')
            return render(request, 'stores/edit_basic_info.html', {'store': store})
        
        if not owner_name:
            messages.error(request, '주인장 이름을 입력해주세요.')
            return render(request, 'stores/edit_basic_info.html', {'store': store})
        
        if not chat_channel:
            messages.error(request, '대화채널을 입력해주세요.')
            return render(request, 'stores/edit_basic_info.html', {'store': store})
        
        if not owner_phone and not owner_email:
            messages.error(request, '휴대전화 또는 이메일 중 하나는 반드시 입력해야 합니다.')
            return render(request, 'stores/edit_basic_info.html', {'store': store})
        
        # 업데이트
        store.store_name = store_name
        store.store_description = store_description
        store.owner_name = owner_name
        store.owner_phone = owner_phone
        store.owner_email = owner_email
        store.business_license_number = business_license_number
        store.telecommunication_sales_number = telecommunication_sales_number
        store.chat_channel = chat_channel
        store.save()
        
        return redirect('stores:my_stores')
    
    return render(request, 'stores/edit_basic_info.html', {
        'store': store,
    })

@login_required
def edit_api_settings(request, store_id):
    """블링크 API 설정 편집"""
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
    
    # 사이트 설정에서 블링크 API 문서 링크 가져오기
    from myshop.models import SiteSettings
    site_settings = SiteSettings.get_settings()
    
    # 기존 API 정보 확인
    has_existing_api_info = bool(store.blink_api_info_encrypted)
    has_existing_wallet_id = bool(store.blink_wallet_id_encrypted)
    
    # 기존 정보가 있으면 마스킹된 형태로 표시용 데이터 준비
    masked_api_info = ""
    masked_wallet_id = ""
    
    if has_existing_api_info:
        try:
            current_api_info = store.get_blink_api_info()
            if current_api_info and len(current_api_info) > 8:
                # API 키의 앞 4자리와 뒤 4자리만 보여주고 나머지는 마스킹
                masked_api_info = current_api_info[:4] + "*" * (len(current_api_info) - 8) + current_api_info[-4:]
            elif current_api_info:
                masked_api_info = "*" * len(current_api_info)
        except:
            masked_api_info = "****암호화된 정보****"
    
    if has_existing_wallet_id:
        try:
            current_wallet_id = store.get_blink_wallet_id()
            if current_wallet_id and len(current_wallet_id) > 8:
                # 월렛 ID의 앞 4자리와 뒤 4자리만 보여주고 나머지는 마스킹
                masked_wallet_id = current_wallet_id[:4] + "*" * (len(current_wallet_id) - 8) + current_wallet_id[-4:]
            elif current_wallet_id:
                masked_wallet_id = "*" * len(current_wallet_id)
        except:
            masked_wallet_id = "****암호화된 정보****"
    
    if request.method == 'POST':
        blink_api_info = request.POST.get('blink_api_info', '').strip()
        blink_wallet_id = request.POST.get('blink_wallet_id', '').strip()
        
        # 기존 정보가 있는 경우, 빈 값이면 기존 값 유지
        if has_existing_api_info and not blink_api_info:
            # API 정보가 비어있으면 기존 값 유지 (변경하지 않음)
            api_info_updated = False
        elif blink_api_info:
            # 새로운 API 정보가 입력되면 업데이트
            store.set_blink_api_info(blink_api_info)
            api_info_updated = True
        else:
            # 기존 정보도 없고 새로운 정보도 없으면 오류
            messages.error(request, '블링크 API 정보를 입력해주세요.')
            return render(request, 'stores/edit_api_settings.html', {
                'store': store,
                'has_existing_api_info': has_existing_api_info,
                'has_existing_wallet_id': has_existing_wallet_id,
                'masked_api_info': masked_api_info,
                'masked_wallet_id': masked_wallet_id,
                'blink_api_doc_url': site_settings.blink_api_doc_url,
            })
        
        if has_existing_wallet_id and not blink_wallet_id:
            # 월렛 ID가 비어있으면 기존 값 유지 (변경하지 않음)
            wallet_id_updated = False
        elif blink_wallet_id:
            # 새로운 월렛 ID가 입력되면 업데이트
            store.set_blink_wallet_id(blink_wallet_id)
            wallet_id_updated = True
        else:
            # 기존 정보도 없고 새로운 정보도 없으면 오류
            messages.error(request, '블링크 월렛 ID를 입력해주세요.')
            return render(request, 'stores/edit_api_settings.html', {
                'store': store,
                'has_existing_api_info': has_existing_api_info,
                'has_existing_wallet_id': has_existing_wallet_id,
                'masked_api_info': masked_api_info,
                'masked_wallet_id': masked_wallet_id,
                'blink_api_doc_url': site_settings.blink_api_doc_url,
            })
        
        # 저장
        store.save()
        
        # 업데이트된 정보에 따라 메시지 표시
        updated_items = []
        if api_info_updated:
            updated_items.append("API 키")
        if wallet_id_updated:
            updated_items.append("월렛 ID")
        
        if updated_items:
            message = f'{", ".join(updated_items)}이(가) 성공적으로 업데이트되었습니다.'
        else:
            message = 'API 설정 확인이 완료되었습니다. (변경사항 없음)'
        
        return redirect('stores:my_stores')
    
    return render(request, 'stores/edit_api_settings.html', {
        'store': store,
        'has_existing_api_info': has_existing_api_info,
        'has_existing_wallet_id': has_existing_wallet_id,
        'masked_api_info': masked_api_info,
        'masked_wallet_id': masked_wallet_id,
        'blink_api_doc_url': site_settings.blink_api_doc_url,
    })

@login_required
def edit_email_settings(request, store_id):
    """스토어 이메일 발송 설정 편집"""
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
    
    # 사이트 설정에서 Gmail 도움말 URL 가져오기
    from myshop.models import SiteSettings
    site_settings = SiteSettings.get_settings()
    
    # 기존 이메일 설정 확인
    has_existing_password = bool(store.email_host_password_encrypted)
    
    # 기존 비밀번호가 있으면 마스킹된 형태로 표시용 데이터 준비
    masked_password = ""
    if has_existing_password:
        try:
            current_password = store.get_email_host_password()
            if current_password and len(current_password) > 8:
                # 앱 비밀번호의 앞 4자리와 뒤 4자리만 보여주고 나머지는 마스킹
                masked_password = current_password[:4] + "*" * (len(current_password) - 8) + current_password[-4:]
            elif current_password:
                masked_password = "*" * len(current_password)
        except:
            masked_password = "****암호화된 정보****"
    
    if request.method == 'POST':
        email_enabled = request.POST.get('email_enabled') == '1'
        email_host_user = request.POST.get('email_host_user', '').strip()
        email_host_password = request.POST.get('email_host_password', '').strip()
        email_from_name = request.POST.get('email_from_name', '').strip()
        
        try:
            # 이메일 기능이 활성화된 경우 필수 필드 검증
            if email_enabled:
                if not email_host_user:
                    messages.error(request, 'Gmail 이메일 주소를 입력해주세요.')
                    return render(request, 'stores/edit_email_settings.html', {
                        'store': store,
                        'has_existing_password': has_existing_password,
                        'masked_password': masked_password,
                    })
                
                # 기존 비밀번호가 없고 새로운 비밀번호도 없으면 오류
                if not has_existing_password and not email_host_password:
                    messages.error(request, 'Gmail 앱 비밀번호를 입력해주세요.')
                    return render(request, 'stores/edit_email_settings.html', {
                        'store': store,
                        'has_existing_password': has_existing_password,
                        'masked_password': masked_password,
                    })
            
            # 설정 업데이트
            store.email_enabled = email_enabled
            store.email_host_user = email_host_user
            store.email_from_name = email_from_name
            
            # 비밀번호가 입력된 경우에만 업데이트
            if email_host_password:
                store.set_email_host_password(email_host_password)
            
            store.save()
            
            if email_enabled:
                messages.success(request, '이메일 발송 설정이 성공적으로 저장되었습니다.')
            else:
                messages.success(request, '이메일 발송 기능이 비활성화되었습니다.')
            
            return redirect('stores:my_stores')
            
        except Exception as e:
            messages.error(request, f'설정 저장 중 오류가 발생했습니다: {str(e)}')
    
    return render(request, 'stores/edit_email_settings.html', {
        'store': store,
        'has_existing_password': has_existing_password,
        'masked_password': masked_password,
        'gmail_help_url': site_settings.gmail_help_url,
    })

@login_required
@require_POST
def test_store_email(request, store_id):
    """스토어 이메일 설정 테스트"""
    import json
    from django.core.mail import EmailMessage
    from django.conf import settings
    
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
    
    try:
        # JSON 요청 파싱
        data = json.loads(request.body)
        test_email = data.get('test_email', '').strip()
        
        if not test_email:
            return JsonResponse({
                'success': False,
                'error': '테스트 이메일 주소를 입력해주세요.'
            })
        
        # 이메일 설정 확인
        if not store.email_enabled:
            return JsonResponse({
                'success': False,
                'error': '이메일 발송 기능이 비활성화되어 있습니다.'
            })
        
        if not store.email_host_user:
            return JsonResponse({
                'success': False,
                'error': 'Gmail 이메일 주소가 설정되지 않았습니다.'
            })
        
        if not store.email_host_password_encrypted:
            return JsonResponse({
                'success': False,
                'error': 'Gmail 앱 비밀번호가 설정되지 않았습니다.'
            })
        
        # 이메일 발송 테스트
        try:
            # Gmail SMTP 설정으로 이메일 전송
            from django.core.mail.backends.smtp import EmailBackend
            
            # 스토어별 SMTP 설정
            backend = EmailBackend(
                host='smtp.gmail.com',
                port=587,
                username=store.email_host_user,
                password=store.get_email_host_password(),
                use_tls=True,
                fail_silently=False,
            )
            
            # 테스트 이메일 작성
            subject = f'[{store.store_name}] 이메일 발송 테스트'
            message = f'''안녕하세요!

{store.store_name} 스토어의 이메일 발송 기능이 정상적으로 작동하고 있습니다.

이 메시지는 테스트 목적으로 발송되었습니다.

감사합니다.

---
{store.store_name}
주인장: {store.owner_name}
'''
            
            email = EmailMessage(
                subject=subject,
                body=message,
                from_email=f'{store.email_from_display} <{store.email_host_user}>',
                to=[test_email],
                connection=backend
            )
            
            email.send()
            
            return JsonResponse({
                'success': True,
                'message': f'{test_email}로 테스트 이메일이 성공적으로 전송되었습니다.'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'이메일 전송 실패: {str(e)}'
            })
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '잘못된 요청 형식입니다.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'테스트 중 오류가 발생했습니다: {str(e)}'
        })

@login_required
def edit_theme(request, store_id):
    """스토어 테마 설정 편집"""
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
    
    if request.method == 'POST':
        hero_color1 = request.POST.get('hero_color1', '#FF6B6B').strip()
        hero_color2 = request.POST.get('hero_color2', '#4ECDC4').strip()
        hero_text_color = request.POST.get('hero_text_color', '#FFFFFF').strip()
        
        # 업데이트
        store.hero_color1 = hero_color1
        store.hero_color2 = hero_color2
        store.hero_text_color = hero_text_color
        store.save()
        
        return redirect('stores:my_stores')
    
    return render(request, 'stores/edit_theme.html', {
        'store': store,
    })

@login_required
def edit_completion_message(request, store_id):
    """스토어 결제완료 안내 메시지 관리"""
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
    
    if request.method == 'POST':
        completion_message = request.POST.get('completion_message', '').strip()
        store.completion_message = completion_message
        store.save()
        
        messages.success(request, '결제완료 안내 메시지가 업데이트되었습니다.')
        return redirect('stores:edit_completion_message', store_id=store_id)
    
    context = {
        'store': store,
        'store_shipping': store.get_shipping_fee_display(),
    }
    
    return render(request, 'stores/edit_completion_message.html', context)



@login_required
def edit_shipping_settings(request, store_id):
    """스토어 배송비 설정"""
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)

    if request.method == 'POST':
        mode = request.POST.get('shipping_fee_mode', 'free')
        mode = mode if mode in dict(Store.SHIPPING_FEE_MODE_CHOICES) else 'free'

        shipping_fee_krw_input = request.POST.get('shipping_fee_krw', '').strip()
        threshold_krw_input = request.POST.get('free_shipping_threshold_krw', '').strip()

        shipping_fee_krw = 0
        shipping_fee_sats = 0
        threshold_krw = None
        threshold_sats = None

        if mode == 'flat':
            if not shipping_fee_krw_input:
                messages.error(request, '배송비를 원화로 입력해주세요.')
                return redirect('stores:edit_shipping_settings', store_id=store_id)

            try:
                shipping_fee_krw = int(shipping_fee_krw_input)
            except ValueError:
                messages.error(request, '배송비는 숫자로 입력해주세요.')
                return redirect('stores:edit_shipping_settings', store_id=store_id)

            if shipping_fee_krw < 0:
                messages.error(request, '배송비는 0 이상이어야 합니다.')
                return redirect('stores:edit_shipping_settings', store_id=store_id)

            shipping_fee_sats = UpbitExchangeService.convert_krw_to_sats(shipping_fee_krw)
            if shipping_fee_sats <= 0 and shipping_fee_krw > 0:
                messages.error(request, '환율 정보를 가져올 수 없어 배송비를 변환하지 못했습니다. 잠시 후 다시 시도해주세요.')
                return redirect('stores:edit_shipping_settings', store_id=store_id)

            if threshold_krw_input:
                try:
                    threshold_krw = int(threshold_krw_input)
                except ValueError:
                    messages.error(request, '무료 배송 기준 금액은 숫자로 입력해주세요.')
                    return redirect('stores:edit_shipping_settings', store_id=store_id)

                if threshold_krw <= 0:
                    messages.error(request, '무료 배송 기준 금액은 0보다 커야 합니다.')
                    return redirect('stores:edit_shipping_settings', store_id=store_id)

                if threshold_krw <= shipping_fee_krw:
                    messages.warning(request, '무료 배송 기준 금액이 배송비보다 낮거나 같으면 의미가 없을 수 있습니다.')

                threshold_sats = UpbitExchangeService.convert_krw_to_sats(threshold_krw)
                if threshold_sats <= 0:
                    messages.error(request, '환율 정보를 가져올 수 없어 무료 배송 기준을 변환하지 못했습니다. 잠시 후 다시 시도해주세요.')
                    return redirect('stores:edit_shipping_settings', store_id=store_id)

        store.set_shipping_fees(
            mode=mode,
            fee_krw=shipping_fee_krw,
            fee_sats=shipping_fee_sats,
            threshold_krw=threshold_krw,
            threshold_sats=threshold_sats,
        )
        store.save()

        messages.success(request, '배송비 설정이 업데이트되었습니다.')
        return redirect('stores:edit_shipping_settings', store_id=store_id)

    shipping_info = store.get_shipping_fee_display()
    converted_threshold_krw = shipping_info['threshold_krw']
    converted_threshold_sats = shipping_info['threshold_sats']

    if converted_threshold_krw is None and shipping_info['threshold_sats']:
        converted_threshold_krw = UpbitExchangeService.convert_sats_to_krw(shipping_info['threshold_sats'])
    if converted_threshold_sats is None and shipping_info['threshold_krw']:
        converted_threshold_sats = UpbitExchangeService.convert_krw_to_sats(shipping_info['threshold_krw'])

    context = {
        'store': store,
        'shipping_info': shipping_info,
        'threshold_preview': {
            'krw': converted_threshold_krw,
            'sats': converted_threshold_sats,
        },
    }

    return render(request, 'stores/edit_shipping_settings.html', context)

@login_required
def manage_store(request, store_id):
    """스토어 관리 (활성화/비활성화, 삭제 등)"""
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
    
    return render(request, 'stores/manage_store.html', {
        'store': store,
    })

@login_required
@require_POST
def toggle_store_status(request, store_id):
    """스토어 활성화/비활성화 토글"""
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
    
    is_active = request.POST.get('is_active') == 'on'
    store.is_active = is_active
    store.save()
    
    return redirect('stores:manage_store', store_id=store_id)

@login_required
@require_POST
def regenerate_qr(request, store_id):
    """QR 코드 재생성"""
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
    
    # QR 코드 재생성 로직
    store_url = f"{settings.SITE_URL}/stores/{store.store_id}/"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(store_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    qr_code_data = base64.b64encode(buffer.getvalue()).decode()
    
    store.qr_code = qr_code_data
    store.save()
    
    messages.success(request, 'QR 코드가 재생성되었습니다.')
    return redirect('stores:manage_store', store_id=store_id)

@login_required
@require_POST
def delete_store(request, store_id):
    """스토어 소프트 삭제"""
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
    
    store_name = store.store_name
    store.soft_delete()
    
    messages.success(request, f'"{store_name}" 스토어가 삭제되었습니다.')
    return redirect('stores:my_stores')

@login_required
@require_POST
def upload_image(request, store_id):
    """스토어 이미지 업로드"""
    try:
        store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
        
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
        
        # 스토어당 1장만 허용 - 기존 이미지가 있으면 삭제
        existing_images = store.images.all()
        if existing_images.exists():
            for existing_image in existing_images:
                # S3에서 파일 삭제
                try:
                    delete_file_from_s3(existing_image.file_path)
                except Exception as e:
                    logger.warning(f"S3 파일 삭제 실패: {e}")
                # DB에서 삭제
                existing_image.delete()
        
        # 이미지 업로드
        result = upload_store_image(image_file, store, request.user)
        
        if result['success']:
            store_image = result['store_image']
            return JsonResponse({
                'success': True,
                'image': {
                    'id': store_image.id,
                    'original_name': store_image.original_name,
                    'file_url': store_image.file_url,
                    'file_size': store_image.file_size,
                    'width': store_image.width,
                    'height': store_image.height,
                    'order': store_image.order,
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result['error']
            })
            
    except Exception as e:
        logger.error(f"이미지 업로드 오류: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': '이미지 업로드 중 오류가 발생했습니다.'
        })

@login_required
def delete_image(request, store_id, image_id):
    """스토어 이미지 삭제"""
    if request.method not in ['DELETE', 'POST']:
        return JsonResponse({
            'success': False,
            'error': 'DELETE 또는 POST 메서드만 허용됩니다.'
        })
    
    try:
        # 스토어 존재 확인
        try:
            store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
        except Http404:
            logger.warning(f"스토어를 찾을 수 없음: store_id={store_id}, user={request.user.username}")
            return JsonResponse({
                'success': False,
                'error': '스토어를 찾을 수 없습니다. 권한을 확인해주세요.'
            })
        
        # 이미지 존재 확인
        try:
            image = get_object_or_404(StoreImage, id=image_id, store=store)
        except Http404:
            logger.warning(f"이미지를 찾을 수 없음: image_id={image_id}, store={store.store_id}")
            return JsonResponse({
                'success': False,
                'error': '이미지를 찾을 수 없습니다.'
            })
        
        # DB에서 삭제 (시그널이 자동으로 S3 파일도 삭제함)
        image_name = image.original_name
        image.delete()
        
        logger.info(f"이미지 삭제 성공: {image_name} (store: {store.store_id})")
        
        return JsonResponse({
            'success': True,
            'message': '이미지가 삭제되었습니다.'
        })
        
    except Exception as e:
        logger.error(f"이미지 삭제 오류: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': '이미지 삭제 중 오류가 발생했습니다.'
        })

@login_required
@require_POST
def reorder_images(request, store_id):
    """스토어 이미지 순서 변경"""
    try:
        store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
        
        data = json.loads(request.body)
        image_orders = data.get('image_orders', [])
        
        if not image_orders:
            return JsonResponse({
                'success': False,
                'error': '이미지 순서 정보가 필요합니다.'
            })
        
        # 트랜잭션으로 순서 업데이트
        with transaction.atomic():
            for order_data in image_orders:
                image_id = order_data.get('id')
                new_order = order_data.get('order')
                
                if image_id and new_order is not None:
                    StoreImage.objects.filter(
                        id=image_id, 
                        store=store
                    ).update(order=new_order)
        
        return JsonResponse({
            'success': True,
            'message': '이미지 순서가 변경되었습니다.'
        })
        
    except Exception as e:
        logger.error(f"이미지 순서 변경 오류: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': '이미지 순서 변경 중 오류가 발생했습니다.'
        })


# =================================
# 상품 관리 관련 View
# =================================

@login_required
def product_list(request, store_id):
    """상품 목록"""
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
    # 관리자 뷰에서는 비활성화된 상품도 포함하여 표시
    products = store.products.all().order_by('-created_at')
    
    context = {
        'store': store,
        'products': products,
        'is_public_view': False,  # 스토어 주인장의 관리 뷰
    }
    return render(request, 'products/product_list.html', context)


@login_required
def add_product(request, store_id):
    """상품 추가"""
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # 상품 생성
                product = Product.objects.create(
                    store=store,
                    title=request.POST.get('title', '').strip(),
                    description=request.POST.get('description', '').strip(),
                    price=int(request.POST.get('price', 0)),
                    is_discounted=request.POST.get('is_discounted') == 'on',
                    discounted_price=int(request.POST.get('discounted_price', 0)) if request.POST.get('discounted_price') else None,
                    completion_message=request.POST.get('completion_message', '').strip(),
                    force_free_shipping=(
                        store.shipping_fee_mode == 'flat' and request.POST.get('force_free_shipping') == 'on'
                    ),
                )
                
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
                
                messages.success(request, '상품이 추가되었습니다.')
                return redirect('stores:product_list', store_id=store_id)
                
        except Exception as e:
            logger.error(f"상품 추가 오류: {e}", exc_info=True)
            messages.error(request, '상품 추가 중 오류가 발생했습니다.')
    
    context = {
        'store': store,
    }
    return render(request, 'stores/add_product.html', context)


@login_required
def edit_product(request, store_id, product_id):
    """상품 수정"""
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
    product = get_object_or_404(Product, id=product_id, store=store)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # 상품 업데이트
                product.title = request.POST.get('title', '').strip()
                product.description = request.POST.get('description', '').strip()
                product.price = int(request.POST.get('price', 0))
                product.is_discounted = request.POST.get('is_discounted') == 'on'
                product.discounted_price = int(request.POST.get('discounted_price', 0)) if request.POST.get('discounted_price') else None
                product.shipping_fee = 0
                product.shipping_fee_krw = None
                product.force_free_shipping = (
                    store.shipping_fee_mode == 'flat' and request.POST.get('force_free_shipping') == 'on'
                )
                product.completion_message = request.POST.get('completion_message', '').strip()
                product.save()
                
                # 기존 옵션 삭제 후 새로 추가
                product.options.all().delete()
                
                options_data = json.loads(request.POST.get('options', '[]'))
                for option_data in options_data:
                    if option_data.get('name'):
                        option = ProductOption.objects.create(
                            product=product,
                            name=option_data['name'],
                            order=option_data.get('order', 0)
                        )
                        
                        for choice_data in option_data.get('choices', []):
                            if choice_data.get('name'):
                                ProductOptionChoice.objects.create(
                                    option=option,
                                    name=choice_data['name'],
                                    price=choice_data.get('price', 0),
                                    order=choice_data.get('order', 0)
                                )
                
                messages.success(request, '상품이 수정되었습니다.')
                return redirect('stores:product_list', store_id=store_id)
                
        except Exception as e:
            logger.error(f"상품 수정 오류: {e}", exc_info=True)
            messages.error(request, '상품 수정 중 오류가 발생했습니다.')
    
    # 기존 옵션 데이터 준비
    options_data = []
    for option in product.options.all().order_by('order'):
        choices_data = []
        for choice in option.choices.all().order_by('order'):
            choices_data.append({
                'name': choice.name,
                'price': choice.price,
                'order': choice.order
            })
        options_data.append({
            'name': option.name,
            'order': option.order,
            'choices': choices_data
        })
    
    context = {
        'store': store,
        'product': product,
        'options_data': json.dumps(options_data),
        'store_shipping': store.get_shipping_fee_display(),
    }
    return render(request, 'stores/edit_product.html', context)


@login_required
@require_POST
def delete_product(request, store_id, product_id):
    """상품 삭제"""
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
    product = get_object_or_404(Product, id=product_id, store=store)
    
    product_title = product.title
    product.is_active = False
    product.save()
    
    messages.success(request, f'"{product_title}" 상품이 비활성화되었습니다.')
    return redirect('stores:product_list', store_id=store_id)


@login_required
@require_POST
def upload_product_image(request, store_id, product_id):
    """상품 이미지 업로드"""
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
        
        # 이미지 업로드 처리 (스토어 이미지 업로드 함수 재사용)
        # TODO: 별도의 상품 이미지 업로드 함수 구현 필요
        result = upload_store_image(image_file, store, request.user)
        
        if result['success']:
            # StoreImage를 ProductImage로 변환
            store_image = result['store_image']
            product_image = ProductImage.objects.create(
                product=product,
                original_name=store_image.original_name,
                file_path=store_image.file_path,
                file_url=store_image.file_url,
                file_size=store_image.file_size,
                width=500,  # 1:1 비율로 리사이즈
                height=500,
                order=current_count,
                uploaded_by=request.user
            )
            
            # 임시로 생성된 StoreImage 삭제
            store_image.delete()
            
            return JsonResponse({
                'success': True,
                'image': {
                    'id': product_image.id,
                    'original_name': product_image.original_name,
                    'file_url': product_image.file_url,
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
def delete_product_image(request, store_id, product_id, image_id):
    """상품 이미지 삭제"""
    if request.method != 'DELETE':
        return JsonResponse({
            'success': False,
            'error': 'DELETE 메서드만 허용됩니다.'
        })
    
    try:
        store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
        product = get_object_or_404(Product, id=product_id, store=store)
        image = get_object_or_404(ProductImage, id=image_id, product=product)
        
        image_name = image.original_name
        image.delete()
        
        return JsonResponse({
            'success': True,
            'message': '이미지가 삭제되었습니다.'
        })
        
    except Exception as e:
        logger.error(f"상품 이미지 삭제 오류: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': '이미지 삭제 중 오류가 발생했습니다.'
        })


# =================================
# 장바구니 관련 View
# =================================

def cart_view(request):
    """장바구니 보기 (CartService 사용)"""
    # orders 앱의 cart_view로 리다이렉트 (중복 제거)
    return redirect('orders:cart_view')


@require_POST
def add_to_cart(request):
    """장바구니에 상품 추가 (CartService 사용)"""
    # orders 앱의 add_to_cart로 리다이렉트 (중복 제거)
    from orders.views import add_to_cart as orders_add_to_cart
    return orders_add_to_cart(request)


@require_POST
def remove_from_cart(request, item_id):
    """장바구니에서 상품 제거 (CartService 사용)"""
    # orders 앱의 remove_from_cart로 리다이렉트 (중복 제거)
    from orders.views import remove_from_cart as orders_remove_from_cart
    return orders_remove_from_cart(request, item_id)


@require_POST
def update_cart_item(request, item_id):
    """장바구니 상품 수량 업데이트 (CartService 사용)"""
    # orders 앱의 update_cart_item로 리다이렉트 (중복 제거)
    from orders.views import update_cart_item as orders_update_cart_item
    return orders_update_cart_item(request, item_id)


# =================================
# 주문 관련 View
# =================================

@login_required
def checkout_step1(request):
    """주문 1단계: 주문자 정보 입력"""
    cart = get_object_or_404(Cart, user=request.user)
    
    if not cart.items.exists():
        messages.warning(request, '장바구니가 비어있습니다.')
        return redirect('stores:cart_view')
    
    if request.method == 'POST':
        # 주문자 정보를 세션에 저장
        order_data = {
            'buyer_name': request.POST.get('buyer_name', '').strip(),
            'buyer_phone': request.POST.get('buyer_phone', '').strip(),
            'buyer_email': request.POST.get('buyer_email', '').strip(),
            'shipping_postal_code': request.POST.get('shipping_postal_code', '').strip(),
            'shipping_address': request.POST.get('shipping_address', '').strip(),
            'shipping_detail_address': request.POST.get('shipping_detail_address', '').strip(),
            'order_memo': request.POST.get('order_memo', '').strip(),
        }
        
        # 필수 필드 검증
        required_fields = ['buyer_name', 'buyer_phone', 'buyer_email', 'shipping_postal_code', 'shipping_address']
        for field in required_fields:
            if not order_data[field]:
                messages.error(request, '필수 정보를 모두 입력해주세요.')
                return render(request, 'stores/checkout_step1.html', {
                    'cart': cart,
                    'form_data': order_data
                })
        
        request.session['order_data'] = order_data
        return redirect('stores:checkout_step2')
    
    context = {
        'cart': cart,
        'cart_items': cart.items.all().select_related('product', 'product__store'),
    }
    return render(request, 'stores/checkout_step1.html', context)


@login_required
def checkout_step2(request):
    """주문 2단계: 주문 상품 내역 확인"""
    if 'order_data' not in request.session:
        return redirect('stores:checkout_step1')
    
    cart = get_object_or_404(Cart, user=request.user)
    order_data = request.session['order_data']
    
    if request.method == 'POST':
        return redirect('stores:checkout_step3')
    
    context = {
        'cart': cart,
        'cart_items': cart.items.all().select_related('product', 'product__store'),
        'order_data': order_data,
    }
    return render(request, 'stores/checkout_step2.html', context)


@login_required
def checkout_step3(request):
    """주문 3단계: 인보이스 생성 및 결제"""
    if 'order_data' not in request.session:
        return redirect('stores:checkout_step1')
    
    cart = get_object_or_404(Cart, user=request.user)
    order_data = request.session['order_data']
    
    try:
        with transaction.atomic():
            # 주문 생성
            # 스토어별로 주문을 분리해서 생성
            stores_orders = {}
            
            for item in cart.items.all():
                store = item.product.store
                if store.id not in stores_orders:
                    # 새 주문 생성
                    order = Order.objects.create(
                        user=request.user,
                        store=store,
                        buyer_name=order_data['buyer_name'],
                        buyer_phone=order_data['buyer_phone'],
                        buyer_email=order_data['buyer_email'],
                        shipping_postal_code=order_data['shipping_postal_code'],
                        shipping_address=order_data['shipping_address'],
                        shipping_detail_address=order_data['shipping_detail_address'],
                        order_memo=order_data['order_memo'],
                        subtotal=0,  # 나중에 계산
                        shipping_fee=0,
                        total_amount=0,  # 나중에 계산
                        status='payment_pending'
                    )
                    stores_orders[store.id] = order
                
                order = stores_orders[store.id]
                
                # 주문 아이템 생성
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    product_title=item.product.title,
                    product_price=item.product.final_price,
                    quantity=item.quantity,
                    selected_options=item.selected_options,  # 옵션명:선택지명 형태로 변환 필요
                    options_price=item.options_price
                )
            
            # 각 주문의 총액 계산
            for order in stores_orders.values():
                order.subtotal = sum(item.total_price for item in order.items.all())
                order.shipping_fee = order.store.get_shipping_fee_sats(order.subtotal)
                order.total_amount = order.subtotal + order.shipping_fee
                order.save()
            
            # 첫 번째 주문으로 리다이렉트 (여러 주문이 있을 경우 향후 개선 필요)
            first_order = list(stores_orders.values())[0]
            
            # 결제 처리 (블링크 API 연동)
            # TODO: 실제 결제 처리 구현
            
            # 임시로 결제 완료 처리
            first_order.status = 'paid'
            first_order.paid_at = timezone.now()
            first_order.save()
            
            # 구매 내역 생성
            PurchaseHistory.objects.create(
                user=request.user,
                order=first_order,
                store_name=first_order.store.store_name,
                total_amount=first_order.total_amount,
                purchase_date=first_order.paid_at
            )
            
            # 장바구니 비우기
            cart.items.all().delete()
            
            # 세션 정리
            del request.session['order_data']
            
            return redirect('stores:checkout_complete', order_number=first_order.order_number)
    
    except Exception as e:
        logger.error(f"주문 생성 오류: {e}", exc_info=True)
        messages.error(request, '주문 처리 중 오류가 발생했습니다.')
        return redirect('stores:checkout_step1')
    
    context = {
        'cart': cart,
        'cart_items': cart.items.all().select_related('product', 'product__store'),
        'order_data': order_data,
    }
    return render(request, 'stores/checkout_step3.html', context)


@login_required
def checkout_complete(request, order_number):
    """주문 4단계: 결제 완료"""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    context = {
        'order': order,
        'order_items': order.items.all(),
    }
    return render(request, 'stores/checkout_complete.html', context)








# =================================
# 상품 상세 페이지
# =================================

def product_detail(request, store_id, product_id):
    """상품 상세 페이지"""
    try:
        store = Store.objects.get(store_id=store_id, deleted_at__isnull=True, is_active=True)
    except Store.DoesNotExist:
        # 스토어가 존재하지 않거나 비활성화된 경우
        return render(request, 'stores/store_not_found.html', {
            'store_id': store_id,
        }, status=404)
    
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

    reviews_page_number = request.GET.get('page') or 1
    review_context = get_paginated_reviews(product, reviews_page_number)
    reviews_page = review_context['reviews_page']

    can_write_review = False
    if request.user.is_authenticated:
        can_write_review = user_has_purchased_product(request.user, product)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' and request.GET.get('fragment') == 'reviews':
        navigation = build_reviews_url(store.store_id, product.id, reviews_page.number)
        html = render_to_string(
            'products/partials/reviews_content.html',
            {
                'store': store,
                'product': product,
                **review_context,
            },
            request=request,
        )
        return JsonResponse(
            {
                'html': html,
                'page': navigation['page'],
                'url': navigation['path'],
                'anchor': navigation['anchor'],
            }
        )

    context = {
        'store': store,
        'product': product,
        'product_images': product.images.all().order_by('order'),
        'product_options': product.options.all().order_by('order').prefetch_related('choices'),
        'cart_items_count': cart_items_count,
        'cart_total_amount': cart_total_amount,
        'cart_items': cart_items,
        'store_shipping': store_shipping,
        'product_shipping': product_shipping,
        **review_context,
        'can_write_review': can_write_review,
        'max_review_images': MAX_IMAGES_PER_REVIEW,
    }
    return render(request, 'products/product_detail.html', context)
