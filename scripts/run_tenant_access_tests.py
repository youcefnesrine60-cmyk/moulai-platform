# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Target only the new functional tenant integration; no G2/live-DB repetition."""

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

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    "app/api/tenant_dependencies.py",
    "app/schemas/tenant_access.py",
    "app/repositories/tenant_repo.py",
    "app/services/business/tenant_access.py",
    "tests/test_tenant_access.py",
    "tests/test_tenant_access_http.py",
    "scripts/run_tenant_access_tests.py",
)


# ==============================================
# NETWORK-DENIED TARGETED EXECUTION
# ==============================================


def main() -> int:
    """Use memory SQL, simulated JWKS and a disposable app with no shared conftest."""
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    os.environ.update(
        {
            "DEBUG": "false",
            "DB_ECHO": "false",
            "DATABASE_TARGET": "development",
            "APP_ENV": "development",
            "OIDC_DIAGNOSTICS_ENABLED": "false",
            "OIDC_ALLOW_LOCAL_HTTP": "false",
            "REDIS_URL": "",
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

    output = ROOT / "artifacts/tenant-functional"
    output.mkdir(parents=True, exist_ok=True)
    measurement = coverage.Coverage(
        source=[str(ROOT / "app")],
        data_file=str(output / "access.coverage"),
        config_file=False,
    )
    results = TestResults()
    measurement.start()
    try:
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
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
                        "tests/test_tenant_access.py",
                        "tests/test_tenant_access_http.py",
                    ],
                    plugins=[results],
                )
            )
    finally:
        measurement.stop()
        measurement.save()
    measurement.json_report(
        outfile=str(output / "coverage.json"),
        include=[str(ROOT / source) for source in SOURCES[:4]],
    )
    shared_conftest = any(
        str(getattr(module, "__file__", ""))
        .replace("\\", "/")
        .endswith("tests/conftest.py")
        for module in tuple(sys.modules.values())
    )
    report = {
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "exit_code": code,
        "collected": results.collected,
        "outcomes": dict(results.outcomes),
        "failures": results.failures,
        "warnings": dict(results.warnings),
        "network_attempts": dict(guard.denied),
        "shared_database_conftest_loaded": shared_conftest,
        "database_scope": "disposable memory SQLite; no PostgreSQL or Keycloak connection",
        "g2_rerun": False,
        "sources": {
            source: hashlib.sha256((ROOT / source).read_bytes()).hexdigest()
            for source in SOURCES
        },
    }
    (output / "validation.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    (output / "complete-python-sources.md").write_text(
        "# Complete tenant functional integration sources\n\n"
        + "\n\n".join(
            f"## {source}\n\n```python\n{(ROOT / source).read_text(encoding='utf-8').rstrip()}\n```"
            for source in SOURCES
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))
    return 1 if code or guard.denied or shared_conftest or results.warnings else 0


if __name__ == "__main__":
    raise SystemExit(main())
