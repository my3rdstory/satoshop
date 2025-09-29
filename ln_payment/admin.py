from django.contrib import admin

from .models import OrderItemReservation, PaymentStageLog, PaymentTransaction


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "store",
        "user",
        "status",
        "current_stage",
        "amount_sats",
        "invoice_expires_at",
        "created_at",
    )
    list_filter = ("status", "current_stage", "store")
    search_fields = ("id", "payment_hash", "user__username", "store__store_id")
    ordering = ("-created_at",)


@admin.register(PaymentStageLog)
class PaymentStageLogAdmin(admin.ModelAdmin):
    list_display = ("transaction", "stage", "status", "message", "created_at")
    list_filter = ("status", "stage")
    search_fields = ("transaction__id", "message")
    ordering = ("-created_at",)


@admin.register(OrderItemReservation)
class OrderItemReservationAdmin(admin.ModelAdmin):
    list_display = ("transaction", "product", "quantity", "status", "expires_at", "created_at")
    list_filter = ("status", "product")
    search_fields = ("transaction__id", "product__title")
    ordering = ("-created_at",)
