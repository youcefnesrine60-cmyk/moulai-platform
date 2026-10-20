# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""E1 static safety contracts: real compilation, zero database or SQLite IO."""

from __future__ import annotations

import ast
import re
from io import StringIO
from typing import Literal
from unittest.mock import MagicMock

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from app.core.security.tenant_types import permission_ceiling
from app.models import Base
from app.models.tenant.schema import TENANT_METADATA
from migration_support.tenant_e1 import (
    EXPANSIONS,
    build_target_metadata,
    operation_metadata,
    upgrade_e1,
)
from migration_support.tenant_e1_schema import (
    ROLE_PERMISSIONS,
    TENANT_TABLE_NAMES,
)
from migration_support.tenant_e1_sql import (
    FUNCTION_DEFINITIONS,
    FUNCTION_SIGNATURES,
    TRIGGER_DEFINITIONS,
)
from scripts.review_tenant_e1 import (
    PROJECT_ROOT,
    REVISION_PATHS,
    load_revision,
    render_revision,
    revision_graph,
)

# ==============================================
# COMPILED SQL FIXTURE
# ==============================================


@pytest.fixture(scope="module")
def compiled_sql() -> dict[str, str]:
    """Generate strings only; importing env.py or creating an engine is unnecessary."""
    return {
        direction: render_revision(
            path=PROJECT_ROOT / REVISION_PATHS[0], direction=direction
        )
        for direction in ("upgrade", "downgrade")
    }


# ==============================================
# COMPLETE LEGACY METADATA PRESERVATION
# ==============================================


def test_target_preserves_full_legacy_tables_and_live_metadata() -> None:
    """Future metadata must neither shrink reference tables nor alter live mappers."""
    before = {
        name: tuple(table.c.keys()) for name, table in Base.metadata.tables.items()
    }
    metadata = build_target_metadata(legacy_metadata=Base.metadata)
    assert set(metadata.tables) == set(before) | set(TENANT_TABLE_NAMES)
    for name, columns in before.items():
        expected = set(columns) | {
            column for table, column in EXPANSIONS if table == name
        }
        assert set(metadata.tables[name].c.keys()) == expected
        assert metadata.tables[name] is not Base.metadata.tables[name]
    assert before == {
        name: tuple(table.c.keys()) for name, table in Base.metadata.tables.items()
    }
    assert "group_id" in metadata.tables["restaurants"].c
    assert "organization_id" not in Base.metadata.tables["restaurants"].c
    assert "auth_subject" in metadata.tables["owners"].c
    assert "auth_subject" in metadata.tables["admins"].c
    assert not any(t.info.get("external_reference") for t in metadata.tables.values())


# ==============================================
# PREREQUISITE DRIFT REFUSAL
# ==============================================


@pytest.mark.parametrize("missing", [table for table, _ in EXPANSIONS])
def test_missing_prerequisite_refuses_integration(missing: str) -> None:
    """An incomplete reference declaration cannot become the autogenerate target."""
    metadata = sa.MetaData()
    for name, _ in EXPANSIONS:
        if name != missing:
            sa.Table(name, metadata, sa.Column("id", sa.Integer(), primary_key=True))
    with pytest.raises(ValueError, match="prerequisite absent"):
        build_target_metadata(legacy_metadata=metadata)


# ==============================================
# FROZEN CONTRACT COMPATIBILITY
# ==============================================


@pytest.mark.parametrize("table_name", TENANT_TABLE_NAMES)
def test_frozen_contract_matches_b1_model(table_name: str) -> None:
    """Compare actual typed metadata while keeping migrations independent of B1 imports."""
    frozen = operation_metadata().tables[table_name]
    model = TENANT_METADATA.tables[table_name]
    dialect = postgresql.dialect(paramstyle="named")
    assert tuple(frozen.c.keys()) == tuple(model.c.keys())
    for column in model.c:
        other = frozen.c[column.name]
        assert other.type.compile(dialect=dialect) == column.type.compile(
            dialect=dialect
        )
        assert other.nullable == column.nullable
        assert other.primary_key == column.primary_key
        assert str(other.server_default.arg if other.server_default else None) == str(
            column.server_default.arg if column.server_default else None
        )
    model_checks = {
        str(c.sqltext) for c in model.constraints if isinstance(c, sa.CheckConstraint)
    }
    frozen_checks = {
        str(c.sqltext) for c in frozen.constraints if isinstance(c, sa.CheckConstraint)
    }
    assert frozen_checks == model_checks
    assert {
        tuple(c.columns.keys())
        for c in frozen.constraints
        if isinstance(c, sa.UniqueConstraint)
    } == {
        tuple(c.columns.keys())
        for c in model.constraints
        if isinstance(c, sa.UniqueConstraint)
    }
    assert {
        (
            tuple(fk.parent.name for fk in c.elements),
            tuple(fk.target_fullname for fk in c.elements),
        )
        for c in frozen.foreign_key_constraints
    } == {
        (
            tuple(fk.parent.name for fk in c.elements),
            tuple(fk.target_fullname for fk in c.elements),
        )
        for c in model.foreign_key_constraints
    }


