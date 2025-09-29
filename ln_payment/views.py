from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.utils import timezone

import json
import qrcode
import io
import base64
import time
import hashlib
import uuid
import requests
import os
import logging

from orders.payment_utils import calculate_totals
from orders.services import CartService
from stores.models import Store

from .blink_service import BlinkAPIService, get_blink_service_for_store
from .models import PaymentTransaction
from .services import (
    LightningPaymentProcessor,
    PaymentStage,
    PaymentStatus,
    build_cart_items,
)

try:
    from svix.webhooks import Webhook, WebhookVerificationError
except ImportError:  # pragma: no cover - optional dependency
    Webhook = None
    class WebhookVerificationError(Exception):
        pass

logger = logging.getLogger(__name__)


def _build_invoice_memo(cart_items, total_amount_sats, user):
    """Blink 인보이스 메모 문자열을 구성한다."""
    if cart_items:
        first_title = cart_items[0].get('product_title') or '상품'
        if len(cart_items) == 1:
            product_label = first_title
        else:
            product_label = f"{first_title} 외 {len(cart_items) - 1}"
    else:
        product_label = '상품'

    total_quantity = sum(item.get('quantity', 1) for item in cart_items) if cart_items else 0
    payer_identifier = getattr(user, 'username', None) or getattr(user, 'email', None) or str(user.id)

    memo = f"{product_label} / 수량 {total_quantity} / 총액 {total_amount_sats} sats / 결제자 {payer_identifier}"
    # Blink description 필드는 최대 639자 → 넉넉히 절단
    return memo[:620] + '…' if len(memo) > 620 else memo

def lightning_payment(request):
    """라이트닝 결제 페이지"""
    store_id = request.GET.get('store_id')
    amount = request.GET.get('amount', '1000')  # 기본값 1000원
    
    store = None
    if store_id:
        store = get_object_or_404(Store, store_id=store_id, is_active=True)
    
    context = {
        'store': store,
        'amount': amount,
    }
    
    return render(request, 'ln_payment/lightning_payment.html', context)

def lightning_payment_complete(request):
    """결제 완료 페이지"""
    payment_hash = request.GET.get('payment_hash')
    store_id = request.GET.get('store_id')
    amount = request.GET.get('amount')
    
    store = None
    if store_id:
        try:
            store = Store.objects.get(store_id=store_id, is_active=True)
        except Store.DoesNotExist:
            pass
    
    context = {
        'payment_hash': payment_hash,
        'store': store,
        'amount': amount,
    }
    
    return render(request, 'ln_payment/lightning_payment_complete.html', context)


def _transaction_to_dict(transaction: PaymentTransaction) -> dict:
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
    return {
        'id': str(transaction.id),
        'status': transaction.status,
        'current_stage': transaction.current_stage,
        'payment_hash': transaction.payment_hash,
        'invoice_expires_at': transaction.invoice_expires_at.isoformat() if transaction.invoice_expires_at else None,
        'logs': logs,
        'created_at': transaction.created_at.isoformat(),
        'updated_at': transaction.updated_at.isoformat(),
        'order_number': transaction.order.order_number if transaction.order else None,
    }


def _build_summary_response(cart_summary, totals, shipping_data):
    groups, subtotal, shipping_fee, total = totals
    return {
        'subtotal_sats': subtotal,
        'shipping_fee_sats': shipping_fee,
        'total_sats': total,
        'items_count': cart_summary['total_items'],
        'stores': [
            {
                'store_id': group.store.store_id,
                'store_name': group.store.store_name,
                'subtotal': group.subtotal,
                'shipping_fee': group.shipping_fee,
                'total': group.total,
                'force_free_override': group.force_free_override,
            }
            for group in groups
        ],
        'shipping_data': shipping_data,
    }

def _workflow_error(message, *, error_code=None, status=200, extra=None):
    payload = {'success': False, 'error': message}
    if error_code:
        payload['error_code'] = error_code
    if extra:
        payload.update(extra)
    return JsonResponse(payload, status=status)



@login_required
def payment_process(request):
    cart_service = CartService(request)
    cart_items = cart_service.get_cart_items()
    if not cart_items:
        return redirect('orders:cart_view')

    shipping_data = request.session.get('shipping_data')
    if not shipping_data:
        return redirect('orders:shipping_info')

    groups, subtotal, shipping_fee, total = calculate_totals(cart_items)
    if not groups or len(groups) > 1:
        return redirect('orders:cart_view')

    primary_store = groups[0].store

    context = {
        'stores_with_items': groups,
        'subtotal_amount': subtotal,
        'total_shipping_fee': shipping_fee,
        'total_amount': total,
        'shipping_data': shipping_data,
        'store': primary_store,
    }
    return render(request, 'ln_payment/payment_process.html', context)


