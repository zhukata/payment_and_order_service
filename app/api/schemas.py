from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import OrderStatus, PaymentStatus, PaymentType


class CreatePaymentRequest(BaseModel):
    order_id: int = Field(gt=0)
    amount: int = Field(gt=0)
    type: PaymentType


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    amount: int
    type: PaymentType
    status: PaymentStatus
    bank_payment_id: str | None
    bank_status_snapshot: str | None
    bank_paid_at: datetime | None
    created_at: datetime


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    total_amount: int
    status: OrderStatus
    created_at: datetime


class SyncPaymentsResponse(BaseModel):
    synced_count: int
    payments: list[PaymentResponse]
