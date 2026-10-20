# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""G2-only Alembic launcher pinned to the approved W endpoint and two revisions.

No branch API, generic URL override, stamp, head target or source fallback exists.
Each invocation requires independently reviewed fresh G1 evidence. Only the
outer owner commits; any failure rolls back and ends this invocation.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import sys
from dataclasses import (
    dataclass,
    field,
)
from datetime import (
    datetime,
    timezone,
)
from pathlib import Path
from typing import (
    Any,
    Literal,
)

from sqlalchemy import text
from sqlalchemy.engine import (
    URL,
    Connection,
    make_url,
)
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

ROOT = Path(__file__).resolve().parents[1]
WRITER_BRANCH = "br-nameless-hall-asvgljm8"
WRITER_ENDPOINT = "ep-spring-fire-asgkya2x"
PROJECT = "shiny-lab-60817779"
PARENT = "dce91870b4a2"
TARGET = "e1b92b200001"
Direction = Literal["upgrade", "downgrade"]
logger = logging.getLogger(__name__)
FROZEN_E1_HASHES = {
    "migration_support/__init__.py": "5b891a65c4441eacfe7ecccc4331cd822acd0845c5d9d12220678a7bf6a4bd69",
    "migration_support/tenant_e1.py": "85165672c9f3ec403d9da2fa9eecd422b6543683f42d47077ae8a79ef752db96",
    "migration_support/tenant_e1_schema.py": "a27fef279e6c55d6546d5a40bfe7fc9692f3038337955e001d8024496dcfd570",
    "migration_support/tenant_e1_sql.py": "7f704a5ce0d17639e71ca09fd6d74bf1471f6805500d74756fe6230cf39219ed",
    "alembic_test/versions/e1b92b200001_tenant_foundation_e1.py": "77f004a287a71a4db3c2bc17f45af9d7582e7d1f43faa36087d90401f5a6f4d3",
}


# ==============================================
# PRIVATE BOUND INPUTS, NEVER SERIALIZED WITH CREDENTIALS
# ==============================================


@dataclass(frozen=True, slots=True, kw_only=True)
class BoundRehearsal:
    """Hold process-local central Settings and approved comparison evidence."""

    manifest: Any
    proof: Any
    approved_sha256: str
    settings: Any = field(repr=False)
    url: URL = field(repr=False)
    environment: dict[str, str] = field(repr=False)
    baseline: dict[str, Any] = field(repr=False)


# ==============================================
# FROZEN MIGRATION SOURCE INTEGRITY
# ==============================================


def verify_frozen_sources() -> None:
    """Reject any change to the exact E1 contract previously approved in B2."""
    for relative, expected in FROZEN_E1_HASHES.items():
        if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != expected:
            raise RuntimeError("frozen_e1_source_hash_mismatch")


# ==============================================
# EXACT WRITER CONFIGURATION AND SECRET-SAFE ADMISSION
# ==============================================


