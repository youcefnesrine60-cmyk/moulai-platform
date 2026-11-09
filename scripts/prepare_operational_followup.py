# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# O4 PAYMENT POLICY RESTORATION AND LOCAL CUTOVER
# Restore a fresh private archive, rehearse one approved JSON policy update, then apply only to the unchanged owned review.
# ==============================================

"""No schema migration, remote URL, synthetic tariff, permission grant or historical rewrite."""

from __future__ import annotations

# isort: split
# ==============================================
# OWNED LOCAL DEPENDENCIES
# Reuse source attestation, full semantic fingerprints and checked native subprocesses.
# ==============================================

import asyncio
import hashlib
import json
import os
import secrets
import socket
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import asyncpg
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    create_async_engine,
)

from app.integration.config import IntegrationConfig
from app.integration.local_setup import PG
from app.integration.process import local_host_lease
from scripts.prepare_operational_o4 import (
    RestorationNetworkGuard,
    attest,
    backup_source,
    fingerprint,
    native,
)
from scripts.run_operational_local import resolve_instance

# ==============================================
# APPROVED POLICY INITIALIZATION
# This source identifies the owner's approved rates; runtime calculations read only the database.
# ==============================================

RATES = {"electronic": "-0.02", "cash": "0.02"}


# ==============================================
# STAGE THE APPROVED POLICY
# Extend only the existing configuration and refuse conflicting values.
# ==============================================


async def stage_policy(*, connection: AsyncConnection) -> None:
    """Initialize missing payment rates once; refuse contradictory existing configuration."""
    policy = await connection.scalar(
        text("SELECT policies FROM subscription_pricing_config WHERE id=1 FOR UPDATE")
    )
    if not isinstance(policy, dict):
        raise TypeError("payment_policy_missing")
    if "payment_adjustment_rates" in policy:
        if policy["payment_adjustment_rates"] != RATES:
            raise RuntimeError("payment_policy_conflict_requires_review")
        return
    policy = {
        **policy,
        "payment_adjustment_rates": RATES,
        "payment_adjustment_source": "Owner-approved electronic reduction and cash surcharge; confirmed 2026-11-09",
    }
    await connection.execute(
        text(
            "UPDATE subscription_pricing_config SET policies=CAST(:p AS json) WHERE id=1"
        ),
        {"p": json.dumps(policy)},
    )


# ==============================================
# PRIVATE ARCHIVE RESTORE AND POLICY REHEARSAL
# A clone must match every source table and catalog category before any forward update.
# ==============================================


async def rehearse(
    *,
    configuration: IntegrationConfig,
    marker: str,
    archive: Path,
    baseline: dict[str, object],
    password: str,
    bootstrap: str,
) -> dict[str, object]:
    """Restore owners and ACLs, verify exact content, then prove rollback and unchanged historical rows."""
    bootstrap_connection = await asyncpg.connect(
        host="127.0.0.1",
        port=55434,
        database="postgres",
        user="moulai_bootstrap",
        password=bootstrap,
        ssl=False,
    )
    try:
        await bootstrap_connection.execute(
            "CREATE ROLE moulai_integrated LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD '"
            + password
            + "'"
        )
        await bootstrap_connection.execute(
            "CREATE DATABASE moulai_integrated OWNER moulai_integrated TEMPLATE template0 ENCODING 'UTF8' LOCALE_PROVIDER builtin BUILTIN_LOCALE 'C.UTF-8' LC_COLLATE 'C' LC_CTYPE 'C'"
        )
        await bootstrap_connection.execute(
            "COMMENT ON DATABASE moulai_integrated IS 'moulai-restored-operational:"
            + marker
            + "'"
        )
    finally:
        await bootstrap_connection.close()
    native(
        arguments=[
            str(PG / "pg_restore.exe"),
            "-h",
            "127.0.0.1",
            "-p",
            "55434",
            "-U",
            "moulai_integrated",
            "-d",
            "moulai_integrated",
            "--single-transaction",
            "--exit-on-error",
            str(archive),
        ],
        environment={**os.environ, "PGPASSWORD": password, "PGSSLMODE": "disable"},
    )
    url = make_url(configuration.database_url).set(port=55434, password=password)
    engine = create_async_engine(url, hide_parameters=True, connect_args={"ssl": False})
    try:
        async with engine.connect() as connection:
            await attest(connection=connection, marker=marker, port=55434)
            if await fingerprint(connection=connection) != baseline:
                raise RuntimeError("followup_restoration_mismatch")
            await connection.rollback()
            async with connection.begin():
                transaction = await connection.begin_nested()
                await stage_policy(connection=connection)
                await transaction.rollback()
                if await fingerprint(connection=connection) != baseline:
                    raise RuntimeError("followup_rollback_mismatch")
            async with connection.begin():
                await stage_policy(connection=connection)
            after = await fingerprint(connection=connection)
            if after["catalog"] != baseline["catalog"]:
                raise RuntimeError("followup_unexpected_schema_change")
            for table, values in baseline["tables"].items():
                if (
                    table != "subscription_pricing_config"
                    and after["tables"][table] != values
                ):
                    raise RuntimeError("followup_historical_rows_changed")
            return {
                "archive_restored": True,
                "catalog_and_rows_exact": True,
                "rollback_exact": True,
                "other_tables_unchanged": True,
                "after": after,
            }
    finally:
        await engine.dispose()


