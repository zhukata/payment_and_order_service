from sqlalchemy.orm import Session

from app.domain.services import PaymentService
from app.infrastructure.bank_client import BankClient
from app.infrastructure.repositories import OrderRepository, PaymentRepository


def build_payment_service(db: Session) -> PaymentService:
    return PaymentService(
        order_repo=OrderRepository(db),
        payment_repo=PaymentRepository(db),
        bank_client=BankClient(),
    )
