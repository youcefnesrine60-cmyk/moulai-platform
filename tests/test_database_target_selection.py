# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Verify explicit ORM target selection without .env reads or database access.

Run directly with unittest. Package initializers, engine construction, and
sessions are replaced by offline module/engine doubles. The real settings model
and pure test-database contract are loaded from source, with dotenv/environment
sources excluded. Startup tests exercise the identity/schema ordering contract.
The separate startup-schema tests cover actual SQLAlchemy schema inspection.
"""

from __future__ import annotations

import importlib.util
import os
import ssl
import sys
import unittest
from collections.abc import (
    Callable,
    Iterator,
)
from contextlib import contextmanager
from pathlib import Path
from types import (
    ModuleType,
    SimpleNamespace,
)
from typing import (
    Any,
    Literal,
)
from unittest.mock import (
    AsyncMock,
    MagicMock,
    patch,
)

from pydantic import ValidationError
from pydantic_settings import BaseSettings
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRIMARY_URL = "postgresql+asyncpg://primary.invalid/neondb"
DEVELOPMENT_URL = (
    "postgresql+asyncpg://ep-development-offline.region.neon.tech/neondb_test"
)
SAFE_MODEL_ENVIRONMENT = {
    "DEBUG": "false",
    "BOT_TOKEN": "offline-settings-validation",
    "OPENAI_API_KEY": "offline-settings-validation",
    "SECRET_KEY": "offline-settings-validation-key-length-32",
}


# ==============================================
# NONCONNECTING SOURCE LOADERS AND CONFIGURATION
# ==============================================


def load_source(*, name: str, relative_path: str) -> ModuleType:
    """Load a real source module under temporary offline package bindings."""
    specification = importlib.util.spec_from_file_location(
        name, PROJECT_ROOT / relative_path
    )
    if specification is None or specification.loader is None:
        raise AssertionError("The offline source module could not be loaded")
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    specification.loader.exec_module(module)
    return module


def declared_configuration(*, target: str = "primary") -> SimpleNamespace:
    """Return synthetic target metadata without any real credential or endpoint."""
    return SimpleNamespace(
        DATABASE_TARGET=target,
        APP_ENV="development",
        DATABASE_URL=PRIMARY_URL,
        TEST_DATABASE_URL=DEVELOPMENT_URL,
        TEST_DATABASE_ENDPOINT_ID="ep-development-offline",
        PROTECTED_DATABASE_ENDPOINT_ID="ep-protected-offline",
        TEST_DATABASE_BRANCH_ID="br-development-offline",
        TEST_DATABASE_PROJECT_ID="project-offline",
        PROTECTED_DATABASE_BRANCH_ID="br-protected-offline",
        DB_ECHO=False,
        DB_POOL_SIZE=1,
        DB_MAX_OVERFLOW=0,
        DB_POOL_TIMEOUT=5,
        DB_POOL_PRE_PING=True,
        DB_POOL_RECYCLE=300,
    )


def offline_packages() -> dict[str, ModuleType]:
    """Avoid app.core's engine and AI-client import side effects."""
    application = ModuleType("app")
    application.__path__ = []
    core = ModuleType("app.core")
    core.__path__ = []
    application_logger = ModuleType("app.core.logger")
    application_logger.logger = MagicMock()
    models = ModuleType("app.models")
    models.__path__ = []
    base = ModuleType("app.models.base")
    base.Base = SimpleNamespace(metadata=MagicMock())
    return {
        "app": application,
        "app.core": core,
        "app.core.logger": application_logger,
        "app.models": models,
        "app.models.base": base,
    }


