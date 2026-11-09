# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# REGISTRATION SUCCESS NOTIFICATION ORDER
# Exercise existing callbacks with inert service/UI doubles to observe commit-before-success.
# ==============================================

"""No Telegram call; the local callback order must never announce success before commit."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND LOCAL SESSION DOUBLE
# Mock only UI and transaction completion; SQL atomicity has separate real PostgreSQL proofs.
# ==============================================

import re
from types import SimpleNamespace
from typing import Self
from unittest.mock import AsyncMock

import pytest

from app.handlers.callbacks.admin import admin_handlers
from app.handlers.callbacks.owner import confirm


class CallbackSession:
    """Track a commit result without opening any connection."""

    # ==============================================
    # INERT CALLBACK SESSION
    # Record pending approval and simulate either a successful or refused commit.
    # ==============================================

    def __init__(self, *, events: list[str], fail_commit: bool) -> None:
        self.events = events
        self.fail_commit = fail_commit

    # ==============================================
    # ENTER THE EXISTING ASYNC SESSION SHAPE
    # Return the test object accepted by the callbacks' session context.
    # ==============================================

    async def __aenter__(self) -> Self:
        return self

    # ==============================================
    # EXIT WITHOUT SUPPRESSING COMMIT ERRORS
    # Preserve the real callback exception handling path.
    # ==============================================

    async def __aexit__(self, kind: object, value: object, traceback: object) -> None:
        return

    # ==============================================
    # SIMULATED COMMIT OUTCOME
    # A failed commit must produce only an error response, never a success notification.
    # ==============================================

    async def commit(self) -> None:
        self.events.append("commit_failed" if self.fail_commit else "commit")
        if self.fail_commit:
            raise ValueError("synthetic_commit_failure")


# ==============================================
# OWNER AND ADMIN CALLBACK NOTIFICATIONS
# Keep success ordering explicit and cover the failure-to-commit branch for both entry points.
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("admin", [False, True])
@pytest.mark.parametrize("fail_commit", [False, True])
async def test_success_message_follows_commit(
    monkeypatch: pytest.MonkeyPatch, admin: bool, fail_commit: bool
) -> None:
    """The success UI is reached only after the callback has completed its commit."""
    events: list[str] = []
    session = CallbackSession(events=events, fail_commit=fail_commit)

    async def get_session() -> CallbackSession:
        """Supply an inert object through the existing asynchronous factory contract."""
        return session

    async def approved(**kwargs: object) -> SimpleNamespace:
        """Represent prepared domain changes without pretending they are committed."""
        events.append("prepared")
        return SimpleNamespace(owner_id=7)

    async def edit(**kwargs: object) -> None:
        """Record success markers without sending a message to any recipient."""
        message = str(kwargs["text"])
        success = message.startswith(("🎉", "✅ تمت الموافقة"))
        events.append("success" if success else "error")
        if success:
            assert "commit" in events

    module = admin_handlers if admin else confirm
    service = SimpleNamespace(
        get_by_chat_id=AsyncMock(return_value=SimpleNamespace(id=41)), approve=approved
    )
    monkeypatch.setattr(module, "get_session", get_session)
    monkeypatch.setattr(module, "RegistrationRequestService", lambda _: service)
    monkeypatch.setattr(module.UIManager, "edit", edit)
    if admin:
        monkeypatch.setattr(
            admin_handlers, "_has_active_admin", AsyncMock(return_value=True)
        )
        match = re.match(r"admin_approve:(\d+)", "admin_approve:41")
        await admin_handlers.admin_approve_callback.__wrapped__(
            chat_id=9001, message_id=42, callback_data="admin_approve:41", match=match
        )
    else:
        monkeypatch.setattr(
            confirm.Idempotency, "protect", AsyncMock(return_value=True)
        )
        await confirm.confirm_callback.__wrapped__(
            chat_id=9001,
            message_id=42,
            callback_data="confirm",
            match=re.match("confirm", "confirm"),
        )
    if fail_commit:
        assert "success" not in events and "commit_failed" in events
    else:
        assert events.index("commit") < events.index("success")
