# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Verify the real FastAPI lifecycle against the attested development database.

Every connection created by this verifier uses the approved TEST_DATABASE_URL
and verified TLS. A mandatory SQLAlchemy begin listener enforces READ ONLY for
every transaction; default_transaction_read_only=on is additionally requested.
The live identity gate runs before importing the application. Real init_db
validates migrated schema; no initializer or schema validation function is
replaced. HTTP requests use ASGITransport for GET / and GET /health only.
Normal outbound httpx network
transports are blocked throughout application import and lifecycle execution.

Run separately from migration rehearsals and other database test processes.
The ignored JSON artifact is independent of application console logs and never
contains connection URLs, credentials, row contents, or raw exception messages.
"""

from __future__ import annotations

# ==============================================
# IMPORTS AND VERIFICATION CONTRACT
# ==============================================

import argparse
import asyncio
import hashlib
import importlib
import json
import logging
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import (
    datetime,
    timezone,
)
from functools import partial
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    TypeAlias,
)
from unittest.mock import (
    AsyncMock,
    patch,
)

import httpx
from sqlalchemy import (
    event,
    inspect,
    text,
)
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if TYPE_CHECKING:
    from app.core.config import Settings

Report: TypeAlias = dict[str, Any]
EXPECTED_TEST_REVISION = "dce91870b4a2"
EXPECTED_PUBLIC_TABLE_COUNT = 47
REPORT_FILENAME = "development-startup-results.json"
APPLICATION_LOGGER_NAME = "MoulAI™ Platform - Agent-as-a-Service"
logger = logging.getLogger("MoulAI.development_startup_verification")


# ==============================================
# SAFE FAILURES AND TEMPORARY APPLICATION LOG FILTER
# ==============================================


class StartupVerificationError(RuntimeError):
    """Carry a verifier-owned failure code without private runtime values."""


class SafeApplicationErrors(logging.Filter):
    """Keep operational logs while removing raw application error details."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Redact exception records that can otherwise include database details."""
        if record.levelno >= logging.ERROR:
            record.msg = "development_startup_application_error"
            record.args = ()
            record.exc_info = None
            record.exc_text = None
            record.stack_info = None
            if "error" in record.__dict__:
                record.__dict__["error"] = "redacted"
        return True


@contextmanager
def sanitized_application_errors() -> Iterator[None]:
    """Restore the application's original logging filters after verification."""
    application_logger = logging.getLogger(APPLICATION_LOGGER_NAME)
    error_filter = SafeApplicationErrors()
    application_logger.addFilter(error_filter)
    try:
        yield
    finally:
        application_logger.removeFilter(error_filter)


# ==============================================
# ISOLATED DEVELOPMENT ENGINE CONFIGURATION
# ==============================================


def _set_transaction_read_only(connection: Connection) -> None:
    """Enforce read-only mode before any statement in each engine transaction."""
    connection.exec_driver_sql("SET TRANSACTION READ ONLY")


def _require_read_only_guard(*, engine: AsyncEngine) -> None:
    """Refuse to use an engine without its transaction-level safety listener."""
    if not event.contains(engine.sync_engine, "begin", _set_transaction_read_only):
        raise StartupVerificationError("read_only_transaction_guard_missing")


def _install_read_only_guard(*, engine: AsyncEngine) -> None:
    """Attach the synchronous event supported by SQLAlchemy's async adapter."""
    if not event.contains(engine.sync_engine, "begin", _set_transaction_read_only):
        event.listen(engine.sync_engine, "begin", _set_transaction_read_only)
    _require_read_only_guard(engine=engine)


def development_engine() -> tuple[AsyncEngine, Settings, str]:
    """Validate the declared development target before constructing its engine."""
    from app.core.config import settings
    from app.core.test_database import (
        isolated_connection_arguments,
        validate_test_branch_configuration,
        validated_test_database_url,
    )

    if settings.APP_ENV not in {"development", "test"}:
        raise StartupVerificationError("development_environment_required")
    validate_test_branch_configuration(
        branch_id=settings.TEST_DATABASE_BRANCH_ID,
        project_id=settings.TEST_DATABASE_PROJECT_ID,
        protected_branch_id=settings.PROTECTED_DATABASE_BRANCH_ID,
    )
    url = validated_test_database_url(
        test_database_url=settings.TEST_DATABASE_URL,
        test_endpoint_id=settings.TEST_DATABASE_ENDPOINT_ID,
        protected_endpoint_id=settings.PROTECTED_DATABASE_ENDPOINT_ID,
    )
    connection_arguments = isolated_connection_arguments()
    connection_arguments["server_settings"] = {
        **connection_arguments["server_settings"],
        "default_transaction_read_only": "on",
    }
    engine = create_async_engine(
        url,
        echo=False,
        hide_parameters=True,
        poolclass=NullPool,
        connect_args=connection_arguments,
    )
    _install_read_only_guard(engine=engine)
    return engine, settings, url


