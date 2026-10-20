# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Exercise administrative HTTP trust boundaries without database or network IO."""

# ==============================================
# IMPORTS
# ==============================================

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import (
    Any,
    TypeAlias,
)
from unittest.mock import (
    AsyncMock,
    Mock,
)

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from httpx import (
    ASGITransport,
    AsyncClient,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import auth
from app.api.v1 import registration_request
from app.api.v1.admin import (
    admin_log,
    admin_session,
)
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import UnauthorizedError
from app.services.business.admin import admin_service

# ==============================================
# ISOLATED HTTP AND DATABASE BOUNDARIES
# ==============================================

JsonObject: TypeAlias = dict[str, Any]
ROUTERS = (admin_log.router, admin_session.router, registration_request.router)
SERVICE_DEPENDENCIES = (
    admin_log.get_admin_log_service,
    admin_session.get_admin_session_service,
    registration_request.get_registration_request_service,
)
CONFIGURATION = ("OIDC_ISSUER", "OIDC_AUDIENCE", "OIDC_JWKS_URL")


@dataclass(frozen=True)
class AdministrativeEndpoint:
    """Identify a real administrative operation exposed by these routers."""

    method: str
    path: str

    @property
    def identifier(self) -> str:
        """Make the HTTP operation visible in parametrized test reports."""
        return f"{self.method} {self.path}"


def administrative_endpoints() -> tuple[AdministrativeEndpoint, ...]:
    """Cover each current HTTP operation using harmless test-only identifiers."""
    endpoints: list[AdministrativeEndpoint] = []
    for router in ROUTERS:
        for route in router.routes:
            if not isinstance(route, APIRoute):
                continue
            path = route.path_format
            for parameter in route.param_convertors:
                path = path.replace("{" + parameter + "}", "7")
            for method in sorted(route.methods):
                endpoints.append(AdministrativeEndpoint(method, "/api/v1" + path))
    return tuple(endpoints)


ENDPOINTS = administrative_endpoints()


@dataclass
class AdministrativeHarness:
    """Record all storage, key lookup, and endpoint service boundaries."""

    app: FastAPI
    session: AsyncMock
    key_client: Mock
    service_access: list[str]

    def assert_no_operations(self) -> None:
        """Ensure rejected requests cannot read or change operational storage."""
        self.session.execute.assert_not_awaited()
        self.session.scalar.assert_not_awaited()
        self.session.scalars.assert_not_awaited()
        self.session.commit.assert_not_awaited()
        self.session.flush.assert_not_awaited()
        self.session.add.assert_not_called()
        self.session.delete.assert_not_awaited()
        self.key_client.assert_not_called()
        assert self.service_access == []


@pytest.fixture
def administrative_harness(
    monkeypatch: pytest.MonkeyPatch,
) -> AdministrativeHarness:
    """Replace IO only; exercise the actual router authentication dependencies."""
    for name in CONFIGURATION:
        monkeypatch.setattr(settings, name, None)
    app = FastAPI()
    for router in ROUTERS:
        app.include_router(router, prefix="/api/v1")
    session = AsyncMock(spec=AsyncSession)
    key_client = Mock(side_effect=AssertionError("Unexpected signing-key lookup"))
    monkeypatch.setattr(auth, "_get_jwks_client", key_client)
    service_access: list[str] = []

    async def database_boundary() -> AsyncIterator[AsyncMock]:
        """Provide an inert session without opening a database connection."""
        yield session

    async def forbidden_service() -> None:
        """Expose any attempt to invoke a business service before authorization."""
        service_access.append("endpoint-service")
        raise AssertionError("Unauthorized endpoint service access")

    app.dependency_overrides[get_db] = database_boundary
    for dependency in SERVICE_DEPENDENCIES:
        app.dependency_overrides[dependency] = forbidden_service
    return AdministrativeHarness(app, session, key_client, service_access)


def spoofed_identifiers() -> JsonObject:
    """Supply numeric and role claims that must never confer administrative access."""
    return {
        "admin_id": 7,
        "owner_id": 7,
        "chat_id": 7,
        "auth_subject": "unverified-subject",
        "role": "superadmin",
        "permissions": ["admins.manage", "subscriptions.review"],
        "status": "approved",
        "approved": True,
        "action": "approve",
        "session_token": "local-session-token",
        "expires_at": "2099-01-01T00:00:00",
    }


# ==============================================
# FAIL CLOSED BEFORE ADMINISTRATION OR APPROVAL
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", ENDPOINTS, ids=lambda item: item.identifier)
@pytest.mark.parametrize("bearer", [False, True], ids=["identifiers", "forged-bearer"])
async def test_unconfigured_keycloak_rejects_every_admin_http_operation(
    administrative_harness: AdministrativeHarness,
    endpoint: AdministrativeEndpoint,
    bearer: bool,
) -> None:
    """IDs in paths, query, and bodies cannot approve registrations or administer IO."""
    headers = {
        "X-Admin-Session-Token": "local-session-token",
        "X-Preserve-Session-Token": "local-session-token",
    }
    if bearer:
        headers["Authorization"] = "Bearer untrusted-admin-id-7"
    async with AsyncClient(
        transport=ASGITransport(app=administrative_harness.app),
        base_url="https://local.test",
    ) as client:
        response = await client.request(
            endpoint.method,
            endpoint.path,
            headers=headers,
            params={"admin_id": 7, "chat_id": 7, "owner_id": 7},
            json=spoofed_identifiers(),
        )
    assert response.status_code == 503, response.text
    administrative_harness.assert_no_operations()


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", ENDPOINTS, ids=lambda item: item.identifier)
async def test_configured_keycloak_does_not_trust_forged_identifiers(
    monkeypatch: pytest.MonkeyPatch,
    administrative_harness: AdministrativeHarness,
    endpoint: AdministrativeEndpoint,
) -> None:
    """Configuration alone cannot turn a supplied admin ID into a verified identity."""
    monkeypatch.setattr(settings, "OIDC_ISSUER", "https://keycloak.test/realms/local")
    monkeypatch.setattr(settings, "OIDC_AUDIENCE", "local-admin-api")
    monkeypatch.setattr(
        settings,
        "OIDC_JWKS_URL",
        "https://keycloak.test/realms/local/protocol/openid-connect/certs",
    )
    async with AsyncClient(
        transport=ASGITransport(app=administrative_harness.app),
        base_url="https://local.test",
    ) as client:
        response = await client.request(
            endpoint.method,
            endpoint.path,
            headers={
                "Authorization": "Bearer untrusted-admin-id-7",
                "X-Admin-Session-Token": "local-session-token",
                "X-Preserve-Session-Token": "local-session-token",
            },
            params={"admin_id": 7, "chat_id": 7, "owner_id": 7},
            json=spoofed_identifiers(),
        )
    assert response.status_code == 401, response.text
    administrative_harness.assert_no_operations()


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", ENDPOINTS, ids=lambda item: item.identifier)
async def test_verified_identity_still_requires_current_admin_management_permission(
    monkeypatch: pytest.MonkeyPatch,
    administrative_harness: AdministrativeHarness,
    endpoint: AdministrativeEndpoint,
) -> None:
    """A verified identity without live admins.manage cannot reach these operations."""

    async def verified_identity() -> auth.AdminPrincipal:
        """Isolate identity verification while retaining the actual permission guard."""
        return auth.AdminPrincipal(admin_id=7)

    check_permission = AsyncMock(side_effect=UnauthorizedError("Permission revoked"))
    service_factory = Mock(return_value=Mock(check_admin_permission=check_permission))
    monkeypatch.setattr(admin_service, "AdminService", service_factory)
    administrative_harness.app.dependency_overrides[auth.get_current_admin] = (
        verified_identity
    )
    async with AsyncClient(
        transport=ASGITransport(app=administrative_harness.app),
        base_url="https://local.test",
    ) as client:
        response = await client.request(
            endpoint.method,
            endpoint.path,
            headers={
                "X-Admin-Session-Token": "local-session-token",
                "X-Preserve-Session-Token": "local-session-token",
            },
            params={"admin_id": 999, "chat_id": 999},
            json=spoofed_identifiers(),
        )
    assert response.status_code == 403, response.text
    check_permission.assert_awaited_once_with(
        admin_id=7, required_permission="admins.manage"
    )
    administrative_harness.assert_no_operations()


# ==============================================
# AUTHORIZED STATIC ROUTING WITHOUT CRUD
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "expected_method"),
    [
        ("/admin-logs/search?query=approval", "search_logs"),
        ("/admin-logs/recent", "get_recent_activity"),
        (
            "/admin-logs/date-range?start_date=2026-10-01T00:00:00"
            "&end_date=2026-10-13T00:00:00",
            "get_logs_by_date_range",
        ),
        ("/admin-sessions/statistics", "get_statistics"),
        ("/registration-requests/stats/summary", "count_pending"),
    ],
)
async def test_authorized_static_paths_reach_their_read_service(
    administrative_harness: AdministrativeHarness,
    path: str,
    expected_method: str,
) -> None:
    """Static operations cannot be swallowed by an earlier integer identifier route."""

    async def trusted_administrator() -> auth.AdminPrincipal:
        """Override the completed permission guard only in this routing test."""
        return auth.AdminPrincipal(admin_id=7)

    service = Mock(
        search_logs=AsyncMock(
            return_value={"items": [], "total": 0, "skip": 0, "limit": 100}
        ),
        get_recent_activity=AsyncMock(return_value=[]),
        get_logs_by_date_range=AsyncMock(
            return_value={"items": [], "total": 0, "skip": 0, "limit": 100}
        ),
        get_statistics=AsyncMock(
            return_value={
                "total_sessions": 0,
                "active_sessions": 0,
                "expired_sessions": 0,
            }
        ),
        get_all=AsyncMock(return_value=[]),
        count_pending=AsyncMock(return_value=0),
        count_by_status=AsyncMock(return_value=0),
        get_by_id=AsyncMock(side_effect=AssertionError("Unexpected identifier lookup")),
    )

    async def readonly_service() -> Mock:
        """Provide successful read responses while performing no database writes."""
        return service

    for router in ROUTERS:
        administrative_harness.app.dependency_overrides[
            router.dependencies[0].dependency
        ] = trusted_administrator
    for dependency in SERVICE_DEPENDENCIES:
        administrative_harness.app.dependency_overrides[dependency] = readonly_service
    async with AsyncClient(
        transport=ASGITransport(app=administrative_harness.app),
        base_url="https://local.test",
    ) as client:
        response = await client.get("/api/v1" + path)
    assert response.status_code == 200, response.text
    getattr(service, expected_method).assert_awaited_once()
    service.get_by_id.assert_not_awaited()
    administrative_harness.assert_no_operations()


def test_integer_converters_preserve_openapi_identifier_paths(
    administrative_harness: AdministrativeHarness,
) -> None:
    """Keep the API contract readable while restricting runtime identifier matching."""
    paths = administrative_harness.app.openapi()["paths"]
    assert "/api/v1/admin-logs/{log_id}" in paths
    assert "/api/v1/admin-sessions/admin/{admin_id}" in paths
    assert "/api/v1/registration-requests/{request_id}/approve" in paths
    assert all(":int" not in path for path in paths)
