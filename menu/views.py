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
import builtins

# 각 기기별 전용 뷰 모듈 import
from . import views_common
from . import views_desktop  
from . import views_mobile

logger = logging.getLogger(__name__)

def is_mobile_device(request):
    """모바일 기기 감지 함수 (강화된 버전)"""
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    
    # 디버깅 로그 추가
    logger.info(f"[모바일감지] User-Agent: {user_agent}")
    
    # 모바일 키워드 확장
    mobile_keywords = [
        'mobile', 'android', 'iphone', 'ipad', 'ipod', 'blackberry', 'webos',
        'nokia', 'samsung', 'htc', 'motorola', 'opera mini', 'opera mobi',
        'iemobile', 'windows phone', 'windows mobile', 'palm', 'symbian',
        'phone', 'tablet', 'fennec', 'firefox mobile', 'mobile safari'
    ]
    
    # 특정 모바일 브라우저 패턴
    mobile_patterns = [
        'mobi', 'mobile', 'android', 'iphone', 'ipad', 'ipod',
        'windows phone', 'blackberry', 'webos', 'opera m',
        'phone', 'tablet', 'silk/', 'kindle'
    ]
    
    # 키워드 기반 검사
    for keyword in mobile_keywords:
        if keyword in user_agent:
            logger.info(f"[모바일감지] 키워드 매치: {keyword} -> MOBILE")
            return True
    
    # 패턴 기반 검사
    for pattern in mobile_patterns:
        if pattern in user_agent:
            logger.info(f"[모바일감지] 패턴 매치: {pattern} -> MOBILE")
            return True
    
    # 화면 크기 기반 검사 (HTTP_SEC_CH_UA_MOBILE 헤더)
    mobile_hint = request.META.get('HTTP_SEC_CH_UA_MOBILE')
    if mobile_hint == '?1':
        logger.info(f"[모바일감지] 모바일 힌트 헤더 매치 -> MOBILE")
        return True
    
    # 모바일 뷰포트 힌트 검사
    viewport_width = request.META.get('HTTP_SEC_CH_VIEWPORT_WIDTH')
    if viewport_width and viewport_width.isdigit() and int(viewport_width) <= 768:
        logger.info(f"[모바일감지] 뷰포트 너비 매치: {viewport_width} -> MOBILE")
        return True
    
    logger.info(f"[모바일감지] 매치 없음 -> DESKTOP")
    return False

# === 공통 뷰들 (관리자용) ===
# 공통 뷰들을 그대로 노출
get_store_or_404 = views_common.get_store_or_404
menu_list = views_common.menu_list
add_menu = views_common.add_menu
edit_menu = views_common.edit_menu
upload_menu_image = views_common.upload_menu_image
category_manage = views_common.category_manage
category_list_api = views_common.category_list_api
category_create_api = views_common.category_create_api
category_update_api = views_common.category_update_api
category_delete_api = views_common.category_delete_api
category_reorder_api = views_common.category_reorder_api
toggle_temporary_out_of_stock = views_common.toggle_temporary_out_of_stock
toggle_menu_active = views_common.toggle_menu_active
manage_menu = views_common.manage_menu
delete_menu = views_common.delete_menu
menu_orders = views_common.menu_orders
menu_orders_detail = views_common.menu_orders_detail


# === 기기별 분기 뷰들 ===

def menu_board_auto_redirect(request, store_id):
    """기기 감지 후 적절한 메뉴판으로 리다이렉트"""
    if is_mobile_device(request):
        return redirect('menu:menu_board_mobile', store_id=store_id)
    else:
        return redirect('menu:menu_board_desktop', store_id=store_id)


def menu_board(request, store_id):
    """기기 감지 후 적절한 메뉴판 표시 (구버전 호환)"""
    if is_mobile_device(request):
        return views_mobile.menu_board_mobile(request, store_id)
    else:
        return views_desktop.menu_board_desktop(request, store_id)


def menu_cart(request, store_id):
    """기기 감지 후 적절한 장바구니 표시 (구버전 호환)"""
    if is_mobile_device(request):
        return views_mobile.menu_cart_mobile(request, store_id)
    else:
        return views_desktop.menu_cart_desktop(request, store_id)


def menu_detail(request, store_id, menu_id):
    """기기 감지 후 적절한 메뉴 상세 표시 (구버전 호환)"""
    if is_mobile_device(request):
        return views_mobile.menu_detail_mobile(request, store_id, menu_id)
    else:
        return views_desktop.menu_detail_desktop(request, store_id, menu_id)