@contextmanager
def offline_settings_model() -> Iterator[ModuleType]:
    """Use the real Literal field while disabling every .env source."""
    original_initialize = BaseSettings.__init__

    def initialize_without_dotenv(
        instance: BaseSettings, *arguments: Any, **options: Any
    ) -> None:
        """Force the global Settings() initializer to ignore its env_file."""
        options["_env_file"] = None
        original_initialize(instance, *arguments, **options)

    with (
        patch.dict(sys.modules, offline_packages()),
        patch.dict(os.environ, SAFE_MODEL_ENVIRONMENT, clear=True),
        patch("dotenv.load_dotenv"),
        patch.object(BaseSettings, "__init__", initialize_without_dotenv),
    ):
        yield load_source(name="app.core.config", relative_path="app/core/config.py")


@contextmanager
def offline_database(
    *, settings: SimpleNamespace
) -> Iterator[tuple[Callable[[], ModuleType], MagicMock, MagicMock]]:
    """Expose the real database module through nonconnecting engine factories."""
    modules = offline_packages()
    config = ModuleType("app.core.config")
    config.DatabaseTarget = Literal["primary", "development"]
    config.Settings = SimpleNamespace
    config.settings = settings
    modules["app.core.config"] = config
    with (
        patch.dict(sys.modules, modules),
        patch("dotenv.load_dotenv"),
        patch("sqlalchemy.ext.asyncio.create_async_engine") as create_engine,
        patch("sqlalchemy.ext.asyncio.async_sessionmaker") as create_sessions,
    ):
        create_engine.return_value = MagicMock(spec=AsyncEngine)
        load_source(
            name="app.core.test_database", relative_path="app/core/test_database.py"
        )

        def load_database() -> ModuleType:
            """Resolve the selected target while engine construction stays mocked."""
            return load_source(
                name="app.core.database", relative_path="app/core/database.py"
            )

        yield load_database, create_engine, create_sessions


# ==============================================
# SETTINGS LITERAL AND EXPLICIT TARGET SELECTION
# ==============================================


class TestDatabaseTargetSettings(unittest.TestCase):
    """Keep primary as the explicit default and reject unknown target values."""

    def test_default_target_preserves_primary(self) -> None:
        """Creating the real settings model never opts into development by default."""
        with offline_settings_model() as config:
            self.assertEqual(config.settings.DATABASE_TARGET, "primary")

    def test_only_declared_targets_are_accepted(self) -> None:
        """Validate both supported Literal values without reading operator values."""
        with offline_settings_model() as config:
            for target in ("primary", "development"):
                with self.subTest(target=target):
                    model = config.Settings(DATABASE_TARGET=target)
                    self.assertEqual(model.DATABASE_TARGET, target)

    def test_unknown_or_empty_target_is_rejected(self) -> None:
        """Reject accidental mode strings instead of selecting another database."""
        with offline_settings_model() as config:
            for target in ("", "test", "production", "Development"):
                with self.subTest(target=target), self.assertRaises(ValidationError):
                    config.Settings(DATABASE_TARGET=target)


