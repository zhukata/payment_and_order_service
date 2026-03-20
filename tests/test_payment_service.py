from dataclasses import dataclass

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.domain.enums import OrderStatus, PaymentStatus, PaymentType
from app.domain.errors import PaymentLimitExceededError
from app.domain.models import Order
from app.infrastructure.db import Base
from app.domain.services import PaymentService
from app.infrastructure.repositories import OrderRepository, PaymentRepository


@dataclass
class FakeBankCheck:
    amount: int
    status: str
    paid_at: None = None


class FakeBankClient:
    def __init__(self) -> None:
        self._counter = 0
        self.statuses: dict[str, str] = {}
        self.amounts: dict[str, int] = {}

    def start_payment(self, order_id: int, amount: int) -> str:
        self._counter += 1
        bank_id = f"b-{order_id}-{self._counter}"
        self.statuses[bank_id] = "pending"
        self.amounts[bank_id] = amount
        return bank_id

    def check_payment(self, bank_payment_id: str):
        return FakeBankCheck(
            amount=self.amounts.get(bank_payment_id, 0),
            status=self.statuses.get(bank_payment_id, "failed"),
        )


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def service(db_session):
    order_repo = OrderRepository(db_session)
    payment_repo = PaymentRepository(db_session)
    bank_client = FakeBankClient()

    order = Order(total_amount=1_000)
    db_session.add(order)
    db_session.commit()

    return PaymentService(order_repo=order_repo, payment_repo=payment_repo, bank_client=bank_client), order.id, db_session, bank_client


def test_create_cash_payment_updates_order_status(service):
    payment_service, order_id, db, _ = service

    payment = payment_service.create_payment(order_id=order_id, amount=400, payment_type=PaymentType.CASH)
    db.commit()

    order = OrderRepository(db).get(order_id)

    assert payment.status == PaymentStatus.SUCCESS
    assert order is not None
    assert order.status == OrderStatus.PARTIALLY_PAID


def test_prevent_payment_over_order_total(service):
    payment_service, order_id, _, _ = service

    payment_service.create_payment(order_id=order_id, amount=900, payment_type=PaymentType.CASH)

    with pytest.raises(PaymentLimitExceededError):
        payment_service.create_payment(order_id=order_id, amount=200, payment_type=PaymentType.CASH)


def test_refund_changes_order_status(service):
    payment_service, order_id, db, _ = service

    payment = payment_service.create_payment(order_id=order_id, amount=1_000, payment_type=PaymentType.CASH)
    db.commit()

    refunded = payment_service.refund_payment(payment.id)
    db.commit()

    order = OrderRepository(db).get(order_id)

    assert refunded.status == PaymentStatus.REFUNDED
    assert order is not None
    assert order.status == OrderStatus.NOT_PAID


def test_acquiring_sync_updates_payment_and_order(service):
    payment_service, order_id, db, bank = service

    payment = payment_service.create_payment(order_id=order_id, amount=600, payment_type=PaymentType.ACQUIRING)
    db.commit()

    assert payment.status == PaymentStatus.PENDING
    bank.statuses[payment.bank_payment_id] = "paid"

    synced = payment_service.sync_acquiring_payment(payment)
    db.commit()

    order = OrderRepository(db).get(order_id)

    assert synced.status == PaymentStatus.SUCCESS
    assert order is not None
    assert order.status == OrderStatus.PARTIALLY_PAID
