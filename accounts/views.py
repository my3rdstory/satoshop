from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, TemplateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.views import View
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.models import User
from django.conf import settings
import json
import logging
from django.core.cache import cache

# orders 앱에서 필요한 모델들 import
from orders.models import PurchaseHistory, Order
from orders.services import CartService
from .models import LightningUser
from .lnurl_service import LNURLAuthService, LNURLAuthException, InvalidSigException

logger = logging.getLogger(__name__)

class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    
    def form_valid(self, form):
        """로그인 성공 후 세션 장바구니를 DB로 마이그레이션"""
        response = super().form_valid(form)
        
        # 세션 장바구니를 DB로 마이그레이션
        try:
            cart_service = CartService(self.request)
            cart_service.migrate_session_to_db()
        except Exception as e:
            # 마이그레이션 실패해도 로그인은 진행
            logger.warning(f"장바구니 마이그레이션 실패: {e}")
        
        return response
    
    def get_success_url(self):
        """로그인 성공 후 리다이렉트 처리"""
        # next 파라미터가 있으면 우선 처리
        next_url = self.request.POST.get('next') or self.request.GET.get('next')
        
        # 스토어를 가진 사용자인지 확인
        from stores.models import Store
        has_store = False
        store_url = None
        
        try:
            store = Store.objects.filter(
                owner=self.request.user, 
                deleted_at__isnull=True,
                is_active=True
            ).first()
            
            if store:
                has_store = True
                store_url = f'/stores/{store.store_id}/'
        except Exception:
            pass  # 에러 발생 시 기본 URL로 이동
        
        # 스토어 주인장인 경우: next가 있으면 next로, 없으면 스토어 홈으로
        if has_store:
            if next_url:
                return next_url
            return store_url
        
        # 스토어 주인장이 아닌 경우: next가 있으면 next로, 없으면 홈으로
        if next_url:
            return next_url
            
        # 기본 홈페이지로 이동
        return reverse_lazy('myshop:home')


class CustomLogoutView(LogoutView):
    http_method_names = ['get', 'post']  # GET 요청도 허용
    
    def get_success_url(self):
        # next 파라미터가 있으면 해당 URL로, 없으면 기본 설정으로
        next_url = self.request.POST.get('next') or self.request.GET.get('next')
        if next_url:
            from urllib.parse import unquote
            return unquote(next_url)
        return super().get_success_url()


class SignUpView(CreateView):
    form_class = UserCreationForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('accounts:login')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        
        # 세션 장바구니를 DB로 마이그레이션
        try:
            cart_service = CartService(self.request)
            cart_service.migrate_session_to_db()
        except Exception as e:
            # 마이그레이션 실패해도 회원가입은 진행
            logger.warning(f"장바구니 마이그레이션 실패: {e}")
        
        # next 파라미터가 있으면 해당 URL로 리다이렉트
        next_url = self.request.POST.get('next') or self.request.GET.get('next')
        if next_url:
            return redirect(next_url)
        
        return redirect('myshop:home')


@method_decorator(login_required, name='dispatch')
class MyPageView(TemplateView):
    template_name = 'accounts/mypage.html'


@method_decorator(login_required, name='dispatch')
class ChangePasswordView(View):
    template_name = 'accounts/change_password.html'
    
    def get(self, request):
        password_form = PasswordChangeForm(user=request.user)
        return render(request, self.template_name, {
            'password_form': password_form,
        })
    
    def post(self, request):
        password_form = PasswordChangeForm(user=request.user, data=request.POST)
        
        if password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)  # 세션 유지
            messages.success(request, '비밀번호가 성공적으로 변경되었습니다.')
            return redirect('accounts:mypage')
        else:
            messages.error(request, '비밀번호 변경 중 오류가 발생했습니다.')
        
        return render(request, self.template_name, {
            'password_form': password_form,
        })


@login_required
def my_purchases(request):
    """구매 내역 목록"""
    purchases = PurchaseHistory.objects.filter(user=request.user).select_related(
        'order', 'order__store'
    ).prefetch_related(
        'order__items', 'order__items__product', 'order__items__product__images'
    ).order_by('-purchase_date')
    
    context = {
        'purchases': purchases,
    }
    return render(request, 'accounts/my_purchases.html', context)