class TestDatabaseTargetEngine(unittest.TestCase):
    """Construct only the declared engine and preserve the primary URL setting."""

    def test_primary_does_not_require_development_configuration(self) -> None:
        """Retain the existing primary behavior when test values are absent."""
        settings = declared_configuration()
        settings.TEST_DATABASE_URL = ""
        settings.TEST_DATABASE_ENDPOINT_ID = None
        settings.TEST_DATABASE_BRANCH_ID = None
        settings.TEST_DATABASE_PROJECT_ID = None
        with offline_database(settings=settings) as (load, engines, sessions):
            database = load()
            self.assertEqual(engines.call_args.args, (PRIMARY_URL,))
            self.assertEqual(engines.call_args.kwargs["connect_args"], {})
            self.assertIs(sessions.call_args.args[0], engines.return_value)
            self.assertIs(database.AsyncSessionLocal, sessions.return_value)
            self.assertEqual(database._DATABASE_CONFIGURATION.target, "primary")
        self.assertEqual(settings.DATABASE_URL, PRIMARY_URL)

    def test_explicit_development_uses_verified_test_url_and_tls(self) -> None:
        """Use the centralized URL/branch guards for both permitted APP_ENV values."""
        for environment in ("development", "test"):
            settings = declared_configuration(target="development")
            settings.APP_ENV = environment
            with (
                self.subTest(environment=environment),
                offline_database(settings=settings) as (load, engines, sessions),
            ):
                database = load()
                self.assertEqual(engines.call_args.args, (DEVELOPMENT_URL,))
                arguments = engines.call_args.kwargs["connect_args"]
                self.assertTrue(arguments["ssl"].check_hostname)
                self.assertEqual(arguments["ssl"].verify_mode, ssl.CERT_REQUIRED)
                self.assertEqual(arguments["server_settings"]["search_path"], "public")
                self.assertIs(sessions.call_args.args[0], engines.return_value)
                self.assertEqual(
                    database._DATABASE_CONFIGURATION.branch_id,
                    "br-development-offline",
                )
            self.assertEqual(settings.DATABASE_URL, PRIMARY_URL)

    def test_unsafe_development_profiles_fail_before_engine_creation(self) -> None:
        """Exercise each required guard rather than falling back to primary."""
        mutations = (
            {"APP_ENV": "production"},
            {"APP_ENV": "staging"},
            {"APP_ENV": "testing"},
            {"TEST_DATABASE_ENDPOINT_ID": "ep-protected-offline"},
            {"TEST_DATABASE_BRANCH_ID": "br-protected-offline"},
            {"TEST_DATABASE_PROJECT_ID": None},
            {"TEST_DATABASE_URL": PRIMARY_URL},
            {"TEST_DATABASE_URL": DEVELOPMENT_URL + "?host=protected.invalid"},
            {"DATABASE_TARGET": "unknown"},
        )
        for mutation in mutations:
            settings = declared_configuration(target="development")
            settings.__dict__.update(mutation)
            with (
                self.subTest(fields=tuple(mutation)),
                offline_database(settings=settings) as (load, engines, sessions),
                self.assertRaises(RuntimeError) as failure,
            ):
                load()
            engines.assert_not_called()
            sessions.assert_not_called()
            self.assertNotIn(PRIMARY_URL, str(failure.exception))
            self.assertNotIn(DEVELOPMENT_URL, str(failure.exception))

    def test_configuration_repr_does_not_include_urls(self) -> None:
        """Avoid accidental credential disclosure through engine-profile logging."""
        settings = declared_configuration(target="development")
        with offline_database(settings=settings) as (load, _engines, _sessions):
            database = load()
            representation = repr(database._DATABASE_CONFIGURATION)
        self.assertNotIn(DEVELOPMENT_URL, representation)
        self.assertNotIn(PRIMARY_URL, representation)


# ==============================================
# LIVE IDENTITY ORDERING WITH NONCONNECTING DOUBLES
# ==============================================


