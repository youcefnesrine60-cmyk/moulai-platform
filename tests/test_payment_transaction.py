# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Verify billing transaction ownership without an engine or database connection."""

# ==============================================
# IMPORTS
# ==============================================

from types import SimpleNamespace
from typing import cast
from unittest.mock import (
    AsyncMock,
    MagicMock,
)

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import SessionTransactionOrigin

from app.services.business.payment_transaction import payment_transaction

# ==============================================
# OFFLINE SESSION BOUNDARIES
# ==============================================


def mocked_session(
    *,
    active: bool,
    origin: SessionTransactionOrigin | None,
    defer: bool,
) -> MagicMock:
    """Expose transaction boundaries and flags while forbidding any database IO."""
    session = MagicMock(spec=AsyncSession)
    session.in_transaction.return_value = active
    session.get_transaction.return_value = SimpleNamespace(
        sync_transaction=SimpleNamespace(origin=origin) if origin is not None else None
    )
    session.info = {"defer_repository_commit": defer, "unrelated_context": "preserved"}
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    for boundary in (session.begin.return_value, session.begin_nested.return_value):
        boundary.__aenter__ = AsyncMock()
        boundary.__aexit__ = AsyncMock(return_value=False)
    return session


# ==============================================
# EXPLICIT OUTER TRANSACTIONS AND AUTOBEGIN
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("active", "origin", "defer", "owned_autobegin"),
    [
        (False, None, False, False),
        (True, SessionTransactionOrigin.BEGIN, False, False),
        (True, SessionTransactionOrigin.AUTOBEGIN, False, True),
        (True, SessionTransactionOrigin.AUTOBEGIN, True, False),
        (True, None, False, False),
    ],
    ids=["new", "explicit-outer", "owned-autobegin", "deferred-autobegin", "no-sync"],
)
@pytest.mark.parametrize("fails", [False, True], ids=["success", "failure"])
async def test_transaction_ownership_preserves_the_callers_boundary(
    active: bool,
    origin: SessionTransactionOrigin | None,
    defer: bool,
    owned_autobegin: bool,
    fails: bool,
) -> None:
    """Only owned autobegin may commit or roll back the session itself."""
    session = mocked_session(active=active, origin=origin, defer=defer)
    previous_info = dict(session.info)
    failure = RuntimeError("Expected local transaction failure")
    try:
        async with payment_transaction(session=cast(AsyncSession, session)):
            assert session.info["defer_repository_commit"] is True
            if fails:
                raise failure
    except RuntimeError as error:
        assert fails
        assert error is failure
    else:
        assert not fails

    chosen = session.begin_nested if active else session.begin
    other = session.begin if active else session.begin_nested
    chosen.assert_called_once_with()
    other.assert_not_called()
    chosen.return_value.__aenter__.assert_awaited_once()
    chosen.return_value.__aexit__.assert_awaited_once()
    if owned_autobegin and not fails:
        session.commit.assert_awaited_once_with()
    else:
        session.commit.assert_not_awaited()
    if owned_autobegin and fails:
        session.rollback.assert_awaited_once_with()
    else:
        session.rollback.assert_not_awaited()
    assert session.info == previous_info


@pytest.mark.asyncio
@pytest.mark.parametrize("fails", [False, True], ids=["success", "failure"])
async def test_nested_real_sqlalchemy_contexts_need_no_database_engine(
    fails: bool,
) -> None:
    """Use actual SQLAlchemy context objects while retaining explicit outer control."""
    async with AsyncSession() as session:
        assert session.sync_session.bind is None
        async with session.begin():
            outer = session.get_transaction()
            assert outer is not None
            try:
                async with payment_transaction(session=session):
                    assert session.get_transaction() is outer
                    assert session.in_nested_transaction()
                    assert session.info["defer_repository_commit"] is True
                    if fails:
                        raise RuntimeError("Expected nested transaction failure")
            except RuntimeError as error:
                assert fails
                assert str(error) == "Expected nested transaction failure"
            else:
                assert not fails
            assert session.get_transaction() is outer
            assert outer.is_active
            assert session.in_transaction()
            assert not session.in_nested_transaction()
            assert "defer_repository_commit" not in session.info
        assert not session.in_transaction()


@pytest.mark.asyncio
async def test_owned_autobegin_commit_failure_rolls_back_and_restores_flags() -> None:
    """A failed final commit cannot leave this operation's session ownership flag."""
    session = mocked_session(
        active=True, origin=SessionTransactionOrigin.AUTOBEGIN, defer=False
    )
    session.commit.side_effect = RuntimeError("Expected local commit failure")
    with pytest.raises(RuntimeError, match="Expected local commit failure"):
        async with payment_transaction(session=cast(AsyncSession, session)):
            assert session.info["defer_repository_commit"] is True
    session.rollback.assert_awaited_once_with()
    assert session.info == {
        "defer_repository_commit": False,
        "unrelated_context": "preserved",
    }