@login_required
@require_POST
def start_payment_workflow(request):
    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return _workflow_error('요청 형식이 올바르지 않습니다.', error_code='invalid_payload')

    cart_service = CartService(request)
    cart_items = cart_service.get_cart_items()
    if not cart_items:
        return _workflow_error('장바구니가 비어 있습니다.', error_code='empty_cart')

    groups, subtotal, shipping_fee, total = calculate_totals(cart_items)
    if not groups:
        return _workflow_error('스토어 정보를 확인할 수 없습니다.', error_code='store_missing')
    if len(groups) > 1:
        return _workflow_error('복수 스토어 결제는 지원되지 않습니다.', error_code='multiple_stores')

    store_group = groups[0]
    shipping_data = request.session.get('shipping_data') or data.get('shipping')
    if not shipping_data:
        return _workflow_error('배송 정보가 필요합니다.', error_code='shipping_missing')

    processor = LightningPaymentProcessor(store_group.store)
    try:
        transaction = processor.create_transaction(
            user=request.user,
            amount_sats=total,
            currency='BTC',
            cart_items=build_cart_items(cart_items),
            metadata={
                'shipping': shipping_data,
                'cart_snapshot': cart_items,
                'subtotal_sats': subtotal,
                'shipping_fee_sats': shipping_fee,
                'total_sats': total,
            },
        )
        memo_text = data.get('memo') or _build_invoice_memo(cart_items, total, request.user)
        invoice = processor.issue_invoice(
            transaction,
            memo=memo_text,
            expires_in_minutes=data.get('expires_in_minutes', 2),
        )
    except ValueError as exc:  # 재고 부족 등
        logger.warning('결제 준비 실패: %s', exc)
        message = str(exc) if str(exc) else '결제 준비에 실패했습니다.'
        if '재고' in message:
            message = '재고 부족으로 결제 진행이 어렵습니다. 재고 확인 후 다시 결제 진행해 주세요.'
        return _workflow_error(message, error_code='inventory_unavailable')
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception('결제 준비 중 오류')
        return JsonResponse({'success': False, 'error': '결제 준비 중 오류가 발생했습니다.'}, status=500)

    cart_summary = cart_service.get_cart_summary()
    summary = _build_summary_response(cart_summary, (groups, subtotal, shipping_fee, total), shipping_data)

    return JsonResponse({
        'success': True,
        'transaction': _transaction_to_dict(transaction),
        'invoice': {
            'payment_hash': invoice['payment_hash'],
            'payment_request': invoice['invoice'],
            'expires_at': invoice.get('expires_at').isoformat() if invoice.get('expires_at') else None,
        },
        'summary': summary,
    })


@login_required
@require_http_methods(['GET'])
def get_payment_status(request, transaction_id):
    transaction = get_object_or_404(PaymentTransaction, id=transaction_id, user=request.user)
    response = _transaction_to_dict(transaction)
    if transaction.payment_request:
        response['invoice'] = {
            'payment_request': transaction.payment_request,
            'payment_hash': transaction.payment_hash,
            'expires_at': transaction.invoice_expires_at.isoformat() if transaction.invoice_expires_at else None,
        }
    return JsonResponse({'success': True, 'transaction': response})


@login_required
@require_POST
def recreate_invoice(request, transaction_id):
    transaction = get_object_or_404(PaymentTransaction, id=transaction_id, user=request.user)
    if transaction.status == PaymentTransaction.STATUS_COMPLETED:
        return JsonResponse({'success': False, 'error': '이미 완료된 결제입니다.'}, status=400)

    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return _workflow_error('요청 형식이 올바르지 않습니다.', error_code='invalid_payload')

    processor = LightningPaymentProcessor(transaction.store)
    try:
        invoice = processor.recreate_invoice(
            transaction,
            memo=payload.get('memo', '상품 결제'),
            expires_in_minutes=payload.get('expires_in_minutes', 2),
            reason='인보이스 재생성',
        )
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception('인보이스 재생성 실패')
        return JsonResponse({'success': False, 'error': str(exc)}, status=500)

    return JsonResponse({
        'success': True,
        'invoice': {
            'payment_hash': invoice['payment_hash'],
            'payment_request': invoice['invoice'],
            'expires_at': invoice.get('expires_at').isoformat() if invoice.get('expires_at') else None,
        },
        'transaction': _transaction_to_dict(transaction),
    })


