from django.urls import path

from . import views, views_category

app_name = 'products'

urlpatterns = [
    # 상품 목록 및 관리
    path('<str:store_id>/', views.product_list, name='product_list'),
    path('<str:store_id>/list/', views.public_product_list, name='public_product_list'),
    path('<str:store_id>/add/', views.add_product, name='add_product'),

    # 카테고리 관리
    path('<str:store_id>/categories/manage/', views_category.category_manage, name='category_manage'),
    path('<str:store_id>/categories/', views_category.category_list_api, name='category_list_api'),
    path('<str:store_id>/categories/create/', views_category.category_create_api, name='category_create_api'),
    path('<str:store_id>/categories/<int:category_id>/', views_category.category_update_api, name='category_update_api'),
    path('<str:store_id>/categories/<int:category_id>/delete/', views_category.category_delete_api, name='category_delete_api'),
    path('<str:store_id>/categories/reorder/', views_category.category_reorder_api, name='category_reorder_api'),

    path('<str:store_id>/<int:product_id>/', views.product_detail, name='product_detail'),
    path('<str:store_id>/<int:product_id>/edit/', views.edit_product, name='edit_product'),
    path('<str:store_id>/<int:product_id>/edit-unified/', views.edit_product_unified, name='edit_product_unified'),
    path('<str:store_id>/<int:product_id>/delete/', views.delete_product, name='delete_product'),
    
    # 섹션별 상품 편집
    path('<str:store_id>/<int:product_id>/manage/', views.manage_product, name='manage_product'),
    path('<str:store_id>/<int:product_id>/edit/basic-info/', views.edit_basic_info, name='edit_basic_info'),
    path('<str:store_id>/<int:product_id>/edit/options/', views.edit_options, name='edit_options'),
    path('<str:store_id>/<int:product_id>/edit/images/', views.edit_images, name='edit_images'),
    path('<str:store_id>/<int:product_id>/edit/completion-message/', views.edit_completion_message, name='edit_completion_message'),
    
    # 상품 상태 관리
    path('<str:store_id>/<int:product_id>/toggle-status/', views.toggle_product_status, name='toggle_product_status'),
    path('<str:store_id>/<int:product_id>/toggle-temporary-out-of-stock/', views.toggle_temporary_out_of_stock, name='toggle_temporary_out_of_stock'),
    
    # 상품 이미지 관리
    path('<str:store_id>/<int:product_id>/upload-image/', views.upload_product_image, name='upload_product_image'),
    path('<str:store_id>/<int:product_id>/delete-image/<int:image_id>/', views.delete_product_image, name='delete_product_image'),
] 
