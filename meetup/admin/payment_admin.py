from django.contrib import admin
from ln_payment.models import (
    ManualPaymentTransaction,
    OrderItemReservation,
    PaymentStageLog,
    PaymentTransaction,
)
from ln_payment.admin import (
    ManualPaymentTransactionAdmin,
    OrderItemReservationAdmin,
    PaymentStageLogAdmin,
    PaymentTransactionAdmin,
)


class MeetupPaymentTransaction(PaymentTransaction):
    class Meta:
        proxy = True
        verbose_name = '결제 트랜잭션'
        verbose_name_plural = '결제 트랜잭션'
        app_label = 'meetup'


@admin.register(MeetupPaymentTransaction)
class MeetupPaymentTransactionAdmin(PaymentTransactionAdmin):
    """밋업 결제에 연결된 트랜잭션만 노출한다."""

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.filter(meetup_order__isnull=False)


class MeetupManualPaymentTransaction(ManualPaymentTransaction):
    class Meta:
        proxy = True
        verbose_name = '수동 저장 결제'
        verbose_name_plural = '수동 저장 결제'
        app_label = 'meetup'


@admin.register(MeetupManualPaymentTransaction)
class MeetupManualPaymentTransactionAdmin(ManualPaymentTransactionAdmin):
    """밋업 주문이 연결된 수동 결제만 표시한다."""

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.filter(meetup_order__isnull=False)


class MeetupPaymentStageLog(PaymentStageLog):
    class Meta:
        proxy = True
        verbose_name = '결제 단계 로그'
        verbose_name_plural = '결제 단계 로그'
        app_label = 'meetup'


@admin.register(MeetupPaymentStageLog)
class MeetupPaymentStageLogAdmin(PaymentStageLogAdmin):
    """밋업 결제 단계 로그만 노출한다."""

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.filter(transaction__meetup_order__isnull=False)


class MeetupOrderItemReservation(OrderItemReservation):
    class Meta:
        proxy = True
        verbose_name = '재고 예약'
        verbose_name_plural = '재고 예약'
        app_label = 'meetup'


@admin.register(MeetupOrderItemReservation)
class MeetupOrderItemReservationAdmin(OrderItemReservationAdmin):
    """밋업 결제와 연결된 재고 예약만 조회한다."""

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.filter(transaction__meetup_order__isnull=False)
