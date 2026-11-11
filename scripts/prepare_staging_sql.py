# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# VERSIONED STAGING SQL FROM THE REAL MAIN HISTORY
# Capture only mutations executed by unchanged Alembic revisions on an empty
# disposable local cluster, then replay both stages into a fresh restoration.
# ==============================================

"""Produce credential-free artifacts for Neon MCP, without transporting a password."""

from __future__ import annotations

# isort: split
# ==============================================
# LOCAL RECONSTRUCTION DEPENDENCIES
# The existing bootstrap owns its DDL and Alembic owns every recorded revision write.
# ==============================================

import argparse
import asyncio
import hashlib
import json
import os
import re
import secrets
import socket
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import asyncpg
from alembic.config import Config
from sqlalchemy import (
    event,
    literal,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import (
    Connection,
    Engine,
    ExecutionContext,
)
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import command
from scripts.rehearse_country_base import (
    CountryBaseNetworkGuard,
    initialize,
)
from scripts.staging_sql_support import (
    OUTPUT,
    PG,
    child,
    fingerprint,
)

# ==============================================
# LIMITED RUNTIME AUTHORITY REHEARSAL
# Test remote target refusal and local privileges without changing any remote role.
# ==============================================


async def verify_o5_runtime(*, bootstrap_password: str, output: Path) -> None:
    """Check the exact runtime grant body on a disposable local O5 database only.

    The remote identity guard must reject this local server. Only the grant body
    is then tested as a separate local rehearsal, never by relaxing its guard.
    """
    connection = await asyncpg.connect(
        host="127.0.0.1",
        port=55434,
        user="moulai_bootstrap",
        password=bootstrap_password,
        database="moulai_base_rehearsal",
        ssl=False,
    )
    try:
        script = (ROOT / "deploy/staging/provision-runtime.sql").read_text(
            encoding="utf-8"
        )
        async with connection.transaction():
            try:
                async with connection.transaction():
                    await connection.execute(script)
            except asyncpg.RaiseError as error:
                if error.message != "staging_runtime_target_refused":
                    raise
            else:
                raise RuntimeError("staging_remote_guard_accepted_local_target")
            await connection.execute(
                "CREATE ROLE moulai_staging_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE"
            )
            await connection.execute(script.split("END $attest$;", 1)[1])
            await connection.execute("SET LOCAL ROLE moulai_staging_app")
            for table in ("subscription_documents", "subscription_document_events"):
                for privilege in ("SELECT", "INSERT"):
                    if not await connection.fetchval(
                        "SELECT has_table_privilege(current_user,$1,$2)",
                        table,
                        privilege,
                    ):
                        raise RuntimeError("staging_o5_runtime_append_grant_missing")
                if not await connection.fetchval(
                    "SELECT has_sequence_privilege(current_user,pg_get_serial_sequence($1,'id'),'USAGE')",
                    table,
                ):
                    raise RuntimeError("staging_o5_runtime_sequence_grant_missing")
                await connection.fetch("SELECT * FROM public." + table + " LIMIT 1")
            forbidden = (
                "UPDATE public.subscription_documents SET version=version WHERE false",
                "UPDATE public.subscription_document_events SET event=event WHERE false",
                "DELETE FROM public.subscription_documents WHERE false",
                "DELETE FROM public.subscription_document_events WHERE false",
                "TRUNCATE public.subscription_documents",
                "TRUNCATE public.subscription_document_events",
                "UPDATE public.alembic_version SET version_num=version_num WHERE false",
                "CREATE TABLE public.runtime_forbidden(id integer)",
            )
            for statement in forbidden:
                try:
                    async with connection.transaction():
                        await connection.execute(statement)
                except asyncpg.InsufficientPrivilegeError:
                    continue
                raise RuntimeError("staging_runtime_forbidden_operation_admitted")
            if await connection.fetchval(
                "SELECT pg_has_role(current_user,'moulai_base_rehearsal','MEMBER')"
            ):
                raise RuntimeError("staging_runtime_inherits_owner")
        (output / "runtime-proof.json").write_text(
            json.dumps(
                {
                    "status": "PASS",
                    "remote_guard_rejected_local": True,
                    "grant_body_sha256": hashlib.sha256(
                        script.split("END $attest$;", 1)[1].encode()
                    ).hexdigest(),
                    "select_insert_document_tables": True,
                    "sequence_usage": True,
                    "forbidden_operations_refused": len(forbidden),
                    "runtime_not_owner": True,
                    "scope": "disposable local PostgreSQL only",
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    finally:
        await connection.close()


# ==============================================
# EXECUTED MAIN CHAIN AND SQL REPLAY
# Keep O4 and O5 observations separate so their row preservation is measurable.
# ==============================================


async def prepare(
    *,
    password: str,
    bootstrap_password: str,
    marker: str,
    target_revision: str = "o420261108",
    output: Path = OUTPUT,
    runtime_checks: bool = False,
) -> None:
    """Run the main graph, retain exact mutation SQL, and prove backup replay equality."""
    if target_revision not in {"o420261108", "o520261111"}:
        raise ValueError("staging_sql_revision_not_approved")
    phases: dict[str, list[str]] = {"bootstrap": [], "transition": []}
    if target_revision == "o520261111":
        phases["documents"] = []
    phase = "bootstrap"

    # ==============================================
    # SQLALCHEMY OBSERVATION CALLBACK
    # Framework signature stays positional and never records query results or secrets.
    # ==============================================

    def capture(
        _connection: Connection,
        _cursor: object,
        statement: str,
        parameters: object,
        _context: ExecutionContext,
        _executemany: bool,
    ) -> None:
        """Record main migration mutations only; reads and driver setup stay unrecorded."""
        nonlocal phase
        first = statement.lstrip().split(None, 1)[0].upper()
        if first not in {
            "CREATE",
            "ALTER",
            "DROP",
            "INSERT",
            "UPDATE",
            "DELETE",
            "DO",
            "GRANT",
            "REVOKE",
            "COMMENT",
            "LOCK",
        }:
            return
        if parameters:
            compiled = _context.compiled
            if compiled is None or not compiled.positiontup:
                raise RuntimeError("staging_typed_sql_compilation_required")
            rows = parameters if _executemany else [parameters]
            for row in rows:
                rendered = []
                for index, value in enumerate(row):
                    name = compiled.positiontup[index]
                    rendered.append(
                        str(
                            literal(value, type_=compiled.binds[name].type).compile(
                                dialect=postgresql.dialect(),
                                compile_kwargs={"literal_binds": True},
                            )
                        )
                    )
                phases[phase].append(
                    re.sub(
                        r"\$(\d+)",
                        lambda match, values=tuple(rendered): values[int(match[1]) - 1],
                        statement,
                    )
                )
        else:
            phases[phase].append(statement)
        if "version_num='s1a20261028'" in statement.replace(" ", ""):
            phase = "transition"
        if (
            target_revision == "o520261111"
            and "version_num='o420261108'" in statement.replace(" ", "")
        ):
            phase = "documents"

    url = (
        "postgresql+asyncpg://moulai_base_rehearsal:"
        + password
        + "@127.0.0.1:55434/moulai_base_rehearsal"
    )
    event.listen(Engine, "before_cursor_execute", capture)
    try:
        await initialize(
            password=password,
            bootstrap_password=bootstrap_password,
            marker=marker,
            url=url,
            operational_history=True,
        )
        engine = create_async_engine(
            url, hide_parameters=True, connect_args={"ssl": False}
        )
        try:
            async with engine.begin() as connection:

                # ==============================================
                # COMPLETE THE SELECTED MAIN REVISION
                # Preserve every historical source and capture O5 separately from O4.
                # ==============================================

                def forward(sync: Connection) -> None:
                    """Let Alembic produce the approved delta on the actual O2 schema."""
                    config = Config()
                    config.set_main_option(
                        "script_location", str(ROOT / "alembic_country_base_local")
                    )
                    config.set_main_option(
                        "version_locations", str(ROOT / "alembic/versions")
                    )
                    config.attributes.update(
                        connection=sync, country_base_marker=marker
                    )
                    command.upgrade(config, target_revision)

                await connection.run_sync(forward)
        finally:
            await engine.dispose()
    finally:
        event.remove(Engine, "before_cursor_execute", capture)
    if phase != (
        "documents" if target_revision == "o520261111" else "transition"
    ) or not all(phases.values()):
        raise RuntimeError("staging_s1a_capture_boundary_missing")
    admin = await asyncpg.connect(
        host="127.0.0.1",
        port=55434,
        user="moulai_bootstrap",
        password=bootstrap_password,
        database="postgres",
        ssl=False,
    )
    try:
        await admin.execute(
            "CREATE DATABASE moulai_staging_restore OWNER moulai_base_rehearsal"
        )
    finally:
        await admin.close()
    source = await asyncpg.connect(
        host="127.0.0.1",
        port=55434,
        user="moulai_base_rehearsal",
        password=password,
        database="moulai_base_rehearsal",
        ssl=False,
    )
    restored = await asyncpg.connect(
        host="127.0.0.1",
        port=55434,
        user="moulai_base_rehearsal",
        password=password,
        database="moulai_staging_restore",
        ssl=False,
    )
    try:
        observations = {}
        for name, statements in phases.items():
            async with restored.transaction():
                for statement in statements:
                    await restored.execute(statement)
            observed = await fingerprint(connection=restored)
            expected_revision = {
                "bootstrap": "s1a20261028",
                "transition": "o420261108",
                "documents": "o520261111",
            }[name]
            if observed["revision"] != expected_revision:
                raise RuntimeError("staging_sql_replay_revision_mismatch")
            observations[name] = observed
            if name == "documents" and any(
                observed["tables"].get(table) != value
                for table, value in observations["transition"]["tables"].items()
                if table != "alembic_version"
            ):
                raise RuntimeError("staging_o5_changed_existing_o4_rows")
            (output / ("sql-" + name + ".json")).write_text(
                json.dumps(statements, indent=2), encoding="utf-8"
            )
            (output / (name + ".sql")).write_text(
                ";\n\n".join(s.rstrip().rstrip(";") for s in statements) + ";\n",
                encoding="utf-8",
            )
        original = await fingerprint(connection=source)
        final = observations[
            "documents" if target_revision == "o520261111" else "transition"
        ]
        differences = [
            name
            for name, value in original["tables"].items()
            if value != final["tables"][name]
        ]
        (output / "sql-replay-difference.json").write_text(
            json.dumps(
                {
                    "catalogue_equal": original["catalogue"] == final["catalogue"],
                    "tables": differences,
                    "original": original,
                    "replayed": final,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        if original["catalogue"] != final["catalogue"]:
            raise RuntimeError("staging_main_chain_and_sql_catalogues_differ")
        clocks = {}
        reference_tables = {
            "branch_pricing",
            "loyalty_discounts",
            "multi_restaurant_discounts",
            "permissions",
            "roles",
            "subscription_base_prices",
            "subscription_pricing_config",
        }
        for table in differences:
            if table not in reference_tables:
                raise RuntimeError("staging_unexpected_replayed_data_difference")
            left = [
                json.loads(row[0])
                for row in await source.fetch(
                    'SELECT row_to_json(t)::text FROM public."'
                    + table
                    + '" t ORDER BY id'
                )
            ]
            right = [
                json.loads(row[0])
                for row in await restored.fetch(
                    'SELECT row_to_json(t)::text FROM public."'
                    + table
                    + '" t ORDER BY id'
                )
            ]
            if len(left) != len(right):
                raise RuntimeError("staging_replayed_reference_count_difference")
            columns = {
                key
                for a, b in zip(left, right, strict=True)
                for key in a
                if a[key] != b[key]
            }
            allowed = {"created_at", "updated_at", "recorded_at"} | (
                {"effective_from"} if table == "subscription_base_prices" else set()
            )
            if not columns <= allowed:
                raise RuntimeError("staging_replayed_reference_value_difference")
            clocks[table] = sorted(columns)
        provenance = {
            "status": "PASS",
            "main_history_executed": True,
            "bootstrap": "main-bootstrap-v1",
            "no_stamp": True,
            "no_fixture_seed": True,
            "local_sql_reconstruction_verified": True,
            "catalogue_exact": True,
            "all_nonclock_reference_values_exact": True,
            "initialization_clock_differences": clocks,
            "phase_counts": {k: len(v) for k, v in phases.items()},
            "revision": target_revision,
            "o4_rows_preserved": target_revision == "o520261111",
            "observations": observations,
            "artifacts": {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in [
                    *(output / (name + ".sql") for name in phases),
                    *(output / ("sql-" + name + ".json") for name in phases),
                ]
            },
        }
        (output / "sql-provenance.json").write_text(
            json.dumps(provenance, indent=2), encoding="utf-8"
        )
        if runtime_checks:
            await verify_o5_runtime(
                bootstrap_password=bootstrap_password, output=output
            )
        print(
            json.dumps(
                {
                    "status": "PASS",
                    "phase_counts": provenance["phase_counts"],
                    "output": str(output),
                }
            )
        )
    finally:
        await source.close()
        await restored.close()


# ==============================================
# ONE OWNED NATIVE CLUSTER
# Refuse an occupied port and retain the isolated data directory as evidence.
# ==============================================


def main() -> int:
    """Prepare SQL locally; never connect to any remote database or read .env."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target", choices=("o420261108", "o520261111"), default="o420261108"
    )
    parser.add_argument("--verify-runtime", action="store_true")
    options = parser.parse_args()
    if options.verify_runtime and options.target != "o520261111":
        parser.error("runtime rehearsal requires O5")
    marker = uuid4().hex
    output = (
        OUTPUT
        if options.target == "o420261108"
        else ROOT / "artifacts/staging-o5-20261111" / "rehearsals" / marker
    )
    if options.target == "o520261111" and (output / "sql-provenance.json").exists():
        raise RuntimeError("staging_o5_preparation_already_recorded")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 55434))
    sys.addaudithook(CountryBaseNetworkGuard())
    private = output / "private" / ("sql-build-" + marker)
    private.mkdir(parents=True)
    data = private / "postgres"
    password, bootstrap_password = secrets.token_hex(32), secrets.token_hex(32)
    password_file = private / "initial-password"
    password_file.write_text(bootstrap_password, encoding="ascii")
    environment = dict(os.environ, PGPASSWORD=bootstrap_password)
    started = False
    try:
        child(
            arguments=[
                str(PG / "initdb.exe"),
                "-D",
                str(data),
                "-U",
                "moulai_bootstrap",
                "--pwfile=" + str(password_file),
                "--auth=scram-sha-256",
                "--encoding=UTF8",
                "--locale=C",
            ],
            environment=environment,
        )
        password_file.unlink()
        child(
            arguments=[
                str(PG / "pg_ctl.exe"),
                "-D",
                str(data),
                "-l",
                str(private / "postgres.log"),
                "-o",
                "-h 127.0.0.1 -p 55434 -c timezone=UTC -c log_min_error_statement=panic",
                "-w",
                "start",
            ],
            environment=environment,
        )
        started = True
        asyncio.run(
            prepare(
                password=password,
                bootstrap_password=bootstrap_password,
                marker=marker,
                target_revision=options.target,
                output=output,
                runtime_checks=options.verify_runtime,
            )
        )
        return 0
    finally:
        if started:
            child(
                arguments=[
                    str(PG / "pg_ctl.exe"),
                    "-D",
                    str(data),
                    "-m",
                    "fast",
                    "-w",
                    "stop",
                ],
                environment=environment,
            )


if __name__ == "__main__":
    raise SystemExit(main())
