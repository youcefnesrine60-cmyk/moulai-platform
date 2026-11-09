# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# DISPOSABLE POSTGRESQL TEST LAUNCHER
# Prepare bounded local test processes and reject permanent or remote database
# destinations.
# ==============================================

"""Provision an owned disposable PostgreSQL instance and run live fixture tests."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Declare the standard-library, framework and project dependencies used below.
# ==============================================

import argparse
import ast
import asyncio
import errno
import hashlib
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

# ==============================================
# CONFIGURATION AND CONSTANTS
# Group the existing configuration values without changing their defaults.
# ==============================================

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
    LOCAL_DINING_REVISION,
    LOCAL_E1_REVISION,
    LOCAL_MAIN_REVISION,
    LOCAL_PORT,
    LOCAL_REVISION,
    LOCAL_ROLE,
    LOCAL_S1_REVISION,
    LocalPostgresNetworkGuard,
    LocalPostgresSettings,
    read_local_test_identity,
)

# ==============================================
# HISTORICAL TABLE INVENTORY FROM FROZEN DDL
# Keep E1 admission independent of later ORM additions such as subscription S1.
# ==============================================


def legacy_schema_tables() -> set[str]:
    """Read literal baseline table names; never execute or rewrite migrations."""
    source = ROOT / "alembic_test/versions/ae6a266365fb_test_schema_baseline.py"
    content = source.read_bytes()
    if hashlib.sha256(content).hexdigest() != (
        "6b168b7bd283d09e6959e61d44cabbf22431a83355dc58f249ff688f59d108e4"
    ):
        raise RuntimeError("local_legacy_inventory_source_mismatch")
    tree = ast.parse(content.decode("utf-8"))
    tables = {
        node.args[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "op"
        and node.func.attr == "create_table"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    } | {"alembic_version", "manual_payment_receipts", "manual_payment_audit"}
    if len(tables) != 47:
        raise RuntimeError("local_legacy_inventory_source_mismatch")
    return tables


# ==============================================
# SELECT ONLY TESTS SUPPORTED BY THE RECONSTRUCTED SCHEMA
# Default to the main history; historical compatibility schemas are not S1a.
# ==============================================


def select_tests(*, profile: str, suite: str, paths: list[str] | None) -> list[str]:
    """Reject obsolete broad legacy runs before starting a disposable server."""
    if profile == "legacy":
        raise ValueError("legacy_schema_not_current_application:use_--profile_main")
    if suite != "profile":
        if profile != "main" or paths:
            raise ValueError("dedicated_suite_requires_main_profile_without_test_paths")
        return [
            (
                "tests/test_health_only_postgres.py"
                if suite == "health-only"
                else "tests/test_catalog_postgres_transactions.py"
            ),
            "--maxfail=1",
        ]
    if paths:
        return paths
    if profile == "k10":
        return ["tests/test_k10_postgres.py", "--maxfail=1"]
    if profile == "dining":
        return ["tests/dining"]
    if profile == "subscription":
        return [
            "tests/subscription_diagnostics",
            "tests/test_subscription_lifecycle.py",
            "tests/test_subscription_decisions.py",
            "tests/test_cash_collection.py",
            "tests/test_subscription_trial_clock.py",
            "tests/test_subscription_compat.py",
            "tests/test_pricing_discount_database_integration.py",
            "tests/test_manual_payment_workflow.py",
            "tests/test_payment_subscription_transactions.py",
        ]
    if profile == "main":
        return ["-m", "database"]
    raise ValueError("unsupported_local_profile")


# ==============================================
# BOUNDED LOCAL PROCESS EXECUTION
# Execute local tools without printing environment values or raw errors.
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
# Prefer an already running Docker engine; otherwise use installed binaries.
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
# Apply the explicit compatibility or tenant-E1 history on a fresh local DB.
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
    if configuration.PROFILE == "dining":
        # Preserve the exact S1a admission path, then apply only the explicit
        # additive D1 node on this same owned disposable connection.
        apply_local_migrations(
            connection,
            configuration=configuration.model_copy(update={"PROFILE": "main"}),
        )
    if configuration.PROFILE == "main":
        from migration_support.main_bootstrap import apply_main_bootstrap

        apply_main_bootstrap(connection, configuration=configuration)
    config = Config()
    config.set_main_option("script_location", str(ROOT / "alembic_local_test"))
    config.set_main_option(
        "version_locations",
        str(
            ROOT
            / (
                "alembic/versions"
                if configuration.PROFILE in {"main", "dining"}
                else "alembic_test/versions"
            )
        ),
    )
    config.set_main_option("path_separator", "os")
    config.attributes["connection"] = connection
    config.attributes["local_configuration"] = configuration
    target = {
        "dining": LOCAL_DINING_REVISION,
        "k10": LOCAL_E1_REVISION,
        "subscription": LOCAL_S1_REVISION,
        "main": LOCAL_MAIN_REVISION,
    }.get(configuration.PROFILE, LOCAL_REVISION)
    command.upgrade(config, target)


# ==============================================
# PROVISION ONLY THE NEW INSTANCE'S DEDICATED DATABASE AND UNPRIVILEGED ROLE
# Use loopback only; credentials remain in memory and are never reported.
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
        port=configuration.CLIENT_PORT,
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
        if configuration.PROFILE in {"main", "dining"}:
            await bootstrap.execute(
                f"CREATE DATABASE {LOCAL_DATABASE} OWNER {LOCAL_ROLE} TEMPLATE template0 ENCODING 'UTF8' LOCALE_PROVIDER builtin BUILTIN_LOCALE 'C.UTF-8' LC_COLLATE 'C' LC_CTYPE 'C'"
            )
        else:
            await bootstrap.execute(
                f"CREATE DATABASE {LOCAL_DATABASE} OWNER {LOCAL_ROLE}"
            )
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
            expected_revision = {
                "dining": LOCAL_DINING_REVISION,
                "k10": LOCAL_E1_REVISION,
                "subscription": LOCAL_S1_REVISION,
                "main": LOCAL_MAIN_REVISION,
            }.get(configuration.PROFILE, LOCAL_REVISION)
            expected_count = {
                "k10": 56,
                "subscription": 52,
                "main": 61,
                "dining": 92,
            }.get(configuration.PROFILE, 47)
            if version != expected_revision or count != expected_count:
                raise RuntimeError("local_migration_catalog_mismatch")
            observed = {
                "revision": version,
                "public_tables": count,
                "server_version": server,
            }
            if configuration.PROFILE == "k10":
                from scripts.rehearse_tenant_e1 import verify_e1_catalog

                observed["e1_catalog"] = await verify_e1_catalog(
                    connection,
                    legacy_tables=legacy_schema_tables(),
                )
            return observed
    finally:
        await engine.dispose()


# ==============================================
# RUN ONLY REAL POSTGRESQL FIXTURE CONSUMERS
# Capture actual outcomes and keep test console output outside the root.
# ==============================================


def execute_tests(
    *,
    output: Path,
    profile: str = "main",
    suite: str = "profile",
    paths: list[str] | None = None,
) -> dict[str, Any]:
    """Capture actual outcomes and keep test console output outside the root."""
    import pytest

    results = TestResults()
    with (
        (output / "postgres-tests.log").open("w", encoding="utf-8") as stream,
        redirect_stdout(stream),
        redirect_stderr(stream),
    ):
        selection = select_tests(profile=profile, suite=suite, paths=paths)
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
# SELECT ONLY AN ALREADY APPROVED TEST PORT
# Keep existing listeners untouched; native startup may use the second isolated port only when the caller has not pinned one explicitly.
# ==============================================


def select_local_port(*, backend: str, requested: int | None) -> int:
    """Probe the fixed allowlist before provisioning; never terminate a listener or select an arbitrary free port."""
    if requested not in {None, LOCAL_PORT, 55435}:
        raise ValueError("local_test_port_not_admitted")
    if backend != "native" and requested == 55435:
        raise ValueError("alternate_local_test_port_requires_native")
    candidates = (
        (requested,)
        if requested is not None
        else (LOCAL_PORT, 55435) if backend == "native" else (LOCAL_PORT,)
    )
    for candidate in candidates:
        try:
            with socket.socket() as reservation:
                reservation.bind(("127.0.0.1", candidate))
            return candidate
        except OSError as error:
            if error.errno not in {errno.EADDRINUSE, errno.EACCES} and getattr(
                error, "winerror", None
            ) not in {10048, 10013}:
                raise
    ports = ", ".join(str(port) for port in candidates)
    raise ValueError(
        f"Port(s) de test local indisponible(s) : {ports}. "
        "Aucun service existant n'a ete arrete. "
        "Utilisez --backend native --port 55435 si ce port est libre, "
        "ou attendez la fin de l'autre campagne de tests."
    )


# ==============================================
# OWN THE COMPLETE LOCAL SERVER LIFECYCLE
# Create, migrate, test and stop only this launcher's isolated instance.
# ==============================================


def main() -> int:
    """Create, migrate, test and stop only this launcher's isolated instance."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--backend", choices=("auto", "docker", "native"), default="auto"
    )
    parser.add_argument("--postgres-bin", type=Path)
    parser.add_argument(
        "--port",
        type=int,
        choices=(55432, 55435),
        default=None,
        help="Pin an approved port; native default tries 55432 then 55435 without stopping existing services",
    )
    parser.add_argument(
        "--profile",
        choices=("legacy", "k10", "subscription", "main", "dining"),
        default="main",
    )
    parser.add_argument(
        "--suite", choices=("profile", "health-only", "catalog"), default="profile"
    )
    parser.add_argument("--test-paths", nargs="+")
    parser.add_argument(
        "--main-archive",
        type=Path,
        help="Export and locally restore S1a canonical seeds instead of running tests",
    )
    options = parser.parse_args()
    if options.main_archive and (options.profile != "main" or options.test_paths):
        parser.error("Canonical archive requires main profile and no test selection")
    if options.test_paths:
        for name in options.test_paths:
            target = (ROOT / name).resolve()
            if (
                not target.is_relative_to(ROOT / "tests")
                or not target.exists()
                or name.startswith("-")
            ):
                parser.error(
                    "Test paths must exist under the repository tests directory"
                )

    try:
        select_tests(
            profile=options.profile, suite=options.suite, paths=options.test_paths
        )
    except ValueError as error:
        parser.error(str(error))
    os.chdir(ROOT)
    backend = choose_backend(requested=options.backend)
    try:
        port = select_local_port(backend=backend, requested=options.port)
    except ValueError as error:
        parser.error(str(error))
    except OSError:
        parser.error(
            "Impossible de verifier le port local. Aucun serveur n'a ete demarre."
        )
    if options.port is None and port != LOCAL_PORT:
        print(
            f"Port {LOCAL_PORT} indisponible ; utilisation du port de test isole {port}. Aucun service existant n'est arrete.",
            flush=True,
        )
    instance_id = uuid4().hex
    output = ROOT / "artifacts/postgres-local-tests" / instance_id
    output.mkdir(parents=True)
    bootstrap_password = secrets.token_hex(32)
    runtime_password = secrets.token_hex(32)
    configuration = LocalPostgresSettings(
        CLIENT_PORT=port,
        URL=f"postgresql+asyncpg://{LOCAL_ROLE}:{runtime_password}@127.0.0.1:{port}/{LOCAL_DATABASE}",
        INSTANCE_ID=instance_id,
        SERVER_PORT=5432 if backend == "docker" else port,
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
            "LOCAL_POSTGRES_TEST_CLIENT_PORT": str(configuration.CLIENT_PORT),
            "LOCAL_POSTGRES_TEST_INSTANCE_ID": instance_id,
            "LOCAL_POSTGRES_TEST_SERVER_PORT": str(configuration.SERVER_PORT),
            "LOCAL_POSTGRES_TEST_PROFILE": configuration.PROFILE,
        }
    )
    guard = LocalPostgresNetworkGuard(client_port=configuration.CLIENT_PORT)
    sys.addaudithook(guard)
    print(
        f"Local PostgreSQL: backend={backend}, port={configuration.CLIENT_PORT}, run={instance_id}",
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
        "suite": options.suite,
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
                    f"-h 127.0.0.1 -p {configuration.CLIENT_PORT} -c log_min_error_statement=panic",
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
        if configuration.PROFILE in {"main", "dining"}:
            from test_support.main_reconstruction import verify_main_reconstruction

            os.environ.update(
                {
                    "DATABASE_TARGET": "primary",
                    "DATABASE_URL": configuration.URL.get_secret_value(),
                    "TEST_DATABASE_URL": configuration.URL.get_secret_value(),
                    "APP_ENV": "test",
                    "BOT_TOKEN": "000000000:LOCAL_REHEARSAL_NOT_A_REAL_BOT_TOKEN",
                    "OPENAI_API_KEY": "local-rehearsal-no-provider-access",
                    "OPENAI_BASE_URL": "http://127.0.0.1:1",
                    "LOG_FILE_PATH": str(output / "application.log"),
                }
            )
            if configuration.PROFILE == "main":
                summary["main_verification"] = asyncio.run(
                    verify_main_reconstruction(
                        configuration=configuration, output=output
                    )
                )
            else:
                from test_support.dining_reconstruction import verify_dining_reconstruction  # isort: skip  # fmt: skip

                summary["dining_verification"] = asyncio.run(
                    verify_dining_reconstruction(
                        configuration=configuration, output=output
                    )
                )
        if options.main_archive:
            from test_support.main_reconstruction import prepare_main_archive

            (output / "main-catalogue-before-restore.json").write_bytes(
                (output / "main-catalogue.json").read_bytes()
            )
            summary["canonical_archive"] = asyncio.run(
                prepare_main_archive(
                    configuration=configuration,
                    binary_root=binary_root,
                    destination=options.main_archive,
                    catalogue_before=json.loads(
                        (output / "main-catalogue-before-restore.json").read_text(
                            encoding="utf-8"
                        )
                    ),
                )
            )
            summary["restored_main_verification"] = asyncio.run(
                verify_main_reconstruction(configuration=configuration, output=output)
            )
            summary["validation_scope"] = (
                "canonical archive and actual local restoration; no pytest campaign"
            )
        else:
            print("Local schema ready; running PostgreSQL fixtures.", flush=True)
            summary.update(
                execute_tests(
                    output=output,
                    profile=configuration.PROFILE,
                    suite=options.suite,
                    paths=options.test_paths,
                )
            )
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
        (
            (
                summary.get("pytest_exit_code") == 0
                and summary.get("outcomes", {}).get("passed", 0) > 0
            )
            or bool(
                summary.get("canonical_archive", {}).get(
                    "local_clean_restore_completed"
                )
                and summary.get("restored_main_verification")
            )
        )
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
