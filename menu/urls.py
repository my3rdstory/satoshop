from django.urls import path
from . import views

app_name = 'menu'

urlpatterns = [
    # 메뉴 관리 페이지
    path('<str:store_id>/', views.menu_list, name='menu_list'),
    path('<str:store_id>/list/', views.menu_board, name='menu_board'),
    path('<str:store_id>/list/<int:menu_id>/', views.menu_detail, name='menu_detail'),
    path('<str:store_id>/detail/<int:menu_id>/ajax/', views.menu_detail_ajax, name='menu_detail_ajax'),
    path('<str:store_id>/cart/', views.menu_cart, name='menu_cart'),
    path('<str:store_id>/add/', views.add_menu, name='add_menu'),
    path('<str:store_id>/<int:menu_id>/edit/', views.edit_menu, name='edit_menu'),
    path('<str:store_id>/<int:menu_id>/manage/', views.manage_menu, name='manage_menu'),
    path('<str:store_id>/<int:menu_id>/delete/', views.delete_menu, name='delete_menu'),
    
    # 메뉴 이미지 업로드 API
    path('<str:store_id>/<int:menu_id>/upload-image/', views.upload_menu_image, name='upload_menu_image'),
    
    # 카테고리 관리 페이지
    path('<str:store_id>/categories/manage/', views.category_manage, name='category_manage'),
    
    # 카테고리 관리 API
    path('<str:store_id>/categories/', views.category_list_api, name='category_list_api'),
    path('<str:store_id>/categories/create/', views.category_create_api, name='category_create_api'),
    path('<str:store_id>/categories/<int:category_id>/', views.category_update_api, name='category_update_api'),
    path('<str:store_id>/categories/<int:category_id>/delete/', views.category_delete_api, name='category_delete_api'),
    path('<str:store_id>/categories/reorder/', views.category_reorder_api, name='category_reorder_api'),
    
    # 메뉴 상태 관리 API
    path('<str:store_id>/<int:menu_id>/toggle-temporary-out-of-stock/', views.toggle_temporary_out_of_stock, name='toggle_temporary_out_of_stock'),
    path('<str:store_id>/<int:menu_id>/toggle-active/', views.toggle_menu_active, name='toggle_menu_active'),
] 