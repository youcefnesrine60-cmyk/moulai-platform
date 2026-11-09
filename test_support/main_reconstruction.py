# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MAIN RECONSTRUCTION CATALOGUE AND STARTUP PROOF
# Inspect all schema object classes and exercise FastAPI on the checked local target.
# ==============================================

"""Capture local main-history evidence without opening any remote connection."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND READ-ONLY CATALOGUE QUERIES
# Query PostgreSQL definitions directly instead of treating ORM metadata as proof.
# ==============================================

import asyncio
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    create_async_engine,
)

from test_support.local_postgres import (
    LOCAL_MAIN_REVISION,
    LocalPostgresSettings,
    read_local_test_identity,
)

QUERIES: dict[str, str] = {
    "tables": """SELECT n.nspname AS schema,c.relname AS name,c.relkind,c.relrowsecurity,c.relforcerowsecurity,c.relreplident,c.reloptions,c.relacl::text AS acl,pg_get_userbyid(c.relowner) AS owner FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind IN ('r','p','v','m','f') ORDER BY 1,2""",
    "columns": """SELECT n.nspname AS schema,c.relname AS table_name,a.attname AS name,a.attnum,format_type(a.atttypid,a.atttypmod) AS type,a.attnotnull,a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid) AS default_value,coll.collname AS collation,a.attacl::text AS acl FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace LEFT JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum LEFT JOIN pg_collation coll ON coll.oid=a.attcollation WHERE n.nspname='public' AND c.relkind IN ('r','p','v','m','f') AND a.attnum>0 AND NOT a.attisdropped ORDER BY 1,2,4""",
    "constraints": """SELECT n.nspname AS schema,c.relname AS table_name,k.conname AS name,k.contype,k.convalidated,k.condeferrable,k.condeferred,k.conislocal,pg_get_constraintdef(k.oid,true) AS definition FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' ORDER BY 1,2,3""",
    "indexes": """SELECT n.nspname AS schema,c.relname AS table_name,ic.relname AS name,i.indisunique,i.indisprimary,i.indisvalid,i.indisready,pg_get_indexdef(i.indexrelid) AS definition,pg_get_expr(i.indpred,i.indrelid) AS predicate,ic.reloptions FROM pg_index i JOIN pg_class c ON c.oid=i.indrelid JOIN pg_class ic ON ic.oid=i.indexrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' ORDER BY 1,2,3""",
    "triggers": """SELECT n.nspname AS schema,c.relname AS table_name,t.tgname AS name,t.tgenabled,pg_get_triggerdef(t.oid,true) AS definition FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND NOT t.tgisinternal ORDER BY 1,2,3""",
    "functions": """SELECT n.nspname AS schema,p.proname AS name,pg_get_function_identity_arguments(p.oid) AS arguments,p.prosecdef,p.provolatile,p.proparallel,p.proconfig,p.proacl::text AS acl,pg_get_userbyid(p.proowner) AS owner,pg_get_functiondef(p.oid) AS definition FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.prokind IN ('f','p') ORDER BY 1,2,3""",
    "policies": """SELECT schemaname AS schema,tablename AS table_name,policyname AS name,permissive,roles::text,cmd,qual,with_check FROM pg_policies WHERE schemaname='public' ORDER BY 1,2,3""",
    "sequences": """SELECT schemaname AS schema,sequencename AS name,sequenceowner AS owner,data_type,start_value,min_value,max_value,increment_by,cycle,cache_size,last_value FROM pg_sequences WHERE schemaname='public' ORDER BY 1,2""",
    "schemas": """SELECT nspname AS name,pg_get_userbyid(nspowner) AS owner,nspacl::text AS acl FROM pg_namespace WHERE nspname NOT LIKE 'pg_%' AND nspname<>'information_schema' ORDER BY 1""",
    "extensions": """SELECT e.extname AS name,e.extversion,n.nspname AS schema FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace ORDER BY 1""",
    "default_acls": """SELECT pg_get_userbyid(d.defaclrole) AS owner,n.nspname AS schema,d.defaclobjtype,d.defaclacl::text AS acl FROM pg_default_acl d LEFT JOIN pg_namespace n ON n.oid=d.defaclnamespace ORDER BY 1,2,3""",
    "enums": """SELECT n.nspname AS schema,t.typname AS name,e.enumsortorder,e.enumlabel FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace JOIN pg_enum e ON e.enumtypid=t.oid WHERE n.nspname='public' ORDER BY 1,2,3""",
    "domains": """SELECT n.nspname AS schema,t.typname AS name,format_type(t.typbasetype,t.typtypmod) AS base_type,t.typnotnull,t.typdefault FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace WHERE n.nspname='public' AND t.typtype='d' ORDER BY 1,2""",
}

