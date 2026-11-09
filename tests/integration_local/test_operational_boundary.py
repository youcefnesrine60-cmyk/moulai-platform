# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# OFFLINE OPERATIONAL SESSION AND INPUT REGRESSIONS
# Verify expiry, encryption, one-use OIDC state and closed pricing inputs without a database.
# ==============================================

"""Run without shared database fixtures; mocked provider responses are not generation or live auth proof."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Only temporary local SQLite storage and explicit HTTP mock transports are used below.
# ==============================================

import asyncio
import sqlite3
import time
from contextlib import closing
from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from urllib.parse import parse_qs

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import auth
from app.integration.config import IntegrationConfig
from app.integration.identity import KeycloakBrowserClient
from app.integration.process import local_host_lease
from app.integration.sessions import BrowserSessions
from app.models.loyalty_discount import Promotion
from app.schemas.saas_pricing import (
    BasePriceCommand,
    CampaignCommand,
    ReminderCommand,
)
from app.services.business.saas_pricing_admin import SaasPricingAdministration
from scripts.run_operational_local import IntegrationNetworkGuard

# ==============================================
# TEMPORARY ENCRYPTED SESSION FACTORY
# Keep test credentials synthetic and never load the operational private account files.
# ==============================================


@pytest.fixture
def store(tmp_path: Path) -> BrowserSessions:
    """Create one private temporary store, independent from the running browser instance."""
    return BrowserSessions(
        path=tmp_path / "sessions.sqlite3", key=Fernet.generate_key().decode()
    )


# ==============================================
# ENCRYPTION AND DURABLE LOGOUT
# Reopening storage must preserve only live encrypted records; logout removes their authority.
# ==============================================


def test_session_is_encrypted_and_deleted(store: BrowserSessions) -> None:
    """Verify actual SQLite bytes, a fresh store object and committed deletion."""
    # ==============================================
    # SCENARIO
    # Verify actual SQLite bytes, a fresh store object and committed deletion.
    # ==============================================

    async def scenario() -> None:
        "Verify actual SQLite bytes, a fresh store object and committed deletion."
        tokens = {
            "access_token": "synthetic-access",
            "refresh_token": "synthetic-refresh",
        }
        identifier = await store.create(tokens=tokens, expires=int(time.time()) + 60)
        with closing(sqlite3.connect(store.path)) as connection, connection:
            digest, payload = connection.execute(
                "SELECT digest,payload FROM browser_sessions"
            ).fetchone()
        assert identifier != digest and b"synthetic-access" not in payload
        assert await store.read(identifier=identifier) == tokens
        await store.delete(identifier=identifier)
        assert await store.read(identifier=identifier) is None

    asyncio.run(scenario())


# ==============================================
# EXPIRED OR CORRUPTED STATE
# A damaged session must fail closed without leaking decrypted provider values.
# ==============================================


@pytest.mark.parametrize("failure", ["expired", "corrupt", "unknown"])
def test_invalid_session_fails_closed(store: BrowserSessions, failure: str) -> None:
    """Use committed local records, without modifying provider or business state."""
    # ==============================================
    # SCENARIO
    # Use committed local records, without modifying provider or business state.
    # ==============================================

    async def scenario() -> None:
        "Use committed local records, without modifying provider or business state."
        identifier = await store.create(
            tokens={"access_token": "fixture", "refresh_token": "fixture"},
            expires=int(time.time()) + 60,
        )
        with closing(sqlite3.connect(store.path)) as connection, connection:
            if failure == "expired":
                connection.execute("UPDATE browser_sessions SET expires=0")
            elif failure == "corrupt":
                connection.execute(
                    "UPDATE browser_sessions SET payload=?",
                    (b"not-authenticated-ciphertext",),
                )
            else:
                identifier = "invalid"
        assert await store.read(identifier=identifier) is None

    asyncio.run(scenario())


# ==============================================
# STRICT SESSION INPUTS
# Accept only the expected encrypted payload shape and a future integer expiry.
# ==============================================


@pytest.mark.parametrize(
    "tokens,expires",
    [
        ({}, 123),
        ({"access_token": "x", "refresh_token": "y"}, 0),
        ({"access_token": 42, "refresh_token": "y"}, 9999999999),
    ],
)
def test_invalid_session_record_is_rejected(
    store: BrowserSessions, tokens: dict[str, object], expires: int
) -> None:
    """Reject malformed state before a browser cookie could be issued."""
    with pytest.raises(ValueError):
        asyncio.run(store.create(tokens=tokens, expires=expires))


# ==============================================
# OFFLINE PROVIDER CLIENT
# Mock only the exchange transport; keep one-use state, cookie and PKCE mechanics real.
# ==============================================


@pytest.fixture
def provider(
    store: BrowserSessions, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> KeycloakBrowserClient:
    """Construct a local-only client without trusting a real provider in this offline test."""
    import ssl

    from app.integration import identity

    monkeypatch.setattr(
        identity.ssl,
        "create_default_context",
        lambda **_kwargs: ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT),
    )
    configuration = IntegrationConfig(
        directory=tmp_path,
        instance_id="a" * 32,
        database_url="postgresql+asyncpg://moulai_integrated:"
        + "a" * 64
        + "@127.0.0.1:55433/moulai_integrated",
        client_secret="synthetic",
        session_key="unused",
        admin_password="synthetic",
    )
    return KeycloakBrowserClient(configuration=configuration, sessions=store)


# ==============================================
# INVALID STATE NEVER EXCHANGES A CODE
# Browser binding and replay protection are independent from the provider's response.
# ==============================================


@pytest.mark.parametrize("failure", ["cookie", "unknown", "expired"])
def test_invalid_login_never_calls_provider(
    provider: KeycloakBrowserClient, failure: str
) -> None:
    """No mocked token endpoint may be reached when admission fails."""
    # ==============================================
    # SCENARIO
    # No mocked token endpoint may be reached when admission fails.
    # ==============================================

    async def scenario() -> None:
        "No mocked token endpoint may be reached when admission fails."
        url, cookie = provider.begin()
        state = parse_qs(url.split("?", 1)[1])["state"][0]
        if failure == "cookie":
            cookie = "incorrect"
        if failure == "unknown":
            state = "unknown"
        if failure == "expired":
            from dataclasses import replace

            provider.pending[state] = replace(provider.pending[state], expires=0)
        provider.http.post = AsyncMock(
            side_effect=AssertionError("network must not be called")
        )
        with pytest.raises(HTTPException) as caught:
            await provider.finish(state=state, cookie=cookie, code="fixture-code")
        assert caught.value.status_code == 401
        provider.http.post.assert_not_called()
        await provider.http.aclose()

    asyncio.run(scenario())


# ==============================================
# POSITIVE ONE-USE ADMISSION
# Token verification is mocked here; the separate browser acceptance verifies actual RS256/TLS.
# ==============================================


def test_valid_state_uses_pkce_once(
    provider: KeycloakBrowserClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unchanged valid state is admitted once and cannot be replayed."""
    # ==============================================
    # SCENARIO
    # An unchanged valid state is admitted once and cannot be replayed.
    # ==============================================

    async def scenario() -> None:
        "An unchanged valid state is admitted once and cannot be replayed."
        url, cookie = provider.begin()
        state = parse_qs(url.split("?", 1)[1])["state"][0]
        attempt = provider.pending[state]
        monkeypatch.setattr(
            auth,
            "_verified_access_token_claims",
            AsyncMock(
                return_value={"sub": "fixture-sub", "exp": int(time.time()) + 60}
            ),
        )
        monkeypatch.setattr(
            auth,
            "_get_jwks_client",
            lambda _url: SimpleNamespace(
                get_signing_key_from_jwt=lambda _token: SimpleNamespace(key="fixture")
            ),
        )
        from app.integration import identity

        monkeypatch.setattr(
            identity.jwt,
            "decode",
            lambda *_args, **_kwargs: {"sub": "fixture-sub", "nonce": attempt.nonce},
        )
        calls = []
        # ==============================================
        # EXCHANGE
        # Keep this local operation within its explicit inputs and resource boundary.
        # ==============================================

        def exchange(request: httpx.Request) -> httpx.Response:
            "Return fixture tokens only after checking the pinned endpoint and PKCE verifier."
            assert request.url.host == "127.0.0.1" and request.url.port == 8444
            data = parse_qs(request.content.decode())
            assert data["code_verifier"] == [attempt.verifier]
            calls.append(request.url.path)
            return httpx.Response(
                200,
                json={
                    "access_token": "fixture",
                    "refresh_token": "fixture",
                    "id_token": "fixture",
                },
            )

        await provider.http.aclose()
        provider.http = httpx.AsyncClient(transport=httpx.MockTransport(exchange))
        identifier, lifetime = await provider.finish(
            state=state, cookie=cookie, code="fixture-code"
        )
        assert lifetime > 0 and await provider.sessions.read(identifier=identifier)
        with pytest.raises(HTTPException):
            await provider.finish(state=state, cookie=cookie, code="fixture-code")
        assert len(calls) == 1
        await provider.http.aclose()

    asyncio.run(scenario())