# ==============================================
# FK TARGET AND KEY RESOLUTION
# ==============================================


def test_all_foreign_keys_resolve_to_qualifying_keys() -> None:
    """Resolve every new FK against full targets, including company-qualified keys."""
    metadata = build_target_metadata(legacy_metadata=Base.metadata)
    for table_name in set(TENANT_TABLE_NAMES) | {name for name, _ in EXPANSIONS}:
        for constraint in metadata.tables[table_name].foreign_key_constraints:
            if not str(constraint.name).startswith("fk_"):
                continue
            referenced = [element.column for element in constraint.elements]
            table = referenced[0].table
            keys = {
                tuple(c.columns.keys())
                for c in table.constraints
                if isinstance(c, (sa.PrimaryKeyConstraint, sa.UniqueConstraint))
            }
            assert tuple(column.name for column in referenced) in keys
            assert constraint.ondelete == "RESTRICT"
    for name in TENANT_TABLE_NAMES:
        assert str(
            CreateTable(metadata.tables[name]).compile(dialect=postgresql.dialect())
        )


# ==============================================
# NULLABLE EXPANSION BOUNDARIES
# ==============================================


@pytest.mark.parametrize("table_name,column_name", EXPANSIONS)
def test_existing_extensions_are_nullable_only(
    table_name: str, column_name: str, compiled_sql: dict[str, str]
) -> None:
    """Legacy data needs no invented company or identity to survive E1."""
    table = build_target_metadata(legacy_metadata=Base.metadata).tables[table_name]
    column = table.c[column_name]
    assert column.nullable and column.server_default is None
    assert (
        f"ALTER TABLE {table_name} ADD COLUMN {column_name} INTEGER;"
        in compiled_sql["upgrade"]
    )
    if table_name != "restaurant_branches":
        assert any(column_name in fk.columns for fk in table.foreign_key_constraints)


# ==============================================
# DISTINCT ALEMBIC HISTORIES
# ==============================================


@pytest.mark.parametrize(
    "directory,head,parent,count",
    [
        ("alembic", "e1a92b200001", "c413b7918a20", 17),
        ("alembic_test", "e1b92b200001", "dce91870b4a2", 4),
    ],
)
def test_histories_have_distinct_reviewed_parents(
    directory: str, head: str, parent: str, count: int
) -> None:
    """Never graft the main history onto a differently versioned test baseline."""
    graph = revision_graph(directory=PROJECT_ROOT / directory / "versions")
    assert len(graph) == count
    assert set(graph) - set(graph.values()) == {head}
    assert graph[head] == parent


# ==============================================
# IDENTICAL E1 BODIES ACROSS HISTORIES
# ==============================================


@pytest.mark.parametrize("direction", ["upgrade", "downgrade"])
def test_two_histories_render_identical_contract(
    direction: Literal["upgrade", "downgrade"],
) -> None:
    """The wrappers differ in version ancestry, not schema or lifecycle behavior."""
    first, second = [load_revision(path=PROJECT_ROOT / path) for path in REVISION_PATHS]
    assert first.revision != second.revision
    assert first.down_revision != second.down_revision
    assert render_revision(
        path=PROJECT_ROOT / REVISION_PATHS[0], direction=direction
    ) == render_revision(path=PROJECT_ROOT / REVISION_PATHS[1], direction=direction)


# ==============================================
# UPGRADE SCOPE AND CREATION ORDER
# ==============================================


