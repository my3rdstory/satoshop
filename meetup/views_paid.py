from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.utils import timezone
from stores.models import Store
from .models import Meetup, MeetupOrder, MeetupOption, MeetupChoice, MeetupOrderOption
from ln_payment.blink_service import get_blink_service_for_store
from datetime import timedelta
import json
import logging

logger = logging.getLogger(__name__)

@login_required
def meetup_checkout(request, store_id, meetup_id):
    """밋업 체크아웃 - 참가자 정보 입력 후 결제 페이지로"""
    
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
    meetup = get_object_or_404(
        Meetup, 
        id=meetup_id, 
        store=store, 
        deleted_at__isnull=True,
        is_active=True
    )
    
    # 무료 밋업인 경우 무료 참가자 정보 입력으로 리다이렉트
    if meetup.is_free:
        return redirect('meetup:meetup_free_participant_info', store_id=store_id, meetup_id=meetup_id)
    
    # 정원 확인
    if meetup.max_participants and meetup.current_participants >= meetup.max_participants:
        messages.error(request, '밋업 신청이 마감되었습니다.')
        return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id)
    
    # 기존 주문 확인 (유료 밋업도 반복 구매 허용)
    existing_orders = MeetupOrder.objects.filter(
        meetup=meetup,
        user=request.user,
        status__in=['confirmed', 'completed']
    ).order_by('-created_at')
    
    # 기존 참가 이력이 있어도 반복 구매 허용 (유료 밋업도 무료 밋업처럼 처리)
    
    # POST 요청 처리 (참가자 정보 업데이트 후 결제 페이지로)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # 정원 재확인 (동시성 이슈 방지)
                if meetup.max_participants and meetup.current_participants >= meetup.max_participants:
                    messages.error(request, '죄송합니다. 방금 전에 밋업 신청이 마감되었습니다.')
                    return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id)
                
                # 참가자 정보 수집
                participant_name = request.POST.get('participant_name', '').strip()
                participant_email = request.POST.get('participant_email', '').strip()
                participant_phone = request.POST.get('participant_phone', '').strip()
                
                # 필수 정보 검증
                if not participant_name:
                    messages.error(request, '참가자 이름을 입력해주세요.')
                    return render(request, 'meetup/meetup_participant_info.html', {
                        'store': store,
                        'meetup': meetup,
                        'error_occurred': True
                    })
                
                if not participant_email:
                    messages.error(request, '이메일을 입력해주세요.')
                    return render(request, 'meetup/meetup_participant_info.html', {
                        'store': store,
                        'meetup': meetup,
                        'error_occurred': True
                    })
                
                # 선택된 옵션 처리 (JSON 형태로 전달됨)
                selected_options = []
                options_price = 0
                
                selected_options_json = request.POST.get('selected_options', '{}')
                try:
                    import json
                    selected_options_data = json.loads(selected_options_json)
                    
                    for option_id_str, option_data in selected_options_data.items():
                        try:
                            option_id = int(option_id_str)
                            option = MeetupOption.objects.get(id=option_id, meetup=meetup)
                            
                            choice_id = option_data.get('choiceId')
                            if choice_id:
                                choice = MeetupChoice.objects.get(id=choice_id, option=option)
                                selected_options.append({
                                    'option': option,
                                    'choice': choice,
                                    'price': choice.additional_price
                                })
                                options_price += choice.additional_price
                        
                        except (ValueError, MeetupOption.DoesNotExist, MeetupChoice.DoesNotExist):
                            continue
                            
                except json.JSONDecodeError:
                    # JSON 파싱 실패 시 기존 방식으로 폴백
                    for key, value in request.POST.items():
                        if key.startswith('option_'):
                            try:
                                option_id = int(key.replace('option_', ''))
                                option = MeetupOption.objects.get(id=option_id, meetup=meetup)
                                
                                choice_id = value
                                if choice_id:
                                    choice = MeetupChoice.objects.get(id=choice_id, option=option)
                                    selected_options.append({
                                        'option': option,
                                        'choice': choice,
                                        'price': choice.additional_price
                                    })
                                    options_price += choice.additional_price
                            
                            except (ValueError, MeetupOption.DoesNotExist, MeetupChoice.DoesNotExist):
                                continue
                
                # 주문 생성 (바로 confirmed 상태로)
                order = MeetupOrder.objects.create(
                    meetup=meetup,
                    user=request.user,
                    participant_name=participant_name,
                    participant_email=participant_email,
                    participant_phone=participant_phone,
                    status='confirmed',
                    is_temporary_reserved=False,
                    base_price=meetup.current_price,
                    options_price=options_price,
                    total_price=meetup.current_price + options_price,
                    is_early_bird=meetup.is_discounted and meetup.is_early_bird_active,
                    discount_rate=meetup.public_discount_rate if meetup.is_early_bird_active else 0,
                    original_price=meetup.price if meetup.is_early_bird_active else None,
                    confirmed_at=timezone.now(),
                )
                
                # 선택된 옵션 저장
                for selected_option in selected_options:
                    MeetupOrderOption.objects.create(
                        order=order,
                        option=selected_option['option'],
                        choice=selected_option['choice'],
                        additional_price=selected_option['price']
                    )
                
                # 결제 페이지로 리다이렉트
                return redirect('meetup:meetup_checkout_payment', store_id=store_id, meetup_id=meetup_id, order_id=order.id)
                
        except Exception:
            
            messages.error(request, '주문 처리 중 오류가 발생했습니다. 다시 시도해주세요.')
            return render(request, 'meetup/meetup_participant_info.html', {
                'store': store,
                'meetup': meetup,
                'error_occurred': True
            })
    
    # 할인 금액 계산 (조기등록 할인)
    discount_amount = 0
    if meetup.is_discounted and meetup.is_early_bird_active and meetup.discounted_price:
        discount_amount = meetup.price - meetup.discounted_price
    
    # URL 파라미터로 전달된 선택된 옵션 처리
    selected_options_data = None
    if request.GET.get('selected_options'):
        try:
            import json
            selected_options_data = json.loads(request.GET.get('selected_options'))
        except json.JSONDecodeError:
            selected_options_data = None
    
    # 밋업 옵션 조회 (필수 옵션 정보와 함께)
    meetup_options = meetup.options.prefetch_related('choices').order_by('order')
    required_option_ids = [option.id for option in meetup_options if option.is_required]
    
    # GET 요청 처리 (참가자 정보 입력 페이지 표시)
    context = {
        'store': store,
        'meetup': meetup,
        'meetup_options': meetup_options,  # 밋업 옵션 추가
        'existing_orders': existing_orders,  # 기존 참가 이력 전달
        'discount_amount': discount_amount,  # 할인 금액 전달
        'selected_options_data': selected_options_data,  # 선택된 옵션 데이터 전달
        'required_option_ids': required_option_ids,  # 필수 옵션 ID 목록 전달
    }
    
    return render(request, 'meetup/meetup_participant_info.html', context)