# ==============================================
# CHECKED CATALOGUE CAPTURE
# Read constraints, triggers, ACLs and configuration before destructive test cleanup.
# ==============================================


async def verify_main_reconstruction(
    *, configuration: LocalPostgresSettings, output: Path
) -> dict[str, Any]:
    """Capture and validate S1a schema, then complete the real application lifespan.

    Requires process settings already pinned to the same local URL. It neither
    seeds fixture prices nor replaces init_db, application routes or schema guards.
    """
    if configuration.PROFILE != "main":
        raise RuntimeError("main_verification_profile_required")
    engine = create_async_engine(
        configuration.URL.get_secret_value(), echo=False, connect_args={"ssl": False}
    )
    catalogue: dict[str, Any] = {}
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SET TRANSACTION READ ONLY"))
            await connection.run_sync(
                lambda sync: read_local_test_identity(sync, configuration=configuration)
            )
            for name, query in QUERIES.items():
                catalogue[name] = [
                    dict(row)
                    for row in (await connection.execute(text(query))).mappings()
                ]
            catalogue["revision"] = (
                await connection.execute(
                    text("SELECT version_num FROM alembic_version")
                )
            ).scalar_one()
            catalogue["row_counts"] = {}
            for row in catalogue["tables"]:
                name = row["name"]
                if not name.replace("_", "").isalnum():
                    raise RuntimeError("unexpected_catalogue_identifier")
                catalogue["row_counts"][name] = (
                    await connection.execute(
                        text(f'SELECT count(*) FROM public."{name}"')
                    )
                ).scalar_one()
            for name, query in {
                "approved_pricing": "SELECT * FROM subscription_pricing_config ORDER BY id",
                "unvalidated_foreign_keys": "SELECT conname FROM pg_constraint WHERE contype='f' AND NOT convalidated ORDER BY conname",
                "personal_role_assignments": "SELECT count(*) AS count FROM admins WHERE role_id IS NOT NULL",
                "role_grants": "SELECT r.name AS role,p.code AS permission FROM role_permissions rp JOIN roles r ON r.id=rp.role_id JOIN permissions p ON p.id=rp.permission_id ORDER BY 1,2",
                "runtime_role": "SELECT rolname,rolsuper,rolcreatedb,rolcreaterole,rolbypassrls FROM pg_roles WHERE rolname=current_user",
                "database_locale": "SELECT encoding,datlocprovider,datlocale,datcollate,datctype,datcollversion FROM pg_database WHERE datname=current_database()",
            }.items():
                catalogue[name] = [
                    dict(row)
                    for row in (await connection.execute(text(query))).mappings()
                ]
    finally:
        await engine.dispose()
    catalogue = json.loads(
        json.dumps(
            catalogue,
            default=lambda value: (
                value.decode("utf-8").rstrip("\x00")
                if isinstance(value, bytes)
                else str(value)
            ),
        )
    )
    (output / "main-catalogue.json").write_text(
        json.dumps(catalogue, indent=2, default=str) + "\n", encoding="utf-8"
    )
    unvalidated = [row["conname"] for row in catalogue["unvalidated_foreign_keys"]]
    expected = [
        "fk_admin_identity",
        "fk_group_link_group_org",
        "fk_group_link_restaurant_org",
        "fk_groups_org",
        "fk_owner_identity",
        "fk_restaurants_org",
    ]
    if (
        catalogue["revision"] != LOCAL_MAIN_REVISION
        or len(catalogue["tables"]) != 61
        or unvalidated != expected
    ):
        raise RuntimeError("main_catalogue_contract_mismatch")
    from app.core.config import settings
    from app.main import app

    if (
        settings.DATABASE_URL != configuration.URL.get_secret_value()
        or settings.DATABASE_TARGET != "primary"
    ):
        raise RuntimeError("application_not_pinned_to_local_reconstruction")
    async with app.router.lifespan_context(app), httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://moulai-local-rehearsal"
    ) as client:
        root = await client.get("/")
        health = await client.get("/health")
    proof = {
        "actual_lifespan_completed": True,
        "init_db_replaced": False,
        "root_http_status": root.status_code,
        "health_http_status": health.status_code,
        "network_server_started": False,
        "not_valid_foreign_keys": unvalidated,
    }
    (output / "main-startup.json").write_text(
        json.dumps(proof, indent=2) + "\n", encoding="utf-8"
    )
    if root.status_code != 200 or health.status_code != 200:
        raise RuntimeError("main_startup_http_failure")
    return proof


