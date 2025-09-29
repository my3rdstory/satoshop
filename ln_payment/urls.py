from django.urls import path
from . import views

app_name = 'ln_payment'

urlpatterns = [
    path('lightning_payment/', views.lightning_payment, name='lightning_payment'),
    path('lightning_payment_complete/', views.lightning_payment_complete, name='lightning_payment_complete'),
    path('process/', views.payment_process, name='payment_process'),
    path('create_invoice/', views.create_invoice, name='create_invoice'),
    path('check_payment/', views.check_payment, name='check_payment'),
    path('test_blink_account/', views.test_blink_account, name='test_blink_account'),  # 테스트용
    path('workflow/start/', views.start_payment_workflow, name='workflow_start'),
    path('workflow/<uuid:transaction_id>/status/', views.get_payment_status, name='workflow_status'),
    path('workflow/<uuid:transaction_id>/invoice/', views.recreate_invoice, name='workflow_recreate_invoice'),
    path('workflow/<uuid:transaction_id>/cancel/', views.cancel_payment, name='workflow_cancel'),
    path('workflow/<uuid:transaction_id>/verify/', views.verify_payment, name='workflow_verify'),
    path('webhook/blink/', views.blink_webhook, name='blink_webhook'),

] 
