# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Exercise the real shared pytest boundary without connecting to a database."""

import importlib.util
import os
import subprocess
import sys
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from types import (
    ModuleType,
    SimpleNamespace,
)
from typing import Any
from unittest.mock import (
    AsyncMock,
    MagicMock,
)

import pytest

ROOT = Path(__file__).resolve().parents[1]


# ==============================================
# TENANT-E1 CASES REQUIRE THEIR OWN LOCAL PROFILE
# ==============================================


@pytest.mark.parametrize(
    "arguments,profile,expected",
    [
        ((), "legacy", "1 skipped"),
        (("--run-database-tests",), "legacy", "1 skipped"),
        (("--local-postgres-tests",), "legacy", "1 skipped"),
        (("--local-postgres-tests",), "k10", "1 passed"),
    ],
)
def test_k10_cases_require_the_local_e1_profile(
    boundary_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
    arguments: tuple[str, ...],
    profile: str,
    expected: str,
) -> None:
    """A remote opt-in or the historical local profile cannot execute E1 fixtures."""
    monkeypatch.setenv("LOCAL_POSTGRES_TEST_PROFILE", profile)
    monkeypatch.setenv("LOCAL_POSTGRES_TEST_INSTANCE_ID", "a" * 32)
    monkeypatch.setenv("LOCAL_POSTGRES_TEST_SERVER_PORT", "55432")
    monkeypatch.setenv(
        "LOCAL_POSTGRES_TEST_URL",
        "postgresql+asyncpg://moulai_pytest:unit-test-password-never-used@127.0.0.1:55432/moulai_pytest",
    )
    result = run_boundary_project(
        directory=boundary_directory,
        arguments=arguments,
        source="""
import pytest

@pytest.mark.k10_postgres
def test_synthetic_e1_case():
    assert True
""",
    )
    assert result.returncode == 0
    assert expected in result.stdout


# ==============================================
# ISOLATE CHILD PYTEST FILES INSIDE THE WRITABLE WORKSPACE
# ==============================================


@pytest.fixture
def boundary_directory() -> Iterator[Path]:
    """Own one disposable directory without using the Windows pytest temp root."""
    temporary_root = ROOT / "artifacts" / "test-runner-fix" / "temporary"
    if not temporary_root.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError(
            "Boundary test temporary storage must stay in the workspace."
        )
    temporary_root.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="boundary-", dir=temporary_root) as name:
        directory = Path(name).resolve()
        if not directory.is_relative_to(temporary_root.resolve()):
            raise RuntimeError("Boundary test temporary directory escaped its root.")
        yield directory


# ==============================================
# LOAD THE SHARED FIXTURE DEFINITIONS WITHOUT RUNNING PYTEST HOOKS
# ==============================================


