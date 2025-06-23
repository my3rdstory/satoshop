from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('lightning-login/', views.lightning_login_view, name='lightning_login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('mypage/', views.MyPageView.as_view(), name='mypage'),
    path('change-password/', views.ChangePasswordView.as_view(), name='change_password'),
    
    # 구매 내역
    path('my-purchases/', views.my_purchases, name='my_purchases'),
    path('purchase/<str:order_number>/', views.purchase_detail, name='purchase_detail'),
    path('purchase/<str:order_number>/download/', views.download_order_txt, name='download_order_txt'),
    
    # LNURL-auth (lnauth-django 호환)
    path('ln-auth-get-url/', views.create_lnurl_auth, name='ln_auth_url_provider'),
    path('ln-auth/', views.lnurl_auth_callback, name='lnurl_auth_callback'),
    path('check-lightning-auth/', views.check_lightning_auth_status, name='check_lightning_auth'),
    
    # 라이트닝 지갑 연동
    path('link-lightning/', views.link_lightning_view, name='link_lightning'),
    path('ln-auth-get-link/', views.create_lnurl_link, name='ln_auth_link_provider'),
    path('ln-auth-check-link/', views.check_lightning_link, name='check_lightning_link'),
    path('unlink-lightning/', views.unlink_lightning_wallet, name='unlink_lightning_wallet'),
    path('delete-account/', views.delete_account, name='delete_account'),
] 