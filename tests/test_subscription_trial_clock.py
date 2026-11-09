# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# TRIAL TIMESTAMP REGRESSION
# Check that a single trial uses naive UTC storage and exactly thirty days of service.
# ==============================================

"""Verify trial dates obey the PostgreSQL billing timestamp convention."""

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
from unittest.mock import Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.business import subscription_service

# ==============================================
# TRIAL TIMESTAMP CONTRACT
# Verify trial dates are utc naive with exact duration.
# ==============================================


@pytest.mark.asyncio
async def test_trial_dates_are_utc_naive_with_exact_duration(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify trial dates are utc naive with exact duration."""

    from test_support.subscription_fixtures import seed_graph

    graph = await seed_graph(db_session)
    instant = datetime(2026, 10, 13, 12, 30, tzinfo=timezone.utc)
    clock = Mock(spec=datetime)
    clock.now.return_value = instant
    monkeypatch.setattr(subscription_service, "datetime", clock)
    result = await subscription_service.SubscriptionService(
        session=db_session
    ).create_trial_subscription(owner_id=graph.owner, restaurant_id=graph.restaurant)
    assert result.starts_at == instant.replace(tzinfo=None)
    assert result.expires_at - result.starts_at == timedelta(days=30)
    assert result.starts_at.tzinfo is None
    from sqlalchemy import select

    from app.models.owner import Owner

    assert (
        await db_session.execute(
            select(Owner.trial_used).where(Owner.id == graph.owner)
        )
    ).scalar_one() is True
