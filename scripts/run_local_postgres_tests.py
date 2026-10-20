# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Provision an owned disposable PostgreSQL instance and run live fixture tests."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
from contextlib import (
    redirect_stderr,
    redirect_stdout,
)
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import asyncpg
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import command
from scripts.run_offline_api_tests import TestResults
from test_support.local_postgres import (
    LOCAL_DATABASE,
    LOCAL_E1_REVISION,
    LOCAL_PORT,
    LOCAL_REVISION,
    LOCAL_ROLE,
    LocalPostgresNetworkGuard,
    LocalPostgresSettings,
    read_local_test_identity,
)

# ==============================================
# BOUNDED LOCAL PROCESS EXECUTION
# ==============================================


def run_process(
    *, arguments: list[str], environment: dict[str, str] | None = None
) -> None:
    """Execute local tools without printing environment values or raw errors."""
    result = subprocess.run(
        arguments,
        cwd=ROOT,
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
        timeout=90,
    )
    if result.returncode:
        raise RuntimeError(
            f"local_tool_failed:{Path(arguments[0]).name}:{result.returncode}"
        )


# ==============================================
# CHOOSE AN AVAILABLE LOCAL BACKEND WITHOUT STARTING EXISTING SERVICES
# ==============================================


def choose_backend(*, requested: str) -> str:
    """Prefer an already running Docker engine; otherwise use installed binaries."""
    if requested == "native":
        return requested
    if shutil.which("docker") is not None:
        result = subprocess.run(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            capture_output=True,
            text=True,
            check=False,
            timeout=20,
        )
        if result.returncode == 0:
            return "docker"
    if requested == "docker":
        raise RuntimeError("docker_engine_unavailable")
    return "native"


# ==============================================
# CONFIGURE PINNED LOCAL ALEMBIC EXECUTION
# ==============================================


def apply_local_migrations(
    connection: Connection, *, configuration: LocalPostgresSettings
) -> None:
    """Apply the explicit compatibility or tenant-E1 history on a fresh local DB."""
    read_local_test_identity(connection, configuration=configuration)
    if connection.execute(
        text("SELECT count(*) FROM pg_tables WHERE schemaname='public'")
    ).scalar_one():
        raise RuntimeError("local_database_must_be_new_and_empty")
    config = Config()
    config.set_main_option("script_location", str(ROOT / "alembic_local_test"))
    config.set_main_option("version_locations", str(ROOT / "alembic_test/versions"))
    config.set_main_option("path_separator", "os")
    config.attributes["connection"] = connection
    config.attributes["local_configuration"] = configuration
    target = LOCAL_E1_REVISION if configuration.PROFILE == "k10" else LOCAL_REVISION
    command.upgrade(config, target)


# ==============================================
# PROVISION ONLY THE NEW INSTANCE'S DEDICATED DATABASE AND UNPRIVILEGED ROLE
# ==============================================