@login_required
def purchase_detail(request, order_number):
    """구매 상세 정보"""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    context = {
        'order': order,
    }
    return render(request, 'accounts/purchase_detail.html', context)


@login_required
def my_meetup_orders(request):
    """내 밋업 참가 내역 (모든 스토어 통합)"""
    from meetup.models import MeetupOrder
    from django.core.paginator import Paginator
    
    # 사용자의 확정된 밋업 주문만 조회 (pending 상태는 제외)
    meetup_orders = MeetupOrder.objects.filter(
        user=request.user,
        status__in=['confirmed', 'completed']
    ).select_related(
        'meetup', 'meetup__store'
    ).prefetch_related(
        'selected_options'
    ).order_by('-created_at')
    
    # 페이지네이션
    paginator = Paginator(meetup_orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'meetup_orders': page_obj.object_list,
    }
    return render(request, 'accounts/my_meetup_orders.html', context)


@login_required
def download_order_txt(request, order_number):
    """주문서 TXT 파일 다운로드"""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    # TXT 내용 생성 (새로운 포맷터 사용)
    from orders.formatters import generate_txt_order
    content = generate_txt_order(order)

    # HTTP 응답 생성 (BOM 추가로 인코딩 문제 해결)
    content_with_bom = '\ufeff' + content  # UTF-8 BOM 추가
    response = HttpResponse(content_with_bom, content_type='text/plain; charset=utf-8')
    
    # 파일명 인코딩 처리 (모바일 브라우저 호환성 개선)
    filename = f"주문서_{order.order_number}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.txt"
    try:
        # RFC 5987 방식으로 UTF-8 파일명 인코딩
        from urllib.parse import quote
        encoded_filename = quote(filename.encode('utf-8'))
        response['Content-Disposition'] = f'attachment; filename*=UTF-8\'\'{encoded_filename}'
    except:
        # 백업 방식: 영문 파일명 사용
        fallback_filename = f"order_{order.order_number}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.txt"
        response['Content-Disposition'] = f'attachment; filename="{fallback_filename}"'
    
    return response


def create_lnurl_auth(request):
    """LNURL-auth 세션 생성 (lnauth-django 방식)"""
    try:
        if not request.user.is_anonymous:
            return JsonResponse({
                'success': False,
                'error': '이미 로그인된 사용자입니다.'
            }, status=400)

        # action 파라미터 확인 (기본값: login)
        action = request.GET.get('action', 'login')
        if action not in ['login', 'register']:
            action = 'login'
        
        if settings.DEBUG:
            logger.debug(f"LNURL-auth 세션 생성 요청 - action: {action}")
        
        # LNURL 서비스 초기화
        lnurl_service = LNURLAuthService()
        
        # k1 생성
        k1_bytes = lnurl_service.generate_k1()
        
        # LNURL 생성
        lnurl = lnurl_service.get_auth_url(k1_bytes, action)
        
        if settings.DEBUG:
            logger.debug(f"LNURL-auth 세션 생성 완료: k1={k1_bytes.hex()[:16]}..., action={action}")
        
        return JsonResponse({
            'success': True,
            'lnurl': lnurl,
            'k1': k1_bytes.hex(),
            'action': action
        })
        
    except LNURLAuthException as e:
        logger.error(f"LNURL-auth 세션 생성 오류: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except Exception as e:
        logger.error(f"LNURL-auth 세션 생성 예외: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'오류가 발생했습니다: {str(e)}'
        }, status=500)


