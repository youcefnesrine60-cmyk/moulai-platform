# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Compile and review E1 without env.py, URLs, engines or database execution."""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import sys
from io import StringIO
from pathlib import Path
from types import ModuleType
from typing import Literal

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REVISION_PATHS: tuple[str, ...] = (
    "alembic/versions/2026_10_18_15_00_00_tenant_foundation_e1.py",
    "alembic_test/versions/e1b92b200001_tenant_foundation_e1.py",
)


# ==============================================
# LOAD REVISION WITHOUT ALEMBIC ENVIRONMENT
# ==============================================


def load_revision(*, path: Path) -> ModuleType:
    """Import one reviewed revision without loading env.py or a connection URL."""
    specification = importlib.util.spec_from_file_location("tenant_e1_revision", path)
    if specification is None or specification.loader is None:
        raise RuntimeError("E1 revision source unavailable")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


# ==============================================
# COMPILE REVISION INTO A STRING ONLY
# ==============================================


def render_revision(*, path: Path, direction: Literal["upgrade", "downgrade"]) -> str:
    """Render a PostgreSQL migration body; no engine, bind or SQL execution exists."""
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    module = load_revision(path=path)
    output = StringIO()
    context = MigrationContext.configure(
        dialect_name="postgresql",
        dialect_opts={"paramstyle": "named"},
        opts={"as_sql": True, "literal_binds": True, "output_buffer": output},
    )
    if context.connection is not None:
        # Alembic offline contexts normally expose a MockConnection sink. Check
        # as_sql instead of accepting any real Connection or connectable.
        from sqlalchemy.engine import Connection

        if isinstance(context.connection, Connection):
            raise RuntimeError("E1 static review cannot use a real connection")
    with context.begin_transaction(), Operations.context(context):
        getattr(module, direction)()
    return output.getvalue().expandtabs(4)


# ==============================================
# READ STATIC REVISION GRAPH
# ==============================================


def revision_graph(*, directory: Path) -> dict[str, str | None]:
    """Read literal revision labels using AST without importing old migrations."""
    graph: dict[str, str | None] = {}
    for path in sorted(directory.glob("*.py")):
        labels: dict[str, str | None] = {}
        for node in ast.parse(path.read_text(encoding="utf-8-sig")).body:
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and target.id in {
                    "revision",
                    "down_revision",
                }:
                    labels[target.id] = ast.literal_eval(node.value)
        if not labels:
            continue
        revision = labels.get("revision")
        if not isinstance(revision, str) or revision in graph:
            raise ValueError("missing or duplicate Alembic revision")
        graph[revision] = labels.get("down_revision")
    for revision in graph:
        seen: set[str] = set()
        cursor: str | None = revision
        while cursor is not None:
            if cursor in seen or cursor not in graph:
                raise ValueError("cyclic or incomplete Alembic history")
            seen.add(cursor)
            cursor = graph[cursor]
    return graph


# ==============================================
# MAIN
# ==============================================


def main() -> int:
    """Guard networking, run static contracts, then save review-only SQL artifacts."""
    os.chdir(PROJECT_ROOT)
    sys.path.insert(0, str(PROJECT_ROOT))
    os.environ.update(
        {
            "APP_ENV": "development",
            "DATABASE_TARGET": "development",
            "DEBUG": "false",
            "DB_ECHO": "false",
            "REDIS_URL": "",
            "OIDC_DIAGNOSTICS_ENABLED": "false",
            "OIDC_ALLOW_LOCAL_HTTP": "false",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        }
    )
    from scripts.run_offline_api_tests import (
        OfflineNetworkGuard,
        TestResults,
    )

    guard = OfflineNetworkGuard()
    sys.addaudithook(guard)
    import pytest

    output = PROJECT_ROOT / "artifacts" / "keycloak-k9-b2"
    output.mkdir(parents=True, exist_ok=True)
    results = TestResults()
    code = int(
        pytest.main(
            [
                "--noconftest",
                "-o",
                "addopts=",
                "-p",
                "pytest_asyncio.plugin",
                "-p",
                "no:cacheprovider",
                "-W",
                "error",
                "--tb=short",
                "-q",
                "tests/test_tenant_e1_static.py",
            ],
            plugins=[results],
        )
    )
    graphs = {}
    for directory in ("alembic", "alembic_test"):
        graph = revision_graph(directory=PROJECT_ROOT / directory / "versions")
        graphs[directory] = {
            "parents": graph,
            "heads": sorted(set(graph) - set(graph.values())),
        }
    for relative_path in REVISION_PATHS:
        path = PROJECT_ROOT / relative_path
        revision = str(load_revision(path=path).revision)
        for direction in ("upgrade", "downgrade"):
            sql = render_revision(path=path, direction=direction)
            (output / f"{revision}-{direction}.sql").write_text(sql, encoding="utf-8")
    conftest_loaded = any(
        str(getattr(module, "__file__", ""))
        .replace("\\", "/")
        .endswith("tests/conftest.py")
        for module in tuple(sys.modules.values())
    )
    report = {
        "pytest_exit_code": code,
        "collected": results.collected,
        "outcomes": dict(results.outcomes),
        "failures": results.failures,
        "warnings": dict(results.warnings),
        "network_denied_categories": dict(guard.denied),
        "conftest_loaded": conftest_loaded,
        "revision_graphs": graphs,
        "scope": "StringIO PostgreSQL compilation and metadata inspection only; no SQL execution",
        "limitations": "No PostgreSQL parser/PLpgSQL execution, locking rehearsal or live schema attestation",
    }
    report["passed"] = code == 0 and not guard.denied and not conftest_loaded
    (output / "validation.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
