# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# ISOLATED KEEP-OR-START LAUNCHER CONTRACT
# Exercise the real ownership dispatcher and local readiness checks with explicit offline transports, never a database or provider.
# ==============================================

"""A held lock, old backend or anonymous HTTP 200 must never count as the integrated review."""

from __future__ import annotations

# isort: split
# ==============================================
# OFFLINE CONTROLLED BOUNDARIES
# Replace only local IO and command invocation while retaining the actual dispatcher and network decisions.
# ==============================================

import ssl
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock

import httpx
import pytest

from app.integration.config import IntegrationConfig
from scripts import run_operational_local as launcher

# ==============================================
# SYNTHETIC PINNED CONFIGURATION
# No actual instance metadata or password file is opened by these fixtures.
# ==============================================


@pytest.fixture
def configuration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> IntegrationConfig:
    """Keep the probe's real SSL requirement but supply an in-memory trust context for a mocked transport."""
    context = ssl.create_default_context()
    monkeypatch.setattr(ssl, "create_default_context", lambda **_options: context)
    return cast(
        IntegrationConfig,
        SimpleNamespace(
            instance_id="a" * 32,
            origin="https://127.0.0.1:5180",
            ca_file=tmp_path / "not-a-real-certificate",
            directory=tmp_path,
            process_environment=lambda: None,
        ),
    )


# ==============================================
# IDENTITY AND FRONTEND READINESS
# Fixed loopback GETs must identify the same instance and its TLS-verified development frontend.
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure",
    [
        None,
        "other-instance",
        "old-backend",
        "redirect",
        "frontend-down",
        "foreign-html",
    ],
)
async def test_existing_review_is_verified(
    configuration: IntegrationConfig,
    failure: str | None,
) -> None:
    """Refuse every misleading success response without following redirects or sending credentials."""
    requests: list[httpx.Request] = []

    # ==============================================
    # EXPLICIT LOCAL HTTP FIXTURE
    # Return only the selected readiness failure; no socket transport is available.
    # ==============================================

    def respond(request: httpx.Request) -> httpx.Response:
        """Record the exact destination and fail if any probe attempts a nonlocal endpoint."""
        requests.append(request)
        assert request.method == "GET" and "authorization" not in request.headers
        if request.url.port == 5582:
            assert str(request.url) == "http://127.0.0.1:5582/api/web/local-status"
            if failure == "redirect":
                return httpx.Response(
                    302, headers={"location": "https://not-allowed.invalid"}
                )
            return httpx.Response(
                200,
                json={
                    "service": (
                        "old-backend"
                        if failure == "old-backend"
                        else "moulai-operational-local"
                    ),
                    "instance_id": (
                        "b" * 32
                        if failure == "other-instance"
                        else configuration.instance_id
                    ),
                    "url": configuration.origin + "/access",
                },
            )
        assert str(request.url) == "https://127.0.0.1:5180/access"
        return httpx.Response(
            503 if failure == "frontend-down" else 200,
            headers={"content-type": "text/html"},
            text=(
                "foreign app"
                if failure == "foreign-html"
                else '<script type="module" src="/src/main.tsx"></script>'
            ),
        )

    probe = launcher.require_existing_review(
        configuration=configuration, transport=httpx.MockTransport(respond)
    )
    if failure:
        with pytest.raises(RuntimeError, match="operational_existing_"):
            await probe
    else:
        await probe
    assert len(requests) in {1, 2}


# ==============================================
# KEEP PATH HAS NO STARTUP SIDE EFFECT
# A locked but verified review must not invoke startup, process provisioning or component shutdown.
# ==============================================


def test_keep_dispatch_does_not_start_components(
    configuration: IntegrationConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Run the true CLI dispatch with only ownership and readiness IO replaced."""

    # ==============================================
    # HELD OWNERSHIP FIXTURE
    # The exception is raised on entry, before any startup body could run.
    # ==============================================

    @contextmanager
    def busy(*, directory: Path) -> Iterator[None]:
        """Represent a live host lease without using another real process."""
        raise RuntimeError("operational_instance_already_running")
        yield

    ready = AsyncMock()
    start = AsyncMock(side_effect=AssertionError("Startup must not run"))
    hooks: list[launcher.IntegrationNetworkGuard] = []
    monkeypatch.setattr(
        sys, "argv", ["run_operational_local.py", "serve", "--keep-running"]
    )
    monkeypatch.setattr(launcher, "resolve_instance", lambda **_fields: configuration)
    monkeypatch.setattr(launcher, "local_host_lease", busy)
    monkeypatch.setattr(launcher, "require_existing_review", ready)
    monkeypatch.setattr(launcher, "serve", start)
    monkeypatch.setattr(sys, "addaudithook", hooks.append)
    assert launcher.main() == 0
    ready.assert_awaited_once_with(configuration=configuration)
    start.assert_not_awaited()
    assert hooks[0].destinations == {("127.0.0.1", 5582), ("127.0.0.1", 5180)}
    assert list(configuration.directory.iterdir()) == []


# ==============================================
# DIFFERENT NETWORK CAPABILITIES FOR PROBING AND HOSTING
# Keeping a review requires no database access; ordinary business hosting still cannot make HTTP calls back into its API.
# ==============================================


@pytest.mark.parametrize("readiness", [False, True])
def test_readiness_scope_does_not_expand_host_network(readiness: bool) -> None:
    """Call the real guard directly so tests cannot install an irreversible process-wide network hook."""
    guard = launcher.IntegrationNetworkGuard(readiness_only=readiness)
    admitted, denied = (5582, 55433) if readiness else (55433, 5582)
    guard("socket.connect", (None, ("127.0.0.1", admitted)))
    with pytest.raises(RuntimeError, match="destination_denied"):
        guard("socket.connect", (None, ("127.0.0.1", denied)))
    with pytest.raises(RuntimeError, match="remote_dns_denied"):
        guard("socket.getaddrinfo", ("api.deepseek.com", 443))
    if readiness:
        with pytest.raises(RuntimeError, match="destination_denied"):
            guard("socket.bind", (None, ("127.0.0.1", 5582)))
