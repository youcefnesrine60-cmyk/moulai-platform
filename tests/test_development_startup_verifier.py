# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Exercise startup-verifier safety without settings imports or database access.

Run with unittest directly. These tests never import the PostgreSQL fixtures in
conftest.py. Database engines, sessions, and application modules are offline test
doubles; HTTP uses a real in-process FastAPI/ASGITransport pair. Target validation
uses the real standalone test_database.py contract without app.core side effects.
"""

from __future__ import annotations

import importlib.util
import io
import json
import logging
import ssl
import sys
import tempfile
import unittest
from collections.abc import (
    AsyncIterator,
    Iterator,
)
from contextlib import (
    asynccontextmanager,
    contextmanager,
    redirect_stdout,
)
from pathlib import Path
from types import (
    ModuleType,
    SimpleNamespace,
)
from typing import (
    Any,
    cast,
)
from unittest.mock import (
    AsyncMock,
    MagicMock,
    patch,
)

import httpx
from fastapi import FastAPI
from sqlalchemy import (
    create_engine,
    event,
    text,
)
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
)
from starlette.responses import JSONResponse

from scripts import verify_development_startup as verifier

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REAL_IMPORT_MODULE = importlib.import_module
OFFLINE_DATABASE_URL = (
    "postgresql+asyncpg://ep-development-offline.region.neon.tech/neondb_test"
)


# ==============================================
# OFFLINE VALUES AND REAL TARGET-CONTRACT LOADING
# ==============================================


class ScalarResult:
    """Expose only the synchronous scalar interface used by verifier reads."""

    def __init__(self, value: Any) -> None:
        """Store an offline scalar, without creating a database result."""
        self.value = value

    def scalar_one(self) -> Any:
        """Return the declared test scalar."""
        return self.value


def configuration() -> SimpleNamespace:
    """Return explicit unit-test profile metadata, never a usable credential."""
    return SimpleNamespace(
        APP_ENV="development",
        DATABASE_URL="original-configuration-value",
        TEST_DATABASE_URL=OFFLINE_DATABASE_URL,
        TEST_DATABASE_ENDPOINT_ID="ep-development-offline",
        PROTECTED_DATABASE_ENDPOINT_ID="ep-protected-offline",
        TEST_DATABASE_BRANCH_ID="br-development-offline",
        TEST_DATABASE_PROJECT_ID="project-offline",
        PROTECTED_DATABASE_BRANCH_ID="br-protected-offline",
    )


def offline_guarded_engine(*, install_guard: bool = True) -> MagicMock:
    """Use a real local event dispatcher without connecting the engine double."""
    engine = MagicMock(spec=AsyncEngine)
    engine.sync_engine = create_engine("sqlite+pysqlite:///:memory:")
    if install_guard:
        verifier._install_read_only_guard(engine=engine)
    return engine


def load_target_contract() -> ModuleType:
    """Load the real pure helpers without running app.core.__init__.py."""
    specification = importlib.util.spec_from_file_location(
        "app.core.test_database", PROJECT_ROOT / "app/core/test_database.py"
    )
    if specification is None or specification.loader is None:
        raise AssertionError("The isolated target contract could not be loaded")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


@contextmanager
def offline_configuration(*, settings: SimpleNamespace) -> Iterator[ModuleType]:
    """Expose pure settings/helpers while excluding all real package initializers."""
    application = ModuleType("app")
    application.__path__ = []
    core = ModuleType("app.core")
    core.__path__ = []
    config = ModuleType("app.core.config")
    config.settings = settings
    contract = load_target_contract()
    modules = {
        "app": application,
        "app.core": core,
        "app.core.config": config,
        "app.core.test_database": contract,
    }
    with patch.dict(sys.modules, modules):
        yield contract


# ==============================================
# PROFILE AND READ-ONLY CONNECTION CONTRACTS
# ==============================================


class TestDevelopmentEngineConfiguration(unittest.TestCase):
    """Keep target guards and read-only/TLS defaults ahead of engine creation."""

    def test_every_engine_connection_retains_verified_tls_and_read_only(self) -> None:
        """Preserve helper settings when adding the PostgreSQL read-only default."""
        settings = configuration()
        expected_engine = offline_guarded_engine(install_guard=False)
        self.addCleanup(expected_engine.sync_engine.dispose)
        with (
            offline_configuration(settings=settings),
            patch.object(
                verifier, "create_async_engine", return_value=expected_engine
            ) as create_engine,
        ):
            engine, actual_settings, url = verifier.development_engine()
        self.assertIs(engine, expected_engine)
        self.assertIs(actual_settings, settings)
        self.assertEqual(url, OFFLINE_DATABASE_URL)
        self.assertEqual(create_engine.call_args.args, (OFFLINE_DATABASE_URL,))
        arguments = create_engine.call_args.kwargs["connect_args"]
        self.assertEqual(arguments["server_settings"]["search_path"], "public")
        self.assertEqual(
            arguments["server_settings"]["default_transaction_read_only"], "on"
        )
        self.assertTrue(arguments["ssl"].check_hostname)
        self.assertEqual(arguments["ssl"].verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(
            event.contains(
                engine.sync_engine, "begin", verifier._set_transaction_read_only
            )
        )

    def test_production_environment_is_rejected_without_an_engine(self) -> None:
        """Fail before constructing a verifier engine in production mode."""
        settings = configuration()
        settings.APP_ENV = "production"
        with (
            offline_configuration(settings=settings),
            patch.object(verifier, "create_async_engine") as create_engine,
            self.assertRaisesRegex(
                verifier.StartupVerificationError, "development_environment_required"
            ),
        ):
            verifier.development_engine()
        create_engine.assert_not_called()

    def test_protected_endpoint_is_rejected_without_an_engine(self) -> None:
        """Use the real endpoint contract to exclude the protected target."""
        settings = configuration()
        settings.TEST_DATABASE_ENDPOINT_ID = settings.PROTECTED_DATABASE_ENDPOINT_ID
        with (
            offline_configuration(settings=settings) as contract,
            patch.object(verifier, "create_async_engine") as create_engine,
            self.assertRaises(contract.UnsafeTestDatabaseError),
        ):
            verifier.development_engine()
        create_engine.assert_not_called()


class TestReadOnlyStartupGate(unittest.IsolatedAsyncioTestCase):
    """Protect cleanup and prevent application loading after a failed live gate."""

    def setUp(self) -> None:
        """Create nonconnecting engine/connection doubles for gate behavior."""
        self.engine = offline_guarded_engine()
        self.addCleanup(self.engine.sync_engine.dispose)
        self.connection = AsyncMock(spec=AsyncConnection)
        self.engine.connect.return_value.__aenter__.return_value = self.connection
        self.connection.execute.return_value = ScalarResult("on")
        self.connection.run_sync.side_effect = [
            {"database": "neondb_test"},
            {"installed_revision": verifier.EXPECTED_TEST_REVISION},
        ]

    async def test_successful_gate_finishes_its_read_only_transaction(self) -> None:
        """Rollback metadata reads and leave no verifier transaction open."""
        report = await verifier.preflight(
            engine=self.engine, configuration=cast(Any, configuration())
        )
        self.assertTrue(report["preflight_passed"])
        self.connection.rollback.assert_awaited_once()
        self.connection.commit.assert_not_awaited()
        self.engine.connect.return_value.__aexit__.assert_awaited_once()

    async def test_failed_identity_still_rolls_back_metadata_reads(self) -> None:
        """Close the transaction when immutable identity attestation fails."""
        self.connection.run_sync.side_effect = RuntimeError("identity rejected")
        with self.assertRaisesRegex(RuntimeError, "identity rejected"):
            await verifier.preflight(
                engine=self.engine, configuration=cast(Any, configuration())
            )
        self.connection.rollback.assert_awaited_once()
        self.engine.connect.return_value.__aexit__.assert_awaited_once()

    async def test_read_write_connection_is_rejected_and_rolled_back(self) -> None:
        """Reject unexpected server defaults before importing application routes."""
        self.connection.execute.return_value = ScalarResult("off")
        with self.assertRaisesRegex(
            verifier.StartupVerificationError, "development_read_only_mode_required"
        ):
            await verifier.preflight(
                engine=self.engine, configuration=cast(Any, configuration())
            )
        self.connection.run_sync.assert_awaited_once()
        self.connection.rollback.assert_awaited_once()

    async def test_read_only_transaction_accepts_and_reports_default_off(self) -> None:
        """Require current READ ONLY while recording a reset connection default."""
        self.connection.execute.side_effect = [ScalarResult("on"), ScalarResult("off")]
        report = await verifier.preflight(
            engine=self.engine, configuration=cast(Any, configuration())
        )
        self.assertTrue(report["read_only"])
        self.assertEqual(report["transaction_read_only"], "on")
        self.assertEqual(report["default_transaction_read_only"], "off")
        self.assertTrue(report["read_only_begin_guard_installed"])
        self.connection.rollback.assert_awaited_once()

    async def test_missing_begin_listener_prevents_connection(self) -> None:
        """Refuse the gate before acquiring a connection without its safety event."""
        event.remove(
            self.engine.sync_engine, "begin", verifier._set_transaction_read_only
        )
        with self.assertRaisesRegex(
            verifier.StartupVerificationError, "read_only_transaction_guard_missing"
        ):
            await verifier.preflight(
                engine=self.engine, configuration=cast(Any, configuration())
            )
        self.engine.connect.assert_not_called()

    async def test_identity_failure_blocks_lifecycle_and_disposes_engine(self) -> None:
        """Keep application imports behind the gate and always release the engine."""
        with (
            patch.object(
                verifier,
                "development_engine",
                return_value=(self.engine, configuration(), OFFLINE_DATABASE_URL),
            ),
            patch.object(
                verifier, "preflight", side_effect=RuntimeError("gate failed")
            ),
            patch.object(verifier, "application_lifecycle") as lifecycle,
            self.assertRaisesRegex(RuntimeError, "gate failed"),
        ):
            await verifier.verify_startup()
        lifecycle.assert_not_called()
        self.engine.dispose.assert_awaited_once()

    async def test_lifecycle_failure_still_disposes_engine(self) -> None:
        """Release the test engine after startup, health, or shutdown failures."""
        with (
            patch.object(
                verifier,
                "development_engine",
                return_value=(self.engine, configuration(), OFFLINE_DATABASE_URL),
            ),
            patch.object(
                verifier, "preflight", return_value={"preflight_passed": True}
            ),
            patch.object(
                verifier,
                "application_lifecycle",
                side_effect=RuntimeError("lifecycle failed"),
            ),
            self.assertRaisesRegex(RuntimeError, "lifecycle failed"),
        ):
            await verifier.verify_startup()
        self.engine.dispose.assert_awaited_once()


# ==============================================
# IN-PROCESS ASGI LIFECYCLE AND GLOBAL RESTORATION
# ==============================================


class TestOfflineApplicationLifecycle(unittest.IsolatedAsyncioTestCase):
    """Exercise real ASGI HTTP while all application/database bindings are offline."""

    def setUp(self) -> None:
        """Construct a small lifecycle contract with observable original bindings."""
        self.settings = configuration()
        self.engine = offline_guarded_engine()
        self.addCleanup(self.engine.sync_engine.dispose)
        self.original_engine = MagicMock(spec=AsyncEngine)
        self.original_factory = object()
        self.factory = MagicMock()
        self.session = AsyncMock(spec=AsyncSession)
        self.factory.return_value.__aenter__.return_value = self.session
        self.session.execute.return_value = ScalarResult("on")
        self.database = ModuleType("app.core.database")
        self.database.engine = self.original_engine
        self.database.AsyncSessionLocal = self.original_factory
        self.core = ModuleType("app.core")
        self.core.AsyncSessionLocal = self.original_factory
        self.application = ModuleType("app.main")
        self.routes = SimpleNamespace(routes=["existing-route"])
        self.router_module = ModuleType("app.core.router_instance")
        self.router_module.router = self.routes
        self.health_status = 200
        self.outbound_on_startup = False
        self.observed_bindings: list[bool] = []

        async def initialize_database() -> None:
            """Observe bindings without opening a database connection."""
            self.observed_bindings = [
                self.database.engine is self.engine,
                self.database.AsyncSessionLocal is self.factory,
                self.core.AsyncSessionLocal is self.factory,
                self.settings.DATABASE_URL == OFFLINE_DATABASE_URL,
            ]
            if self.outbound_on_startup:
                httpx.get("https://forbidden.invalid")

        async def close_database() -> None:
            """Exercise the real wrapped-close behavior against an offline engine."""
            await self.database.engine.dispose()

        self.database.init_db = initialize_database
        self.database.close_db = close_database
        self.application.init_db = initialize_database
        self.application.close_db = close_database
        self.original_close = close_database

        @asynccontextmanager
        async def lifespan(application: FastAPI) -> AsyncIterator[None]:
            """Match the application's startup/yield/shutdown ordering."""
            await self.application.init_db()
            self.routes.routes.append("startup-registration")
            yield
            await self.application.close_db()

        async def root() -> dict[str, str]:
            """Return the real root endpoint's public contract."""
            return {"message": "Welcome to MoulAI Platform"}

        async def health() -> JSONResponse:
            """Allow a controlled health failure without any outbound transport."""
            return JSONResponse(
                content={"status": "healthy"}, status_code=self.health_status
            )

        self.application.app = FastAPI(lifespan=lifespan)
        self.application.app.add_api_route("/", root, methods=["GET"])
        self.application.app.add_api_route("/health", health, methods=["GET"])

    def _import_module(self, name: str, package: str | None = None) -> ModuleType:
        """Reject application imports outside the declared offline surface."""
        modules = {
            "app.core.database": self.database,
            "app.core": self.core,
            "app.main": self.application,
            "app.core.router_instance": self.router_module,
        }
        if name in modules:
            return modules[name]
        if name.startswith("app."):
            raise AssertionError("Unexpected application import in offline test")
        return REAL_IMPORT_MODULE(name, package)

    @contextmanager
    def _bindings(self) -> Iterator[None]:
        """Keep all database/app objects nonconnecting throughout each scenario."""
        with (
            patch.object(verifier, "async_sessionmaker", return_value=self.factory),
            patch.object(
                verifier.importlib, "import_module", side_effect=self._import_module
            ),
        ):
            yield

    def _assert_original_bindings(self) -> None:
        """Require every modified global and route registration to be restored."""
        self.assertIs(self.database.engine, self.original_engine)
        self.assertIs(self.database.AsyncSessionLocal, self.original_factory)
        self.assertIs(self.core.AsyncSessionLocal, self.original_factory)
        self.assertIs(self.application.close_db, self.original_close)
        self.assertEqual(self.settings.DATABASE_URL, "original-configuration-value")
        self.assertEqual(self.routes.routes, ["existing-route"])
        self.original_engine.dispose.assert_not_awaited()

    async def test_success_uses_test_bindings_and_awaits_wrapped_close(self) -> None:
        """Run GET / and /health with a real in-process ASGI transport."""
        with self._bindings():
            report = await verifier.application_lifecycle(
                engine=self.engine,
                configuration=cast(Any, self.settings),
                database_url=OFFLINE_DATABASE_URL,
            )
        self.assertTrue(all(self.observed_bindings))
        self.assertEqual(report["root_status"], 200)
        self.assertEqual(report["health_status"], 200)
        self.assertEqual(report["outbound_http_transport_calls"], 0)
        self.engine.dispose.assert_awaited_once()
        self.session.rollback.assert_awaited_once()
        self._assert_original_bindings()

    async def test_failed_health_restores_globals_and_registration(self) -> None:
        """Restore bindings even if an exception enters the lifespan's yield."""
        self.health_status = 503
        with (
            self._bindings(),
            self.assertRaisesRegex(
                verifier.StartupVerificationError, "application_health_request_failed"
            ),
        ):
            await verifier.application_lifecycle(
                engine=self.engine,
                configuration=cast(Any, self.settings),
                database_url=OFFLINE_DATABASE_URL,
            )
        self.session.rollback.assert_awaited_once()
        self._assert_original_bindings()

    async def test_read_write_session_is_rolled_back_and_rejected(self) -> None:
        """Fail a factory binding that does not preserve server read-only mode."""
        self.session.execute.return_value = ScalarResult("off")
        with (
            self._bindings(),
            self.assertRaisesRegex(
                verifier.StartupVerificationError, "application_session_not_read_only"
            ),
        ):
            await verifier.application_lifecycle(
                engine=self.engine,
                configuration=cast(Any, self.settings),
                database_url=OFFLINE_DATABASE_URL,
            )
        self.session.rollback.assert_awaited_once()
        self._assert_original_bindings()

    async def test_unexpected_outbound_http_fails_before_network_io(self) -> None:
        """Block a real httpx client before its socket transport can execute."""
        self.outbound_on_startup = True
        with (
            self._bindings(),
            self.assertRaisesRegex(
                verifier.StartupVerificationError, "outbound_http_forbidden"
            ),
        ):
            await verifier.application_lifecycle(
                engine=self.engine,
                configuration=cast(Any, self.settings),
                database_url=OFFLINE_DATABASE_URL,
            )
        self._assert_original_bindings()

    async def test_replaced_initializer_is_rejected_before_lifespan(self) -> None:
        """Require the unmodified database initializer rather than a test stub."""
        self.application.init_db = AsyncMock()
        with (
            self._bindings(),
            self.assertRaisesRegex(
                verifier.StartupVerificationError,
                "application_database_lifecycle_replaced",
            ),
        ):
            await verifier.application_lifecycle(
                engine=self.engine,
                configuration=cast(Any, self.settings),
                database_url=OFFLINE_DATABASE_URL,
            )
        self.application.init_db.assert_not_awaited()
        self._assert_original_bindings()

    async def test_missing_guard_blocks_application_session_construction(self) -> None:
        """Recheck the guard before importing routes or creating the app factory."""
        event.remove(
            self.engine.sync_engine, "begin", verifier._set_transaction_read_only
        )
        with (
            patch.object(verifier, "async_sessionmaker") as sessions,
            self.assertRaisesRegex(
                verifier.StartupVerificationError, "read_only_transaction_guard_missing"
            ),
        ):
            await verifier.application_lifecycle(
                engine=self.engine,
                configuration=cast(Any, self.settings),
                database_url=OFFLINE_DATABASE_URL,
            )
        sessions.assert_not_called()
        self._assert_original_bindings()