@csrf_exempt
def lnurl_auth_callback(request):
    """LNURL-auth 콜백 (lnauth-django 방식)"""
    try:
        logger.info(f"LNURL-auth 콜백 요청: method={request.method}, user={request.user}, GET={dict(request.GET)}")
        
        if request.method == 'GET':
            # sig와 key가 있으면 2단계 요청으로 처리
            if 'sig' in request.GET and 'key' in request.GET:
                logger.info("GET 요청이지만 sig/key가 있어서 2단계 요청으로 처리")
                # POST 처리 로직으로 이동
                data = request.GET
                k1_hex = data['k1']
                sig_hex = data['sig']
                key_hex = data['key']
                action = data.get('action', 'login')
                
                logger.info(f"LNURL-auth GET 서명 검증 시작 - k1: {k1_hex[:16]}..., action: {action}, key: {key_hex[:16]}...")
                
                # 서명 검증 및 인증 처리
                lnurl_service = LNURLAuthService()
                
                try:
                    # 서명 검증
                    lnurl_service.verify_ln_auth(k1_hex, sig_hex, key_hex, action)
                    logger.info("서명 검증 성공")
                    
                    # 사용자 인증/등록/연동
                    if action == 'link':
                        logger.info("연동 처리 시작")
                        # 연동 처리
                        user, is_linked = lnurl_service.authenticate_user(key_hex, action, k1_hex)
                        logger.info(f"연동 완료: user={user.username}")
                        
                        return JsonResponse({
                            'status': 'OK',
                            'event': 'link-success'
                        })
                    else:
                        # 로그인/회원가입의 경우 이미 인증된 사용자면 오류
                        if not request.user.is_anonymous:
                            logger.error(f"로그인/회원가입 GET 요청이지만 이미 인증된 상태: {request.user.username}")
                            return JsonResponse({
                                'status': 'ERROR',
                                'reason': '이미 인증된 사용자입니다.'
                            }, status=400)
                        
                        print(f"🚀 GET 로그인/회원가입 처리 시작: action={action}")
                        logger.info(f"로그인/회원가입 처리 시작: action={action}")
                        # 로그인/회원가입
                        user, is_new = lnurl_service.authenticate_user(key_hex, action)
                        
                        print(f"✅ GET 사용자 인증 완료: user={user.username}, is_new={is_new}")
                        logger.info(f"사용자 인증 완료: user={user.username}, is_new={is_new}")
                        
                        # 로그인 성공 정보를 캐시에 저장 (브라우저에서 확인할 수 있도록)
                        auth_cache_key = f"lnauth-success-{k1_hex}"
                        print(f"🔑 GET 캐시 키 생성: {auth_cache_key}")
                        auth_data = {
                            'user_id': user.id,
                            'username': user.username,
                            'is_new': is_new,
                            'next_url': request.GET.get('next')
                        }
                        from django.core.cache import cache
                        cache.set(auth_cache_key, auth_data, timeout=300)  # 5분
                        print(f"💾 GET 인증 정보 캐시 저장: {auth_cache_key}, data={auth_data}")
                        logger.info(f"인증 정보 캐시 저장: {auth_cache_key}")
                        
                        return JsonResponse({
                            'status': 'OK',
                            'event': 'auth-signup' if is_new else 'auth-success'
                        })
                        
                except LNURLAuthException as e:
                    logger.warning(f"LNURL-auth GET 검증 실패: {str(e)}")
                    
                    # 에러 정보를 캐시에 저장 (클라이언트에서 확인할 수 있도록)
                    if action in ['login', 'register']:
                        error_cache_key = f"lnauth-error-{k1_hex}"
                        cache.set(error_cache_key, str(e), timeout=300)  # 5분
                        logger.info(f"GET 에러 정보 캐시 저장: {error_cache_key}")
                    elif action == 'link':
                        # 연동 에러는 k1과 공개키 둘 다로 저장
                        error_cache_key_k1 = f"lnauth-error-{k1_hex}"
                        error_cache_key_pubkey = f"lnauth-link-error-{key_hex}"
                        cache.set(error_cache_key_k1, str(e), timeout=300)  # 5분
                        cache.set(error_cache_key_pubkey, str(e), timeout=300)  # 5분
                        logger.info(f"GET 연동 에러 정보 캐시 저장: {error_cache_key_k1}, {error_cache_key_pubkey}")
                    
                    return JsonResponse({
                        'status': 'ERROR',
                        'reason': str(e)
                    }, status=400)
            
            # 1단계: 지갑이 QR 코드 정보를 요청
            required_params = ['tag', 'k1', 'action']
            for param in required_params:
                if param not in request.GET:
                    logger.error(f"필수 파라미터 누락: {param}")
                    return JsonResponse({
                        'status': 'ERROR',
                        'reason': f'필수 파라미터 누락: {param}'
                    }, status=400)
            
            if request.GET['tag'] != 'login':
                logger.error(f"잘못된 태그: {request.GET['tag']}")
                return JsonResponse({
                    'status': 'ERROR',
                    'reason': 'Invalid tag'
                }, status=400)
            
            k1_hex = request.GET['k1']
            action = request.GET['action']
            logger.info(f"LNURL-auth GET 요청: k1={k1_hex[:16]}..., action={action}")
            
            # 연동 액션의 경우 추가 검증
            if action == 'link':
                # 로그인 상태가 아니면 오류
                if request.user.is_anonymous:
                    logger.error("연동 요청이지만 로그인되지 않은 상태")
                    return JsonResponse({
                        'status': 'ERROR',
                        'reason': '라이트닝 연동은 로그인된 상태에서만 가능합니다.'
                    }, status=400)
                
                logger.info(f"연동 요청: user={request.user.username}")
                
                # 연동 세션을 위해 사용자 ID를 캐시에 저장
                from django.core.cache import cache
                timeout = getattr(settings, 'LNURL_AUTH_K1_TIMEOUT', 60 * 60)  # 1시간
                cache.set(f"lnauth-link-user-{k1_hex}", request.user.id, timeout=timeout)
                logger.info(f"사용자 ID 캐시 저장: lnauth-link-user-{k1_hex[:16]}... = {request.user.id}")
                
            else:
                # 로그인/회원가입의 경우 이미 인증된 사용자면 오류
                if not request.user.is_anonymous:
                    logger.error(f"로그인/회원가입 요청이지만 이미 인증된 상태: {request.user.username}")
                    return JsonResponse({
                        'status': 'ERROR',
                        'reason': '이미 인증된 사용자입니다.'
                    }, status=400)
            
            # LNURL 서비스로 응답 생성
            lnurl_service = LNURLAuthService()
            response_data = lnurl_service.create_lnurl_response(k1_hex)
            logger.info(f"LNURL 응답 생성 완료: {response_data}")
            
            return JsonResponse(response_data)
            
        elif request.method == 'POST':
            # 2단계: 지갑이 서명과 함께 인증 요청
            logger.info(f"LNURL-auth POST 요청: content_type={request.content_type}")
            
            # POST 데이터 파싱
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                logger.info(f"JSON 데이터: {data}")
            else:
                data = request.POST
                logger.info(f"POST 데이터: {dict(data)}")
                
            # URL 파라미터도 확인 (일부 지갑에서 GET 파라미터로 전송)
            if not data:
                data = request.GET
                logger.info(f"GET 파라미터로 폴백: {dict(data)}")
            
            required_params = ['k1', 'sig', 'key']
            for param in required_params:
                if param not in data:
                    logger.error(f"POST 요청에서 필수 파라미터 누락: {param}")
                    return JsonResponse({
                        'status': 'ERROR',
                        'reason': f'필수 파라미터 누락: {param}'
                    }, status=400)
            
            k1_hex = data['k1']
            sig_hex = data['sig']
            key_hex = data['key']
            action = data.get('action', 'login')
            
            logger.info(f"LNURL-auth 서명 검증 시작 - k1: {k1_hex[:16]}..., action: {action}, key: {key_hex[:16]}...")
            
            # LNURL 서비스로 검증 및 인증
            lnurl_service = LNURLAuthService()
            
            try:
                # 서명 검증
                lnurl_service.verify_ln_auth(k1_hex, sig_hex, key_hex, action)
                logger.info("서명 검증 성공")
                
                # 사용자 인증/등록/연동
                if action == 'link':
                    logger.info("연동 처리 시작")
                    # 연동 처리
                    user, is_linked = lnurl_service.authenticate_user(key_hex, action, k1_hex)
                    logger.info(f"연동 완료: user={user.username}")
                    
                    return JsonResponse({
                        'status': 'OK',
                        'event': 'link-success'
                    })
                else:
                    # 로그인/회원가입의 경우 이미 인증된 사용자면 오류
                    if not request.user.is_anonymous:
                        logger.error(f"로그인/회원가입 POST 요청이지만 이미 인증된 상태: {request.user.username}")
                        return JsonResponse({
                            'status': 'ERROR',
                            'reason': '이미 인증된 사용자입니다.'
                        }, status=400)
                    
                    print(f"🚀 로그인/회원가입 처리 시작: action={action}")
                    logger.info(f"로그인/회원가입 처리 시작: action={action}")
                    # 로그인/회원가입
                    user, is_new = lnurl_service.authenticate_user(key_hex, action)
                    
                    print(f"✅ 사용자 인증 완료: user={user.username}, is_new={is_new}")
                    logger.info(f"사용자 인증 완료: user={user.username}, is_new={is_new}")
                    
                    # 로그인 성공 정보를 캐시에 저장 (브라우저에서 확인할 수 있도록)
                    auth_cache_key = f"lnauth-success-{k1_hex}"
                    print(f"🔑 캐시 키 생성: {auth_cache_key}")
                    auth_data = {
                        'user_id': user.id,
                        'username': user.username,
                        'is_new': is_new,
                        'next_url': request.GET.get('next')
                    }
                    cache.set(auth_cache_key, auth_data, timeout=300)  # 5분
                    print(f"💾 인증 정보 캐시 저장: {auth_cache_key}, data={auth_data}")
                    logger.info(f"인증 정보 캐시 저장: {auth_cache_key}")
                    
                    if settings.DEBUG:
                        logger.debug(f"LNURL-auth 완료: user={user.username}, is_new={is_new}")
                    
                    return JsonResponse({
                        'status': 'OK',
                        'event': 'auth-signup' if is_new else 'auth-success'
                    })
                
            except LNURLAuthException as e:
                logger.warning(f"LNURL-auth 검증 실패: {str(e)}")
                
                # 에러 정보를 캐시에 저장 (클라이언트에서 확인할 수 있도록)
                if action in ['login', 'register']:
                    error_cache_key = f"lnauth-error-{k1_hex}"
                    cache.set(error_cache_key, str(e), timeout=300)  # 5분
                    logger.info(f"에러 정보 캐시 저장: {error_cache_key}")
                
                return JsonResponse({
                    'status': 'ERROR',
                    'reason': str(e)
                }, status=400)
        
        else:
            logger.error(f"지원하지 않는 HTTP 메서드: {request.method}")
            return JsonResponse({
                'status': 'ERROR',
                'reason': 'Method not allowed'
            }, status=405)
        
    except Exception as e:
        logger.error(f"LNURL-auth 콜백 오류: {str(e)}", exc_info=True)
        return JsonResponse({
            'status': 'ERROR',
            'reason': 'Internal server error'
        }, status=500)