def bind_writer(
    *, manifest_path: Path, approved_sha256: str, proof_path: Path, baseline_path: Path
) -> BoundRehearsal:
    """Use central Settings, change only the isolated process's intended target."""
    from app.core.config import (
        Settings,
        settings,
    )
    from app.core.rehearsal_admission import (
        InitialStateEquivalence,
        admit_destination,
        initial_state_digest,
        parse_manifest,
    )
    from app.core.test_database import validated_test_database_url

    verify_frozen_sources()
    if (
        settings.TEST_DATABASE_PROJECT_ID != PROJECT
        or settings.TEST_DATABASE_BRANCH_ID != "br-lively-truth-asga1dtk"
        or settings.TEST_DATABASE_ENDPOINT_ID != "ep-quiet-rain-assrs0gv"
        or settings.PROTECTED_DATABASE_BRANCH_ID != "br-plain-firefly-as17il6w"
        or settings.PROTECTED_DATABASE_ENDPOINT_ID != "ep-billowing-term-as9aufue"
    ):
        raise RuntimeError("source_configuration_drift")
    manifest = parse_manifest(payload=manifest_path.read_text(encoding="utf-8"))
    proof = InitialStateEquivalence.model_validate_json(
        proof_path.read_text(encoding="utf-8")
    )
    writer = next(item for item in manifest.resources if item.purpose == "rehearsal")
    if writer.branch_id != WRITER_BRANCH or writer.endpoint_id != WRITER_ENDPOINT:
        raise RuntimeError("exclusive_writer_mismatch")
    endpoint = next(
        item
        for item in manifest.control_plane.endpoints
        if item.endpoint_id == WRITER_ENDPOINT
    )
    source = validated_test_database_url(
        test_database_url=settings.TEST_DATABASE_URL,
        test_endpoint_id=settings.TEST_DATABASE_ENDPOINT_ID,
        protected_endpoint_id=settings.PROTECTED_DATABASE_ENDPOINT_ID,
    )
    url = make_url(source).set(host=endpoint.direct_host, port=5432, query={})
    runtime = Settings(
        TEST_DATABASE_URL=url.render_as_string(hide_password=False),
        TEST_DATABASE_BRANCH_ID=WRITER_BRANCH,
        TEST_DATABASE_ENDPOINT_ID=WRITER_ENDPOINT,
    )
    environment = {
        "APP_ENV": runtime.APP_ENV,
        "DATABASE_TARGET": runtime.DATABASE_TARGET,
        "DEBUG": str(runtime.DEBUG).lower(),
        "DB_ECHO": str(runtime.DB_ECHO).lower(),
        "OIDC_DIAGNOSTICS_ENABLED": str(runtime.OIDC_DIAGNOSTICS_ENABLED).lower(),
        "OIDC_ALLOW_LOCAL_HTTP": str(runtime.OIDC_ALLOW_LOCAL_HTTP).lower(),
        "TEST_DATABASE_PROJECT_ID": runtime.TEST_DATABASE_PROJECT_ID,
        "TEST_DATABASE_BRANCH_ID": runtime.TEST_DATABASE_BRANCH_ID,
        "TEST_DATABASE_ENDPOINT_ID": runtime.TEST_DATABASE_ENDPOINT_ID,
        "PROTECTED_DATABASE_BRANCH_ID": runtime.PROTECTED_DATABASE_BRANCH_ID,
        "PROTECTED_DATABASE_ENDPOINT_ID": runtime.PROTECTED_DATABASE_ENDPOINT_ID,
    }
    admit_destination(
        manifest=manifest,
        approved_sha256=approved_sha256,
        purpose="rehearsal",
        operation="e1",
        database_url=url.render_as_string(hide_password=False),
        environment=environment,
        now=datetime.now(timezone.utc),
        equivalence=proof,
    )
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    if initial_state_digest(report=baseline) != proof.rehearsal:
        raise RuntimeError("writer_baseline_evidence_mismatch")
    return BoundRehearsal(
        manifest=manifest,
        proof=proof,
        approved_sha256=approved_sha256,
        settings=runtime,
        url=url,
        environment=environment,
        baseline=baseline,
    )


# ==============================================
# ACTUAL PINNED CONNECTION CHECK (DB HELPER)
# ==============================================


def check_connection(
    connection: Connection, *, bound: BoundRehearsal, expected_revision: str
) -> None:
    """Re-admit W on the exact actual connection before any mutation."""
    from app.core.rehearsal_admission import admit_destination
    from app.core.test_database import read_test_database_identity

    if (
        not connection.in_transaction()
        or connection.dialect.name != "postgresql"
        or connection.get_execution_options().get("isolation_level") == "AUTOCOMMIT"
    ):
        raise RuntimeError("writer_transaction_required")
    admit_destination(
        manifest=bound.manifest,
        approved_sha256=bound.approved_sha256,
        purpose="rehearsal",
        operation="e1",
        database_url=connection.engine.url.render_as_string(hide_password=False),
        environment=bound.environment,
        now=datetime.now(timezone.utc),
        equivalence=bound.proof,
    )
    read_test_database_identity(
        connection,
        endpoint_id=WRITER_ENDPOINT,
        branch_id=WRITER_BRANCH,
        project_id=PROJECT,
        protected_branch_id="br-plain-firefly-as17il6w",
    )
    versions = (
        connection.execute(
            text("SELECT version_num FROM public.alembic_version LIMIT 2")
        )
        .scalars()
        .all()
    )
    if expected_revision not in {PARENT, TARGET} or versions != [expected_revision]:
        raise RuntimeError("writer_revision_mismatch")


