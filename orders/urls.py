from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    # 장바구니
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/api/', views.cart_api, name='cart_api'),
    path('cart/check_conflict/', views.check_cart_store_conflict, name='check_cart_store_conflict'),
    path('cart/add/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/', views.remove_from_cart, name='remove_from_cart'),  # POST 요청용
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart_get'),  # GET 요청용
    path('cart/update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    
    # 주문 관리
    path('<str:store_id>/orders/', views.order_management, name='order_management'),
    path('<str:store_id>/orders/export/', views.export_orders_csv, name='export_orders_csv'),
    path('<str:store_id>/products/<int:product_id>/orders/', views.product_orders, name='product_orders'),
    path('<str:store_id>/products/<int:product_id>/orders/export/', views.export_product_orders_csv, name='export_product_orders_csv'),
    path('orders/<int:order_id>/toggle-delivery-status/', views.toggle_delivery_status, name='toggle_delivery_status'),
    path('orders/<int:order_id>/update-tracking/', views.update_tracking_info, name='update_tracking_info'),
    
    # 결제 및 구매
    path('shipping/', views.shipping_info, name='shipping_info'),
    path('checkout/', views.checkout, name='checkout'),
    path('checkout/create_invoice/', views.create_checkout_invoice, name='create_checkout_invoice'),
    path('checkout/check_payment/', views.check_checkout_payment, name='check_checkout_payment'),
    path('checkout/cancel_invoice/', views.cancel_invoice, name='cancel_invoice'),
    path('checkout/complete/<str:order_number>/', views.checkout_complete, name='checkout_complete'),
    path('download/<str:order_number>/', views.download_order_txt_public, name='download_order_txt_public'),
] 