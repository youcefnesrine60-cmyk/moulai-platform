# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# SUBSCRIPTION METRICS AND HISTORY
# Resolve owned measurement windows and retain verified history without inventing
# missing inputs.
# ==============================================

"""Authoritative 30-day inputs and immutable evidence; no current-data fallback."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Declare the standard-library, framework and project dependencies used below.
# ==============================================

from datetime import (
    datetime,
    timedelta,
    timezone,
)
from decimal import Decimal
from typing import cast as typing_cast

from sqlalchemy import (
    Numeric,
    cast,
    func,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload

from app.core.logger import logger
from app.models.branch import Branch
from app.models.category import Category
from app.models.order import Order
from app.models.order_item import OrderStatusHistory
from app.models.product import Product
from app.models.restaurant import Restaurant
from app.models.subscription import Subscription
from app.models.subscription_pricing import SubscriptionPricingSnapshot as Snapshot
from app.repositories.subscription_queries import base_select
from app.services.business.pricing_service import number
from app.services.business.subscription_types import (
    HistoricalValues,
    JsonValue,
    PeriodMetrics,
    PricingInputs,
    ReferenceMetrics,
)

# ==============================================
# CONFIGURATION AND CONSTANTS
# Group the existing configuration values without changing their defaults.
# ==============================================

METRICS = (
    "products_count",
    "categories_count",
    "monthly_orders",
    "average_order_value",
)


# ==============================================
# UTC
# Normalize a timestamp to naive UTC for persisted SQLAlchemy comparisons.
# ==============================================


def utc(*, value: datetime) -> datetime:
    """Normalize a timestamp to naive UTC for persisted SQLAlchemy comparisons."""

    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


# ==============================================
# COLLECT
# Verify ownership and collect authoritative metrics over [end - 30 days, end).
# ==============================================


async def collect(
    *, session: AsyncSession, owner_id: int, restaurant_id: int, end: datetime
) -> PeriodMetrics:
    """Verify ownership and collect authoritative metrics over [end - 30 days, end)."""

    end = utc(value=end)
    start = end - timedelta(days=30)
    owned = (
        await session.execute(
            base_select(Restaurant)
            .with_only_columns(Restaurant.id)
            .where(Restaurant.id == restaurant_id, Restaurant.owner_id == owner_id)
        )
    ).scalar_one_or_none()
    if owned is None:
        raise ValueError("restaurant_owner_mismatch")
    completed = (
        base_select(OrderStatusHistory)
        .with_only_columns(
            OrderStatusHistory.order_id,
            func.max(OrderStatusHistory.created_at).label("completed_at"),
        )
        .where(OrderStatusHistory.new_status == "completed")
        .group_by(OrderStatusHistory.order_id)
        .subquery()
    )
    missing = (
        await session.execute(
            base_select(Order)
            .with_only_columns(Order.id)
            .outerjoin(completed, completed.c.order_id == Order.id)
            .where(
                Order.restaurant_id == restaurant_id,
                Order.status == "completed",
                completed.c.completed_at.is_(None),
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if missing is not None:
        raise ValueError("order_completion_evidence_missing")
    orders = (
        await session.execute(
            base_select(Order)
            .with_only_columns(
                cast(Order.subtotal_amount, Numeric(38, 18)).label("subtotal_amount"),
                cast(Order.discount_amount, Numeric(38, 18)).label("discount_amount"),
            )
            .join(completed, completed.c.order_id == Order.id)
            .where(
                Order.restaurant_id == restaurant_id,
                Order.status == "completed",
                completed.c.completed_at >= start,
                completed.c.completed_at < end,
            )
        )
    ).all()
    total = Decimal(0)
    for order in orders:
        net = number(value=order.subtotal_amount) - number(value=order.discount_amount)
        total += number(value=net)

    # ==============================================
    # COUNT
    # Count catalog rows restricted to the already verified restaurant.
    # ==============================================

    async def count(*, model: type[Product | Category]) -> int:
        """Count catalog rows restricted to the already verified restaurant."""

        return (
            await session.execute(
                base_select(model)
                .with_only_columns(func.count())
                .select_from(model)
                .where(model.restaurant_id == restaurant_id)
            )
        ).scalar_one()

    return {
        "reference_start": start,
        "reference_end": end,
        "products_count": await count(model=Product),
        "categories_count": await count(model=Category),
        "monthly_orders": len(orders),
        "average_order_value": total / len(orders) if orders else Decimal(0),
    }


# ==============================================
# CAPTURE ACTIVE MONTH
# Called at an active-period boundary, never reconstruct past catalog counts.
# ==============================================


async def capture_active_month(
    *,
    session: AsyncSession,
    owner_id: int,
    restaurant_id: int,
    source: Subscription,
    now: datetime,
) -> Snapshot:
    """Called at an active-period boundary, never reconstruct past catalog counts."""
    now = utc(value=now)
    if source.owner_id != owner_id or source.restaurant_id != restaurant_id:
        raise ValueError("snapshot_source_mismatch")
    if (
        not source.starts_at
        or not source.expires_at
        or not (source.starts_at < now <= source.expires_at)
        or (source.billing_cycle == "trial" and now != source.expires_at)
    ):
        raise ValueError("active_month_boundary_required")
    existing = (
        await session.execute(
            base_select(Snapshot).where(
                Snapshot.source_subscription_id == source.id,
                Snapshot.reference_end == now,
                Snapshot.context == "active_month",
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    data = await collect(
        session=session, owner_id=owner_id, restaurant_id=restaurant_id, end=now
    )
    snapshot = Snapshot(
        owner_id=owner_id,
        restaurant_id=restaurant_id,
        source_subscription_id=source.id,
        context="active_month",
        calculated_at=now,
        pricing={},
        parameters={"exact_average_order_value": str(data["average_order_value"])},
        **data,
    )
    session.add(snapshot)
    await session.flush()
    logger.info(
        "subscription_history_prepared",
        extra={
            "snapshot_id": snapshot.id,
            "restaurant_id": restaurant_id,
            "source_subscription_id": source.id,
        },
    )
    return snapshot


# ==============================================
# REFERENCE
# Distinguish trial end, continuous renewal and return; fail on lost history.
# ==============================================


async def reference(
    *, session: AsyncSession, owner_id: int, restaurant_id: int, now: datetime
) -> ReferenceMetrics:
    """Distinguish trial end, continuous renewal and return; fail on lost history."""
    now = utc(value=now)
    source = (
        (
            await session.execute(
                base_select(Subscription)
                .options(raiseload("*"))
                .where(
                    Subscription.owner_id == owner_id,
                    Subscription.restaurant_id == restaurant_id,
                    Subscription.status.in_(
                        ["active", "trial", "expired", "cancelled"]
                    ),
                    Subscription.expires_at.is_not(None),
                )
                .order_by(Subscription.expires_at.desc(), Subscription.id.desc())
                .limit(1)
            )
        )
        .scalars()
        .first()
    )
    if source is None:
        raise ValueError("subscription_reference_missing")
    effective_end = source.expires_at
    if source.status == "cancelled":
        if source.cancelled_at is None:
            raise ValueError("paid_service_history_incomplete")
        effective_end = min(effective_end, utc(value=source.cancelled_at))
    # The instant of expiry belongs to continuous renewal. Later returns need a recorded active month.
    if (source.status != "cancelled" and now == effective_end) or (
        source.status == "active" and now < source.expires_at
    ):
        snapshot = await capture_active_month(
            session=session,
            owner_id=owner_id,
            restaurant_id=restaurant_id,
            source=source,
            now=now,
        )
        context = "trial_end" if source.billing_cycle == "trial" else "renewal"
        return {
            **{
                key: getattr(snapshot, key)
                for key in (*METRICS, "reference_start", "reference_end")
            },
            "source_subscription_id": source.id,
            "context": context,
            "average_order_value": Decimal(
                snapshot.parameters["exact_average_order_value"]
            ),
        }
    if now < effective_end:
        raise ValueError("trial_period_not_finished")
    snapshot = (
        await session.execute(
            base_select(Snapshot)
            .where(
                Snapshot.owner_id == owner_id,
                Snapshot.restaurant_id == restaurant_id,
                Snapshot.source_subscription_id == source.id,
                Snapshot.context == "active_month",
                Snapshot.reference_end <= effective_end,
            )
            .order_by(Snapshot.reference_end.desc(), Snapshot.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if snapshot is None:
        raise ValueError("subscription_history_missing")
    data = {
        key: getattr(snapshot, key)
        for key in (*METRICS, "reference_start", "reference_end")
    }
    if "exact_average_order_value" in snapshot.parameters:
        data["average_order_value"] = Decimal(
            snapshot.parameters["exact_average_order_value"]
        )
    for key in METRICS:
        number(value=data[key], integer=key != "average_order_value")
    return {
        **data,
        "source_subscription_id": source.id,
        "context": "trial_end" if source.billing_cycle == "trial" else "return",
    }


# ==============================================
# PRICING INPUTS
# Combine verified history with owned restaurant, branch and paid-year counts.
# ==============================================


async def pricing_inputs(
    *, session: AsyncSession, owner_id: int, restaurant_id: int, now: datetime
) -> tuple[ReferenceMetrics, PricingInputs]:
    """Combine verified history with owned restaurant, branch and paid-year counts."""

    ref = await reference(
        session=session, owner_id=owner_id, restaurant_id=restaurant_id, now=now
    )
    restaurants = (
        await session.execute(
            base_select(Restaurant)
            .with_only_columns(func.count())
            .select_from(Restaurant)
            .where(Restaurant.owner_id == owner_id)
        )
    ).scalar_one()
    branches = (
        await session.execute(
            base_select(Branch)
            .with_only_columns(func.count())
            .select_from(Branch)
            .where(Branch.restaurant_id == restaurant_id)
        )
    ).scalar_one()
    from app.services.business.subscription_calendar import paid_years

    years = await paid_years(session=session, owner_id=owner_id, now=utc(value=now))
    return ref, {
        "restaurants_count": restaurants,
        "branches_count": branches,
        "years_with_platform": years,
        **{key: ref[key] for key in METRICS},
    }


# ==============================================
# JSON EVIDENCE
# Serialize decimal evidence without passing through binary floats.
# ==============================================


def json_evidence(*, value: object) -> JsonValue:
    """Serialize decimal evidence without passing through binary floats."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: json_evidence(value=item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_evidence(value=item) for item in value]
    return typing_cast(JsonValue, value)