def lightning_login_view(request):
    """라이트닝 로그인 페이지"""
    # 이미 로그인된 경우 리다이렉트
    if request.user.is_authenticated:
        next_url = request.GET.get('next')
        if next_url:
            return redirect(next_url)
        return redirect('accounts:mypage')
    
    return render(request, 'accounts/lightning_login.html')


@login_required
def link_lightning_view(request):
    """라이트닝 인증 연동 페이지"""
    # 이미 연동된 경우 마이페이지로 리다이렉트
    if hasattr(request.user, 'lightning_profile'):
        messages.info(request, '이미 라이트닝 지갑이 연동되어 있습니다.')
        return redirect('accounts:mypage')
    
    return render(request, 'accounts/link_lightning.html')


def check_lightning_auth_status(request):
    """라이트닝 인증 상태 확인 및 로그인 처리"""
    try:
        # 이미 로그인된 경우
        if request.user.is_authenticated:
            return JsonResponse({
                'authenticated': True,
                'username': request.user.username
            })
        
        # k1 파라미터로 인증 성공 여부 확인
        k1 = request.GET.get('k1')
        if not k1:
            return JsonResponse({'authenticated': False})
        
        # 캐시에서 인증 성공 정보 확인
        auth_cache_key = f"lnauth-success-{k1}"
        auth_data = cache.get(auth_cache_key)
        
        # 캐시에서 에러 정보 확인
        error_cache_key = f"lnauth-error-{k1}"
        error_data = cache.get(error_cache_key)
        
        print(f"🔍 인증 상태 확인: k1={k1[:16]}..., cache_key={auth_cache_key}, data={auth_data}, error={error_data}")
        logger.info(f"인증 상태 확인: k1={k1[:16]}..., cache_key={auth_cache_key}, data={auth_data}, error={error_data}")
        
        # 에러가 있으면 에러 반환
        if error_data:
            cache.delete(error_cache_key)  # 에러는 한 번만 반환
            return JsonResponse({
                'authenticated': False,
                'error': error_data
            })
        
        if auth_data:
            # 인증 성공한 사용자 정보가 있으면 실제 로그인 처리
            try:
                user = User.objects.get(id=auth_data['user_id'])
                login(request, user)
                
                # 세션 장바구니를 DB로 마이그레이션
                try:
                    from orders.services import CartService
                    cart_service = CartService(request)
                    cart_service.migrate_session_to_db()
                except Exception as e:
                    logger.warning(f"장바구니 마이그레이션 실패: {e}")
                
                # 캐시에서 제거
                cache.delete(auth_cache_key)
                
                logger.info(f"라이트닝 로그인 완료: {user.username}")
                
                return JsonResponse({
                    'authenticated': True,
                    'username': user.username,
                    'is_new': auth_data.get('is_new', False),
                    'next_url': auth_data.get('next_url')
                })
                
            except User.DoesNotExist:
                logger.error(f"인증된 사용자를 찾을 수 없음: user_id={auth_data['user_id']}")
                cache.delete(auth_cache_key)
                return JsonResponse({'authenticated': False, 'error': '사용자를 찾을 수 없습니다.'})
        
        return JsonResponse({'authenticated': False})
        
    except Exception as e:
        logger.error(f"라이트닝 인증 상태 확인 오류: {str(e)}")
        return JsonResponse({
            'authenticated': False,
            'error': str(e)
        }, status=500)


