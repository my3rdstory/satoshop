from django.contrib import admin
from django.db.models import OuterRef, Subquery
from django.utils.html import format_html

from .models import OrderItemReservation, PaymentStageLog, PaymentTransaction
from .services import PaymentStage


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
    list_display = (
        "transaction",
        "stage1_status",
        "stage2_status",
        "stage3_status",
        "stage4_status",
        "stage5_status",
        "last_log_at",
    )
    list_select_related = ("transaction", "transaction__store", "transaction__user")
    list_filter = ("transaction__status", "transaction__current_stage", "transaction__store")
    search_fields = ("transaction__id", "transaction__payment_hash", "transaction__user__username")
    ordering = ("-transaction__created_at",)

    STATUS_STYLES = {
        PaymentStageLog.STATUS_COMPLETED: ("Completed", "background:#16a34a;border-radius:12px;color:white;padding:2px 10px;"),
        PaymentStageLog.STATUS_IN_PROGRESS: ("Processing", "background:#2563eb;border-radius:12px;color:white;padding:2px 10px;"),
        PaymentStageLog.STATUS_PENDING: ("Pending", "background:#f59e0b;border-radius:12px;color:white;padding:2px 10px;"),
        PaymentStageLog.STATUS_FAILED: ("Failed", "background:#dc2626;border-radius:12px;color:white;padding:2px 10px;"),
    }

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        latest_stage_one = PaymentStageLog.objects.filter(
            transaction=OuterRef("transaction"),
            stage=PaymentStage.PREPARE,
        ).order_by("-created_at", "-pk").values("pk")[:1]

        queryset = queryset.filter(pk__in=Subquery(latest_stage_one))
        queryset = queryset.prefetch_related("transaction__stage_logs")
        return queryset

    def _stage_logs(self, transaction):
        cached = getattr(transaction, "_prefetched_stage_logs", None)
        if cached is not None:
            return cached

        if (
            hasattr(transaction, "_prefetched_objects_cache")
            and "stage_logs" in transaction._prefetched_objects_cache
        ):
            logs = list(transaction._prefetched_objects_cache["stage_logs"])
        else:
            logs = list(transaction.stage_logs.all())

        logs.sort(key=lambda log: (log.created_at, log.pk))
        transaction._prefetched_stage_logs = logs
        return logs

    def _stage_map(self, obj):
        transaction = obj.transaction
        cached = getattr(transaction, "_stage_map", None)
        if cached is not None:
            return cached

        stage_map = {}
        for log in self._stage_logs(transaction):
            stage_map[log.stage] = log
        transaction._stage_map = stage_map
        return stage_map

    def _format_stage(self, obj, stage_number):
        stage_map = self._stage_map(obj)
        stage_log = stage_map.get(stage_number)
        if not stage_log:
            return "-"

        label, style = self.STATUS_STYLES.get(
            stage_log.status,
            (stage_log.get_status_display(), "background:#64748b;border-radius:12px;color:white;padding:2px 10px;"),
        )
        message = stage_log.message or ""
        return format_html(
            '<div><span style="{}">{}</span>{}</div>',
            style,
            label,
            format_html('<div style="margin-top:4px;font-size:11px;color:#475569;">{}</div>', message) if message else "",
        )

    @admin.display(description="1단계")
    def stage1_status(self, obj):
        return self._format_stage(obj, PaymentStage.PREPARE)

    @admin.display(description="2단계")
    def stage2_status(self, obj):
        return self._format_stage(obj, PaymentStage.INVOICE)

    @admin.display(description="3단계")
    def stage3_status(self, obj):
        return self._format_stage(obj, PaymentStage.USER_PAYMENT)

    @admin.display(description="4단계")
    def stage4_status(self, obj):
        return self._format_stage(obj, PaymentStage.MERCHANT_SETTLEMENT)

    @admin.display(description="5단계")
    def stage5_status(self, obj):
        return self._format_stage(obj, PaymentStage.ORDER_FINALIZE)

    @admin.display(description="마지막 업데이트", ordering="transaction__updated_at")
    def last_log_at(self, obj):
        logs = self._stage_logs(obj.transaction)
        last_log = logs[-1] if logs else None
        if not last_log:
            return "-"
        return last_log.created_at


@admin.register(OrderItemReservation)
class OrderItemReservationAdmin(admin.ModelAdmin):
    list_display = ("transaction", "product", "quantity", "status", "expires_at", "created_at")
    list_filter = ("status", "product")
    search_fields = ("transaction__id", "product__title")
    ordering = ("-created_at",)
