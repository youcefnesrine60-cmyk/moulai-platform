# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# RETAINED FOOD INVOICE RECEIPT
# Map the additive O2 ledger independently of legacy Float order payment fields.
# ==============================================

"""No import-time DDL; the explicit O2 migration owns persistence constraints and triggers."""

from __future__ import annotations

# isort: split
# ==============================================
# EXACT RECORD TYPES
# Keep receipt money in Decimal and scope tied to the finalized invoice.
# ==============================================

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from app.models.dining import DiningBase

# ==============================================
# IMMUTABLE RECEIPT MAPPING
# The database enforces one final receipt per invoice and a unique reference within the branch.
# ==============================================


class DiningSettlement(DiningBase):
    """A human-recorded verified remaining balance, never a payment-gateway transaction."""

    __tablename__ = "dining_settlements"
    __table_args__ = (
        ForeignKeyConstraint(
            ["restaurant_id", "branch_id", "invoice_id"],
            [
                "dining_invoices.restaurant_id",
                "dining_invoices.branch_id",
                "dining_invoices.id",
            ],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("restaurant_id", "branch_id", "reference"),
        CheckConstraint("amount>0 AND amount<>'NaN'::numeric"),
        CheckConstraint("invoice_total=advance_amount+amount AND advance_amount>=0"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(Integer)
    branch_id: Mapped[int] = mapped_column(Integer)
    invoice_id: Mapped[int] = mapped_column(Integer, unique=True)
    invoice_revision: Mapped[int] = mapped_column(BigInteger)
    invoice_total: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    advance_amount: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    amount: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    currency: Mapped[str] = mapped_column(String(3))
    mode: Mapped[str] = mapped_column(String(40))
    reference: Mapped[str] = mapped_column(String(160))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    author_membership_id: Mapped[int] = mapped_column(Integer)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
