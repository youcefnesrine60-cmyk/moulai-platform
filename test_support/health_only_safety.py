# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================


"""Reuse the existing socket boundary and result accounting for scoped tests."""

from __future__ import annotations

import os
import socket
import sys
from collections import Counter
from pathlib import Path
from typing import Any


class OfflineNetworkGuard:
    """Deny network IO, allowing only Python's local asyncio socket pair."""

    # ==============================================
    # INIT
    # ==============================================

    def __init__(self) -> None:
        """Record event categories without retaining addresses or credentials."""
        self.denied: Counter[str] = Counter()
        self.local_socket_pairs = 0
        self._socket_source = str(Path(socket.__file__).resolve())

    # ==============================================
    # IS SOCKET PAIR
    # ==============================================

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

    # ==============================================
    # CALL
    # ==============================================

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


class TestResults:
    """Collect actual Pytest outcomes without depending on console parsing."""

    # ==============================================
    # INIT
    # ==============================================

    def __init__(self) -> None:
        """Initialize outcome and failure inventories."""
        self.outcomes: Counter[str] = Counter()
        self.failures: list[str] = []
        self.subtests: Counter[str] = Counter()
        self.warnings: Counter[str] = Counter()
        self.parent_nodes: set[str] = set()
        self.collected = 0

    # ==============================================
    # PYTEST COLLECTION FINISH
    # ==============================================

    def pytest_collection_finish(self, session: Any) -> None:
        """Record the number of collected executable tests."""
        self.collected = len(session.items)

    # ==============================================
    # PYTEST RUNTEST LOGREPORT
    # ==============================================

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

    # ==============================================
    # PYTEST WARNING RECORDED
    # ==============================================

    def pytest_warning_recorded(self, warning_message: Any) -> None:
        """Record warning categories separately from passing-test totals."""
        self.warnings[warning_message.category.__name__] += 1


# ==============================================
# SYNTHETIC APPLICATION CONFIGURATION IN THE TEST PROCESS ONLY
# ==============================================


def configure_offline_application() -> None:
    """Avoid operator settings and all real integration credentials in test runs."""
    os.environ.update(
        {
            "PYTHON_DOTENV_DISABLED": "1",
            "APP_ENV": "development",
            "DATABASE_TARGET": "primary",
            "HEALTH_ONLY_MODE": "false",
            "DATABASE_URL": "postgresql+asyncpg://ep-protected-fixture.region.neon.tech/neondb",
            "DATABASE_SYNC_URL": "",
            "TEST_DATABASE_URL": "",
            "TEST_DATABASE_SYNC_URL": "",
            "DEBUG": "false",
            "DB_ECHO": "false",
            "REDIS_URL": "",
            "OIDC_DIAGNOSTICS_ENABLED": "false",
            "OIDC_ALLOW_LOCAL_HTTP": "false",
            "BOT_TOKEN": "offline-health-only-fixture",
            "OPENAI_API_KEY": "offline-health-only-fixture",
            "SECRET_KEY": "h" * 32,
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        }
    )
