# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# ISOLATED POSTGRESQL PROFILE SAFETY TESTS
# Reject unrelated destinations and mismatched revisions before any local migration.
# ==============================================

"""Prove the independent local allowlist cannot route tests to Neon or other DBs."""

# isort: split
# ==============================================
# IMPORTS
# Exercise destination and migration admission without a database connection.
# ==============================================

import errno
import runpy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from test_support.local_postgres import (
    LocalPostgresNetworkGuard,
    LocalPostgresSettings,
    read_local_test_identity,
    validate_local_test_url,
)

FIXTURE_URL = "postgresql+asyncpg://moulai_pytest:unit-test-password-never-used@127.0.0.1:55432/moulai_pytest"

# ==============================================
# REQUIRE THE EXACT LOCAL URL TUPLE
# No local option can make a remote or unrelated URL a valid target.
# ==============================================


@pytest.mark.parametrize(
    "value",
    [
        FIXTURE_URL.replace("127.0.0.1", "ep-fixture.neon.tech"),
        FIXTURE_URL.replace("127.0.0.1", "localhost"),
        FIXTURE_URL.replace("127.0.0.1", "0.0.0.0"),
        FIXTURE_URL.replace(":55432/", ":5432/"),
        FIXTURE_URL.replace("/moulai_pytest", "/neondb_test"),
        FIXTURE_URL.replace("/moulai_pytest", "/neondb"),
        FIXTURE_URL.replace("//moulai_pytest:", "//postgres:"),
        FIXTURE_URL + "?host=other",
        FIXTURE_URL + "?sslmode=disable",
        FIXTURE_URL.replace("+asyncpg", ""),
        "not-a-url",
        "",
    ],
)
def test_local_url_rejects_non_allowlisted_targets(value: str) -> None:
    """No local option can make a remote or unrelated URL a valid target."""
    with pytest.raises(ValueError, match="not_allowlisted"):
        validate_local_test_url(value=value)


# ==============================================
# KEEP LOCAL SECRETS OUT OF SETTINGS REPRESENTATIONS
# The independent settings do not read the project's Neon URLs.
# ==============================================


def test_local_settings_accept_exact_target_without_exposing_password() -> None:
    """The independent settings do not read the project's Neon URLs."""
    configuration = LocalPostgresSettings(URL=FIXTURE_URL, INSTANCE_ID="a" * 32)
    assert (
        validate_local_test_url(value=configuration.URL.get_secret_value())
        == FIXTURE_URL
    )
    assert "unit-test-password" not in repr(configuration)


# ==============================================
# LOAD THE EXACT STRING VALUES PROVIDED BY THE REAL LAUNCHER
# Environment loading must preserve the approved integer port contract.
# ==============================================


@pytest.mark.parametrize("port", ["5432", "55432"])
def test_local_settings_round_trip_from_environment(
    monkeypatch: pytest.MonkeyPatch, port: str
) -> None:
    """Environment loading must preserve the approved integer port contract."""
    monkeypatch.setenv("LOCAL_POSTGRES_TEST_URL", FIXTURE_URL)
    monkeypatch.setenv("LOCAL_POSTGRES_TEST_INSTANCE_ID", "a" * 32)
    monkeypatch.setenv("LOCAL_POSTGRES_TEST_SERVER_PORT", port)
    configuration = LocalPostgresSettings()
    assert configuration.SERVER_PORT == int(port)


# ==============================================
# CHECK LIVE SERVER IDENTITY THROUGH SELECT ONLY
# A matching host alone cannot authorize database reset or migrations.
# ==============================================


@pytest.mark.parametrize(
    "change",
    [
        {"database": "neondb_test"},
        {"role": "postgres"},
        {"owner": "other"},
        {"port": 5432},
        {"rolsuper": True},
        {"rolcreatedb": True},
        {"rolcreaterole": True},
        {"marker": "other-instance"},
    ],
)
def test_local_identity_refuses_unrelated_or_privileged_server(
    change: dict[str, object],
) -> None:
    """A matching host alone cannot authorize database reset or migrations."""
    from sqlalchemy.engine import make_url

    connection = MagicMock()
    connection.engine.url = make_url(FIXTURE_URL)
    connection.execute.return_value.mappings.return_value.one.return_value = {
        "database": "moulai_pytest",
        "role": "moulai_pytest",
        "owner": "moulai_pytest",
        "port": 55432,
        "rolsuper": False,
        "rolcreatedb": False,
        "rolcreaterole": False,
        "marker": "moulai-local-pytest:" + "a" * 32,
        **change,
    }
    with pytest.raises(RuntimeError, match="identity_mismatch"):
        read_local_test_identity(
            connection,
            configuration=LocalPostgresSettings(URL=FIXTURE_URL, INSTANCE_ID="a" * 32),
        )
    assert str(connection.execute.call_args.args[0]).startswith("SELECT ")


