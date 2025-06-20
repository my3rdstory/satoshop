from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .services import UpbitExchangeService
import json
import os
from django.utils import timezone
from django.http import Http404
from django.conf import settings
import hashlib

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

@require_http_methods(["POST"])
@csrf_exempt
def update_exchange_rate_webhook(request):
    """외부 서비스에서 환율 업데이트를 트리거하는 웹훅 엔드포인트"""
    import logging
    logger = logging.getLogger(__name__)
    
    start_time = timezone.now()
    client_ip = request.META.get('REMOTE_ADDR', 'unknown')
    user_agent = request.META.get('HTTP_USER_AGENT', 'unknown')
    
    try:
        logger.info(f'웹훅 요청 수신 - IP: {client_ip}, User-Agent: {user_agent}')
        
        # JSON 데이터 파싱
        auth_token = None
        source = 'unknown'
        timestamp = None
        
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
                auth_token = data.get('token')
                source = data.get('source', 'unknown')
                timestamp = data.get('timestamp')
            except json.JSONDecodeError as e:
                logger.error(f'JSON 파싱 오류: {e}')
                return JsonResponse({
                    'success': False,
                    'error': '잘못된 JSON 형식입니다.',
                    'details': str(e),
                    'timestamp': timezone.now().isoformat()
                }, status=400)
        else:
            # Form 데이터에서 가져오기 (호환성)
            auth_token = request.POST.get('token')
            source = request.POST.get('source', 'unknown')
            timestamp = request.POST.get('timestamp')
        
        logger.info(f'웹훅 요청 상세 - 소스: {source}, 타임스탬프: {timestamp}')
        
        # 보안 토큰 확인
        expected_token = os.getenv('WEBHOOK_TOKEN')
        
        if not expected_token:
            logger.error('WEBHOOK_TOKEN 환경 변수가 설정되지 않았습니다.')
            return JsonResponse({
                'success': False,
                'error': '서버 설정 오류',
                'details': 'WEBHOOK_TOKEN 환경 변수가 설정되지 않았습니다.',
                'timestamp': timezone.now().isoformat()
            }, status=500)
        
        if not auth_token:
            logger.warning(f'토큰 없는 웹훅 시도 - 소스: {source}, IP: {client_ip}')
            return JsonResponse({
                'success': False,
                'error': '인증 토큰이 필요합니다.',
                'details': 'token 필드에 유효한 웹훅 토큰을 제공하세요.',
                'timestamp': timezone.now().isoformat()
            }, status=401)
        
        if auth_token != expected_token:
            logger.warning(f'웹훅 인증 실패 - 소스: {source}, IP: {client_ip}, 토큰 길이: {len(auth_token)}')
            return JsonResponse({
                'success': False,
                'error': '인증 실패',
                'details': '제공된 토큰이 유효하지 않습니다.',
                'timestamp': timezone.now().isoformat()
            }, status=401)
        
        logger.info(f'웹훅 인증 성공 - 소스: {source}, IP: {client_ip}')
        
        # 환율 업데이트 실행
        logger.info('환율 업데이트 시작')
        update_start_time = timezone.now()
        
        try:
            exchange_rate = UpbitExchangeService.fetch_btc_krw_rate()
            update_duration = (timezone.now() - update_start_time).total_seconds()
            
            if exchange_rate:
                logger.info(f'환율 업데이트 성공: 1 BTC = {exchange_rate.btc_krw_rate:,} KRW (소요시간: {update_duration:.2f}초)')
                
                # 성공 응답
                response_data = {
                    'success': True,
                    'message': '환율 업데이트 성공',
                    'btc_krw_rate': float(exchange_rate.btc_krw_rate),
                    'updated_at': exchange_rate.created_at.isoformat(),
                    'source': source,
                    'timestamp': timezone.now().isoformat(),
                    'processing_time': {
                        'update_duration': f'{update_duration:.2f}s',
                        'total_duration': f'{(timezone.now() - start_time).total_seconds():.2f}s'
                    }
                }
                
                return JsonResponse(response_data)
            else:
                logger.error('환율 업데이트 실패: API에서 데이터를 가져올 수 없음')
                return JsonResponse({
                    'success': False,
                    'error': '환율 업데이트 실패',
                    'details': 'API에서 데이터를 가져올 수 없습니다. 업비트 API 상태를 확인하세요.',
                    'source': source,
                    'timestamp': timezone.now().isoformat(),
                    'processing_time': f'{update_duration:.2f}s'
                }, status=500)
                
        except Exception as api_error:
            update_duration = (timezone.now() - update_start_time).total_seconds()
            logger.error(f'환율 업데이트 API 오류: {api_error}', exc_info=True)
            return JsonResponse({
                'success': False,
                'error': '환율 업데이트 중 오류 발생',
                'details': str(api_error),
                'source': source,
                'timestamp': timezone.now().isoformat(),
                'processing_time': f'{update_duration:.2f}s'
            }, status=500)
            
    except Exception as e:
        total_duration = (timezone.now() - start_time).total_seconds()
        logger.error(f'웹훅 처리 중 예상치 못한 오류: {e}', exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'서버 오류: {str(e)}',
            'details': '예상치 못한 오류가 발생했습니다. 서버 로그를 확인하세요.',
            'timestamp': timezone.now().isoformat(),
            'processing_time': f'{total_duration:.2f}s'
        }, status=500)

