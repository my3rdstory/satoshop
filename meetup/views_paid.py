from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_POST, require_http_methods
from django.db import transaction
from django.utils import timezone
from stores.models import Store
from .models import Meetup, MeetupOrder, MeetupOption, MeetupChoice, MeetupOrderOption
from ln_payment.blink_service import get_blink_service_for_store
from ln_payment.models import PaymentTransaction
from ln_payment.services import LightningPaymentProcessor
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

    _sync_meetup_order_options(order, participant_data)

    return order


def _sync_meetup_order_options(order, participant_data):
    """선택된 옵션 정보를 주문에 반영한다."""
    MeetupOrderOption.objects.filter(order=order).delete()

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
            logger.warning(
                "옵션 또는 선택지를 찾을 수 없음: option_id=%s, choice_id=%s",
                option_data.get('option_id'),
                option_data.get('choice_id'),
            )


def create_pending_meetup_order(meetup, participant_data, *, user=None, reservation_seconds=180):
    """결제 진행을 위한 임시 밋업 주문을 생성한다."""
    reservation_expires_at = timezone.now() + timedelta(seconds=reservation_seconds)

    order = MeetupOrder.objects.create(
        meetup=meetup,
        user=user,
        participant_name=participant_data['participant_name'],
        participant_email=participant_data['participant_email'],
        participant_phone=participant_data.get('participant_phone', ''),
        total_price=participant_data['total_price'],
        status='pending',
        is_temporary_reserved=True,
        reservation_expires_at=reservation_expires_at,
        base_price=participant_data.get('base_price', meetup.current_price),
        options_price=participant_data.get('options_price', 0),
        is_early_bird=participant_data.get('is_early_bird', False),
        discount_rate=participant_data.get('discount_rate', 0),
        original_price=participant_data.get('original_price', 0) or None,
    )

    return order


def finalize_meetup_order_from_transaction(order, participant_data, *, payment_hash='', payment_request=''):
    """결제 완료 정보로 임시 주문을 확정 상태로 전환한다."""
    order.participant_name = participant_data['participant_name']
    order.participant_email = participant_data['participant_email']
    order.participant_phone = participant_data.get('participant_phone', '')
    order.base_price = participant_data.get('base_price', order.base_price)
    order.options_price = participant_data.get('options_price', order.options_price)
    order.total_price = participant_data.get('total_price', order.total_price)
    order.is_early_bird = participant_data.get('is_early_bird', order.is_early_bird)
    order.discount_rate = participant_data.get('discount_rate', order.discount_rate)
    order.original_price = participant_data.get('original_price', order.original_price)
    order.payment_hash = payment_hash
    order.payment_request = payment_request
    now = timezone.now()
    if not order.paid_at:
        order.paid_at = now
    if not order.confirmed_at:
        order.confirmed_at = now
    order.status = 'confirmed'
    order.is_temporary_reserved = False
    order.auto_cancelled_reason = ''
    order.save(update_fields=[
        'participant_name',
        'participant_email',
        'participant_phone',
        'base_price',
        'options_price',
        'total_price',
        'is_early_bird',
        'discount_rate',
        'original_price',
        'payment_hash',
        'payment_request',
        'paid_at',
        'confirmed_at',
        'status',
        'is_temporary_reserved',
        'auto_cancelled_reason',
        'updated_at',
    ])

    _sync_meetup_order_options(order, participant_data)

    return order


def serialize_transaction(transaction: PaymentTransaction) -> dict:
    logs = [
        {
            'stage': log.stage,
            'status': log.status,
            'message': log.message,
            'detail': log.detail,
            'created_at': log.created_at.isoformat(),
        }
        for log in transaction.stage_logs.order_by('created_at')
    ]

    payload = {
        'id': str(transaction.id),
        'status': transaction.status,
        'current_stage': transaction.current_stage,
        'payment_hash': transaction.payment_hash,
        'invoice_expires_at': transaction.invoice_expires_at.isoformat() if transaction.invoice_expires_at else None,
        'logs': logs,
        'created_at': transaction.created_at.isoformat(),
        'updated_at': transaction.updated_at.isoformat(),
    }

    if transaction.payment_request:
        payload['invoice'] = {
            'payment_request': transaction.payment_request,
            'payment_hash': transaction.payment_hash,
            'expires_at': transaction.invoice_expires_at.isoformat() if transaction.invoice_expires_at else None,
        }

    if transaction.meetup_order:
        payload['meetup_order_id'] = transaction.meetup_order.id
        payload['order_number'] = transaction.meetup_order.order_number

    if transaction.order:
        payload['order_number'] = transaction.order.order_number

    return payload


