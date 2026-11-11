# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# VERSIONED ADMINISTRATIVE AUDIT READ CONTRACTS
# Keep historical log reads usable while refusing incomplete O1 or unknown schemas.
# ==============================================

"""Exercise real local schema inspection without PostgreSQL or external calls."""

from __future__ import annotations

# isort: split
# ==============================================
# OFFLINE SCHEMA AND QUERY DEPENDENCIES
# Compile the real mapper and inspect SQLite tables without weakening application startup.
# ==============================================

from collections.abc import Iterator
from types import SimpleNamespace
from typing import TypeAlias

import pytest
from sqlalchemy import (
    Column,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    event,
    inspect,
    select,
)
from sqlalchemy.engine import Connection

from app.core import database
from app.core.schema_compatibility import historical_schema_compatibility
from app.models.admin_log import AdminLog

AuditSchema: TypeAlias = tuple[Connection, list[str]]
ACTOR_COLUMNS = {"actor_admin_id", "actor_name", "actor_subject"}

# ==============================================
# REAL DISPOSABLE SCHEMA INSPECTION
# Revision and retained columns vary independently; capture every validation statement.
# ==============================================


@pytest.fixture
def audit_schema(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> Iterator[AuditSchema]:
    """Build a tiny installed schema and compare it to the shared mapped contract."""
    revisions, with_actors, missing_shared = request.param
    required = MetaData()
    Table(
        "admin_logs",
        required,
        Column("id", Integer, primary_key=True),
        Column("action", String(50), nullable=False),
    )
    installed = MetaData()
    columns = [Column("id", Integer, primary_key=True)]
    if not missing_shared:
        columns.append(Column("action", String(50), nullable=False))
    if with_actors:
        columns.extend(Column(name, String(255)) for name in sorted(ACTOR_COLUMNS))
    Table("admin_logs", installed, *columns)
    if revisions is not None:
        Table("alembic_version", installed, Column("version_num", String(32)))
    engine = create_engine("sqlite+pysqlite:///:memory:")
    installed.create_all(engine)
    statements: list[str] = []

    # ==============================================
    # OBSERVE VALIDATION SQL ONLY
    # Fixture DDL occurs before observation; the application checker must stay read-only.
    # ==============================================

    def record(
        connection: Connection,
        cursor: object,
        statement: str,
        parameters: object,
        context: object,
        executemany: bool,
    ) -> None:
        """Record statements without collecting bound data or credentials."""
        statements.append(statement)

    monkeypatch.setattr(database, "Base", SimpleNamespace(metadata=required))
    try:
        with engine.begin() as connection:
            if revisions:
                connection.execute(
                    installed.tables["alembic_version"].insert(),
                    [{"version_num": revision} for revision in revisions],
                )
            event.listen(engine, "before_cursor_execute", record)
            yield connection, statements
    finally:
        engine.dispose()


# ==============================================
# EXACT HISTORICAL READ ADMISSION
# Only reviewed pre-O1 revision sets may lack the newer retained actor snapshot.
# ==============================================


@pytest.mark.parametrize(
    "audit_schema",
    [
        (["s1a20261028"], False, False),
        (["s1b20261028"], False, False),
        (["s1b20261028", "e1b92b200001"], False, False),
        (["d1a20261102"], False, False),
        (["d1b20261103"], False, False),
        (["d1c20261104"], False, False),
        (["d1d20261105"], False, False),
        (["o520261111"], True, False),
    ],
    indirect=True,
)
def test_exact_revision_and_complete_schema_are_readable(
    audit_schema: AuditSchema,
) -> None:
    """Admit historical shared fields and require actual retained columns on O5."""
    connection, statements = audit_schema
    database._validate_schema(connection)
    assert not any(
        statement.lstrip().upper().startswith(("CREATE", "ALTER", "DROP", "UPDATE"))
        for statement in statements
    )


# ==============================================
# INCOMPLETE OR AMBIGUOUS SCHEMA REFUSAL
# Neither a revision label nor a test environment may hide required missing columns.
# ==============================================


@pytest.mark.parametrize(
    "audit_schema",
    [
        (["o120261108"], False, False),
        (["o520261111"], False, False),
        (["unknown"], False, False),
        (["s1a20261028", "unknown"], False, False),
        ([], False, False),
        (None, False, False),
        (["s1a20261028"], False, True),
    ],
    indirect=True,
)
def test_missing_required_fields_fail_without_schema_repair(
    audit_schema: AuditSchema,
) -> None:
    """Current audit omissions and historical shared-column omissions stay fatal."""
    connection, statements = audit_schema
    before = {item["name"] for item in inspect(connection).get_columns("admin_logs")}
    with pytest.raises(RuntimeError, match="explicit Alembic migration"):
        database._validate_schema(connection)
    assert before == {
        item["name"] for item in inspect(connection).get_columns("admin_logs")
    }
    assert not any(
        statement.lstrip().upper().startswith(("CREATE", "ALTER", "DROP", "UPDATE"))
        for statement in statements
    )


# ==============================================
# SHARED ORM QUERY COMPATIBILITY
# Legacy entity reads and trigger-backed inserts must not mention O1-only fields.
# ==============================================


def test_shared_log_mapping_excludes_retained_projection_columns() -> None:
    """Preserve one physical log table without inventing snapshot values on S1a."""
    assert not ACTOR_COLUMNS & set(AdminLog.__table__.columns.keys())
    compiled = str(select(AdminLog))
    assert all(name not in compiled for name in ACTOR_COLUMNS)


# ==============================================
# LATE FEATURE IMPORTS DO NOT CHANGE HISTORICAL PROFILES
# Require both documentary tables on O5 while admitting only exact earlier revisions without them.
# ==============================================


@pytest.mark.parametrize(
    "audit_schema,accepted",
    [
        ((["s1a20261028"], False, False), True),
        ((["d1d20261105"], False, False), True),
        ((["o420261108"], True, False), True),
        ((["o520261111"], True, False), False),
        ((["unknown"], True, False), False),
    ],
    indirect=["audit_schema"],
)
def test_later_document_models_do_not_redefine_old_schema(
    audit_schema: AuditSchema, accepted: bool
) -> None:
    """Use loaded future metadata without creating or pretending to install its tables."""
    connection, statements = audit_schema
    for name in ("subscription_documents", "subscription_document_events"):
        Table(name, database.Base.metadata, Column("id", Integer, primary_key=True))
    if accepted:
        database._validate_schema(connection)
    else:
        with pytest.raises(RuntimeError, match="explicit Alembic migration"):
            database._validate_schema(connection)
    assert not any(
        statement.lstrip().upper().startswith(("CREATE", "ALTER", "DROP", "UPDATE"))
        for statement in statements
    )


# ==============================================
# EVERY RETAINED ACTOR FIELD REMAINS MANDATORY ON O5
# A partially installed audit migration must fail even when the other snapshot fields exist.
# ==============================================


@pytest.mark.parametrize("audit_schema", [(["o520261111"], True, False)], indirect=True)
@pytest.mark.parametrize("missing", sorted(ACTOR_COLUMNS))
def test_o5_rejects_each_missing_actor_field(
    audit_schema: AuditSchema, missing: str
) -> None:
    """Remove one synthetic fixture column before observing the read-only check."""
    connection, statements = audit_schema
    assert missing in ACTOR_COLUMNS
    connection.exec_driver_sql(f'ALTER TABLE admin_logs DROP COLUMN "{missing}"')
    statements.clear()
    with pytest.raises(RuntimeError, match="explicit Alembic migration"):
        database._validate_schema(connection)
    assert not any(
        statement.lstrip().upper().startswith(("CREATE", "ALTER", "DROP", "UPDATE"))
        for statement in statements
    )


# ==============================================
# ADDITIVE TABLE BOUNDARIES AND FAIL-CLOSED REVISION SETS
# Importing future feature models must not turn an older checked profile into a different schema.
# ==============================================


@pytest.mark.parametrize(
    "revisions,omitted,actor_required",
    [
        ({"s1a20261028"}, 10, False),
        ({"s1b20261028", "e1b92b200001"}, 10, False),
        ({"o120261108"}, 10, True),
        ({"o220261108"}, 10, True),
        ({"o320261108"}, 9, True),
        ({"o420261108"}, 2, True),
        ({"o520261111"}, 0, True),
        ({"unknown"}, 0, True),
        (set(), 0, True),
        ({"s1a20261028", "o520261111"}, 0, True),
    ],
)
def test_exact_additive_schema_boundaries(
    revisions: set[str], omitted: int, actor_required: bool
) -> None:
    """Keep every current requirement on unknown, absent or unreviewed multiple heads."""
    contract = historical_schema_compatibility(revisions=frozenset(revisions))
    assert len(contract.tables_not_yet_introduced) == omitted
    assert contract.retained_actor_required is actor_required
    assert not {"admin_logs", "payments", "subscriptions", "restaurants"} & (
        contract.tables_not_yet_introduced
    )
