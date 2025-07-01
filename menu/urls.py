from django.urls import path
from . import views

app_name = 'menu'

urlpatterns = [
    # === 관리자용 메뉴 관리 ===
    path('<str:store_id>/', views.menu_list, name='menu_list'),
    path('<str:store_id>/add/', views.add_menu, name='add_menu'),
    path('<str:store_id>/<int:menu_id>/edit/', views.edit_menu, name='edit_menu'),
    path('<str:store_id>/<int:menu_id>/manage/', views.manage_menu, name='manage_menu'),
    path('<str:store_id>/<int:menu_id>/delete/', views.delete_menu, name='delete_menu'),
    
    # 메뉴 이미지 업로드 API
    path('<str:store_id>/<int:menu_id>/upload-image/', views.upload_menu_image, name='upload_menu_image'),
    
    # 카테고리 관리
    path('<str:store_id>/categories/manage/', views.category_manage, name='category_manage'),
    path('<str:store_id>/categories/', views.category_list_api, name='category_list_api'),
    path('<str:store_id>/categories/create/', views.category_create_api, name='category_create_api'),
    path('<str:store_id>/categories/<int:category_id>/', views.category_update_api, name='category_update_api'),
    path('<str:store_id>/categories/<int:category_id>/delete/', views.category_delete_api, name='category_delete_api'),
    path('<str:store_id>/categories/reorder/', views.category_reorder_api, name='category_reorder_api'),
    
    # 메뉴 상태 관리 API
    path('<str:store_id>/<int:menu_id>/toggle-temporary-out-of-stock/', views.toggle_temporary_out_of_stock, name='toggle_temporary_out_of_stock'),
    path('<str:store_id>/<int:menu_id>/toggle-active/', views.toggle_menu_active, name='toggle_menu_active'),
    
    # 메뉴 판매 현황
    path('<str:store_id>/orders/', views.menu_orders, name='menu_orders'),
    path('<str:store_id>/orders/<int:menu_id>/', views.menu_orders_detail, name='menu_orders_detail'),
    
    # === 데스크톱 메뉴판 ===
    path('<str:store_id>/list/', views.menu_board_desktop, name='menu_board_desktop'),
    path('<str:store_id>/list/<int:menu_id>/', views.menu_detail_desktop, name='menu_detail_desktop'),
    path('<str:store_id>/detail/<int:menu_id>/ajax/', views.menu_detail_ajax_desktop, name='menu_detail_ajax_desktop'),
    path('<str:store_id>/cart/', views.menu_cart_desktop, name='menu_cart_desktop'),
    path('<str:store_id>/cart/create-invoice/', views.create_cart_invoice_desktop, name='create_cart_invoice_desktop'),
    path('<str:store_id>/cart/check-payment/', views.check_cart_payment, name='check_cart_payment_desktop'),
    
    # === 모바일 메뉴판 ===
    path('<str:store_id>/m/', views.menu_board_mobile, name='menu_board_mobile'),
    path('<str:store_id>/m/<int:menu_id>/', views.menu_detail_mobile, name='menu_detail_mobile'),
    path('<str:store_id>/m/detail/<int:menu_id>/ajax/', views.menu_detail_ajax_mobile, name='menu_detail_ajax_mobile'),
    path('<str:store_id>/m/cart/', views.menu_cart_mobile, name='menu_cart_mobile'),
    path('<str:store_id>/m/cart/create-invoice/', views.create_cart_invoice_mobile, name='create_cart_invoice_mobile'),
    path('<str:store_id>/m/cart/check-payment/', views.check_cart_payment, name='check_cart_payment_mobile'),
    
    # === 하위 호환성 (기존 URL 지원) ===
    path('<str:store_id>/list/auto/', views.menu_board_auto_redirect, name='menu_board_auto_redirect'),
    path('<str:store_id>/board/', views.menu_board, name='menu_board'),  # 구버전 호환
    path('<str:store_id>/board/<int:menu_id>/', views.menu_detail, name='menu_detail'),  # 구버전 호환
    path('<str:store_id>/board/cart/', views.menu_cart, name='menu_cart'),  # 구버전 호환
    path('<str:store_id>/cart/create-invoice-legacy/', views.create_cart_invoice, name='create_cart_invoice_legacy'),
]