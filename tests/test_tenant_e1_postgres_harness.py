# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Offline safety regression for G2 transaction ownership and expected failures."""

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import (
    AsyncMock,
    MagicMock,
)

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
)

from scripts.rehearse_tenant_e1 import (
    ROOT,
    BoundRehearsal,
)
from scripts.validate_tenant_e1_postgres import (
    checked_transaction,
    original_catalogs,
    reject_sql,
)

# ==============================================
# PINNED TRANSACTION REFUSAL BEFORE FIXTURE SQL
# ==============================================


@pytest.mark.asyncio
async def test_failed_identity_cannot_reach_fixture() -> None:
    """A connection refusal rolls back and does not execute even timeout SQL."""
    connection = AsyncMock(spec=AsyncConnection)
    transaction = AsyncMock()
    connection.execution_options.return_value = connection
    connection.begin = AsyncMock(return_value=transaction)
    connection.run_sync.side_effect = RuntimeError("wrong_identity")
    engine = MagicMock(spec=AsyncEngine)
    engine.connect.return_value.__aenter__.return_value = connection
    with pytest.raises(RuntimeError, match="wrong_identity"):
        async with checked_transaction(engine, bound=cast(BoundRehearsal, object())):
            pytest.fail("unauthorized fixture was reached")
    transaction.rollback.assert_awaited_once()
    transaction.commit.assert_not_awaited()
    connection.execute.assert_not_awaited()


# ==============================================
# CALLER-OWNED COMMIT AND FULL ROLLBACK
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("commit", [False, True])
async def test_transaction_commits_only_explicitly(*, commit: bool) -> None:
    """Default fixture work rolls back; only an explicit caller commits."""
    connection = AsyncMock(spec=AsyncConnection)
    transaction = AsyncMock()
    connection.execution_options.return_value = connection
    connection.begin = AsyncMock(return_value=transaction)
    engine = MagicMock(spec=AsyncEngine)
    engine.connect.return_value.__aenter__.return_value = connection
    async with checked_transaction(
        engine, bound=cast(BoundRehearsal, object()), commit=commit
    ) as actual:
        assert actual is connection
    assert transaction.commit.await_count == int(commit)
    assert transaction.rollback.await_count == int(not commit)
    connection.run_sync.assert_awaited_once()


# ==============================================
# FIXTURE ERROR CANNOT COMMIT PARTIAL WORK
# ==============================================


@pytest.mark.asyncio
async def test_fixture_failure_rolls_back_commit_requested() -> None:
    """An unexpected assertion aborts the full requested write transaction."""
    connection = AsyncMock(spec=AsyncConnection)
    transaction = AsyncMock()
    connection.execution_options.return_value = connection
    connection.begin = AsyncMock(return_value=transaction)
    engine = MagicMock(spec=AsyncEngine)
    engine.connect.return_value.__aenter__.return_value = connection
    with pytest.raises(AssertionError, match="fixture_failed"):
        async with checked_transaction(
            engine, bound=cast(BoundRehearsal, object()), commit=True
        ):
            raise AssertionError("fixture_failed")
    transaction.commit.assert_not_awaited()
    transaction.rollback.assert_awaited_once()


# ==============================================
# EXPECTED SQL ERRORS MUST MATCH EXACT STATES
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "state,accepted", [("23514", True), ("23503", False), ("42601", False)]
)
async def test_unexpected_sqlstate_is_a_failure(*, state: str, accepted: bool) -> None:
    """A syntax error cannot be counted as a passing security rejection."""
    error = RuntimeError("synthetic driver error")
    error.sqlstate = state  # type: ignore[attr-defined]
    connection = AsyncMock(spec=AsyncConnection)
    savepoint = AsyncMock()
    connection.begin_nested = AsyncMock(return_value=savepoint)
    connection.execute.side_effect = IntegrityError(None, None, error)
    if accepted:
        assert await reject_sql(connection, statement="SELECT 1") == "23514"
    else:
        with pytest.raises(AssertionError, match="unexpected_sqlstate"):
            await reject_sql(connection, statement="SELECT 1")
    savepoint.rollback.assert_awaited_once()


# ==============================================
# MISSING DATABASE REFUSAL IS A REAL FAILURE
# ==============================================


@pytest.mark.asyncio
async def test_successful_forbidden_statement_fails_case() -> None:
    """An unexpectedly successful bypass must stop the PostgreSQL suite."""
    connection = AsyncMock(spec=AsyncConnection)
    connection.begin_nested = AsyncMock(return_value=AsyncMock())
    with pytest.raises(AssertionError, match="expected_database_refusal"):
        await reject_sql(connection, statement="SELECT 1")


# ==============================================
# EXACT E1 TRIGGER EXCLUSION PRESERVES LEGACY TRIGGERS
# ==============================================


@pytest.mark.asyncio
async def test_catalog_comparison_excludes_only_exact_e1_triggers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Use publishable SQL and preserve legacy triggers without artifact access."""
    from migration_support.tenant_e1_sql import TRIGGER_DEFINITIONS

    read_bytes = Path.read_bytes

    # ==============================================
    # FORBID RUNTIME SOURCE DEPENDENCIES ON IGNORED EVIDENCE
    # ==============================================
    def source_bytes(path: Path) -> bytes:
        """Keep historical artifacts optional for a clean checkout's verifier."""
        if path.resolve().is_relative_to((ROOT / "artifacts").resolve()):
            raise AssertionError("ignored_artifact_source_dependency")
        return read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", source_bytes)
    legacy = {"table_name": "legacy_table", "tgname": "tr_e1_existing_legacy"}
    created = [
        {"table_name": table, "tgname": name} for table, name, _ in TRIGGER_DEFINITIONS
    ]
    observed_categories: list[str] = []

    # ==============================================
    # MOCKED SELECT RESULT WITHOUT DATABASE IO
    # ==============================================
    async def query_result(statement: object) -> MagicMock:
        """Supply the two real trigger-name families and a distinct legacy row."""
        sql = str(statement)
        rows = [legacy, *created] if "pg_catalog.pg_trigger " in sql else []
        observed_categories.append(sql)
        result = MagicMock()
        result.mappings.return_value = rows
        return result

    names = (
        "columns",
        "constraints",
        "indexes",
        "triggers",
        "routines",
        "relations",
        "schemas",
        "database_privileges",
        "roles",
        "role_memberships",
        "default_privileges",
        "rls",
        "sequence_definitions",
    )
    catalogs = {
        name: {
            "count": int(name == "triggers"),
            "sha256": hashlib.sha256(
                json.dumps(
                    [legacy] if name == "triggers" else [],
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest(),
        }
        for name in names
    }
    bound = cast(
        BoundRehearsal,
        SimpleNamespace(
            baseline={
                "tables": {"legacy_table": {"columns": []}},
                "sequences": {},
                "catalogs": catalogs,
            }
        ),
    )
    connection = AsyncMock(spec=AsyncConnection)
    connection.execute.side_effect = query_result
    assert await original_catalogs(connection, bound=bound) == catalogs
    assert len(observed_categories) == 13
