# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Non-writing runtime proofs on the existing disposable loopback launcher.

Only test setup writes its synthetic probe. The production transaction listener
is unchanged; Neon identity observations are replaced with real local instance
attestation because a standalone PostgreSQL server has no Neon postmaster GUCs.
"""

import importlib
from collections.abc import AsyncIterator
from dataclasses import replace
from types import SimpleNamespace
from typing import Any
from unittest.mock import (
    AsyncMock,
    patch,
)

import pytest
from httpx import (
    ASGITransport,
    AsyncClient,
)
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core import (
    database,
    health_only,
)
from app.core.health_only import (
    HealthOnlyConfigurationError,
    HealthOnlyDatabasePolicy,
    install_health_only_database_guard,
)
from test_support.local_postgres import (
    LocalPostgresSettings,
    read_local_test_identity,
)

pytestmark = pytest.mark.database


# ==============================================
# OWNED LOCAL INSTANCE AND SYNTHETIC PROBE
# ==============================================


@pytest.fixture
async def local_probe(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[SimpleNamespace]:
    """Refuse every remote mode; provision only the launcher's owned local DB."""
    if not request.config.getoption("--local-postgres-tests"):
        pytest.skip("Health-only PostgreSQL proofs require the isolated local launcher")
    configuration = LocalPostgresSettings()
    assert configuration.PROFILE == "legacy"
    arguments = {"ssl": False, "timeout": 10, "command_timeout": 15}
    writer = create_async_engine(
        configuration.URL.get_secret_value(),
        connect_args=arguments,
        hide_parameters=True,
    )
    reader = create_async_engine(
        configuration.URL.get_secret_value(),
        connect_args=arguments,
        hide_parameters=True,
        pool_size=1,
        max_overflow=0,
    )
    attestations: list[str] = []

    # ==============================================
    # REAL LOCAL IDENTITY IN PLACE OF NEON-ONLY POSTMASTER SETTINGS
    # ==============================================

    def attest_local(connection: Connection, **expected: Any) -> dict[str, str]:
        """Attest the same owned local process on every guarded transaction."""
        read_local_test_identity(connection, configuration=configuration)
        assert expected["branch_id"] == "br-health-only-fixture"
        attestations.append("attested")
        return {"database": "moulai_pytest"}

    policy = HealthOnlyDatabasePolicy(
        endpoint_id="ep-health-only-fixture",
        branch_id="br-health-only-fixture",
        project_id="project-health-only-fixture",
        protected_branch_id="br-protected-fixture",
    )
    monkeypatch.setattr(health_only, "read_test_database_identity", attest_local)
    install_health_only_database_guard(engine=reader, policy=policy)
    probe_created = False
    try:
        async with writer.begin() as connection:
            await connection.run_sync(
                lambda sync: read_local_test_identity(sync, configuration=configuration)
            )
            await connection.execute(
                text(
                    "CREATE TABLE public.health_only_probe (id SERIAL PRIMARY KEY, value TEXT NOT NULL)"
                )
            )
            await connection.execute(
                text("INSERT INTO public.health_only_probe VALUES (1,'unchanged')")
            )
        probe_created = True
        yield SimpleNamespace(
            writer=writer,
            reader=reader,
            policy=policy,
            attest=attest_local,
            attestations=attestations,
        )
        async with writer.connect() as connection:
            assert (
                await connection.execute(
                    text("SELECT id,value FROM health_only_probe ORDER BY id")
                )
            ).all() == [(1, "unchanged")]
    finally:
        try:
            await reader.dispose()
            if probe_created:
                # Remove only the probe this fixture created and committed.
                # A pre-existing table is never adopted or dropped on failure.
                async with writer.begin() as connection:
                    await connection.run_sync(
                        lambda sync: read_local_test_identity(
                            sync, configuration=configuration
                        )
                    )
                    await connection.execute(
                        text("DROP TABLE public.health_only_probe")
                    )
                    assert (
                        await connection.scalar(
                            text("SELECT to_regclass('public.health_only_probe')")
                        )
                        is None
                    )
                    assert (
                        await connection.scalar(
                            text(
                                "SELECT to_regclass('public.health_only_probe_id_seq')"
                            )
                        )
                        is None
                    )
        finally:
            await writer.dispose()


# ==============================================
# REAL POSTGRESQL REJECTION, NOT SQL-TEXT MOCKING
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "statement",
    [
        "INSERT INTO health_only_probe VALUES (2,'blocked')",
        "UPDATE health_only_probe SET value='blocked' WHERE id=1",
        "DELETE FROM health_only_probe WHERE id=1",
        "TRUNCATE health_only_probe",
        "CREATE TABLE health_only_forbidden (id INTEGER)",
        "ALTER TABLE health_only_probe ADD COLUMN forbidden INTEGER",
        "DROP TABLE health_only_probe",
        "GRANT SELECT ON health_only_probe TO PUBLIC",
        "SELECT nextval('health_only_probe_id_seq')",
    ],
)
async def test_postgres_rejects_persistent_writes(
    local_probe: SimpleNamespace, statement: str
) -> None:
    """The real server returns read_only_sql_transaction and preserves the probe."""
    async with local_probe.reader.connect() as connection:
        with pytest.raises(DBAPIError) as failure:
            await connection.execute(text(statement))
        assert failure.value.orig.sqlstate == "25006"
        await connection.rollback()
    assert local_probe.attestations


