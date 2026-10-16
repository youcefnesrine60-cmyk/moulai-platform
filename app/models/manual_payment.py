# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Private receipt evidence and append-only application audit records."""

# ==============================================
# IMPORTS
# ==============================================

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
)

from .base import BaseModel

# ==============================================
# MANUAL PAYMENT RECEIPT
# ==============================================


class ManualPaymentReceipt(BaseModel):
    """Store one private transfer receipt and its administrative decision.

    Global reference and content uniqueness prevent receipt reuse across
    tenants. Receipt submission never establishes payment settlement.
    """

    __tablename__ = "manual_payment_receipts"
    __table_args__ = (
        CheckConstraint("review_status IN ('pending', 'approved', 'rejected')"),
        CheckConstraint("octet_length(content) BETWEEN 1 AND 2097152"),
    )

    # ==========================================
    # COLUMNS
    # ==========================================

    payment_id = Column(
        Integer,
        ForeignKey("payments.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    # Both methods share the postal transfer ledger. Deduplicate globally,
    # including across tenants and after rejection, without disclosing matches.
    transaction_reference = Column(String(120), unique=True, nullable=False)
    sha256 = Column(String(64), unique=True, nullable=False)
    media_type = Column(String(50), nullable=False)
    content = Column(LargeBinary, nullable=False)
    review_status = Column(String(20), nullable=False, default="pending")
    reviewed_by = Column(Integer, ForeignKey("admins.id", ondelete="SET NULL"))
    reviewed_at = Column(DateTime)
    received_amount = Column(Numeric(12, 2))
    received_currency = Column(String(3))
    review_note = Column(Text)


# ==============================================
# MANUAL PAYMENT AUDIT
# ==============================================


class ManualPaymentAudit(BaseModel):
    """Preserve the tenant and reviewer involved in each payment decision.

    The owner identifier is an immutable snapshot. Services append events
    within the same transaction as their payment and receipt changes.
    """

    __tablename__ = "manual_payment_audit"

    # ==========================================
    # COLUMNS
    # ==========================================

    payment_id = Column(
        Integer,
        ForeignKey("payments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    receipt_id = Column(
        Integer,
        ForeignKey("manual_payment_receipts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    owner_id = Column(Integer, nullable=False)
    admin_id = Column(Integer, ForeignKey("admins.id", ondelete="SET NULL"))
    action = Column(String(30), nullable=False)
    details = Column(JSON, nullable=False)
