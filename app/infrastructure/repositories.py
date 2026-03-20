from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.domain.enums import PaymentStatus
from app.domain.models import Order, Payment


class OrderRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, order_id: int) -> Order | None:
        return self.db.get(Order, order_id)

    def create(self, total_amount: int) -> Order:
        order = Order(total_amount=total_amount)
        self.db.add(order)
        self.db.flush()
        return order

    def save(self, order: Order) -> None:
        self.db.add(order)


class PaymentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, payment_id: int) -> Payment | None:
        return self.db.get(Payment, payment_id)

    def get_by_bank_payment_id(self, bank_payment_id: str) -> Payment | None:
        stmt: Select[tuple[Payment]] = select(Payment).where(
            Payment.bank_payment_id == bank_payment_id
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def create(
        self,
        order_id: int,
        amount: int,
        payment_type,
        status,
        bank_payment_id: str | None = None,
    ) -> Payment:
        payment = Payment(
            order_id=order_id,
            amount=amount,
            type=payment_type,
            status=status,
            bank_payment_id=bank_payment_id,
        )
        self.db.add(payment)
        self.db.flush()
        return payment

    def save(self, payment: Payment) -> None:
        self.db.add(payment)

    def sum_reserved_amount(self, order_id: int) -> int:
        stmt = select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.order_id == order_id,
            Payment.status.in_([PaymentStatus.PENDING, PaymentStatus.SUCCESS]),
        )
        return int(self.db.execute(stmt).scalar_one())

    def sum_paid_amount(self, order_id: int) -> int:
        stmt = select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.order_id == order_id,
            Payment.status == PaymentStatus.SUCCESS,
        )
        return int(self.db.execute(stmt).scalar_one())

    def list_pending_acquiring(self) -> list[Payment]:
        stmt: Select[tuple[Payment]] = select(Payment).where(
            Payment.status == PaymentStatus.PENDING,
            Payment.bank_payment_id.is_not(None),
        )
        return list(self.db.execute(stmt).scalars().all())
