# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Verify offline-suite isolation and coverage accounting without service IO."""

# ==============================================
# IMPORTS
# ==============================================

import json
import subprocess
import sys
from pathlib import Path

import pytest
from _pytest.reports import TestReport as PytestReport
from _pytest.subtests import (
    SubtestContext,
    SubtestReport,
)

from scripts.run_offline_api_tests import (
    INTEGRATION_FILES,
    PROJECT_ROOT,
    OfflineNetworkGuard,
    coverage_summary,
    selected_tests,
)
from scripts.run_offline_api_tests import TestResults as ResultsRecorder

# ==============================================
# NETWORK GUARD AND LIVE-FIXTURE EXCLUSION
# ==============================================


@pytest.mark.parametrize(
    "path",
    [
        "tests",
        "app/main.py",
        "../outside/test_live.py",
        "tests/api/v1/restaurant/test_restaurants.py",
        *["tests/" + name for name in sorted(INTEGRATION_FILES)],
    ],
)
def test_explicit_live_or_non_test_paths_are_rejected(path: str) -> None:
    """Unsafe suite paths cannot quietly enable shared cleanup fixtures."""
    with pytest.raises(ValueError, match="explicit_offline_test_file_required"):
        selected_tests(paths=[path])


def test_default_selection_keeps_database_integrations_outside_offline_suite() -> None:
    """Integration exclusions affect execution only, never app source coverage."""
    paths = selected_tests(paths=[])
    assert paths
    assert not INTEGRATION_FILES.intersection(Path(path).name for path in paths)
    assert "tests/test_offline_api_runner.py" in paths
    assert all(path.startswith("tests/") and path.endswith(".py") for path in paths)


@pytest.mark.parametrize(
    ("event", "arguments"),
    [
        ("socket.connect", (object(), ("203.0.113.10", 443))),
        ("socket.connect", (object(), ("127.0.0.1", 5432))),
        ("socket.connect", (object(), ("::1", 6379))),
        ("socket.getaddrinfo", ("offline.invalid", 443, 0, 0, 0)),
        ("socket.gethostbyname", ("offline.invalid",)),
        ("socket.gethostbyaddr", ("203.0.113.10",)),
        ("socket.getnameinfo", (("203.0.113.10", 443), 0)),
        ("socket.sendto", (object(), ("203.0.113.10", 53))),
    ],
)
def test_network_policy_rejects_transmissions_without_storing_addresses(
    event: str, arguments: tuple[object, ...]
) -> None:
    """Both remote destinations and local database ports fail closed."""
    guard = OfflineNetworkGuard()
    with pytest.raises(RuntimeError, match="offline_test_network_access_denied"):
        guard(event, arguments)
    assert dict(guard.denied) == {event: 1}
    assert guard.local_socket_pairs == 0
    assert "203.0.113.10" not in repr(vars(guard))


def test_installed_audit_guard_intercepts_events_in_an_independent_process() -> None:
    """Prove audit-hook registration, without attempting an actual connection."""
    script = """
import json
import sys
from scripts.run_offline_api_tests import OfflineNetworkGuard
guard = OfflineNetworkGuard()
sys.addaudithook(guard)
events = (
    ('socket.connect', (object(), ('203.0.113.10', 443))),
    ('socket.getaddrinfo', ('offline.invalid', 443, 0, 0, 0)),
)
for event, arguments in events:
    try:
        sys.audit(event, *arguments)
    except RuntimeError as error:
        assert str(error) == 'offline_test_network_access_denied'
    else:
        raise AssertionError('Audit event escaped the network boundary')
print(json.dumps(dict(guard.denied)))
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=True,
        timeout=30,
    )
    assert json.loads(result.stdout) == {"socket.connect": 1, "socket.getaddrinfo": 1}


# ==============================================
# REPORT ACCURACY
# ==============================================


def test_coverage_aggregation_keeps_unexecuted_namespace_sources() -> None:
    """Zero-hit API files remain in the denominator used for the threshold."""
    data = {
        "files": {
            "app/api/tested.py": {
                "summary": {"num_statements": 10, "covered_lines": 8}
            },
            "app/api/untested.py": {
                "summary": {"num_statements": 10, "covered_lines": 0}
            },
            "app/services/unit.py": {
                "summary": {"num_statements": 10, "covered_lines": 10}
            },
        }
    }
    api = coverage_summary(data=data, prefix="app/api/")
    assert api["files"] == 2 and api["statements"] == 20
    assert api["covered_lines"] == 8 and api["line_percent"] == 40.0
    assert coverage_summary(data=data, prefix="app/")["line_percent"] == 60.0


def test_report_counts_parent_cases_and_unittest_subtests_separately() -> None:
    """Subtests must not inflate the number of passed collected Pytest cases."""
    recorder = ResultsRecorder()
    report = PytestReport(
        nodeid="unit::parent",
        location=("unit.py", 1, "parent"),
        keywords={},
        outcome="passed",
        longrepr=None,
        when="call",
    )
    recorder.pytest_runtest_logreport(report)
    subtest = SubtestReport(
        nodeid="unit::parent",
        location=("unit.py", 1, "parent"),
        keywords={},
        outcome="passed",
        longrepr=None,
        when="call",
        context=SubtestContext(msg="nested", kwargs={}),
    )
    recorder.pytest_runtest_logreport(subtest)
    assert dict(recorder.outcomes) == {"passed": 1}
    assert dict(recorder.subtests) == {"passed": 1}
    assert recorder.parent_nodes == {"unit::parent"}
