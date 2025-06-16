from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
import json
import qrcode
import io
import base64
import time
import hashlib
import uuid
import requests
from stores.models import Store
import os
from django.contrib.auth.decorators import login_required
from .blink_service import BlinkAPIService, get_blink_service_for_store
import logging

logger = logging.getLogger(__name__)

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


