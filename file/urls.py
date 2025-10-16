from django.urls import path
from . import views

app_name = 'file'

urlpatterns = [
    # 파일 목록/상세
    path('<str:store_id>/files/', views.file_list, name='file_list'),
    path('<str:store_id>/files/<int:file_id>/', views.file_detail, name='file_detail'),
    
    # 파일 관리 (스토어 주인장용)
    path('<str:store_id>/files/add/', views.add_file, name='add_file'),
    path('<str:store_id>/files/<int:file_id>/edit/', views.edit_file, name='edit_file'),
    path('<str:store_id>/files/<int:file_id>/delete/', views.delete_file, name='delete_file'),
    path('<str:store_id>/files/manage/', views.file_manage, name='file_manage'),
    path('<str:store_id>/files/orders/', views.file_orders, name='file_orders'),
    path('<str:store_id>/files/payment-transactions/', views.file_payment_transactions, name='file_payment_transactions'),
    
    # 구매/다운로드
    path('<str:store_id>/files/<int:file_id>/checkout/', views.file_checkout, name='file_checkout'),
    path(
        '<str:store_id>/files/<int:file_id>/checkout/workflow/start/',
        views.file_start_payment_workflow,
        name='file_start_payment_workflow',
    ),
    path(
        '<str:store_id>/files/<int:file_id>/checkout/workflow/<uuid:transaction_id>/status/',
        views.file_payment_status,
        name='file_payment_status',
    ),
    path(
        '<str:store_id>/files/<int:file_id>/checkout/workflow/<uuid:transaction_id>/verify/',
        views.file_verify_payment,
        name='file_verify_payment',
    ),
    path(
        '<str:store_id>/files/<int:file_id>/checkout/workflow/<uuid:transaction_id>/cancel/',
        views.file_cancel_payment,
        name='file_cancel_payment',
    ),
    path('<str:store_id>/files/<int:file_id>/download/', views.download_file, name='download_file'),
    path('complete/<int:order_id>/', views.file_complete, name='file_complete'),
    path('<str:store_id>/files/<int:file_id>/toggle-closure/', views.toggle_file_temporary_closure, name='toggle_file_temporary_closure'),
]
