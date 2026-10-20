# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Offline HTTP, admission and engine-wiring proofs for health observation."""

import importlib
import json
import os
import subprocess
import sys
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any
from unittest.mock import (
    AsyncMock,
    MagicMock,
    patch,
)

import pytest
from httpx import (
    ASGITransport,
    AsyncClient,
)
from sqlalchemy.engine import Connection
from starlette.middleware import Middleware
from starlette.types import (
    ASGIApp,
    Receive,
    Scope,
    Send,
)

from app.core import database
from app.core.config import Settings
from app.core.health_only import (
    HealthOnlyConfigurationError,
    HealthOnlyMiddleware,
    health_only_database_policy,
    validate_health_only_configuration,
)
from app.core.test_database import UnsafeTestDatabaseError

# ==============================================
# EXPLICIT SYNTHETIC PROFILE, WITH NO USABLE CREDENTIALS
# ==============================================


def configuration(**changes: Any) -> SimpleNamespace:
    """Supply a complete isolated profile without reading local .env values."""
    values = {
        "HEALTH_ONLY_MODE": True,
        "APP_ENV": "development",
        "DATABASE_TARGET": "development",
        "DATABASE_URL": "postgresql+asyncpg://ep-protected-fixture.region.neon.tech/neondb",
        "TEST_DATABASE_URL": "postgresql+asyncpg://ep-development-fixture.region.neon.tech/neondb_test",
        "TEST_DATABASE_PROJECT_ID": "project-fixture",
        "TEST_DATABASE_BRANCH_ID": "br-development-fixture",
        "TEST_DATABASE_ENDPOINT_ID": "ep-development-fixture",
        "PROTECTED_DATABASE_BRANCH_ID": "br-protected-fixture",
        "PROTECTED_DATABASE_ENDPOINT_ID": "ep-protected-fixture",
        "REDIS_URL": "",
        "DEBUG": False,
        "DB_ECHO": False,
        "OIDC_DIAGNOSTICS_ENABLED": False,
        "OIDC_ALLOW_LOCAL_HTTP": False,
    }
    return SimpleNamespace(**(values | changes))


# ==============================================
# FAIL-CLOSED CONFIGURATION AND DEFAULT-OFF REGRESSION
# ==============================================


@pytest.mark.parametrize(
    "changes",
    [
        {"DATABASE_TARGET": "primary"},
        {"APP_ENV": "production"},
        {"APP_ENV": "test"},
        {"REDIS_URL": "redis://localhost:6379/0"},
        {"REDIS_URL": " "},
        {"DEBUG": True},
        {"DB_ECHO": True},
        {"OIDC_DIAGNOSTICS_ENABLED": True},
        {"OIDC_ALLOW_LOCAL_HTTP": True},
        {"TEST_DATABASE_PROJECT_ID": None},
        {"TEST_DATABASE_BRANCH_ID": None},
        {"TEST_DATABASE_ENDPOINT_ID": None},
        {"PROTECTED_DATABASE_BRANCH_ID": None},
        {"PROTECTED_DATABASE_ENDPOINT_ID": None},
        {"TEST_DATABASE_BRANCH_ID": "br-protected-fixture"},
        {"TEST_DATABASE_ENDPOINT_ID": "ep-protected-fixture"},
        {
            "TEST_DATABASE_URL": "postgresql+asyncpg://ep-protected-fixture.region.neon.tech/neondb_test"
        },
        {
            "TEST_DATABASE_URL": "postgresql+asyncpg://ep-development-fixture.region.neon.tech/neondb"
        },
        {
            "TEST_DATABASE_URL": "postgresql+asyncpg://ep-development-fixture.region.neon.tech/neondb_test?options=unsafe"
        },
        {
            "TEST_DATABASE_URL": "postgresql+asyncpg://ep-development-fixture.region.neon.tech/neondb_test?ssl=require"
        },
        {
            "DATABASE_URL": "postgresql+asyncpg://ep-other-fixture.region.neon.tech/neondb"
        },
        {"DATABASE_URL": "invalid-credential-bearing-reference"},
        # Relabelling production as the test endpoint still conflicts with the
        # preserved primary reference, even with a falsified exclusion label.
        {
            "TEST_DATABASE_URL": "postgresql+asyncpg://ep-protected-fixture.region.neon.tech/neondb_test",
            "TEST_DATABASE_ENDPOINT_ID": "ep-protected-fixture",
            "PROTECTED_DATABASE_ENDPOINT_ID": "ep-other-fixture",
        },
    ],
)
def test_health_profile_rejects_unsafe_configuration(changes: dict[str, Any]) -> None:
    """Reject before any engine or external client is opened."""
    with pytest.raises((HealthOnlyConfigurationError, UnsafeTestDatabaseError)):
        validate_health_only_configuration(configuration=configuration(**changes))


