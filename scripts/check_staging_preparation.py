# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# CLOSED STAGING AND LOCAL ADAPTER REGRESSIONS
# Deny networking and exclude shared destructive fixtures while testing the changed
# browser composition and original local boundaries together.
# ==============================================

"""No database, remote provider, worker, deployment or general backend campaign."""

from __future__ import annotations

# isort: split
# ==============================================
# ESTABLISHED OFFLINE TEST HARNESS
# Keep existing proof files intact and write this pass into its own directory.
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

from scripts.check_operational_followup import TESTS
from scripts.run_offline_api_tests import (
    OfflineNetworkGuard,
    TestResults,
)
from test_support.offline_storage import reserve_pytest_directory

# ==============================================
# SINGLE OFFLINE CAMPAIGN
# Warnings remain errors and a failed assertion is never converted into a success.
# ==============================================


def main() -> int:
    """Run only new staging admission and the four affected local adapter files."""
    os.chdir(ROOT)
    os.environ.update(DEBUG="false", REDIS_URL="", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    guard = OfflineNetworkGuard()
    sys.addaudithook(guard)
    import pytest

    output = ROOT / "artifacts/staging-preparation-20261109"
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
                    "tests/staging/test_staging_boundary.py",
                ],
                plugins=[results],
            )
        )
    summary = {
        "status": "PASS" if code == 0 else "FAIL",
        "exit_code": code,
        "outcomes": dict(results.outcomes),
        "network_denied": dict(guard.denied),
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