async def provision_database(
    *,
    bootstrap_password: str,
    configuration: LocalPostgresSettings,
    runtime_password: str,
) -> dict[str, Any]:
    """Use loopback only; credentials remain in memory and are never reported."""
    bootstrap = await asyncpg.connect(
        host="127.0.0.1",
        port=LOCAL_PORT,
        database="postgres",
        user="moulai_test_bootstrap",
        password=bootstrap_password,
        timeout=20,
    )
    try:
        # Passwords are generated as hexadecimal, never accepted as SQL input.
        if len(runtime_password) != 64 or any(
            c not in "0123456789abcdef" for c in runtime_password
        ):
            raise RuntimeError("local_runtime_password_not_generated")
        await bootstrap.execute(
            f"CREATE ROLE {LOCAL_ROLE} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
            f"PASSWORD '{runtime_password}'"
        )
        await bootstrap.execute(f"CREATE DATABASE {LOCAL_DATABASE} OWNER {LOCAL_ROLE}")
        await bootstrap.execute(
            f"COMMENT ON DATABASE {LOCAL_DATABASE} IS "
            f"'moulai-local-pytest:{configuration.INSTANCE_ID}'"
        )
    finally:
        await bootstrap.close()
    engine = create_async_engine(
        configuration.URL.get_secret_value(),
        echo=False,
        connect_args={"ssl": False, "timeout": 20, "command_timeout": 90},
    )
    try:
        async with engine.begin() as connection:
            await connection.run_sync(
                lambda sync: apply_local_migrations(sync, configuration=configuration)
            )
        async with engine.connect() as connection:
            await connection.run_sync(
                lambda sync: read_local_test_identity(sync, configuration=configuration)
            )
            version = (
                await connection.execute(
                    text("SELECT version_num FROM alembic_version")
                )
            ).scalar_one()
            count = (
                await connection.execute(
                    text("SELECT count(*) FROM pg_tables WHERE schemaname='public'")
                )
            ).scalar_one()
            server = (
                await connection.execute(text("SHOW server_version"))
            ).scalar_one()
            expected_revision = (
                LOCAL_E1_REVISION if configuration.PROFILE == "k10" else LOCAL_REVISION
            )
            expected_count = 56 if configuration.PROFILE == "k10" else 47
            if version != expected_revision or count != expected_count:
                raise RuntimeError("local_migration_catalog_mismatch")
            observed = {
                "revision": version,
                "public_tables": count,
                "server_version": server,
            }
            if configuration.PROFILE == "k10":
                from app.models import Base
                from scripts.rehearse_tenant_e1 import verify_e1_catalog

                observed["e1_catalog"] = await verify_e1_catalog(
                    connection,
                    legacy_tables=set(Base.metadata.tables) | {"alembic_version"},
                )
            return observed
    finally:
        await engine.dispose()


# ==============================================
# RUN ONLY REAL POSTGRESQL FIXTURE CONSUMERS
# ==============================================


def execute_tests(*, output: Path, profile: str = "legacy") -> dict[str, Any]:
    """Capture actual outcomes and keep test console output outside the root."""
    import pytest

    results = TestResults()
    with (
        (output / "postgres-tests.log").open("w", encoding="utf-8") as stream,
        redirect_stdout(stream),
        redirect_stderr(stream),
    ):
        selection = (
            ["tests/test_k10_postgres.py", "--maxfail=1"]
            if profile == "k10"
            else ["-m", "database"]
        )
        code = int(
            pytest.main(
                [
                    "-o",
                    "addopts=",
                    "-p",
                    "pytest_asyncio.plugin",
                    "-p",
                    "no:cacheprovider",
                    "--local-postgres-tests",
                    *selection,
                    "-q",
                    "-rs",
                    "--tb=short",
                    "-W",
                    "error",
                    f"--junitxml={output / 'postgres-results.xml'}",
                ],
                plugins=[results],
            )
        )
    return {
        "pytest_exit_code": code,
        "collected": results.collected,
        "outcomes": dict(results.outcomes),
        "warnings": dict(results.warnings),
        "failed_tests": results.failures,
    }


# ==============================================
# OWN THE COMPLETE LOCAL SERVER LIFECYCLE
# ==============================================


