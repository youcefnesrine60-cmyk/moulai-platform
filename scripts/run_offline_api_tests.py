# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Run isolated HTTP contracts with coverage and a mandatory network guard.

Shared conftest files are deliberately disabled: their integration fixtures
truncate the development database. This runner executes mocked HTTP and unit
contracts only. It never starts the application's database lifecycle.
"""

# ==============================================
# IMPORTS AND OFFLINE SUITE
# ==============================================

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import socket
import sys
from collections import Counter
from collections.abc import Sequence
from datetime import (
    datetime,
    timezone,
)
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIRECTORY = PROJECT_ROOT / "artifacts" / "api-test-review"
INTEGRATION_FILES = frozenset(
    {
        "test_k10_postgres.py",
        "test_manual_payment_workflow.py",
        "test_admin_rbac_refresh.py",
        "test_order_postgres_transactions.py",
        "test_order_tenant_isolation.py",
        "test_payment_subscription_transactions.py",
        "test_payment_tenant_isolation.py",
        "test_pricing_discount_database_integration.py",
        "test_rbac_branch_database_integration.py",
    }
)


# ==============================================
# FAIL-CLOSED NETWORK BOUNDARY
# ==============================================


class OfflineNetworkGuard:
    """Deny network IO, allowing only Python's local asyncio socket pair."""

    def __init__(self) -> None:
        """Record event categories without retaining addresses or credentials."""
        self.denied: Counter[str] = Counter()
        self.local_socket_pairs = 0
        self._socket_source = str(Path(socket.__file__).resolve())

    def _is_socket_pair(self) -> bool:
        """Recognize Windows' stdlib-only implementation of socket.socketpair."""
        frame = sys._getframe(1)
        while frame is not None:
            if (
                frame.f_code.co_filename == self._socket_source
                and frame.f_code.co_name in {"socketpair", "_fallback_socketpair"}
            ):
                return True
            frame = frame.f_back
        return False

    def __call__(self, event: str, arguments: tuple[Any, ...]) -> None:
        """Reject DNS and socket transmissions before the operation occurs."""
        if event not in {
            "socket.connect",
            "socket.sendto",
            "socket.sendmsg",
            "socket.getaddrinfo",
            "socket.gethostbyname",
            "socket.gethostbyaddr",
            "socket.getnameinfo",
        }:
            return
        if event == "socket.connect" and len(arguments) > 1:
            address = arguments[1]
            if (
                isinstance(address, tuple)
                and address[0] in {"127.0.0.1", "::1"}
                and self._is_socket_pair()
            ):
                self.local_socket_pairs += 1
                return
        self.denied[event] += 1
        raise RuntimeError("offline_test_network_access_denied")


# ==============================================
# EXPLICIT TEST SELECTION AND RESULTS
# ==============================================


def selected_tests(*, paths: Sequence[str]) -> list[str]:
    """Select repository tests without loading live integration fixtures."""
    if not paths:
        candidates = [
            *sorted((PROJECT_ROOT / "tests").glob("test_*.py")),
            *sorted((PROJECT_ROOT / "tests/api/unit").rglob("test_*.py")),
        ]
        return [
            path.relative_to(PROJECT_ROOT).as_posix()
            for path in candidates
            if path.name not in INTEGRATION_FILES
        ]
    selected: list[str] = []
    test_root = PROJECT_ROOT / "tests"
    for name in paths:
        path = (PROJECT_ROOT / name).resolve()
        if (
            not path.is_relative_to(test_root)
            or not path.is_file()
            or not path.name.startswith("test_")
            or path.suffix != ".py"
            or path.name in INTEGRATION_FILES
            or "restaurant" in path.relative_to(test_root).parts
        ):
            raise ValueError("explicit_offline_test_file_required")
        selected.append(path.relative_to(PROJECT_ROOT).as_posix())
    return selected


class TestResults:
    """Collect actual Pytest outcomes without depending on console parsing."""

    def __init__(self) -> None:
        """Initialize outcome and failure inventories."""
        self.outcomes: Counter[str] = Counter()
        self.failures: list[str] = []
        self.subtests: Counter[str] = Counter()
        self.warnings: Counter[str] = Counter()
        self.parent_nodes: set[str] = set()
        self.collected = 0

    def pytest_collection_finish(self, session: Any) -> None:
        """Record the number of collected executable tests."""
        self.collected = len(session.items)

    def pytest_runtest_logreport(self, report: Any) -> None:
        """Separate test-call results from setup and teardown failures."""
        if type(report).__name__ in {"SubtestReport", "SubTestReport"}:
            self.subtests[report.outcome] += 1
            if report.failed:
                self.failures.append(report.nodeid)
            return
        if report.when == "call":
            self.parent_nodes.add(report.nodeid)
            self.outcomes[report.outcome] += 1
        elif report.failed:
            self.outcomes[f"{report.when}_error"] += 1
        elif report.skipped and report.when == "setup":
            self.outcomes["skipped"] += 1
        if report.failed:
            self.failures.append(report.nodeid)

    def pytest_warning_recorded(self, warning_message: Any) -> None:
        """Record warning categories separately from passing-test totals."""
        self.warnings[warning_message.category.__name__] += 1