@login_required
def check_lightning_link(request):
    """라이트닝 지갑 연동 상태 확인"""
    try:
        # k1 파라미터로 에러 정보도 확인
        k1 = request.GET.get('k1')
        if k1:
            # 캐시에서 에러 정보 확인 (k1 기반)
            error_cache_key = f"lnauth-error-{k1}"
            error_data = cache.get(error_cache_key)
            
            if error_data:
                cache.delete(error_cache_key)  # 에러는 한 번만 반환
                return JsonResponse({
                    'success': False,
                    'linked': False,
                    'error': error_data
                })
            
            # 사용자별 연동 에러 확인 (연동 세션 기반)
            user_error_cache_key = f"lnauth-link-error-user-{request.user.id}"
            user_error_data = cache.get(user_error_cache_key)
            
            if user_error_data:
                cache.delete(user_error_cache_key)  # 에러는 한 번만 반환
                return JsonResponse({
                    'success': False,
                    'linked': False,
                    'error': user_error_data
                })
        
        lightning_user = LightningUser.objects.get(user=request.user)
        return JsonResponse({
            'success': True,
            'linked': True,
            'public_key': lightning_user.public_key
        })
    except LightningUser.DoesNotExist:
        return JsonResponse({
            'success': True,
            'linked': False
        })
    except Exception as e:
        logger.error(f"연동 상태 확인 오류: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def create_lnurl_link(request):
    """라이트닝 지갑 연동용 LNURL 생성"""
    try:
        # 이미 연동된 경우 체크
        if hasattr(request.user, 'lightning_profile'):
            return JsonResponse({
                'success': False,
                'error': '이미 라이트닝 지갑이 연동되어 있습니다.'
            }, status=400)

        if settings.DEBUG:
            logger.debug(f"라이트닝 연동용 LNURL 생성 요청 - user: {request.user.username}")
        
        # LNURL 서비스 초기화
        lnurl_service = LNURLAuthService()
        
        # k1 생성
        k1_bytes = lnurl_service.generate_k1()
        
        # action=link로 LNURL 생성
        lnurl = lnurl_service.get_auth_url(k1_bytes, 'link')
        
        # 사용자 정보를 캐시에 저장 (연동용)
        cache_key = f"lnauth-link-user-{k1_bytes.hex()}"
        cache.set(cache_key, request.user.id, timeout=getattr(settings, 'LNURL_AUTH_K1_TIMEOUT', 60 * 60))
        
        if settings.DEBUG:
            logger.debug(f"라이트닝 연동용 LNURL 생성 완료: k1={k1_bytes.hex()[:16]}...")
        
        return JsonResponse({
            'success': True,
            'lnurl': lnurl,
            'k1': k1_bytes.hex(),
            'action': 'link'
        })
        
    except LNURLAuthException as e:
        logger.error(f"라이트닝 연동용 LNURL 생성 오류: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except Exception as e:
        logger.error(f"라이트닝 연동용 LNURL 생성 예외: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'오류가 발생했습니다: {str(e)}'
        }, status=500)


@login_required
@require_POST
def unlink_lightning_wallet(request):
    """라이트닝 지갑 연동 해제 (일반 계정용)"""
    try:
        # 연동된 라이트닝 프로필이 있는지 확인
        if not hasattr(request.user, 'lightning_profile'):
            return JsonResponse({
                'success': False,
                'error': '연동된 라이트닝 지갑이 없습니다.'
            }, status=400)
        
        # 비밀번호가 설정되지 않은 라이트닝 전용 계정인지 확인
        if not request.user.has_usable_password():
            return JsonResponse({
                'success': False,
                'error': '라이트닝 전용 계정은 연동 해제 시 계정이 삭제됩니다. 계정 삭제 기능을 사용해주세요.'
            }, status=400)
        
        # 연동 해제
        lightning_profile = request.user.lightning_profile
        public_key_short = lightning_profile.public_key[:16]
        lightning_profile.delete()
        
        if settings.DEBUG:
            logger.debug(f"라이트닝 지갑 연동 해제: user={request.user.username}, pubkey={public_key_short}...")
        
        return JsonResponse({
            'success': True,
            'message': '라이트닝 지갑 연동이 해제되었습니다.'
        })
            
    except Exception as e:
        logger.error(f"라이트닝 지갑 연동 해제 오류: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'오류가 발생했습니다: {str(e)}'
        }, status=500)


