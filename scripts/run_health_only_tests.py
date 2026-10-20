# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Run only standalone Render observation regressions with network IO denied."""

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
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from test_support.health_only_safety import (
    OfflineNetworkGuard,
    TestResults,
    configure_offline_application,
)

TEST_FILES = (
    "tests/test_health_only.py",
    "tests/test_database_target_selection.py",
    "tests/test_database_startup_schema.py",
    "tests/test_test_database_safety.py",
    "tests/test_development_startup_verifier.py",
    "tests/test_health_only_local_safety.py",
)


# ==============================================
# OWN THE OFFLINE TEST PROFILE AND LOCAL REPORTS
# ==============================================


def main() -> int:
    """Deny sockets before application imports and exclude every shared conftest."""
    os.chdir(ROOT)
    configure_offline_application()
    guard = OfflineNetworkGuard()
    sys.addaudithook(guard)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = ROOT / "artifacts/health-only-tests" / f"offline-{stamp}"
    output.mkdir(parents=True)

    import pytest

    results = TestResults()
    with (
        (output / "tests.log").open("w", encoding="utf-8") as stream,
        redirect_stdout(stream),
        redirect_stderr(stream),
    ):
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
                    "-q",
                    "--tb=short",
                    f"--junitxml={output / 'results.xml'}",
                    *TEST_FILES,
                ],
                plugins=[results],
            )
        )
    shared_conftest_loaded = any(
        Path(filename).resolve() == ROOT / "tests/conftest.py"
        for module in tuple(sys.modules.values())
        if isinstance(filename := getattr(module, "__file__", None), str)
    )
    report = {
        "pytest_exit_code": code,
        "scope": TEST_FILES,
        "collected": results.collected,
        "outcomes": dict(results.outcomes),
        "subtests": dict(results.subtests),
        "warnings": dict(results.warnings),
        "failed_tests": results.failures,
        "network_denied_categories": dict(guard.denied),
        "shared_conftest_loaded": shared_conftest_loaded,
        "passed": (
            code == 0
            and not guard.denied
            and not shared_conftest_loaded
            and results.outcomes["passed"] == results.collected
            and not results.failures
        ),
    }
    (output / "validation.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    print(f"Local evidence: {output.relative_to(ROOT).as_posix()}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
