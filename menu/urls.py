from django.urls import path
from . import views

app_name = 'menu'

urlpatterns = [
    # 메뉴 관리 페이지
    path('<str:store_id>/', views.menu_list, name='menu_list'),
    path('<str:store_id>/add/', views.add_menu, name='add_menu'),
    path('<str:store_id>/<uuid:menu_id>/edit/', views.edit_menu, name='edit_menu'),
    path('<str:store_id>/<uuid:menu_id>/', views.menu_detail, name='menu_detail'),
    
    # 카테고리 관리 API
    path('<str:store_id>/categories/', views.category_list_api, name='category_list_api'),
    path('<str:store_id>/categories/create/', views.category_create_api, name='category_create_api'),
    path('<str:store_id>/categories/<uuid:category_id>/', views.category_update_api, name='category_update_api'),
    path('<str:store_id>/categories/<uuid:category_id>/delete/', views.category_delete_api, name='category_delete_api'),
    
    # 메뉴 상태 관리 API
    path('<str:store_id>/<uuid:menu_id>/toggle-temporary-out-of-stock/', views.toggle_temporary_out_of_stock, name='toggle_temporary_out_of_stock'),
] 