# ==============================================
# PINNED NETWORK TARGETS
# Probe the Python audit policy itself without opening a socket or touching another service.
# ==============================================


@pytest.mark.parametrize(
    "address",
    [("api.deepseek.com", 443), ("127.0.0.1", 5432), ("0.0.0.0", 5582), ("::1", 8444)],
)
def test_remote_and_wrong_ports_refused(address: tuple[str, int]) -> None:
    """A plausible local or provider name never expands the explicit allowlist."""
    with pytest.raises(RuntimeError):
        IntegrationNetworkGuard()("socket.connect", (object(), address))


# ==============================================
# CLOSED PRICING INTENT
# No request can smuggle permission fields, float percentages or unversioned edits.
# ==============================================


@pytest.mark.parametrize(
    "change",
    [
        {"discount_percent": 3.5},
        {"starts_at": "2026-12-01T00:00:00"},
        {"discount_percent": "101"},
        {"expires_at": "2026-11-01T00:00:00Z"},
    ],
)
def test_campaign_values_reject_ambiguous_inputs(change: dict[str, object]) -> None:
    """Validate request contracts offline; these are not approved commercial prices."""
    values = {
        "name": "SYNTHETIC CONTRACT TEST",
        "discount_percent": "2",
        "starts_at": "2026-12-01T00:00:00Z",
        "expires_at": "2027-01-01T00:00:00Z",
        "priority": 1,
        **change,
    }
    with pytest.raises(ValidationError):
        CampaignCommand.model_validate(
            {"operation": "create", "reason": "offline test", "values": values}
        )


