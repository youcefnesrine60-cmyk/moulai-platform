# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🏢 BRANCH FEATURE GUARD
# التحقق من اشتراك الفروع والذرية مع عداد الاستخدام
# ==============================================

"""Unit tests for fail-closed branch feature access and its unit of work."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import ForbiddenError
from app.schemas.branch import BranchCreate
from app.services.business import branch_service
from app.services.business.branch_service import BranchService

# ==============================================
# 🧩 TEST HELPERS
# ==============================================


@asynccontextmanager
async def no_op_branch_transaction(_session: object):
    """Provide an isolated transaction boundary for service-unit tests."""
    yield


def build_branch() -> SimpleNamespace:
    """Build a branch object accepted by the response schema."""
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=7,
        restaurant_id=11,
        name="Central branch",
        phone=None,
        wilaya=None,
        lat=None,
        lng=None,
        is_active=True,
        created_at=now,
        updated_at=now,
    )


def build_service() -> BranchService:
    """Build a service with an isolated repository and session."""
    service = BranchService(session=MagicMock())
    service.repo = MagicMock()
    service.repo.get_by_name = AsyncMock(return_value=None)
    service.repo.create = AsyncMock(return_value=build_branch())
    service.count_by_restaurant = AsyncMock(return_value=0)
    return service


# ==============================================
# 🚫 FAIL-CLOSED FEATURE ACCESS
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "guard_error",
    (
        "no_active_subscription",
        "feature_not_available",
        "feature_limit_reached",
    ),
)
async def test_branch_creation_denies_each_feature_guard_error(
    monkeypatch: pytest.MonkeyPatch,
    guard_error: str,
) -> None:
    """Every documented feature-guard failure prevents creating a branch."""
    service = build_service()
    require_feature = AsyncMock(side_effect=ValueError(guard_error))
    increment_usage = AsyncMock()
    monkeypatch.setattr(
        branch_service,
        "branch_transaction",
        no_op_branch_transaction,
    )
    monkeypatch.setattr(branch_service, "require_feature", require_feature)
    monkeypatch.setattr(branch_service, "increase_usage", increment_usage)

    with pytest.raises(ForbiddenError) as captured:
        await service.create_branch(
            restaurant_id=11,
            branch_data=BranchCreate(name="Central branch"),
        )

    assert captured.value.error_code == guard_error
    service.repo.create.assert_not_awaited()
    increment_usage.assert_not_awaited()


# ==============================================
# ✅ ALLOWED FEATURE ACCESS
# ==============================================


@pytest.mark.asyncio
async def test_branch_creation_checks_feature_and_increments_usage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An allowed branch is persisted and counted with the same session."""
    service = build_service()
    require_feature = AsyncMock()
    increment_usage = AsyncMock(return_value=1)
    monkeypatch.setattr(
        branch_service,
        "branch_transaction",
        no_op_branch_transaction,
    )
    monkeypatch.setattr(branch_service, "require_feature", require_feature)
    monkeypatch.setattr(branch_service, "increase_usage", increment_usage)

    response = await service.create_branch(
        restaurant_id=11,
        branch_data=BranchCreate(name="Central branch"),
    )

    assert response.id == 7
    require_feature.assert_awaited_once_with(
        session=service.session,
        restaurant_id=11,
        feature_id=branch_service.BRANCH_FEATURE_ID,
    )
    increment_usage.assert_awaited_once_with(
        session=service.session,
        restaurant_id=11,
        feature_id=branch_service.BRANCH_FEATURE_ID,
    )


# ==============================================
# 🔒 TRANSACTION BOUNDARY
# ==============================================


class FakeTransaction:
    """Record entry and exit of a minimal async transaction context."""

    def __init__(self) -> None:
        self.entered = False
        self.exit_exception: type[BaseException] | None = None

    async def __aenter__(self) -> None:
        """Record that the transaction began."""
        self.entered = True

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        _exception: BaseException | None,
        _traceback: object,
    ) -> bool:
        """Record the exception that would cause the database rollback."""
        self.exit_exception = exception_type
        return False


class FakeSession:
    """Minimal session implementing the branch transaction contract."""

    def __init__(self) -> None:
        self.info: dict[str, object] = {}
        self.transaction = FakeTransaction()
        self.commit = AsyncMock()
        self.rollback = AsyncMock()

    def in_transaction(self) -> bool:
        """Report a new unit of work with no prior transaction."""
        return False

    def begin(self) -> FakeTransaction:
        """Return the transaction context used by the unit of work."""
        return self.transaction


@pytest.mark.asyncio
async def test_branch_transaction_defers_repository_commits_until_boundary() -> None:
    """The boundary owns commits and restores repository commit configuration."""
    session = FakeSession()

    async with branch_service.branch_transaction(session):
        assert session.info["defer_repository_commit"] is True

    assert session.transaction.entered is True
    assert session.info == {}


# ==============================================
# ➖ USAGE DECREMENT
# التحقق من ربط حذف الفرع بالجلسة ذاتها
# ==============================================


@pytest.mark.asyncio
async def test_branch_deletion_decrements_usage_with_the_service_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Deleting a branch decrements feature usage through the active session."""
    service = build_service()
    service.repo.get_by_id = AsyncMock(return_value=build_branch())
    service.repo.deactivate = AsyncMock()
    decrement_usage = AsyncMock(return_value=0)
    monkeypatch.setattr(branch_service, "decrease_usage", decrement_usage)

    await service.delete_branch(branch_id=7)

    decrement_usage.assert_awaited_once_with(
        session=service.session,
        restaurant_id=11,
        feature_id=branch_service.BRANCH_FEATURE_ID,
    )