def build_meetup_invoice_memo(meetup: Meetup, participant_data: dict, user) -> str:
    participant_name = participant_data.get('participant_name') or '참가자'
    quantity_label = len(participant_data.get('selected_options', []))
    quantity_text = f"옵션 {quantity_label}개" if quantity_label else "옵션 없음"
    payer_identifier = getattr(user, 'username', None) or getattr(user, 'email', None) or str(user.id)
    memo = f"{meetup.name} / {participant_name} / {quantity_text} / 결제자 {payer_identifier}"
    return memo[:620] + '…' if len(memo) > 620 else memo

def meetup_checkout_payment(request, store_id, meetup_id):
    """밋업 결제 페이지"""
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
    meetup = get_object_or_404(
        Meetup,
        id=meetup_id,
        store=store,
        deleted_at__isnull=True
    )

    participant_data = request.session.get(f'meetup_participant_data_{meetup_id}')
    if not participant_data:
        messages.error(request, '참가자 정보가 없습니다. 다시 신청해주세요.')
        return redirect('meetup:meetup_checkout', store_id=store_id, meetup_id=meetup_id)

    total_price = int(participant_data.get('total_price', 0))

    if request.method == 'POST' and total_price == 0:
        try:
            order = create_meetup_order(
                meetup=meetup,
                participant_data=participant_data,
                is_free=True,
                user=request.user,
            )
            if f'meetup_participant_data_{meetup_id}' in request.session:
                del request.session[f'meetup_participant_data_{meetup_id}']
            messages.success(request, '무료 밋업 참가 신청이 완료되었습니다!')
            return redirect('meetup:meetup_checkout_complete', store_id=store_id, meetup_id=meetup_id, order_id=order.id)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("무료 밋업 주문 생성 실패: %s", exc)
            messages.error(request, '참가 신청 중 오류가 발생했습니다. 다시 시도해주세요.')

    payment_service_available = get_blink_service_for_store(store) is not None

    from myshop.models import SiteSettings
    site_settings = SiteSettings.get_settings()
    countdown_seconds = site_settings.meetup_countdown_seconds
    placeholder_uuid = '11111111-1111-1111-1111-111111111111'

    existing_transaction = None
    transaction_payload = None
    transaction_id = participant_data.get('transaction_id')
    if transaction_id:
        try:
            existing_transaction = PaymentTransaction.objects.select_related('meetup_order').get(
                id=transaction_id,
                user=request.user,
                store=store,
            )
            transaction_payload = serialize_transaction(existing_transaction)
        except (PaymentTransaction.DoesNotExist, ValueError):
            transaction_payload = None

    context = {
        'store': store,
        'meetup': meetup,
        'participant_data': participant_data,
        'payment_service_available': payment_service_available,
        'countdown_seconds': countdown_seconds,
        'workflow_start_url': reverse('meetup:meetup_start_payment_workflow', args=[store_id, meetup_id]),
        'workflow_status_url_template': reverse('meetup:meetup_payment_status', args=[store_id, meetup_id, placeholder_uuid]),
        'workflow_verify_url_template': reverse('meetup:meetup_verify_payment', args=[store_id, meetup_id, placeholder_uuid]),
        'workflow_cancel_url_template': reverse('meetup:meetup_cancel_payment', args=[store_id, meetup_id, placeholder_uuid]),
        'workflow_inventory_redirect_url': reverse('meetup:meetup_detail', args=[store_id, meetup_id]),
        'workflow_cart_url': reverse('meetup:meetup_checkout', args=[store_id, meetup_id]),
        'placeholder_uuid': placeholder_uuid,
        'existing_transaction': transaction_payload,
        'total_price': total_price,
    }

    return render(request, 'meetup/meetup_checkout.html', context)