# ==============================================
# EVERY EXISTING CAMPAIGN REQUIRES A DIGEST
# Mutation types are separate and cannot be authorized merely by a role field in JSON.
# ==============================================


@pytest.mark.parametrize("operation", ["update", "publish", "deactivate"])
def test_campaign_mutation_requires_version(operation: str) -> None:
    """Reject a stale or absent approval shape before SQL execution."""
    with pytest.raises(ValidationError):
        CampaignCommand.model_validate(
            {"operation": operation, "identifier": 1, "reason": "test"}
        )


# ==============================================
# BASE PARAMETER NEVER USES A FLOAT OR FUTURE APPROXIMATION
# Keep the existing Numeric precision and explicit immediate-effect contract.
# ==============================================


@pytest.mark.parametrize(
    "change",
    [
        {"amount": 3000.1},
        {"amount": "1.001"},
        {"effective": "tomorrow"},
        {"role": "super_admin"},
    ],
)
def test_base_parameter_closed_contract(change: dict[str, object]) -> None:
    """Caller-declared roles or unsupported scheduling cannot change the canonical value."""
    with pytest.raises(ValidationError):
        BasePriceCommand.model_validate(
            {
                "amount": "3000",
                "expected_sha256": "a" * 64,
                "effective": "on_commit",
                "reason": "offline",
                **change,
            }
        )


# ==============================================
# NUMERIC SCALE CANONICAL DIGEST
# PostgreSQL's eight decimal places must not invalidate an unchanged freshly created draft.
# ==============================================


