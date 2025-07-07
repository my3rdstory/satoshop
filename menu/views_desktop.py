# 데스크톱용 메뉴판 뷰들

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.db import transaction
from stores.models import Store
from .models import Menu, MenuCategory, MenuOrder, MenuOrderItem
import logging
import json
from django.utils import timezone

logger = logging.getLogger(__name__)


def menu_board_desktop(request, store_id):
    """데스크톱용 메뉴판"""
    store = get_object_or_404(Store, store_id=store_id, is_active=True)
    
    # 활성화된 메뉴들과 카테고리 가져오기
    categories = MenuCategory.objects.filter(store=store).order_by('order', 'id')
    menus = Menu.objects.filter(
        store=store, 
        is_active=True
    ).prefetch_related('categories').order_by('created_at')
    
    context = {
        'store': store,
        'categories': categories,
        'menus': menus,
        'store_id': store_id,
        'current_url': request.build_absolute_uri(),
    }
    
    return render(request, 'menu/menu_board_desktop.html', context)


def menu_detail_desktop(request, store_id, menu_id):
    """데스크톱용 메뉴 상세 페이지"""
    store = get_object_or_404(Store, store_id=store_id, is_active=True)
    menu = get_object_or_404(Menu, id=menu_id, store=store, is_active=True)
    
    context = {
        'store': store,
        'menu': menu,
        'store_id': store_id,
        'current_url': request.build_absolute_uri(),
    }
    
    return render(request, 'menu/menu_detail_desktop.html', context)


def menu_detail_ajax_desktop(request, store_id, menu_id):
    """데스크톱용 메뉴 상세 정보 AJAX"""
    try:
        store = get_object_or_404(Store, store_id=store_id, is_active=True)
        menu = get_object_or_404(Menu, id=menu_id, store=store, is_active=True)
        
        # 활성화된 카테고리들 가져오기
        categories = MenuCategory.objects.filter(store=store).order_by('order', 'id')
        
        context = {
            'store': store,
            'menu': menu,
            'categories': categories,
            'store_id': store_id,
            'is_ajax': True,
            'current_url': request.build_absolute_uri(),
        }
        
        return render(request, 'menu/menu_detail_desktop.html', context)
        
    except Exception as e:
        logger.error(f"데스크톱 메뉴 상세 정보 로드 오류: {str(e)}")
        return render(request, 'menu/menu_error.html', {'error': '메뉴 정보를 불러올 수 없습니다.'})


def menu_cart_desktop(request, store_id):
    """데스크톱용 메뉴 장바구니 페이지"""
    store = get_object_or_404(Store, store_id=store_id, is_active=True)
    
    context = {
        'store': store,
        'store_id': store_id,
        'current_url': request.build_absolute_uri(),
    }
    
    return render(request, 'menu/menu_cart_desktop.html', context)


