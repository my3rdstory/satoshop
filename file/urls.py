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
    
    # 구매/다운로드
    path('<str:store_id>/files/<int:file_id>/checkout/', views.file_checkout, name='file_checkout'),
    path('<str:store_id>/files/<int:file_id>/download/', views.download_file, name='download_file'),
    path('complete/<int:order_id>/', views.file_complete, name='file_complete'),
    
    # AJAX 엔드포인트
    path('ajax/create-invoice/', views.create_file_invoice, name='create_file_invoice'),
    path('ajax/check-payment/', views.check_file_payment, name='check_file_payment'),
    path('ajax/cancel-payment/', views.cancel_file_payment, name='cancel_file_payment'),
    path('<str:store_id>/files/<int:file_id>/toggle-closure/', views.toggle_file_temporary_closure, name='toggle_file_temporary_closure'),
]