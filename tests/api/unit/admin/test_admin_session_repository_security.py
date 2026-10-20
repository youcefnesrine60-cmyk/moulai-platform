# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Exercise real session repositories without a connection or sensitive logs."""

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
)

import pytest
from sqlalchemy.exc import (
    IntegrityError,
    StatementError,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.repositories.admin.admin_sessions_repo import AdminSessionsRepository
from app.schemas.admin_session import AdminSessionCreate
from app.services.business.admin.admin_session_service import AdminSessionService

# ==============================================
# INERT SQLALCHEMY BOUNDARY
# ==============================================

TOKEN = "repository-credential-must-never-appear-in-logs"
FUTURE = datetime(2099, 1, 1, tzinfo=UTC).replace(tzinfo=None)
STAMP = datetime(2026, 1, 1, tzinfo=UTC).replace(tzinfo=None)
LOOKUPS = ("get_by_session_token", "get_active_session")
MUTATIONS = ("update_activity", "deactivate_session", "extend_session")


def session_record(*, identifier: int = 9) -> SimpleNamespace:
    """Represent a database row while preserving the real repository behavior."""
    return SimpleNamespace(
        id=identifier,
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


def database_failure(*, integrity: bool = False) -> StatementError:
    """Include bound credential parameters, as real SQLAlchemy failures can do."""
    statement = "SELECT session_token FROM admin_sessions"
    parameters = {"session_token": TOKEN}
    original = RuntimeError("Sensitive driver failure")
    if integrity:
        return IntegrityError(statement, parameters, original)
    return StatementError("Session storage failed", statement, parameters, original)


@pytest.fixture
def repository() -> AdminSessionsRepository:
    """Replace only SQLAlchemy IO; never mock the repository under examination."""
    session = AsyncMock(spec=AsyncSession)
    session.info = {}
    session.execute.return_value = Mock()
    session.execute.return_value.scalar_one_or_none.return_value = session_record()
    return AdminSessionsRepository(session)


def assert_credential_free(*, caplog: pytest.LogCaptureFixture) -> None:
    """Check formatted exceptions and every structured log field for token data."""
    records = [record for record in caplog.records if record.name == logger.name]
    serialized = json.dumps([record.__dict__ for record in records], default=str)
    assert TOKEN[:12] not in caplog.text
    assert TOKEN[:12] not in serialized
    assert TOKEN not in serialized


# ==============================================
# LOOKUP AND MUTATION CREDENTIAL BOUNDARIES
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("method_name", [*LOOKUPS, *MUTATIONS])
@pytest.mark.parametrize("outcome", ["success", "missing", "error"])
async def test_real_repository_never_logs_session_lookup_credentials(
    repository: AdminSessionsRepository,
    caplog: pytest.LogCaptureFixture,
    method_name: str,
    outcome: str,
) -> None:
    """Keep raw parameters and token prefixes out of all lookup/write log paths."""
    caplog.set_level(logging.INFO, logger=logger.name)
    arguments: dict[str, Any] = {"session_token": TOKEN}
    if method_name == "extend_session":
        arguments["expires_at"] = FUTURE
    row = None if outcome == "missing" else session_record()
    repository.session.execute.return_value.scalar_one_or_none.return_value = row
    failure = database_failure()
    if outcome == "error":
        repository.session.execute.side_effect = failure
        with pytest.raises(StatementError) as raised:
            await getattr(repository, method_name)(**arguments)
        assert raised.value is failure
    else:
        result = await getattr(repository, method_name)(**arguments)
        assert result is row
        if method_name in MUTATIONS and row is not None:
            repository.session.commit.assert_awaited_once()
            repository.session.refresh.assert_awaited_once_with(row)
        else:
            repository.session.commit.assert_not_awaited()
    if outcome == "error":
        repository.session.commit.assert_not_awaited()
    repository.session.execute.assert_awaited_once()
    assert_credential_free(caplog=caplog)


@pytest.mark.asyncio
@pytest.mark.parametrize("outcome", ["success", "integrity", "statement"])
@pytest.mark.parametrize("entry_point", ["create", "create_session"])
async def test_real_repository_creation_does_not_log_insert_parameters(
    repository: AdminSessionsRepository,
    caplog: pytest.LogCaptureFixture,
    outcome: str,
    entry_point: str,
) -> None:
    """Cover inherited creation used by the service as well as the typed helper."""
    caplog.set_level(logging.INFO, logger=logger.name)
    data = {"admin_id": 7, "session_token": TOKEN, "expires_at": FUTURE}
    arguments = {"data": data} if entry_point == "create" else data
    if outcome == "success":
        result = await getattr(repository, entry_point)(**arguments)
        assert result.session_token == TOKEN
        repository.session.commit.assert_awaited_once()
        repository.session.rollback.assert_not_awaited()
    else:
        failure = database_failure(integrity=outcome == "integrity")
        repository.session.flush.side_effect = failure
        with pytest.raises(StatementError) as raised:
            await getattr(repository, entry_point)(**arguments)
        assert raised.value is failure
        repository.session.rollback.assert_awaited_once()
        repository.session.commit.assert_not_awaited()
    assert_credential_free(caplog=caplog)


# ==============================================
# REAL BUSINESS-REPOSITORY SIGNATURE CONTRACTS
# ==============================================


@pytest.mark.asyncio
async def test_service_creates_through_the_real_typed_repository_entry_point(
    repository: AdminSessionsRepository, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exercise token generation and SQLAlchemy insertion without a mock API."""
    service = AdminSessionService(repository.session)
    service.repo = repository
    service.admin_repo = Mock()
    service.admin_repo.get_by_id = AsyncMock(return_value=SimpleNamespace(id=7))

    def generated_token() -> str:
        """Make the actual inserted credential deterministic for the assertion."""
        return TOKEN

    monkeypatch.setattr(
        "app.services.business.admin.admin_session_service.generate_session_token",
        generated_token,
    )
    result = await service.create_session(
        session_data=AdminSessionCreate(admin_id=7, expires_at=FUTURE)
    )
    assert result.session_token == TOKEN
    inserted = repository.session.add.call_args.args[0]
    assert inserted.admin_id == 7
    assert inserted.session_token == TOKEN
    assert inserted.expires_at == FUTURE
    repository.session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_service_deactivates_with_the_real_repository_contract(
    repository: AdminSessionsRepository,
) -> None:
    """A service mock must not conceal a nonexistent repository method."""
    service = AdminSessionService(repository.session)
    service.repo = repository
    result = await service.deactivate_session(session_token=TOKEN)
    assert result.is_active is False
    assert result.session_token == TOKEN


@pytest.mark.asyncio
@pytest.mark.parametrize("preserve_session", [False, True])
async def test_bulk_deactivation_preserves_the_explicitly_excluded_session(
    repository: AdminSessionsRepository, preserve_session: bool
) -> None:
    """Use the real bulk repository API and honor the caller's session exclusion."""
    service = AdminSessionService(repository.session)
    service.repo = repository
    rows = [session_record(), session_record(identifier=10)]
    rows[1].session_token = "another-administrative-session-token"
    returned = rows[1:] if preserve_session else rows
    repository.session.execute.return_value.scalars.return_value.all.return_value = (
        returned
    )
    count = await service.deactivate_all_sessions(
        admin_id=7, except_session_token=TOKEN if preserve_session else None
    )
    assert count == (1 if preserve_session else 2)
    assert rows[0].is_active is preserve_session
    assert rows[1].is_active is False
    statement = repository.session.execute.await_args.args[0]
    parameters = statement.compile().params
    assert 7 in parameters.values()
    assert (TOKEN in parameters.values()) is preserve_session
    assert "admin_sessions.admin_id =" in str(statement)
    assert "admin_sessions.is_active IS true" in str(statement)
    if preserve_session:
        assert "admin_sessions.session_token !=" in str(statement)
