# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# CASH COLLECTION EVIDENCE MODELS
# Store physical cash receipts separately from immutable collection-attempt evidence.
# ==============================================

"""Cash evidence is separate from uploaded bank transfer receipts."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Declare the standard-library, framework and project dependencies used below.
# ==============================================

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
)

from .base import BaseModel

# ==============================================
# CASH COLLECTION
# Immutable receipt of cash physically received by an authorized official.
# ==============================================


class CashCollection(BaseModel):
    """Immutable receipt of cash physically received by an authorized official."""

    # ==============================================
    # PERSISTED FIELDS AND RELATIONSHIPS
    # Declare this entity's stored fields, integrity metadata and ORM links.
    # ==============================================

    __tablename__ = "cash_collections"
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=False, unique=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False)
    admin_id = Column(Integer, ForeignKey("admins.id"), nullable=False)
    expected_amount = Column(Numeric(24, 8), nullable=False)
    received_amount = Column(Numeric(24, 8), nullable=False)
    currency = Column(String(3), nullable=False)
    collected_at = Column(DateTime, nullable=False)
    confirmed_at = Column(DateTime, nullable=False)
    receipt_reference = Column(String(120), nullable=False, unique=True)


# ==============================================
# CASH COLLECTION ATTEMPT
# Append-only trace of accepted, denied and interrupted cash validation attempts.
# ==============================================


class CashCollectionAttempt(BaseModel):
    """Append-only trace of accepted, denied and interrupted cash validation attempts."""

    # ==============================================
    # PERSISTED FIELDS AND RELATIONSHIPS
    # Declare this entity's stored fields, integrity metadata and ORM links.
    # ==============================================

    __tablename__ = "cash_collection_attempts"
    # No foreign key: attempts against nonexistent identifiers must also survive.
    attempt_id = Column(String(32), nullable=False, index=True)
    payment_id = Column(Integer, nullable=False)
    attempted_admin_id = Column(Integer, nullable=False)
    result = Column(String(40), nullable=False)
    details = Column(JSON, nullable=False)
