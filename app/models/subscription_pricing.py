# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# PRICING HISTORY AND REMINDER MODELS
# Persist pricing policies, immutable calculation evidence and the reminder outbox.
# ==============================================

"""Persisted pricing configuration and append-only subscription evidence."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Declare the standard-library, framework and project dependencies used below.
# ==============================================

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)

from .base import BaseModel

# ==============================================
# SUBSCRIPTION PRICING CONFIG
# Persistent commercial configuration shared by all subscription quotations.
# ==============================================


class SubscriptionPricingConfig(BaseModel):
    """Persistent commercial configuration shared by all subscription quotations."""

    # ==============================================
    # PERSISTED FIELDS AND RELATIONSHIPS
    # Declare this entity's stored fields, integrity metadata and ORM links.
    # ==============================================

    __tablename__ = "subscription_pricing_config"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_subscription_pricing_singleton"),
    )
    # Unsettled commercial policies have no implicit production default.
    policies = Column(JSON, nullable=False, default=dict)


# ==============================================
# SUBSCRIPTION PRICING SNAPSHOT
# Immutable owned measurement period and retained pricing evidence.
# ==============================================


class SubscriptionPricingSnapshot(BaseModel):
    """Immutable owned measurement period and retained pricing evidence."""

    # ==============================================
    # PERSISTED FIELDS AND RELATIONSHIPS
    # Declare this entity's stored fields, integrity metadata and ORM links.
    # ==============================================

    __tablename__ = "subscription_pricing_snapshots"
    __table_args__ = (
        UniqueConstraint("subscription_id", name="uq_subscription_price_snapshot"),
        Index(
            "uq_subscription_metric_period",
            "source_subscription_id",
            "reference_end",
            unique=True,
            postgresql_where=text("context='active_month' AND subscription_id IS NULL"),
        ),
        CheckConstraint(
            "reference_end-reference_start=INTERVAL '30 days'",
            name="ck_snapshot_period",
        ),
        CheckConstraint(
            "products_count >= 0 AND categories_count >= 0 AND monthly_orders >= 0 AND average_order_value >= 0",
            name="ck_snapshot_metrics",
        ),
    )
    owner_id = Column(Integer, ForeignKey("owners.id"), nullable=False)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)
    source_subscription_id = Column(
        Integer, ForeignKey("subscriptions.id"), nullable=False
    )
    reference_start = Column(DateTime, nullable=False)
    reference_end = Column(DateTime, nullable=False)
    context = Column(String(30), nullable=False)
    products_count = Column(Integer, nullable=False)
    categories_count = Column(Integer, nullable=False)
    monthly_orders = Column(Integer, nullable=False)
    average_order_value = Column(Numeric(20, 8), nullable=False)
    calculated_at = Column(DateTime, nullable=False)
    pricing = Column(JSON, nullable=False, default=dict)
    parameters = Column(JSON, nullable=False, default=dict)


# ==============================================
# SUBSCRIPTION REMINDER
# Durable per-recipient reminder with deduplication and delivery status.
# ==============================================


class SubscriptionReminder(BaseModel):
    """Durable per-recipient reminder with deduplication and delivery status."""

    # ==============================================
    # PERSISTED FIELDS AND RELATIONSHIPS
    # Declare this entity's stored fields, integrity metadata and ORM links.
    # ==============================================

    __tablename__ = "subscription_reminders"
    __table_args__ = (
        UniqueConstraint(
            "subscription_id",
            "expires_at",
            "offset_days",
            "recipient",
            name="uq_subscription_reminder",
        ),
    )
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    offset_days = Column(Integer, nullable=False)
    recipient = Column(String(30), nullable=False)
    target_chat_id = Column(String(40), nullable=True)
    due_at = Column(DateTime, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    attempts = Column(Integer, nullable=False, default=0)
    sent_at = Column(DateTime, nullable=True)
    attempt_log = Column(JSON, nullable=False, default=list)