# ==============================================
# REAPPLY AFTER COMMIT, ROLLBACK, SESSION RESET AND RECONNECT
# ==============================================


@pytest.mark.asyncio
async def test_every_transaction_is_read_only_even_when_session_default_is_off(
    local_probe: SimpleNamespace,
) -> None:
    """Pooling, explicit commits and caller session changes cannot weaken the hook."""
    async with local_probe.reader.connect() as connection:
        assert (
            await connection.scalar(text("SHOW default_transaction_read_only")) == "off"
        )
        assert await connection.scalar(text("SHOW transaction_read_only")) == "on"
        await connection.commit()
        await connection.execute(text("SET default_transaction_read_only=off"))
        await connection.commit()
        assert await connection.scalar(text("SHOW transaction_read_only")) == "on"
        await connection.rollback()
        assert (
            await connection.scalar(
                text("SELECT value FROM health_only_probe WHERE id=1")
            )
            == "unchanged"
        )
        await connection.commit()
    await local_probe.reader.dispose()
    async with local_probe.reader.connect() as connection:
        assert await connection.scalar(text("SHOW transaction_read_only")) == "on"
    assert len(local_probe.attestations) >= 5


# ==============================================
# ORM SESSION AND SAVEPOINTS USE THE SAME GUARDED ENGINE
# ==============================================


@pytest.mark.asyncio
async def test_async_sessions_and_savepoints_cannot_write(
    local_probe: SimpleNamespace,
) -> None:
    """Direct Core and ORM-session statements share actual PostgreSQL enforcement."""
    sessions = async_sessionmaker(local_probe.reader, class_=AsyncSession)
    async with sessions() as session:
        assert (
            await session.scalar(text("SELECT value FROM health_only_probe WHERE id=1"))
            == "unchanged"
        )
        with pytest.raises(DBAPIError) as failure:
            async with session.begin_nested():
                await session.execute(
                    text("UPDATE health_only_probe SET value='blocked'")
                )
        assert failure.value.orig.sqlstate == "25006"
        await session.rollback()
        assert await session.scalar(text("SHOW transaction_read_only")) == "on"


# ==============================================
# ATTEMPTS TO REOPEN WRITES OR USE AUTOCOMMIT
# ==============================================


@pytest.mark.asyncio
async def test_transaction_cannot_be_changed_to_read_write(
    local_probe: SimpleNamespace,
) -> None:
    """The identity SELECT has taken a snapshot before caller SQL is admitted."""
    async with local_probe.reader.connect() as connection:
        with pytest.raises(DBAPIError) as failure:
            await connection.execute(text("SET TRANSACTION READ WRITE"))
        assert failure.value.orig.sqlstate == "25001"
        await connection.rollback()


# ==============================================
# SQLALCHEMY AUTOCOMMIT CANNOT BYPASS THE BEGIN GUARD
# ==============================================


@pytest.mark.asyncio
async def test_autocommit_is_refused_before_application_sql(
    local_probe: SimpleNamespace,
) -> None:
    """SET TRANSACTION must never be accepted outside a PostgreSQL transaction."""
    async with local_probe.reader.connect() as connection:
        connection = await connection.execution_options(isolation_level="AUTOCOMMIT")
        with pytest.raises(HealthOnlyConfigurationError, match="transaction_required"):
            await connection.execute(
                text("UPDATE health_only_probe SET value='blocked'")
            )


# ==============================================
# REAL STARTUP CHECKS AND HTTP OBSERVATION ON LOCAL POSTGRESQL
# ==============================================


@pytest.mark.asyncio
async def test_real_lifespan_schema_validation_and_health_http(
    local_probe: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Run the real schema validator on the compatible migrated local schema."""
    from app import main

    original_app = main.app
    # Preserve existing imports of app.main.app in the other PostgreSQL suites.
    with patch.dict(main.__dict__), monkeypatch.context() as patcher:
        patcher.setattr(main.settings, "HEALTH_ONLY_MODE", True)
        patcher.setattr(database, "engine", local_probe.reader)
        patcher.setattr(
            database,
            "_DATABASE_CONFIGURATION",
            replace(
                database._DATABASE_CONFIGURATION,
                target="development",
                health_only_policy=local_probe.policy,
                endpoint_id=local_probe.policy.endpoint_id,
                branch_id=local_probe.policy.branch_id,
                project_id=local_probe.policy.project_id,
                protected_branch_id=local_probe.policy.protected_branch_id,
            ),
        )
        patcher.setattr(database, "read_test_database_identity", local_probe.attest)
        main = importlib.reload(main)
        callbacks = AsyncMock(
            side_effect=AssertionError("No business callback startup is allowed")
        )
        patcher.setattr(main, "register_routes", callbacks)
        async with main.app.router.lifespan_context(main.app), AsyncClient(
            transport=ASGITransport(app=main.app), base_url="http://test"
        ) as client:
            assert (await client.get("/")).status_code == 200
            assert (await client.get("/health")).status_code == 200
            assert (await client.post("/api/v1/users/", json={})).status_code == 503
            assert (await client.post("/webhook", json={})).status_code == 503
            assert (await client.get("/docs")).status_code == 503
        callbacks.assert_not_awaited()
    assert main.app is original_app