# ==============================================
# ORIGINAL DATA AND SEQUENCES (DB HELPER)
# ==============================================


async def verify_original_data(
    connection: AsyncConnection, *, baseline: dict[str, Any], revision: str
) -> None:
    """Compare original column projections and sequence values without mutation."""
    quote = connection.dialect.identifier_preparer.quote_identifier
    for name, expected in baseline["tables"].items():
        if name == "alembic_version":
            if (
                await connection.execute(
                    text("SELECT version_num FROM public.alembic_version")
                )
            ).scalars().all() != [revision]:
                raise RuntimeError("unexpected_alembic_revision")
            continue
        columns = ",".join(quote(item) for item in expected["columns"])
        order = ",".join(quote(item) for item in expected["primary_key"])
        query = text(
            f"SELECT pg_catalog.to_jsonb(t)::text FROM (SELECT {columns} FROM public.{quote(name)}) AS t ORDER BY {order}"
        )
        count, digest = 0, hashlib.sha256()
        async with connection.stream(query) as stream:
            async for row in stream:
                value = row[0].encode("utf-8")
                if len(value) > 16777216 or count >= 1000000:
                    raise RuntimeError("legacy_stream_limit")
                digest.update(len(value).to_bytes(8, "big"))
                digest.update(value)
                count += 1
        if count != expected["rows"] or digest.hexdigest() != expected["sha256"]:
            raise RuntimeError("original_data_changed")
    for name, expected in baseline["sequences"].items():
        actual = (
            (
                await connection.execute(
                    text(f"SELECT last_value,is_called FROM public.{quote(name)}")
                )
            )
            .mappings()
            .one()
        )
        if (
            actual["last_value"] != expected["last_value"]
            or actual["is_called"] != expected["is_called"]
        ):
            raise RuntimeError("original_sequence_changed")


# ==============================================
# E1 CATALOG VERIFICATION (DB HELPER)
# ==============================================