# ==============================================
# CENTRAL SETTINGS AND ENGINE CONTRACT
# ==============================================


def test_default_off_preserves_primary_engine_configuration() -> None:
    """Normal mode adds no read-only argument, identity policy or profile gate."""
    assert Settings.model_fields["HEALTH_ONLY_MODE"].default is False
    profile = configuration(HEALTH_ONLY_MODE=False, DATABASE_TARGET="primary")
    snapshot = database._engine_configuration(configuration=profile)
    assert snapshot.database_url == profile.DATABASE_URL
    assert snapshot.connect_arguments == {}
    assert snapshot.health_only_policy is None


# ==============================================
# STRICT CENTRAL SETTINGS VALIDATION
# ==============================================


def test_settings_reject_health_mode_on_primary_without_leaking_inputs() -> None:
    """The startup gate raises a safe fixed code, not a credential-bearing dump."""
    profile = vars(configuration(DATABASE_TARGET="primary")) | {
        "BOT_TOKEN": "private-fixture-token",
        "OPENAI_API_KEY": "private-fixture-api-key",
        "SECRET_KEY": "x" * 32,
    }
    with pytest.raises(HealthOnlyConfigurationError) as failure:
        Settings(_env_file=None, **profile)
    assert str(failure.value) == "health_only_development_target_required"
    assert "private-fixture" not in str(failure.value)


# ==============================================
# IMMUTABLE POLICY AND SERVER DEFAULTS
# ==============================================


def test_health_engine_snapshot_enables_read_only_and_freezes_identity() -> None:
    """Every pooled connection inherits READ ONLY in addition to the begin hook."""
    profile = configuration()
    snapshot = database._engine_configuration(configuration=profile)
    policy = snapshot.health_only_policy
    assert policy is not None
    assert (
        snapshot.connect_arguments["server_settings"]["default_transaction_read_only"]
        == "on"
    )
    profile.TEST_DATABASE_BRANCH_ID = "br-protected-fixture"
    assert policy.branch_id == "br-development-fixture"


# ==============================================
# FRESH PROCESS PROVES THE REAL SETTINGS-TO-ENGINE WIRING
# ==============================================


def test_fresh_health_process_installs_the_guard_without_external_io() -> None:
    """Load the actual application with synthetic URLs and a child network guard."""
    environment = {
        **os.environ,
        **{
            key: str(value).lower() if isinstance(value, bool) else value
            for key, value in vars(configuration()).items()
        },
        "BOT_TOKEN": "offline-health-fixture",
        "OPENAI_API_KEY": "offline-health-fixture",
        "SECRET_KEY": "h" * 32,
        "DATABASE_SYNC_URL": "",
        "TEST_DATABASE_SYNC_URL": "",
        "PYTHON_DOTENV_DISABLED": "1",
    }
    program = """
import json
import sys
from test_support.health_only_safety import OfflineNetworkGuard
guard = OfflineNetworkGuard()
sys.addaudithook(guard)
from sqlalchemy import event
from app import main
from app.core import database
from app.core.redis_client import redis_client
policy = database._DATABASE_CONFIGURATION.health_only_policy
assert policy is not None
assert event.contains(database.engine.sync_engine, 'begin', policy.begin)
assert database.engine.sync_engine.hide_parameters
assert redis_client is None
assert main.app.user_middleware[0].cls.__name__ == 'HealthOnlyMiddleware'
assert main.app.user_middleware[0].kwargs['enabled'] is True
assert not guard.denied
print(json.dumps({'guard_installed': True, 'network_attempts': 0}))
"""
    completed = subprocess.run(
        [sys.executable, "-c", program],
        env=environment,
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout.splitlines()[-1]) == {
        "guard_installed": True,
        "network_attempts": 0,
    }