def coverage_summary(*, data: dict[str, Any], prefix: str) -> dict[str, Any]:
    """Aggregate the unchanged source denominator for app or its API subtree."""
    files = {
        name: result
        for name, result in data["files"].items()
        if name.replace("\\", "/").startswith(prefix)
    }
    statements = sum(item["summary"]["num_statements"] for item in files.values())
    covered = sum(item["summary"]["covered_lines"] for item in files.values())
    return {
        "source": prefix,
        "files": len(files),
        "statements": statements,
        "covered_lines": covered,
        "missing_lines": statements - covered,
        "line_percent": 100.0 * covered / statements if statements else 0.0,
    }


# ==============================================
# GUARDED RUNNER ENTRY POINT
# ==============================================


def main(*, arguments: Sequence[str] | None = None) -> int:
    """Measure all application Python sources and save local, bounded reports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--name", default="final")
    parser.add_argument("--minimum", type=float, default=50.0)
    options = parser.parse_args(arguments)
    if re.fullmatch(r"[a-z][a-z0-9-]{0,63}", options.name) is None:
        parser.error("name must be a short lowercase report identifier")
    if not 0 <= options.minimum <= 100:
        parser.error("minimum must be between 0 and 100")
    try:
        paths = selected_tests(paths=options.paths)
    except ValueError as error:
        parser.error(str(error))
    if not paths:
        parser.error("at least one offline test is required")

    os.chdir(PROJECT_ROOT)
    sys.path.insert(0, str(PROJECT_ROOT))
    os.environ["DEBUG"] = "false"
    os.environ["REDIS_URL"] = ""
    os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    guard = OfflineNetworkGuard()
    sys.addaudithook(guard)

    import coverage
    import pytest

    expected_sources = {
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in (PROJECT_ROOT / "app").rglob("*.py")
    }
    source_hashes = {
        name: hashlib.sha256((PROJECT_ROOT / name).read_bytes()).hexdigest()
        for name in sorted(expected_sources)
    }
    data_path = OUTPUT_DIRECTORY / f"{options.name}.coverage"
    measurement = coverage.Coverage(
        source=[str(PROJECT_ROOT / "app")],
        data_file=str(data_path),
        config_file=False,
    )
    # Routers use namespace packages. Missing files must remain in the report.
    measurement.set_option("report:include_namespace_packages", True)
    results = TestResults()
    started = datetime.now(timezone.utc)
    measurement.start()
    try:
        exit_code = int(
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
                    *paths,
                ],
                plugins=[results],
            )
        )
    finally:
        measurement.stop()
        measurement.save()

    json_path = OUTPUT_DIRECTORY / f"{options.name}-coverage.json"
    measurement.json_report(outfile=str(json_path))
    measurement.html_report(directory=str(OUTPUT_DIRECTORY / f"{options.name}-html"))
    measurement.xml_report(
        outfile=str(OUTPUT_DIRECTORY / f"{options.name}-coverage.xml")
    )
    data = json.loads(json_path.read_text(encoding="utf-8"))
    reported_sources = {name.replace("\\", "/") for name in data["files"]}
    if reported_sources != expected_sources:
        raise RuntimeError("coverage_source_inventory_mismatch")
    if any(
        hashlib.sha256((PROJECT_ROOT / name).read_bytes()).hexdigest() != digest
        for name, digest in source_hashes.items()
    ):
        raise RuntimeError("application_source_changed_during_coverage_run")
    shared_conftest = PROJECT_ROOT / "tests" / "conftest.py"
    shared_conftest_loaded = any(
        isinstance(filename := getattr(module, "__file__", None), str)
        and Path(filename).resolve() == shared_conftest
        for module in tuple(sys.modules.values())
    )
    application = coverage_summary(data=data, prefix="app/")
    api = coverage_summary(data=data, prefix="app/api/")
    targets_met = all(
        result["line_percent"] > options.minimum for result in (application, api)
    )
    accounting_valid = (
        sum(results.outcomes[name] for name in ("passed", "failed"))
        == len(results.parent_nodes)
        <= results.collected
    )
    report = {
        "started_at": started.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "scope": paths,
        "collected": results.collected,
        "outcomes": dict(results.outcomes),
        "subtests": dict(results.subtests),
        "case_accounting_valid": accounting_valid,
        "warnings": dict(results.warnings),
        "warnings_as_errors": True,
        "failed_tests": results.failures,
        "pytest_exit_code": exit_code,
        "network_denied_categories": dict(guard.denied),
        "network_guard_scope": "Python socket audit events, not OS-level isolation",
        "allowed_stdlib_socketpair_connections": guard.local_socket_pairs,
        "application": application,
        "api": api,
        "minimum_exclusive": options.minimum,
        "targets_met": targets_met,
        "source_exclusions": [],
        "source_inventory_verified": True,
        "source_sha256": source_hashes,
        "shared_conftest_loaded": shared_conftest_loaded,
        "passed": (
            exit_code == 0
            and not guard.denied
            and not shared_conftest_loaded
            and accounting_valid
            and targets_met
        ),
    }
    report_path = OUTPUT_DIRECTORY / f"{options.name}-results.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
