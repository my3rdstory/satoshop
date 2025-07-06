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
                
                # 🔄 상품과 동일: 결제 완료 후에만 주문 생성, 지금은 세션에 정보 저장
                participant_data = {
                    'participant_name': participant_name,
                    'participant_email': participant_email,
                    'participant_phone': participant_phone,
                    'selected_options': [
                        {
                            'option_id': selected_option['option'].id,
                            'option_name': selected_option['option'].name,
                            'choice_id': selected_option['choice'].id,
                            'choice_name': selected_option['choice'].name,
                            'additional_price': selected_option['price']
                        }
                        for selected_option in selected_options
                    ],
                    'base_price': meetup.current_price,
                    'options_price': options_price,
                    'total_price': meetup.current_price + options_price,
                    'is_early_bird': meetup.is_discounted and meetup.is_early_bird_active,
                    'discount_rate': meetup.public_discount_rate if meetup.is_early_bird_active else 0,
                    'original_price': meetup.price if meetup.is_early_bird_active else None,
                }
                
                # 세션에 참가자 정보 저장 (결제 완료 시 사용)
                request.session[f'meetup_participant_data_{meetup_id}'] = participant_data
                
                # 결제 페이지로 리다이렉트 (order_id 없이)
                return redirect('meetup:meetup_checkout_payment', store_id=store_id, meetup_id=meetup_id)
                
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

def create_meetup_order(meetup, participant_data, is_free=False, user=None):
    """밋업 주문 생성 함수"""
    # 주문 생성
    order = MeetupOrder.objects.create(
        meetup=meetup,
        user=user,
        participant_name=participant_data['participant_name'],
        participant_email=participant_data['participant_email'],
        participant_phone=participant_data.get('participant_phone', ''),
        total_price=participant_data['total_price'],
        status='confirmed',
        is_temporary_reserved=False,
        payment_hash=participant_data.get('payment_hash', ''),
        payment_request=participant_data.get('payment_request', ''),
        confirmed_at=timezone.now(),
        paid_at=timezone.now(),
        is_early_bird=participant_data.get('is_early_bird', False),
        discount_rate=participant_data.get('discount_rate', 0),
        original_price=participant_data.get('original_price', 0),
        base_price=participant_data.get('base_price', 0),
        options_price=participant_data.get('options_price', 0),
    )
    
    # 선택된 옵션 처리
    for option_data in participant_data.get('selected_options', []):
        try:
            option = MeetupOption.objects.get(id=option_data['option_id'])
            choice = MeetupChoice.objects.get(id=option_data['choice_id'])
            
            MeetupOrderOption.objects.create(
                order=order,
                option=option,
                choice=choice,
                additional_price=option_data['additional_price']
            )
        except (MeetupOption.DoesNotExist, MeetupChoice.DoesNotExist):
            logger.warning(f"옵션 또는 선택지를 찾을 수 없음: option_id={option_data['option_id']}, choice_id={option_data['choice_id']}")
    
    return order

def meetup_checkout_payment(request, store_id, meetup_id):
    """밋업 결제 페이지"""
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
    meetup = get_object_or_404(
        Meetup, 
        id=meetup_id, 
        store=store, 
        deleted_at__isnull=True
    )
    # 🔄 세션에서 참가자 정보 확인 (상품과 동일한 방식)
    participant_data = request.session.get(f'meetup_participant_data_{meetup_id}')
    if not participant_data:
        messages.error(request, '참가자 정보가 없습니다. 다시 신청해주세요.')
        return redirect('meetup:meetup_checkout', store_id=store_id, meetup_id=meetup_id)
    
    # 무료 밋업인 경우 POST 요청 처리
    if request.method == 'POST' and participant_data.get('total_price', 0) == 0:
        try:
            # 무료 밋업 주문 생성
            order = create_meetup_order(
                meetup=meetup,
                participant_data=participant_data,
                is_free=True,
                user=request.user
            )
            
            # 세션에서 참가자 정보 제거
            if f'meetup_participant_data_{meetup_id}' in request.session:
                del request.session[f'meetup_participant_data_{meetup_id}']
            
            # 성공 메시지 및 리다이렉션
            messages.success(request, '무료 밋업 참가 신청이 완료되었습니다!')
            return redirect('meetup:meetup_checkout_complete', store_id=store_id, meetup_id=meetup_id, order_id=order.id)
            
        except Exception as e:
            logger.error(f"무료 밋업 주문 생성 실패: {str(e)}")
            messages.error(request, '참가 신청 중 오류가 발생했습니다. 다시 시도해주세요.')
    
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
        'participant_data': participant_data,
        'payment_service_available': payment_service_available,
        'countdown_seconds': countdown_seconds,
    }
    
    return render(request, 'meetup/meetup_checkout.html', context)