# ==============================================
# REAL SQLALCHEMY BEGIN EVENT ORDERING WITHOUT POSTGRESQL
# ==============================================


class TestReadOnlyBeginEvent(unittest.TestCase):
    """Use a real local engine and intercept only PostgreSQL's SET statement."""

    def test_guard_precedes_sql_in_every_transaction_without_duplicate_events(
        self,
    ) -> None:
        """Observe the begin event twice around real SELECT/rollback/SELECT/commit."""
        engine = offline_guarded_engine()
        self.addCleanup(engine.sync_engine.dispose)
        verifier._install_read_only_guard(engine=engine)
        original_execute = engine.sync_engine.dialect.do_execute
        statements: list[str] = []

        def execute_statement(
            cursor: Any,
            statement: str,
            parameters: Any,
            context: Any = None,
        ) -> None:
            """Record ordering while SQLite runs actual SELECT statements locally."""
            statements.append(statement)
            if statement == "SET TRANSACTION READ ONLY":
                return
            original_execute(cursor, statement, parameters, context)

        with patch.object(
            engine.sync_engine.dialect, "do_execute", side_effect=execute_statement
        ):
            with engine.sync_engine.connect() as connection:
                self.assertEqual(connection.execute(text("SELECT 1")).scalar_one(), 1)
                connection.rollback()
                self.assertEqual(connection.execute(text("SELECT 2")).scalar_one(), 2)
                connection.commit()
        self.assertEqual(
            statements,
            [
                "SET TRANSACTION READ ONLY",
                "SELECT 1",
                "SET TRANSACTION READ ONLY",
                "SELECT 2",
            ],
        )

    def test_failed_read_only_statement_prevents_application_sql(self) -> None:
        """Fail the transaction if the safety statement cannot execute."""
        engine = offline_guarded_engine()
        self.addCleanup(engine.sync_engine.dispose)
        with patch.object(
            engine.sync_engine.dialect,
            "do_execute",
            side_effect=RuntimeError("read-only guard rejected"),
        ) as execute:
            with engine.sync_engine.connect() as connection:
                with self.assertRaisesRegex(RuntimeError, "read-only guard rejected"):
                    connection.execute(text("SELECT 1"))
        self.assertEqual(execute.call_count, 1)
        self.assertEqual(execute.call_args.args[1], "SET TRANSACTION READ ONLY")


