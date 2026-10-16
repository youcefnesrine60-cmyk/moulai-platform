# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Verify database startup checks migrated schemas without creating objects."""

from collections.abc import (
    Callable,
    Iterator,
)
from dataclasses import replace
from types import (
    SimpleNamespace,
    TracebackType,
)
from typing import (
    Self,
    TypeAlias,
)
from unittest.mock import (
    AsyncMock,
    MagicMock,
)

import pytest
from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    LargeBinary,
    MetaData,
    String,
    Table,
    create_engine,
    event,
    inspect,
)
from sqlalchemy.engine import Connection

import app.core.database as database

# ==============================================
# REQUIRED AND INSTALLED SCHEMAS
# ==============================================


def schema_metadata(
    *,
    include_owner_subject: bool = True,
    include_receipts: bool = True,
) -> MetaData:
    """Build a small relational schema using the same inspection contract."""
    metadata = MetaData()
    owner_columns = [Column("id", Integer, primary_key=True)]
    if include_owner_subject:
        owner_columns.append(Column("auth_subject", String(255)))
    Table("owners", metadata, *owner_columns)
    Table(
        "payments",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("owner_id", Integer, ForeignKey("owners.id"), nullable=False),
    )
    if include_receipts:
        Table(
            "manual_payment_receipts",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("payment_id", Integer, ForeignKey("payments.id"), nullable=False),
            Column("content", LargeBinary, nullable=False),
        )
    return metadata


# ==============================================
# OFFLINE ASYNC CONNECTION ADAPTER
# ==============================================


class OfflineConnection:
    """Expose async lifecycle around a real in-memory SQLite connection."""

    def __init__(self, *, connection: Connection) -> None:
        """Keep the synchronous connection for SQLAlchemy's inspection callback."""
        self.connection = connection
        self.active = False
        self.closed = False
        self.run_sync = AsyncMock(side_effect=self._run_sync)

    async def __aenter__(self) -> Self:
        """Mark the connection active during the startup inspection."""
        self.active = True
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Record connection cleanup even when migration validation fails."""
        self.active = False
        self.closed = True

    async def _run_sync(self, callback: Callable[[Connection], None]) -> None:
        """Run the actual schema inspector while the connection scope is active."""
        assert self.active
        callback(self.connection)


StartupSchemaFixture: TypeAlias = tuple[
    OfflineConnection,
    Connection,
    MetaData,
    list[str],
]


# ==============================================
# DATABASE FIXTURE
# ==============================================


@pytest.fixture
def installed_schema(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[StartupSchemaFixture]:
    """Install a local schema, then record every SQL statement issued at startup."""
    options: dict[str, bool] = getattr(request, "param", {})
    required_metadata = schema_metadata()
    installed_metadata = schema_metadata(**options)
    engine = create_engine("sqlite+pysqlite:///:memory:")
    installed_metadata.create_all(engine)
    statements: list[str] = []

    def record_statement(
        connection: Connection,
        cursor: object,
        statement: str,
        parameters: object,
        context: object,
        executemany: bool,
    ) -> None:
        """Record actual SQL so startup cannot hide an automatic schema mutation."""
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", record_statement)
    monkeypatch.setattr(database, "Base", SimpleNamespace(metadata=required_metadata))
    # These offline SQLite tests exercise the primary schema-inspection path.
    # Development's Neon identity gate has separate nonconnecting unit coverage.
    monkeypatch.setattr(
        database,
        "_DATABASE_CONFIGURATION",
        replace(database._DATABASE_CONFIGURATION, target="primary"),
    )
    try:
        with engine.connect() as connection:
            adapter = OfflineConnection(connection=connection)
            engine_facade = MagicMock()
            engine_facade.connect.return_value = adapter
            engine_facade.begin.return_value = adapter
            monkeypatch.setattr(database, "engine", engine_facade)
            yield adapter, connection, required_metadata, statements
    finally:
        engine.dispose()


# ==============================================
# EXPLICIT MIGRATION REQUIREMENT
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "installed_schema",
    [
        {"include_receipts": False},
        {"include_owner_subject": False},
    ],
    indirect=True,
    ids=["missing-table", "missing-column"],
)
async def test_startup_rejects_missing_schema_objects_without_repairing_them(
    installed_schema: StartupSchemaFixture,
) -> None:
    """Missing migration objects remain missing after startup fails closed."""
    adapter, connection, _required_metadata, statements = installed_schema
    before = {
        table_name: tuple(
            column["name"] for column in inspect(connection).get_columns(table_name)
        )
        for table_name in inspect(connection).get_table_names()
    }

    with pytest.raises(RuntimeError, match="explicit Alembic migration"):
        await database.init_db()

    after = {
        table_name: tuple(
            column["name"] for column in inspect(connection).get_columns(table_name)
        )
        for table_name in inspect(connection).get_table_names()
    }
    assert after == before
    assert adapter.closed and not adapter.active
    assert not any(
        statement.lstrip().upper().startswith(("CREATE", "ALTER", "DROP"))
        for statement in statements
    )


@pytest.mark.asyncio
async def test_startup_accepts_all_required_tables_and_columns_without_ddl(
    installed_schema: StartupSchemaFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A complete installed schema is inspected while metadata creation stays unused."""
    adapter, connection, required_metadata, statements = installed_schema
    create_all = MagicMock(side_effect=AssertionError("Startup cannot create schema"))
    monkeypatch.setattr(required_metadata, "create_all", create_all)

    await database.init_db()

    assert adapter.closed and not adapter.active
    assert set(inspect(connection).get_table_names()) == {
        "owners",
        "payments",
        "manual_payment_receipts",
    }
    create_all.assert_not_called()
    assert statements
    assert not any(
        statement.lstrip().upper().startswith(("CREATE", "ALTER", "DROP"))
        for statement in statements
    )
