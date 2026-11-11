# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# ISOLATED OPERATIONAL HISTORY AND COUNTRY REHEARSALS
# Reconstruct O2, O3 or O4 on a fresh owned PostgreSQL cluster, without using the retained application's port.
# ==============================================

"""Dedicated port 55434; no retained review mutation, Keycloak, Neon or .env edits."""

from __future__ import annotations

# isort: split
# ==============================================
# LOCAL PROCESS AND TRANSACTION DEPENDENCIES
# Generate temporary credentials privately and allow Python connections only to this test server.
# ==============================================

import argparse
import asyncio
import json
import os
import secrets
import socket
import subprocess
import sys
import tempfile
from contextlib import (
    redirect_stderr,
    redirect_stdout,
)
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import asyncpg
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
)

from alembic import command
from migration_support.main_bootstrap import load_bootstrap_statements
from scripts.run_offline_api_tests import OfflineNetworkGuard

PG = Path(r"C:\Program Files\PostgreSQL\18\bin")
PORT = 55434
DATABASE = "moulai_base_rehearsal"

# ==============================================
# LOOPBACK-ONLY TEST TRANSPORT
# Keep DNS, every remote endpoint and both existing review database ports inaccessible.
# ==============================================


class CountryBaseNetworkGuard(OfflineNetworkGuard):
    """Admit only the numeric address and dedicated native test port."""

    # ==============================================
    # AUDIT CALLBACK
    # Preserve the framework-required callback signature while narrowing network admission.
    # ==============================================

    def __call__(self, event: str, arguments: tuple[object, ...]) -> None:
        """Reject all unlisted network activity before any application test can run."""
        if event == "socket.connect" and len(arguments) > 1:
            address = arguments[1]
            if isinstance(address, tuple) and address[:2] == ("127.0.0.1", PORT):
                return
        if event == "socket.getaddrinfo" and arguments[:2] == ("127.0.0.1", PORT):
            return
        super().__call__(event, arguments)


# ==============================================
# NONSECRET PROCESS FAILURE REPORTS
# Never emit PostgreSQL commands, credentials or captured stderr on a failed subprocess.
# ==============================================