async def verify_e1_catalog(
    connection: AsyncConnection, *, legacy_tables: set[str]
) -> dict[str, Any]:
    """Require the exact nine tables, five nullable columns and frozen SQL/policy."""
    from migration_support.tenant_e1 import (
        EXPANSIONS,
        operation_metadata,
    )
    from migration_support.tenant_e1_schema import (
        ROLE_PERMISSIONS,
        TENANT_TABLE_NAMES,
    )
    from migration_support.tenant_e1_sql import (
        FUNCTION_SIGNATURES,
        TRIGGER_DEFINITIONS,
    )

    tables = set(
        (
            await connection.execute(
                text(
                    "SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname='public'"
                )
            )
        ).scalars()
    )
    if tables != legacy_tables | set(TENANT_TABLE_NAMES):
        raise RuntimeError("e1_table_inventory_mismatch")
    for table, column in EXPANSIONS:
        row = (
            (
                await connection.execute(
                    text(
                        "SELECT is_nullable,data_type FROM information_schema.columns WHERE table_schema='public' AND table_name=:table AND column_name=:column"
                    ),
                    {"table": table, "column": column},
                )
            )
            .mappings()
            .one()
        )
        if row["is_nullable"] != "YES" or row["data_type"] != "integer":
            raise RuntimeError("e1_expansion_mismatch")
    rows = (
        await connection.execute(
            text(
                "SELECT role_code,permission_code FROM public.tenant_role_permissions ORDER BY 1,2"
            )
        )
    ).all()
    expected = sorted(
        (role, permission)
        for role, permissions in ROLE_PERMISSIONS.items()
        for permission in permissions
    )
    roles = (
        await connection.execute(
            text("SELECT code,policy_revision FROM public.tenant_roles ORDER BY code")
        )
    ).all()
    if [tuple(row) for row in rows] != expected or [tuple(row) for row in roles] != [
        (role, 1) for role in sorted(ROLE_PERMISSIONS)
    ]:
        raise RuntimeError("e1_policy_mismatch")
    triggers = (
        await connection.execute(
            text(
                "SELECT c.relname,t.tgname,t.tgdeferrable,t.tginitdeferred FROM pg_catalog.pg_trigger t JOIN pg_catalog.pg_class c ON c.oid=t.tgrelid JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND NOT t.tgisinternal"
            )
        )
    ).all()
    if {(r[0], r[1]) for r in triggers} != {
        (table, name) for table, name, _ in TRIGGER_DEFINITIONS
    } or sum(r[2] and r[3] for r in triggers) != 2:
        raise RuntimeError("e1_trigger_mismatch")
    functions = set(
        (
            await connection.execute(
                text(
                    "SELECT p.proname||'('||pg_catalog.pg_get_function_identity_arguments(p.oid)||')' FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public'"
                )
            )
        ).scalars()
    )
    # pg_get_function_identity_arguments includes the declared parameter name.
    expected_functions = {
        name.replace("(integer)", "(company_id integer)")
        for name in FUNCTION_SIGNATURES
    }
    if functions != expected_functions:
        raise RuntimeError("e1_function_mismatch")
    metadata = operation_metadata()
    constraints = (
        await connection.execute(
            text(
                "SELECT c.relname,k.conname,k.contype,k.convalidated FROM pg_catalog.pg_constraint k JOIN pg_catalog.pg_class c ON c.oid=k.conrelid JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public'"
            )
        )
    ).all()
    constraint_pairs = {(r[0], r[1]) for r in constraints}
    expected_pairs = {
        (name, str(c.name))
        for name in TENANT_TABLE_NAMES
        for c in metadata.tables[name].constraints
    }
    if not expected_pairs.issubset(constraint_pairs):
        raise RuntimeError("e1_constraint_mismatch")
    invalid_fks = sum((r[2] in {"f", b"f"}) and not r[3] for r in constraints)
    if invalid_fks != 6:
        raise RuntimeError("e1_fk_validation_flags_mismatch")
    indexes = set(
        (
            await connection.execute(
                text(
                    "SELECT tablename,indexname FROM pg_catalog.pg_indexes WHERE schemaname='public'"
                )
            )
        ).all()
    )
    expected_indexes = {
        (name, str(index.name))
        for name, table in metadata.tables.items()
        for index in table.indexes
    }
    if not expected_indexes.issubset({tuple(row) for row in indexes}):
        raise RuntimeError("e1_index_mismatch")
    return {
        "new_tables": 9,
        "nullable_columns": 5,
        "roles": len(roles),
        "permissions": len(rows),
        "triggers": len(triggers),
        "functions": len(functions),
        "new_table_constraints": len(expected_pairs),
        "not_valid_legacy_fks": invalid_fks,
    }


# ==============================================
# PROGRAMMATIC ALEMBIC WITH AN ADMITTED SHARED CONNECTION
# ==============================================


def run_alembic(
    connection: Connection, *, bound: BoundRehearsal, direction: Direction
) -> None:
    """Use only test history and the one approved adjacent revision transition."""
    from alembic.config import Config

    from alembic import command

    verify_frozen_sources()
    expected = PARENT if direction == "upgrade" else TARGET
    config = Config()
    config.set_main_option("script_location", str(ROOT / "alembic_test"))
    config.attributes.update(
        {
            "connection": connection,
            "moulai_rehearsal_settings": bound.settings,
            "moulai_rehearsal_admission": lambda actual: check_connection(
                actual, bound=bound, expected_revision=expected
            ),
        }
    )
    if direction == "upgrade":
        command.upgrade(config, TARGET)
    else:
        command.downgrade(config, PARENT)


# ==============================================
# OWNED TRANSACTION, COMMIT OR FULL ROLLBACK
# ==============================================


