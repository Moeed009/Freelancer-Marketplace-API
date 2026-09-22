from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import PaymentStatus


class PaymentCreate(BaseModel):
    milestone_id: UUID


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    milestone_id: UUID
    client_id: UUID
    freelancer_id: UUID
    amount: Decimal
    currency: str
    status: PaymentStatus
    stripe_checkout_session_id: str | None
    stripe_payment_intent_id: str | None
    created_at: datetime
    updated_at: datetime


class CheckoutResponse(BaseModel):
    payment_id: UUID
    checkout_url: str
    status: PaymentStatus