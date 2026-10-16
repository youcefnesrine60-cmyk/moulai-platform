# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Verify trial dates obey the PostgreSQL billing timestamp convention."""

# ==============================================
# IMPORTS
# ==============================================

from datetime import (
    datetime,
    timedelta,
    timezone,
)
from types import SimpleNamespace
from unittest.mock import (
    AsyncMock,
    Mock,
)

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Subscription
from app.services.business import subscription_service

# ==============================================
# TRIAL TIMESTAMP CONTRACT
# ==============================================


@pytest.mark.asyncio
async def test_trial_dates_are_utc_naive_with_exact_duration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Avoid asyncpg offset mismatches while preserving the thirty-day trial."""
    instant = datetime(2026, 10, 13, 12, 30, tzinfo=timezone.utc)
    clock = Mock(spec=datetime)
    clock.now.return_value = instant
    monkeypatch.setattr(subscription_service, "datetime", clock)
    service = subscription_service.SubscriptionService(session=Mock(spec=AsyncSession))
    subscription = Subscription(id=88)
    service.owner_repo = SimpleNamespace(
        get_by_id=AsyncMock(return_value=SimpleNamespace(trial_used=False)),
        update=AsyncMock(),
    )
    service.plan_repo = SimpleNamespace(
        get_by_code=AsyncMock(return_value=SimpleNamespace(id=7))
    )
    service.repo = SimpleNamespace(create=AsyncMock(return_value=subscription))

    result = await service.create_trial_subscription(owner_id=10, restaurant_id=55)

    data = service.repo.create.await_args.kwargs["data"]
    assert result is subscription
    assert data["starts_at"] == instant.replace(tzinfo=None)
    assert data["expires_at"] - data["starts_at"] == timedelta(days=30)
    assert data["starts_at"].tzinfo is None
    assert data["expires_at"].tzinfo is None
    service.owner_repo.update.assert_awaited_once_with(id=10, data={"trial_used": True})
