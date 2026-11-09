# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# FRESH OPERATIONAL POSTGRESQL REHEARSAL
# Reconstruct the main chain and run synthetic regressions on a new cluster without changing the active instance.
# ==============================================

"""Native local PostgreSQL only; no Keycloak creation, remote IO or exported fixture prices."""

from __future__ import annotations

# isort: split
# ==============================================
# CONTROLLED LOCAL DEPENDENCIES
# Reuse the established bootstrap and network guard, with private generated test credentials.
# ==============================================

import asyncio
import json
import os
import secrets
import sys
from contextlib import (
    redirect_stderr,
    redirect_stdout,
)
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cryptography.fernet import Fernet

from app.integration.config import (
    INSTANCE_ROOT,
    IntegrationConfig,
)
from app.integration.local_setup import (
    PG,
    initialize_database,
    issue_local_certificates,
    local_process,
)
from scripts.run_operational_local import IntegrationNetworkGuard

# ==============================================
# TEMPORARY MARKED CLUSTER
# Never replace active.json or connect to the retained application database while it is running.
# ==============================================


def main() -> int:
    """Keep the generated test data for inspection, stop the native server and report actual pytest outcomes."""
    identifier = uuid4().hex
    directory = INSTANCE_ROOT / identifier
    (directory / "private").mkdir(parents=True)
    account = local_process(arguments=["whoami"])
    local_process(
        arguments=[
            "icacls",
            str(directory / "private"),
            "/inheritance:r",
            "/grant:r",
            account + ":(OI)(CI)F",
            "*S-1-5-18:(OI)(CI)F",
        ]
    )
    (directory / "instance-marker").write_text(identifier, encoding="ascii")
    (directory / "disposable-test-only").write_text("o1", encoding="ascii")
    data = {
        "instance_id": identifier,
        "database_url": "postgresql+asyncpg://moulai_integrated:"
        + secrets.token_hex(32)
        + "@127.0.0.1:55433/moulai_integrated",
        "client_secret": secrets.token_urlsafe(48),
        "session_key": Fernet.generate_key().decode(),
        "admin_password": secrets.token_urlsafe(32),
    }
    (directory / "private/instance.json").write_text(json.dumps(data), encoding="utf-8")
    configuration = IntegrationConfig.load(directory=directory)
    configuration.process_environment()
    sys.addaudithook(IntegrationNetworkGuard())
    issue_local_certificates(directory=directory)
    password = secrets.token_urlsafe(32)
    password_file = directory / "private/postgres-password"
    password_file.write_text(password, encoding="utf-8")
    try:
        local_process(
            arguments=[
                str(PG / "initdb.exe"),
                "-D",
                str(directory / "postgres-data"),
                "-U",
                "moulai_bootstrap",
                "--encoding=UTF8",
                "--locale=C",
                "--auth-host=scram-sha-256",
                "--auth-local=trust",
                "--pwfile=" + str(password_file),
            ]
        )
    finally:
        password_file.unlink(missing_ok=True)
    local_process(
        arguments=[
            str(PG / "pg_ctl.exe"),
            "-D",
            str(directory / "postgres-data"),
            "-l",
            str(directory / "postgres.log"),
            "-o",
            "-h 127.0.0.1 -p 55433 -c log_min_error_statement=panic",
            "-w",
            "start",
        ]
    )
    output = ROOT / "artifacts/operational-milestone-20261108"
    previous = [
        output / name
        for name in (
            "postgres-tests.log",
            "postgres-results.xml",
            "postgres-rehearsal.json",
        )
        if (output / name).exists()
    ]
    if previous:
        retained = output / ("attempt-" + uuid4().hex)
        retained.mkdir()
        for evidence in previous:
            evidence.replace(retained / evidence.name)
    try:
        asyncio.run(
            initialize_database(
                configuration=configuration, bootstrap_password=password
            )
        )
        os.environ["MOULAI_O1_TEST_INSTANCE"] = str(directory)
        import pytest

        with (output / "postgres-tests.log").open(
            "w", encoding="utf-8"
        ) as log, redirect_stdout(log), redirect_stderr(log):
            result = pytest.main(
                [
                    "--noconftest",
                    "-o",
                    "addopts=",
                    "-o",
                    "markers=dining_postgres: isolated dining database proofs\noperational_rehearsal: dedicated O2 disposable database proofs",
                    "-p",
                    "no:cacheprovider",
                    "-q",
                    "tests/integration_local/test_operational_postgres.py",
                    "--junitxml=" + str(output / "postgres-results.xml"),
                ]
            )
        report = {
            "status": "PASS" if result == 0 else "FAIL",
            "pytest_exit_code": int(result),
            "instance": identifier,
            "revision": "o220261108",
            "fresh_main_chain": True,
            "active_instance_unchanged": True,
            "synthetic_tariffs": "this disposable instance only",
            "server_stopped": True,
        }
        (output / "postgres-rehearsal.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        print(json.dumps(report))
        return int(result)
    finally:
        local_process(
            arguments=[
                str(PG / "pg_ctl.exe"),
                "-D",
                str(directory / "postgres-data"),
                "-m",
                "fast",
                "-w",
                "stop",
            ]
        )


if __name__ == "__main__":
    raise SystemExit(main())