def test_upgrade_creates_only_nine_owned_tables(compiled_sql: dict[str, str]) -> None:
    """Partial restaurants/admins declarations must never become CREATE TABLE ops."""
    sql = compiled_sql["upgrade"]
    assert re.findall(r"CREATE TABLE (\w+) \(", sql) == list(TENANT_TABLE_NAMES)
    additions = re.findall(r"ALTER TABLE (\w+) ADD COLUMN (\w+) INTEGER;", sql)
    assert additions == list(EXPANSIONS)
    assert not re.search(
        r"\b(DROP TABLE|DELETE FROM|TRUNCATE|ALTER COLUMN)\b",
        sql.split("CREATE FUNCTION", 1)[0],
    )
    assert "IF NOT EXISTS" not in sql
    assert sql.index("CREATE TABLE organization_memberships") < sql.index(
        "ALTER TABLE restaurants ADD"
    )
    assert sql.index(
        "ALTER TABLE restaurants ADD CONSTRAINT uq_restaurants_org_id"
    ) < sql.index("CREATE TABLE membership_restaurant_grants")
    assert "LIKE 'https://%'" in sql and "https://%%" not in sql
    assert sql.startswith("BEGIN;") and sql.rstrip().endswith("COMMIT;")


# ==============================================
# INITIAL POLICY ROWS
# ==============================================


@pytest.mark.parametrize(
    "role,expected_count", [("owner", 26), ("manager", 17), ("employee", 6)]
)
def test_policy_rows_are_explicit_and_fulfillment_is_absent(
    role: str, expected_count: int, compiled_sql: dict[str, str]
) -> None:
    """A realm role or permission catalogue ceiling never provisions authority."""
    permissions = ROLE_PERMISSIONS[role]
    assert len(permissions) == expected_count
    assert set(permissions) == permission_ceiling(role_code=role) - {
        "tenant.orders.fulfill"
    }
    inserts = [
        line
        for line in compiled_sql["upgrade"].splitlines()
        if line.startswith("INSERT INTO")
    ]
    assert not any("tenant.orders.fulfill" in line for line in inserts)
    assert set(re.findall(r"INSERT INTO (\w+)", "\n".join(inserts))) == {
        "tenant_roles",
        "tenant_role_permissions",
    }
    assert len(inserts) == 52


# ==============================================
# LEGACY FINANCE AND PLATFORM RBAC PRESERVATION
# ==============================================


@pytest.mark.parametrize(
    "table_name",
    [
        "payments",
        "subscriptions",
        "manual_payment_receipts",
        "manual_payment_audit",
        "roles",
        "permissions",
        "role_permissions",
        "order_payments",
    ],
)
def test_finance_and_platform_authority_are_outside_e1(
    table_name: str, compiled_sql: dict[str, str]
) -> None:
    """Reject any DDL/DML or grant targeting financial/platform policy tables."""
    for sql in compiled_sql.values():
        assert not re.search(
            rf"(?:ALTER TABLE|DROP TABLE|CREATE TABLE|INSERT INTO|UPDATE|DELETE FROM|ON TABLE) (?:public\.)?{table_name}\b",
            sql,
        )
    assert not re.search(r"\bowner_id\b", compiled_sql["upgrade"])
    assert "auth_subject" not in compiled_sql["upgrade"]
    assert "DROP COLUMN group_id" not in compiled_sql["downgrade"]


# ==============================================
# CONSTRAINT NAMES AND INDEX COLLISIONS
# ==============================================


def test_names_are_explicit_bounded_and_do_not_shadow_legacy_indexes() -> None:
    """PostgreSQL must not truncate names or collide with historical key indexes."""
    metadata = operation_metadata()
    constraints = [
        c
        for t in metadata.tables.values()
        for c in t.constraints
        if t.name in TENANT_TABLE_NAMES or not isinstance(c, sa.PrimaryKeyConstraint)
    ]
    names = [str(c.name) for c in constraints]
    names += [str(i.name) for t in metadata.tables.values() for i in t.indexes]
    names += [name for _, name, _ in TRIGGER_DEFINITIONS]
    names += [signature.split("(")[0] for signature in FUNCTION_SIGNATURES]
    assert all(name != "None" and len(name.encode("utf-8")) <= 63 for name in names)
    assert len(names) == len(set(names))
    legacy_indexes = {
        str(item.name)
        for t in Base.metadata.tables.values()
        for item in (*t.indexes, *t.constraints)
        if isinstance(item, (sa.Index, sa.PrimaryKeyConstraint, sa.UniqueConstraint))
        and item.name
    }
    assert not set(names) & legacy_indexes


