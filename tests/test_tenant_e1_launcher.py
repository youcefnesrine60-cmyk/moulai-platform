# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Offline launcher boundaries; no engine, database or Alembic environment IO."""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock

import pytest
from sqlalchemy.engine import Connection

from scripts.rehearse_tenant_e1 import (
    PARENT,
    ROOT,
    TARGET,
    BoundRehearsal,
    Direction,
    run_alembic,
    verify_frozen_sources,
)

# ==============================================
# FROZEN SOURCE HASH REGRESSION
# ==============================================


def test_approved_frozen_e1_sources() -> None:
    """Match every migration-only contract against the approved B2 hashes."""
    verify_frozen_sources()


# ==============================================
# EXACT REVISION AND SHARED CONNECTION
# ==============================================


@pytest.mark.parametrize(
    "direction,target", [("upgrade", TARGET), ("downgrade", PARENT)]
)
def test_programmatic_alembic_pins_connection(
    monkeypatch: pytest.MonkeyPatch, direction: Direction, target: str
) -> None:
    """Never resolve a default URL or replace the actual caller-owned connection."""
    from alembic import command

    called = MagicMock()
    monkeypatch.setattr(command, direction, called)
    connection = MagicMock(spec=Connection)
    runtime = object()
    bound = cast(BoundRehearsal, SimpleNamespace(settings=runtime))
    run_alembic(connection, bound=bound, direction=direction)
    config, actual_target = called.call_args.args
    assert actual_target == target
    assert config.get_main_option("script_location") == str(ROOT / "alembic_test")
    assert config.attributes["connection"] is connection
    assert config.attributes["moulai_rehearsal_settings"] is runtime
    assert callable(config.attributes["moulai_rehearsal_admission"])
    assert config.config_file_name is None


# ==============================================
# SUPPLIED CONNECTION CANNOT SKIP THE EXISTING IDENTITY CHECK
# ==============================================


def test_test_history_environment_preserves_admission() -> None:
    """Check the pinned branch still calls both dedicated and central guards."""
    source = (ROOT / "alembic_test/env.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    functions = {
        node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)
    }
    pinned = ast.get_source_segment(source, functions["run_migrations_online"])
    shared = ast.get_source_segment(source, functions["do_run_migrations"])
    assert pinned is not None and shared is not None
    assert "admission(supplied_connection)" in pinned
    assert "do_run_migrations(supplied_connection)" in pinned
    assert "read_test_database_identity(" in shared
    assert pinned.index("admission(supplied_connection)") < pinned.index(
        "do_run_migrations(supplied_connection)"
    )


# ==============================================
# ONLY THE AUTHORIZED MIGRATION HISTORY IS REFERENCED
# ==============================================


def test_launcher_has_no_main_history_or_stamp_path() -> None:
    """Reject accidental broad migration entry points in the opt-in launcher."""
    source = (ROOT / "scripts/rehearse_tenant_e1.py").read_text(encoding="utf-8")
    assert "command.stamp(" not in source
    assert '"head"' not in source
    assert 'ROOT / "alembic"' not in source
    assert 'choices=("upgrade", "downgrade")' in source
    assert Path(
        ROOT / "alembic_test/versions/e1b92b200001_tenant_foundation_e1.py"
    ).is_file()
