# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# SUBSCRIPTION BOUNDARY PROCESSING
# Record due service metrics and process expiry within the existing transaction
# contract.
# ==============================================

"""Local callable worker primitives; no scheduler or remote delivery is installed."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Declare the standard-library, framework and project dependencies used below.
# ==============================================

from datetime import datetime

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload

from app.core.logger import logger
from app.models.restaurant import Restaurant
from app.models.subscription import Subscription
from app.models.subscription_pricing import SubscriptionPricingSnapshot
from app.repositories.subscription_queries import base_select
from app.services.business.payment_transaction import payment_transaction
from app.services.business.subscription_calendar import add_months
from app.services.business.subscription_metrics import (
    capture_active_month,
    utc,
)
from app.services.business.subscription_types import WorkerResults

# ==============================================
# PROCESS BOUNDARIES
# Capture due active-month metrics and process expiry within the caller transaction.
# ==============================================


async def process_boundaries(*, session: AsyncSession, now: datetime) -> WorkerResults:
    """Capture due active-month metrics and process expiry within the caller transaction."""

    now = utc(value=now)
    results: WorkerResults = []
    async with payment_transaction(session=session):
        ids = list(
            (
                await session.execute(
                    base_select(Subscription)
                    .with_only_columns(Subscription.id, Subscription.restaurant_id)
                    .where(Subscription.status.in_(["active", "trial", "scheduled"]))
                )
            ).all()
        )
        for identifier, restaurant_id in ids:
            await session.execute(
                base_select(Restaurant)
                .with_only_columns(Restaurant.id)
                .where(Restaurant.id == restaurant_id)
                .with_for_update()
            )
            sub = (
                await session.execute(
                    base_select(Subscription)
                    .options(raiseload("*"))
                    .where(Subscription.id == identifier)
                    .with_for_update()
                )
            ).scalar_one()
            if sub.status == "scheduled" and sub.starts_at <= now:
                await session.execute(
                    update(Subscription)
                    .where(
                        Subscription.restaurant_id == sub.restaurant_id,
                        Subscription.id != sub.id,
                        Subscription.status.in_(["active", "trial"]),
                        Subscription.expires_at <= sub.starts_at,
                    )
                    .values(status="expired")
                )
                sub.status = "active"
                await session.flush()
            if sub.status not in {"active", "trial"}:
                continue
            last = (
                await session.execute(
                    base_select(SubscriptionPricingSnapshot)
                    .with_only_columns(SubscriptionPricingSnapshot.reference_end)
                    .where(
                        SubscriptionPricingSnapshot.source_subscription_id == sub.id,
                        SubscriptionPricingSnapshot.context == "active_month",
                    )
                    .order_by(SubscriptionPricingSnapshot.reference_end.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            anchor = sub.calendar_anchor or sub.starts_at
            due = min(
                add_months(
                    start=last or sub.starts_at, months=1, anchor_day=anchor.day
                ),
                sub.expires_at,
            )
            if (
                now <= sub.expires_at
                and (now >= due or now == sub.expires_at)
                and (sub.billing_cycle != "trial" or now == sub.expires_at)
            ):
                await capture_active_month(
                    session=session,
                    owner_id=sub.owner_id,
                    restaurant_id=sub.restaurant_id,
                    source=sub,
                    now=now,
                )
                results.append((sub.id, "recorded_active_month"))
            if now >= sub.expires_at:
                sub.status = "expired"
                results.append((sub.id, "expired"))
        await session.flush()
    if results:
        logger.info(
            "subscription_boundaries_processed", extra={"event_count": len(results)}
        )
    return results