def local_call(*, arguments: list[str]) -> str:
    """Run an already installed local executable; fail without printing sensitive output."""
    # Native PostgreSQL children inherit stdout on Windows; use a file rather than
    # a pipe whose lifetime could outlast pg_ctl itself.
    with tempfile.TemporaryFile() as captured:
        result = subprocess.run(
            arguments,
            stdout=captured,
            stderr=subprocess.STDOUT,
            timeout=120,
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode:
            raise RuntimeError("country_base_local_process_failed")
        captured.seek(0)
        return captured.read().decode("utf-8", errors="replace").strip()


# ==============================================
# REAL EMPTY-DATABASE MAIN CHAIN
# Bootstrap only an empty target and let Alembic write every revision through O3 itself.
# ==============================================


async def initialize(
    *,
    password: str,
    bootstrap_password: str,
    marker: str,
    url: str,
    billing_country: bool = False,
    operational_history: bool = False,
    saas_documents: bool = False,
) -> None:
    """Create a nonsuperuser owner, execute frozen prerequisites and the complete main history."""
    bootstrap = await asyncpg.connect(
        host="127.0.0.1",
        port=PORT,
        user="moulai_bootstrap",
        password=bootstrap_password,
        database="postgres",
        ssl=False,
    )
    try:
        await bootstrap.execute(
            "CREATE ROLE moulai_base_rehearsal LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD '"
            + password
            + "'"
        )
        await bootstrap.execute(
            "CREATE DATABASE moulai_base_rehearsal OWNER moulai_base_rehearsal TEMPLATE template0 ENCODING 'UTF8' LOCALE_PROVIDER builtin BUILTIN_LOCALE 'C.UTF-8' LC_COLLATE 'C' LC_CTYPE 'C'"
        )
        await bootstrap.execute(
            "COMMENT ON DATABASE moulai_base_rehearsal IS 'moulai-country-base:"
            + marker
            + "'"
        )
    finally:
        await bootstrap.close()
    engine = create_async_engine(url, hide_parameters=True, connect_args={"ssl": False})
    try:
        async with engine.begin() as connection:
            if await connection.scalar(
                text("SELECT count(*) FROM pg_tables WHERE schemaname='public'")
            ):
                raise RuntimeError("country_base_database_not_empty")
            for statement in load_bootstrap_statements():
                await connection.exec_driver_sql(statement)

            # ==============================================
            # ALEMBIC CONNECTION HANDOFF
            # The isolated environment reattests database, owner, port and marker before applying history.
            # ==============================================

            def migrate(sync: Connection) -> None:
                """Use the real version directory without changing the normal migration environment."""
                config = Config()
                config.set_main_option(
                    "script_location", str(ROOT / "alembic_country_base_local")
                )
                config.set_main_option(
                    "version_locations", str(ROOT / "alembic/versions")
                )
                config.attributes.update(connection=sync, country_base_marker=marker)
                command.upgrade(config, "o220261108")

            await connection.run_sync(migrate)
            if operational_history:
                return
            from test_support.country_base_seed import seed_retained_quote

            async with AsyncSession(
                bind=connection,
                expire_on_commit=False,
                join_transaction_mode="create_savepoint",
            ) as session:
                identifiers = await seed_retained_quote(session=session)
                await session.commit()
            os.environ["COUNTRY_BASE_TEST_EVIDENCE"] = json.dumps(identifiers)

            # ==============================================
            # REAL FORWARD MIGRATION WITH RETAINED HISTORY
            # O3 runs over an O2 database containing a synthetic frozen quotation and paid period.
            # ==============================================

            def forward(sync: Connection) -> None:
                """Let Alembic advance from O2 to O3 without stamp or manual revision writes."""
                config = Config()
                config.set_main_option(
                    "script_location", str(ROOT / "alembic_country_base_local")
                )
                config.set_main_option(
                    "version_locations", str(ROOT / "alembic/versions")
                )
                config.attributes.update(connection=sync, country_base_marker=marker)
                command.upgrade(
                    config,
                    (
                        "o520261111"
                        if saas_documents
                        else "o420261108" if billing_country else "o320261108"
                    ),
                )

            await connection.run_sync(forward)
    finally:
        await engine.dispose()


# ==============================================
# OWNED CLUSTER LIFECYCLE
# A unique directory and free port are required; existing review services are never stopped.
# ==============================================


def main() -> int:
    """Run the selected historical O2 or country O3/O4 scenarios and stop only this newly created server."""
    parser = argparse.ArgumentParser(description=__doc__)
    profiles = parser.add_mutually_exclusive_group()
    profiles.add_argument("--billing-country", action="store_true")
    profiles.add_argument("--operational-history", action="store_true")
    profiles.add_argument("--saas-documents", action="store_true")
    options = parser.parse_args()
    revision = (
        "o220261108"
        if options.operational_history
        else (
            "o520261111"
            if options.saas_documents
            else "o420261108" if options.billing_country else "o320261108"
        )
    )
    with socket.socket() as check:
        check.bind(("127.0.0.1", PORT))
    marker = uuid4().hex
    output = (
        ROOT
        / (
            "artifacts/operational-history-tests-20261109"
            if options.operational_history
            else (
                "artifacts/saas-documents-20261111/rehearsals"
                if options.saas_documents
                else (
                    "artifacts/operational-o3-20261108"
                    if options.billing_country
                    else "artifacts/saas-base-country-20261108"
                )
            )
        )
        / marker
    )
    private = output / "private"
    private.mkdir(parents=True)
    account = local_call(arguments=["whoami"])
    local_call(
        arguments=[
            "icacls",
            str(private),
            "/inheritance:r",
            "/grant:r",
            account + ":(OI)(CI)F",
            "*S-1-5-18:(OI)(CI)F",
        ]
    )
    (output / "instance-marker").write_text(marker, encoding="ascii")
    password, bootstrap_password = secrets.token_hex(32), secrets.token_hex(32)
    secret = private / "bootstrap-password"
    secret.write_text(bootstrap_password, encoding="ascii")
    data = output / "postgres-data"
    try:
        local_call(
            arguments=[
                str(PG / "initdb.exe"),
                "-D",
                str(data),
                "-U",
                "moulai_bootstrap",
                "--encoding=UTF8",
                "--locale=C",
                "--auth-host=scram-sha-256",
                "--auth-local=trust",
                "--pwfile=" + str(secret),
            ]
        )
    finally:
        secret.unlink(missing_ok=True)
    url = f"postgresql+asyncpg://{DATABASE}:{password}@127.0.0.1:{PORT}/{DATABASE}"
    os.environ.update(
        DEBUG="false",
        DB_ECHO="false",
        APP_ENV="test",
        DATABASE_TARGET="primary",
        DATABASE_URL=url,
        TEST_DATABASE_URL=url,
        REDIS_URL="",
        BOT_TOKEN="000000000:LOCAL_ONLY",
        OPENAI_API_KEY="local-no-provider",
        OPENAI_BASE_URL="http://127.0.0.1:1",
        LOG_FILE_PATH=str(output / "application.log"),
        COUNTRY_BASE_TEST_URL=url,
        COUNTRY_BASE_TEST_MARKER=marker,
        COUNTRY_BASE_TEST_PROFILE=(
            "operational-o2"
            if options.operational_history
            else (
                "documents-o5"
                if options.saas_documents
                else "billing-o4" if options.billing_country else "country-o3"
            )
        ),
    )
    sys.addaudithook(CountryBaseNetworkGuard())
    started = False
    try:
        local_call(
            arguments=[
                str(PG / "pg_ctl.exe"),
                "-D",
                str(data),
                "-l",
                str(private / "postgres.log"),
                "-o",
                "-h 127.0.0.1 -p 55434 -c log_min_error_statement=panic",
                "-w",
                "start",
            ]
        )
        started = True
        asyncio.run(
            initialize(
                password=password,
                bootstrap_password=bootstrap_password,
                marker=marker,
                url=url,
                billing_country=options.billing_country or options.saas_documents,
                operational_history=options.operational_history,
                saas_documents=options.saas_documents,
            )
        )
        import pytest

        with (output / "tests.log").open("w", encoding="utf-8") as log, redirect_stdout(
            log
        ), redirect_stderr(log):
            result = pytest.main(
                [
                    "--noconftest",
                    "-o",
                    "addopts=",
                    "-p",
                    "no:cacheprovider",
                    "-q",
                    (
                        "tests/integration_local/test_operational_postgres.py"
                        if options.operational_history
                        else "tests/integration_local/test_country_base_postgres.py"
                    ),
                    *(
                        [
                            "tests/integration_local/test_billing_country_postgres.py",
                            "tests/integration_local/test_country_checkout_postgres.py",
                            "tests/integration_local/test_followup_postgres.py",
                        ]
                        if options.billing_country or options.saas_documents
                        else []
                    ),
                    *(
                        ["tests/integration_local/test_saas_documents_postgres.py"]
                        if options.saas_documents
                        else []
                    ),
                    "--junitxml=" + str(output / "results.xml"),
                ]
            )
        report = {
            "status": "PASS" if result == 0 else "FAIL",
            "revision": revision,
            "bootstrap": "main-bootstrap-v1",
            "main_chain": True,
            "instance": marker,
            "target": "127.0.0.1:55434/moulai_base_rehearsal",
            "review_instance_changed": False,
            "Neon_connection": False,
            "pytest_exit_code": int(result),
        }
        (output / "summary.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        print(json.dumps(report))
        return int(result)
    finally:
        if started:
            local_call(
                arguments=[
                    str(PG / "pg_ctl.exe"),
                    "-D",
                    str(data),
                    "-m",
                    "fast",
                    "-w",
                    "stop",
                ]
            )
            report_path = output / "summary.json"
            if report_path.exists():
                saved = json.loads(report_path.read_text(encoding="utf-8"))
                saved["server_stopped"] = True
                report_path.write_text(json.dumps(saved, indent=2), encoding="utf-8")


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
        print(
            json.dumps({"status": "STOPPED", "type": type(error).__name__}),
            file=sys.stderr,
        )
        raise SystemExit(1) from None