def test_campaign_digest_preserves_numeric_equivalence() -> None:
    """Reproduce Decimal scale normalization while retaining strict content comparison."""

    # ==============================================
    # SCENARIO
    # Reproduce Decimal scale normalization while retaining strict content comparison.
    # ==============================================

    async def scenario() -> None:
        "Reproduce Decimal scale normalization while retaining strict content comparison."
        session = AsyncMock(spec=AsyncSession)
        session.scalar.return_value = "pricing.create"
        service = SaasPricingAdministration(session=session)
        row = Promotion(
            id=1,
            name="OFFLINE FIXTURE",
            discount_percent=Decimal("2.125"),
            priority=1,
            starts_at=datetime(2027, 1, 1, tzinfo=timezone.utc).replace(tzinfo=None),
            expires_at=datetime(2027, 2, 1, tzinfo=timezone.utc).replace(tzinfo=None),
            active=False,
        )
        before = await service.view(row=row)
        row.discount_percent = Decimal("2.12500000")
        assert (await service.view(row=row))["sha256"] == before["sha256"]
        row.discount_percent = Decimal("2.12600000")
        assert (await service.view(row=row))["sha256"] != before["sha256"]

    asyncio.run(scenario())


# ==============================================
# SINGLETON NUMERIC SCALE
# Editing B with integer-looking decimal text must keep the same post-commit revision digest.
# ==============================================


def test_base_digest_preserves_numeric_equivalence() -> None:
    """Compare actual Numeric representations without accepting a different amount or policy."""
    service = SaasPricingAdministration(session=AsyncMock(spec=AsyncSession))
    policies = {"currencies": {"DZD": {"decimals": 2}}}
    before = service.base_view(
        amount=Decimal(3000), policies=policies, revision="test-version"
    )
    assert (
        service.base_view(
            amount=Decimal("3000.00"), policies=policies, revision="test-version"
        )["sha256"]
        == before["sha256"]
    )
    assert (
        service.base_view(
            amount=Decimal("3000.01"), policies=policies, revision="test-version"
        )["sha256"]
        != before["sha256"]
    )


# ==============================================
# REVOKED OR UNAVAILABLE IDENTITY PROVIDER
# A cached valid token never bypasses the current session-state check.
# ==============================================


