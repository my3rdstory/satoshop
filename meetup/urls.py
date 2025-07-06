from django.urls import path
from . import views, views_free, views_paid
from .admin import admin_views

app_name = 'meetup'

urlpatterns = [
    # 밋업 목록 (공개/관리자)
    path('<str:store_id>/', views.meetup_list, name='meetup_list'),
    path('<str:store_id>/list/', views.public_meetup_list, name='public_meetup_list'),
    
    # 밋업 추가
    path('<str:store_id>/add/', views.add_meetup, name='add_meetup'),
    
    # 밋업 현황 (구체적인 패턴을 먼저 배치)
    path('<str:store_id>/status/', views.meetup_status, name='meetup_status'),
    path('<str:store_id>/status/<int:meetup_id>/', views.meetup_status_detail, name='meetup_status_detail'),
    path('<str:store_id>/status/<int:meetup_id>/csv/', views.export_meetup_participants_csv, name='export_meetup_participants_csv'),
    path('<str:store_id>/status/<int:meetup_id>/update_attendance/', views.update_attendance, name='update_attendance'),
    path('<str:store_id>/<int:meetup_id>/cancel_participation/', views.cancel_participation, name='cancel_participation'),
    
    # 밋업 주문 내역
    path('<str:store_id>/orders/', views.meetup_orders, name='meetup_orders'),
    
    # 밋업 상세 (일반적인 패턴을 나중에 배치)
    path('<str:store_id>/<int:meetup_id>/', views.meetup_detail, name='meetup_detail'),
    
    # 밋업 정원 상태 API
    path('<str:store_id>/<int:meetup_id>/capacity-status/', views.meetup_capacity_status, name='meetup_capacity_status'),
    
    # 밋업 통합수정
    path('<str:store_id>/<int:meetup_id>/edit/', views.edit_meetup_unified, name='edit_meetup_unified'),
    
    # 밋업 관리
    path('<str:store_id>/<int:meetup_id>/manage/', views.manage_meetup, name='manage_meetup'),
    
    # 밋업 일시중단 토글
    path('<str:store_id>/<int:meetup_id>/toggle-temporary-closure/', views.toggle_temporary_closure, name='toggle_temporary_closure'),
    
    # 무료 밋업 전용 (구체적인 패턴을 먼저 배치)
    path('<str:store_id>/<int:meetup_id>/free_participant_info/', views_free.meetup_free_participant_info, name='meetup_free_participant_info'),
    
    # 밋업 체크아웃 (라우팅 뷰)
    path('<str:store_id>/<int:meetup_id>/checkout/', views.meetup_checkout, name='meetup_checkout'),
    path('<str:store_id>/<int:meetup_id>/checkout/payment/', views_paid.meetup_checkout_payment, name='meetup_checkout_payment'),
    
    # 밋업 결제 관련 API (🔄 order_id 제거 - 상품과 통일)
    path('<str:store_id>/<int:meetup_id>/checkout/create_invoice/', views_paid.create_meetup_invoice, name='create_meetup_invoice'),
    path('<str:store_id>/<int:meetup_id>/checkout/check_payment/', views_paid.check_meetup_payment_status, name='check_meetup_payment_status'),
    path('<str:store_id>/<int:meetup_id>/checkout/cancel_invoice/', views_paid.cancel_meetup_invoice, name='cancel_meetup_invoice'),
    
    # 밋업 결제 완료
    path('<str:store_id>/<int:meetup_id>/complete/<int:order_id>/', views.meetup_checkout_complete, name='meetup_checkout_complete'),
    
    # 밋업 참가 취소
    path('<str:store_id>/<int:meetup_id>/cancel_participation/', views.cancel_participation, name='cancel_participation'),
    
    # 밋업 임시 예약 해제 (페이지 벗어날 때)
    path('<str:store_id>/<int:meetup_id>/release_reservation/', views.release_meetup_reservation, name='release_reservation'),
    
    # 밋업체커 (QR 스캔 및 수동 참석 확인)
    path('<str:store_id>/<int:meetup_id>/checker/', views.meetup_checker, name='meetup_checker'),
    path('<str:store_id>/<int:meetup_id>/check-attendance/', views.check_attendance, name='check_attendance'),
    
    # Admin 전용 URL
    path('admin/csv-upload/<int:meetup_id>/', admin_views.csv_upload_view, name='admin_csv_upload'),
    path('admin/csv-progress/<str:task_id>/', admin_views.get_progress, name='admin_csv_progress'),
] 