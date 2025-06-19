from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('mypage/', views.MyPageView.as_view(), name='mypage'),
    path('change-password/', views.ChangePasswordView.as_view(), name='change_password'),
    
    # 구매 내역
    path('my-purchases/', views.my_purchases, name='my_purchases'),
    path('purchase/<str:order_number>/', views.purchase_detail, name='purchase_detail'),
    path('purchase/<str:order_number>/download/', views.download_order_txt, name='download_order_txt'),
] 