def main() -> int:
    """Create, migrate, test and stop only this launcher's isolated instance."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--backend", choices=("auto", "docker", "native"), default="auto"
    )
    parser.add_argument("--postgres-bin", type=Path)
    parser.add_argument("--profile", choices=("legacy", "k10"), default="legacy")
    options = parser.parse_args()
    os.chdir(ROOT)
    instance_id = uuid4().hex
    output = ROOT / "artifacts/postgres-local-tests" / instance_id
    output.mkdir(parents=True)
    backend = choose_backend(requested=options.backend)
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", LOCAL_PORT))
    bootstrap_password = secrets.token_hex(32)
    runtime_password = secrets.token_hex(32)
    configuration = LocalPostgresSettings(
        URL=f"postgresql+asyncpg://{LOCAL_ROLE}:{runtime_password}@127.0.0.1:{LOCAL_PORT}/{LOCAL_DATABASE}",
        INSTANCE_ID=instance_id,
        SERVER_PORT=5432 if backend == "docker" else LOCAL_PORT,
        PROFILE=options.profile,
    )
    os.environ.update(
        {
            "DEBUG": "false",
            "DB_ECHO": "false",
            "REDIS_URL": "",
            "OIDC_DIAGNOSTICS_ENABLED": "false",
            "OIDC_ALLOW_LOCAL_HTTP": "false",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "LOCAL_POSTGRES_TEST_URL": configuration.URL.get_secret_value(),
            "LOCAL_POSTGRES_TEST_INSTANCE_ID": instance_id,
            "LOCAL_POSTGRES_TEST_SERVER_PORT": str(configuration.SERVER_PORT),
            "LOCAL_POSTGRES_TEST_PROFILE": configuration.PROFILE,
        }
    )
    guard = LocalPostgresNetworkGuard()
    sys.addaudithook(guard)
    print(
        f"Local PostgreSQL: backend={backend}, port={LOCAL_PORT}, run={instance_id}",
        flush=True,
    )
    project = f"moulai-pgtests-{instance_id}"
    compose = [
        "docker",
        "compose",
        "--project-name",
        project,
        "--file",
        str(ROOT / "compose.postgres-tests.yml"),
    ]
    docker_environment = {
        **os.environ,
        "MOULAI_LOCAL_BOOTSTRAP_PASSWORD": bootstrap_password,
    }
    data = output / "server-data"
    binary_root = options.postgres_bin or Path(r"C:\Program Files\PostgreSQL\18\bin")
    pg_ctl = str(binary_root / ("pg_ctl.exe" if os.name == "nt" else "pg_ctl"))
    started = False
    server_attempted = False
    summary: dict[str, Any] = {
        "instance_id": instance_id,
        "backend": backend,
        "profile": configuration.PROFILE,
    }
    try:
        if backend == "docker":
            server_attempted = True
            run_process(
                arguments=[*compose, "up", "-d", "--wait"],
                environment=docker_environment,
            )
        else:
            password_file = output / "bootstrap-password"
            password_file.write_text(bootstrap_password + "\n", encoding="utf-8")
            try:
                run_process(
                    arguments=[
                        str(
                            binary_root
                            / ("initdb.exe" if os.name == "nt" else "initdb")
                        ),
                        "-D",
                        str(data),
                        "-U",
                        "moulai_test_bootstrap",
                        "--encoding=UTF8",
                        "--locale=C",
                        "--auth-host=scram-sha-256",
                        "--auth-local=trust",
                        f"--pwfile={password_file}",
                    ]
                )
            finally:
                password_file.unlink(missing_ok=True)
            server_attempted = True
            run_process(
                arguments=[
                    pg_ctl,
                    "-D",
                    str(data),
                    "-l",
                    str(output / "server.log"),
                    "-o",
                    f"-h 127.0.0.1 -p {LOCAL_PORT} -c log_min_error_statement=panic",
                    "-w",
                    "-t",
                    "30",
                    "start",
                ]
            )
        started = True
        summary["schema"] = asyncio.run(
            provision_database(
                bootstrap_password=bootstrap_password,
                configuration=configuration,
                runtime_password=runtime_password,
            )
        )
        print("Local schema ready; running PostgreSQL fixtures.", flush=True)
        summary.update(execute_tests(output=output, profile=configuration.PROFILE))
        summary["network_denied_categories"] = dict(guard.denied)
    except (
        OSError,
        RuntimeError,
        ValueError,
        subprocess.SubprocessError,
        SQLAlchemyError,
        asyncpg.PostgresError,
    ) as error:
        # Raw provisioning exceptions can contain SQL/password literals.
        summary["setup_error"] = type(error).__name__
        if type(error) is RuntimeError:
            summary["setup_reason"] = str(error)
        summary["passed"] = False
        print(f"Local setup/execution stopped: {type(error).__name__}", flush=True)
    finally:
        if server_attempted:
            if backend == "docker":
                run_process(
                    arguments=[*compose, "down", "--volumes"],
                    environment=docker_environment,
                )
            elif (data / "postmaster.pid").exists():
                if not data.resolve().is_relative_to(output.resolve()):
                    raise RuntimeError("local_server_cleanup_path_mismatch")
                run_process(
                    arguments=[pg_ctl, "-D", str(data), "-m", "fast", "-w", "stop"]
                )
        summary["server_stopped"] = started
    summary["passed"] = (
        summary.get("pytest_exit_code") == 0
        and summary.get("outcomes", {}).get("passed", 0) > 0
        and not summary.get("outcomes", {}).get("skipped", 0)
        and not guard.denied
        and "setup_error" not in summary
    )
    (output / "validation.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