@login_required
@require_POST
def cancel_payment(request, transaction_id):
    transaction = get_object_or_404(PaymentTransaction, id=transaction_id, user=request.user)
    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        payload = {}
    processor = LightningPaymentProcessor(transaction.store)
    processor.cancel_transaction(transaction, '사용자 취소', detail=payload)
    return JsonResponse({'success': True, 'transaction': _transaction_to_dict(transaction)})


@login_required
@require_POST
def verify_payment(request, transaction_id):
    transaction = get_object_or_404(PaymentTransaction, id=transaction_id, user=request.user)
    processor = LightningPaymentProcessor(transaction.store)

    try:
        status_result = processor.check_user_payment(transaction)
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception('결제 상태 확인 실패 transaction=%s', transaction_id)
        return JsonResponse({'success': False, 'error': str(exc)}, status=500)

    status = status_result.get('status')
    if status == 'expired':
        processor.cancel_transaction(transaction, '인보이스 만료', detail=status_result)
        return JsonResponse({'success': False, 'error': '인보이스가 만료되었습니다.', 'transaction': _transaction_to_dict(transaction)}, status=400)

    if status != 'paid':
        return JsonResponse({'success': True, 'transaction': _transaction_to_dict(transaction), 'status': status})

    if transaction.order:
        response = _transaction_to_dict(transaction)
        response['redirect_url'] = f"/orders/checkout/complete/{transaction.order.order_number}/"
        return JsonResponse({'success': True, 'transaction': response, 'status': status})

    from orders.views import create_order_from_cart_service  # 지연 임포트로 순환 의존 방지

    shipping_data = transaction.metadata.get('shipping') if isinstance(transaction.metadata, dict) else None
    try:
        order_result = create_order_from_cart_service(request, transaction.payment_hash, shipping_data)
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception('주문 생성 실패 transaction=%s', transaction_id)
        processor.cancel_transaction(transaction, '주문 생성 실패', detail={'error': str(exc)})
        return JsonResponse({'success': False, 'error': '주문 생성에 실패했습니다.'}, status=500)

    primary_order = order_result['orders'][0] if order_result['orders'] else None
    if not primary_order:
        processor.cancel_transaction(transaction, '주문 생성 실패', detail={'reason': 'order_missing'})
        return JsonResponse({'success': False, 'error': '주문을 생성할 수 없습니다.'}, status=500)

    settlement_detail = processor.fetch_transactions(transaction.payment_hash) if transaction.payment_hash else {'success': False}
    if settlement_detail.get('success'):
        payload = {'transactions': settlement_detail.get('transactions')}
    else:
        payload = {'error': settlement_detail.get('error')}
    processor.mark_settlement(transaction, tx_payload=payload)
    processor.finalize_order(transaction, primary_order)

    response = _transaction_to_dict(transaction)
    response['redirect_url'] = f"/orders/checkout/complete/{primary_order.order_number}/"
    response['order_number'] = primary_order.order_number

    return JsonResponse({
        'success': True,
        'transaction': response,
        'status': status,
        'order': {
            'number': primary_order.order_number,
            'total_amount': primary_order.total_amount,
        }
    })


@csrf_exempt
@require_POST
def blink_webhook(request):
    """Blink/Svix webhook 수신."""
    secret = getattr(settings, 'BLINK_WEBHOOK_SECRET', None)
    payload = request.body

    try:
        if secret and Webhook:
            wh = Webhook(secret)
            data = wh.verify(payload, request.headers)
        else:
            data = json.loads(payload.decode('utf-8'))
    except (WebhookVerificationError, json.JSONDecodeError) as exc:
        logger.warning('Blink webhook 검증 실패: %s', exc)
        return JsonResponse({'success': False, 'error': 'invalid_signature'}, status=400)

    event_type = data.get('eventType') or data.get('event_type')
    if event_type != 'receive.lightning':
        return JsonResponse({'success': True})

    transaction_payload = data.get('transaction') or {}
    initiation = transaction_payload.get('initiationVia') or {}
    payment_hash = initiation.get('paymentHash') or data.get('paymentHash')

    if not payment_hash:
        return JsonResponse({'success': False, 'error': 'payment hash missing'}, status=400)

    try:
        transaction = PaymentTransaction.objects.select_related('store').get(payment_hash=payment_hash)
    except PaymentTransaction.DoesNotExist:
        logger.info('Blink webhook: 해당 payment_hash 트랜잭션 없음 %s', payment_hash)
        return JsonResponse({'success': True})

    processor = LightningPaymentProcessor(transaction.store)
    processor.mark_settlement(transaction, tx_payload=transaction_payload)

    return JsonResponse({'success': True})