@pytest.mark.parametrize("failure", ["inactive", "foreign-subject", "unavailable"])
def test_provider_introspection_fails_closed(
    provider: KeycloakBrowserClient, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    """Use explicit mocked failures; never connect to the running local or a remote provider."""

    # ==============================================
    # SCENARIO
    # Use explicit mocked failures; never connect to the running local or a remote provider.
    # ==============================================

    async def scenario() -> None:
        "Use explicit mocked failures; never connect to the running local or a remote provider."
        identifier = await provider.sessions.create(
            tokens={"access_token": "fixture", "refresh_token": "fixture"},
            expires=int(time.time()) + 60,
        )
        monkeypatch.setattr(
            auth,
            "_verified_access_token_claims",
            AsyncMock(
                return_value={
                    "iss": provider.configuration.issuer,
                    "sub": "fixture-sub",
                }
            ),
        )

        # ==============================================
        # INTROSPECT
        # Return the requested offline provider failure without transmitting any request.
        # ==============================================

        def introspect(request: httpx.Request) -> httpx.Response:
            "Return the requested offline provider failure without transmitting any request."
            if failure == "unavailable":
                raise httpx.ConnectError("offline fixture", request=request)
            return httpx.Response(
                200,
                json={
                    "active": failure != "inactive",
                    "sub": (
                        "other-sub" if failure == "foreign-subject" else "fixture-sub"
                    ),
                },
            )

        await provider.http.aclose()
        provider.http = httpx.AsyncClient(transport=httpx.MockTransport(introspect))
        with pytest.raises(HTTPException) as caught:
            await provider.identity(identifier=identifier)
        assert caught.value.status_code == (503 if failure == "unavailable" else 401)
        await provider.http.aclose()

    asyncio.run(scenario())


# ==============================================
# NON-CONNECT NETWORK CHANNELS
# UDP and alternate DNS calls must not bypass the explicit TCP transport boundary.
# ==============================================


@pytest.mark.parametrize(
    "event",
    [
        "socket.sendto",
        "socket.sendmsg",
        "socket.gethostbyname",
        "socket.gethostbyaddr",
        "socket.getnameinfo",
    ],
)
def test_alternate_network_channels_refused(event: str) -> None:
    """Probe policy admission only; no datagram or DNS request is transmitted."""
    guard = IntegrationNetworkGuard()
    with pytest.raises(RuntimeError):
        guard(event, ())
    assert guard.denied[event] == 1


# ==============================================
# CANONICAL ENGINE REVISION EVIDENCE
# New calculation metadata identifies the selected existing B without duplicating formulas.
# ==============================================


def test_engine_retains_base_revision(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exercise the actual base breakdown with only database lookups replaced offline."""
    from app.services.business import pricing_service

    monkeypatch.setattr(
        pricing_service, "plan_features", AsyncMock(return_value=("basic", {}, set()))
    )
    monkeypatch.setattr(
        pricing_service,
        "configuration",
        AsyncMock(
            return_value=(
                Decimal(3000),
                {
                    "currencies": {"DZD": {"decimals": 2}},
                    "base_revision": "approved-local-revision",
                },
            )
        ),
    )
    monkeypatch.setattr(pricing_service, "feature_costs", AsyncMock(return_value={}))
    amount, parameters = asyncio.run(
        pricing_service.base_breakdown(
            session=AsyncMock(spec=AsyncSession), plan_id=1, billing_cycle="monthly"
        )
    )
    assert amount == Decimal(3000)
    assert (
        parameters["B"] == "3000"
        and parameters["base_revision"] == "approved-local-revision"
    )


# ==============================================
# DUPLICATE HOST ADMISSION
# Reject a second launcher before any shared component can be restarted or stopped.
# ==============================================


def test_host_lease_is_exclusive_and_released(tmp_path: Path) -> None:
    """Exercise actual local file locking without starting a server or database."""
    with (
        local_host_lease(directory=tmp_path),
        pytest.raises(RuntimeError, match="operational_instance_already_running"),
        local_host_lease(directory=tmp_path),
    ):
        pytest.fail("A competing host was admitted")
    with local_host_lease(directory=tmp_path):
        assert (tmp_path / "host.lock").is_file()


# ==============================================
# CONFIGURATION CONSTRUCTOR BOUNDARY
# The public configuration type rejects accidental remote targets before any side effect.
# ==============================================


@pytest.mark.parametrize(
    "change",
    [
        {
            "database_url": "postgresql+asyncpg://user:synthetic-only-password-with-32-chars@remote.invalid:5432/neondb"
        },
        {"issuer": "https://remote.invalid/realms/moulai-local"},
        {"origin": "https://remote.invalid"},
    ],
)
def test_direct_remote_configuration_refused(
    tmp_path: Path, change: dict[str, str]
) -> None:
    """Validate construction only; no hostname resolution, credentials lookup or connection occurs."""
    values = {
        "directory": tmp_path,
        "instance_id": "a" * 32,
        "database_url": "postgresql+asyncpg://moulai_integrated:"
        + "a" * 64
        + "@127.0.0.1:55433/moulai_integrated",
        "client_secret": "offline-fixture",
        "session_key": "offline-fixture",
        "admin_password": "offline-fixture",
        **change,
    }
    with pytest.raises(ValueError, match="integration_nonlocal_configuration_refused"):
        IntegrationConfig(**values)


# ==============================================
# CLOSED FUTURE REMINDER CALENDAR
# Invalid offsets or caller-supplied authority never reach persisted settings.
# ==============================================


@pytest.mark.parametrize(
    "days", [[14, 14, 0], [0, 14], [14, 7, 1], [14, -1, 0], [14.0, 0], [True, 0]]
)
def test_reminder_calendar_rejects_ambiguous_days(days: list[object]) -> None:
    """Validate strict integers, uniqueness, ordering and the mandatory expiry event offline."""
    with pytest.raises(ValidationError):
        ReminderCommand(
            days=days, expected_sha256="a" * 64, reason="Offline contract proof"
        )


# ==============================================
# EXISTING APPROVED OFFSETS ARE ACCEPTED
# The test establishes request admission only, not delivery or a commercial policy change.
# ==============================================


def test_approved_reminder_calendar_admission() -> None:
    """Keep the configured 14/7/1/0 baseline valid without a notification transport."""
    command = ReminderCommand(
        days=[14, 7, 1, 0], expected_sha256="a" * 64, reason="Offline contract proof"
    )
    assert command.days == [14, 7, 1, 0]
