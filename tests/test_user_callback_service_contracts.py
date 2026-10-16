# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# USER CALLBACK SERVICE CONTRACTS
# Telegram consent callbacks use UserService directly.
# ==============================================

"""Contract tests for user-consent callback service migration."""

import re
from types import SimpleNamespace
from typing import Self
from unittest.mock import AsyncMock

import pytest

from app.handlers.callbacks.customer import restaurant_list
from app.handlers.callbacks.owner import register

# ==============================================
# TEST HELPERS
# ==============================================


class ManagedSession:
    """Minimal async session scope for callback contract assertions."""

    async def __aenter__(self) -> Self:
        """Return the fake session when entering the async context."""
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        """Exit the fake session context without suppressing exceptions."""
        return


async def get_managed_session(*, session: ManagedSession) -> ManagedSession:
    """Provide a fake session through the production session factory contract."""
    return session


# ==============================================
# CONSENT CHECK
# ==============================================


@pytest.mark.asyncio
async def test_customer_callback_checks_consent_through_user_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A customer without consent is routed to consent UI through UserService."""
    session = ManagedSession()
    service = SimpleNamespace(has_consent=AsyncMock(return_value=False))

    monkeypatch.setattr(
        restaurant_list,
        "get_session",
        lambda: get_managed_session(session=session),
    )
    monkeypatch.setattr(restaurant_list, "UserService", lambda _: service)
    monkeypatch.setattr(restaurant_list.UIManager, "edit", AsyncMock())
    monkeypatch.setattr(restaurant_list, "consent_text", lambda: "consent")
    monkeypatch.setattr(restaurant_list, "consent_ui", AsyncMock(return_value={}))

    await restaurant_list.customer_callback(
        chat_id=501,
        message_id=61,
        callback_data="customer",
        match=re.match(r"customer", "customer"),
    )

    service.has_consent.assert_awaited_once_with(chat_id=501)
    restaurant_list.UIManager.edit.assert_awaited_once()


# ==============================================
# CONSENT WRITE
# ==============================================


@pytest.mark.asyncio
async def test_owner_consent_callback_grants_consent_through_user_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Accepting owner consent calls UserService without repository compatibility."""
    session = ManagedSession()
    service = SimpleNamespace(give_consent=AsyncMock())

    monkeypatch.setattr(
        register,
        "get_session",
        lambda: get_managed_session(session=session),
    )
    monkeypatch.setattr(register, "UserService", lambda _: service)
    monkeypatch.setattr(register.UIManager, "cleanup_messages", AsyncMock())
    monkeypatch.setattr(register.UIManager, "send_new_message", AsyncMock(return_value=None))
    monkeypatch.setattr(register, "clear_user_state", AsyncMock())
    monkeypatch.setattr(register, "delete_message", AsyncMock())
    monkeypatch.setattr(register, "back_ui", AsyncMock(return_value={}))

    await register.consent_callback(
        chat_id=502,
        message_id=62,
        callback_data="consent_owner",
        match=re.match(r"consent_owner", "consent_owner"),
    )

    service.give_consent.assert_awaited_once_with(chat_id=502)
