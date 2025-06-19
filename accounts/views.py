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
from django.http import HttpResponse
from django.utils import timezone

# orders 앱에서 필요한 모델들 import
from orders.models import PurchaseHistory, Order
from orders.services import CartService


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
            import logging
            logger = logging.getLogger(__name__)
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
            import logging
            logger = logging.getLogger(__name__)
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
def download_order_txt(request, order_number):
    """주문서 TXT 파일 다운로드"""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    # TXT 내용 생성
    content = f"""
===============================================
                주 문 서
===============================================

▣ 주문 정보
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
주문번호: {order.order_number}
주문일시: {order.created_at.strftime('%Y년 %m월 %d일 %H시 %M분')}
결제일시: {order.paid_at.strftime('%Y년 %m월 %d일 %H시 %M분') if order.paid_at else '-'}
주문상태: 결제 완료
결제방식: 라이트닝 네트워크 (Lightning Network)

▣ 스토어 정보
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
스토어명: {order.store.store_name}
판매자: {order.store.owner_name}"""

    if order.store.owner_phone:
        content += f"\n연락처: {order.store.owner_phone}"
    
    if order.store.chat_channel:
        content += f"\n소통채널: {order.store.chat_channel}"

    content += f"""

▣ 주문자 정보
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
이름: {order.buyer_name}
연락처: {order.buyer_phone}
이메일: {order.buyer_email}

▣ 배송지 정보
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
우편번호: {order.shipping_postal_code}
주소: {order.shipping_address}"""

    if order.shipping_detail_address:
        content += f"\n상세주소: {order.shipping_detail_address}"

    if order.order_memo:
        content += f"\n배송요청사항: {order.order_memo}"

    content += f"""

▣ 주문 상품 ({order.items.count()}개)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

    for i, item in enumerate(order.items.all(), 1):
        content += f"""

{i}. {item.product_title}
   - 수량: {item.quantity}개
   - 단가: {item.product_price:,.0f} sats"""
        
        if item.options_price > 0:
            content += f"\n   - 옵션추가: {item.options_price:,.0f} sats"
        
        if item.selected_options:
            content += "\n   - 선택옵션:"
            for option_name, choice_name in item.selected_options.items():
                content += f" {option_name}({choice_name})"
        
        content += f"\n   - 소계: {item.total_price:,.0f} sats"

    content += f"""

▣ 결제 내역
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
상품 금액: {order.subtotal:,.0f} sats
배송비: {order.shipping_fee:,.0f} sats
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
총 결제 금액: {order.total_amount:,.0f} sats

▣ 비트코인 관련 정보
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• 결제 네트워크: 라이트닝 네트워크 (Lightning Network)
• 단위: sats (사토시, 1 BTC = 100,000,000 sats)
• 특징: 즉시 결제, 낮은 수수료, 확장성

※ 이 주문서는 SatoShop에서 자동 생성된 문서입니다.
   문의사항이 있으시면 스토어 판매자에게 연락해주세요.

생성일시: {timezone.now().strftime('%Y년 %m월 %d일 %H시 %M분')}
===============================================
"""

    # HTTP 응답 생성
    response = HttpResponse(content, content_type='text/plain; charset=utf-8')
    filename = f"주문서_{order.order_number}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.txt"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response
