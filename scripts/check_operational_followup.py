# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# TARGETED OFFLINE OPERATIONAL REGRESSIONS
# Run a closed list of unit/ASGI tests with networking denied and integration fixtures disabled.
# ==============================================

"""No application startup, database, provider, microphone, migration or general campaign."""

from __future__ import annotations

# isort: split
# ==============================================
# FIXED LOCAL TEST SCOPE
# Reuse the established network guard and workspace-owned temporary-directory checks.
# ==============================================

import json
import os
import sys
from contextlib import (
    redirect_stderr,
    redirect_stdout,
)
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_offline_api_tests import (
    OfflineNetworkGuard,
    TestResults,
)
from test_support.offline_storage import reserve_pytest_directory

TESTS = [
    "tests/integration_local/test_operational_followup.py",
    "tests/integration_local/test_operational_boundary.py",
    "tests/integration_local/test_enrollment_http_offline.py",
    "tests/integration_local/test_enrollment_offline.py",
]


# ==============================================
# NETWORK-ISOLATED PYTEST INVOCATION
# Treat warnings as errors, record actual outcomes and never load destructive shared fixtures.
# ==============================================


def main() -> int:
    """Execute only the declared tests and return their actual failure code."""
    os.chdir(ROOT)
    os.environ.update(DEBUG="false", REDIS_URL="", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    guard = OfflineNetworkGuard()
    sys.addaudithook(guard)
    import pytest

    output = ROOT / "artifacts/operational-followup-20261109"
    output.mkdir(parents=True, exist_ok=True)
    results = TestResults()
    with (output / "offline-tests.log").open(
        "w", encoding="utf-8"
    ) as log, redirect_stdout(log), redirect_stderr(log):
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
                    "--basetemp=" + str(reserve_pytest_directory()),
                    "-W",
                    "error",
                    "-q",
                    *TESTS,
                ],
                plugins=[results],
            )
        )
    summary = {
        "status": "PASS" if code == 0 else "FAIL",
        "exit_code": code,
        "tests": TESTS,
        "outcomes": dict(results.outcomes),
        "network_denied": dict(guard.denied),
        "network_guard_scope": "Python socket audit, not OS-level isolation",
        "shared_conftest_loaded": False,
        "warnings_as_errors": True,
    }
    (output / "offline-summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