@login_required
@require_POST
def meetup_start_payment_workflow(request, store_id, meetup_id):
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
    meetup = get_object_or_404(
        Meetup,
        id=meetup_id,
        store=store,
        deleted_at__isnull=True,
        is_active=True,
    )

    participant_data = request.session.get(f'meetup_participant_data_{meetup_id}')
    if not participant_data:
        return JsonResponse({'success': False, 'error': '참가자 정보가 없습니다.'}, status=400)

    amount_sats = int(participant_data.get('total_price', 0))
    if amount_sats <= 0:
        return JsonResponse({'success': False, 'error': '결제 금액이 올바르지 않습니다.'}, status=400)

    from myshop.models import SiteSettings
    site_settings = SiteSettings.get_settings()
    reservation_seconds = max(120, site_settings.meetup_countdown_seconds)
    soft_lock_minutes = max(1, (reservation_seconds + 59) // 60)

    processor = LightningPaymentProcessor(store)

    previous_transaction_id = participant_data.get('transaction_id')
    if previous_transaction_id:
        try:
            previous_transaction = PaymentTransaction.objects.select_related('meetup_order').get(
                id=previous_transaction_id,
                user=request.user,
                store=store,
            )
            if previous_transaction.status != PaymentTransaction.STATUS_COMPLETED:
                processor.cancel_transaction(previous_transaction, '밋업 결제 재시작', detail={'reason': 'restart'})
                if previous_transaction.meetup_order and previous_transaction.meetup_order.status == 'pending':
                    previous_transaction.meetup_order.status = 'cancelled'
                    previous_transaction.meetup_order.is_temporary_reserved = False
                    previous_transaction.meetup_order.auto_cancelled_reason = '밋업 결제 재시작'
                    previous_transaction.meetup_order.save(update_fields=[
                        'status',
                        'is_temporary_reserved',
                        'auto_cancelled_reason',
                        'updated_at',
                    ])
        except (PaymentTransaction.DoesNotExist, ValueError):
            pass
        participant_data.pop('transaction_id', None)
        participant_data.pop('payment_hash', None)
        participant_data.pop('payment_request', None)

    try:
        with transaction.atomic():
            locked_meetup = Meetup.objects.select_for_update().get(
                id=meetup.id,
                store=store,
                deleted_at__isnull=True,
            )
            if locked_meetup.max_participants and locked_meetup.current_participants >= locked_meetup.max_participants:
                return JsonResponse({'success': False, 'error': '밋업 정원이 가득 찼습니다.'}, status=409)

            pending_order = create_pending_meetup_order(
                locked_meetup,
                participant_data,
                user=request.user,
                reservation_seconds=reservation_seconds,
            )

        transaction = processor.create_transaction(
            user=request.user,
            amount_sats=amount_sats,
            currency='BTC',
            cart_items=None,
            soft_lock_ttl_minutes=soft_lock_minutes,
            metadata={
                'participant': participant_data,
                'meetup_id': meetup.id,
                'meetup_order_id': pending_order.id,
            },
            prepare_message='밋업 참가 정보 확인 완료',
            prepare_detail={
                'meetup_order_id': pending_order.id,
                'reservation_expires_at': pending_order.reservation_expires_at.isoformat() if pending_order.reservation_expires_at else None,
                'amount_sats': amount_sats,
            },
        )
        transaction.meetup_order = pending_order
        transaction.save(update_fields=['meetup_order', 'updated_at'])

        invoice = processor.issue_invoice(
            transaction,
            memo=build_meetup_invoice_memo(meetup, participant_data, request.user),
            expires_in_minutes=max(1, min(soft_lock_minutes, 15)),
        )
    except ValueError as exc:
        logger.warning('밋업 결제 준비 실패: %s', exc)
        return JsonResponse({'success': False, 'error': str(exc)}, status=400)
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception('밋업 결제 준비 중 오류')
        return JsonResponse({'success': False, 'error': '결제 준비 중 오류가 발생했습니다.'}, status=500)

    participant_data['transaction_id'] = str(transaction.id)
    participant_data['meetup_order_id'] = pending_order.id
    participant_data['payment_hash'] = invoice['payment_hash']
    participant_data['payment_request'] = invoice['invoice']
    request.session[f'meetup_participant_data_{meetup_id}'] = participant_data

    return JsonResponse({
        'success': True,
        'transaction': serialize_transaction(transaction),
        'invoice': {
            'payment_hash': invoice['payment_hash'],
            'payment_request': invoice['invoice'],
            'expires_at': invoice.get('expires_at').isoformat() if invoice.get('expires_at') else None,
        },
        'reservation_expires_at': pending_order.reservation_expires_at.isoformat() if pending_order.reservation_expires_at else None,
    })


@login_required
@require_http_methods(['GET'])
def meetup_payment_status(request, store_id, meetup_id, transaction_id):
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
    meetup = get_object_or_404(
        Meetup,
        id=meetup_id,
        store=store,
        deleted_at__isnull=True,
    )

    try:
        transaction = PaymentTransaction.objects.select_related('meetup_order').get(
            id=transaction_id,
            user=request.user,
            store=store,
        )
    except (PaymentTransaction.DoesNotExist, ValueError):
        return JsonResponse({'success': False, 'error': '결제 정보를 찾을 수 없습니다.'}, status=404)

    payload = serialize_transaction(transaction)
    payload['meetup_id'] = meetup.id

    return JsonResponse({'success': True, 'transaction': payload})


@login_required
@require_POST
def meetup_verify_payment(request, store_id, meetup_id, transaction_id):
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
    meetup = get_object_or_404(
        Meetup,
        id=meetup_id,
        store=store,
        deleted_at__isnull=True,
    )

    try:
        transaction = PaymentTransaction.objects.select_related('meetup_order').get(
            id=transaction_id,
            user=request.user,
            store=store,
        )
    except (PaymentTransaction.DoesNotExist, ValueError):
        return JsonResponse({'success': False, 'error': '결제 정보를 찾을 수 없습니다.'}, status=404)

    processor = LightningPaymentProcessor(store)

    try:
        status_result = processor.check_user_payment(transaction)
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception('밋업 결제 상태 확인 실패 transaction=%s', transaction_id)
        return JsonResponse({'success': False, 'error': str(exc)}, status=500)

    status_value = status_result.get('status')
    participant_data = transaction.metadata.get('participant') if isinstance(transaction.metadata, dict) else None
    if not participant_data:
        participant_data = request.session.get(f'meetup_participant_data_{meetup_id}', {})

    if status_value == 'expired':
        processor.cancel_transaction(transaction, '인보이스 만료', detail=status_result)
        if transaction.meetup_order and transaction.meetup_order.status == 'pending':
            transaction.meetup_order.status = 'cancelled'
            transaction.meetup_order.is_temporary_reserved = False
            transaction.meetup_order.auto_cancelled_reason = '인보이스 만료'
            transaction.meetup_order.save(update_fields=[
                'status',
                'is_temporary_reserved',
                'auto_cancelled_reason',
                'updated_at',
            ])
        session_data = request.session.get(f'meetup_participant_data_{meetup_id}', {})
        session_data.pop('transaction_id', None)
        session_data.pop('payment_hash', None)
        session_data.pop('payment_request', None)
        request.session[f'meetup_participant_data_{meetup_id}'] = session_data
        return JsonResponse({'success': False, 'error': '인보이스가 만료되었습니다.', 'transaction': serialize_transaction(transaction)}, status=400)

    if status_value != 'paid':
        return JsonResponse({'success': True, 'status': status_value, 'transaction': serialize_transaction(transaction)})

    meetup_order = transaction.meetup_order
    if not meetup_order and isinstance(transaction.metadata, dict):
        meetup_order_id = transaction.metadata.get('meetup_order_id')
        if meetup_order_id:
            meetup_order = MeetupOrder.objects.filter(id=meetup_order_id).first()

    if not meetup_order:
        return JsonResponse({'success': False, 'error': '주문 정보를 찾을 수 없습니다.'}, status=500)

    participant_data['payment_hash'] = transaction.payment_hash
    participant_data['payment_request'] = transaction.payment_request
    finalize_meetup_order_from_transaction(
        meetup_order,
        participant_data,
        payment_hash=transaction.payment_hash,
        payment_request=transaction.payment_request,
    )

    settlement_payload = {'status': status_result.get('raw_status'), 'provider': 'blink'}
    processor.mark_settlement(transaction, tx_payload=settlement_payload)
    processor.finalize_meetup_order(transaction, meetup_order)

    try:
        from .services import send_meetup_notification_email, send_meetup_participant_confirmation_email

        send_meetup_notification_email(meetup_order)
        send_meetup_participant_confirmation_email(meetup_order)
    except Exception as exc:  # pylint: disable=broad-except
        logger.error('밋업 결제 이메일 발송 실패 - order_id=%s, error=%s', meetup_order.id, exc)

    if f'meetup_participant_data_{meetup_id}' in request.session:
        del request.session[f'meetup_participant_data_{meetup_id}']

    redirect_url = reverse('meetup:meetup_checkout_complete', args=[store_id, meetup_id, meetup_order.id])

    payload = serialize_transaction(transaction)
    payload['redirect_url'] = redirect_url

    return JsonResponse({
        'success': True,
        'status': status_value,
        'transaction': payload,
        'order': {
            'id': meetup_order.id,
            'order_number': meetup_order.order_number,
            'total_price': meetup_order.total_price,
        },
        'redirect_url': redirect_url,
    })


@login_required
@require_POST
def meetup_cancel_payment(request, store_id, meetup_id, transaction_id):
    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        payload = {}

    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)

    try:
        transaction = PaymentTransaction.objects.select_related('meetup_order').get(
            id=transaction_id,
            user=request.user,
            store=store,
        )
    except (PaymentTransaction.DoesNotExist, ValueError):
        return JsonResponse({'success': False, 'error': '결제 정보를 찾을 수 없습니다.'}, status=404)

    processor = LightningPaymentProcessor(store)
    processor.cancel_transaction(transaction, '사용자 취소', detail=payload)

    if transaction.meetup_order and transaction.meetup_order.status == 'pending':
        order = transaction.meetup_order
        order.status = 'cancelled'
        order.is_temporary_reserved = False
        order.auto_cancelled_reason = '사용자 취소'
        order.save(update_fields=[
            'status',
            'is_temporary_reserved',
            'auto_cancelled_reason',
            'updated_at',
        ])

    session_data = request.session.get(f'meetup_participant_data_{meetup_id}', {})
    session_data.pop('transaction_id', None)
    session_data.pop('payment_hash', None)
    session_data.pop('payment_request', None)
    request.session[f'meetup_participant_data_{meetup_id}'] = session_data

    return JsonResponse({'success': True, 'transaction': serialize_transaction(transaction)})
