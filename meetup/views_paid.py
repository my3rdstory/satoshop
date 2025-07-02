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
    """밋업 체크아웃 - 임시 예약 생성 후 참가자 정보 입력 페이지로"""
    from .services import create_temporary_reservation, release_reservation, extend_reservation
    
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
    meetup = get_object_or_404(
        Meetup, 
        id=meetup_id, 
        store=store, 
        deleted_at__isnull=True,
        is_active=True
    )
    
    # 무료 밋업인 경우 무료 체크아웃으로 리다이렉트
    if meetup.is_free:
        logger.info(f"무료 밋업 감지 - 무료 체크아웃으로 리다이렉트: {meetup_id}")
        return redirect('meetup:meetup_free_checkout', store_id=store_id, meetup_id=meetup_id)
    
    # 기존 진행 중인 주문 확인
    existing_order = MeetupOrder.objects.filter(
        meetup=meetup,
        user=request.user,
        status='pending',
        is_temporary_reserved=True
    ).first()
    
    if existing_order:
        # 기존 예약이 아직 유효한지 확인
        if existing_order.reservation_expires_at and timezone.now() < existing_order.reservation_expires_at:
            # 유효한 기존 예약이 있으면 해당 페이지로 진행
            logger.info(f"유효한 기존 임시 예약 발견 - 주문: {existing_order.order_number}, 만료시간: {existing_order.reservation_expires_at}")
        else:
            # 만료된 예약은 취소
            logger.info(f"만료된 임시 예약 취소 - 주문: {existing_order.order_number}")
            release_reservation(existing_order, "예약 시간 만료")
            existing_order = None
    
    # 새로운 임시 예약 생성 (GET 요청인 경우)
    if request.method == 'GET' and not existing_order:
        success, message, order = create_temporary_reservation(meetup, request.user)
        
        if not success:
            # 정원이 마감된 경우 특별 메시지 표시
            if "마감되었습니다" in message:
                context = {
                    'store': store,
                    'meetup': meetup,
                    'is_full_message': True,
                    'message': message
                }
                return render(request, 'meetup/meetup_full.html', context)
            else:
                messages.error(request, message)
                return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id)
        
        existing_order = order
    
    # GET 요청인 경우 참가자 정보 입력 페이지 표시
    if request.method == 'GET':
        # URL 파라미터에서 선택된 옵션 정보 가져오기
        selected_options_param = request.GET.get('selected_options')
        selected_options = {}
        
        if selected_options_param:
            try:
                selected_options = json.loads(selected_options_param)
            except (json.JSONDecodeError, ValueError):
                # 잘못된 JSON이면 빈 딕셔너리로 초기화
                selected_options = {}
        
        # 필수 옵션 정보 수집
        required_option_ids = list(meetup.options.filter(is_required=True).values_list('id', flat=True))
        
        # 할인 금액 계산 (조기등록 할인)
        discount_amount = 0
        if meetup.is_early_bird_active:
            discount_amount = meetup.price - meetup.current_price
        
        # 사이트 설정에서 카운트다운 시간 가져오기
        from myshop.models import SiteSettings
        site_settings = SiteSettings.get_settings()
        countdown_seconds = site_settings.meetup_countdown_seconds
        
        context = {
            'store': store,
            'meetup': meetup,
            'order': existing_order,
            'selected_options_json': json.dumps(selected_options) if selected_options else '{}',
            'required_option_ids': json.dumps(required_option_ids) if required_option_ids else '[]',
            'discount_amount': discount_amount,
            'countdown_seconds': countdown_seconds,
            'reservation_expires_at': existing_order.reservation_expires_at.isoformat() if existing_order and existing_order.reservation_expires_at else None,
        }
        return render(request, 'meetup/meetup_participant_info.html', context)
    
    # POST 요청인 경우 참가자 정보 업데이트 후 결제 페이지로
    if request.method == 'POST':
        # 유효한 임시 예약이 있는지 확인
        if not existing_order or not existing_order.is_temporary_reserved:
            messages.error(request, '유효한 예약이 없습니다. 다시 신청해 주세요.')
            return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id)
        
        # 예약 시간이 만료되었는지 확인
        if existing_order.reservation_expires_at and timezone.now() > existing_order.reservation_expires_at:
            release_reservation(existing_order, "참가자 정보 입력 시간 초과")
            messages.error(request, '신청 시간이 초과되어 자동으로 취소되었습니다. 다시 신청해 주세요.')
            return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id)
    
        # 기존 예약 주문 업데이트
        try:
            with transaction.atomic():
                # 기본 가격 재계산 (현재 가격 기준)
                base_price = meetup.current_price
                options_price = 0
                
                # 선택한 옵션 처리 (POST 데이터에서)
                options_data = request.POST.get('selected_options')
                selected_option_choices = []
                
                if options_data:
                    try:
                        selected_options = json.loads(options_data)
                        
                        # 각 옵션의 선택지 가격 계산
                        for option_id, choice_info in selected_options.items():
                            choice_id = choice_info.get('choiceId')
                            choice_price = choice_info.get('price', 0)
                            
                            # 실제 옵션 선택지 검증
                            try:
                                choice = MeetupChoice.objects.get(
                                    id=choice_id,
                                    option__meetup=meetup,
                                    option__id=option_id
                                )
                                # 가격 검증 (보안을 위해)
                                if choice.additional_price == choice_price:
                                    options_price += choice_price
                                    selected_option_choices.append(choice)
                            except MeetupChoice.DoesNotExist:
                                # 잘못된 선택지는 무시
                                pass
                                
                    except (json.JSONDecodeError, KeyError, ValueError):
                        # 잘못된 옵션 데이터는 무시
                        pass
                
                total_price = base_price + options_price
                
                # 할인 정보
                is_early_bird = meetup.is_discounted and meetup.is_early_bird_active
                discount_rate = meetup.public_discount_rate if is_early_bird else 0
                original_price = meetup.price if is_early_bird else None
                
                # 참가자 정보 업데이트
                participant_name = request.POST.get('participant_name') or request.user.get_full_name() or request.user.username
                participant_email = request.POST.get('participant_email') or request.user.email
                participant_phone = request.POST.get('participant_phone', '').strip()
                
                # 기존 주문 정보 업데이트
                existing_order.participant_name = participant_name
                existing_order.participant_email = participant_email
                existing_order.participant_phone = participant_phone
                existing_order.base_price = base_price
                existing_order.options_price = options_price
                existing_order.total_price = total_price
                existing_order.is_early_bird = is_early_bird
                existing_order.discount_rate = discount_rate
                existing_order.original_price = original_price
                
                # 예약 시간을 다음 단계(결제)로 연장
                extend_reservation(existing_order)
                
                existing_order.save()
                
                # 기존 옵션 선택 삭제 후 새로 생성
                existing_order.selected_options.all().delete()
                for choice in selected_option_choices:
                    MeetupOrderOption.objects.create(
                        order=existing_order,
                        option=choice.option,
                        choice=choice,
                        additional_price=choice.additional_price
                    )
                
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
                    'order': existing_order,
                    'payment_service_available': payment_service_available,
                    'countdown_seconds': countdown_seconds,
                    'reservation_expires_at': existing_order.reservation_expires_at.isoformat() if existing_order.reservation_expires_at else None,
                }
                
                return render(request, 'meetup/meetup_checkout.html', context)
                
        except Exception as e:
            logger.error(f"밋업 주문 업데이트 오류: {e}", exc_info=True)
            
            # 예외 종류별 상세 처리
            import traceback
            logger.error(f"밋업 주문 업데이트 상세 오류: {traceback.format_exc()}")
            
            # 사용자에게 구체적인 오류 메시지 제공
            if "order_number" in str(e).lower():
                messages.error(request, '주문번호 생성 중 오류가 발생했습니다.')
            elif "confirm_reservation" in str(e).lower():
                messages.error(request, '참가 확정 처리 중 오류가 발생했습니다.')
            elif "email" in str(e).lower():
                messages.error(request, '이메일 발송 중 오류가 발생했지만 참가 신청은 완료되었습니다.')
            else:
                messages.error(request, '주문 처리 중 오류가 발생했습니다.')
            
            return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id)

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
        status__in=['pending', 'cancelled']  # 취소된 주문도 포함
    )
    
    # 임시 예약 상태가 아니거나 예약 시간이 만료된 경우 처리
    if order.status == 'pending':
        if not order.is_temporary_reserved:
            messages.error(request, '유효한 예약이 아닙니다. 다시 신청해 주세요.')
            return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id)
        
        # 예약 시간 만료 확인
        if order.reservation_expires_at and timezone.now() > order.reservation_expires_at:
            from .services import release_reservation
            release_reservation(order, "결제 페이지 접근 시 예약 시간 만료")
            messages.error(request, '예약 시간이 만료되었습니다. 다시 신청해 주세요.')
            return redirect('meetup:meetup_detail', store_id=store_id, meetup_id=meetup_id)
    
    # 주문 생성 후 30분 경과 시 만료 (기존 로직 유지)
    if timezone.now() - order.created_at > timedelta(minutes=30):
        if order.status == 'pending' and order.is_temporary_reserved:
            from .services import release_reservation
            release_reservation(order, "주문 생성 후 30분 경과")
        else:
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
        'reservation_expires_at': order.reservation_expires_at.isoformat() if order.reservation_expires_at else None,
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
            status__in=['pending', 'cancelled']  # 취소된 주문도 포함
        )
        
        # 취소된 주문은 pending 상태로 복원
        if order.status == 'cancelled':
            order.status = 'pending'
        
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
            # 주문에 인보이스 정보 저장
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
            
    except Exception as e:
        logger.error(f"밋업 인보이스 생성 오류: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': '인보이스 생성 중 오류가 발생했습니다.'
        })