@login_required
@require_POST
def delete_account(request):
    """계정 완전 삭제"""
    try:
        # 수퍼어드민은 탈퇴 불가
        if request.user.is_superuser:
            return JsonResponse({
                'success': False,
                'error': '관리자 계정은 탈퇴할 수 없습니다.'
            }, status=400)
        
        user = request.user
        username = user.username
        
        if settings.DEBUG:
            logger.debug(f"계정 삭제 요청: user={username}")
        
        # 사용자 계정 완전 삭제 (연관된 모든 데이터도 CASCADE로 삭제됨)
        # Django의 User 모델은 related objects를 CASCADE로 삭제하므로
        # LightningUser, 주문내역, 스토어 등이 자동으로 삭제됩니다
        
        # 로그아웃 처리 (계정 삭제 전에)
        from django.contrib.auth import logout
        logout(request)
        
        # 계정 삭제
        user.delete()
        
        logger.info(f"계정 삭제 완료: username={username}")
        
        return JsonResponse({
            'success': True,
            'message': '계정이 성공적으로 삭제되었습니다.'
        })
            
    except Exception as e:
        logger.error(f"계정 삭제 오류: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'오류가 발생했습니다: {str(e)}'
        }, status=500)


@login_required
def meetup_participants_admin(request):
    """밋업 참가자 관리 어드민 페이지 (스태프만 접근 가능)"""
    from meetup.models import MeetupOrder
    from django.core.paginator import Paginator
    from django.contrib.auth.models import User
    from django.db.models import Count, Sum, Q
    
    # 스태프 권한 확인
    if not request.user.is_staff:
        messages.error(request, '관리자 권한이 필요합니다.')
        return redirect('accounts:mypage')
    
    # 검색 및 필터 처리
    search_query = request.GET.get('search', '').strip()
    store_filter = request.GET.get('store', '').strip()
    
    # 밋업 참가 내역이 있는 사용자들 조회
    user_ids_with_meetups = MeetupOrder.objects.filter(
        status__in=['confirmed', 'completed']
    ).values_list('user_id', flat=True).distinct()
    
    users_queryset = User.objects.filter(
        id__in=user_ids_with_meetups
    ).annotate(
        meetup_count=Count('meetuporder', filter=Q(meetuporder__status__in=['confirmed', 'completed'])),
        total_spent=Sum('meetuporder__total_price', filter=Q(meetuporder__status__in=['confirmed', 'completed']))
    ).select_related('lightning_profile').order_by('-meetup_count', '-date_joined')
    
    # 검색 필터 적용
    if search_query:
        users_queryset = users_queryset.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    # 스토어 필터 적용
    if store_filter:
        users_with_store_meetups = MeetupOrder.objects.filter(
            status__in=['confirmed', 'completed'],
            meetup__store__store_id=store_filter
        ).values_list('user_id', flat=True).distinct()
        users_queryset = users_queryset.filter(id__in=users_with_store_meetups)
    
    # 페이지네이션
    paginator = Paginator(users_queryset, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 스토어 목록 (필터용)
    from stores.models import Store
    stores_with_meetups = Store.objects.filter(
        meetups__meetuporder__status__in=['confirmed', 'completed']
    ).distinct().order_by('store_name')
    
    # 통계 정보
    total_participants = User.objects.filter(id__in=user_ids_with_meetups).count()
    total_meetup_orders = MeetupOrder.objects.filter(status__in=['confirmed', 'completed']).count()
    total_revenue = MeetupOrder.objects.filter(
        status__in=['confirmed', 'completed']
    ).aggregate(total=Sum('total_price'))['total'] or 0
    
    context = {
        'page_obj': page_obj,
        'users': page_obj.object_list,
        'search_query': search_query,
        'store_filter': store_filter,
        'stores_with_meetups': stores_with_meetups,
        'total_participants': total_participants,
        'total_meetup_orders': total_meetup_orders,
        'total_revenue': total_revenue,
    }
    return render(request, 'accounts/meetup_participants_admin.html', context)


@login_required
def meetup_participant_detail(request, user_id):
    """특정 사용자의 밋업 참가 상세 내역 (스태프만 접근 가능)"""
    from meetup.models import MeetupOrder
    from django.core.paginator import Paginator
    from django.contrib.auth.models import User
    from django.db.models import Sum
    
    # 스태프 권한 확인
    if not request.user.is_staff:
        messages.error(request, '관리자 권한이 필요합니다.')
        return redirect('accounts:mypage')
    
    # 사용자 정보 조회
    participant = get_object_or_404(User, id=user_id)
    
    # 사용자의 밋업 주문 내역 조회
    meetup_orders = MeetupOrder.objects.filter(
        user=participant,
        status__in=['confirmed', 'completed']
    ).select_related(
        'meetup', 'meetup__store'
    ).prefetch_related(
        'selected_options__option', 'selected_options__choice'
    ).order_by('-created_at')
    
    # 페이지네이션
    paginator = Paginator(meetup_orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 통계 정보
    total_meetups = meetup_orders.count()
    total_spent = meetup_orders.aggregate(total=Sum('total_price'))['total'] or 0
    unique_stores = meetup_orders.values_list('meetup__store__store_name', flat=True).distinct()
    
    context = {
        'participant': participant,
        'page_obj': page_obj,
        'meetup_orders': page_obj.object_list,
        'total_meetups': total_meetups,
        'total_spent': total_spent,
        'unique_stores': list(unique_stores),
    }
    return render(request, 'accounts/meetup_participant_detail.html', context)