@require_POST
@csrf_exempt
def create_meetup_invoice(request, store_id, meetup_id):
    """밋업 결제 인보이스 생성"""
    try:
        store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
        meetup = get_object_or_404(
            Meetup, 
            id=meetup_id, 
            store=store, 
            deleted_at__isnull=True
        )
        # 🔄 세션에서 참가자 정보 확인 (상품과 동일한 방식)
        participant_data = request.session.get(f'meetup_participant_data_{meetup_id}')
        if not participant_data:
            return JsonResponse({
                'success': False,
                'error': '참가자 정보가 없습니다.'
            })
        
        # 블링크 서비스 가져오기
        blink_service = get_blink_service_for_store(store)
        if not blink_service:
            return JsonResponse({
                'success': False,
                'error': '결제 서비스가 설정되지 않았습니다.'
            })
        
        # 인보이스 생성
        amount_sats = participant_data['total_price']
        memo = f"{meetup.name}"
        
        result = blink_service.create_invoice(
            amount_sats=amount_sats,
            memo=memo,
            expires_in_minutes=15
        )
        
        if result['success']:
            # 🔄 세션에 인보이스 정보 저장 (상품과 동일한 방식)
            participant_data['payment_hash'] = result['payment_hash']
            participant_data['payment_request'] = result['invoice']
            request.session[f'meetup_participant_data_{meetup_id}'] = participant_data
            
            return JsonResponse({
                'success': True,
                'payment_hash': result['payment_hash'],
                'invoice': result['invoice'],
                'amount_sats': participant_data['total_price'],
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
def check_meetup_payment_status(request, store_id, meetup_id):
    """밋업 결제 상태 확인 (최적화된 버전)"""
    import time
    start_time = time.time()
    
    try:
        # 🔄 스토어와 밋업 정보 조회
        store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
        meetup = get_object_or_404(
            Meetup, 
            id=meetup_id, 
            store=store, 
            deleted_at__isnull=True
        )
        
        # 🔄 세션에서 참가자 정보 확인
        participant_data = request.session.get(f'meetup_participant_data_{meetup_id}')
        if not participant_data:
            return JsonResponse({
                'success': False,
                'error': '참가자 정보가 없습니다.'
            })
        
        # 결제 정보가 없거나 빈 문자열인 경우
        payment_hash = participant_data.get('payment_hash')
        if not payment_hash or payment_hash.strip() == '':
            logger.warning(f"결제 정보 없음 - meetup_id: {meetup_id}")
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
        logger.debug(f"결제 상태 확인 시작 - payment_hash: {payment_hash}")
        result = blink_service.check_invoice_status(payment_hash)
        
        logger.debug(f"결제 상태 확인 완료 - 소요 시간: {time.time() - start_time:.3f}s")
        
        if result['success']:
            if result['status'] == 'paid':
                # 🔄 결제 완료 처리 - 상품과 동일: 결제 완료 후 즉시 주문 생성
                logger.info(f"결제 완료 감지 - meetup_id: {meetup_id}, payment_hash: {payment_hash}")
                
                # 🛡️ 중복 주문 생성 방지: 이미 해당 payment_hash로 주문이 존재하는지 확인
                existing_orders = MeetupOrder.objects.filter(payment_hash=payment_hash)
                if existing_orders.exists():
                    logger.debug(f"이미 결제 완료된 주문 발견: {payment_hash}")
                    order = existing_orders.first()
                    return JsonResponse({
                        'success': True,
                        'paid': True,
                        'redirect_url': f'/meetup/{store_id}/{meetup_id}/complete/{order.id}/'
                    })
                
                with transaction.atomic():
                    # 🔄 상품과 동일: 결제 완료 후 즉시 주문 생성
                    order = create_meetup_order(
                        meetup=meetup,
                        participant_data=participant_data,
                        is_free=False,
                        user=request.user
                    )
                    
                    logger.info(f"주문 생성 완료 - order_id: {order.id}, 티켓번호: {order.order_number}")
                    
                # 세션에서 참가자 정보 삭제 (주문 생성 완료)
                if f'meetup_participant_data_{meetup_id}' in request.session:
                    del request.session[f'meetup_participant_data_{meetup_id}']
                    
                # 밋업 참가 확정 이메일 발송 - 트랜잭션 외부에서 비동기로 실행
                try:
                    from .services import send_meetup_notification_email, send_meetup_participant_confirmation_email
                    
                    # 주인장에게 알림 이메일
                    send_meetup_notification_email(order)
                    
                    # 참가자에게 확인 이메일
                    send_meetup_participant_confirmation_email(order)
                    
                    logger.debug(f"결제 완료 이메일 발송 완료 - order_id: {order.id}")
                        
                except Exception as e:
                    # 이메일 발송 실패해도 주문 처리는 계속 진행
                    logger.error(f"이메일 발송 실패 - order_id: {order.id}, error: {e}")
                    pass
                
                return JsonResponse({
                    'success': True,
                    'paid': True,
                    'redirect_url': f'/meetup/{store_id}/{meetup_id}/complete/{order.id}/'
                })
            else:
                # 결제 대기 중
                logger.debug(f"결제 대기 중 - meetup_id: {meetup_id}, status: {result['status']}")
                return JsonResponse({
                    'success': True,
                    'paid': False,
                    'status': result['status']
                })
        else:
            logger.error(f"결제 상태 확인 실패 - meetup_id: {meetup_id}, error: {result.get('error')}")
            return JsonResponse({
                'success': False,
                'error': result.get('error', '결제 상태 확인에 실패했습니다.')
            })
            
    except Exception as e:
        logger.error(f"결제 상태 확인 중 오류 - meetup_id: {meetup_id}, error: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': '결제 상태 확인 중 오류가 발생했습니다.'
        })

@require_POST
@csrf_exempt
def cancel_meetup_invoice(request, store_id, meetup_id):
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
        
        # 🔄 세션에서 참가자 정보 확인 (상품과 동일한 방식)
        participant_data = request.session.get(f'meetup_participant_data_{meetup_id}')
        if not participant_data:
            return JsonResponse({
                'success': False,
                'error': '참가자 정보가 없습니다.'
            })
        
        stored_payment_hash = participant_data.get('payment_hash')
        if not stored_payment_hash or stored_payment_hash != payment_hash:
            return JsonResponse({
                'success': False,
                'error': '결제 정보가 일치하지 않습니다.'
            })
        
        # 🛡️ 이미 결제 완료된 주문이 있는지 확인 (취소 불가)
        existing_orders = MeetupOrder.objects.filter(payment_hash=payment_hash)
        if existing_orders.exists():
            order = existing_orders.first()
            logger.warning(f"이미 결제 완료된 주문의 취소 시도 - 주문: {order.order_number}")
            return JsonResponse({
                'success': False,
                'error': '이미 결제가 완료된 주문은 취소할 수 없습니다.',
                'redirect_url': f'/meetup/{store_id}/{meetup_id}/complete/{order.id}/'
            })
        
        # 결제 상태를 한 번 더 확인 (마지막 안전장치)
        try:
            blink_service = get_blink_service_for_store(store)
            if blink_service:
                result = blink_service.check_invoice_status(payment_hash)
                if result['success'] and result['status'] == 'paid':
                    # 실제로는 결제가 완료된 경우 - 즉시 주문 생성 후 리다이렉트
                    logger.warning(f"취소 시도 중 결제 완료 발견 - payment_hash: {payment_hash}")
                    
                    # 즉시 주문 생성 (위의 결제 완료 로직과 동일)
                    with transaction.atomic():
                        order = create_meetup_order(
                            meetup=meetup,
                            participant_data=participant_data,
                            is_free=False,
                            user=request.user
                        )
                    
                    # 세션에서 참가자 정보 삭제 (결제 완료되었으므로 삭제)
                    if f'meetup_participant_data_{meetup_id}' in request.session:
                        del request.session[f'meetup_participant_data_{meetup_id}']
                    
                    return JsonResponse({
                        'success': False,
                        'error': '결제가 이미 완료되었습니다.',
                        'redirect_url': f'/meetup/{store_id}/{meetup_id}/complete/{order.id}/'
                    })
        except Exception as e:
            # 결제 상태 확인 실패는 무시하고 취소 계속 진행
            logger.warning(f"취소 시 결제 상태 확인 실패 (계속 진행): {e}")
        
        # 🔄 세션에서 결제 정보만 삭제하고 참가자 정보는 유지
        if f'meetup_participant_data_{meetup_id}' in request.session:
            participant_data = request.session[f'meetup_participant_data_{meetup_id}']
            # 결제 관련 정보만 삭제
            participant_data.pop('payment_hash', None)
            participant_data.pop('payment_request', None)
            # 업데이트된 데이터를 세션에 다시 저장
            request.session[f'meetup_participant_data_{meetup_id}'] = participant_data
        
        logger.info(f"밋업 인보이스 취소 - meetup_id: {meetup_id}, payment_hash: {payment_hash}")
        
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