# ==============================================
# AUTOCOMMIT MUST NOT TURN SET TRANSACTION INTO A NO-OP
# ==============================================


@pytest.mark.parametrize("autocommit", [True, None])
def test_read_only_guard_refuses_autocommit_or_unknown_driver_mode(
    autocommit: bool | None,
) -> None:
    """Refuse before issuing an ineffective SET TRANSACTION outside a transaction."""
    policy = health_only_database_policy(configuration=configuration())
    assert policy is not None
    connection = MagicMock(spec=Connection)
    connection.dialect = SimpleNamespace(name="postgresql")
    connection.connection.dbapi_connection = SimpleNamespace()
    if autocommit is not None:
        connection.connection.dbapi_connection.autocommit = autocommit
    with pytest.raises(HealthOnlyConfigurationError, match="transaction_required"):
        policy.begin(connection)
    connection.exec_driver_sql.assert_not_called()


# ==============================================
# REAL APPLICATION WITH AN INNER SIDE-EFFECT SENTINEL
# ==============================================


class InnerSentinel:
    """Count requests that pass admission before any router/dependency runs."""

    # ==============================================
    # RETAIN THE TEST'S EVENT LIST
    # ==============================================

    def __init__(self, app: ASGIApp, *, calls: list[str]) -> None:
        """Wrap the actual application without altering its business endpoints."""
        self.app = app
        self.calls = calls

    # ==============================================
    # OBSERVE INNER REQUEST DISPATCH
    # ==============================================

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Record actual entry and pass through to the original stack."""
        self.calls.append(scope.get("path", scope["type"]))
        await self.app(scope, receive, send)


@pytest.fixture
def health_application(monkeypatch: pytest.MonkeyPatch) -> Iterator[SimpleNamespace]:
    """Build the real main app with a captured health gate and mocked DB startup."""
    from app import main

    original_app = main.app
    with patch.dict(main.__dict__), monkeypatch.context() as patcher:
        patcher.setattr(main.settings, "HEALTH_ONLY_MODE", True)
        main = importlib.reload(main)
        calls: list[str] = []
        main.app.user_middleware.insert(1, Middleware(InnerSentinel, calls=calls))
        init = AsyncMock()
        close = AsyncMock()
        callbacks = AsyncMock()
        patcher.setattr(main, "init_db", init)
        patcher.setattr(main, "close_db", close)
        patcher.setattr(main, "register_routes", callbacks)
        yield SimpleNamespace(
            app=main.app, calls=calls, init=init, close=close, callbacks=callbacks
        )
    assert main.app is original_app


# ==============================================
# EXACT HTTP ADMISSION MATRIX
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/docs"),
        ("GET", "/redoc"),
        ("GET", "/openapi.json"),
        ("GET", "/webhook"),
        ("POST", "/webhook"),
        ("POST", "/api/v1/users/"),
        ("DELETE", "/api/v1/restaurants/1"),
        ("PUT", "/api/v1/orders/1"),
        ("PATCH", "/api/v1/payments/1"),
        ("GET", "/api/v1/restaurants/"),
        ("GET", "/api/v1/diagnostics/oidc/me"),
        ("GET", "/missing"),
        ("GET", "/health/"),
        ("GET", "/Health"),
        ("GET", "/%68ealth"),
        *(
            (method, path)
            for method in (
                "HEAD",
                "POST",
                "PUT",
                "PATCH",
                "DELETE",
                "OPTIONS",
                "TRACE",
                "CONNECT",
            )
            for path in ("/", "/health")
        ),
    ],
)
async def test_rejected_http_never_reaches_inner_application(
    health_application: SimpleNamespace, method: str, path: str
) -> None:
    """CORS preflight, docs, writes and webhook traffic all stop at admission."""
    async with AsyncClient(
        transport=ASGITransport(app=health_application.app), base_url="http://test"
    ) as client:
        response = await client.request(
            method,
            path,
            headers={
                "Origin": "https://example.org",
                "Access-Control-Request-Method": "POST",
            },
            content=b"sensitive-body-not-dispatched",
        )
    assert response.status_code == 503
    assert response.headers["cache-control"] == "no-store"
    assert health_application.calls == []
    health_application.init.assert_not_awaited()
    health_application.callbacks.assert_not_awaited()


# ==============================================
# HEALTH REQUESTS AND LIFESPAN
# ==============================================


@pytest.mark.asyncio
async def test_health_gets_work_and_callback_initialization_is_skipped(
    health_application: SimpleNamespace,
) -> None:
    """Keep startup checks but do not initialize business callback registrations."""
    app = health_application.app
    async with app.router.lifespan_context(app), AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        root = await client.get("/")
        health = await client.get("/health")
    assert root.status_code == health.status_code == 200
    assert health.json()["status"] == "healthy"
    assert health_application.calls == ["/", "/health"]
    health_application.init.assert_awaited_once()
    health_application.close.assert_awaited_once()
    health_application.callbacks.assert_not_awaited()


# ==============================================
# DISABLED ADMISSION PRESERVES ORDINARY ROUTING
# ==============================================


@pytest.mark.asyncio
async def test_disabled_gate_forwards_requests_without_inspecting_them() -> None:
    """Existing routes and business authorization remain the normal-mode authority."""
    inner = AsyncMock()
    gate = HealthOnlyMiddleware(inner, enabled=False)
    scope: Scope = {"type": "http", "method": "POST", "path": "/api/v1/users/"}
    receive, send = AsyncMock(), AsyncMock()
    await gate(scope, receive, send)
    inner.assert_awaited_once_with(scope, receive, send)


# ==============================================
# REJECT WITHOUT READING THE REQUEST BODY
# ==============================================


@pytest.mark.asyncio
async def test_denial_does_not_consume_body_or_invoke_inner_app() -> None:
    """Even an unreadable incoming webhook body cannot reach business processing."""
    inner, receive, send = AsyncMock(), AsyncMock(), AsyncMock()
    receive.side_effect = AssertionError("The blocked body must not be read")
    await HealthOnlyMiddleware(inner, enabled=True)(
        {"type": "http", "method": "POST", "path": "/webhook"}, receive, send
    )
    inner.assert_not_awaited()
    receive.assert_not_awaited()
    assert send.await_args_list[0].args[0]["status"] == 503


# ==============================================
# WEBSOCKET HANDSHAKE AND LIFESPAN BOUNDARIES
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("http_extension", [True, False])
async def test_websocket_cannot_bypass_health_admission(http_extension: bool) -> None:
    """Use 503 where ASGI supports denial responses; otherwise close with 1008."""
    inner, receive, send = AsyncMock(), AsyncMock(), AsyncMock()
    scope: Scope = {
        "type": "websocket",
        "path": "/health",
        "extensions": {"websocket.http.response": {}} if http_extension else {},
    }
    await HealthOnlyMiddleware(inner, enabled=True)(scope, receive, send)
    inner.assert_not_awaited()
    first = send.await_args_list[0].args[0]
    assert first == (
        {"type": "websocket.http.response.start", "status": 503, "headers": []}
        if http_extension
        else {"type": "websocket.close", "code": 1008}
    )


# ==============================================
# LEGACY PRIMARY POOL MUST REMAIN UNAVAILABLE IN HEALTH MODE
# ==============================================


@pytest.mark.asyncio
async def test_legacy_pool_cannot_connect_to_primary_in_health_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject the legacy helper before opening a second, unguarded DB pool."""
    from app.core import db

    monkeypatch.setattr(db.settings, "HEALTH_ONLY_MODE", True)
    constructor = MagicMock()
    monkeypatch.setattr(db, "AsyncConnectionPool", constructor)
    with pytest.raises(
        HealthOnlyConfigurationError, match="legacy_database_access_disabled"
    ):
        await db.init_db()
    constructor.assert_not_called()