# ==============================================
# EFFECTIVE TABLE PRIVILEGES
# Resolve default owner ACLs explicitly before comparing restored privileges.
# ==============================================


async def effective_table_privileges(
    *, connection: AsyncConnection
) -> list[dict[str, Any]]:
    """Read effective table grants, treating NULL ACLs as PostgreSQL defaults."""
    query = "SELECT c.relname, a.grantee, a.grantor, a.privilege_type, a.is_grantable FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace CROSS JOIN LATERAL aclexplode(coalesce(c.relacl,acldefault('r',c.relowner))) a WHERE n.nspname='public' AND c.relkind='r' ORDER BY 1,2,3,4,5"
    return [dict(row) for row in (await connection.execute(text(query))).mappings()]


# ==============================================
# RESTORED CHECK AND INDEX PREDICATE SEMANTICS
# Evaluate changed varchar expressions with valid, invalid and NULL values, without writes.
# ==============================================


async def verify_restored_expressions(
    *, connection: AsyncConnection, before: dict[str, Any]
) -> list[dict[str, object]]:
    """Compare each changed CHECK and the partial-index predicate by SQL truth value."""
    after_constraints = [
        dict(row)
        for row in (await connection.execute(text(QUERIES["constraints"]))).mappings()
    ]
    after_indexes = [
        dict(row)
        for row in (await connection.execute(text(QUERIES["indexes"]))).mappings()
    ]
    proof: list[dict[str, object]] = []
    for category, after_rows, field in [
        ("constraints", after_constraints, "definition"),
        ("indexes", after_indexes, "predicate"),
    ]:
        previous = {(row["table_name"], row["name"]): row for row in before[category]}
        if set(previous) != {(row["table_name"], row["name"]) for row in after_rows}:
            raise RuntimeError("restored_schema_object_identity_changed")
        for row in after_rows:
            old = previous[(row["table_name"], row["name"])][field]
            new = row[field]
            if old == new:
                continue
            if (
                not old
                or not new
                or (category == "constraints" and not old.startswith("CHECK ("))
            ):
                raise RuntimeError("unreviewed_restored_expression_difference")
            if category == "constraints":
                old, new = old[7:-1], new[7:-1]
            table_columns = {
                item["name"]
                for item in before["columns"]
                if item["table_name"] == row["table_name"]
            }
            columns = sorted(
                table_columns & set(re.findall(r"\b([a-z_][a-z0-9_]*)\)?::text", old))
            )
            if not columns or any(
                item["type"] not in {"text"}
                and not item["type"].startswith("character varying")
                for item in before["columns"]
                if item["table_name"] == row["table_name"] and item["name"] in columns
            ):
                raise RuntimeError("restored_expression_requires_separate_type_review")
            values: list[str | None] = [
                *sorted(set(re.findall(r"'([^']*)'", old + new))),
                "__invalid__",
                "",
                None,
            ]
            sources = " CROSS JOIN ".join(
                f'unnest(CAST(:values{index} AS varchar[])) AS v{index}("{column}")'
                for index, column in enumerate(columns)
            )
            result = (
                (
                    await connection.execute(
                        text(
                            f"SELECT count(*) AS samples, count(*) FILTER (WHERE (({old}) IS DISTINCT FROM ({new}))) AS mismatches FROM {sources}"
                        ),
                        {f"values{index}": values for index in range(len(columns))},
                    )
                )
                .mappings()
                .one()
            )
            if result["mismatches"]:
                raise RuntimeError("restored_expression_truth_value_changed")
            proof.append(
                {
                    "object": row["table_name"] + "." + row["name"],
                    "samples": result["samples"],
                    "mismatches": result["mismatches"],
                }
            )
    return proof


# ==============================================
# VERIFIED CANONICAL ARCHIVE AND LOCAL RESTORATION
# Export approved seeds only, then rehearse the future reconstruction from that archive.
# ==============================================