def meetup_checkout_payment(request, store_id, meetup_id, order_id):
    """밋업 결제 페이지"""
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
    meetup = get_object_or_404(
        Meetup, 
        id=meetup_id, 
        store=store, 
        deleted_at__isnull=True
    )
    order = get_object_or_404(
        MeetupOrder,
        id=order_id,
        meetup=meetup,
        status='confirmed'
    )
    
    # 주문 생성 후 30분 경과 시 만료
    if timezone.now() - order.created_at > timedelta(minutes=30):
        order.status = 'cancelled'
        order.save()
        messages.error(request, '주문이 만료되었습니다. 다시 신청해주세요.')
        return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id)
    
    # 블링크 서비스 연결 확인
    blink_service = get_blink_service_for_store(store)
    payment_service_available = blink_service is not None
    
    # 사이트 설정에서 카운트다운 시간 가져오기
    from myshop.models import SiteSettings
    site_settings = SiteSettings.get_settings()
    countdown_seconds = site_settings.meetup_countdown_seconds
    
    context = {
        'store': store,
        'meetup': meetup,
        'order': order,
        'payment_service_available': payment_service_available,
        'countdown_seconds': countdown_seconds,
    }
    
    return render(request, 'meetup/meetup_checkout.html', context)

@require_POST
@csrf_exempt
def create_meetup_invoice(request, store_id, meetup_id, order_id):
    """밋업 결제 인보이스 생성"""
    try:
        store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
        meetup = get_object_or_404(
            Meetup, 
            id=meetup_id, 
            store=store, 
            deleted_at__isnull=True
        )
        order = get_object_or_404(
            MeetupOrder,
            id=order_id,
            meetup=meetup,
            status__in=['confirmed', 'cancelled']  # 취소된 주문도 포함
        )
        
        # 취소된 주문은 confirmed 상태로 복원
        if order.status == 'cancelled':
            order.status = 'confirmed'
        
        # 블링크 서비스 가져오기
        blink_service = get_blink_service_for_store(store)
        if not blink_service:
            return JsonResponse({
                'success': False,
                'error': '결제 서비스가 설정되지 않았습니다.'
            })
        
        # 기존 결제 정보 초기화 (재생성 대비)
        order.payment_hash = ''
        order.payment_request = ''
        order.paid_at = None  # 결제 완료 시간도 초기화
        order.save()
        
        # 인보이스 생성
        amount_sats = order.total_price
        memo = f"{meetup.name}"
        
        result = blink_service.create_invoice(
            amount_sats=amount_sats,
            memo=memo,
            expires_in_minutes=15
        )
        
        if result['success']:
            # 주문에 인보이스 정보 저장 (이미 confirmed 상태)
            order.payment_hash = result['payment_hash']
            order.payment_request = result['invoice']
            order.save()
            
            return JsonResponse({
                'success': True,
                'payment_hash': result['payment_hash'],
                'invoice': result['invoice'],
                'amount_sats': order.total_price,
                'expires_at': result['expires_at'].isoformat() if result.get('expires_at') else None
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', '인보이스 생성에 실패했습니다.')
            })
            
    except Exception:
        return JsonResponse({
            'success': False,
            'error': '인보이스 생성 중 오류가 발생했습니다.'
        })

