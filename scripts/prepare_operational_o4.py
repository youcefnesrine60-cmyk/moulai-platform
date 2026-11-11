# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# OWNED LOCAL BACKUP RESTORATION AND O4 REHEARSAL
# Verify the retained O2 review archive by actual restore, migration rollback, forward migration and recovery on another port.
# ==============================================

"""No remote URL, source migration, production target, stamp, application worker or provider call."""

from __future__ import annotations

# isort: split
# ==============================================
# EXPLICIT LOCAL DEPENDENCIES
# Passwords remain in private files or child environments and are never printed or passed as command arguments.
# ==============================================

import argparse
import asyncio
import hashlib
import json
import os
import re
import secrets
import socket
import subprocess
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import asyncpg
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import (
    Connection,
    make_url,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    create_async_engine,
)

from alembic import command
from app.integration.config import IntegrationConfig
from app.integration.local_setup import PG
from app.integration.process import local_host_lease
from scripts.run_offline_api_tests import OfflineNetworkGuard
from scripts.run_operational_local import resolve_instance

OUTPUT = ROOT / "artifacts/operational-o3-20261108"


# ==============================================
# TWO OWNED LOOPBACK PORTS ONLY
# The source is readable while the marked clone is writable; no DNS or other service is admitted.
# ==============================================


class RestorationNetworkGuard(OfflineNetworkGuard):
    """Limit Python sockets to the two reviewed numeric PostgreSQL addresses."""

    # ==============================================
    # AUDIT CALLBACK
    # Preserve the audit framework signature and deny every unlisted address through the offline guard.
    # ==============================================

    def __call__(self, event: str, arguments: tuple[object, ...]) -> None:
        """Admit only exact IPv4 connect/name resolution for the retained database and disposable clone."""
        address = (
            arguments[1]
            if event == "socket.connect" and len(arguments) > 1
            else arguments if event == "socket.getaddrinfo" else None
        )
        if isinstance(address, tuple) and address[:2] in {
            ("127.0.0.1", 55433),
            ("127.0.0.1", 55434),
        }:
            return
        if (
            event == "socket.bind"
            and len(arguments) > 1
            and arguments[1]
            in {
                ("127.0.0.1", 5180),
                ("127.0.0.1", 5582),
                ("127.0.0.1", 55433),
                ("127.0.0.1", 55434),
            }
        ):
            return
        super().__call__(event, arguments)


# ==============================================
# NONSECRET NATIVE PROCESS BOUNDARY
# File-backed capture avoids inherited Windows pipes and never returns sensitive stderr on failure.
# ==============================================


