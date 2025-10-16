import uuid

from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class PaymentTransaction(models.Model):
    """Blink 기반 결제 트랜잭션 상태를 기록하는 모델."""

    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_FAILED = "failed"
    STATUS_COMPLETED = "completed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "대기"),
        (STATUS_PROCESSING, "진행 중"),
        (STATUS_FAILED, "실패"),
        (STATUS_COMPLETED, "완료"),
    ]

    CURRENCY_BTC = "BTC"
    CURRENCY_USD = "USD"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_transactions",
        verbose_name="사용자",
    )
    store = models.ForeignKey(
        "stores.Store",
        on_delete=models.CASCADE,
        related_name="payment_transactions",
        verbose_name="스토어",
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_transactions",
        verbose_name="연결 주문",
    )
    meetup_order = models.ForeignKey(
        "meetup.MeetupOrder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_transactions",
        verbose_name="연결 밋업 주문",
    )
    live_lecture_order = models.ForeignKey(
        "lecture.LiveLectureOrder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_transactions",
        verbose_name="연결 라이브 강의 주문",
    )
    file_order = models.ForeignKey(
        "file.FileOrder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_transactions",
        verbose_name="연결 파일 주문",
    )
    amount_sats = models.PositiveIntegerField(verbose_name="결제 금액(사토시)")
    currency = models.CharField(
        max_length=10,
        choices=[(CURRENCY_BTC, "BTC"), (CURRENCY_USD, "USD")],
        default=CURRENCY_BTC,
        verbose_name="결제 통화",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name="상태",
    )
    current_stage = models.PositiveSmallIntegerField(default=1, verbose_name="현재 단계")
    payment_hash = models.CharField(max_length=120, blank=True, verbose_name="결제 해시")
    payment_request = models.TextField(blank=True, verbose_name="인보이스 문자열")
    invoice_expires_at = models.DateTimeField(null=True, blank=True, verbose_name="인보이스 만료 시각")
    soft_lock_expires_at = models.DateTimeField(null=True, blank=True, verbose_name="소프트락 만료 시각")
    metadata = models.JSONField(default=dict, blank=True, verbose_name="메타데이터")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성 시각")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정 시각")

    class Meta:
        verbose_name = "결제 트랜잭션"
        verbose_name_plural = "결제 트랜잭션 목록"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["store", "created_at"], name="lnpay_tx_store_created_idx"),
            models.Index(fields=["user", "created_at"], name="lnpay_tx_user_created_idx"),
            models.Index(fields=["status", "current_stage"], name="lnpay_tx_status_stage_idx"),
            models.Index(fields=["payment_hash"], name="lnpay_tx_payment_hash_idx"),
        ]

    def __str__(self):
        return f"{self.store.store_id} - {self.id} ({self.get_status_display()})"


class PaymentStageLog(models.Model):
    """단계별 진행/실패 로그를 기록."""

    STATUS_PENDING = "pending"
    STATUS_IN_PROGRESS = "processing"
    STATUS_FAILED = "failed"
    STATUS_COMPLETED = "completed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "대기"),
        (STATUS_IN_PROGRESS, "진행 중"),
        (STATUS_FAILED, "실패"),
        (STATUS_COMPLETED, "완료"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction = models.ForeignKey(
        PaymentTransaction,
        on_delete=models.CASCADE,
        related_name="stage_logs",
        verbose_name="결제 트랜잭션",
    )
    stage = models.PositiveSmallIntegerField(verbose_name="단계")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name="상태",
    )
    message = models.CharField(max_length=255, blank=True, verbose_name="메시지")
    detail = models.JSONField(default=dict, blank=True, verbose_name="세부 정보")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="기록 시각")

    class Meta:
        verbose_name = "결제 단계 로그"
        verbose_name_plural = "결제 단계 로그"
        ordering = ["transaction", "stage", "created_at"]
        indexes = [
            models.Index(fields=["transaction", "stage"], name="lnpay_stage_tx_stage_idx"),
            models.Index(fields=["created_at"], name="lnpay_stage_created_idx"),
        ]

    def __str__(self):
        return f"{self.transaction_id} / stage {self.stage} ({self.get_status_display()})"


class OrderItemReservation(models.Model):
    """상품 재고 soft lock을 위한 예약 레코드."""

    STATUS_ACTIVE = "active"
    STATUS_RELEASED = "released"
    STATUS_CONVERTED = "converted"

    STATUS_CHOICES = [
        (STATUS_ACTIVE, "활성"),
        (STATUS_RELEASED, "해제"),
        (STATUS_CONVERTED, "전환"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction = models.ForeignKey(
        PaymentTransaction,
        on_delete=models.CASCADE,
        related_name="reservations",
        verbose_name="결제 트랜잭션",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="reservations",
        verbose_name="상품",
    )
    quantity = models.PositiveIntegerField(verbose_name="수량")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        verbose_name="상태",
    )
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name="만료 시각")
    metadata = models.JSONField(default=dict, blank=True, verbose_name="메타데이터")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성 시각")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정 시각")

    class Meta:
        verbose_name = "재고 예약"
        verbose_name_plural = "재고 예약 목록"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["transaction", "status"], name="lnpay_resv_tx_status_idx"),
            models.Index(fields=["product", "status"], name="lnpay_resv_product_status_idx"),
            models.Index(fields=["expires_at"], name="lnpay_resv_expires_idx"),
        ]

    def __str__(self):
        return f"{self.product_id} x{self.quantity} ({self.get_status_display()})"


class ManualPaymentTransactionManager(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(order__isnull=False, stage_logs__detail__manual=True)
            .distinct()
        )


class ManualPaymentTransaction(PaymentTransaction):
    """주문을 수동으로 저장한 결제 트랜잭션만 노출하는 프록시 모델."""

    objects = ManualPaymentTransactionManager()

    class Meta:
        proxy = True
        verbose_name = "수동 저장 결제 트랜잭션"
        verbose_name_plural = "수동 저장 결제 트랜잭션"
