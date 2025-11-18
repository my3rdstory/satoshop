from django.urls import path

from .views import CouponGeneratorView, CouponInvoiceStatusView, CouponInvoiceView

app_name = "coupon"

urlpatterns = [
    path("", CouponGeneratorView.as_view(), name="generator"),
    path("invoice/", CouponInvoiceView.as_view(), name="create_invoice"),
    path(
        "invoice/<str:payment_hash>/status/",
        CouponInvoiceStatusView.as_view(),
        name="invoice_status",
    ),
]