# ==============================================
# SAFE LOGGING AND INDEPENDENT JSON ARTIFACT
# ==============================================


class TestStartupReportSafety(unittest.TestCase):
    """Protect standalone JSON evidence from console logs and exception details."""

    def test_error_filter_removes_raw_exception_content_and_is_restored(self) -> None:
        """Redact unsafe error fields without retaining a global logging filter."""
        application_logger = logging.getLogger(verifier.APPLICATION_LOGGER_NAME)
        original_filters = list(application_logger.filters)
        record = logging.LogRecord(
            "offline", logging.ERROR, __file__, 1, "private %s", ("details",), None
        )
        record.__dict__["error"] = "private-error-details"
        record.exc_text = "private traceback"
        with self.assertRaisesRegex(RuntimeError, "controlled failure"):
            with verifier.sanitized_application_errors():
                for error_filter in application_logger.filters:
                    error_filter.filter(record)
                raise RuntimeError("controlled failure")
        self.assertEqual(application_logger.filters, original_filters)
        self.assertEqual(record.getMessage(), "development_startup_application_error")
        self.assertEqual(record.__dict__["error"], "redacted")
        self.assertIsNone(record.exc_text)

    def test_artifact_is_valid_utf8_json_with_source_hashes(self) -> None:
        """Keep the artifact independently parseable and replace its temp file."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            for source in (
                "scripts/verify_development_startup.py",
                "app/main.py",
                "app/core/database.py",
                "app/core/test_database.py",
            ):
                target = root / source
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((PROJECT_ROOT / source).read_bytes())
            console = io.StringIO()
            with (
                patch.object(verifier, "PROJECT_ROOT", root),
                redirect_stdout(console),
            ):
                verifier._write_report(report={"completed": True})
            artifact = (
                root
                / "artifacts"
                / "billing-production-review"
                / verifier.REPORT_FILENAME
            )
            report = json.loads(artifact.read_text(encoding="utf-8"))
            self.assertEqual(report, json.loads(console.getvalue()))
            self.assertEqual(len(report["source_sha256"]), 64)
            self.assertEqual(len(report["source_files_sha256"]), 4)
            self.assertFalse(artifact.with_suffix(".json.tmp").exists())

    def test_cli_failure_does_not_report_untrusted_exception_text(self) -> None:
        """Return a stable failure and nonzero exit status without loading config."""
        with (
            patch.object(sys, "argv", ["verify_development_startup.py"]),
            patch.object(verifier.logging, "basicConfig"),
            patch.object(verifier.logger, "error"),
            patch.object(
                verifier,
                "verify_startup",
                side_effect=RuntimeError("private-connection-details"),
            ),
            patch.object(verifier, "_write_report") as write_report,
        ):
            status = verifier.main()
        report = write_report.call_args.kwargs["report"]
        self.assertEqual(status, 1)
        self.assertEqual(report["reason"], "development_startup_verification_failed")
        self.assertNotIn("private-connection-details", json.dumps(report))


if __name__ == "__main__":
    unittest.main()