# ==============================================
# KEEP NETWORK ACCESS LIMITED TO THE DEDICATED LOOPBACK PORT
# The existing offline policy still blocks all unapproved transmissions.
# ==============================================


@pytest.mark.parametrize("address", [("127.0.0.1", 5432), ("203.0.113.1", 55432)])
def test_local_network_policy_denies_other_destinations(
    address: tuple[str, int],
) -> None:
    """The existing offline policy still blocks all unapproved transmissions."""
    guard = LocalPostgresNetworkGuard()
    with pytest.raises(RuntimeError, match="network_access_denied"):
        guard("socket.connect", (object(), address))
    assert guard.denied["socket.connect"] == 1


# ==============================================
# ADMIT ONLY THE LOOPBACK TEST CONNECTION
# No DNS wildcard or production host exception is introduced.
# ==============================================


def test_local_network_policy_accepts_exact_numeric_destination() -> None:
    """No DNS wildcard or production host exception is introduced."""
    guard = LocalPostgresNetworkGuard()
    guard("socket.connect", (object(), ("127.0.0.1", 55432)))
    guard("socket.getaddrinfo", ("127.0.0.1", 55432, 0, 0, 0))
    assert not guard.denied


# ==============================================
# EXPLICIT COMPATIBILITY / E1 PROFILES WITH NO ARBITRARY TARGET
# Local profile selection never consults the Neon target variables.
# ==============================================


@pytest.mark.parametrize("profile", ["legacy", "k10", "dining"])
def test_local_profile_is_explicit_and_independent(
    monkeypatch: pytest.MonkeyPatch, profile: str
) -> None:
    """Local profile selection never consults the Neon target variables."""
    monkeypatch.setenv("LOCAL_POSTGRES_TEST_PROFILE", profile)
    configuration = LocalPostgresSettings(URL=FIXTURE_URL, INSTANCE_ID="a" * 32)
    assert configuration.PROFILE == profile


# ==============================================
# NO CUSTOM ALEMBIC HEAD OR REMOTE PROFILE
# A profile cannot be repurposed as an arbitrary migration revision.
# ==============================================