@require_POST
@csrf_exempt
def check_meetup_payment_status(request, store_id, meetup_id, order_id):
    """밋업 결제 상태 확인"""
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
            meetup=meetup
        )
        
        if not order.payment_hash or order.payment_hash.strip() == '':
            return JsonResponse({
                'success': False,
                'error': '결제 정보가 없습니다.'
            })
        
        # 블링크 서비스 가져오기
        blink_service = get_blink_service_for_store(store)
        if not blink_service:
            return JsonResponse({
                'success': False,
                'error': '결제 서비스가 설정되지 않았습니다.'
            })
        
        # 결제 상태 확인
        result = blink_service.check_invoice_status(order.payment_hash)
        
        if result['success']:
            if result['status'] == 'paid':
                # 결제 완료 처리 - 임시예약을 확정으로 변경
                with transaction.atomic():
                    order.status = 'confirmed'
                    order.is_temporary_reserved = False  # 임시예약 해제
                    order.reservation_expires_at = None  # 예약 만료시간 제거
                    order.paid_at = timezone.now()
                    order.confirmed_at = timezone.now()
                    order.save()
                    
                logger.info(f"밋업 결제 완료 및 예약 확정 - 주문: {order.order_number}")
                
                # 밋업 참가 확정 이메일 발송 (주인장에게 + 참가자에게)
                try:
                    from .services import send_meetup_notification_email, send_meetup_participant_confirmation_email
                    
                    # 주인장에게 알림 이메일
                    owner_email_sent = send_meetup_notification_email(order)
                    if owner_email_sent:
                        logger.info(f"[MEETUP_EMAIL] 밋업 알림 이메일 발송 성공: {order.order_number}")
                    else:
                        logger.info(f"[MEETUP_EMAIL] 밋업 알림 이메일 발송 조건 미충족: {order.order_number}")
                    
                    # 참가자에게 확인 이메일
                    participant_email_sent = send_meetup_participant_confirmation_email(order)
                    if participant_email_sent:
                        logger.info(f"[MEETUP_EMAIL] 밋업 참가자 확인 이메일 발송 성공: {order.order_number}")
                    else:
                        logger.info(f"[MEETUP_EMAIL] 밋업 참가자 확인 이메일 발송 조건 미충족: {order.order_number}")
                        
                except Exception as e:
                    # 이메일 발송 실패해도 주문 처리는 계속 진행
                    logger.error(f"[MEETUP_EMAIL] 밋업 이메일 발송 오류: {order.order_number}, {str(e)}")
                    pass
                
                return JsonResponse({
                    'success': True,
                    'paid': True,
                    'redirect_url': f'/meetup/{store_id}/{meetup_id}/complete/{order.id}/'
                })
            else:
                return JsonResponse({
                    'success': True,
                    'paid': False
                })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', '결제 상태 확인에 실패했습니다.')
            })
            
    except Exception as e:
        logger.error(f"밋업 결제 상태 확인 오류: {e}", exc_info=True)
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