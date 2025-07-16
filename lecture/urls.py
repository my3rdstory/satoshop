from django.urls import path
from . import views

app_name = 'lecture'

urlpatterns = [
    path('', views.LectureListView.as_view(), name='list'),
    path('<int:pk>/', views.LectureDetailView.as_view(), name='detail'),
    path('<int:pk>/enroll/', views.enroll_lecture, name='enroll'),
    path('my-lectures/', views.MyLecturesView.as_view(), name='my_lectures'),
    
    # 전체 라이브 강의 둘러보기
    path('browse/', views.browse_live_lectures, name='browse_live_lectures'),
    
    path('<str:store_id>/live/', views.live_lecture_list, name='live_lecture_list'),
    path('<str:store_id>/live/grid/', views.live_lecture_grid, name='live_lecture_grid'),
    
    path('<str:store_id>/live/add/', views.add_live_lecture, name='add_live_lecture'),
    
    path('<str:store_id>/live/status/', views.live_lecture_status, name='live_lecture_status'),
    path('<str:store_id>/live/status/<int:live_lecture_id>/', views.live_lecture_status_detail, name='live_lecture_status_detail'),
    path('<str:store_id>/live/status/<int:live_lecture_id>/export/', views.export_live_lecture_participants_csv, name='export_live_lecture_participants_csv'),
    path('<str:store_id>/live/status/<int:live_lecture_id>/update_attendance/', views.update_live_lecture_attendance, name='update_live_lecture_attendance'),
    path('<str:store_id>/live/status/<int:live_lecture_id>/cancel_participation/', views.cancel_live_lecture_participation, name='cancel_live_lecture_participation'),
    
    path('<str:store_id>/live/<int:live_lecture_id>/', views.live_lecture_detail, name='live_lecture_detail'),
    
    path('<str:store_id>/live/<int:live_lecture_id>/edit/', views.edit_live_lecture, name='edit_live_lecture'),
    
    path('<str:store_id>/live/<int:live_lecture_id>/manage/', views.live_lecture_manage, name='live_lecture_manage'),
    
    path('<str:store_id>/live/<int:live_lecture_id>/toggle-temporary-closure/', views.toggle_live_lecture_temporary_closure, name='toggle_live_lecture_temporary_closure'),
    
    path('<str:store_id>/live/<int:live_lecture_id>/delete/', views.delete_live_lecture, name='delete_live_lecture'),
    
    path('<str:store_id>/live/<int:live_lecture_id>/checkout/', views.live_lecture_checkout, name='live_lecture_checkout'),
    
    path('<str:store_id>/live/<int:live_lecture_id>/checkout/create_invoice/', views.create_live_lecture_invoice, name='create_live_lecture_invoice'),
    path('<str:store_id>/live/<int:live_lecture_id>/checkout/check_payment/', views.check_live_lecture_payment, name='check_live_lecture_payment'),
    path('<str:store_id>/live/<int:live_lecture_id>/checkout/cancel_payment/', views.cancel_live_lecture_payment, name='cancel_live_lecture_payment'),
    
    path('<str:store_id>/live/<int:live_lecture_id>/debug/', views.debug_live_lecture_participation, name='debug_live_lecture_participation'),
    
    path('<str:store_id>/live/<int:live_lecture_id>/complete/<int:order_id>/', views.live_lecture_checkout_complete, name='live_lecture_checkout_complete'),
    path('<str:store_id>/live/<int:live_lecture_id>/order/<int:order_id>/', views.live_lecture_order_complete, name='live_lecture_order_complete'),
    path('<str:store_id>/live/orders/', views.live_lecture_orders, name='live_lecture_orders'),
] 