@pytest.mark.parametrize(
    "profile", ["production", "development", "head", "e1a92b200001", ""]
)
def test_local_profile_rejects_other_histories(profile: str) -> None:
    """A profile cannot be repurposed as an arbitrary migration revision."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        LocalPostgresSettings(URL=FIXTURE_URL, INSTANCE_ID="a" * 32, PROFILE=profile)


# ==============================================
# PROFILE AND ALEMBIC REVISION MUST MATCH ON THE PINNED CONNECTION
# Admit the current D1d target and reject older or ambiguous revisions without SQL.
# ==============================================


@pytest.mark.parametrize(
    "profile,revision,accepted",
    [
        ("legacy", "dce91870b4a2", True),
        ("subscription", "s1b20261028", True),
        ("main", "s1a20261028", True),
        ("dining", "d1d20261105", True),
        ("dining", "d1c20261104", False),
        ("dining", "d1b20261103", False),
        ("dining", "d1a20261102", False),
        ("dining", "head", False),
        ("dining", "s1a20261028", False),
        ("main", "d1a20261102", False),
        ("subscription", "s1a20261028", False),
        ("main", "s1b20261028", False),
        ("k10", "e1b92b200001", True),
        ("legacy", "e1b92b200001", False),
        ("k10", "dce91870b4a2", False),
        ("k10", "e1a92b200001", False),
        ("k10", "head", False),
    ],
)
def test_local_alembic_enforces_profile_revision(
    monkeypatch: pytest.MonkeyPatch, profile: str, revision: str, accepted: bool
) -> None:
    """Exercise the real local env with mocked context; execute no SQL or DDL."""
    from sqlalchemy.engine import Connection

    import alembic
    from test_support import local_postgres

    connection = MagicMock(spec=Connection)
    connection.in_transaction.return_value = True
    configuration = LocalPostgresSettings(
        URL=FIXTURE_URL, INSTANCE_ID="a" * 32, PROFILE=profile
    )
    migration_context = MagicMock()
    migration_context.config = SimpleNamespace(
        attributes={"connection": connection, "local_configuration": configuration}
    )
    migration_context.is_offline_mode.return_value = False
    migration_context.get_revision_argument.return_value = revision
    identity = MagicMock()
    monkeypatch.setattr(alembic, "context", migration_context)
    monkeypatch.setattr(local_postgres, "read_local_test_identity", identity)
    path = Path(__file__).resolve().parents[1] / "alembic_local_test/env.py"
    if accepted:
        runpy.run_path(str(path))
        identity.assert_called_once_with(connection, configuration=configuration)
        migration_context.run_migrations.assert_called_once()
    else:
        with pytest.raises(RuntimeError, match="profile_revision_mismatch"):
            runpy.run_path(str(path))
        identity.assert_not_called()
        migration_context.run_migrations.assert_not_called()


# ==============================================
# CURRENT APPLICATION TESTS REQUIRE THE MAIN SCHEMA
# Prevent the broad database marker from running against the historical baseline.
# ==============================================


@pytest.mark.parametrize("suite", ["profile", "health-only", "catalog"])
def test_legacy_suite_is_rejected_before_server_start(
    monkeypatch: pytest.MonkeyPatch, suite: str
) -> None:
    """CLI rejection must occur before backend discovery or instance creation."""
    import sys

    from scripts import run_local_postgres_tests as launcher

    backend = MagicMock(side_effect=AssertionError("No server may be prepared"))
    monkeypatch.setattr(launcher, "choose_backend", backend)
    monkeypatch.setattr(
        sys, "argv", ["launcher", "--profile", "legacy", "--suite", suite]
    )
    with pytest.raises(SystemExit) as failure:
        launcher.main()
    assert failure.value.code == 2
    backend.assert_not_called()


# ==============================================
# SCHEMA-BOUND SUITE SELECTION
# Keep dedicated proofs and the sibling S1b and E1 histories separate.
# ==============================================


@pytest.mark.parametrize(
    "profile,suite,expected",
    [
        ("main", "profile", ["-m", "database"]),
        ("dining", "profile", ["tests/dining"]),
        ("k10", "profile", ["tests/test_k10_postgres.py", "--maxfail=1"]),
        (
            "main",
            "health-only",
            ["tests/test_health_only_postgres.py", "--maxfail=1"],
        ),
        (
            "main",
            "catalog",
            ["tests/test_catalog_postgres_transactions.py", "--maxfail=1"],
        ),
    ],
)
def test_schema_bound_test_selection(
    profile: str, suite: str, expected: list[str]
) -> None:
    """Select the exact applicable proofs without marking failures as skipped."""
    from scripts.run_local_postgres_tests import select_tests

    assert select_tests(profile=profile, suite=suite, paths=None) == expected


# ==============================================
# DEDICATED PROOFS CANNOT USE A SIBLING HISTORY
# Reject incompatible selection instead of provisioning a known invalid schema.
# ==============================================


@pytest.mark.parametrize("profile", ["subscription", "k10", "dining"])
@pytest.mark.parametrize("suite", ["health-only", "catalog"])
def test_dedicated_suite_requires_main(profile: str, suite: str) -> None:
    """Both dedicated applications now consume S1a-compatible ORM contracts."""
    from scripts.run_local_postgres_tests import select_tests

    with pytest.raises(ValueError, match="requires_main"):
        select_tests(profile=profile, suite=suite, paths=None)


# ==============================================
# HISTORICAL E1 INVENTORY MUST NOT FOLLOW LIVE ORM MODELS
# Read the frozen baseline DDL and retain the strict exact-table comparison.
# ==============================================


def test_e1_inventory_excludes_later_subscription_tables() -> None:
    """New ORM tables must not become expected tables in the older E1 graph."""
    from scripts.run_local_postgres_tests import legacy_schema_tables

    tables = legacy_schema_tables()
    assert len(tables) == 47
    assert {"alembic_version", "manual_payment_audit", "owners"} <= tables
    assert not tables & {
        "subscription_pricing_config",
        "subscription_pricing_snapshots",
        "subscription_reminders",
        "cash_collections",
        "cash_collection_attempts",
    }


# ==============================================
# DEFAULT CLI PROFILE TRACKS THE MAIN HISTORY
# Exercise argument parsing without reaching filesystem or server provisioning.
# ==============================================


def test_launcher_defaults_to_main(monkeypatch: pytest.MonkeyPatch) -> None:
    """The user's minimal command must no longer select the legacy schema."""
    import sys

    from scripts import run_local_postgres_tests as launcher

    selection = MagicMock(side_effect=ValueError("stop_before_provisioning"))
    monkeypatch.setattr(launcher, "select_tests", selection)
    monkeypatch.setattr(sys, "argv", ["launcher", "--backend", "native"])
    with pytest.raises(SystemExit):
        launcher.main()
    selection.assert_called_once_with(profile="main", suite="profile", paths=None)


