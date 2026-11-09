# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# PAID SERVICE CALENDAR
# Preserve calendar anchors and count paid-service seniority without overlap or trial
# time.
# ==============================================

"""Calendar service periods and an overlap-free paid-service clock."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Declare the standard-library, framework and project dependencies used below.
# ==============================================

from calendar import monthrange
from collections.abc import Iterable
from datetime import (
    datetime,
    timedelta,
)

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Payment
from app.models.subscription import Subscription
from app.repositories.subscription_queries import base_select
from app.services.business.subscription_types import ServicePeriod

# ==============================================
# ADD MONTHS
# Advance calendar months, clamping short months without losing the anchor.
# ==============================================


def add_months(
    *, start: datetime, months: int, anchor_day: int | None = None
) -> datetime:
    """Advance calendar months, clamping short months without losing the anchor."""

    absolute = start.year * 12 + start.month - 1 + months
    year, month = divmod(absolute, 12)
    month += 1
    return start.replace(
        year=year,
        month=month,
        day=min(anchor_day or start.day, monthrange(year, month)[1]),
    )


# ==============================================
# COMPLETED PAID YEARS
# Union intervals, then advance a virtual calendar from first paid service.
# ==============================================


def completed_paid_years(*, periods: Iterable[ServicePeriod], now: datetime) -> int:
    """Union intervals, then advance a virtual calendar from first paid service.

    Interruptions pause this clock by their exact duration. Calendar anniversaries
    of its initial anchor determine whole years, including leap-day clamping.
    """
    ranges: list[ServicePeriod] = []
    for start, end in sorted(periods):
        end = min(end, now)
        if start >= end:
            continue
        if ranges and start <= ranges[-1][1]:
            ranges[-1] = (ranges[-1][0], max(ranges[-1][1], end))
        else:
            ranges.append((start, end))
    if not ranges:
        return 0
    anchor = ranges[0][0]
    virtual_end = anchor + sum((end - start for start, end in ranges), timedelta())
    years = virtual_end.year - anchor.year
    if add_months(start=anchor, months=years * 12) > virtual_end:
        years -= 1
    return max(0, years)


# ==============================================
# PAID YEARS
# Count an owner's paid service, excluding trials and clipping cancellations.
# ==============================================


async def paid_years(*, session: AsyncSession, owner_id: int, now: datetime) -> int:
    """Count an owner's paid service, excluding trials and clipping cancellations."""

    paid = (
        base_select(Payment)
        .with_only_columns(Payment.subscription_id)
        .where(
            Payment.owner_id == owner_id,
            Payment.status == "paid",
            Payment.paid_at.is_not(None),
        )
    )
    rows = (
        await session.execute(
            base_select(Subscription)
            .with_only_columns(
                Subscription.starts_at,
                Subscription.expires_at,
                Subscription.cancelled_at,
                Subscription.status,
            )
            .where(
                Subscription.owner_id == owner_id,
                Subscription.billing_cycle != "trial",
                Subscription.amount > 0,
                Subscription.starts_at.is_not(None),
                Subscription.expires_at.is_not(None),
                Subscription.id.in_(paid),
            )
        )
    ).all()
    periods: list[ServicePeriod] = []
    for start, end, cancelled, status in rows:
        if status == "cancelled":
            if cancelled is None:
                raise ValueError("paid_service_history_incomplete")
            end = min(end, cancelled)
        periods.append((start, end))
    return completed_paid_years(periods=periods, now=now)
