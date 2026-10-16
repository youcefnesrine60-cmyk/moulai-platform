# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Evidence and administrative decisions are distinct from a paid receipt."""

# ==============================================
# IMPORTS
# ==============================================

from datetime import datetime
from decimal import Decimal
from typing import (
    Literal,
    Self,
    TypeAlias,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StrictBool,
    model_validator,
)

from app.schemas.payment import PaymentResponse

# ==============================================
# TYPE ALIASES
# ==============================================

ManualPaymentMethod: TypeAlias = Literal["ccp", "baridimob"]
ManualReceiptStatus: TypeAlias = Literal["pending", "approved", "rejected"]
ManualReviewDecision: TypeAlias = Literal["approve", "reject"]
SubscriptionBillingCycle: TypeAlias = Literal["monthly", "yearly"]
PaymentAuditDetails: TypeAlias = dict[str, JsonValue]


# ==============================================
# RECEIPT RESPONSE
# ==============================================


class ReceiptResponse(BaseModel):
    """Expose receipt metadata without disclosing its private binary content."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    payment_id: int
    transaction_reference: str
    sha256: str
    media_type: str
    review_status: ManualReceiptStatus
    reviewed_by: int | None
    reviewed_at: datetime | None
    received_amount: Decimal | None
    received_currency: str | None
    review_note: str | None


# ==============================================
# ADMINISTRATIVE REVIEW
# ==============================================


class ManualPaymentReview(BaseModel):
    """Require independent bank verification before approving a transfer."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    decision: ManualReviewDecision
    funds_received: StrictBool = False
    bank_transaction_reference: str | None = Field(None, min_length=3, max_length=120)
    received_amount: Decimal | None = Field(None, gt=0, max_digits=12, decimal_places=2)
    received_currency: Literal["DZD"] | None = None
    note: str = Field(min_length=3, max_length=2000)

    # ==========================================
    # CONFIRM INDEPENDENT SETTLEMENT EVIDENCE
    # ==========================================

    @model_validator(mode="after")
    def require_independent_confirmation(self) -> Self:
        """Reject incomplete approvals and contradictory rejection evidence."""

        if self.decision == "approve" and (
            not self.funds_received
            or not self.bank_transaction_reference
            or self.received_amount is None
            or self.received_currency is None
        ):
            raise ValueError(
                "Approval requires independently verified bank funds and reference"
            )
        if self.decision == "reject" and (
            self.funds_received
            or self.received_amount is not None
            or self.received_currency is not None
            or self.bank_transaction_reference is not None
        ):
            raise ValueError("Rejection cannot attest received funds")
        return self


# ==============================================
# SUBSCRIPTION CHECKOUT
# ==============================================


class ManualSubscriptionCheckout(BaseModel):
    """Select an owned restaurant, plan, cycle, and enabled transfer method.

    Pricing and subscription status remain authoritative server values.
    Extra fields cannot inject a client-supplied amount or discount.
    """

    model_config = ConfigDict(extra="forbid")

    restaurant_id: int = Field(gt=0)
    plan_id: int = Field(gt=0)
    billing_cycle: SubscriptionBillingCycle = "monthly"
    payment_method: ManualPaymentMethod


# ==============================================
# AUDIT RESPONSE
# ==============================================


class PaymentAuditResponse(BaseModel):
    """Expose an immutable audit event to an authorized payment reviewer."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    owner_id: int
    admin_id: int | None
    created_at: datetime
    details: PaymentAuditDetails


# ==============================================
# PAYMENT REVIEW CONTEXT
# ==============================================


class PaymentReviewContext(BaseModel):
    """Combine the invoice, receipt metadata, and decision history."""

    payment: PaymentResponse
    receipt: ReceiptResponse
    audit: list[PaymentAuditResponse]