@require_POST
@csrf_exempt
def check_meetup_payment_status(request, store_id, meetup_id, order_id):
    """밋업 결제 상태 확인 (최적화된 버전)"""
    import time
    start_time = time.time()
    
    try:
        # 캐시 키 생성
        cache_key = f"meetup_payment_status_{store_id}_{meetup_id}_{order_id}"
        
        # DB 조회 최적화 - select_related로 한 번에 조회
        try:
            order = MeetupOrder.objects.select_related('meetup', 'meetup__store').get(
                id=order_id,
                meetup__id=meetup_id,
                meetup__store__store_id=store_id,
                meetup__store__deleted_at__isnull=True,
                meetup__deleted_at__isnull=True
            )
            store = order.meetup.store
            meetup = order.meetup
        except MeetupOrder.DoesNotExist:
            logger.warning(f"밋업 주문 조회 실패 - order_id: {order_id}, meetup_id: {meetup_id}, store_id: {store_id}")
            return JsonResponse({
                'success': False,
                'error': '주문을 찾을 수 없습니다.'
            })
        
        # 이미 결제 완료된 주문인지 먼저 확인 (가장 빠른 경로)
        if order.paid_at:
            logger.debug(f"이미 결제 완료된 주문 - order_id: {order_id}, 응답 시간: {time.time() - start_time:.3f}s")
            return JsonResponse({
                'success': True,
                'paid': True,
                'redirect_url': f'/meetup/{store_id}/{meetup_id}/complete/{order.id}/'
            })
        
        # 결제 정보가 없거나 빈 문자열인 경우
        if not order.payment_hash or order.payment_hash.strip() == '':
            logger.warning(f"결제 정보 없음 - order_id: {order_id}")
            return JsonResponse({
                'success': False,
                'error': '결제 정보가 없습니다.'
            })
        
        # 블링크 서비스 가져오기
        blink_service = get_blink_service_for_store(store)
        if not blink_service:
            logger.error(f"결제 서비스 설정 없음 - store_id: {store_id}")
            return JsonResponse({
                'success': False,
                'error': '결제 서비스가 설정되지 않았습니다.'
            })
        
        # 결제 상태 확인 (외부 API 호출)
        logger.debug(f"결제 상태 확인 시작 - payment_hash: {order.payment_hash}")
        result = blink_service.check_invoice_status(order.payment_hash)
        
        logger.debug(f"결제 상태 확인 완료 - 소요 시간: {time.time() - start_time:.3f}s")
        
        if result['success']:
            if result['status'] == 'paid':
                # 결제 완료 처리 - 트랜잭션으로 안전하게 처리
                logger.info(f"결제 완료 감지 - order_id: {order_id}, payment_hash: {order.payment_hash}")
                
                with transaction.atomic():
                    # 주문을 다시 조회하여 최신 상태 확인 (동시성 문제 방지)
                    order_locked = MeetupOrder.objects.select_for_update().get(id=order_id)
                    
                    # 이미 결제 완료된 경우 (다른 요청에서 처리된 경우)
                    if order_locked.paid_at:
                        logger.debug(f"이미 다른 요청에서 결제 완료 처리됨 - order_id: {order_id}")
                        return JsonResponse({
                            'success': True,
                            'paid': True,
                            'redirect_url': f'/meetup/{store_id}/{meetup_id}/complete/{order_locked.id}/'
                        })
                    
                    # 결제 정보가 삭제된 경우 (사용자가 취소한 경우)
                    if not order_locked.payment_hash or order_locked.payment_hash.strip() == '':
                        logger.warning(f"결제 완료되었지만 payment_hash가 삭제됨 - 주문: {order_locked.order_number}")
                        return JsonResponse({
                            'success': False,
                            'error': '결제가 취소되었습니다.'
                        })
                    
                    # 결제 완료 처리
                    order_locked.paid_at = timezone.now()
                    order_locked.save()
                    
                    logger.info(f"결제 완료 처리 완료 - order_id: {order_id}, 총 소요 시간: {time.time() - start_time:.3f}s")
                    
                # 밋업 참가 확정 이메일 발송 - 트랜잭션 외부에서 비동기로 실행
                try:
                    from .services import send_meetup_notification_email, send_meetup_participant_confirmation_email
                    
                    # 주인장에게 알림 이메일
                    send_meetup_notification_email(order_locked)
                    
                    # 참가자에게 확인 이메일
                    send_meetup_participant_confirmation_email(order_locked)
                    
                    logger.debug(f"결제 완료 이메일 발송 완료 - order_id: {order_id}")
                        
                except Exception as e:
                    # 이메일 발송 실패해도 주문 처리는 계속 진행
                    logger.error(f"이메일 발송 실패 - order_id: {order_id}, error: {e}")
                    pass
                
                return JsonResponse({
                    'success': True,
                    'paid': True,
                    'redirect_url': f'/meetup/{store_id}/{meetup_id}/complete/{order_id}/'
                })
            else:
                # 결제 대기 중
                logger.debug(f"결제 대기 중 - order_id: {order_id}, status: {result['status']}")
                return JsonResponse({
                    'success': True,
                    'paid': False,
                    'status': result['status']
                })
        else:
            logger.error(f"결제 상태 확인 실패 - order_id: {order_id}, error: {result.get('error')}")
            return JsonResponse({
                'success': False,
                'error': result.get('error', '결제 상태 확인에 실패했습니다.')
            })
            
    except Exception as e:
        logger.error(f"결제 상태 확인 중 오류 - order_id: {order_id}, error: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': '결제 상태 확인 중 오류가 발생했습니다.'
        })