# ==============================================
# RECORD VERIFIED HISTORY
# Explicit finance review, with immutable source/author evidence; no automatic backfill.
# ==============================================


async def record_verified_history(
    *,
    session: AsyncSession,
    owner_id: int,
    restaurant_id: int,
    source_subscription_id: int,
    reference_start: datetime,
    reference_end: datetime,
    values: HistoricalValues,
    admin_id: int,
    source_reference: str,
    now: datetime,
) -> Snapshot:
    """Explicit finance review, with immutable source/author evidence; no automatic backfill."""
    from app.services.business.manual_payment_service import ManualPaymentService
    from app.services.business.payment_transaction import payment_transaction

    async with payment_transaction(session=session):
        await ManualPaymentService(session=session).require_reviewer(admin_id=admin_id)
        source = (
            await session.execute(
                base_select(Subscription)
                .options(raiseload("*"))
                .where(
                    Subscription.id == source_subscription_id,
                    Subscription.owner_id == owner_id,
                    Subscription.restaurant_id == restaurant_id,
                )
                .with_for_update()
            )
        ).scalar_one_or_none()
        start, end = utc(value=reference_start), utc(value=reference_end)
        if (
            source is None
            or end - start != timedelta(days=30)
            or end > utc(value=now)
            or not source.starts_at
            or not source.expires_at
            or not source.starts_at < end <= source.expires_at
        ):
            raise ValueError("historical_reference_invalid")
        if (
            not isinstance(source_reference, str)
            or not 3 <= len(source_reference) <= 500
        ):
            raise ValueError("historical_source_required")
        if set(values) != set(METRICS):
            raise ValueError("historical_metrics_incomplete")
        for key, value in values.items():
            number(value=value, integer=key != "average_order_value")
        snapshot = Snapshot(
            owner_id=owner_id,
            restaurant_id=restaurant_id,
            source_subscription_id=source.id,
            reference_start=start,
            reference_end=end,
            context="active_month",
            calculated_at=utc(value=now),
            pricing={},
            parameters={
                "exact_average_order_value": str(values["average_order_value"]),
                "manual_reconstruction": {
                    "author_admin_id": admin_id,
                    "source_reference": source_reference,
                },
            },
            **values,
        )
        session.add(snapshot)
        await session.flush()
    logger.info(
        "subscription_history_retained",
        extra={
            "snapshot_id": snapshot.id,
            "restaurant_id": restaurant_id,
            "source_subscription_id": source.id,
        },
    )
    return snapshot
