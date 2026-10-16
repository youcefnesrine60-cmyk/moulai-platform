# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Rehearse the exact pending production revision on the approved test endpoint.

Each scenario runs in an outer PostgreSQL transaction that is always rolled back.
It preserves the dedicated test migration history and verifies public-table
rows, column/constraint/index definitions, and captured sequence state after
rollback. Views, routines, triggers, ACLs, and other metadata are outside that
snapshot's scope. No production URL
is used to create an engine. Run alone, without another test runner or developer
writing to the test database. Reports contain no row data, identities, or URLs.
"""

from __future__ import annotations

# ==============================================
# IMPORTS AND REHEARSAL CONTRACT
# ==============================================

import argparse
import asyncio
import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from traceback import extract_tb
from typing import (
    Any,
    Literal,
    TypeAlias,
)

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import (
    inspect,
    text,
)
from sqlalchemy.engine import Connection
from sqlalchemy.exc import (
    DBAPIError,
    IntegrityError,
)
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings
from app.core.logger import logger
from app.core.test_database import (
    UnsafeTestDatabaseError,
    isolated_connection_arguments,
    read_test_database_identity,
    validate_test_branch_configuration,
    validated_test_database_url,
)

Scenario: TypeAlias = Literal["fresh", "adoption", "drift"]
Report: TypeAlias = dict[str, Any]
TEST_HEAD = "dce91870b4a2"
PREDECESSOR = "a91e7c2b4d10"
TARGET = "c413b7918a20"
LOCK_ID = 636052368236129
FIXTURE_ID = -1984620000
FIXTURE_LAST_ID = FIXTURE_ID + 100
FIXTURE_ROLE_CODE = "isolated_rehearsal_custom"
FIXTURE_PERMISSION_CODE = "isolated_rehearsal.nonfinancial.read"
FIXTURE_PLAN_CODE = "isolated_rehearsal_plan"
FIXTURE_OWNER_SUBJECT = "test-only:migration-rehearsal:owner"
SNAPSHOT_SCOPE = (
    "public_table_rows",
    "public_column_definitions",
    "public_constraint_definitions_and_validation",
    "public_index_definitions",
    "public_sequence_last_value_is_called_increment",
    "alembic_version",
)


# ==============================================
# SAFE FAILURE AND DATABASE SNAPSHOTS
# ==============================================


class RehearsalError(RuntimeError):
    """Carry a stable failure code without private database values."""


@dataclass(frozen=True)
class DatabaseSnapshot:
    """Hold private hashes of the measured metadata and sequence positions.

    This comparison excludes views, routines, triggers, ACLs, and unmeasured
    sequence options. Hashes and row data remain in memory and are not reported.
    """

    rows: dict[str, tuple[int, str]]
    schema_hash: str
    sequences: dict[str, tuple[int, bool, int]]
    revision: str


def _quoted(connection: Connection, name: str) -> str:
    """Quote a reflected identifier through the PostgreSQL dialect."""
    return connection.dialect.identifier_preparer.quote_identifier(name)


def _rows(
    connection: Connection, table: str, *, exclude: tuple[str, ...] = ()
) -> tuple[int, str]:
    """Hash canonical ordered rows without logging or returning their content."""
    expression = "to_jsonb(t)"
    parameters: dict[str, Any] = {}
    for index, column in enumerate(exclude):
        expression += f" - CAST(:excluded_{index} AS text)"
        parameters[f"excluded_{index}"] = column
    sql = f"SELECT ({expression})::text FROM public.{_quoted(connection, table)} t ORDER BY ({expression})::text"
    digest = hashlib.sha256()
    count = 0
    for row in connection.execute(text(sql), parameters).scalars():
        digest.update(row.encode("utf-8") + b"\n")
        count += 1
    return count, digest.hexdigest()


def _snapshot(connection: Connection) -> DatabaseSnapshot:
    """Capture public rows, columns/constraints/indexes, and sequence positions."""
    tables = inspect(connection).get_table_names(schema="public")
    schema: dict[str, list[tuple[Any, ...]]] = {}
    queries = {
        "columns": "SELECT table_name, column_name, ordinal_position, data_type, udt_name, is_nullable, column_default, character_maximum_length, numeric_precision, numeric_scale FROM information_schema.columns WHERE table_schema='public' ORDER BY table_name, ordinal_position",
        "constraints": "SELECT c.conrelid::regclass::text, c.conname, pg_get_constraintdef(c.oid), c.convalidated, c.condeferrable, c.condeferred FROM pg_constraint c JOIN pg_namespace n ON n.oid=c.connamespace WHERE n.nspname='public' ORDER BY 1,2",
        "indexes": "SELECT tablename, indexname, indexdef FROM pg_indexes WHERE schemaname='public' ORDER BY 1,2",
    }
    for kind, sql in queries.items():
        schema[kind] = [tuple(row) for row in connection.execute(text(sql))]
    sequences: dict[str, tuple[int, bool, int]] = {}
    for name, increment in connection.execute(
        text(
            "SELECT c.relname, s.seqincrement FROM pg_sequence s JOIN pg_class c ON c.oid=s.seqrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' ORDER BY c.relname"
        )
    ):
        value, called = connection.execute(
            text(
                f"SELECT last_value, is_called FROM public.{_quoted(connection, name)}"
            )
        ).one()
        sequences[name] = (int(value), bool(called), int(increment))
    return DatabaseSnapshot(
        rows={table: _rows(connection, table) for table in sorted(tables)},
        schema_hash=hashlib.sha256(
            json.dumps(schema, sort_keys=True, default=str).encode()
        ).hexdigest(),
        sequences=sequences,
        revision=connection.execute(
            text("SELECT version_num FROM public.alembic_version")
        ).scalar_one(),
    )


# ==============================================
# PRIVATE ALEMBIC CONNECTION AND FIXTURE PREDECESSOR
# ==============================================


def _configuration(connection: Connection) -> Config:
    """Use the real production graph exclusively through a guarded connection."""
    if (
        connection.execute(text("SELECT current_database()")).scalar_one()
        != "neondb_test"
    ):
        raise RehearsalError("unexpected_database")
    configuration = Config()
    configuration.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
    configuration.set_main_option("path_separator", "os")
    configuration.attributes["connection"] = connection
    revision = ScriptDirectory.from_config(configuration).get_revision(TARGET)
    if revision is None or revision.down_revision != PREDECESSOR:
        raise RehearsalError("unexpected_production_revision_chain")
    return configuration


def _reserve_fixture_identifiers(connection: Connection) -> None:
    """Reject every fixture ID and unique-key collision before staging any DDL."""
    tables = (
        "owners",
        "restaurants",
        "payments",
        "admins",
        "roles",
        "permissions",
        "subscription_plans",
        "subscriptions",
        "manual_payment_receipts",
        "manual_payment_audit",
    )
    for table in tables:
        if connection.execute(
            text(
                f"SELECT EXISTS(SELECT 1 FROM public.{_quoted(connection, table)} "
                "WHERE id BETWEEN :first AND :last)"
            ),
            {"first": FIXTURE_ID, "last": FIXTURE_LAST_ID},
        ).scalar_one():
            raise RehearsalError("fixture_identifier_collision")
    for table in ("owners", "admins"):
        if connection.execute(
            text(
                f"SELECT EXISTS(SELECT 1 FROM public.{_quoted(connection, table)} "
                "WHERE chat_id BETWEEN :first AND :last)"
            ),
            {"first": FIXTURE_ID, "last": FIXTURE_LAST_ID},
        ).scalar_one():
            raise RehearsalError("fixture_identifier_collision")
    if connection.execute(
        text(
            "SELECT EXISTS(SELECT 1 FROM public.roles WHERE code=:role) "
            "OR EXISTS(SELECT 1 FROM public.permissions WHERE code=:permission) "
            "OR EXISTS(SELECT 1 FROM public.subscription_plans WHERE code=:plan) "
            "OR EXISTS(SELECT 1 FROM public.owners WHERE auth_subject=:subject) "
            "OR EXISTS(SELECT 1 FROM public.manual_payment_receipts "
            "WHERE transaction_reference=:reference OR sha256=:hash)"
        ),
        {
            "role": FIXTURE_ROLE_CODE,
            "permission": FIXTURE_PERMISSION_CODE,
            "plan": FIXTURE_PLAN_CODE,
            "subject": FIXTURE_OWNER_SUBJECT,
            "reference": f"ISOLATED-REHEARSAL-{FIXTURE_ID}",
            "hash": hashlib.sha256(str(FIXTURE_ID).encode()).hexdigest(),
        },
    ).scalar_one():
        raise RehearsalError("fixture_unique_key_collision")


def _seed_authorization_fixtures(connection: Connection) -> None:
    """Create test administrators without binding subjects or changing real admins.

    Existing canonical roles are reused read-only. Missing roles and all custom
    fixtures receive explicit negative IDs without consuming any sequence.
    """
    for offset, code in enumerate(
        ("admin", "super_admin", "support", FIXTURE_ROLE_CODE)
    ):
        role_id = connection.execute(
            text("SELECT id FROM public.roles WHERE code=:code"), {"code": code}
        ).scalar_one_or_none()
        if role_id is None:
            role_id = FIXTURE_ID + offset
            connection.execute(
                text(
                    "INSERT INTO public.roles (id,code,name,is_active) "
                    "VALUES (:id,:code,'Isolated rehearsal role',:active)"
                ),
                {"id": role_id, "code": code, "active": code != FIXTURE_ROLE_CODE},
            )
        connection.execute(
            text(
                "INSERT INTO public.admins (id,chat_id,full_name,role,role_id,is_active) "
                "VALUES (:id,:chat_id,'Isolated rehearsal administrator',:code,:role,:active)"
            ),
            {
                "id": FIXTURE_ID + 10 + offset,
                "chat_id": FIXTURE_ID + 10 + offset,
                "code": code,
                "role": role_id,
                "active": code != "support",
            },
        )
    connection.execute(
        text(
            "INSERT INTO public.permissions (id,code,name) "
            "VALUES (:id,:code,'Isolated nonfinancial read permission')"
        ),
        {"id": FIXTURE_ID + 30, "code": FIXTURE_PERMISSION_CODE},
    )
    connection.execute(
        text(
            "INSERT INTO public.role_permissions (role_id,permission_id) "
            "SELECT id,:permission FROM public.roles WHERE code=:role"
        ),
        {"permission": FIXTURE_ID + 30, "role": FIXTURE_ROLE_CODE},
    )


def _prepare_predecessor(
    connection: Connection, *, scenario: Scenario
) -> tuple[int, str]:
    """Stage only the prior billing contract inside the rollback-only transaction.

    The shared test database already contains the equivalent dce test revision.
    We temporarily remove its added billing fields, retaining every other
    predecessor table. This is a rehearsal of the exact a91-to-c413 step, not a
    reconstruction or certification of every historical production migration.
    """
    _reserve_fixture_identifiers(connection)
    connection.execute(
        text(
            "ALTER TABLE public.payments DROP COLUMN payment_provider, DROP COLUMN currency"
        )
    )
    connection.execute(text("ALTER TABLE public.admins DROP COLUMN auth_subject"))
    if scenario == "fresh":
        connection.execute(text("DROP TABLE public.manual_payment_audit"))
        connection.execute(text("DROP TABLE public.manual_payment_receipts"))
        connection.execute(
            text(
                "DELETE FROM public.role_permissions WHERE permission_id IN (SELECT id FROM public.permissions WHERE code='payments.review')"
            )
        )
        connection.execute(
            text("DELETE FROM public.permissions WHERE code='payments.review'")
        )
    connection.execute(
        text("UPDATE public.alembic_version SET version_num=:revision"),
        {"revision": PREDECESSOR},
    )
    connection.execute(
        text(
            "INSERT INTO public.owners (id, chat_id, auth_subject, full_name, phone, registration_status) VALUES (:id, :chat_id, :subject, 'Isolated migration rehearsal', '0000000000', 'approved')"
        ),
        {"id": FIXTURE_ID, "chat_id": FIXTURE_ID, "subject": FIXTURE_OWNER_SUBJECT},
    )
    connection.execute(
        text(
            "INSERT INTO public.restaurants (id, owner_id, name, type, phone, wilaya, is_active) VALUES (:id, :id, 'Isolated migration rehearsal', 'restaurant', '0000000000', 'Isolated test', true)"
        ),
        {"id": FIXTURE_ID},
    )
    _seed_authorization_fixtures(connection)
    connection.execute(
        text(
            "INSERT INTO public.subscription_plans "
            "(id,code,name,base_price,plan_discount_percent,active) "
            "VALUES (:id,:code,'Isolated rehearsal plan',1500.25,0,false)"
        ),
        {"id": FIXTURE_ID + 40, "code": FIXTURE_PLAN_CODE},
    )
    connection.execute(
        text(
            "INSERT INTO public.subscriptions "
            "(id,owner_id,restaurant_id,plan_id,billing_cycle,amount,status) "
            "VALUES (:id,:owner,:owner,:plan,'monthly',1500.25,'pending')"
        ),
        {"id": FIXTURE_ID + 50, "owner": FIXTURE_ID, "plan": FIXTURE_ID + 40},
    )
    for offset, method in enumerate(("ccp", "baridimob", "card")):
        connection.execute(
            text(
                "INSERT INTO public.payments (id, owner_id, restaurant_id, subscription_id, payment_method, amount, status, paid_at) VALUES (:id, :owner, :owner, :subscription, :method, 1500.25, :status, :paid_at)"
            ),
            {
                "id": FIXTURE_ID + offset,
                "owner": FIXTURE_ID,
                "subscription": FIXTURE_ID + 50,
                "method": method,
                "status": "pending" if offset < 2 else "completed",
                "paid_at": None if offset < 2 else datetime(2026, 10, 1, 12),
            },
        )
    if scenario in {"adoption", "drift"}:
        _insert_receipt(connection, receipt_id=FIXTURE_ID, payment_id=FIXTURE_ID)
    if scenario == "drift":
        connection.execute(
            text(
                "ALTER TABLE public.manual_payment_audit ADD COLUMN unexpected_rehearsal_column text"
            )
        )
    return _rows(connection, "payments")


def _insert_receipt(
    connection: Connection, *, receipt_id: int, payment_id: int
) -> None:
    """Seed synthetic evidence using explicit IDs without consuming sequences."""
    connection.execute(
        text(
            "INSERT INTO public.manual_payment_receipts (id, payment_id, transaction_reference, sha256, media_type, content, review_status) VALUES (:id, :payment, :reference, :hash, 'application/pdf', :content, 'pending')"
        ),
        {
            "id": receipt_id,
            "payment": payment_id,
            "reference": f"ISOLATED-REHEARSAL-{receipt_id}",
            "hash": hashlib.sha256(str(receipt_id).encode()).hexdigest(),
            "content": b"%PDF-1.4\nIsolated test evidence",
        },
    )
    connection.execute(
        text(
            "INSERT INTO public.manual_payment_audit (id, payment_id, receipt_id, owner_id, action, details) VALUES (:id, :payment, :id, :owner, 'submitted', '{}')"
        ),
        {"id": receipt_id, "payment": payment_id, "owner": FIXTURE_ID},
    )


# ==============================================
# MIGRATION AND RELATIONAL INTEGRITY CHECKS
# ==============================================


def _expect_constraint_failure(
    connection: Connection,
    *,
    case: str,
    sql: str,
    parameters: dict[str, Any],
    sqlstate: str,
) -> None:
    """Verify a real PostgreSQL constraint without leaving an aborted transaction."""
    try:
        with connection.begin_nested():
            connection.execute(text(sql), parameters)
    except IntegrityError as error:
        actual_sqlstate = getattr(error.orig, "sqlstate", None)
        if actual_sqlstate != sqlstate:
            constraint = getattr(
                getattr(error.orig, "__cause__", None), "constraint_name", None
            )
            raise RehearsalError(
                f"unexpected_constraint_failure:case={case}:expected={sqlstate}:actual={actual_sqlstate}:constraint={constraint}"
            ) from None
        return
    except (DBAPIError, TimeoutError) as error:
        raise RehearsalError(
            f"constraint_check_failed:case={case}:type={type(error).__name__}"
        ) from None
    raise RehearsalError(f"required_database_constraint_not_enforced:case={case}")


def _verify_integrity(connection: Connection, *, configuration: Config) -> int:
    """Verify actual receipt contracts, FK enforcement, and global deduplication."""
    revision = ScriptDirectory.from_config(configuration).get_revision(TARGET)
    if revision is None:
        raise RehearsalError("missing_target_revision")
    for table in ("manual_payment_receipts", "manual_payment_audit"):
        revision.module._validate_manual_table(inspect(connection), table)
    # Independently inspect identity uniqueness without binding any fake subject.
    administrator_uniques = inspect(connection).get_unique_constraints(
        "admins", schema="public"
    )
    if not any(
        constraint["column_names"] == ["auth_subject"]
        for constraint in administrator_uniques
    ):
        raise RehearsalError("administrator_identity_unique_constraint_missing")
    receipt_sql = "INSERT INTO public.manual_payment_receipts (id,payment_id,transaction_reference,sha256,media_type,content,review_status) VALUES (:id,:payment,:reference,:hash,'application/pdf',:content,:status)"
    base: dict[str, Any] = {
        "id": FIXTURE_ID + 20,
        "payment": FIXTURE_ID + 1,
        "reference": "ISOLATED-SECOND-RECEIPT",
        "hash": "b" * 64,
        "content": b"%PDF-1.4",
        "status": "pending",
    }
    original_reference = f"ISOLATED-REHEARSAL-{FIXTURE_ID}"
    original_hash = hashlib.sha256(str(FIXTURE_ID).encode()).hexdigest()
    cases = (
        ("duplicate_payment", {"payment": FIXTURE_ID}, "23505"),
        ("duplicate_reference", {"reference": original_reference}, "23505"),
        ("duplicate_digest", {"hash": original_hash}, "23505"),
        ("missing_payment", {"payment": FIXTURE_ID + 99}, "23503"),
        ("invalid_review_status", {"status": "paid"}, "23514"),
        ("empty_receipt", {"content": b""}, "23514"),
    )
    for case, changes, sqlstate in cases:
        _expect_constraint_failure(
            connection,
            case=case,
            sql=receipt_sql,
            parameters=base | changes,
            sqlstate=sqlstate,
        )
    # Build the oversized value on PostgreSQL to exercise the same CHECK without
    # transferring a multi-megabyte synthetic parameter over the network.
    _expect_constraint_failure(
        connection,
        case="oversized_receipt",
        sql=receipt_sql.replace(":content", "CAST(repeat('x', 2097153) AS bytea)"),
        parameters={name: value for name, value in base.items() if name != "content"},
        sqlstate="23514",
    )
    server_version = connection.dialect.server_version_info
    if not server_version:
        raise RehearsalError("postgresql_server_version_unavailable")
    # PostgreSQL 18 distinguishes RESTRICT from ordinary missing-parent FK
    # errors. Earlier versions use 23503 for both; require the precise code.
    # See postgres/postgres REL_18_STABLE src/backend/utils/adt/ri_triggers.c.
    _expect_constraint_failure(
        connection,
        case="payment_with_receipt_delete",
        sql="DELETE FROM public.payments WHERE id=:id",
        parameters={"id": FIXTURE_ID},
        sqlstate="23001" if server_version >= (18,) else "23503",
    )
    _expect_constraint_failure(
        connection,
        case="missing_audit_receipt",
        sql="INSERT INTO public.manual_payment_audit (id,payment_id,receipt_id,owner_id,action,details) VALUES (:id,:payment,:receipt,:owner,'submitted','{}')",
        parameters={
            "id": FIXTURE_ID + 20,
            "payment": FIXTURE_ID,
            "receipt": FIXTURE_ID + 99,
            "owner": FIXTURE_ID,
        },
        sqlstate="23503",
    )
    # Check the server default with direct SQL, independently of ORM defaults.
    payment_sql = (
        "INSERT INTO public.payments "
        "(id,owner_id,restaurant_id,payment_method,amount,status) "
        "VALUES (:id,:owner,:owner,'card',1500.25,'pending') "
        "RETURNING currency,payment_provider"
    )
    savepoint = connection.begin_nested()
    try:
        currency, provider = connection.execute(
            text(payment_sql), {"id": FIXTURE_ID + 60, "owner": FIXTURE_ID}
        ).one()
        if currency != "DZD" or provider is not None:
            raise RehearsalError("new_payment_server_default_failed")
    finally:
        savepoint.rollback()
    _expect_constraint_failure(
        connection,
        case="null_payment_currency",
        sql=(
            "INSERT INTO public.payments "
            "(id,owner_id,restaurant_id,payment_method,amount,status,currency) "
            "VALUES (:id,:owner,:owner,'card',1500.25,'pending',NULL)"
        ),
        parameters={"id": FIXTURE_ID + 60, "owner": FIXTURE_ID},
        sqlstate="23502",
    )
    return len(cases) + 4


def _run_scenario(connection: Connection, *, scenario: Scenario) -> Report:
    """Execute one real Alembic upgrade and assertions inside the outer rollback."""
    configuration = _configuration(connection)
    prior_payments = _prepare_predecessor(connection, scenario=scenario)
    admins = _rows(connection, "admins")
    role_links = _rows(connection, "role_permissions")
    roles = _rows(connection, "roles")
    owners = _rows(connection, "owners")
    subscriptions = _rows(connection, "subscriptions")
    evidence = (
        {
            table: _rows(connection, table)
            for table in ("manual_payment_receipts", "manual_payment_audit")
        }
        if scenario != "fresh"
        else {}
    )
    if scenario == "drift":
        try:
            command.upgrade(configuration, TARGET)
        except RuntimeError as error:
            if not str(error).startswith("manual_payment_schema_drift:"):
                raise RehearsalError("unexpected_drift_failure") from None
        else:
            raise RehearsalError("schema_drift_was_accepted")
        if MigrationContext.configure(connection).get_current_heads() != (PREDECESSOR,):
            raise RehearsalError("drift_changed_revision")
        if {"payment_provider", "currency"}.intersection(
            column["name"] for column in inspect(connection).get_columns("payments")
        ):
            raise RehearsalError("drift_changed_billing_fields")
        return {
            "scenario": scenario,
            "drift_rejected_before_billing_writes": True,
            "snapshot_scope": SNAPSHOT_SCOPE,
        }
    command.upgrade(configuration, TARGET)
    if MigrationContext.configure(connection).get_current_heads() != (TARGET,):
        raise RehearsalError("target_revision_not_installed")
    if (
        _rows(connection, "payments", exclude=("payment_provider", "currency"))
        != prior_payments
    ):
        raise RehearsalError("legacy_payment_data_changed")
    if _rows(connection, "admins", exclude=("auth_subject",)) != admins:
        raise RehearsalError("administrator_data_changed")
    if connection.execute(
        text("SELECT count(*) FROM public.admins WHERE auth_subject IS NOT NULL")
    ).scalar_one():
        raise RehearsalError("administrator_identity_was_automatically_bound")
    if (
        _rows(connection, "role_permissions") != role_links
        or _rows(connection, "roles") != roles
    ):
        raise RehearsalError("migration_changed_existing_roles_or_grants")
    if _rows(connection, "subscriptions") != subscriptions:
        raise RehearsalError("migration_changed_subscription_state")
    if _rows(connection, "owners") != owners:
        raise RehearsalError("migration_changed_owner_identity_or_data")
    if (
        connection.execute(
            text("SELECT auth_subject FROM public.owners WHERE id=:id"),
            {"id": FIXTURE_ID},
        ).scalar_one()
        != FIXTURE_OWNER_SUBJECT
    ):
        raise RehearsalError("existing_nonnull_owner_identity_changed")
    custom_grants = (
        connection.execute(
            text(
                "SELECT p.code FROM public.permissions p "
                "JOIN public.role_permissions rp ON rp.permission_id=p.id "
                "JOIN public.roles r ON r.id=rp.role_id "
                "WHERE r.code=:code ORDER BY p.code"
            ),
            {"code": FIXTURE_ROLE_CODE},
        )
        .scalars()
        .all()
    )
    if custom_grants != [FIXTURE_PERMISSION_CODE]:
        raise RehearsalError("custom_nonfinancial_role_grant_changed")
    if (
        connection.execute(
            text("SELECT count(*) FROM public.permissions WHERE code='payments.review'")
        ).scalar_one()
        != 1
    ):
        raise RehearsalError("review_permission_not_defined_once")
    for method, provider, currency in connection.execute(
        text("SELECT payment_method,payment_provider,currency FROM public.payments")
    ):
        if (
            provider != ("manual_transfer" if method in {"ccp", "baridimob"} else None)
            or currency != "DZD"
        ):
            raise RehearsalError("provider_backfill_or_currency_default_failed")
    for table, fingerprint in evidence.items():
        if _rows(connection, table) != fingerprint:
            raise RehearsalError("existing_evidence_changed_during_adoption")
    if not evidence:
        _insert_receipt(connection, receipt_id=FIXTURE_ID, payment_id=FIXTURE_ID)
    enforced = _verify_integrity(connection, configuration=configuration)
    installed = _snapshot(connection)
    command.upgrade(configuration, TARGET)
    if _snapshot(connection) != installed:
        raise RehearsalError("repeat_upgrade_was_not_idempotent")
    return {
        "scenario": scenario,
        "from_revision": PREDECESSOR,
        "to_revision": TARGET,
        "legacy_rows_preserved": True,
        "identities_unbound": True,
        "role_grants_unchanged": True,
        "subscription_state_unchanged": True,
        "constraints_enforced": enforced,
        "repeat_upgrade_idempotent": True,
        "existing_evidence_preserved": bool(evidence),
        "existing_nonnull_owner_identity_preserved": True,
        "custom_nonfinancial_grant_preserved": True,
        "administrator_identity_unique_metadata_verified": True,
        "new_payment_server_default_verified": True,
        "snapshot_scope": SNAPSHOT_SCOPE,
    }


# ==============================================
# GUARDED ASYNC ENTRY AND MANDATORY ROLLBACK VERIFICATION
# ==============================================


async def rehearse(*, scenario: Scenario) -> Report:
    """Always roll back test DDL/DML, including sequence changes and version rows."""
    if scenario not in {"fresh", "adoption", "drift"}:
        raise RehearsalError("unsupported_rehearsal_scenario")
    validate_test_branch_configuration(
        branch_id=settings.TEST_DATABASE_BRANCH_ID,
        project_id=settings.TEST_DATABASE_PROJECT_ID,
        protected_branch_id=settings.PROTECTED_DATABASE_BRANCH_ID,
    )
    url = validated_test_database_url(
        test_database_url=settings.TEST_DATABASE_URL,
        test_endpoint_id=settings.TEST_DATABASE_ENDPOINT_ID,
        protected_endpoint_id=settings.PROTECTED_DATABASE_ENDPOINT_ID,
    )
    engine = create_async_engine(
        url,
        echo=False,
        poolclass=NullPool,
        connect_args=isolated_connection_arguments(),
    )
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SET TRANSACTION READ ONLY"))
            identity = await connection.run_sync(
                lambda sync: read_test_database_identity(
                    sync,
                    endpoint_id=settings.TEST_DATABASE_ENDPOINT_ID,
                    branch_id=settings.TEST_DATABASE_BRANCH_ID,
                    project_id=settings.TEST_DATABASE_PROJECT_ID,
                    protected_branch_id=settings.PROTECTED_DATABASE_BRANCH_ID,
                )
            )
            await connection.rollback()
            logger.info(
                "billing_test_rehearsal_started",
                extra={"scenario": scenario, "database": "neondb_test"},
            )
            transaction = await connection.begin()
            before: DatabaseSnapshot | None = None
            failure: BaseException | None = None
            report: Report = {}
            try:
                acquired = (
                    await connection.execute(
                        text("SELECT pg_try_advisory_xact_lock(:id)"), {"id": LOCK_ID}
                    )
                ).scalar_one()
                if not acquired:
                    raise RehearsalError("another_rehearsal_is_running")
                tables = await connection.run_sync(
                    lambda sync: inspect(sync).get_table_names(schema="public")
                )
                for table in sorted(tables):
                    await connection.run_sync(
                        lambda sync, name=table: sync.execute(
                            text(
                                f"LOCK TABLE public.{_quoted(sync, name)} IN SHARE ROW EXCLUSIVE MODE"
                            )
                        )
                    )
                before = await connection.run_sync(_snapshot)
                if before.revision != TEST_HEAD:
                    raise RehearsalError("unexpected_test_revision")
                await connection.run_sync(_reserve_fixture_identifiers)
                # nextval()/setval() alone are not transactional. RESTART obtains
                # transactional sequence state and rolls back to the prior value.
                for name, (value, called, increment) in before.sequences.items():
                    restart = value + increment if called else value
                    await connection.run_sync(
                        lambda sync, sequence=name, position=restart: sync.execute(
                            text(
                                f"ALTER SEQUENCE public.{_quoted(sync, sequence)} RESTART WITH {position}"
                            )
                        )
                    )
                report = await connection.run_sync(
                    lambda sync: _run_scenario(sync, scenario=scenario)
                )
            except BaseException as error:
                failure = error
            finally:
                await transaction.rollback()
            if before is not None:
                after = await connection.run_sync(_snapshot)
                if after != before:
                    raise RehearsalError("test_database_not_identical_after_rollback")
                logger.info(
                    "billing_test_rehearsal_rollback_verified",
                    extra={
                        "scenario": scenario,
                        "baseline_revision": before.revision,
                        "outcome": "failed" if failure is not None else "passed",
                    },
                )
            if failure is not None:
                raise failure
            return report | {
                "database": "neondb_test",
                "original_test_revision": TEST_HEAD,
                "measured_rollback_state_restored": True,
                "snapshot_scope": SNAPSHOT_SCOPE,
                "verified_identity": identity,
                "permanent_database_changes": False,
            }
    finally:
        await engine.dispose()


# ==============================================
# READ-ONLY PREFLIGHT BEFORE ANY REHEARSAL WRITE
# ==============================================


async def preflight() -> Report:
    """Attest the configured development server within a read-only transaction."""
    validate_test_branch_configuration(
        branch_id=settings.TEST_DATABASE_BRANCH_ID,
        project_id=settings.TEST_DATABASE_PROJECT_ID,
        protected_branch_id=settings.PROTECTED_DATABASE_BRANCH_ID,
    )
    url = validated_test_database_url(
        test_database_url=settings.TEST_DATABASE_URL,
        test_endpoint_id=settings.TEST_DATABASE_ENDPOINT_ID,
        protected_endpoint_id=settings.PROTECTED_DATABASE_ENDPOINT_ID,
    )
    engine = create_async_engine(
        url,
        echo=False,
        poolclass=NullPool,
        connect_args=isolated_connection_arguments(),
    )
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SET TRANSACTION READ ONLY"))
            identity = await connection.run_sync(
                lambda sync: read_test_database_identity(
                    sync,
                    endpoint_id=settings.TEST_DATABASE_ENDPOINT_ID,
                    branch_id=settings.TEST_DATABASE_BRANCH_ID,
                    project_id=settings.TEST_DATABASE_PROJECT_ID,
                    protected_branch_id=settings.PROTECTED_DATABASE_BRANCH_ID,
                )
            )
            read_only = (
                await connection.execute(text("SHOW transaction_read_only"))
            ).scalar_one() == "on"
            revision = (
                await connection.execute(
                    text("SELECT version_num FROM public.alembic_version")
                )
            ).scalar_one()
            tables = await connection.run_sync(
                lambda sync: len(inspect(sync).get_table_names(schema="public"))
            )
            server_version = int(
                (await connection.execute(text("SHOW server_version_num"))).scalar_one()
            )
            await connection.rollback()
            if not read_only or revision != TEST_HEAD:
                raise RehearsalError("test_preflight_state_not_ready")
            return identity | {
                "read_only": True,
                "tls_hostname_verified": True,
                "installed_revision": revision,
                "public_table_count": tables,
                "postgresql_server_version_num": server_version,
                "preflight_passed": True,
            }
    finally:
        await engine.dispose()


# ==============================================
# GUARDED COMMAND-LINE ENTRY
# ==============================================


def _write_report(*, report: Report, filename: str) -> None:
    """Write valid JSON into the ignored review folder separately from console logs."""
    directory = PROJECT_ROOT / "artifacts" / "billing-production-review"
    directory.mkdir(parents=True, exist_ok=True)
    result = report | {
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    }
    (directory / filename).write_text(
        json.dumps(result, indent=2), encoding="utf-8", newline="\n"
    )
    print(json.dumps(result, indent=2))


async def main() -> None:
    """Complete the read-only gate before any rollback-only migration scenario."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Verify test identity and schema without a migration rehearsal",
    )
    options = parser.parse_args()
    identity = await preflight()
    if options.preflight_only:
        _write_report(
            report={"preflight": identity, "production_touched": False},
            filename="development-preflight.json",
        )
        return
    reports = [
        await rehearse(scenario=scenario) for scenario in ("fresh", "adoption", "drift")
    ]
    _write_report(
        report={
            "preflight": identity,
            "scenarios": reports,
            "production_touched": False,
        },
        filename="development-rehearsal-results.json",
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as error:
        source_frames = [
            {
                "file": str(Path(frame.filename).relative_to(PROJECT_ROOT)),
                "line": frame.lineno,
                "function": frame.name,
            }
            for frame in extract_tb(error.__traceback__)
            if Path(frame.filename).is_relative_to(PROJECT_ROOT)
            and Path(frame.filename).relative_to(PROJECT_ROOT).parts[0]
            in {"scripts", "app", "alembic", "alembic_test"}
        ]
        message = (
            str(error)
            if isinstance(error, (RehearsalError, UnsafeTestDatabaseError))
            else "rehearsal_failed"
        )
        print(
            json.dumps(
                {
                    "completed": False,
                    "reason": message,
                    "error_type": type(error).__name__,
                    "sqlstate": getattr(getattr(error, "orig", None), "sqlstate", None),
                    "source_frames": source_frames,
                }
            )
        )
        sys.exit(1)
