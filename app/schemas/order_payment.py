# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / SCHEMAS / ORDER PAYMENT
# Operational component of the MoulAI platform.
# ==============================================

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


__all__ = [
    "PaymentCreate",
    "PaymentResponse",
    "PaymentStatusUpdate",
    "PaymentSummary",
]
