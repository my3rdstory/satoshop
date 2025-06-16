from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .services import UpbitExchangeService
import json
import os
from django.utils import timezone

# Create your views here.

def home(request):
    """홈페이지 뷰"""
    # force_home 파라미터가 있으면 리다이렉트하지 않고 홈페이지 표시
    if request.GET.get('force_home'):
        return render(request, 'myshop/home.html')
    
    # 로그인한 사용자가 스토어를 가지고 있으면 스토어 홈으로 이동
    if request.user.is_authenticated:
        from stores.models import Store
        try:
            store = Store.objects.filter(
                owner=request.user, 
                deleted_at__isnull=True,
                is_active=True
            ).first()
            
            if store:
                return redirect('stores:store_detail', store_id=store.store_id)
        except Exception:
            pass  # 에러 발생 시 홈페이지 계속 표시
    
    return render(request, 'myshop/home.html')

@require_http_methods(["GET"])
def get_exchange_rate(request):
    """현재 BTC/KRW 환율 API"""
    try:
        rate = UpbitExchangeService.get_current_rate()
        if rate:
            return JsonResponse({
                'success': True,
                'btc_krw_rate': float(rate.btc_krw_rate),
                'updated_at': rate.created_at.isoformat(),
            })
        else:
            return JsonResponse({
                'success': False,
                'error': '환율 데이터를 가져올 수 없습니다.'
            }, status=500)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@require_http_methods(["POST"])
@csrf_exempt
def convert_currency(request):
    """통화 변환 API"""
    try:
        data = json.loads(request.body)
        conversion_type = data.get('type')  # 'krw_to_sats' or 'sats_to_krw'
        amount = data.get('amount', 0)
        
        if conversion_type == 'krw_to_sats':
            result = UpbitExchangeService.convert_krw_to_sats(amount)
            return JsonResponse({
                'success': True,
                'result': result,
                'type': 'sats'
            })
        elif conversion_type == 'sats_to_krw':
            result = UpbitExchangeService.convert_sats_to_krw(amount)
            return JsonResponse({
                'success': True,
                'result': result,
                'type': 'krw'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': '잘못된 변환 타입입니다.'
            }, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '잘못된 JSON 형식입니다.'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@require_http_methods(["POST", "GET"])
@csrf_exempt
def update_exchange_rate_webhook(request):
    """외부 서비스에서 환율 업데이트를 트리거하는 웹훅 엔드포인트"""
    try:
        # 간단한 보안 토큰 확인 (옵션)
        auth_token = request.GET.get('token') or request.POST.get('token')
        expected_token = os.getenv('WEBHOOK_TOKEN', 'your-secret-token')
        
        if auth_token != expected_token:
            return JsonResponse({
                'success': False,
                'error': '인증 실패'
            }, status=401)
        
        # 환율 업데이트 실행
        exchange_rate = UpbitExchangeService.fetch_btc_krw_rate()
        
        if exchange_rate:
            return JsonResponse({
                'success': True,
                'message': '환율 업데이트 성공',
                'btc_krw_rate': float(exchange_rate.btc_krw_rate),
                'updated_at': exchange_rate.created_at.isoformat(),
                'timestamp': timezone.now().isoformat()
            })
        else:
            return JsonResponse({
                'success': False,
                'error': '환율 업데이트 실패',
                'timestamp': timezone.now().isoformat()
            }, status=500)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'서버 오류: {str(e)}',
            'timestamp': timezone.now().isoformat()
        }, status=500)