@require_POST
@csrf_exempt
def cancel_meetup_invoice(request, store_id, meetup_id, order_id):
    """밋업 인보이스 취소"""
    try:
        data = json.loads(request.body)
        payment_hash = data.get('payment_hash')
        
        if not payment_hash:
            return JsonResponse({
                'success': False,
                'error': '결제 해시가 필요합니다.'
            })
        
        store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
        meetup = get_object_or_404(
            Meetup, 
            id=meetup_id, 
            store=store, 
            deleted_at__isnull=True
        )
        order = get_object_or_404(
            MeetupOrder,
            id=order_id,
            meetup=meetup,
            payment_hash=payment_hash
        )
        
        # 이미 결제 완료된 주문인지 확인 (취소 불가)
        if order.paid_at:
            logger.warning(f"이미 결제 완료된 주문의 취소 시도 - 주문: {order.order_number}")
            return JsonResponse({
                'success': False,
                'error': '이미 결제가 완료된 주문은 취소할 수 없습니다.'
            })
        
        # 결제 상태를 한 번 더 확인 (마지막 안전장치)
        try:
            blink_service = get_blink_service_for_store(store)
            if blink_service:
                result = blink_service.check_invoice_status(order.payment_hash)
                if result['success'] and result['status'] == 'paid':
                    # 실제로는 결제가 완료된 경우
                    logger.warning(f"취소 시도 중 결제 완료 발견 - 주문: {order.order_number}")
                    
                    # 결제 완료 처리
                    with transaction.atomic():
                        order.paid_at = timezone.now()
                        order.save()
                    
                    # 이메일 발송
                    try:
                        from .services import send_meetup_notification_email, send_meetup_participant_confirmation_email
                        send_meetup_notification_email(order)
                        send_meetup_participant_confirmation_email(order)
                    except Exception as e:
                        logger.error(f"이메일 발송 실패: {e}")
                    
                    return JsonResponse({
                        'success': False,
                        'error': '결제가 이미 완료되었습니다.',
                        'redirect_url': f'/meetup/{store_id}/{meetup_id}/complete/{order.id}/'
                    })
        except Exception as e:
            # 결제 상태 확인 실패는 무시하고 취소 계속 진행
            logger.warning(f"취소 시 결제 상태 확인 실패 (계속 진행): {e}")
        
        # 주문 취소 및 결제 정보 초기화
        from .services import release_reservation
        release_reservation(order, "사용자 결제 취소")
        
        # 결제 정보 초기화
        order.payment_hash = ''
        order.payment_request = ''
        order.save()
        
        logger.info(f"밋업 인보이스 취소 및 예약 해제 - 주문: {order.order_number}")
        
        return JsonResponse({
            'success': True,
            'message': '결제가 취소되었습니다.'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '잘못된 요청 형식입니다.'
        })
    except Exception as e:
        logger.error(f"밋업 인보이스 취소 오류: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': '취소 처리 중 오류가 발생했습니다.'
        }) 