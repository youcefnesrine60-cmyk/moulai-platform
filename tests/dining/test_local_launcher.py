# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# LOCAL DINING LAUNCHER ISOLATION CONTRACTS
# Exercise the audit policy without installing a global hook or opening a socket.
# ==============================================

"""Strictly offline checks of the exact loopback surface and destination admission."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND EXPLICIT LOCAL CONTRACTS
# Reuse typed module dependencies without creating a connection or enabling a transport.
# ==============================================

import pytest

from scripts.run_dining_local import LocalDiningNetworkGuard
from test_support.local_postgres import LocalPostgresSettings

# ==============================================
# TEST PUBLIC OR UNOWNED BIND IS DENIED
# Deny a public server or any unrelated local service before bind occurs.
# ==============================================


@pytest.mark.parametrize(
    "address", [("0.0.0.0", 5581), ("127.0.0.1", 5432), ("::", 5581), ("127.0.0.1", 80)]
)
def test_public_or_unowned_bind_is_denied(address: tuple[str, int]) -> None:
    """Deny a public server or any unrelated local service before bind occurs."""
    guard = LocalDiningNetworkGuard()
    with pytest.raises(RuntimeError, match="dining_public_bind_denied"):
        guard("socket.bind", (None, address))
    assert guard.denied["socket.bind"] == 1


# ==============================================
# TEST EXACT OWNED BINDS ARE ALLOWED
# Allow only the test cluster and D1 HTTP loopback listeners.
# ==============================================


@pytest.mark.parametrize(
    "address", [("127.0.0.1", 55432), ("127.0.0.1", 5581), ("127.0.0.1", 5574)]
)
def test_exact_owned_binds_are_allowed(address: tuple[str, int]) -> None:
    """Allow only the test cluster and D1 HTTP loopback listeners."""
    guard = LocalDiningNetworkGuard()
    guard("socket.bind", (None, address))
    assert not guard.denied


# ==============================================
# TEST PROVIDERS REMOTE DATABASES AND OTHER SERVICES DENIED
# AI initialization cannot turn into an allowed provider or distant database call.
# ==============================================


@pytest.mark.parametrize(
    "event,arguments",
    [
        ("socket.connect", (None, ("127.0.0.1", 1))),
        ("socket.connect", (None, ("127.0.0.1", 5581))),
        ("socket.connect", (None, ("203.0.113.1", 443))),
        ("socket.getaddrinfo", ("api.deepseek.com", 443)),
        ("socket.getaddrinfo", ("unapproved.neon.tech", 5432)),
    ],
)
def test_providers_remote_databases_and_other_services_denied(
    event: str, arguments: tuple[object, ...]
) -> None:
    """AI initialization cannot turn into an allowed provider or distant database call."""
    guard = LocalDiningNetworkGuard()
    with pytest.raises(RuntimeError, match="offline_test_network_access_denied"):
        guard(event, arguments)


# ==============================================
# TEST ONLY OWNED POSTGRES CONNECT IS ALLOWED
# The Python HTTP app requires no outgoing HTTP or notification transport.
# ==============================================


def test_only_owned_postgres_connect_is_allowed() -> None:
    """The Python HTTP app requires no outgoing HTTP or notification transport."""
    guard = LocalDiningNetworkGuard()
    guard("socket.connect", (None, ("127.0.0.1", 55432)))
    assert not guard.denied


# ==============================================
# TEST WRONG TARGETS REFUSED WITHOUT CONNECTION
# A local profile is not permission to select a permanent or ambiguous database.
# ==============================================


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+asyncpg://role:local-test-password-only@127.0.0.1:55432/neondb_test",
        "postgresql+asyncpg://moulai_pytest:local-test-password-only@db.neon.tech:5432/neondb",
        "postgresql+asyncpg://moulai_pytest:local-test-password-only@127.0.0.1:5432/moulai_pytest",
    ],
)
def test_wrong_targets_refused_without_connection(url: str) -> None:
    """A local profile is not permission to select a permanent or ambiguous database."""
    with pytest.raises(ValueError, match="local_postgres_destination_not_allowlisted"):
        LocalPostgresSettings(URL=url, INSTANCE_ID="offline-check", PROFILE="dining")