# ==============================================
# ATTESTED SOURCE POLICY COMMIT
# Refuse any writer, source drift or proof mismatch instead of retrying or correcting automatically.
# ==============================================


async def apply_policy(
    *, configuration: IntegrationConfig, baseline: dict[str, object]
) -> None:
    """Apply only the rehearsed JSON change while the application host lease is held."""
    engine = create_async_engine(
        configuration.database_url, hide_parameters=True, connect_args={"ssl": False}
    )
    try:
        async with engine.begin() as connection:
            await attest(
                connection=connection, marker=configuration.instance_id, port=55433
            )
            if await fingerprint(connection=connection) != baseline:
                raise RuntimeError("followup_source_changed")
            await stage_policy(connection=connection)
    finally:
        await engine.dispose()


# ==============================================
# EXCLUSIVE LOCAL PROCESS LIFECYCLE
# Start and stop only the owned source and fresh clone; never borrow a running writer.
# ==============================================


def main() -> int:
    """Create verifiable private backup/rehearsal evidence before the authorized local update."""
    configuration = resolve_instance(supplied=None)
    marker = uuid4().hex
    private = configuration.directory / "private/backups" / ("followup-" + marker)
    private.mkdir(parents=True)
    output = ROOT / "artifacts/operational-followup-20261109" / marker
    output.mkdir(parents=True)
    data = private / "postgres-data"
    archive = private / "before-policy.dump"
    bootstrap, password = secrets.token_hex(32), secrets.token_hex(32)
    password_file = private / "bootstrap-password"
    sys.addaudithook(RestorationNetworkGuard())
    with local_host_lease(directory=configuration.directory):
        for port in (5180, 5582, 55433, 55434):
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", port))
        password_file.write_text(bootstrap, encoding="ascii")
        try:
            native(
                arguments=[
                    str(PG / "initdb.exe"),
                    "-D",
                    str(data),
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
        started = []
        try:
            for directory, port in [
                (configuration.directory / "postgres-data", 55433),
                (data, 55434),
            ]:
                native(
                    arguments=[
                        str(PG / "pg_ctl.exe"),
                        "-D",
                        str(directory),
                        "-l",
                        str(private / f"postgres-{port}.log"),
                        "-o",
                        f"-h 127.0.0.1 -p {port} -c log_min_error_statement=panic",
                        "-w",
                        "start",
                    ]
                )
                started.append(directory)
            baseline = asyncio.run(
                backup_source(
                    configuration=configuration,
                    archive=archive,
                    expected_revision="o420261108",
                    expected_tables=101,
                )
            )
            proof = asyncio.run(
                rehearse(
                    configuration=configuration,
                    marker=marker,
                    archive=archive,
                    baseline=baseline,
                    password=password,
                    bootstrap=bootstrap,
                )
            )
            asyncio.run(apply_policy(configuration=configuration, baseline=baseline))
            report = {
                "status": "PASS",
                "target": "127.0.0.1:55433/moulai_integrated",
                "revision": "o420261108",
                "backup": str(archive),
                "backup_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                "rehearsal": proof,
                "schema_migration": False,
                "remote_write": False,
            }
            (output / "summary.json").write_text(
                json.dumps(report, indent=2, default=str), encoding="utf-8"
            )
            print(
                json.dumps({"status": "PASS", "report": str(output / "summary.json")})
            )
        finally:
            for directory in reversed(started):
                native(
                    arguments=[
                        str(PG / "pg_ctl.exe"),
                        "-D",
                        str(directory),
                        "-m",
                        "fast",
                        "-w",
                        "stop",
                    ]
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