@pytest.fixture
def fixture_module() -> ModuleType:
    """Import definitions only; import must not create a PostgreSQL engine."""
    spec = importlib.util.spec_from_file_location(
        "moulai_fixture_boundary_review", ROOT / "tests/conftest.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ==============================================
# EXECUTE A DISPOSABLE PYTEST PROJECT WITH THE REAL SHARED CONFIGURATION
# ==============================================


def run_boundary_project(
    *, directory: Path, source: str, arguments: tuple[str, ...] = ()
) -> subprocess.CompletedProcess[str]:
    """Copy only configuration and synthetic tests, retaining no credentials."""
    (directory / "conftest.py").write_text(
        (ROOT / "tests/conftest.py").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (directory / "pytest.ini").write_text(
        "[pytest]\nasyncio_mode=auto\n"
        "asyncio_default_fixture_loop_scope=session\n"
        "asyncio_default_test_loop_scope=session\n",
        encoding="utf-8",
    )
    (directory / "test_boundary.py").write_text(source, encoding="utf-8")
    environment = os.environ.copy()
    environment.update(
        {
            "PYTHONPATH": str(ROOT),
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "PYTEST_ADDOPTS": "",
            "TEST_DATABASE_URL": "not-a-database-url",
            "TEST_DATABASE_ENDPOINT_ID": "",
            "TEST_DATABASE_BRANCH_ID": "",
        }
    )
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-p",
            "pytest_asyncio.plugin",
            "-p",
            "no:cacheprovider",
            "-W",
            "error",
            "-q",
            "--tb=short",
            *arguments,
        ],
        cwd=directory,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


# ==============================================
# DEFAULT PYTEST DOES NOT REQUIRE OR CONNECT TO NEON
# ==============================================


def test_default_pytest_keeps_units_and_skips_live_dependencies(
    boundary_directory: Path,
) -> None:
    """Broken live settings must affect neither sync/async units nor local clients."""
    result = run_boundary_project(
        directory=boundary_directory,
        source="""
import sys
import pytest

def test_sync_unit():
    assert "app.main" not in sys.modules

async def test_async_unit():
    assert "app.core.config" not in sys.modules

class TestLocalClient:
    @pytest.fixture
    def client(self):
        return "in-memory-client"

    def test_local_client(self, client):
        assert client == "in-memory-client"

def test_live_session(db_session):
    raise AssertionError("live session must be skipped")

def test_live_api(client):
    raise AssertionError("live API must be skipped")

def test_live_revision(verify_test_schema_revision):
    raise AssertionError("revision probe must be skipped")

@pytest.mark.database
def test_explicit_database_marker():
    raise AssertionError("explicit live marker must be skipped")

def test_dynamic_engine_request(request):
    request.getfixturevalue("test_database_engine")
    raise AssertionError("dynamic engine request must be skipped")
""",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "3 passed, 5 skipped" in result.stdout


# ==============================================
# A CAUGHT NETWORK ATTEMPT STILL FAILS THE RUN
# ==============================================


def test_default_pytest_denies_network_even_if_test_catches_error(
    boundary_directory: Path,
) -> None:
    """Emit an audit event only; no socket or external connection is opened."""
    result = run_boundary_project(
        directory=boundary_directory,
        source="""
import sys
import pytest

def test_network_refused():
    with pytest.raises(RuntimeError, match="offline_test_network_access_denied"):
        sys.audit("socket.getaddrinfo", "boundary.invalid", 443, 0, 0, 0)
""",
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "1 passed" in result.stdout


# ==============================================
# REJECT A BARE LOCAL FLAG WITHOUT REPEATING ERRORS FOR EVERY TEST
# ==============================================


def test_local_flag_without_launcher_configuration_stops_before_collection(
    boundary_directory: Path,
) -> None:
    """A missing local contract must fail once, without inspecting Neon."""
    result = run_boundary_project(
        directory=boundary_directory,
        source="def test_not_collected():\n    raise AssertionError('must not run')\n",
        arguments=("--local-postgres-tests",),
    )
    assert result.returncode == 4
    assert "Local PostgreSQL configuration is incomplete or unsafe" in result.stderr
    assert "No Neon fallback" not in result.stdout


# ==============================================
# KEEP TESTS EXECUTABLE WHEN THE WINDOWS TEMP ROOT IS INACCESSIBLE
# ==============================================


def test_boundary_storage_does_not_use_system_temp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reproduce denied system-temp lookup and verify owned-directory cleanup."""
    import tempfile

    denied = MagicMock(side_effect=PermissionError("simulated system temp denial"))
    monkeypatch.setattr(tempfile, "gettempdir", denied)
    with closing(boundary_directory.__wrapped__()) as directories:
        directory = next(directories)
        assert directory.is_relative_to(ROOT / "artifacts")
        (directory / "owned-test-file.txt").write_text("synthetic", encoding="utf-8")
    denied.assert_not_called()
    assert not directory.exists()


# ==============================================
# KEEP PARALLEL TEMPORARY WORKSPACES INDEPENDENT
# ==============================================


def test_boundary_storage_does_not_delete_another_run() -> None:
    """Closing one owned fixture must preserve another active fixture's files."""
    with (
        closing(boundary_directory.__wrapped__()) as first,
        closing(boundary_directory.__wrapped__()) as second,
    ):
        first_directory = next(first)
        second_directory = next(second)
        assert first_directory != second_directory
        marker = second_directory / "owned-test-file.txt"
        marker.write_text("synthetic", encoding="utf-8")
        first.close()
        assert not first_directory.exists()
        assert marker.read_text(encoding="utf-8") == "synthetic"
    assert not second_directory.exists()


# ==============================================
# VALIDATE THE READ-ONLY REVISION GUARD USING A FAKE CONNECTION
# ==============================================


@pytest.mark.parametrize(
    "revisions",
    [[], ["dce91870b4a2"], ["e1b92b200001", "dce91870b4a2"], ["other-history"]],
)
async def test_revision_mismatch_refuses_before_cleanup(
    fixture_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    revisions: list[str],
) -> None:
    """No downgrade of the expected head, implicit upgrade or cleanup is allowed."""
    monkeypatch.setattr(
        fixture_module, "get_expected_test_schema_revision", lambda: "e1b92b200001"
    )
    from app.core import test_database

    identity = MagicMock()
    monkeypatch.setattr(test_database, "read_test_database_identity", identity)
    connection = AsyncMock()
    rows = MagicMock()
    rows.scalars.return_value.all.return_value = revisions
    connection.execute.return_value = rows
    engine = MagicMock()
    engine.connect.return_value.__aenter__ = AsyncMock(return_value=connection)

    # ==============================================
    # RUN THE REAL SYNC IDENTITY CALLBACK WITH A SIMULATED CONNECTION
    # ==============================================

    async def run_sync(callback: Any) -> None:
        """Exercise identity attestation without providing a database socket."""
        callback(object())

    connection.run_sync.side_effect = run_sync
    with pytest.raises(RuntimeError, match="No migration is authorized"):
        await fixture_module.verify_test_schema_revision.__wrapped__(engine)
    identity.assert_called_once()
    assert [str(call.args[0]) for call in connection.execute.await_args_list] == [
        "SET TRANSACTION READ ONLY",
        "SELECT version_num FROM alembic_version",
    ]
    engine.begin.assert_not_called()


# ==============================================
# ACCEPT THE EXACT HEAD WITHOUT WRITING SQL
# ==============================================


async def test_exact_revision_accepts_only_read_only_probe(
    fixture_module: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A matching revision still executes no migration, DML or cleanup."""
    monkeypatch.setattr(
        fixture_module, "get_expected_test_schema_revision", lambda: "e1b92b200001"
    )
    connection = AsyncMock()
    rows = MagicMock()
    rows.scalars.return_value.all.return_value = ["e1b92b200001"]
    connection.execute.return_value = rows
    engine = MagicMock()
    engine.connect.return_value.__aenter__ = AsyncMock(return_value=connection)
    await fixture_module.verify_test_schema_revision.__wrapped__(engine)
    assert [str(call.args[0]) for call in connection.execute.await_args_list] == [
        "SET TRANSACTION READ ONLY",
        "SELECT version_num FROM alembic_version",
    ]
    engine.begin.assert_not_called()


# ==============================================
# KEEP EXISTING TARGET REJECTIONS BEFORE ENGINE CREATION
# ==============================================


@pytest.mark.parametrize(
    "overrides",
    [
        {"TEST_DATABASE_BRANCH_ID": "br-protected"},
        {"TEST_DATABASE_ENDPOINT_ID": "ep-protected"},
        {"TEST_DATABASE_PROJECT_ID": None},
        {"TEST_DATABASE_BRANCH_ID": None},
        {"TEST_DATABASE_ENDPOINT_ID": None},
        {"TEST_DATABASE_URL": "postgresql+asyncpg://ep-fixture.neon.tech/neondb"},
        {"TEST_DATABASE_URL": "postgresql+asyncpg://ep-other.neon.tech/neondb_test"},
    ],
)
async def test_invalid_live_configuration_cannot_create_engine(
    fixture_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    overrides: dict[str, str | None],
) -> None:
    """Explicit opt-in does not bypass the existing endpoint and branch guards."""
    from app.core import config
    from app.core.test_database import UnsafeTestDatabaseError

    values = {
        "TEST_DATABASE_URL": "postgresql+asyncpg://ep-fixture.neon.tech/neondb_test",
        "TEST_DATABASE_ENDPOINT_ID": "ep-fixture",
        "PROTECTED_DATABASE_ENDPOINT_ID": "ep-protected",
        "TEST_DATABASE_BRANCH_ID": "br-fixture",
        "TEST_DATABASE_PROJECT_ID": "fixture-project",
        "PROTECTED_DATABASE_BRANCH_ID": "br-protected",
        **overrides,
    }
    monkeypatch.setattr(config, "settings", SimpleNamespace(**values))
    creator = MagicMock(side_effect=AssertionError("engine must not be created"))
    monkeypatch.setattr(fixture_module, "create_async_engine", creator)
    request = SimpleNamespace(
        config=SimpleNamespace(
            getoption=lambda option: option == "--run-database-tests"
        )
    )
    generator = fixture_module.test_database_engine.__wrapped__(request)
    with pytest.raises(UnsafeTestDatabaseError):
        await anext(generator)
    creator.assert_not_called()