class TestDatabaseTargetStartup(unittest.IsolatedAsyncioTestCase):
    """Require development identity before schema validation on one connection."""

    def connection_for(self, *, engine: MagicMock) -> AsyncMock:
        """Install a nonconnecting connection that executes supplied sync callbacks."""
        connection = AsyncMock(spec=AsyncConnection)
        engine.connect.return_value.__aenter__.return_value = connection
        synchronous_connection = MagicMock(spec=Connection)

        async def run_sync(callback: Callable[[Connection], Any]) -> Any:
            """Use one known offline connection for identity and schema callbacks."""
            return callback(synchronous_connection)

        connection.run_sync.side_effect = run_sync
        return connection

    async def test_development_attests_identity_then_validates_schema(self) -> None:
        """Complete read-only startup without DDL, DML, or automatic migrations."""
        settings = declared_configuration(target="development")
        order: list[str] = []

        def record_identity(
            connection: Connection, **identity_arguments: str | None
        ) -> None:
            """Record successful identity verification without a server request."""
            order.append("identity")

        def record_schema(connection: Connection) -> None:
            """Record the later schema check on the same offline connection."""
            order.append("schema")

        with offline_database(settings=settings) as (load, engines, _sessions):
            database = load()
            connection = self.connection_for(engine=engines.return_value)
            with (
                patch.object(
                    database,
                    "read_test_database_identity",
                    side_effect=record_identity,
                ) as identity,
                patch.object(
                    database,
                    "_validate_schema",
                    side_effect=record_schema,
                ) as schema,
            ):
                await database.init_db()
            self.assertEqual(order, ["identity", "schema"])
            self.assertIs(identity.call_args.args[0], schema.call_args.args[0])
            self.assertEqual(
                identity.call_args.kwargs["branch_id"], "br-development-offline"
            )
            self.assertEqual(
                [str(call.args[0]) for call in connection.execute.await_args_list],
                ["SET TRANSACTION READ ONLY"],
            )
            connection.rollback.assert_awaited_once()
            engines.return_value.begin.assert_not_called()
            database.Base.metadata.create_all.assert_not_called()
            database.Base.metadata.drop_all.assert_not_called()

    async def test_wrong_identity_blocks_schema_and_finishes_transaction(self) -> None:
        """Fail closed before schema inspection when the server identity is wrong."""
        settings = declared_configuration(target="development")
        with offline_database(settings=settings) as (load, engines, _sessions):
            database = load()
            connection = self.connection_for(engine=engines.return_value)
            with (
                patch.object(
                    database,
                    "read_test_database_identity",
                    side_effect=RuntimeError("identity_validation_failed"),
                ),
                patch.object(database, "_validate_schema") as schema,
                self.assertRaisesRegex(RuntimeError, "identity_validation_failed"),
            ):
                await database.init_db()
            schema.assert_not_called()
            connection.rollback.assert_awaited_once()
            engines.return_value.connect.return_value.__aexit__.assert_awaited_once()

    async def test_schema_failure_does_not_leave_development_transaction(self) -> None:
        """Preserve explicit migration failures and release the read-only connection."""
        settings = declared_configuration(target="development")
        with offline_database(settings=settings) as (load, engines, _sessions):
            database = load()
            connection = self.connection_for(engine=engines.return_value)
            with (
                patch.object(database, "read_test_database_identity"),
                patch.object(
                    database,
                    "_validate_schema",
                    side_effect=RuntimeError("explicit migration required"),
                ),
                self.assertRaisesRegex(RuntimeError, "explicit migration required"),
            ):
                await database.init_db()
            connection.rollback.assert_awaited_once()
            database.Base.metadata.create_all.assert_not_called()

    async def test_primary_inspects_schema_without_development_identity(self) -> None:
        """Keep the primary path independent from missing test identity settings."""
        settings = declared_configuration()
        with offline_database(settings=settings) as (load, engines, _sessions):
            database = load()
            connection = self.connection_for(engine=engines.return_value)
            with (
                patch.object(database, "read_test_database_identity") as identity,
                patch.object(database, "_validate_schema") as schema,
            ):
                await database.init_db()
            identity.assert_not_called()
            schema.assert_called_once()
            connection.execute.assert_not_awaited()

    async def test_identity_contract_remains_paired_with_the_constructed_engine(
        self,
    ) -> None:
        """Do not weaken the captured gate when mutable settings change later."""
        settings = declared_configuration(target="development")
        with offline_database(settings=settings) as (load, engines, _sessions):
            database = load()
            connection = self.connection_for(engine=engines.return_value)
            settings.DATABASE_TARGET = "primary"
            settings.TEST_DATABASE_BRANCH_ID = "br-changed-after-creation"
            with (
                patch.object(database, "read_test_database_identity") as identity,
                patch.object(database, "_validate_schema"),
            ):
                await database.init_db()
            self.assertEqual(
                identity.call_args.kwargs["branch_id"], "br-development-offline"
            )
            connection.rollback.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
