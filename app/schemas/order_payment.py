"""Order payment contracts, separate from subscription billing payments."""
from pydantic import BaseModel
from app.schemas.order_item import (
    OrderPaymentCreate as PaymentCreate,
    OrderPaymentResponse as PaymentResponse,
    OrderPaymentStatusUpdate as PaymentStatusUpdate,
)


class PaymentSummary(BaseModel):
    total_payments: int
    total_amount: float
    paid_amount: float
    pending_amount: float
    status_counts: dict[str, int]