def menu_detail_ajax(request, store_id, menu_id):
    """기기 감지 후 적절한 메뉴 상세 AJAX API (구버전 호환)"""
    if is_mobile_device(request):
        return views_mobile.menu_detail_ajax_mobile(request, store_id, menu_id)
    else:
        return views_desktop.menu_detail_ajax_desktop(request, store_id, menu_id)


# === 데스크톱 전용 뷰들 ===
menu_board_desktop = views_desktop.menu_board_desktop
menu_detail_desktop = views_desktop.menu_detail_desktop
menu_detail_ajax_desktop = views_desktop.menu_detail_ajax_desktop
menu_cart_desktop = views_desktop.menu_cart_desktop
create_cart_invoice_desktop = views_desktop.create_cart_invoice_desktop


# === 모바일 전용 뷰들 ===
menu_board_mobile = views_mobile.menu_board_mobile
menu_detail_mobile = views_mobile.menu_detail_mobile
menu_detail_ajax_mobile = views_mobile.menu_detail_ajax_mobile
menu_cart_mobile = views_mobile.menu_cart_mobile
create_cart_invoice_mobile = views_mobile.create_cart_invoice_mobile


# === 기존 공통 API (하위 호환성) ===
@csrf_exempt
@require_POST
def create_cart_invoice(request, store_id):
    """기기 감지 후 적절한 결제 인보이스 생성 API (구버전 호환)"""
    if is_mobile_device(request):
        return views_mobile.create_cart_invoice_mobile(request, store_id)
    else:
        return views_desktop.create_cart_invoice_desktop(request, store_id)