def native(*, arguments: list[str], environment: dict[str, str] | None = None) -> bytes:
    """Run an installed local executable once; stop on errors without retry or credential disclosure."""
    with tempfile.TemporaryFile() as output:
        result = subprocess.run(
            arguments,
            env=environment,
            stdout=output,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=180,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode:
            raise RuntimeError("operational_restore_native_process_failed")
        output.seek(0)
        return output.read()


# ==============================================
# LIVE TARGET AND WRITER ATTESTATION
# A configuration string does not prove the connected database or absence of writers.
# ==============================================


async def attest(*, connection: AsyncConnection, marker: str, port: int) -> None:
    """Require the actual owned database, runtime role, port, marker and no competing database client."""
    row = (
        await connection.execute(
            text(
                "SELECT current_database(),current_user,host(inet_server_addr()),inet_server_port(),shobj_description(oid,'pg_database') FROM pg_database WHERE datname=current_database()"
            )
        )
    ).one()
    prefix = (
        "moulai-operational-local:" if port == 55433 else "moulai-restored-operational:"
    )
    if tuple(row) != (
        "moulai_integrated",
        "moulai_integrated",
        "127.0.0.1",
        port,
        prefix + marker,
    ):
        raise RuntimeError("operational_restore_target_mismatch")
    if await connection.scalar(
        text(
            "SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid()"
        )
    ):
        raise RuntimeError("operational_restore_competing_client")
    if await connection.scalar(
        text(
            "SELECT count(*) FROM pg_namespace WHERE nspname NOT IN ('public','information_schema') AND nspname NOT LIKE 'pg_%'"
        )
    ):
        raise RuntimeError("operational_restore_unreviewed_schema")


# ==============================================
# FULL PUBLIC CATALOGUE AND ROW FINGERPRINT
# Keep constraints, indexes, triggers, types, defaults, function definitions and ACLs distinct from row counts.
# ==============================================


def canonical_text_arrays(*, definition: str) -> str:
    """Normalize only equivalent literal varchar-to-text array casts from pg_dump reparsing.

    Preserve literals, their order, operators and all other casts. Unknown
    expressions remain unchanged and therefore still fail comparison.
    """
    literal = r"'(?:[^']|'')*'"
    item = literal + r"::character varying(?:::text)?"
    items = item + r"(?:, " + item + r")*"
    value = re.sub(
        r"\((" + literal + r"::character varying)\)::text", r"\1::text", definition
    )
    value = re.sub(r"\((ARRAY\[" + items + r"\])\)::text\[\]", r"\1::text[]", value)

    # ==============================================
    # EXACT LITERAL ARRAY REPLACEMENT
    # A varchar array without text coercion is deliberately left unchanged.
    # ==============================================

    def replace(match: re.Match[str]) -> str:
        """Use one spelling only when every element already resolves to text."""
        entries = re.findall(item, match.group("items"))
        if not match.group("cast") and not all(
            entry.endswith("::text") for entry in entries
        ):
            return match.group(0)
        return (
            "ARRAY["
            + ", ".join(
                re.sub(r"::character varying(?:::text)?$", "::text", entry)
                for entry in entries
            )
            + "]"
        )

    return re.sub(
        r"ARRAY\[(?P<items>" + items + r")\](?P<cast>::text\[\])?", replace, value
    )


# ==============================================
# SEMANTIC FINGERPRINT
# Retain exact data and authorization results while normalizing only the documented deparser representation.
# ==============================================


async def fingerprint(*, connection: AsyncConnection) -> dict[str, object]:
    """Hash full deterministic row JSON and catalogue definitions without displaying their potentially private content."""
    revision = await connection.scalar(
        text("SELECT version_num FROM public.alembic_version")
    )
    catalog_queries = {
        "columns": "SELECT c.relname,a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,pg_get_expr(d.adbin,d.adrelid) FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace LEFT JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum WHERE n.nspname='public' AND c.relkind IN ('r','p') AND a.attnum>0 AND NOT a.attisdropped ORDER BY c.relname,a.attnum",
        "constraints": "SELECT c.relname,k.conname,k.convalidated,pg_get_constraintdef(k.oid,true) FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' ORDER BY c.relname,k.conname",
        "indexes": "SELECT tablename,indexname,indexdef FROM pg_indexes WHERE schemaname='public' ORDER BY tablename,indexname",
        "triggers": "SELECT c.relname,t.tgname,t.tgenabled,pg_get_triggerdef(t.oid,true) FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND NOT t.tgisinternal ORDER BY c.relname,t.tgname",
        "functions": "SELECT p.proname,pg_get_function_identity_arguments(p.oid),pg_get_functiondef(p.oid),p.prosecdef,p.proconfig,p.proacl::text,pg_get_userbyid(p.proowner) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.prokind='f' ORDER BY p.proname,pg_get_function_identity_arguments(p.oid)",
        "acls": "SELECT c.relname,c.relkind::text,pg_get_userbyid(c.relowner),pg_get_userbyid(a.grantor),a.grantee,a.privilege_type,a.is_grantable FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace CROSS JOIN LATERAL aclexplode(coalesce(c.relacl,acldefault(CASE WHEN c.relkind='S' THEN 'S'::\"char\" ELSE 'r'::\"char\" END,c.relowner))) a WHERE n.nspname='public' AND c.relkind IN ('r','p','S','v') ORDER BY c.relname,a.grantor,a.grantee,a.privilege_type,a.is_grantable",
    }
    catalog: dict[str, str] = {}
    definitions: dict[str, list[tuple[object, ...]]] = {}
    for key, query in catalog_queries.items():
        rows = [tuple(row) for row in (await connection.execute(text(query))).all()]
        if key in {"constraints", "indexes"}:
            rows = [
                (*row[:-1], canonical_text_arrays(definition=str(row[-1])))
                for row in rows
            ]
        catalog[key] = hashlib.sha256(
            json.dumps(rows, default=str, ensure_ascii=False).encode()
        ).hexdigest()
        if key in {"constraints", "indexes", "acls"}:
            definitions[key] = rows
    tables = (
        await connection.scalars(
            text(
                "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
            )
        )
    ).all()
    rows: dict[str, dict[str, object]] = {}
    for table in tables:
        if re.fullmatch(r"[a-z_][a-z_0-9]*", table) is None:
            raise RuntimeError("operational_restore_identifier_not_admitted")
        row = (
            await connection.execute(
                text(
                    f"SELECT count(*),md5(coalesce(string_agg(to_jsonb(t)::text,chr(10) ORDER BY to_jsonb(t)::text),'')) FROM public.\"{table}\" t"
                )
            )
        ).one()
        rows[table] = {"count": row[0], "digest": row[1]}
    return {
        "revision": revision,
        "catalog": catalog,
        "definitions": definitions,
        "tables": rows,
    }


# ==============================================
# REHEARSAL ALEMBIC CONNECTION
# The restored clone uses the same object owner and ACLs as the source, but a different owned port and database marker.
# ==============================================


def migrate_clone(
    *, connection: Connection, marker: str, target: str = "o420261108"
) -> None:
    """Run only the reviewed O2 to O4 chain through Alembic without editing installed revision metadata."""
    settings = Config()
    settings.set_main_option(
        "script_location", str(ROOT / "alembic_country_base_local")
    )
    settings.set_main_option("version_locations", str(ROOT / "alembic/versions"))
    settings.set_main_option("path_separator", "os")
    settings.attributes.update(
        connection=connection, country_base_marker=marker, restored_operational=True
    )
    if target not in {"o420261108", "o520261111"}:
        raise RuntimeError("operational_restore_target_not_approved")
    command.upgrade(settings, target)


# ==============================================
# FRESH SOURCE ARCHIVE
# The retained source is read only; acquire the host lease before even starting its owned database for backup.
# ==============================================


async def backup_source(
    *,
    configuration: IntegrationConfig,
    archive: Path,
    expected_revision: str = "o220261108",
    expected_tables: int = 93,
) -> dict[str, object]:
    """Reattest the declared revision/count, inventory read-only, then create a complete private archive."""
    engine = create_async_engine(
        configuration.database_url, hide_parameters=True, connect_args={"ssl": False}
    )
    try:
        async with engine.connect() as connection, connection.begin():
            await connection.execute(text("SET TRANSACTION READ ONLY"))
            await attest(
                connection=connection, marker=configuration.instance_id, port=55433
            )
            before = await fingerprint(connection=connection)
            if (
                before["revision"] != expected_revision
                or len(before["tables"]) != expected_tables
            ):
                raise RuntimeError("operational_restore_source_revision_changed")
        native(
            arguments=[
                str(PG / "pg_dump.exe"),
                "-h",
                "127.0.0.1",
                "-p",
                "55433",
                "-U",
                "moulai_integrated",
                "-d",
                "moulai_integrated",
                "-Fc",
                "-f",
                str(archive),
            ],
            environment={
                **os.environ,
                "PGPASSWORD": make_url(configuration.database_url).password or "",
                "PGSSLMODE": "disable",
            },
        )
        listing = native(arguments=[str(PG / "pg_restore.exe"), "--list", str(archive)])
        if b"alembic_version" not in listing or b"ACL" not in listing:
            raise RuntimeError("operational_restore_archive_incomplete")
        async with engine.connect() as connection, connection.begin():
            await connection.execute(text("SET TRANSACTION READ ONLY"))
            await attest(
                connection=connection, marker=configuration.instance_id, port=55433
            )
            if await fingerprint(connection=connection) != before:
                raise RuntimeError("operational_restore_source_changed_during_backup")
        return before
    finally:
        await engine.dispose()


# ==============================================
# REAL RESTORE, FORWARD REPETITION AND RECOVERY
# A successful archive listing is insufficient; compare the restored schema and every table's content.
# ==============================================


async def verify_clone(
    *,
    marker: str,
    password: str,
    bootstrap_password: str,
    archive: Path,
    baseline: dict[str, object],
    output: Path,
    target: str = "o420261108",
) -> dict[str, object]:
    """Restore all source ACLs and owners, prove transactional migration rollback and test actual recovery."""
    bootstrap = await asyncpg.connect(
        host="127.0.0.1",
        port=55434,
        database="postgres",
        user="moulai_bootstrap",
        password=bootstrap_password,
        ssl=False,
    )
    try:
        await bootstrap.execute(
            "CREATE ROLE moulai_integrated LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD '"
            + password
            + "'"
        )
        await bootstrap.execute(
            "CREATE DATABASE moulai_integrated OWNER moulai_integrated TEMPLATE template0 ENCODING 'UTF8' LOCALE_PROVIDER builtin BUILTIN_LOCALE 'C.UTF-8' LC_COLLATE 'C' LC_CTYPE 'C'"
        )
        await bootstrap.execute(
            "COMMENT ON DATABASE moulai_integrated IS 'moulai-restored-operational:"
            + marker
            + "'"
        )
    finally:
        await bootstrap.close()
    environment = {**os.environ, "PGPASSWORD": password, "PGSSLMODE": "disable"}
    address = [
        "-h",
        "127.0.0.1",
        "-p",
        "55434",
        "-U",
        "moulai_integrated",
        "-d",
        "moulai_integrated",
    ]
    native(
        arguments=[
            str(PG / "pg_restore.exe"),
            *address,
            "--single-transaction",
            "--exit-on-error",
            str(archive),
        ],
        environment=environment,
    )
    url = (
        "postgresql+asyncpg://moulai_integrated:"
        + password
        + "@127.0.0.1:55434/moulai_integrated"
    )
    engine = create_async_engine(url, hide_parameters=True, connect_args={"ssl": False})
    try:
        async with engine.connect() as connection:
            await attest(connection=connection, marker=marker, port=55434)
            restored = await fingerprint(connection=connection)
            if restored != baseline:
                (output / "restore-difference.json").write_text(
                    json.dumps({"source": baseline, "restored": restored}, indent=2),
                    encoding="utf-8",
                )
                raise RuntimeError("operational_restored_catalogue_or_data_differ")
            await connection.rollback()
            transaction = await connection.begin()
            await connection.run_sync(
                lambda sync: migrate_clone(
                    connection=sync, marker=marker, target=target
                )
            )
            if (
                await connection.scalar(text("SELECT version_num FROM alembic_version"))
                != target
            ):
                raise RuntimeError("operational_clone_migration_not_complete")
            await transaction.rollback()
            if await fingerprint(connection=connection) != baseline:
                raise RuntimeError("operational_clone_migration_rollback_not_exact")
            await connection.rollback()
            async with connection.begin():
                await connection.run_sync(
                    lambda sync: migrate_clone(
                        connection=sync, marker=marker, target=target
                    )
                )
            after = await fingerprint(connection=connection)
            if (
                after["revision"] != target
                or len(after["tables"])
                != {"o420261108": 101, "o520261111": 103}[target]
            ):
                raise RuntimeError("operational_clone_final_catalogue_incomplete")
            for table, value in baseline["tables"].items():
                if (
                    table
                    not in (
                        {"alembic_version", "subscription_pricing_config"}
                        if target == "o420261108"
                        else {"alembic_version"}
                    )
                    and after["tables"].get(table) != value
                ):
                    raise RuntimeError("operational_clone_changed_preexisting_rows")
        await engine.dispose()
        # Generate the complete recovery script privately. Public is the only
        # application schema, verified above. The database and its marker remain.
        restore_sql = archive.with_suffix(".sql")
        native(
            arguments=[str(PG / "pg_restore.exe"), "-f", str(restore_sql), str(archive)]
        )
        recovery = archive.with_name("recovery.sql")
        recovery.write_bytes(
            b"DROP SCHEMA public CASCADE;\nCREATE SCHEMA public AUTHORIZATION pg_database_owner;\n"
            + restore_sql.read_bytes()
        )
        native(
            arguments=[
                str(PG / "psql.exe"),
                *address,
                "--single-transaction",
                "-v",
                "ON_ERROR_STOP=1",
                "-f",
                str(recovery),
            ],
            environment=environment,
        )
        async with engine.connect() as connection:
            await attest(connection=connection, marker=marker, port=55434)
            if await fingerprint(connection=connection) != baseline:
                raise RuntimeError("operational_clone_recovery_not_exact")
        return {
            "archive_restored": True,
            "catalogue_and_rows_identical": True,
            "transactional_rollback_identical": True,
            "forward": after,
            "recovery_restored_original": True,
        }
    finally:
        await engine.dispose()


# ==============================================
# EXCLUSIVE LOCAL REHEARSAL LIFECYCLE
# Start and stop only the retained marked database and this new disposable cluster, while the application stays stopped.
# ==============================================


def verified_restoration_proof(
    *, configuration: IntegrationConfig, target: str = "o420261108"
) -> dict[str, object]:
    """Admit only this source's verified immutable archive and the exact migration sources rehearsed with it."""
    root = (
        OUTPUT if target == "o420261108" else ROOT / "artifacts/saas-documents-20261111"
    )
    if target not in {"o420261108", "o520261111"}:
        raise RuntimeError("operational_restore_target_not_approved")
    pointer = json.loads((root / "restore-proof.json").read_text(encoding="utf-8"))
    path = Path(pointer["report"]).resolve()
    if (
        not path.is_relative_to(root.resolve())
        or hashlib.sha256(path.read_bytes()).hexdigest() != pointer["sha256"]
    ):
        raise RuntimeError("operational_restore_proof_integrity_failed")
    report = json.loads(path.read_text(encoding="utf-8"))
    archive = Path(report["backup_reference"]).resolve()
    if (
        report["status"] != "PASS"
        or report["forward"]["revision"] != target
        or report["source_instance"] != configuration.instance_id
        or report["source_migrated"] is not False
        or any(
            report.get(key) is not True
            for key in (
                "archive_restored",
                "catalogue_and_rows_identical",
                "transactional_rollback_identical",
                "recovery_restored_original",
            )
        )
        or not archive.is_relative_to(
            (configuration.directory / "private/backups").resolve()
        )
        or hashlib.sha256(archive.read_bytes()).hexdigest() != report["backup_sha256"]
    ):
        raise RuntimeError("operational_restore_proof_not_applicable")
    for relative, expected in report["migration_sources"].items():
        source = (ROOT / relative).resolve()
        if (
            not source.is_relative_to(ROOT)
            or hashlib.sha256(source.read_bytes()).hexdigest() != expected
        ):
            raise RuntimeError("operational_restore_migration_sources_changed")
    return report


# ==============================================
# EXPLICIT LOCAL PREPARATION ENTRY
# Preparation never authorizes source writes by itself; the separate guarded migration command consumes this evidence.
# ==============================================


def main() -> int:
    """Create a private fresh backup and a public nonsensitive restoration report; never migrate the source."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target", choices=("o420261108", "o520261111"), default="o420261108"
    )
    parser.add_argument("--recover-o5", action="store_true")
    options = parser.parse_args()
    target = options.target
    if options.recover_o5 and target != "o520261111":
        parser.error("O5 recovery requires the exact O5 target")
    root = (
        ROOT / "artifacts/staging-o5-20261111/recovery"
        if options.recover_o5
        else (
            OUTPUT
            if target == "o420261108"
            else ROOT / "artifacts/saas-documents-20261111"
        )
    )
    configuration = resolve_instance(supplied=None)
    marker = uuid4().hex
    output = root / ("restore-" + marker)
    private = configuration.directory / "private" / "backups" / (target + "-" + marker)
    private.mkdir(parents=True)
    output.mkdir(parents=True)
    archive = private / ("before-" + target + ".dump")
    clone_data = output / "postgres-data"
    sys.addaudithook(RestorationNetworkGuard())
    with local_host_lease(directory=configuration.directory):
        for port in (5180, 5582, 55433, 55434):
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", port))
        bootstrap_password = secrets.token_hex(32)
        password_file = private / "clone-bootstrap-password"
        password_file.write_text(bootstrap_password, encoding="ascii")
        try:
            native(
                arguments=[
                    str(PG / "initdb.exe"),
                    "-D",
                    str(clone_data),
                    "-U",
                    "moulai_bootstrap",
                    "--encoding=UTF8",
                    "--locale=C",
                    "--auth-local=trust",
                    "--auth-host=scram-sha-256",
                    "--pwfile=" + str(password_file),
                ]
            )
        finally:
            password_file.unlink(missing_ok=True)
        source_started = clone_started = False
        try:
            native(
                arguments=[
                    str(PG / "pg_ctl.exe"),
                    "-D",
                    str(configuration.directory / "postgres-data"),
                    "-l",
                    str(private / "source.log"),
                    "-o",
                    "-h 127.0.0.1 -p 55433 -c log_min_error_statement=panic",
                    "-w",
                    "start",
                ]
            )
            source_started = True
            baseline = asyncio.run(
                backup_source(
                    configuration=configuration,
                    archive=archive,
                    expected_revision=(
                        "o520261111"
                        if options.recover_o5
                        else "o220261108" if target == "o420261108" else "o420261108"
                    ),
                    expected_tables=(
                        103
                        if options.recover_o5
                        else 93 if target == "o420261108" else 101
                    ),
                )
            )
            native(
                arguments=[
                    str(PG / "pg_ctl.exe"),
                    "-D",
                    str(clone_data),
                    "-l",
                    str(private / "clone.log"),
                    "-o",
                    "-h 127.0.0.1 -p 55434 -c log_min_error_statement=panic",
                    "-w",
                    "start",
                ]
            )
            clone_started = True
            result = asyncio.run(
                verify_clone(
                    marker=marker,
                    password=secrets.token_hex(32),
                    bootstrap_password=bootstrap_password,
                    archive=archive,
                    baseline=baseline,
                    output=output,
                    target=target,
                )
            )
            hashes = {
                str(path.relative_to(ROOT)): hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
                for path in (
                    ROOT / "migration_support/country_base_o3.py",
                    ROOT / "migration_support/billing_country_o4.py",
                    ROOT / "alembic/versions/2026_11_08_country_base_o3.py",
                    ROOT / "alembic/versions/2026_11_08_billing_country_o4.py",
                    ROOT / "migration_support/saas_documents_o5.py",
                    ROOT / "alembic/versions/2026_11_11_saas_documents_o5.py",
                    ROOT / "alembic_country_base_local/env.py",
                    ROOT / "alembic_operational_local/env.py",
                )
            }
            report = {
                "status": "PASS",
                "source": "127.0.0.1:55433/moulai_integrated",
                "clone": "127.0.0.1:55434/moulai_integrated",
                "source_instance": configuration.instance_id,
                "clone_marker": marker,
                "backup_reference": str(archive),
                "backup_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                "source_before": baseline,
                "source_migrated": False,
                "recovery_mode": (
                    "retained-O5-including-document-history"
                    if options.recover_o5
                    else "pre-transition-parent"
                ),
                "migration_sources": hashes,
                **result,
            }
            (output / "summary.json").write_text(
                json.dumps(report, indent=2), encoding="utf-8"
            )
            (root / "restore-proof.json").write_text(
                json.dumps(
                    {
                        "report": str(output / "summary.json"),
                        "sha256": hashlib.sha256(
                            (output / "summary.json").read_bytes()
                        ).hexdigest(),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            print(
                json.dumps(
                    {
                        "status": "PASS",
                        "report": str(output / "summary.json"),
                        "source_migrated": False,
                    }
                )
            )
            return 0
        finally:
            if clone_started:
                native(
                    arguments=[
                        str(PG / "pg_ctl.exe"),
                        "-D",
                        str(clone_data),
                        "-m",
                        "fast",
                        "-w",
                        "stop",
                    ]
                )
            if source_started:
                native(
                    arguments=[
                        str(PG / "pg_ctl.exe"),
                        "-D",
                        str(configuration.directory / "postgres-data"),
                        "-m",
                        "fast",
                        "-w",
                        "stop",
                    ]
                )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        OSError,
        RuntimeError,
        ValueError,
        subprocess.SubprocessError,
        asyncpg.PostgresError,
        SQLAlchemyError,
    ) as error:
        code = str(error) if re.fullmatch(r"[a-z_]{1,120}", str(error)) else None
        print(
            json.dumps(
                {"status": "STOPPED", "type": type(error).__name__, "code": code}
            ),
            file=sys.stderr,
        )
        raise SystemExit(1) from None
