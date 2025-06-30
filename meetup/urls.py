from django.urls import path
from . import views

app_name = 'meetup'

urlpatterns = [
    # 밋업 목록 (공개/관리자)
    path('<str:store_id>/', views.meetup_list, name='meetup_list'),
    
    # 밋업 추가
    path('<str:store_id>/add/', views.add_meetup, name='add_meetup'),
    
    # 밋업 상세
    path('<str:store_id>/<int:meetup_id>/', views.meetup_detail, name='meetup_detail'),
    
    # 밋업 관리
    path('<str:store_id>/<int:meetup_id>/manage/', views.manage_meetup, name='manage_meetup'),
    
    # 카테고리 관리
    path('<str:store_id>/category/manage/', views.category_manage, name='category_manage'),
    
    # API 엔드포인트 (카테고리 목록)
    path('<str:store_id>/categories/', views.get_categories, name='get_categories'),
] 