# ==============================================
# NOT VALID SCOPE
# ==============================================


def test_only_six_legacy_foreign_keys_are_not_valid(
    compiled_sql: dict[str, str],
) -> None:
    """Existing nullable references are staged; new empty-table FKs remain checked."""
    lines = [
        line for line in compiled_sql["upgrade"].splitlines() if "NOT VALID" in line
    ]
    assert len(lines) == 6
    assert all("FOREIGN KEY" in line and "ON DELETE RESTRICT" in line for line in lines)
    assert not any("UNIQUE" in line for line in lines)


# ==============================================
# LAST OWNER SERIALIZATION CONTRACT
# ==============================================


def test_deferred_owner_check_has_early_revision_write_serialization() -> None:
    """Deferral alone does not prevent write skew; both company and identity are written."""
    membership_guard = FUNCTION_DEFINITIONS[3]
    assert "UPDATE public.identities SET revision = revision + 1" in membership_guard
    assert "UPDATE public.organizations SET revision = revision + 1" in membership_guard
    assert membership_guard.index("UPDATE public.identities") < membership_guard.index(
        "UPDATE public.organizations"
    )
    assert "ORDER BY organization_id" in FUNCTION_DEFINITIONS[4]
    assert (
        "UPDATE public.organizations SET revision = revision + 1"
        in FUNCTION_DEFINITIONS[4]
    )
    owner_check = FUNCTION_DEFINITIONS[5]
    assert owner_check.index("FOR UPDATE;") < owner_check.index("IF company_state")
    for fragment in (
        "m.role_code = 'owner'",
        "m.status = 'active'",
        "i.status = 'active'",
        "m.accepted_at IS NOT NULL",
        "m.activated_at IS NOT NULL",
    ):
        assert fragment in owner_check
    deferred = [sql for _, _, sql in TRIGGER_DEFINITIONS if "CONSTRAINT TRIGGER" in sql]
    assert len(deferred) == 2
    assert all("DEFERRABLE INITIALLY DEFERRED" in sql for sql in deferred)


# ==============================================
# CLOSED GOVERNANCE AND APPEND-ONLY HISTORY
# ==============================================


def test_unreleased_governance_is_fenced_after_policy_provisioning(
    compiled_sql: dict[str, str],
) -> None:
    """No acceptance/sealing workflow is invented to make the tables appear released."""
    sql = compiled_sql["upgrade"]
    assert sql.index("INSERT INTO tenant_role_permissions") < sql.index(
        "CREATE TRIGGER tr_e1_tenant_roles_closed"
    )
    fenced = {
        table for table, name, _ in TRIGGER_DEFINITIONS if name.endswith("_closed")
    }
    assert fenced == {
        "tenant_roles",
        "tenant_role_permissions",
        "membership_change_proposals",
        "membership_proposal_restaurants",
    }
    assert "BEFORE UPDATE OR DELETE ON public.tenant_audit_events" in sql
    assert sql.count("BEFORE TRUNCATE") == 9
    assert sql.count("REVOKE ALL ON TABLE") == 9
    assert "SECURITY DEFINER" not in sql
    assert "GRANT " not in sql


# ==============================================
# DEPENDENCY-SAFE GUARDED DOWNGRADE
# ==============================================


