# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Protect session credentials while exercising real administrative service logic."""

# ==============================================
# IMPORTS
# ==============================================

import json
import logging
from datetime import (
    UTC,
    datetime,
)
from types import SimpleNamespace
from typing import Any
from unittest.mock import (
    AsyncMock,
    Mock,
    create_autospec,
)

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.logger import logger
from app.repositories.admin.admin_repo import AdminRepository
from app.repositories.admin.admin_sessions_repo import AdminSessionsRepository
from app.schemas.admin_session import (
    AdminSessionCreate,
    AdminSessionExtend,
)
from app.services.business.admin import admin_session_service

# ==============================================
# INERT REPOSITORIES AND DETERMINISTIC SESSION DATA
# ==============================================

TOKEN = "credential-must-never-enter-administrative-logs"
FUTURE = datetime(2099, 1, 1, tzinfo=UTC).replace(tzinfo=None)
STAMP = datetime(2026, 1, 1, tzinfo=UTC).replace(tzinfo=None)
READ_METHODS = {
    "get_session_by_token": "get_by_session_token",
    "get_active_session": "get_active_session",
    "get_session_status": "get_by_session_token",
    "validate_session": "get_active_session",
}
WRITE_METHODS = {
    "create_session": "create_session",
    "update_activity": "update_activity",
    "deactivate_session": "deactivate_session",
    "deactivate_all_sessions": "deactivate_all_sessions",
    "extend_session": "extend_session",
}


def session_record() -> SimpleNamespace:
    """Represent an ORM row without attaching it to a database connection."""
    return SimpleNamespace(
        id=9,
        admin_id=7,
        session_token=TOKEN,
        expires_at=FUTURE,
        is_active=True,
        last_activity=STAMP,
        created_at=STAMP,
        updated_at=STAMP,
        ip_address=None,
        user_agent=None,
    )


def request_arguments(*, method_name: str) -> dict[str, Any]:
    """Create typed request data for token reads and administrative mutations."""
    if method_name == "create_session":
        return {"session_data": AdminSessionCreate(admin_id=7, expires_at=FUTURE)}
    if method_name == "extend_session":
        return {
            "extend_data": AdminSessionExtend(session_token=TOKEN, expires_at=FUTURE)
        }
    if method_name == "deactivate_all_sessions":
        return {"admin_id": 7, "except_session_token": TOKEN}
    return {"session_token": TOKEN}


@pytest.fixture
def session_service(
    monkeypatch: pytest.MonkeyPatch,
) -> admin_session_service.AdminSessionService:
    """Keep business logic and schema checks real while replacing all persistence."""
    service = admin_session_service.AdminSessionService(AsyncMock(spec=AsyncSession))
    service.repo = create_autospec(AdminSessionsRepository, instance=True)
    service.admin_repo = Mock(spec=AdminRepository)
    service.admin_repo.get_by_id = AsyncMock(return_value=SimpleNamespace(id=7))
    for method_name in set(READ_METHODS.values()) | set(WRITE_METHODS.values()):
        result = 4 if method_name == "deactivate_all_sessions" else session_record()
        getattr(service.repo, method_name).return_value = result

    def generated_token() -> str:
        """Supply a known credential to detect accidental logging during creation."""
        return TOKEN

    monkeypatch.setattr(
        admin_session_service, "generate_session_token", generated_token
    )
    return service


# ==============================================
# CREDENTIAL DISCLOSURE AND TRANSACTION BOUNDARIES
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("method_name", [*READ_METHODS, *WRITE_METHODS])
async def test_session_operations_keep_credentials_out_of_log_records(
    session_service: admin_session_service.AdminSessionService,
    caplog: pytest.LogCaptureFixture,
    method_name: str,
) -> None:
    """Keep both human log messages and serialized structured extras credential-free."""
    caplog.set_level(logging.INFO, logger=logger.name)
    arguments = request_arguments(method_name=method_name)
    result = await getattr(session_service, method_name)(**arguments)
    records = [record for record in caplog.records if record.name == logger.name]
    assert records, "Important session operations should retain their event logs"
    assert TOKEN not in caplog.text
    assert TOKEN not in json.dumps([record.__dict__ for record in records], default=str)
    if method_name in WRITE_METHODS:
        session_service.session.commit.assert_awaited_once()
    else:
        session_service.session.commit.assert_not_awaited()
    repository_method = (READ_METHODS | WRITE_METHODS)[method_name]
    getattr(session_service.repo, repository_method).assert_awaited_once()
    if method_name == "deactivate_all_sessions":
        assert result == 4
        session_service.repo.deactivate_all_sessions.assert_awaited_once_with(
            admin_id=7, except_session_token=TOKEN
        )
    elif method_name == "validate_session":
        assert result is True
    elif method_name == "get_session_status":
        assert result["admin_id"] == 7
        assert result["is_active"] is True
        assert result["is_expired"] is False
    else:
        assert result.id == 9
        assert result.session_token == TOKEN


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method_name",
    [
        "get_session_by_token",
        "get_active_session",
        "get_session_status",
        "update_activity",
        "deactivate_session",
        "extend_session",
    ],
)
async def test_missing_session_does_not_commit_or_disclose_its_lookup_token(
    session_service: admin_session_service.AdminSessionService,
    caplog: pytest.LogCaptureFixture,
    method_name: str,
) -> None:
    """Missing token lookups fail before commit and remain safe to log."""
    caplog.set_level(logging.INFO, logger=logger.name)
    repository_method = (READ_METHODS | WRITE_METHODS)[method_name]
    getattr(session_service.repo, repository_method).return_value = None
    with pytest.raises(NotFoundError):
        await getattr(session_service, method_name)(
            **request_arguments(method_name=method_name)
        )
    session_service.session.commit.assert_not_awaited()
    assert TOKEN not in caplog.text
    assert TOKEN not in json.dumps(
        [record.__dict__ for record in caplog.records], default=str
    )


@pytest.mark.asyncio
async def test_unlinked_admin_cannot_create_or_commit_a_session(
    session_service: admin_session_service.AdminSessionService,
) -> None:
    """Session creation still requires a persisted administrator before insertion."""
    session_service.admin_repo.get_by_id.return_value = None
    with pytest.raises(NotFoundError):
        await session_service.create_session(
            session_data=AdminSessionCreate(admin_id=7, expires_at=FUTURE)
        )
    session_service.repo.create_session.assert_not_awaited()
    session_service.session.commit.assert_not_awaited()