async def prepare_main_archive(
    *,
    configuration: LocalPostgresSettings,
    binary_root: Path,
    destination: Path,
    catalogue_before: dict[str, Any],
) -> dict[str, object]:
    """Archive and restore the checked local canonical schema, never a remote database.

    Refuse application rows, existing archives and destinations inside the repository.
    The existing protected backup directory must have been prepared separately.
    """
    private = Path.home() / "MoulAI-private-backups/20261030-main-rehearsal"
    if (
        configuration.PROFILE != "main"
        or destination.resolve().parent != private.resolve()
        or destination.exists()
        or not private.is_dir()
    ):
        raise RuntimeError("main_archive_destination_not_private_and_new")
    engine = create_async_engine(
        configuration.URL.get_secret_value(),
        echo=False,
        hide_parameters=True,
        connect_args={"ssl": False},
    )
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SET TRANSACTION READ ONLY"))
            await connection.run_sync(
                lambda sync: read_local_test_identity(sync, configuration=configuration)
            )
            before_acl = await effective_table_privileges(connection=connection)
            tables = list(
                (
                    await connection.execute(
                        text(
                            "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
                        )
                    )
                ).scalars()
            )
            seed_tables = {
                "alembic_version",
                "branch_pricing",
                "loyalty_discounts",
                "multi_restaurant_discounts",
                "permissions",
                "role_permissions",
                "roles",
                "subscription_pricing_config",
                "tenant_roles",
                "tenant_role_permissions",
            }
            for name in tables:
                if (
                    name not in seed_tables
                    and (
                        await connection.execute(
                            text(f'SELECT count(*) FROM public."{name}"')
                        )
                    ).scalar_one()
                ):
                    raise RuntimeError("main_archive_contains_application_rows")
            revision = (
                await connection.execute(
                    text("SELECT version_num FROM alembic_version")
                )
            ).scalar_one()
            if revision != LOCAL_MAIN_REVISION or len(tables) != 61:
                raise RuntimeError("main_archive_requires_verified_s1a")
    finally:
        await engine.dispose()
    from sqlalchemy.engine import make_url

    url = make_url(configuration.URL.get_secret_value())
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith("PG")
    }
    environment.update(
        {
            "PGHOST": "127.0.0.1",
            "PGPORT": "55432",
            "PGDATABASE": "moulai_pytest",
            "PGUSER": "moulai_pytest",
            "PGPASSWORD": url.password,
            "PGSSLMODE": "disable",
        }
    )
    steps = [
        [
            str(binary_root / "pg_dump.exe"),
            "--no-password",
            "--format=custom",
            "--no-owner",
            "--no-privileges",
            "--file=" + str(destination),
        ],
        [str(binary_root / "pg_restore.exe"), "--list", str(destination)],
        [
            str(binary_root / "pg_restore.exe"),
            "--no-password",
            "--dbname=moulai_pytest",
            "--exit-on-error",
            "--single-transaction",
            "--clean",
            "--if-exists",
            "--no-owner",
            "--no-privileges",
            str(destination),
        ],
    ]
    for index, arguments in enumerate(steps):
        result = await asyncio.to_thread(
            subprocess.run,
            arguments,
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=120,
        )
        if result.returncode:
            raise RuntimeError(f"main_archive_local_step_failed:{index}")
    # A no-ACL restore must retain the reviewed denial of schema access to PUBLIC.
    engine = create_async_engine(
        configuration.URL.get_secret_value(),
        echo=False,
        hide_parameters=True,
        connect_args={"ssl": False},
    )
    try:
        async with engine.begin() as connection:
            await connection.run_sync(
                lambda sync: read_local_test_identity(sync, configuration=configuration)
            )
            await connection.execute(text("REVOKE ALL ON SCHEMA public FROM PUBLIC"))
        async with engine.connect() as connection:
            await connection.execute(text("SET TRANSACTION READ ONLY"))
            after_acl = await effective_table_privileges(connection=connection)
            expression_proof = await verify_restored_expressions(
                connection=connection, before=catalogue_before
            )
            if before_acl != after_acl:
                raise RuntimeError("restored_effective_privileges_changed")
    finally:
        await engine.dispose()
    return {
        "effective_table_privileges_equal": True,
        "expression_proof": expression_proof,
        "path": str(destination),
        "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "bytes": destination.stat().st_size,
        "archive_list_verified": True,
        "local_clean_restore_completed": True,
        "application_rows_exported": 0,
        "remote_operations": 0,
    }
