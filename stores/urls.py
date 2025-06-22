from django.urls import path
from . import views

app_name = 'stores'

urlpatterns = [
    # 스토어 탐색
    path('browse/', views.browse_stores, name='browse_stores'),
    
    # 스토어 생성 관련
    path('create/', views.create_store, name='create_store'),
    path('create/step/<int:step>/', views.create_store_step, name='create_store_step'),
    path('check-store-id/', views.check_store_id, name='check_store_id'),
    path('test-payment/', views.test_payment, name='test_payment'),
    
    # 스토어 관리
    path('my-stores/', views.my_stores, name='my_stores'),
    path('edit/<str:store_id>/', views.edit_store, name='edit_store'),
    
    # 분리된 편집 기능들
    path('edit/<str:store_id>/basic-info/', views.edit_basic_info, name='edit_basic_info'),
    path('edit/<str:store_id>/api-settings/', views.edit_api_settings, name='edit_api_settings'),
    path('edit/<str:store_id>/email-settings/', views.edit_email_settings, name='edit_email_settings'),
    path('edit/<str:store_id>/test-email/', views.test_store_email, name='test_store_email'),
    path('edit/<str:store_id>/theme/', views.edit_theme, name='edit_theme'),
    path('edit/<str:store_id>/manage/', views.manage_store, name='manage_store'),
    
    # 스토어 관리 액션들
    path('edit/<str:store_id>/toggle-status/', views.toggle_store_status, name='toggle_store_status'),
    path('edit/<str:store_id>/regenerate-qr/', views.regenerate_qr, name='regenerate_qr'),
    path('edit/<str:store_id>/delete/', views.delete_store, name='delete_store'),
    
    # 스토어 이미지 관리
    path('edit/<str:store_id>/upload-image/', views.upload_image, name='upload_image'),
    path('edit/<str:store_id>/delete-image/<int:image_id>/', views.delete_image, name='delete_image'),
    path('edit/<str:store_id>/reorder-images/', views.reorder_images, name='reorder_images'),
    
    # 상품 관리
    path('edit/<str:store_id>/products/', views.product_list, name='product_list'),
    path('edit/<str:store_id>/products/add/', views.add_product, name='add_product'),
    path('edit/<str:store_id>/products/<int:product_id>/edit/', views.edit_product, name='edit_product'),
    path('edit/<str:store_id>/products/<int:product_id>/delete/', views.delete_product, name='delete_product'),
    path('edit/<str:store_id>/products/<int:product_id>/upload-image/', views.upload_product_image, name='upload_product_image'),
    path('edit/<str:store_id>/products/<int:product_id>/delete-image/<int:image_id>/', views.delete_product_image, name='delete_product_image'),
    

    
    # 장바구니 관련
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/add/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    
    # 주문 관련
    path('checkout/', views.checkout_step1, name='checkout_step1'),
    path('checkout/step2/', views.checkout_step2, name='checkout_step2'),
    path('checkout/step3/', views.checkout_step3, name='checkout_step3'),
    path('checkout/complete/<str:order_number>/', views.checkout_complete, name='checkout_complete'),
    

    
    # 스토어 페이지
    path('<str:store_id>/', views.store_detail, name='store_detail'),
    path('<str:store_id>/product/<int:product_id>/', views.product_detail, name='product_detail'),
] 