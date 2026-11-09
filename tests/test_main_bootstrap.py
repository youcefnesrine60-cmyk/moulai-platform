# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MAIN BOOTSTRAP OFFLINE ADMISSION TESTS
# Prove contract integrity, historical reproducibility and refusal before schema mutation.
# ==============================================

"""Check main bootstrap boundaries without a database connection or network call."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND SYNTHETIC LOCAL IDENTITY
# Use an inert password and mocked SQL connection for negative admission tests.
# ==============================================

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy.engine import Connection

from migration_support import main_bootstrap
from scripts.freeze_main_bootstrap import build
from test_support.local_postgres import LocalPostgresSettings

FIXTURE_URL = "postgresql+asyncpg://moulai_pytest:unit-test-password-never-used@127.0.0.1:55432/moulai_pytest"


# ==============================================
# EXACT HISTORICAL CONTRACT REPRODUCTION
# Detect source, ownership-selection or generated DDL changes independently of ORM models.
# ==============================================


def test_historical_bootstrap_is_reproducible() -> None:
    """The frozen contract must match local versioned evidence and exclude migrated tables."""
    contract = json.loads(main_bootstrap.CONTRACT_PATH.read_bytes())
    assert build() == contract
    statements = main_bootstrap.load_bootstrap_statements()
    assert len(contract["tables"]) == 33
    assert "agents" not in contract["tables"]
    assert "admin_logs" not in contract["tables"]
    assert "manual_payment_receipts" not in contract["tables"]
    assert not any("alembic_version" in statement for statement in statements)


# ==============================================
# TAMPERED CONTRACT REJECTION
# Refuse modified bytes before returning any executable DDL to the caller.
# ==============================================


def test_bootstrap_rejects_changed_contract(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Even harmless-looking changes invalidate the pinned contract digest."""
    changed = tmp_path / "changed.json"
    changed.write_bytes(main_bootstrap.CONTRACT_PATH.read_bytes() + b" ")
    monkeypatch.setattr(main_bootstrap, "CONTRACT_PATH", changed)
    with pytest.raises(RuntimeError, match="hash_mismatch"):
        main_bootstrap.load_bootstrap_statements()


# ==============================================
# NONEMPTY TARGET REJECTION
# Prove no bootstrap statement runs when any existing relation is detected.
# ==============================================


def test_bootstrap_refuses_existing_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    """A restored diagnostic schema cannot be adopted as a fresh main installation."""
    connection = MagicMock(spec=Connection)
    connection.in_transaction.return_value = True
    connection.execute.return_value.scalar_one.return_value = 1
    identity = MagicMock()
    monkeypatch.setattr(main_bootstrap, "read_local_test_identity", identity)
    configuration = LocalPostgresSettings(
        URL=FIXTURE_URL, INSTANCE_ID="a" * 32, PROFILE="main"
    )
    with pytest.raises(RuntimeError, match="empty_database"):
        main_bootstrap.apply_main_bootstrap(connection, configuration=configuration)
    identity.assert_called_once_with(connection, configuration=configuration)
    connection.exec_driver_sql.assert_not_called()


# ==============================================
# PROFILE AND TRANSACTION REFUSALS
# Protect S1b and reject accidental autocommit before even checking the live database.
# ==============================================


@pytest.mark.parametrize(
    "profile,transaction", [("subscription", True), ("main", False)]
)
def test_bootstrap_requires_main_transaction(profile: str, transaction: bool) -> None:
    """Neither compatibility installations nor unowned transactions authorize bootstrap."""
    connection = MagicMock(spec=Connection)
    connection.in_transaction.return_value = transaction
    configuration = LocalPostgresSettings(
        URL=FIXTURE_URL, INSTANCE_ID="a" * 32, PROFILE=profile
    )
    with pytest.raises(RuntimeError, match="explicit_transaction_and_profile"):
        main_bootstrap.apply_main_bootstrap(connection, configuration=configuration)
    connection.execute.assert_not_called()
    connection.exec_driver_sql.assert_not_called()


# ==============================================
# NO AMBIGUOUS APPLICATION URL FALLBACK
# Refuse missing dedicated target settings before calling the asynchronous runner.
# ==============================================


def test_main_launcher_never_uses_database_url(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """DATABASE_URL cannot substitute for the explicit migration target variable."""
    from scripts import run_main_migrations

    monkeypatch.delenv("MOULAI_MAIN_LOCAL_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", FIXTURE_URL)
    monkeypatch.setattr(
        "sys.argv",
        ["run_main_migrations.py", "--instance-id", "a" * 32, "--confirm-empty-local"],
    )
    runner = MagicMock()
    monkeypatch.setattr(run_main_migrations, "reconstruct", runner)
    assert run_main_migrations.main() == 1
    runner.assert_not_called()
    assert "unit-test-password" not in capsys.readouterr().out
