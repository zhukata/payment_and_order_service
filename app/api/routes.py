from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.orm import Session

from app.api.dependencies import build_payment_service
from app.api.schemas import (
    CreatePaymentRequest,
    OrderResponse,
    PaymentResponse,
    SyncPaymentsResponse,
)
from app.domain.errors import (
    ExternalServiceError,
    InvalidPaymentStateError,
    NotFoundError,
    PaymentLimitExceededError,
    ValidationError,
)
from app.domain.models import Payment
from app.infrastructure.db import get_db
from app.infrastructure.repositories import OrderRepository, PaymentRepository

router = APIRouter()


def _map_error(exc: Exception) -> HTTPException:
    logger.exception("Request failed with domain/internal error")
    if isinstance(exc, NotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        )
    if isinstance(exc, (ValidationError, InvalidPaymentStateError)):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        )
    if isinstance(exc, PaymentLimitExceededError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        )
    if isinstance(exc, ExternalServiceError):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        )
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Internal server error",
    )


def _to_payment_response(payment: Payment) -> PaymentResponse:
    return PaymentResponse.model_validate(payment)


@router.post(
    "/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_payment(
    payload: CreatePaymentRequest, db: Session = Depends(get_db)
) -> PaymentResponse:
    logger.info(
        "HTTP create payment: order_id={}, amount={}, type={}",
        payload.order_id,
        payload.amount,
        payload.type,
    )
    service = build_payment_service(db)
    try:
        payment = service.create_payment(
            order_id=payload.order_id,
            amount=payload.amount,
            payment_type=payload.type,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _map_error(exc) from exc
    return _to_payment_response(payment)


@router.post("/payments/{payment_id}/refund", response_model=PaymentResponse)
def refund_payment(
    payment_id: int, db: Session = Depends(get_db)
) -> PaymentResponse:
    logger.info("HTTP refund payment: payment_id={}", payment_id)
    service = build_payment_service(db)
    try:
        payment = service.refund_payment(payment_id)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _map_error(exc) from exc
    return _to_payment_response(payment)


@router.get("/payments/{payment_id}", response_model=PaymentResponse)
def get_payment(
    payment_id: int, db: Session = Depends(get_db)
) -> PaymentResponse:
    logger.info("HTTP get payment: payment_id={}", payment_id)
    payment_repo = PaymentRepository(db)
    payment = payment_repo.get(payment_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment {payment_id} not found",
        )

    service = build_payment_service(db)
    try:
        payment = service.sync_acquiring_payment(payment)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _map_error(exc) from exc

    return _to_payment_response(payment)


@router.post("/payments/sync", response_model=SyncPaymentsResponse)
def sync_pending_payments(
    db: Session = Depends(get_db),
) -> SyncPaymentsResponse:
    logger.info("HTTP sync pending payments")
    service = build_payment_service(db)
    try:
        payments = service.sync_pending_payments()
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _map_error(exc) from exc

    responses = [_to_payment_response(payment) for payment in payments]
    return SyncPaymentsResponse(synced_count=len(responses), payments=responses)


@router.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db)) -> OrderResponse:
    logger.info("HTTP get order: order_id={}", order_id)
    order = OrderRepository(db).get(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found",
        )
    return OrderResponse.model_validate(order)
