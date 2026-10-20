# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Run only offline rehearsal admission tests and export secret-free evidence."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from contextlib import (
    redirect_stderr,
    redirect_stdout,
)
from datetime import (
    datetime,
    timezone,
)
from io import StringIO
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    "app/core/rehearsal_admission.py",
    "tests/test_rehearsal_admission.py",
    "scripts/review_rehearsal_admission.py",
    "scripts/rehearse_tenant_e1.py",
    "tests/test_tenant_e1_launcher.py",
    "scripts/validate_tenant_e1_postgres.py",
    "scripts/verify_tenant_e1_preservation.py",
    "tests/test_tenant_e1_postgres_harness.py",
    "alembic_test/env.py",
)


# ==============================================
# OFFLINE REVIEW ENTRY POINT
# ==============================================


def main() -> int:
    """Block sockets before imports and disable all shared database fixtures."""
    os.chdir(PROJECT_ROOT)
    sys.path.insert(0, str(PROJECT_ROOT))
    os.environ.update(
        {
            "DEBUG": "false",
            "DB_ECHO": "false",
            "APP_ENV": "development",
            "DATABASE_TARGET": "development",
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

    results = TestResults()
    # Do not persist arbitrary traceback/Settings representations to test logs.
    with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
        from app.core.rehearsal_admission import RehearsalManifest

        code = int(
            pytest.main(
                [
                    "--noconftest",
                    "-o",
                    "addopts=",
                    "-p",
                    "no:cacheprovider",
                    "-p",
                    "pytest_asyncio.plugin",
                    "-W",
                    "error",
                    "--tb=short",
                    "-q",
                    "tests/test_rehearsal_admission.py",
                    "tests/test_test_database_safety.py",
                    "tests/test_tenant_e1_launcher.py",
                    "tests/test_tenant_e1_static.py",
                    "tests/test_tenant_e1_postgres_harness.py",
                ],
                plugins=[results],
            )
        )
    conftest_loaded = any(
        str(getattr(module, "__file__", ""))
        .replace("\\", "/")
        .endswith("tests/conftest.py")
        for module in tuple(sys.modules.values())
    )
    report = {
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "exit_code": code,
        "outcomes": dict(results.outcomes),
        "subtests": dict(results.subtests),
        "warnings": dict(results.warnings),
        "failures": results.failures,
        "network_attempts": dict(guard.denied),
        "shared_conftest_loaded": conftest_loaded,
        "source_sha256": {
            name: hashlib.sha256((PROJECT_ROOT / name).read_bytes()).hexdigest()
            for name in SOURCES
        },
        "database_execution": False,
        "resource_creation": False,
    }
    output = PROJECT_ROOT / "artifacts/keycloak-k9-g1-admission"
    output.mkdir(parents=True, exist_ok=True)
    (output / "validation.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    (output / "resource-manifest.schema.json").write_text(
        json.dumps(RehearsalManifest.model_json_schema(), indent=2) + "\n",
        encoding="utf-8",
    )
    sources = "# Complete rehearsal admission and G2 Python sources\n\n" + "\n\n".join(
        f"## {name}\n\n```python\n{(PROJECT_ROOT/name).read_text(encoding='utf-8').rstrip()}\n```"
        for name in SOURCES
    )
    (output / "complete-python-sources.md").write_text(sources + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 1 if code or guard.denied or conftest_loaded or results.warnings else 0


if __name__ == "__main__":
    raise SystemExit(main())
