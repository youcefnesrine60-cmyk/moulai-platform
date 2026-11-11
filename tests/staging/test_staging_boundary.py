# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# OFFLINE STAGING ADMISSION REGRESSIONS
# Verify target refusal, proxy/origin boundaries and compiled UI delivery without
# a provider call, database connection, production secret or business mutation.
# ==============================================

"""These mocks test admission only, not remote identity or end-to-end deployment."""

from __future__ import annotations

# isort: split
# ==============================================
# FIXED SYNTHETIC TEST INPUTS
# Test credentials are generated in RAM and cannot authenticate with any provider.
# ==============================================

import json
from dataclasses import replace
from ipaddress import ip_network
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest
from cryptography.fernet import Fernet

from app.staging.config import StagingConfig
from app.staging.target import StagingTarget

ROOT = Path(__file__).resolve().parents[2]


# ==============================================
# CLOSED CONFIGURATION FIXTURE
# Use only offline .invalid origins and the public target manifest.
# ==============================================


def configuration(*, directory: Path) -> StagingConfig:
    """Create no identity, database object, role or permission."""
    target = StagingTarget.load(path=ROOT / "deploy/staging/target.json")
    return StagingConfig(
        target=target,
        directory=directory,
        database_url="postgresql+asyncpg://"
        + target.runtime_role
        + ":offline-fixture@"
        + target.host
        + "/"
        + target.database,
        client_secret="offline-fixture" * 4,
        session_key=Fernet.generate_key().decode(),
        origin="https://moulai-staging.example.invalid",
        issuer="https://identity.example.invalid/realms/moulai-staging",
        client_id="moulai-staging-browser",
        audience="moulai-staging-api",
        proxy_networks=(ip_network("10.55.0.0/24"),),
    )


# ==============================================
# TARGET AND SECRET FAILURES
# A global environment URL or administrative role cannot silently become runtime authority.
# ==============================================


@pytest.mark.parametrize(
    "change",
    [
        {"project_id": "shiny-lab-60817779"},
        {"database": "neondb"},
        {"database": "neondb_test"},
        {"branch_id": "br-plain-firefly-as17il6w"},
        {"endpoint_id": "ep-quiet-rain-assrs0gv"},
    ],
)
def test_historical_targets_refused(*, change: dict[str, str]) -> None:
    """Reject production and development metadata before any connection."""
    target = StagingTarget.load(path=ROOT / "deploy/staging/target.json")
    with pytest.raises(ValueError, match="staging_target_not_approved"):
        replace(target, **change)


# ==============================================
# OIDC AND PROXY ADMISSION
# HTTPS alone never authorizes arbitrary realms, callback hosts or wildcard proxies.
# ==============================================


@pytest.mark.parametrize(
    "change",
    [
        {"origin": "http://moulai-staging.example.invalid"},
        {"issuer": "https://identity.example.invalid/realms/master"},
        {"origin": "https://moulai-staging.example.invalid/path"},
        {"proxy_networks": (ip_network("0.0.0.0/0"),)},
        {"client_secret": "short"},
    ],
)
def test_host_configuration_refused(
    tmp_path: Path, *, change: dict[str, object]
) -> None:
    """Refuse incomplete or overbroad hosting configuration without external IO."""
    with pytest.raises(ValueError):
        replace(configuration(directory=tmp_path), **change)


# ==============================================
# DISABLED LEGACY PROVIDER CONFIGURATION
# Required legacy settings must validate without importing a real secret or provider.
# ==============================================


