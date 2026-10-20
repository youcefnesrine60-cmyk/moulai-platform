# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Prove the independent local allowlist cannot route tests to Neon or other DBs."""

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
# ==============================================


def test_local_network_policy_accepts_exact_numeric_destination() -> None:
    """No DNS wildcard or production host exception is introduced."""
    guard = LocalPostgresNetworkGuard()
    guard("socket.connect", (object(), ("127.0.0.1", 55432)))
    guard("socket.getaddrinfo", ("127.0.0.1", 55432, 0, 0, 0))
    assert not guard.denied


# ==============================================
# EXPLICIT COMPATIBILITY / E1 PROFILES WITH NO ARBITRARY TARGET
# ==============================================


@pytest.mark.parametrize("profile", ["legacy", "k10"])
def test_local_profile_is_explicit_and_independent(
    monkeypatch: pytest.MonkeyPatch, profile: str
) -> None:
    """Local profile selection never consults the Neon target variables."""
    monkeypatch.setenv("LOCAL_POSTGRES_TEST_PROFILE", profile)
    configuration = LocalPostgresSettings(URL=FIXTURE_URL, INSTANCE_ID="a" * 32)
    assert configuration.PROFILE == profile


# ==============================================
# NO CUSTOM ALEMBIC HEAD OR REMOTE PROFILE
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
# ==============================================


@pytest.mark.parametrize(
    "profile,revision,accepted",
    [
        ("legacy", "dce91870b4a2", True),
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