@csrf_exempt
@require_POST
def check_cart_payment(request, store_id):
    """결제 상태 확인 (공통)"""
    try:
        import json
        from .models import MenuOrder
        from django.db import transaction
        
        logger.info(f"[결제상태체크] 요청 시작 - Store ID: {store_id}")
        
        # 스토어 조회 (비회원도 접근 가능)
        store = get_object_or_404(Store, store_id=store_id, is_active=True)
        logger.info(f"[결제상태체크] 스토어 조회 성공: {store.store_name}")
        
        # 요청 본문 파싱
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            logger.error(f"[결제상태체크] JSON 파싱 오류: {str(e)}")
            return JsonResponse({'success': False, 'error': f'JSON 파싱 오류: {str(e)}'}, status=400)
        
        payment_hash = data.get('payment_hash')
        if not payment_hash:
            logger.error(f"[결제상태체크] payment_hash 누락")
            return JsonResponse({'success': False, 'error': 'payment_hash가 필요합니다.'}, status=400)
        
        logger.info(f"[결제상태체크] Payment Hash: {payment_hash}")
        
        # 🛡️ 이미 결제 완료된 주문이 있는지 먼저 확인 (중복 이메일 발송 방지)
        try:
            menu_order = MenuOrder.objects.get(payment_hash=payment_hash, store=store)
            logger.info(f"[결제상태체크] 주문 조회 성공 - 주문번호: {menu_order.order_number}, 현재 상태: {menu_order.status}")
            
            if menu_order.status == 'paid' and menu_order.paid_at:
                logger.info(f"[결제상태체크] 이미 결제 완료된 주문: {menu_order.order_number}")
                return JsonResponse({
                    'success': True,
                    'status': 'paid',
                    'order_status': menu_order.status
                })
        except MenuOrder.DoesNotExist:
            logger.error(f"[결제상태체크] 주문을 찾을 수 없음 - Payment Hash: {payment_hash}, Store: {store.store_id}")
            return JsonResponse({'success': False, 'error': '주문을 찾을 수 없습니다.'}, status=404)
        
        # BlinkAPIService로 결제 상태 확인
        try:
            from ln_payment.blink_service import get_blink_service_for_store
            
            # 스토어의 Blink API 정보 먼저 확인
            logger.info(f"[결제상태체크] 스토어 Blink API 정보 확인 시작...")
            api_key = store.get_blink_api_info()
            wallet_id = store.get_blink_wallet_id()
            
            logger.info(f"[결제상태체크] API 키 길이: {len(api_key) if api_key else 0}")
            logger.info(f"[결제상태체크] 월렛 ID: {wallet_id[:8] + '...' if wallet_id and len(wallet_id) > 8 else wallet_id}")
            
            if not api_key:
                logger.error(f"[결제상태체크] 스토어에 API 키가 설정되지 않았습니다.")
                return JsonResponse({'success': False, 'error': '스토어에 Blink API 키가 설정되지 않았습니다.'})
            
            if not wallet_id:
                logger.error(f"[결제상태체크] 스토어에 월렛 ID가 설정되지 않았습니다.")
                return JsonResponse({'success': False, 'error': '스토어에 Blink 월렛 ID가 설정되지 않았습니다.'})
            
            blink_service = get_blink_service_for_store(store)
            logger.info(f"[결제상태체크] BlinkAPIService 초기화 성공")
            
            result = blink_service.check_invoice_status(payment_hash)
            logger.info(f"[결제상태체크] Blink API 결과: {result}")
            
            if result['success']:
                if result['status'] == 'paid' and menu_order.status != 'paid':
                    # 🛡️ 트랜잭션 및 select_for_update로 동시성 문제 방지
                    try:
                        with transaction.atomic():
                            menu_order_locked = MenuOrder.objects.select_for_update().get(
                                id=menu_order.id,
                                payment_hash=payment_hash,
                                store=store
                            )
                            
                            # 다시 한 번 상태 확인 (트랜잭션 내에서)
                            if menu_order_locked.status == 'paid':
                                logger.info(f"[결제상태체크] 이미 처리된 주문: {menu_order_locked.order_number}")
                                return JsonResponse({
                                    'success': True,
                                    'status': result['status'],
                                    'order_status': menu_order_locked.status,
                                    'order_number': menu_order_locked.order_number
                                })
                            
                            # 결제 완료 처리: 주문번호 생성 및 상태 업데이트
                            logger.info(f"[결제상태체크] 결제 완료 - 주문번호 생성 및 상태 업데이트 중...")
                            
                            # 주문번호 생성 (아직 없는 경우에만)
                            if not menu_order_locked.order_number:
                                menu_order_locked.order_number = menu_order_locked.generate_order_number()
                            
                            menu_order_locked.status = 'paid'
                            menu_order_locked.paid_at = timezone.now()
                            menu_order_locked.save()
                            
                            logger.info(f"[결제상태체크] 주문 완료 - 주문번호: {menu_order_locked.order_number}")
                            
                    except MenuOrder.DoesNotExist:
                        logger.error(f"[결제상태체크] 주문 락 획득 실패: {payment_hash}")
                        return JsonResponse({'success': False, 'error': '주문 처리 중 오류가 발생했습니다.'})
                
                response_data = {
                    'success': True,
                    'status': result['status'],
                    'order_status': menu_order.status
                }
                
                # 결제 완료 시 주문번호 포함
                if menu_order.status == 'paid' and menu_order.order_number:
                    response_data['order_number'] = menu_order.order_number
                
                logger.info(f"[결제상태체크] 응답 데이터: {response_data}")
                return JsonResponse(response_data)
            else:
                logger.error(f"[결제상태체크] Blink API 오류: {result['error']}")
                return JsonResponse({'success': False, 'error': result['error']})
                
        except Exception as e:
            logger.error(f"[결제상태체크] Blink API 서비스 오류: {str(e)}")
            import traceback
            logger.error(f"[결제상태체크] 스택 트레이스: {traceback.format_exc()}")
            return JsonResponse({'success': False, 'error': '결제 상태 확인 중 오류가 발생했습니다.'})
        
    except Exception as e:
        logger.error(f"[결제상태체크] 전체 오류: {str(e)}")
        return JsonResponse({'success': False, 'error': f'요청 처리 중 오류가 발생했습니다: {str(e)}'}, status=500)