async def execute(*, bound: BoundRehearsal, direction: Direction, output: Path) -> int:
    """Check the same connection read-only, then re-attest its write transaction."""
    from app.core.test_database import isolated_connection_arguments

    expected, target = (PARENT, TARGET) if direction == "upgrade" else (TARGET, PARENT)
    engine = create_async_engine(
        bound.url,
        poolclass=NullPool,
        echo=False,
        connect_args=isolated_connection_arguments(),
    )
    result: dict[str, Any] = {
        "writer_branch": WRITER_BRANCH,
        "writer_endpoint": WRITER_ENDPOINT,
        "database": "neondb_test",
        "direction": direction,
        "from": expected,
        "to": target,
        "committed": False,
        "rolled_back": False,
    }
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                await connection.execute(text("SET TRANSACTION READ ONLY"))
                await connection.run_sync(
                    lambda c: check_connection(
                        c, bound=bound, expected_revision=expected
                    )
                )
                await verify_original_data(
                    connection, baseline=bound.baseline, revision=expected
                )
            finally:
                await transaction.rollback()
            transaction = await connection.begin()
            try:
                await connection.run_sync(
                    lambda c: check_connection(
                        c, bound=bound, expected_revision=expected
                    )
                )
                if (
                    await connection.scalar(
                        text("SELECT current_setting('transaction_read_only')")
                    )
                    != "off"
                ):
                    raise RuntimeError("writer_transaction_not_writable")
                logger.info(
                    "tenant_e1_rehearsal_started",
                    extra={"branch_id": WRITER_BRANCH, "direction": direction},
                )
                await connection.run_sync(
                    lambda c: run_alembic(c, bound=bound, direction=direction)
                )
                if direction == "upgrade":
                    result["catalog"] = await verify_e1_catalog(
                        connection, legacy_tables=set(bound.baseline["tables"])
                    )
                await verify_original_data(
                    connection, baseline=bound.baseline, revision=target
                )
                await transaction.commit()
                result["committed"] = True
                logger.info(
                    "tenant_e1_rehearsal_committed",
                    extra={"branch_id": WRITER_BRANCH, "direction": direction},
                )
            except Exception:
                await transaction.rollback()
                result["rolled_back"] = True
                raise
    # Driver failures must not expose statement parameters or credentials.
    except Exception as error:  # noqa: BLE001
        result.update(
            outcome="blocked",
            error_class=type(error).__name__,
            sqlstate=getattr(getattr(error, "orig", None), "sqlstate", None),
            statement_sha256=hashlib.sha256(
                str(getattr(error, "statement", "")).encode("utf-8")
            ).hexdigest(),
        )
        if isinstance(error, RuntimeError):
            # Our RuntimeErrors contain fixed codes only; driver messages do not.
            result["guard_code"] = str(error)
    finally:
        await engine.dispose()
    result["observed_at"] = datetime.now(timezone.utc).isoformat()
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["committed"] else 1


# ==============================================
# EXPLICIT COMMAND ENTRY POINT
# ==============================================


def main() -> int:
    """Require reviewed files and an exact direction; never infer a target URL."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--approved-sha256", required=True)
    parser.add_argument("--proof", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--direction", choices=("upgrade", "downgrade"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    os.environ.update(
        {
            "DEBUG": "false",
            "DB_ECHO": "false",
            "OIDC_DIAGNOSTICS_ENABLED": "false",
            "OIDC_ALLOW_LOCAL_HTTP": "false",
        }
    )
    try:
        bound = bind_writer(
            manifest_path=arguments.manifest,
            approved_sha256=arguments.approved_sha256,
            proof_path=arguments.proof,
            baseline_path=arguments.baseline,
        )
        return asyncio.run(
            execute(bound=bound, direction=arguments.direction, output=arguments.output)
        )
    # The CLI boundary retains only safe error classifications.
    except Exception as error:  # noqa: BLE001
        result = {
            "outcome": "blocked_before_execution",
            "error_class": type(error).__name__,
        }
        arguments.output.write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(result))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
