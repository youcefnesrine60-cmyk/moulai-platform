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
from scripts.rehearse_country_base import initialize
from scripts.staging_sql_support import (
    OUTPUT,
    PG,
    child,
    fingerprint,
)

# ==============================================
# REAL DDL CAPTURE AND REPLAY
# Compile bound mutations with SQLAlchemy types instead of interpolating values.
# ==============================================


async def prepare(*, password: str, bootstrap_password: str, marker: str) -> None:
    """Run the main graph, retain exact mutation SQL, and prove backup replay equality."""
    phases: dict[str, list[str]] = {"bootstrap": [], "transition": []}
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
                # COMPLETE O4 THROUGH THE LOCAL ATTESTED ENVIRONMENT
                # Preserve every historical source and connection guard.
                # ==============================================

                def forward(sync: Connection) -> None:
                    """Let Alembic produce the O3/O4 delta on the actual O2 schema."""
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
                    command.upgrade(config, "o420261108")

                await connection.run_sync(forward)
        finally:
            await engine.dispose()
    finally:
        event.remove(Engine, "before_cursor_execute", capture)
    if phase != "transition" or not all(phases.values()):
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
            expected_revision = "s1a20261028" if name == "bootstrap" else "o420261108"
            if observed["revision"] != expected_revision:
                raise RuntimeError("staging_sql_replay_revision_mismatch")
            observations[name] = observed
            (OUTPUT / ("sql-" + name + ".json")).write_text(
                json.dumps(statements, indent=2), encoding="utf-8"
            )
            (OUTPUT / (name + ".sql")).write_text(
                ";\n\n".join(s.rstrip().rstrip(";") for s in statements) + ";\n",
                encoding="utf-8",
            )
        original = await fingerprint(connection=source)
        differences = [
            name
            for name, value in original["tables"].items()
            if value != observations["transition"]["tables"][name]
        ]
        (OUTPUT / "sql-replay-difference.json").write_text(
            json.dumps(
                {
                    "catalogue_equal": original["catalogue"]
                    == observations["transition"]["catalogue"],
                    "tables": differences,
                    "original": original,
                    "replayed": observations["transition"],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        if original["catalogue"] != observations["transition"]["catalogue"]:
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
            "observations": observations,
            "artifacts": {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in [
                    OUTPUT / "bootstrap.sql",
                    OUTPUT / "transition.sql",
                    OUTPUT / "sql-bootstrap.json",
                    OUTPUT / "sql-transition.json",
                ]
            },
        }
        (OUTPUT / "sql-provenance.json").write_text(
            json.dumps(provenance, indent=2), encoding="utf-8"
        )
        print(
            json.dumps({"status": "PASS", "phase_counts": provenance["phase_counts"]})
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
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 55434))
    marker = uuid4().hex
    private = OUTPUT / "private" / ("sql-build-" + marker)
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
                password=password, bootstrap_password=bootstrap_password, marker=marker
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
