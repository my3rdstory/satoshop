from django.urls import path
from . import views

app_name = 'ln_payment'

urlpatterns = [
    path('lightning_payment/', views.lightning_payment, name='lightning_payment'),
    path('lightning_payment_complete/', views.lightning_payment_complete, name='lightning_payment_complete'),
    path('create_invoice/', views.create_invoice, name='create_invoice'),
    path('check_payment/', views.check_payment, name='check_payment'),
    path('test_blink_account/', views.test_blink_account, name='test_blink_account'),  # 테스트용

] 