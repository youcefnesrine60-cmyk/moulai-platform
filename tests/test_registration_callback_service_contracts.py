# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# REGISTRATION CALLBACK SERVICE CONTRACTS
# Telegram callbacks use the SQLAlchemy business service directly.
# ==============================================

"""Contract tests for registration callbacks after compatibility removal."""

import re
from types import SimpleNamespace
from typing import Self
from unittest.mock import AsyncMock

import pytest

from app.handlers.callbacks.admin import admin_handlers
from app.handlers.callbacks.owner import confirm

# ==============================================
# TEST HELPERS
# ==============================================


class ManagedSession:
    """Minimal async session context used to assert callback transactions."""

    def __init__(self) -> None:
        """Initialize the context-managed fake session."""
        self.commit = AsyncMock()

    async def __aenter__(self) -> Self:
        """Return the session when entering its async scope."""
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        """Close the fake session scope without suppressing exceptions."""
        return


async def get_managed_session(*, session: ManagedSession) -> ManagedSession:
    """Return the fake SQLAlchemy session through the production factory shape."""
    return session


# ==============================================
# OWNER CONFIRMATION
# ==============================================


@pytest.mark.asyncio
async def test_confirm_callback_approves_chat_request_through_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Owner confirmation resolves the request, approves it, and commits once."""
    session = ManagedSession()
    service = SimpleNamespace(
        get_by_chat_id=AsyncMock(return_value=SimpleNamespace(id=41)),
        approve=AsyncMock(return_value=SimpleNamespace(owner_id=7)),
    )
    update = AsyncMock()

    monkeypatch.setattr(
        confirm,
        "get_session",
        lambda: get_managed_session(session=session),
    )
    monkeypatch.setattr(confirm, "RegistrationRequestService", lambda _: service)
    monkeypatch.setattr(confirm.Idempotency, "protect", AsyncMock(return_value=True))
    monkeypatch.setattr(confirm.UIManager, "edit", update)

    await confirm.confirm_callback.__wrapped__(
        chat_id=9001,
        message_id=42,
        callback_data="confirm",
        match=re.match(r"confirm", "confirm"),
    )

    service.get_by_chat_id.assert_awaited_once_with(chat_id=9001)
    service.approve.assert_awaited_once_with(request_id=41)
    session.commit.assert_awaited_once()
    update.assert_awaited_once()


# ==============================================
# ADMIN APPROVAL AND REJECTION
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("callback", "method_name"),
    [
        (admin_handlers.admin_approve_callback, "approve"),
        (admin_handlers.admin_reject_callback, "reject"),
    ],
)
async def test_admin_registration_callbacks_use_service_and_commit(
    monkeypatch: pytest.MonkeyPatch,
    callback: object,
    method_name: str,
) -> None:
    """Administrative decisions use the service contract and commit their write."""
    session = ManagedSession()
    service = SimpleNamespace(
        approve=AsyncMock(return_value=SimpleNamespace(owner_id=7)),
        reject=AsyncMock(return_value=SimpleNamespace()),
    )

    monkeypatch.setattr(
        admin_handlers,
        "get_session",
        lambda: get_managed_session(session=session),
    )
    monkeypatch.setattr(admin_handlers, "RegistrationRequestService", lambda _: service)
    monkeypatch.setattr(
        admin_handlers,
        "_has_active_admin",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(admin_handlers.UIManager, "edit", AsyncMock())

    await callback.__wrapped__(
        chat_id=9002,
        message_id=43,
        callback_data="registration:42",
        match=re.match(r"(42)", "42"),
    )

    getattr(service, method_name).assert_awaited_once_with(request_id=42)
    session.commit.assert_awaited_once()
