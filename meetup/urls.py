from django.urls import path
from . import views

app_name = 'meetup'

urlpatterns = [
    # 밋업 목록 (공개/관리자)
    path('<str:store_id>/', views.meetup_list, name='meetup_list'),
    
    # 밋업 추가
    path('<str:store_id>/add/', views.add_meetup, name='add_meetup'),
    
    # 밋업 상세
    path('<str:store_id>/<str:meetup_id>/', views.meetup_detail, name='meetup_detail'),
    
    # 밋업 통합수정
    path('<str:store_id>/<str:meetup_id>/edit/', views.edit_meetup_unified, name='edit_meetup_unified'),
    
    # 밋업 관리
    path('<str:store_id>/<str:meetup_id>/manage/', views.manage_meetup, name='manage_meetup'),
] 