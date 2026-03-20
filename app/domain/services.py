from dataclasses import dataclass

from loguru import logger

from app.domain.enums import OrderStatus, PaymentStatus, PaymentType
from app.domain.errors import (
    ExternalServiceError,
    InvalidPaymentStateError,
    NotFoundError,
    PaymentLimitExceededError,
    ValidationError,
)
from app.domain.models import Order, Payment
from app.infrastructure.bank_client import BankClient
from app.infrastructure.repositories import OrderRepository, PaymentRepository


@dataclass
class PaymentService:
    order_repo: OrderRepository
    payment_repo: PaymentRepository
    bank_client: BankClient

    def create_payment(
        self, order_id: int, amount: int, payment_type: PaymentType
    ) -> Payment:
        logger.info(
            "Create payment request: order_id={}, amount={}, type={}",
            order_id,
            amount,
            payment_type,
        )
        if amount <= 0:
            raise ValidationError("Payment amount must be positive")

        order = self.order_repo.get(order_id)
        if not order:
            raise NotFoundError(f"Order {order_id} not found")

        reserved_amount = self.payment_repo.sum_reserved_amount(order.id)
        if reserved_amount + amount > order.total_amount:
            raise PaymentLimitExceededError(
                "Total payments exceed order amount"
            )

        if payment_type == PaymentType.CASH:
            payment = self.payment_repo.create(
                order_id=order.id,
                amount=amount,
                payment_type=payment_type,
                status=PaymentStatus.SUCCESS,
            )
        else:
            bank_payment_id = self.bank_client.start_payment(order.id, amount)
            payment = self.payment_repo.create(
                order_id=order.id,
                amount=amount,
                payment_type=payment_type,
                status=PaymentStatus.PENDING,
                bank_payment_id=bank_payment_id,
            )

        self.refresh_order_status(order)
        logger.info(
            "Payment created: payment_id={}, status={}",
            payment.id,
            payment.status,
        )
        return payment

    def refund_payment(self, payment_id: int) -> Payment:
        logger.info("Refund payment request: payment_id={}", payment_id)
        payment = self.payment_repo.get(payment_id)
        if not payment:
            raise NotFoundError(f"Payment {payment_id} not found")

        if payment.status != PaymentStatus.SUCCESS:
            raise InvalidPaymentStateError(
                "Only successful payments can be refunded"
            )

        payment.status = PaymentStatus.REFUNDED
        self.payment_repo.save(payment)

        order = self.order_repo.get(payment.order_id)
        if not order:
            raise NotFoundError(f"Order {payment.order_id} not found")
        self.refresh_order_status(order)
        logger.info("Payment refunded: payment_id={}", payment.id)
        return payment

    def sync_acquiring_payment(self, payment: Payment) -> Payment:
        if (
            payment.type != PaymentType.ACQUIRING
            or not payment.bank_payment_id
            or payment.status != PaymentStatus.PENDING
        ):
            return payment

        bank_data = self.bank_client.check_payment(payment.bank_payment_id)
        if bank_data.amount != payment.amount:
            raise ExternalServiceError(
                f"Bank payment amount mismatch for payment {payment.id}: "
                f"local={payment.amount}, bank={bank_data.amount}"
            )
        payment.bank_status_snapshot = bank_data.status
        payment.bank_paid_at = bank_data.paid_at

        normalized = bank_data.status.lower()
        if normalized in {"success", "paid"}:
            payment.status = PaymentStatus.SUCCESS
        elif normalized in {"failed", "canceled", "cancelled"}:
            payment.status = PaymentStatus.FAILED

        self.payment_repo.save(payment)

        order = self.order_repo.get(payment.order_id)
        if order:
            self.refresh_order_status(order)

        logger.info(
            "Acquiring payment synced: payment_id={}, status={}",
            payment.id,
            payment.status,
        )
        return payment

    def sync_pending_payments(self) -> list[Payment]:
        synced: list[Payment] = []
        for payment in self.payment_repo.list_pending_acquiring():
            synced.append(self.sync_acquiring_payment(payment))
        return synced

    def refresh_order_status(self, order: Order) -> OrderStatus:
        self.payment_repo.db.flush()
        paid_amount = self.payment_repo.sum_paid_amount(order.id)
        if paid_amount <= 0:
            order.status = OrderStatus.NOT_PAID
        elif paid_amount < order.total_amount:
            order.status = OrderStatus.PARTIALLY_PAID
        else:
            order.status = OrderStatus.PAID

        self.order_repo.save(order)
        logger.debug(
            "Order status updated: order_id={}, status={}",
            order.id,
            order.status,
        )
        return order.status