# ==============================================
# READ-ONLY IDENTITY AND SCHEMA DATABASE HELPERS
# ==============================================


def _identity(connection: Connection, configuration: Settings) -> Report:
    """Attest the immutable Neon project/branch and configured endpoint."""
    from app.core.test_database import read_test_database_identity

    return read_test_database_identity(
        connection,
        endpoint_id=configuration.TEST_DATABASE_ENDPOINT_ID,
        branch_id=configuration.TEST_DATABASE_BRANCH_ID,
        project_id=configuration.TEST_DATABASE_PROJECT_ID,
        protected_branch_id=configuration.PROTECTED_DATABASE_BRANCH_ID,
    )


def _schema_state(connection: Connection) -> Report:
    """Read the dedicated test revision and public-table count without row data."""
    revision = connection.execute(
        text("SELECT version_num FROM public.alembic_version")
    ).scalar_one()
    table_count = len(inspect(connection).get_table_names(schema="public"))
    if revision != EXPECTED_TEST_REVISION or table_count != EXPECTED_PUBLIC_TABLE_COUNT:
        raise StartupVerificationError("development_schema_state_unexpected")
    return {
        "installed_revision": revision,
        "public_table_count": table_count,
    }


async def preflight(*, engine: AsyncEngine, configuration: Settings) -> Report:
    """Complete the live read-only gate before importing any application module."""
    _require_read_only_guard(engine=engine)
    async with engine.connect() as connection:
        try:
            identity = await connection.run_sync(
                partial(_identity, configuration=configuration)
            )
            current_read_only = (
                await connection.execute(text("SHOW transaction_read_only"))
            ).scalar_one()
            default_read_only = (
                await connection.execute(text("SHOW default_transaction_read_only"))
            ).scalar_one()
            if current_read_only != "on":
                raise StartupVerificationError("development_read_only_mode_required")
            schema = await connection.run_sync(_schema_state)
        finally:
            await connection.rollback()
    return (
        identity
        | schema
        | {
            "read_only": True,
            "transaction_read_only": current_read_only,
            "default_transaction_read_only": default_read_only,
            "read_only_begin_guard_installed": True,
            "tls_hostname_verified": True,
            "preflight_passed": True,
        }
    )


# ==============================================
# REAL FASTAPI LIFECYCLE WITH TEST-ONLY BINDINGS
# ==============================================


