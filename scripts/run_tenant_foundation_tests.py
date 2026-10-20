# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Run B1 contracts without conftest, live databases, sockets or real Keycloak."""

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


# ==============================================
# MAIN
# ==============================================


def main() -> int:
    """Install the existing network guard before any application import."""
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
    import coverage
    import pytest

    output = PROJECT_ROOT / "artifacts" / "keycloak-k9-b1"
    output.mkdir(parents=True, exist_ok=True)
    measurement = coverage.Coverage(
        source=[str(PROJECT_ROOT / "app")],
        data_file=str(output / "foundation.coverage"),
        config_file=False,
    )
    results = TestResults()
    measurement.start()
    try:
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
                    "tests/test_tenant_foundation.py",
                    "tests/test_tenant_foundation_oidc.py",
                ],
                plugins=[results],
            )
        )
    finally:
        measurement.stop()
        measurement.save()
    measurement.json_report(
        outfile=str(output / "foundation-coverage.json"),
        include=[
            "*/tenant_types.py",
            "*/tenant_context.py",
            "*/models/tenant/*.py",
            "*/tenant_repo.py",
            "*/tenant_foundation.py",
        ],
    )
    report = {
        "pytest_exit_code": code,
        "collected": results.collected,
        "outcomes": dict(results.outcomes),
        "failed_tests": results.failures,
        "warnings": dict(results.warnings),
        "network_denied_categories": dict(guard.denied),
        "network_guard_scope": "Python socket audit events; no OS-level network sandbox claim",
        "sqlite_scope": "disposable in-memory fixtures only; no PostgreSQL locking evidence",
        "conftest_loaded": any(
            str(getattr(module, "__file__", "")).endswith("tests/conftest.py")
            or str(getattr(module, "__file__", "")).endswith("tests\\conftest.py")
            for module in tuple(sys.modules.values())
        ),
    }
    report["passed"] = code == 0 and not guard.denied and not report["conftest_loaded"]
    (output / "validation.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