@require_POST
def create_invoice(request):
    """인보이스 생성 API"""
    try:
        if settings.DEBUG:
            logger.debug(f"create_invoice 호출 - User: {request.user}, Authenticated: {request.user.is_authenticated}")
        
        # 로그인 확인
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': '로그인이 필요합니다.'}, status=401)
        
        # 요청 본문 파싱
        try:
            data = json.loads(request.body)
            if settings.DEBUG:
                logger.debug(f"요청 데이터: {data}")
        except json.JSONDecodeError as e:
            return JsonResponse({'success': False, 'error': f'JSON 파싱 오류: {str(e)}'}, status=400)
        
        amount = int(data.get('amount', 10))  # 기본값 10 사토시
        store_id = data.get('store_id')
        memo = data.get('memo', data.get('description', '상품 결제'))  # memo 우선, description은 호환성용
        
        if settings.DEBUG:
            logger.debug(f"파라미터 - amount: {amount}, store_id: {store_id}, memo: {memo}")
        
        # 스토어 정보 확인
        store = None
        if store_id:
            try:
                # 먼저 store_id로 찾기 시도 (사용자 소유의 스토어만)
                store = Store.objects.get(store_id=store_id, owner=request.user, deleted_at__isnull=True)
                if settings.DEBUG:
                    logger.debug(f"store_id로 스토어 찾음: {store}")
            except Store.DoesNotExist:
                if settings.DEBUG:
                    logger.debug(f"store_id {store_id}로 사용자 스토어를 찾을 수 없음, 다른 스토어 검색")
                # store_id로 찾을 수 없으면, 로그인한 사용자의 스토어 찾기 (진행 중인 것 우선)
                store = Store.objects.filter(
                    owner=request.user, 
                    deleted_at__isnull=True
                ).order_by('is_active', '-created_at').first()
                if settings.DEBUG:
                    logger.debug(f"사용자의 스토어: {store}")
                
                if not store:
                    return JsonResponse({'success': False, 'error': '존재하지 않는 스토어입니다.'}, status=404)
        else:
            if settings.DEBUG:
                logger.debug("store_id가 없음, 사용자의 스토어 검색")
            # store_id가 없으면 사용자의 스토어 찾기 (진행 중인 것 우선, 그 다음 활성화된 것)
            store = Store.objects.filter(
                owner=request.user, 
                deleted_at__isnull=True
            ).order_by('is_active', '-created_at').first()
            if settings.DEBUG:
                logger.debug(f"사용자의 스토어: {store}")
            
            if not store:
                return JsonResponse({'success': False, 'error': '스토어를 찾을 수 없습니다.'}, status=404)
        
        # BlinkAPIService 초기화
        try:
            blink_service = get_blink_service_for_store(store)
            if settings.DEBUG:
                logger.debug("BlinkAPIService 초기화 성공")
        except Exception as e:
            if settings.DEBUG:
                logger.error(f"BlinkAPIService 초기화 실패: {str(e)}")
            return JsonResponse({'success': False, 'error': f'Blink API 서비스 초기화 실패: {str(e)}'}, status=500)
        
        # 인보이스 생성
        if settings.DEBUG:
            logger.debug(f"인보이스 생성 시작: amount={amount} sats, memo={memo}")
        
        result = blink_service.create_invoice(
            amount_sats=amount,
            memo=memo,
            expires_in_minutes=15
        )
        
        if settings.DEBUG:
            logger.debug(f"인보이스 생성 결과: {result}")
        
        if not result['success']:
            return JsonResponse({
                'success': False,
                'error': result['error']
            }, status=500)
        
        # 응답 데이터 준비
        response_data = {
            'success': True,
            'payment_hash': result['payment_hash'],
            'invoice': result['invoice'],  # 클라이언트에서 QR 코드 생성용
            'amount': amount,
            'memo': memo,
            'expires_at': result['expires_at'].isoformat() if result.get('expires_at') else None,
        }
        
        if settings.DEBUG:
            logger.debug(f"응답 데이터: {response_data}")
        return JsonResponse(response_data)
        
    except json.JSONDecodeError as e:
        if settings.DEBUG:
            logger.error(f"JSON 디코딩 오류: {str(e)}")
        return JsonResponse({'success': False, 'error': f'JSON 파싱 오류: {str(e)}'}, status=400)
    except Exception as e:
        if settings.DEBUG:
            logger.error(f"create_invoice 예외 발생: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': f'오류가 발생했습니다: {str(e)}'}, status=500)

@require_POST
def check_payment(request):
    """결제 상태 확인 API"""
    try:
        if settings.DEBUG:
            logger.debug("check_payment 호출")
        
        # 로그인 확인
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': '로그인이 필요합니다.'}, status=401)
        
        # 요청 본문 파싱
        try:
            data = json.loads(request.body)
            if settings.DEBUG:
                logger.debug(f"결제 상태 확인 요청 데이터: {data}")
        except json.JSONDecodeError as e:
            return JsonResponse({'success': False, 'error': f'JSON 파싱 오류: {str(e)}'}, status=400)
        
        payment_hash = data.get('payment_hash')
        if not payment_hash:
            return JsonResponse({'success': False, 'error': 'payment_hash가 필요합니다.'}, status=400)
        
        if settings.DEBUG:
            logger.debug(f"결제 상태 확인: payment_hash={payment_hash}")
        
        # 사용자의 스토어 찾기 (API 정보를 위해) - 진행 중인 것 우선, 그 다음 활성화된 것
        store = Store.objects.filter(
            owner=request.user, 
            deleted_at__isnull=True
        ).order_by('is_active', '-created_at').first()
        
        if not store:
            return JsonResponse({'success': False, 'error': '스토어를 찾을 수 없습니다.'}, status=404)
        
        # BlinkAPIService 초기화
        try:
            blink_service = get_blink_service_for_store(store)
            if settings.DEBUG:
                logger.debug("스토어 정보로 BlinkAPIService 초기화")
        except Exception as e:
            if settings.DEBUG:
                logger.error(f"BlinkAPIService 초기화 실패: {str(e)}")
            return JsonResponse({'success': False, 'error': f'Blink API 서비스 초기화 실패: {str(e)}'}, status=500)
        
        # 결제 상태 확인
        result = blink_service.check_invoice_status(payment_hash)
        
        if settings.DEBUG:
            logger.debug(f"결제 상태 확인 결과: {result}")
        
        if not result['success']:
            return JsonResponse({
                'success': False,
                'status': 'error',
                'error': result['error']
            }, status=500)
        
        status = result['status']
        raw_status = result.get('raw_status', '')
        
        if settings.DEBUG:
            logger.debug(f"결제 상태: {status} (원본: {raw_status})")
        
        # 응답 구조를 프론트엔드가 이해할 수 있도록 명확하게 구성
        response_data = {
            'success': True,
            'status': status,  # 'pending', 'paid', 'expired'
            'payment_hash': payment_hash,
            'raw_status': raw_status,  # 디버깅용
        }
        
        if settings.DEBUG:
            logger.debug(f"최종 응답 데이터: {response_data}")
        
        return JsonResponse(response_data)
        
    except json.JSONDecodeError as e:
        if settings.DEBUG:
            logger.error(f"JSON 디코딩 오류: {str(e)}")
        return JsonResponse({'success': False, 'error': f'JSON 파싱 오류: {str(e)}'}, status=400)
    except Exception as e:
        if settings.DEBUG:
            logger.error(f"check_payment 예외 발생: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': f'오류가 발생했습니다: {str(e)}'}, status=500)

@login_required
def test_blink_account(request):
    """Blink 계정 정보 테스트 (관리자용)"""
    
    if not request.user.is_staff:
        return JsonResponse({'error': '관리자만 접근 가능합니다.'}, status=403)
    
    try:
        # 진행 중인 스토어 찾기
        store = Store.objects.filter(
            owner=request.user, 
            is_active=False
        ).first()
        
        if not store:
            return JsonResponse({'error': '진행 중인 스토어를 찾을 수 없습니다.'}, status=404)
        
        # BlinkAPIService 초기화
        blink_service = get_blink_service_for_store(store)
        
        # 계정 정보 조회
        result = blink_service.get_account_info()
        
        if not result['success']:
            return JsonResponse({
                'success': False,
                'error': result['error']
            })
        
        account_info = result['account_info']
        wallets = result['wallets']
        
        # 현재 설정된 월렛 ID와 비교
        current_wallet_id = store.get_blink_wallet_id()
        
        response_data = {
            'success': True,
            'current_wallet_id': current_wallet_id,
            'account_info': account_info,
            'available_wallets': wallets,
            'wallet_found': any(w['id'] == current_wallet_id for w in wallets)
        }
        
        return JsonResponse(response_data, json_dumps_params={'indent': 2})
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'테스트 중 오류 발생: {str(e)}'
        }, status=500)