async def application_lifecycle(
    *,
    engine: AsyncEngine,
    configuration: Settings,
    database_url: str,
) -> Report:
    """Run real startup/shutdown and two local ASGI requests with restored globals."""
    _require_read_only_guard(engine=engine)
    sessions = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    # app.core's initializer can construct its default engine before the gate;
    # importing it does not open a connection. Replace its operational bindings
    # before importing routes, and confine any later URL reads to the test URL.
    with (
        patch.object(configuration, "DATABASE_URL", database_url),
        sanitized_application_errors(),
        patch.object(
            httpx.HTTPTransport,
            "handle_request",
            side_effect=StartupVerificationError("outbound_http_forbidden"),
        ) as synchronous_network,
        patch.object(
            httpx.AsyncHTTPTransport,
            "handle_async_request",
            side_effect=StartupVerificationError("outbound_http_forbidden"),
        ) as asynchronous_network,
    ):
        database = importlib.import_module("app.core.database")
        core_package = importlib.import_module("app.core")
        with (
            patch.object(database, "engine", engine),
            patch.object(database, "AsyncSessionLocal", sessions),
            patch.object(core_package, "AsyncSessionLocal", sessions),
        ):
            application = importlib.import_module("app.main")
            if (
                application.init_db is not database.init_db
                or application.close_db is not database.close_db
            ):
                raise StartupVerificationError(
                    "application_database_lifecycle_replaced"
                )
            callback_router = importlib.import_module("app.core.router_instance").router
            original_routes = list(callback_router.routes)
            close_monitor = AsyncMock(wraps=database.close_db)
            try:
                with patch.object(application, "close_db", close_monitor):
                    async with application.app.router.lifespan_context(application.app):
                        # Exercise the patched factory as well as init_db's engine.
                        async with database.AsyncSessionLocal() as session:
                            try:
                                session_read_only = (
                                    await session.execute(
                                        text("SHOW transaction_read_only")
                                    )
                                ).scalar_one()
                                if session_read_only != "on":
                                    raise StartupVerificationError(
                                        "application_session_not_read_only"
                                    )
                            finally:
                                await session.rollback()
                        transport = httpx.ASGITransport(app=application.app)
                        async with httpx.AsyncClient(
                            transport=transport,
                            base_url="http://localhost",
                            follow_redirects=False,
                        ) as client:
                            root = await client.get("/")
                            health = await client.get("/health")
                        if root.status_code != 200 or health.status_code != 200:
                            raise StartupVerificationError(
                                "application_health_request_failed"
                            )
                        root_body = root.json()
                        health_body = health.json()
                        if (
                            not isinstance(root_body, dict)
                            or root_body.get("message") != "Welcome to MoulAI Platform"
                            or not isinstance(health_body, dict)
                            or health_body.get("status") != "healthy"
                        ):
                            raise StartupVerificationError(
                                "application_health_response_unexpected"
                            )
                if close_monitor.await_count != 1:
                    raise StartupVerificationError("application_shutdown_not_observed")
            finally:
                callback_router.routes[:] = original_routes
            if synchronous_network.call_count or asynchronous_network.call_count:
                raise StartupVerificationError("unexpected_outbound_http_attempt")
    return {
        "real_init_db_used": True,
        "lifespan_startup_completed": True,
        "lifespan_shutdown_completed": True,
        "real_close_db_awaited_once": True,
        "session_factory_read_only": True,
        "root_status": root.status_code,
        "health_status": health.status_code,
        "health_payload_verified": True,
        "outbound_http_transport_calls": 0,
        "patched_globals_restored": True,
    }


# ==============================================
# VERIFICATION ORCHESTRATION AND SANITIZED ARTIFACT
# ==============================================


async def verify_startup() -> Report:
    """Dispose the isolated engine even when identity or application checks fail."""
    engine, configuration, database_url = development_engine()
    try:
        identity = await preflight(engine=engine, configuration=configuration)
        logger.info("development_startup_identity_verified")
        lifecycle = await application_lifecycle(
            engine=engine,
            configuration=configuration,
            database_url=database_url,
        )
        logger.info("development_startup_verification_completed")
        return {
            "completed": True,
            "preflight": identity,
            "application": lifecycle,
            "production_touched": False,
            "database_mode": "read_only",
        }
    finally:
        await engine.dispose()


def _write_report(*, report: Report) -> None:
    """Atomically write valid UTF-8 JSON separately from runtime console logs."""
    directory = PROJECT_ROOT / "artifacts" / "billing-production-review"
    directory.mkdir(parents=True, exist_ok=True)
    source_paths = (
        "scripts/verify_development_startup.py",
        "app/main.py",
        "app/core/database.py",
        "app/core/test_database.py",
    )
    result = report | {
        "reported_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "source_files_sha256": {
            path: hashlib.sha256((PROJECT_ROOT / path).read_bytes()).hexdigest()
            for path in source_paths
        },
    }
    target = directory / REPORT_FILENAME
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(target)
    print(json.dumps(result, indent=2, ensure_ascii=False))


def main() -> int:
    """Run the standalone verifier and report failures without raw exceptions."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    try:
        report = asyncio.run(verify_startup())
    except Exception as error:
        report = {
            "completed": False,
            "reason": (
                str(error)
                if isinstance(error, StartupVerificationError)
                else (
                    "unsafe_development_target"
                    if (
                        type(error).__module__ == "app.core.test_database"
                        and type(error).__name__ == "UnsafeTestDatabaseError"
                    )
                    else "development_startup_verification_failed"
                )
            ),
            "error_type": type(error).__name__,
        }
        logger.error("development_startup_verification_failed")
    try:
        _write_report(report=report)
    except OSError:
        print(json.dumps({"completed": False, "reason": "startup_report_write_failed"}))
        return 1
    return 0 if report["completed"] else 1


if __name__ == "__main__":
    sys.exit(main())