def document_view(request, doc_type):
    """문서 보기 페이지"""
    from .models import DocumentContent
    
    # 유효한 문서 타입인지 확인
    valid_doc_types = ['terms', 'privacy', 'refund']
    if doc_type not in valid_doc_types:
        raise Http404("존재하지 않는 문서입니다.")
    
    try:
        document = DocumentContent.objects.get(document_type=doc_type, is_active=True)
    except DocumentContent.DoesNotExist:
        raise Http404("문서를 찾을 수 없습니다.")
    
    context = {
        'document': document,
    }
    
    return render(request, 'myshop/document.html', context)

def offline_view(request):
    """PWA 오프라인 페이지"""
    return render(request, 'myshop/offline.html')

def manifest_view(request):
    """Web App Manifest 파일 서빙 (해시 기반 캐시 무효화 적용)"""
    try:
        manifest_path = os.path.join(settings.BASE_DIR, 'static', 'manifest.json')
        
        # 파일 내용 읽기
        with open(manifest_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 파일 해시 계산 (캐시 무효화용)
        file_hash = hashlib.md5(content.encode('utf-8')).hexdigest()[:8]
        
        # ETag 헤더로 조건부 요청 지원
        etag = f'"{file_hash}"'
        if_none_match = request.META.get('HTTP_IF_NONE_MATCH')
        
        if if_none_match == etag:
            # 파일이 변경되지 않았으면 304 응답
            response = HttpResponse(status=304)
            response['ETag'] = etag
            return response
        
        # JSON 파싱하여 동적으로 수정
        try:
            manifest_data = json.loads(content)
            
            # 매니페스트에 버전 정보 추가
            manifest_data['version'] = file_hash
            manifest_data['cache_version'] = f"v1.1.0-{file_hash}"
            
            # 아이콘 URL에 버전 파라미터 추가
            if 'icons' in manifest_data:
                for icon in manifest_data['icons']:
                    if 'src' in icon and not icon['src'].startswith('http'):
                        # 이미 버전 파라미터가 있으면 제거 후 새로 추가
                        src = icon['src'].split('?')[0]
                        icon['src'] = f"{src}?v={file_hash}"
            
            # 숏컷 아이콘에도 버전 파라미터 추가
            if 'shortcuts' in manifest_data:
                for shortcut in manifest_data['shortcuts']:
                    if 'icons' in shortcut:
                        for icon in shortcut['icons']:
                            if 'src' in icon and not icon['src'].startswith('http'):
                                # 이미 버전 파라미터가 있으면 제거 후 새로 추가
                                src = icon['src'].split('?')[0]
                                icon['src'] = f"{src}?v={file_hash}"
            
            # 수정된 내용을 JSON으로 변환
            content = json.dumps(manifest_data, ensure_ascii=False, indent=2)
            
        except json.JSONDecodeError:
            # JSON 파싱 실패시 원본 내용 사용
            pass
        
        # 응답 생성
        response = HttpResponse(content, content_type='application/manifest+json')
        
        # 캐시 헤더 설정 (더 적극적인 캐시 무효화)
        response['ETag'] = etag
        response['Cache-Control'] = 'public, max-age=300, must-revalidate'  # 5분 캐시, 재검증 필수
        response['Vary'] = 'Accept-Encoding'
        response['Last-Modified'] = request.build_absolute_uri().split('?')[0]  # URL 기반 Last-Modified
        
        return response
        
    except FileNotFoundError:
        return HttpResponse('Manifest not found', status=404)
    except Exception as e:
        return HttpResponse(f'Manifest error: {str(e)}', status=500)

def service_worker_view(request):
    """Service Worker 파일 서빙"""
    try:
        sw_path = os.path.join(settings.BASE_DIR, 'static', 'js', 'sw.js')
        with open(sw_path, 'r', encoding='utf-8') as f:
            content = f.read()
        response = HttpResponse(content, content_type='application/javascript')
        # Service Worker는 캐시되면 안 되므로 no-cache 헤더 추가
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response
    except FileNotFoundError:
        return HttpResponse('Service Worker not found', status=404)


def custom_404_view(request, exception):
    """커스텀 404 페이지"""
    return render(request, '404.html', status=404)


def custom_500_view(request):
    """커스텀 500 페이지"""
    return render(request, '500.html', status=500)