def test_downgrade_refuses_data_and_policy_drift_before_dropping(
    compiled_sql: dict[str, str],
) -> None:
    """An empty-only rollback must lock first and must never force-drop retained history."""
    sql = compiled_sql["downgrade"]
    assert sql.index("LOCK TABLE") < sql.index("DO $e1$") < sql.index("DROP TRIGGER")
    assert "IN ACCESS EXCLUSIVE MODE" in sql
    assert "ck_e1_empty_downgrade" in sql
    assert "EXCEPT VALUES" in sql
    assert not re.search(r"\bCASCADE\b|\bTRUNCATE\b|DELETE FROM", sql)
    for name in TENANT_TABLE_NAMES:
        assert (
            f"SELECT 1 FROM public.{name}" in sql or f"FROM public.{name} EXCEPT" in sql
        )
    assert set(re.findall(r"DROP TABLE (\w+);", sql)) == set(TENANT_TABLE_NAMES)
    assert set(re.findall(r"ALTER TABLE (\w+) DROP COLUMN (\w+);", sql)) == set(
        EXPANSIONS
    )
    assert sql.index("DROP TABLE membership_proposal_restaurants") < sql.index(
        "DROP TABLE membership_change_proposals"
    )
    assert sql.index("DROP TABLE membership_restaurant_grants") < sql.index(
        "DROP TABLE organization_memberships"
    )
    assert sql.index("DROP COLUMN identity_id") < sql.index("DROP TABLE identities")


# ==============================================
# DIALECT AND TRANSACTION GUARD
# ==============================================


@pytest.mark.parametrize(
    "dialect,transactional", [("sqlite", True), ("postgresql", False)]
)
def test_non_postgresql_or_nontransactional_context_is_rejected(
    dialect: str, transactional: bool
) -> None:
    """Static and later execution entry points share fail-closed dialect checks."""
    output = StringIO()
    context = MigrationContext.configure(
        dialect_name=dialect,
        opts={
            "as_sql": True,
            "output_buffer": output,
            "transactional_ddl": transactional,
        },
    )
    with pytest.raises(RuntimeError, match="PostgreSQL transactional DDL"):
        upgrade_e1(operations=Operations(context))
    assert output.getvalue() == ""


# ==============================================
# EXECUTION TRANSACTION REFUSAL WITHOUT A DATABASE
# ==============================================


@pytest.mark.parametrize("state", ["absent", "inactive", "autocommit"])
def test_execution_context_requires_a_real_transaction_boundary(state: str) -> None:
    """An eventual caller cannot silently apply E1 with autocommitted DDL."""
    operations = MagicMock(spec=Operations)
    context = operations.get_context.return_value
    context.dialect.name = "postgresql"
    context.impl.transactional_ddl = True
    context.as_sql = False
    connection = operations.get_bind.return_value
    if state == "absent":
        operations.get_bind.return_value = None
    else:
        connection.in_transaction.return_value = state != "inactive"
        connection.get_execution_options.return_value = {
            "isolation_level": (
                "AUTOCOMMIT" if state == "autocommit" else "READ COMMITTED"
            )
        }
    with pytest.raises(RuntimeError, match="active non-autocommit transaction"):
        upgrade_e1(operations=operations)
    operations.execute.assert_not_called()


# ==============================================
# MIGRATION IMPORT BOUNDARY
# ==============================================


def test_frozen_migration_modules_do_not_import_application_or_create_engines() -> None:
    """Later model/config changes must not silently rewrite a historical migration."""
    paths = list((PROJECT_ROOT / "migration_support").glob("*.py"))
    paths += [PROJECT_ROOT / path for path in REVISION_PATHS]
    for path in paths:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith("app.")
            if isinstance(node, ast.Call):
                name = node.func.attr if isinstance(node.func, ast.Attribute) else ""
                assert name not in {
                    "connect",
                    "create_engine",
                    "create_async_engine",
                    "create_all",
                    "drop_all",
                }
        assert not re.search(r"\bTODO\b|\bTBD\b|NotImplementedError", source)


# ==============================================
# ENVIRONMENT INTEGRATION SCOPE
# ==============================================


def test_alembic_environments_only_switch_to_complete_copied_metadata() -> None:
    """Both existing isolation/connection entry points remain present and unexecuted."""
    for directory in ("alembic", "alembic_test"):
        source = (PROJECT_ROOT / directory / "env.py").read_text(encoding="utf-8")
        assert (
            "target_metadata = build_target_metadata(legacy_metadata=Base.metadata)"
            in source
        )
        assert "TENANT_METADATA" not in source
    test_source = (PROJECT_ROOT / "alembic_test/env.py").read_text(encoding="utf-8")
    assert "read_test_database_identity(" in test_source
    assert "validated_test_database_url(" in test_source
    assert "validate_test_branch_configuration(" in test_source