# ==============================================
# REFUSE CHANGED HISTORICAL INVENTORY SOURCES
# An extra baseline table cannot silently expand the E1 verifier's allowlist.
# ==============================================


def test_e1_inventory_rejects_changed_source(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Do not execute migration source while reading its literal table inventory."""
    from scripts import run_local_postgres_tests as launcher

    relative = "alembic_test/versions/ae6a266365fb_test_schema_baseline.py"
    target = tmp_path / relative
    target.parent.mkdir(parents=True)
    target.write_text(
        (launcher.ROOT / relative).read_text(encoding="utf-8")
        + "\nraise AssertionError('must never execute')\nop.create_table('unexpected')\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(launcher, "ROOT", tmp_path)
    with pytest.raises(RuntimeError, match="inventory_source_mismatch"):
        launcher.legacy_schema_tables()


# ==============================================
# OCCUPIED PORTS NEVER AUTHORIZE PROCESS TERMINATION
# Exercise the fixed native fallback and explicit-port refusal with mocked sockets, leaving all real listeners untouched.
# ==============================================


@pytest.mark.parametrize(
    "backend,requested,busy,expected,attempted",
    [
        ("native", None, (), 55432, (55432,)),
        ("native", None, (55432,), 55435, (55432, 55435)),
        ("native", 55435, (), 55435, (55435,)),
        ("native", 55432, (55432,), None, (55432,)),
        ("native", None, (55432, 55435), None, (55432, 55435)),
        ("docker", None, (55432,), None, (55432,)),
        ("docker", 55435, (), None, ()),
        ("native", 55433, (), None, ()),
    ],
)
def test_local_port_selection_preserves_existing_services(
    monkeypatch: pytest.MonkeyPatch,
    backend: str,
    requested: int | None,
    busy: tuple[int, ...],
    expected: int | None,
    attempted: tuple[int, ...],
) -> None:
    """Only the two approved test ports may be tried; explicit choices and Docker mappings never move silently."""
    from scripts import run_local_postgres_tests as launcher

    calls: list[int] = []

    # ==============================================
    # SYNTHETIC SOCKET ADMISSION
    # Simulate Windows address conflicts without binding or stopping an actual application.
    # ==============================================

    def bind(address: tuple[str, int]) -> None:
        """Record only allowlisted loopback probes and reproduce the reported address-in-use error."""
        assert address[0] == "127.0.0.1"
        calls.append(address[1])
        if address[1] in busy:
            raise OSError(errno.EADDRINUSE, "synthetic occupied port")

    socket = MagicMock()
    socket.__enter__.return_value.bind.side_effect = bind
    monkeypatch.setattr(launcher.socket, "socket", MagicMock(return_value=socket))
    if expected is None:
        with pytest.raises(ValueError):
            launcher.select_local_port(backend=backend, requested=requested)
    else:
        assert (
            launcher.select_local_port(backend=backend, requested=requested) == expected
        )
    assert tuple(calls) == attempted


# ==============================================
# BUSY-PORT CLI REFUSAL PRECEDES PROVISIONING
# A fully occupied allowlist must produce a useful command error, not a raw traceback or a partially initialized test database.
# ==============================================


def test_busy_ports_stop_before_instance_creation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify the actual argument dispatcher has no filesystem or server side effects on port refusal."""
    import sys

    from scripts import run_local_postgres_tests as launcher

    monkeypatch.setattr(sys, "argv", ["launcher", "--backend", "native"])
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(launcher, "ROOT", tmp_path)
    monkeypatch.setattr(launcher, "choose_backend", MagicMock(return_value="native"))
    monkeypatch.setattr(
        launcher,
        "select_local_port",
        MagicMock(side_effect=ValueError("Ports 55432, 55435 indisponibles")),
    )
    startup = MagicMock(side_effect=AssertionError("No server may start"))
    monkeypatch.setattr(launcher, "run_process", startup)
    with pytest.raises(SystemExit) as failure:
        launcher.main()
    assert failure.value.code == 2
    message = capsys.readouterr().err
    assert "55432, 55435" in message and "Traceback" not in message
    assert list(tmp_path.iterdir()) == []
    startup.assert_not_called()
