from django.urls import path

from . import views
from .admin_views import ChannelSalesView

app_name = "api"

urlpatterns = [
    path("v1/", views.api_index, name="api_index"),
    path("v1/docs/", views.api_docs, name="api_docs"),
    path("v1/csrf/", views.api_csrf, name="api_csrf"),
    path("v1/nostr/challenge/", views.nostr_challenge, name="nostr_challenge"),
    path("v1/stores/", views.store_feed, name="store_feed"),
    path("v1/stores/<str:store_id>/owner/", views.store_owner_info, name="store_owner_info"),
    path("v1/stores/<str:store_id>/products/", views.store_products, name="store_products"),
    path("v1/stores/<str:store_id>/meetups/", views.store_meetups, name="store_meetups"),
    path("v1/stores/<str:store_id>/live-lectures/", views.store_live_lectures, name="store_live_lectures"),
    path("v1/stores/<str:store_id>/digital-files/", views.store_digital_files, name="store_digital_files"),
    path("v1/stores/<str:store_id>/orders/", views.store_create_order, name="store_create_order"),
    path(
        "v1/stores/<str:store_id>/lightning-invoices/",
        views.store_create_lightning_invoice,
        name="store_create_lightning_invoice",
    ),
    path(
        "v1/stores/<str:store_id>/lightning-invoices/confirm-order/",
        views.store_confirm_lightning_invoice_and_create_order,
        name="store_confirm_lightning_invoice_and_create_order",
    ),
    path("v1/notices/", views.notice_list, name="notice_list"),
    path("v1/notices/<int:notice_id>/", views.notice_detail, name="notice_detail"),

    # Admin 통합 채널 판매 리포트
    path("admin/channel-sales/", ChannelSalesView.as_view(), name="channel_sales"),
]