def test_staging_process_overrides_provider_without_file_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Replace inherited credentials only in a disposable mapping, never in .env."""
    import os

    isolated = dict(os.environ)
    isolated["OPENAI_API_KEY"] = "offline-inherited-fixture"
    monkeypatch.setattr(os, "environ", isolated)
    config = configuration(directory=tmp_path)
    config.process_environment()
    assert isolated["OPENAI_API_KEY"] == "staging-provider-disabled"
    assert isolated["OPENAI_BASE_URL"] == "https://provider-disabled.invalid"
    assert isolated["AI_MODEL"] == "staging-provider-disabled"
    assert isolated["PYTHON_DOTENV_DISABLED"] == "1"
    assert isolated["DATABASE_URL"] == config.database_url
    assert not list(tmp_path.iterdir())


# ==============================================
# LIVE DATABASE IDENTITY CONTRACT
# The mock distinguishes every server identity field and schema revision.
# ==============================================


def test_database_identity_and_role_required() -> None:
    """Require runtime role, true branch metadata and marker in addition to the URL."""
    target = StagingTarget.load(path=ROOT / "deploy/staging/target.json")
    connection = MagicMock()
    valid = (
        target.database,
        target.runtime_role,
        target.project_id,
        target.branch_id,
        target.endpoint_id,
        "moulai-staging:" + target.instance_id,
    )
    connection.execute.return_value.one.return_value = valid
    connection.scalar.return_value = "o520261111"
    target.attest(connection=connection, migration=False, require_revision=True)
    for index in range(6):
        row = list(valid)
        row[index] = "foreign"
        connection.execute.return_value.one.return_value = tuple(row)
        with pytest.raises(RuntimeError, match="identity_mismatch"):
            target.attest(connection=connection, migration=False)
    connection.execute.return_value.one.return_value = valid
    for revision in ("s1a20261028", "o420261108", "unknown"):
        connection.scalar.return_value = revision
        with pytest.raises(RuntimeError, match="revision_mismatch"):
            target.attest(connection=connection, migration=False, require_revision=True)


# ==============================================
# SIGNED TESTER ROLE IS NOT BUSINESS AUTHORITY
# Owners/admins without an invitation cannot enter the remote acceptance host.
# ==============================================


@pytest.mark.parametrize(
    "roles", [frozenset(), frozenset({"owner"}), frozenset({"admin"})]
)
def test_uninvited_tester_refused(tmp_path: Path, *, roles: frozenset[str]) -> None:
    """Exercise only the verified-role admission step, with no provider transport."""
    from fastapi import HTTPException

    from app.integration.identity import KeycloakBrowserClient

    provider = object.__new__(KeycloakBrowserClient)
    provider.configuration = configuration(directory=tmp_path)
    with pytest.raises(HTTPException) as result:
        provider.require_environment_role(roles=roles)
    assert result.value.status_code == 403
    assert (
        provider.require_environment_role(roles=frozenset({"moulai-staging-tester"}))
        is None
    )


# ==============================================
# REAL ASGI BOUNDARY WITH OFFLINE PROVIDER
# No lifespan/database connection is started for these transport-only checks.
# ==============================================


@pytest.mark.asyncio
async def test_staging_browser_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep public health separate from business access, enforce origin/proxy, and protect files."""
    from app.api import auth
    from app.staging.web import create_staging_app

    config = configuration(directory=tmp_path)
    (tmp_path / "private").mkdir()
    monkeypatch.setattr(auth.settings, "DATABASE_URL", config.database_url)
    monkeypatch.setattr(auth.settings, "OIDC_ISSUER", config.issuer)
    monkeypatch.setattr(auth.settings, "OIDC_ALLOW_LOCAL_HTTP", False)
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    (frontend / "index.html").write_text(
        "<html><script>window.test=1</script><body>synthetic staging</body></html>"
    )
    (frontend / "staging-build.json").write_text(
        json.dumps(
            {"mode": "staging", "syntheticOnly": True, "fixtureAdapterIncluded": False}
        )
    )
    app = create_staging_app(configuration=config, frontend=frontend)
    try:
        transport = httpx.ASGITransport(app=app, client=("10.55.0.2", 5000))
        async with httpx.AsyncClient(
            transport=transport,
            base_url=config.origin,
            headers={"X-Forwarded-Proto": "https"},
        ) as client:
            response = await client.get("/access")
            assert response.status_code == 200
            assert "sha256-" in response.headers["content-security-policy"]
            assert (
                "script-src 'self' 'unsafe-inline'"
                not in response.headers["content-security-policy"]
            )
            assert (await client.get("/api/web/session")).json() is None
            assert (await client.get("/api/web/unknown")).status_code == 401
            assert (await client.get("/..%2Foutside.txt")).status_code == 404
            assert (await client.post("/api/web/auth/logout")).status_code == 403
            assert (
                await client.get("/access", headers={"Host": "foreign.invalid"})
            ).status_code == 403
            assert (
                await client.get("/access", headers={"X-Forwarded-Proto": "http"})
            ).status_code == 403
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, client=("203.0.113.2", 1000)),
            base_url=config.origin,
        ) as outsider:
            assert (await outsider.get("/access")).status_code == 403
            assert (await outsider.get("/health")).json()["syntheticOnly"] is True
    finally:
        await app.state.browser_provider.http.aclose()
        await app.state.browser_engine.dispose()


# ==============================================
# REALM MANIFEST IS SECRET-FREE AND CLOSED
# Generation grants no tester account, business privilege or password flow.
# ==============================================


def test_realm_manifest_requires_exact_callback() -> None:
    """Keep Keycloak setup reviewable without configuring any provider."""
    from scripts.prepare_staging_identity import realm_manifest

    value = realm_manifest(
        origin="https://staging.example.invalid",
        client_id="staging-browser",
        audience="staging-api",
    )
    assert value["users"] == [] and value["registrationAllowed"] is False
    client = value["clients"][0]
    assert client["directAccessGrantsEnabled"] is False
    assert client["redirectUris"] == [
        "https://staging.example.invalid/api/web/auth/callback"
    ]
    assert "secret" not in client
    with pytest.raises(ValueError):
        realm_manifest(origin="http://localhost", client_id="browser", audience="api")


# ==============================================
# OUTBOUND PROVIDERS STAY UNREACHABLE
# DNS and socket audit checks use mock addresses and never open a socket.
# ==============================================


def test_staging_egress_denies_unrelated_services(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Permit only approved endpoint ports; refuse AI DNS and foreign connections."""
    import socket

    from app.staging.network import StagingNetworkGuard

    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda _host, port, **_kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.0.2.10", port))
        ],
    )
    guard = StagingNetworkGuard(
        configuration=configuration(directory=tmp_path), port=10000
    )
    guard("socket.connect", (None, ("192.0.2.10", 5432)))
    guard("socket.bind", (None, ("0.0.0.0", 10000)))
    with pytest.raises(RuntimeError):
        guard("socket.getaddrinfo", ("api.deepseek.com", 443))
    with pytest.raises(RuntimeError):
        guard("socket.connect", (None, ("192.0.2.11", 443)))