@csrf_exempt
@require_POST
def create_cart_invoice_desktop(request, store_id):
    """데스크톱용 장바구니 결제 인보이스 생성"""
    try:
        # 스토어 조회 (비회원도 접근 가능)
        store = get_object_or_404(Store, store_id=store_id, is_active=True)
        
        # 요청 본문 파싱
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            return JsonResponse({'success': False, 'error': f'JSON 파싱 오류: {str(e)}'}, status=400)
        
        cart_items = data.get('cart_items', [])
        if not cart_items:
            return JsonResponse({'success': False, 'error': '장바구니가 비어있습니다.'}, status=400)
        
        # 디버깅을 위한 로그
        logger.debug(f"[DESKTOP] 장바구니 결제 요청 - 스토어: {store.store_name}, 아이템 수: {len(cart_items)}")
        
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
                
                menu_id = menu_id_raw.split('_')[0] if isinstance(menu_id_raw, str) and '_' in menu_id_raw else menu_id_raw
                menu_id = int(menu_id)
                menu = Menu.objects.get(id=menu_id, store=store, is_active=True)
                
                # 수량 검증
                quantity = int(item.get('quantity', 1))
                if quantity <= 0:
                    return JsonResponse({'success': False, 'error': '수량은 1개 이상이어야 합니다.'}, status=400)
                
                # 메뉴 가격 계산
                menu_price = menu.public_discounted_price if menu.is_discounted else menu.public_price
                item_total_price = item.get('totalPrice', menu_price)
                if isinstance(item_total_price, str):
                    item_total_price = int(float(item_total_price))
                
                validated_items.append({
                    'menu': menu,
                    'menu_name': menu.name,
                    'menu_price': menu_price,
                    'quantity': quantity,
                    'selected_options': item.get('options', {}),
                    'options_price': 0,
                    'total_price': item_total_price * quantity
                })
                
                total_amount += item_total_price * quantity
                memo_items.append(f"{menu.name} x{quantity}")
                
            except (Menu.DoesNotExist, ValueError) as e:
                return JsonResponse({'success': False, 'error': f'메뉴 데이터 오류: {str(e)}'}, status=400)
        
        # 가격이 0인 경우도 허용 (음수이거나 NaN인 경우만 차단)
        if total_amount < 0 or total_amount != total_amount:
            return JsonResponse({'success': False, 'error': '결제 금액이 올바르지 않습니다.'}, status=400)
        
        # 메모 생성
        memo = ', '.join(memo_items[:3])
        if len(memo_items) > 3:
            memo += f' 외 {len(memo_items) - 3}개'
        
        # BlinkAPIService 초기화
        try:
            from ln_payment.blink_service import get_blink_service_for_store
            blink_service = get_blink_service_for_store(store)
        except Exception as e:
            logger.error(f"[DESKTOP] BlinkAPIService 초기화 실패: {str(e)}")
            return JsonResponse({'success': False, 'error': f'결제 서비스 초기화 실패: {str(e)}'}, status=500)
        
        # 인보이스 생성
        result = blink_service.create_invoice(
            amount_sats=int(total_amount),
            memo=memo,
            expires_in_minutes=15
        )
        
        if not result['success']:
            return JsonResponse({'success': False, 'error': result['error']}, status=500)
        
        # 메뉴 주문 생성
        with transaction.atomic():
            # 🛡️ 기존 pending 상태의 주문 초기화 (재생성 대비)
            try:
                if request.user.is_authenticated:
                    # 로그인된 사용자의 기존 pending 주문 취소
                    user_id = request.user.id
                    existing_orders = MenuOrder.objects.filter(
                        store=store,
                        status__in=['pending', 'payment_pending'],
                        customer_info__user_id=user_id
                    )
                else:
                    # 비로그인 사용자의 경우 IP 기반으로 처리
                    ip_address = request.META.get('REMOTE_ADDR', '')
                    from datetime import timedelta
                    cutoff_time = timezone.now() - timedelta(hours=1)  # 1시간 이전 것들 정리
                    existing_orders = MenuOrder.objects.filter(
                        store=store,
                        status__in=['pending', 'payment_pending'],
                        customer_info__ip_address=ip_address,
                        created_at__lt=cutoff_time
                    ) if ip_address else MenuOrder.objects.none()
                
                if existing_orders.exists():
                    existing_orders.update(status='cancelled')
                    logger.debug(f"[DESKTOP] 기존 pending 주문 {existing_orders.count()}개 취소됨")
                    
            except Exception as e:
                logger.warning(f"[DESKTOP] 기존 주문 정리 실패: {str(e)}")
                # 실패해도 계속 진행
            
            menu_order = MenuOrder.objects.create(
                store=store,
                status='payment_pending',
                total_amount=total_amount,
                payment_hash=result['payment_hash'],
                customer_info={
                    'user_id': request.user.id if request.user.is_authenticated else None,
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'ip_address': request.META.get('REMOTE_ADDR', ''),
                    'created_via': 'menu_board_desktop'
                }
            )
            
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
        
        response_data = {
            'success': True,
            'payment_hash': result['payment_hash'],
            'invoice': result['invoice'],
            'amount': total_amount,
            'memo': memo,
            'expires_at': result['expires_at'].isoformat() if result.get('expires_at') else None,
        }
        
        logger.debug(f"[DESKTOP] 인보이스 생성 성공")
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"[DESKTOP] 장바구니 인보이스 생성 오류: {str(e)}")
        return JsonResponse({'success': False, 'error': f'인보이스 생성 중 오류가 발생했습니다: {str(e)}'}, status=500) 