@csrf_exempt
@require_POST
def cancel_menu_invoice(request, store_id):
    """메뉴 인보이스 취소"""
    try:
        import json
        from .models import MenuOrder
        from django.db import transaction
        
        logger.info(f"[메뉴취소] 요청 시작 - Store ID: {store_id}")
        
        # 스토어 조회 (비회원도 접근 가능)
        store = get_object_or_404(Store, store_id=store_id, is_active=True)
        logger.info(f"[메뉴취소] 스토어 조회 성공: {store.store_name}")
        
        # 요청 본문 파싱
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            logger.error(f"[메뉴취소] JSON 파싱 오류: {str(e)}")
            return JsonResponse({'success': False, 'error': f'JSON 파싱 오류: {str(e)}'}, status=400)
        
        payment_hash = data.get('payment_hash')
        if not payment_hash:
            logger.error(f"[메뉴취소] payment_hash 누락")
            return JsonResponse({'success': False, 'error': 'payment_hash가 필요합니다.'}, status=400)
        
        logger.info(f"[메뉴취소] Payment Hash: {payment_hash}")
        
        # 메뉴 주문 조회
        try:
            menu_order = MenuOrder.objects.get(payment_hash=payment_hash, store=store)
            logger.info(f"[메뉴취소] 주문 조회 성공 - 주문번호: {menu_order.order_number}, 현재 상태: {menu_order.status}")
        except MenuOrder.DoesNotExist:
            logger.error(f"[메뉴취소] 주문을 찾을 수 없음 - Payment Hash: {payment_hash}, Store: {store.store_id}")
            return JsonResponse({'success': False, 'error': '주문을 찾을 수 없습니다.'}, status=404)
        
        # 🛡️ 이미 결제 완료된 주문인지 확인 (취소 불가)
        if menu_order.status == 'paid' and menu_order.paid_at:
            logger.info(f"[메뉴취소] 이미 결제 완료된 주문: {menu_order.order_number}")
            return JsonResponse({
                'success': False,
                'error': '이미 결제가 완료되었습니다. 취소할 수 없습니다.'
            })
        
        # 취소 가능한 상태인지 확인
        if menu_order.status not in ['pending', 'payment_pending']:
            return JsonResponse({
                'success': False, 
                'error': f'취소할 수 없는 상태입니다. 현재 상태: {menu_order.get_status_display()}'
            }, status=400)
        
        # 🛡️ 실제 결제 상태를 Blink API로 재확인
        try:
            from ln_payment.blink_service import get_blink_service_for_store
            
            # BlinkAPIService 초기화
            blink_service = get_blink_service_for_store(store)
            
            # 결제 상태 재확인
            result = blink_service.check_invoice_status(payment_hash)
            
            if result['success'] and result['status'] == 'paid':
                # 실제로는 결제가 완료되었음!
                logger.info(f"[메뉴취소] 실제 결제 완료 감지: {payment_hash}")
                
                # 주문 상태 업데이트 (결제 완료 처리)
                try:
                    with transaction.atomic():
                        menu_order_locked = MenuOrder.objects.select_for_update().get(
                            id=menu_order.id,
                            payment_hash=payment_hash,
                            store=store
                        )
                        
                        # 주문번호 생성 (아직 없는 경우에만)
                        if not menu_order_locked.order_number:
                            menu_order_locked.order_number = menu_order_locked.generate_order_number()
                        
                        menu_order_locked.status = 'paid'
                        menu_order_locked.paid_at = timezone.now()
                        menu_order_locked.save()
                        
                        logger.info(f"[메뉴취소] 결제 완료 상태로 업데이트: {menu_order_locked.order_number}")
                        
                        return JsonResponse({
                            'success': False,
                            'error': '결제가 완료되었습니다.',
                            'order_number': menu_order_locked.order_number
                        })
                        
                except MenuOrder.DoesNotExist:
                    logger.error(f"[메뉴취소] 주문 락 획득 실패: {payment_hash}")
                    return JsonResponse({
                        'success': False,
                        'error': '결제는 완료되었지만 주문 처리에 실패했습니다. 고객센터에 문의해주세요.'
                    })
            
        except Exception as e:
            logger.warning(f"[메뉴취소] 결제 상태 재확인 실패: {str(e)}")
            # 재확인 실패 시에는 그대로 진행
        
        # 주문 상태를 취소로 변경
        menu_order.status = 'cancelled'
        menu_order.save()
        
        logger.info(f"[메뉴취소] 주문 취소 완료: {menu_order.order_number}")
        
        return JsonResponse({
            'success': True,
            'message': '주문이 취소되었습니다.'
        })
        
    except Exception as e:
        logger.error(f"[메뉴취소] 전체 오류: {str(e)}")
        import traceback
        logger.error(f"[메뉴취소] 스택 트레이스: {traceback.format_exc()}")
        return JsonResponse({'success': False, 'error': f'주문 취소 중 오류가 발생했습니다: {str(e)}'}, status=500)

