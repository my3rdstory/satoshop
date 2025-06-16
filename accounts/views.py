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

# orders 앱에서 필요한 모델들 import
from orders.models import PurchaseHistory, Order


class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    
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
