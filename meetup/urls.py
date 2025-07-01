from django.urls import path
from . import views

app_name = 'meetup'

urlpatterns = [
    # 밋업 목록 (공개/관리자)
    path('<str:store_id>/', views.meetup_list, name='meetup_list'),
    path('<str:store_id>/list/', views.public_meetup_list, name='public_meetup_list'),
    
    # 밋업 추가
    path('<str:store_id>/add/', views.add_meetup, name='add_meetup'),
    
    # 밋업 현황 (구체적인 패턴을 먼저 배치)
    path('<str:store_id>/status/', views.meetup_status, name='meetup_status'),
    path('<str:store_id>/status/<str:meetup_id>/', views.meetup_status_detail, name='meetup_status_detail'),
    path('<str:store_id>/status/<str:meetup_id>/update_attendance/', views.update_attendance, name='update_attendance'),
    
    # 밋업 주문 내역
    path('<str:store_id>/orders/', views.meetup_orders, name='meetup_orders'),
    
    # 밋업 상세 (일반적인 패턴을 나중에 배치)
    path('<str:store_id>/<str:meetup_id>/', views.meetup_detail, name='meetup_detail'),
    
    # 밋업 통합수정
    path('<str:store_id>/<str:meetup_id>/edit/', views.edit_meetup_unified, name='edit_meetup_unified'),
    
    # 밋업 관리
    path('<str:store_id>/<str:meetup_id>/manage/', views.manage_meetup, name='manage_meetup'),
    
    # 밋업 체크아웃
    path('<str:store_id>/<str:meetup_id>/checkout/', views.meetup_checkout, name='meetup_checkout'),
    path('<str:store_id>/<str:meetup_id>/checkout/<int:order_id>/', views.meetup_checkout_payment, name='meetup_checkout_payment'),
    
    # 밋업 결제 관련 API
    path('<str:store_id>/<str:meetup_id>/checkout/<int:order_id>/create_invoice/', views.create_meetup_invoice, name='create_meetup_invoice'),
    path('<str:store_id>/<str:meetup_id>/checkout/<int:order_id>/check_payment/', views.check_meetup_payment_status, name='check_meetup_payment_status'),
    path('<str:store_id>/<str:meetup_id>/checkout/<int:order_id>/cancel_invoice/', views.cancel_meetup_invoice, name='cancel_meetup_invoice'),
    
    # 밋업 결제 완료
    path('<str:store_id>/<str:meetup_id>/complete/<int:order_id>/', views.meetup_checkout_complete, name='meetup_checkout_complete'),
] 