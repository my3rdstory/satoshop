"""LN 결제 단계 전환 및 Blink 연동 서비스를 정의한다."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, Iterable, List, Optional

from django.conf import settings
from django.db import models, transaction as db_transaction
from django.utils import timezone

from orders.models import Order
from products.models import Product
from stores.models import Store

from .blink_service import BlinkAPIService, get_blink_service_for_store
from .models import OrderItemReservation, PaymentStageLog, PaymentTransaction

logger = logging.getLogger(__name__)


@dataclass
class CartItemData:
    product_id: int
    quantity: int
    metadata: Dict[str, Any]


class PaymentStage:
    PREPARE = 1
    INVOICE = 2
    USER_PAYMENT = 3
    MERCHANT_SETTLEMENT = 4
    ORDER_FINALIZE = 5


class PaymentStatus:
    PENDING = PaymentStageLog.STATUS_PENDING
    PROCESSING = PaymentStageLog.STATUS_IN_PROGRESS
    FAILED = PaymentStageLog.STATUS_FAILED
    COMPLETED = PaymentStageLog.STATUS_COMPLETED


class LightningPaymentProcessor:
    """5단계 결제 플로우를 관리하는 서비스."""

    def __init__(self, store: Store):
        self.store = store
        self._blink_service: Optional[BlinkAPIService] = None

    # ------------------------------------------------------------------
    # 내부 유틸
    # ------------------------------------------------------------------
    def _blink(self) -> BlinkAPIService:
        if not self._blink_service:
            self._blink_service = get_blink_service_for_store(self.store)
        return self._blink_service

    def fetch_transactions(self, payment_hash: str) -> Dict[str, Any]:
        try:
            return self._blink().get_transactions_by_hash(payment_hash)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning('Blink transactionsByPaymentHash 실패: %s', exc)
            return {'success': False, 'error': str(exc)}

    def _log_stage(
        self,
        transaction: PaymentTransaction,
        stage: int,
        status: str,
        message: str,
        detail: Optional[Dict[str, Any]] = None,
    ) -> PaymentStageLog:
        return PaymentStageLog.objects.create(
            transaction=transaction,
            stage=stage,
            status=status,
            message=message,
            detail=detail or {},
        )

    def _set_stage(
        self,
        transaction: PaymentTransaction,
        stage: int,
        status: str,
        message: str,
        detail: Optional[Dict[str, Any]] = None,
    ) -> PaymentStageLog:
        transaction.current_stage = stage
        if status == PaymentStatus.COMPLETED and transaction.status != PaymentTransaction.STATUS_COMPLETED:
            # 이미 완료 처리된 트랜잭션은 진행 중 상태로 되돌리지 않는다.
            transaction.status = PaymentTransaction.STATUS_PROCESSING
        elif status == PaymentStatus.FAILED:
            transaction.status = PaymentTransaction.STATUS_FAILED
        transaction.save(update_fields=["current_stage", "status", "updated_at"])
        return self._log_stage(transaction, stage, status, message, detail)

    # ------------------------------------------------------------------
    # 트랜잭션 생성 및 예약 관리
    # ------------------------------------------------------------------
    def _cleanup_expired_reservations(self) -> None:
        now = timezone.now()
        expired = OrderItemReservation.objects.filter(
            status=OrderItemReservation.STATUS_ACTIVE,
            expires_at__lt=now,
        )
        count = expired.update(status=OrderItemReservation.STATUS_RELEASED)
        if count:
            logger.debug('만료된 재고 예약 %s건 해제', count)

    @db_transaction.atomic
    def create_transaction(
        self,
        *,
        user,
        amount_sats: int,
        currency: str,
        cart_items: Iterable[CartItemData],
        soft_lock_ttl_minutes: int = 3,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PaymentTransaction:
        now = timezone.now()
        self._cleanup_expired_reservations()
        transaction = PaymentTransaction.objects.create(
            user=user,
            store=self.store,
            amount_sats=amount_sats,
            currency=currency,
            status=PaymentTransaction.STATUS_PENDING,
            current_stage=PaymentStage.PREPARE,
            soft_lock_expires_at=now + timedelta(minutes=soft_lock_ttl_minutes),
            metadata=metadata or {},
        )

        for item in cart_items:
            product = Product.objects.select_for_update().get(id=item.product_id, store=self.store)
            active_reserved = (
                OrderItemReservation.objects.filter(
                    product=product,
                    status=OrderItemReservation.STATUS_ACTIVE,
                )
                .exclude(transaction=transaction)
                .aggregate(total=models.Sum("quantity"))
                .get("total")
                or 0
            )
            available_stock = max(product.stock_quantity - active_reserved, 0)
            if item.quantity > available_stock:
                raise ValueError("재고가 부족합니다.")

            OrderItemReservation.objects.create(
                transaction=transaction,
                product=product,
                quantity=item.quantity,
                expires_at=transaction.soft_lock_expires_at,
                metadata=item.metadata,
            )

        self._log_stage(
            transaction,
            PaymentStage.PREPARE,
            PaymentStatus.COMPLETED,
            "재고 예약 및 결제 준비 완료",
            {
                "amount_sats": amount_sats,
                "items": [
                    {
                        "product_id": item.product_id,
                        "quantity": item.quantity,
                    }
                    for item in cart_items
                ],
            },
        )
        transaction.status = PaymentTransaction.STATUS_PROCESSING
        transaction.save(update_fields=["status", "updated_at"])
        return transaction

    # ------------------------------------------------------------------
    # 인보이스 관리
    # ------------------------------------------------------------------
    def issue_invoice(
        self,
        transaction: PaymentTransaction,
        *,
        amount_sats: Optional[int] = None,
        memo: str = "상품 결제",
        expires_in_minutes: int = 2,
    ) -> Dict[str, Any]:
        blink = self._blink()
        result = blink.create_invoice(
            amount_sats=amount_sats or transaction.amount_sats,
            memo=memo,
            expires_in_minutes=expires_in_minutes,
        )
        if not result.get("success"):
            self._log_stage(
                transaction,
                PaymentStage.INVOICE,
                PaymentStatus.FAILED,
                "인보이스 생성 실패",
                {"error": result.get("error")},
            )
            raise RuntimeError(result.get("error") or "인보이스 생성 실패")

        transaction.payment_hash = result["payment_hash"]
        transaction.payment_request = result["invoice"]
        transaction.invoice_expires_at = result.get("expires_at")
        transaction.status = PaymentTransaction.STATUS_PROCESSING
        transaction.current_stage = PaymentStage.INVOICE
        transaction.save(update_fields=[
            "payment_hash",
            "payment_request",
            "invoice_expires_at",
            "status",
            "current_stage",
            "updated_at",
        ])

        self._log_stage(
            transaction,
            PaymentStage.INVOICE,
            PaymentStatus.COMPLETED,
            "인보이스 생성 완료",
            {
                "payment_hash": transaction.payment_hash,
                "expires_at": transaction.invoice_expires_at.isoformat() if transaction.invoice_expires_at else None,
            },
        )
        return result

    def recreate_invoice(
        self,
        transaction: PaymentTransaction,
        *,
        memo: str = "상품 결제",
        expires_in_minutes: int = 2,
        reason: str = "인보이스 재생성",
    ) -> Dict[str, Any]:
        self._log_stage(
            transaction,
            PaymentStage.INVOICE,
            PaymentStatus.PROCESSING,
            reason,
            {"previous_payment_hash": transaction.payment_hash},
        )
        return self.issue_invoice(
            transaction,
            memo=memo,
            expires_in_minutes=expires_in_minutes,
        )

    # ------------------------------------------------------------------
    # 결제 상태 확인
    # ------------------------------------------------------------------
    def check_user_payment(self, transaction: PaymentTransaction) -> Dict[str, Any]:
        if not transaction.payment_hash:
            raise ValueError("결제 해시가 존재하지 않습니다.")

        blink = self._blink()
        status_result = blink.check_invoice_status(transaction.payment_hash)
        if not status_result.get("success"):
            self._log_stage(
                transaction,
                PaymentStage.USER_PAYMENT,
                PaymentStatus.FAILED,
                "결제 상태 확인 실패",
                {"error": status_result.get("error")},
            )
            raise RuntimeError(status_result.get("error") or "결제 상태 확인 실패")

        raw_status = status_result.get("raw_status")
        status = status_result.get("status")

        detail = {
            "raw_status": raw_status,
            "status": status,
        }

        if status == "paid":
            self._set_stage(
                transaction,
                PaymentStage.USER_PAYMENT,
                PaymentStatus.COMPLETED,
                "사용자 결제 완료 감지",
                detail,
            )
        elif status == "expired":
            self._set_stage(
                transaction,
                PaymentStage.USER_PAYMENT,
                PaymentStatus.FAILED,
                "인보이스 만료",
                detail,
            )
        else:
            self._set_stage(
                transaction,
                PaymentStage.USER_PAYMENT,
                PaymentStatus.PROCESSING,
                "사용자 결제 대기 중",
                detail,
            )
        return status_result

    # ------------------------------------------------------------------
    # 입금 확인 및 주문 생성
    # ------------------------------------------------------------------
    def mark_settlement(self, transaction: PaymentTransaction, *, tx_payload: Optional[Dict[str, Any]] = None) -> None:
        self._set_stage(
            transaction,
            PaymentStage.MERCHANT_SETTLEMENT,
            PaymentStatus.COMPLETED,
            "스토어 지갑 입금 확인",
            tx_payload or {},
        )

    def finalize_order(self, transaction: PaymentTransaction, order: Order) -> None:
        with db_transaction.atomic():
            OrderItemReservation.objects.filter(
                transaction=transaction,
                status=OrderItemReservation.STATUS_ACTIVE,
            ).update(status=OrderItemReservation.STATUS_CONVERTED)
            transaction.order = order
            transaction.status = PaymentTransaction.STATUS_COMPLETED
            transaction.current_stage = PaymentStage.ORDER_FINALIZE
            transaction.save(update_fields=["order", "status", "current_stage", "updated_at"])

        self._log_stage(
            transaction,
            PaymentStage.ORDER_FINALIZE,
            PaymentStatus.COMPLETED,
            "주문 저장 완료",
            {"order_number": order.order_number},
        )

    def release_reservations(self, transaction: PaymentTransaction) -> None:
        updated = OrderItemReservation.objects.filter(
            transaction=transaction,
            status=OrderItemReservation.STATUS_ACTIVE,
        ).update(status=OrderItemReservation.STATUS_RELEASED)
        if updated:
            logger.info("소프트락 해제 완료 transaction=%s count=%s", transaction.id, updated)

    def cancel_transaction(self, transaction: PaymentTransaction, reason: str, detail: Optional[Dict[str, Any]] = None) -> None:
        self.release_reservations(transaction)
        transaction.status = PaymentTransaction.STATUS_FAILED
        transaction.save(update_fields=["status", "updated_at"])
        self._log_stage(
            transaction,
            transaction.current_stage,
            PaymentStatus.FAILED,
            reason,
            detail,
        )


def build_cart_items(raw_items: Iterable[Dict[str, Any]]) -> List[CartItemData]:
    items: List[CartItemData] = []
    for item in raw_items:
        items.append(
            CartItemData(
                product_id=item["product_id"],
                quantity=item.get("quantity", 1),
                metadata={k: v for k, v in item.items() if k not in {"product_id", "quantity"}},
            )
        )
    return items
