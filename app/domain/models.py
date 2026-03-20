from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import OrderStatus, PaymentStatus, PaymentType
from app.infrastructure.db import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def enum_values(enum_cls: type) -> list[str]:
    return [item.value for item in enum_cls]


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    total_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, native_enum=False, values_callable=enum_values),
        nullable=False,
        default=OrderStatus.NOT_PAID,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    payments: Mapped[list["Payment"]] = relationship(
        "Payment", back_populates="order"
    )

    __table_args__ = (
        CheckConstraint(
            "total_amount > 0", name="ck_orders_total_amount_positive"
        ),
    )


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"), nullable=False, index=True
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[PaymentType] = mapped_column(
        Enum(PaymentType, native_enum=False, values_callable=enum_values),
        nullable=False,
    )
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, native_enum=False, values_callable=enum_values),
        nullable=False,
    )
    bank_payment_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, unique=True
    )
    bank_status_snapshot: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    bank_paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    order: Mapped[Order] = relationship("Order", back_populates="payments")

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
    )
