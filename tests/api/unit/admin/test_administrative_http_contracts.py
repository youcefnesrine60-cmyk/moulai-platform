# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Exercise administrative HTTP contracts with inert storage and real RBAC guards."""

# ==============================================
# IMPORTS
# ==============================================

import json
import logging
from collections.abc import AsyncIterator
from dataclasses import (
    dataclass,
    replace,
)
from datetime import (
    UTC,
    datetime,
)
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
from httpx import (
    ASGITransport,
    AsyncClient,
    Response,
)
from pydantic import ValidationError as SchemaValidationError
from sqlalchemy.exc import StatementError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import auth
from app.api.v1.admin import (
    admin,
    admin_log,
    admin_session,
)
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from app.core.logger import logger
from app.schemas.admin_log import AdminLogFilter
from app.services.business.admin import admin_service

# ==============================================
# DETERMINISTIC REQUEST AND RESPONSE DATA
# ==============================================

JsonObject: TypeAlias = dict[str, Any]
STAMP = "2026-01-01T12:00:00"
FUTURE = "2099-01-01T12:00:00"
TOKEN = "local-session-token"
ADMIN = {
    "id": 7,
    "chat_id": 700,
    "username": "reviewer",
    "full_name": "Local Reviewer",
    "role": "admin",
    "is_active": True,
    "created_at": STAMP,
    "updated_at": STAMP,
}
LOG = {
    "id": 8,
    "admin_id": 7,
    "action": "view",
    "resource": "payment",
    "resource_id": 9,
    "details": {"source": "http-contract"},
    "ip_address": None,
    "user_agent": None,
    "timestamp": STAMP,
    "created_at": STAMP,
}
SESSION = {
    "id": 9,
    "admin_id": 7,
    "session_token": TOKEN,
    "ip_address": None,
    "user_agent": None,
    "expires_at": FUTURE,
    "is_active": True,
    "last_activity": STAMP,
    "created_at": STAMP,
    "updated_at": STAMP,
}


def page(*, item: JsonObject, skip: int = 3, limit: int = 2) -> JsonObject:
    """Return one serialized page with distinct pagination values."""
    return {"items": [item], "total": 6, "skip": skip, "limit": limit}


@dataclass(frozen=True)
class Operation:
    """Describe one public operation independently of its handler implementation."""

    method: str
    path: str
    service: str
    result: Any
    kwargs: JsonObject
    params: JsonObject | None = None
    body: JsonObject | None = None
    headers: dict[str, str] | None = None
    status: int = 200


OPERATIONS = (
    Operation(
        "POST",
        "/admins/",
        "create_admin",
        ADMIN,
        {
            "admin_data": {
                "chat_id": 700,
                "username": "reviewer",
                "full_name": "Local Reviewer",
                "password": None,
                "role": "admin",
                "is_active": True,
            }
        },
        body={"chat_id": 700, "username": "Reviewer", "full_name": "Local Reviewer"},
        status=201,
    ),
    Operation(
        "GET",
        "/admins/7",
        "get_admin_by_id",
        ADMIN,
        {"admin_id": 7, "include_inactive": True},
        params={"include_inactive": True},
    ),
    Operation(
        "GET",
        "/admins/username/reviewer",
        "get_admin_by_username",
        ADMIN,
        {"username": "reviewer", "include_inactive": False},
    ),
    Operation(
        "GET",
        "/admins/chat/700",
        "get_admin_by_chat_id",
        ADMIN,
        {"chat_id": 700, "include_inactive": False},
    ),
    Operation(
        "GET",
        "/admins/",
        "get_all_admins",
        page(item=ADMIN),
        {
            "only_active": False,
            "skip": 3,
            "limit": 2,
            "order_by": "username",
            "order_desc": True,
        },
        params={
            "only_active": False,
            "skip": 3,
            "limit": 2,
            "order_by": "username",
            "order_desc": True,
        },
    ),
    Operation(
        "GET",
        "/admins/",
        "search_admins",
        page(item=ADMIN),
        {"query": "review", "only_active": True, "skip": 3, "limit": 2},
        params={"search": "review", "role": "admin", "skip": 3, "limit": 2},
    ),
    Operation(
        "GET",
        "/admins/",
        "get_admins_by_role",
        page(item=ADMIN),
        {"role": "manager", "only_active": True, "skip": 3, "limit": 2},
        params={"role": "manager", "skip": 3, "limit": 2},
    ),
    Operation(
        "PATCH",
        "/admins/7",
        "update_admin",
        ADMIN,
        {
            "admin_id": 7,
            "update_data": {
                "username": "reviewer",
                "full_name": None,
                "password": None,
                "role": None,
                "is_active": None,
            },
        },
        body={"username": "Reviewer"},
    ),
    Operation(
        "PATCH",
        "/admins/7/role",
        "update_admin_role",
        ADMIN,
        {"admin_id": 7, "role": "manager"},
        params={"role": "manager"},
    ),
    Operation(
        "PATCH",
        "/admins/7/toggle-status",
        "toggle_admin_status",
        ADMIN,
        {"admin_id": 7},
    ),
    Operation(
        "DELETE",
        "/admins/7",
        "delete_admin",
        None,
        {"admin_id": 7, "permanent": True},
        params={"permanent": True},
        status=204,
    ),
    Operation(
        "GET",
        "/admins/statistics",
        "get_admin_statistics",
        {"total": 6, "active": 5, "inactive": 1, "roles": {"admin": 5, "manager": 1}},
        {},
    ),
    Operation(
        "POST",
        "/admin-logs/",
        "create_log",
        LOG,
        {
            "log_data": {
                "admin_id": 7,
                "action": "view",
                "resource": "payment",
                "resource_id": 9,
                "details": {"source": "http-contract"},
                "ip_address": None,
                "user_agent": None,
            }
        },
        body={
            "admin_id": 7,
            "action": "VIEW",
            "resource": "payment",
            "resource_id": 9,
            "details": {"source": "http-contract"},
        },
        status=201,
    ),
    Operation("GET", "/admin-logs/8", "get_log_by_id", LOG, {"log_id": 8}),
    Operation(
        "GET",
        "/admin-logs/admin/7",
        "get_logs_by_admin",
        page(item=LOG),
        {
            "admin_id": 7,
            "filters": {
                "action": "view",
                "resource": "payment",
                "start_date": None,
                "end_date": None,
            },
            "skip": 3,
            "limit": 2,
        },
        params={"action": "VIEW", "resource": "payment", "skip": 3, "limit": 2},
    ),
    Operation(
        "GET",
        "/admin-logs/search",
        "search_logs",
        page(item=LOG),
        {"query": "payment", "admin_id": 7, "skip": 3, "limit": 2},
        params={"query": "payment", "admin_id": 7, "skip": 3, "limit": 2},
    ),
    Operation(
        "GET",
        "/admin-logs/summary/actions",
        "get_actions_summary",
        [{"action": "view", "count": 6}],
        {"admin_id": 7, "limit": 2},
        params={"admin_id": 7, "limit": 2},
    ),
    Operation(
        "GET",
        "/admin-logs/recent",
        "get_recent_activity",
        [LOG],
        {"admin_id": 7, "limit": 2},
        params={"admin_id": 7, "limit": 2},
    ),
    Operation(
        "GET",
        "/admin-logs/date-range",
        "get_logs_by_date_range",
        page(item=LOG),
        {
            "start_date": datetime(2026, 1, 1, tzinfo=UTC),
            "end_date": datetime(2026, 1, 2, tzinfo=UTC),
            "admin_id": 7,
            "skip": 3,
            "limit": 2,
        },
        params={
            "start_date": "2026-01-01T00:00:00Z",
            "end_date": "2026-01-02T00:00:00Z",
            "admin_id": 7,
            "skip": 3,
            "limit": 2,
        },
    ),
    Operation(
        "GET",
        "/admin-logs/action/view",
        "get_logs_by_action",
        page(item=LOG),
        {"action": "view", "admin_id": 7, "skip": 3, "limit": 2},
        params={"admin_id": 7, "skip": 3, "limit": 2},
    ),
    Operation(
        "POST",
        "/admin-sessions/",
        "create_session",
        SESSION,
        {
            "session_data": {
                "admin_id": 7,
                "expires_at": FUTURE,
                "ip_address": None,
                "user_agent": None,
            }
        },
        body={"admin_id": 7, "expires_at": FUTURE},
        status=201,
    ),
    Operation(
        "GET",
        "/admin-sessions/lookup",
        "get_session_by_token",
        SESSION,
        {"session_token": TOKEN},
        headers={"X-Admin-Session-Token": TOKEN},
    ),
    Operation(
        "GET",
        "/admin-sessions/lookup/active",
        "get_active_session",
        SESSION,
        {"session_token": TOKEN},
        headers={"X-Admin-Session-Token": TOKEN},
    ),
    Operation(
        "GET",
        "/admin-sessions/lookup/status",
        "get_session_status",
        {"is_active": True, "admin_id": 7},
        {"session_token": TOKEN},
        headers={"X-Admin-Session-Token": TOKEN},
    ),
    Operation(
        "GET",
        "/admin-sessions/admin/7",
        "get_sessions_by_admin",
        page(item=SESSION),
        {"admin_id": 7, "only_active": False, "skip": 3, "limit": 2},
        params={"only_active": False, "skip": 3, "limit": 2},
    ),
    Operation(
        "GET",
        "/admin-sessions/admin/7/active",
        "get_active_sessions_by_admin",
        page(item=SESSION),
        {"admin_id": 7, "skip": 3, "limit": 2},
        params={"skip": 3, "limit": 2},
    ),
    Operation(
        "PATCH",
        "/admin-sessions/lookup/activity",
        "update_activity",
        SESSION,
        {"session_token": TOKEN},
        headers={"X-Admin-Session-Token": TOKEN},
    ),
    Operation(
        "DELETE",
        "/admin-sessions/lookup/deactivate",
        "deactivate_session",
        SESSION,
        {"session_token": TOKEN},
        headers={"X-Admin-Session-Token": TOKEN},
    ),
    Operation(
        "DELETE",
        "/admin-sessions/admin/7/all",
        "deactivate_all_sessions",
        None,
        {"admin_id": 7, "except_session_token": TOKEN},
        headers={"X-Preserve-Session-Token": TOKEN},
        status=204,
    ),
    Operation(
        "PATCH",
        "/admin-sessions/extend",
        "extend_session",
        SESSION,
        {"extend_data": {"session_token": TOKEN, "expires_at": FUTURE}},
        body={"session_token": f" {TOKEN} ", "expires_at": FUTURE},
    ),
    Operation(
        "GET",
        "/admin-sessions/statistics",
        "get_statistics",
        {"total_sessions": 6, "active_sessions": 5, "expired_sessions": 1},
        {"admin_id": 7},
        params={"admin_id": 7},
    ),
    Operation(
        "POST",
        "/admin-sessions/cleanup",
        "cleanup_expired_sessions",
        3,
        {"days": 90},
        params={"days": 90},
    ),
)


@dataclass
class AdminHarness:
    """Contain HTTP dependencies without opening any external resources."""

    app: FastAPI
    service: Mock
    permission: AsyncMock
    session: AsyncMock

    async def request(self, *, operation: Operation) -> Response:
        """Dispatch a real ASGI request with application exceptions made visible."""
        async with AsyncClient(
            transport=ASGITransport(app=self.app), base_url="https://local.test"
        ) as client:
            return await client.request(
                operation.method,
                "/api/v1" + operation.path,
                params=operation.params,
                json=operation.body,
                headers=operation.headers,
            )


@pytest.fixture
def admin_harness(monkeypatch: pytest.MonkeyPatch) -> AdminHarness:
    """Keep real permission resolution while replacing identity and business IO."""
    app = FastAPI()
    for router in (admin.router, admin_log.router, admin_session.router):
        app.include_router(router, prefix="/api/v1")
    session = AsyncMock(spec=AsyncSession)
    service = Mock()
    for operation in OPERATIONS:
        setattr(service, operation.service, AsyncMock())
    permission = AsyncMock()
    monkeypatch.setattr(
        admin_service,
        "AdminService",
        Mock(return_value=Mock(check_admin_permission=permission)),
    )

    async def database_boundary() -> AsyncIterator[AsyncMock]:
        """Supply an inert session; no connection may be acquired."""
        yield session

    async def trusted_identity() -> auth.AdminPrincipal:
        """Represent identity verification without trusting caller-provided IDs."""
        return auth.AdminPrincipal(admin_id=71)

    async def service_boundary() -> Mock:
        """Replace only the business collaborator for the HTTP contract."""
        return service

    app.dependency_overrides[get_db] = database_boundary
    app.dependency_overrides[auth.get_current_admin] = trusted_identity
    for dependency in (
        admin.get_admin_service,
        admin_log.get_admin_log_service,
        admin_session.get_admin_session_service,
    ):
        app.dependency_overrides[dependency] = service_boundary
    return AdminHarness(app, service, permission, session)


# ==============================================
# AUTHORIZED HTTP RESPONSES AND DELEGATION
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", OPERATIONS, ids=lambda item: item.service)
async def test_authorized_operation_preserves_its_http_contract(
    admin_harness: AdminHarness, operation: Operation
) -> None:
    """Check real routing, schema normalization, status, response and RBAC identity."""
    method = getattr(admin_harness.service, operation.service)
    method.return_value = operation.result
    response = await admin_harness.request(operation=operation)
    assert response.status_code == operation.status, response.text
    admin_harness.permission.assert_awaited_once_with(
        admin_id=71, required_permission="admins.manage"
    )
    method.assert_awaited_once()
    kwargs = {
        key: value.model_dump(mode="json") if hasattr(value, "model_dump") else value
        for key, value in method.await_args.kwargs.items()
    }
    assert kwargs == operation.kwargs
    if operation.status == 204:
        assert response.content == b""
    elif operation.service == "get_actions_summary":
        assert response.json() == {"items": operation.result, "total": 1}
    elif operation.service == "get_statistics":
        assert response.json() == {**operation.result, "admin_id": 7}
    elif operation.service == "cleanup_expired_sessions":
        assert response.json()["cleaned_count"] == 3
        assert response.json()["status"] == "success"
    else:
        assert response.json() == operation.result
    admin_harness.session.execute.assert_not_awaited()
    admin_harness.session.commit.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", OPERATIONS, ids=lambda item: item.service)
async def test_revoked_permission_cannot_reach_any_administrative_operation(
    admin_harness: AdminHarness, operation: Operation
) -> None:
    """Recheck RBAC on reads and writes before consulting endpoint business IO."""
    admin_harness.permission.side_effect = UnauthorizedError("Permission revoked")
    response = await admin_harness.request(operation=operation)
    assert response.status_code == 403, response.text
    assert response.json() == {"detail": "Administrator permission required"}
    getattr(admin_harness.service, operation.service).assert_not_awaited()
    admin_harness.permission.assert_awaited_once_with(
        admin_id=71, required_permission="admins.manage"
    )


# ==============================================
# DOMAIN ERRORS AND INTERNAL ERROR BOUNDARIES
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", OPERATIONS, ids=lambda item: item.service)
async def test_unexpected_service_failure_returns_a_sanitized_500(
    admin_harness: AdminHarness, operation: Operation
) -> None:
    """Unexpected failures must not expose database details in the HTTP body."""
    getattr(admin_harness.service, operation.service).side_effect = RuntimeError(
        "private-database-connection-detail"
    )
    response = await admin_harness.request(operation=operation)
    assert response.status_code == 500, response.text
    assert "private-database-connection-detail" not in response.text
    assert isinstance(response.json()["detail"], str)


DOMAIN_ERRORS = (
    ("create_admin", ConflictError, 409),
    ("create_admin", ValidationError, 422),
    ("get_admin_by_id", NotFoundError, 404),
    ("get_admin_by_username", NotFoundError, 404),
    ("get_admin_by_chat_id", NotFoundError, 404),
    ("update_admin", NotFoundError, 404),
    ("update_admin", ConflictError, 409),
    ("update_admin", ValidationError, 422),
    ("update_admin_role", NotFoundError, 404),
    ("update_admin_role", ValidationError, 422),
    ("toggle_admin_status", NotFoundError, 404),
    ("delete_admin", NotFoundError, 404),
    ("delete_admin", ValidationError, 422),
    ("get_log_by_id", NotFoundError, 404),
    ("create_session", NotFoundError, 404),
    ("create_session", ValidationError, 422),
    ("get_session_by_token", NotFoundError, 404),
    ("get_active_session", NotFoundError, 404),
    ("get_active_session", UnauthorizedError, 401),
    ("get_session_status", NotFoundError, 404),
    ("update_activity", NotFoundError, 404),
    ("deactivate_session", NotFoundError, 404),
    ("extend_session", NotFoundError, 404),
    ("extend_session", ValidationError, 422),
)


@pytest.mark.asyncio
@pytest.mark.parametrize("service_name,error_type,status_code", DOMAIN_ERRORS)
async def test_domain_errors_preserve_documented_http_status(
    admin_harness: AdminHarness,
    service_name: str,
    error_type: type[Exception],
    status_code: int,
) -> None:
    """Translate known domain failures to the intended client-facing status."""
    operation = next(item for item in OPERATIONS if item.service == service_name)
    getattr(admin_harness.service, service_name).side_effect = error_type(
        "Known failure"
    )
    response = await admin_harness.request(operation=operation)
    assert response.status_code == status_code, response.text
    assert response.json() == {"detail": "Known failure"}


# ==============================================
# REQUEST VALIDATION AND VERIFIED IDENTITY BOUNDARIES
# ==============================================


INVALID_REQUESTS = (
    ("GET", "/admins/0", None, None),
    ("GET", "/admins/username/ab", None, None),
    ("GET", "/admins/chat/0", None, None),
    ("GET", "/admins/", {"skip": -1}, None),
    ("GET", "/admins/", {"limit": 201}, None),
    ("GET", "/admins/", {"search": ""}, None),
    ("PATCH", "/admins/7/role", None, None),
    (
        "POST",
        "/admins/",
        None,
        {"chat_id": 700, "username": "has spaces", "full_name": "Valid Name"},
    ),
    ("PATCH", "/admins/7", None, {"role": "invented-role"}),
    ("POST", "/admin-logs/", None, {"admin_id": 0, "action": "view"}),
    ("POST", "/admin-logs/", None, {"admin_id": 7, "action": "invented-action"}),
    ("GET", "/admin-logs/search", None, None),
    ("GET", "/admin-logs/summary/actions", {"limit": 51}, None),
    (
        "GET",
        "/admin-logs/date-range",
        {"start_date": "not-a-date", "end_date": STAMP},
        None,
    ),
    ("GET", "/admin-logs/action/" + "a" * 51, None, None),
    ("GET", "/admin-sessions/admin/7", {"skip": -1}, None),
    ("GET", "/admin-sessions/admin/7/active", {"limit": 0}, None),
    (
        "POST",
        "/admin-sessions/",
        None,
        {"admin_id": 7, "expires_at": "2000-01-01T00:00:00"},
    ),
    (
        "PATCH",
        "/admin-sessions/extend",
        None,
        {"session_token": "   ", "expires_at": FUTURE},
    ),
    ("POST", "/admin-sessions/cleanup", {"days": 366}, None),
)


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path,params,body", INVALID_REQUESTS)
async def test_invalid_http_input_never_reaches_business_service(
    admin_harness: AdminHarness,
    method: str,
    path: str,
    params: JsonObject | None,
    body: JsonObject | None,
) -> None:
    """Reject invalid identifiers, pagination and payloads before business IO."""
    operation = Operation(method, path, "", None, {}, params=params, body=body)
    response = await admin_harness.request(operation=operation)
    assert response.status_code == 422, response.text
    assert isinstance(response.json()["detail"], list)
    for registered in OPERATIONS:
        getattr(admin_harness.service, registered.service).assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", OPERATIONS[:12], ids=lambda item: item.service)
@pytest.mark.parametrize(
    "configured,bearer,expected",
    [(False, False, 503), (True, False, 401), (True, True, 401)],
)
async def test_admin_crud_requires_trusted_oidc_before_any_database_operation(
    admin_harness: AdminHarness,
    monkeypatch: pytest.MonkeyPatch,
    operation: Operation,
    configured: bool,
    bearer: bool,
    expected: int,
) -> None:
    """Numerical or Telegram IDs cannot substitute for verified Keycloak tokens."""
    del admin_harness.app.dependency_overrides[auth.get_current_admin]
    for name, value in (
        ("OIDC_ISSUER", "https://keycloak.test/realms/local"),
        ("OIDC_AUDIENCE", "local-admin-api"),
        (
            "OIDC_JWKS_URL",
            "https://keycloak.test/realms/local/protocol/openid-connect/certs",
        ),
    ):
        monkeypatch.setattr(settings, name, value if configured else None)
    key_lookup = Mock(side_effect=AssertionError("Unexpected signing-key lookup"))
    monkeypatch.setattr(auth, "_get_jwks_client", key_lookup)
    async with AsyncClient(
        transport=ASGITransport(app=admin_harness.app), base_url="https://local.test"
    ) as client:
        response = await client.request(
            operation.method,
            "/api/v1" + operation.path,
            params={"admin_id": 7, "chat_id": 700},
            json=operation.body,
            headers={"Authorization": "Bearer forged-admin-id-7"} if bearer else {},
        )
    assert response.status_code == expected, response.text
    if expected == 401:
        assert response.headers["www-authenticate"] == "Bearer"
    admin_harness.session.execute.assert_not_awaited()
    admin_harness.permission.assert_not_awaited()
    key_lookup.assert_not_called()
    for registered in OPERATIONS:
        getattr(admin_harness.service, registered.service).assert_not_awaited()


# ==============================================
# SESSION DATETIME AND HISTORICAL RESPONSE REGRESSIONS
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("service_name", ["create_session", "extend_session"])
@pytest.mark.parametrize(
    "expires_at,normalized",
    [
        ("2099-01-01T12:00:00Z", "2099-01-01T12:00:00"),
        ("2099-01-01T14:00:00+02:00", "2099-01-01T12:00:00"),
    ],
)
async def test_session_write_normalizes_timezone_aware_input_to_utc_storage(
    admin_harness: AdminHarness,
    service_name: str,
    expires_at: str,
    normalized: str,
) -> None:
    """Accept valid ISO offsets and preserve the established naive UTC DB contract."""
    operation = next(item for item in OPERATIONS if item.service == service_name)
    assert operation.body is not None
    body = {**operation.body, "expires_at": expires_at}
    method = getattr(admin_harness.service, service_name)
    method.return_value = SESSION
    async with AsyncClient(
        transport=ASGITransport(app=admin_harness.app, raise_app_exceptions=False),
        base_url="https://local.test",
    ) as client:
        response = await client.request(
            operation.method, "/api/v1" + operation.path, json=body
        )
    assert response.status_code == operation.status, response.text
    data = next(iter(method.await_args.kwargs.values()))
    assert data.expires_at.tzinfo is None
    assert data.expires_at.isoformat() == normalized


@pytest.mark.asyncio
@pytest.mark.parametrize("service_name", ["create_session", "extend_session"])
async def test_expired_timezone_aware_input_is_validation_error_not_server_error(
    admin_harness: AdminHarness, service_name: str
) -> None:
    """Reject an expired aware timestamp with 422 before any session mutation."""
    operation = next(item for item in OPERATIONS if item.service == service_name)
    assert operation.body is not None
    body = {**operation.body, "expires_at": "2000-01-01T12:00:00Z"}
    async with AsyncClient(
        transport=ASGITransport(app=admin_harness.app, raise_app_exceptions=False),
        base_url="https://local.test",
    ) as client:
        response = await client.request(
            operation.method, "/api/v1" + operation.path, json=body
        )
    assert response.status_code == 422, response.text
    getattr(admin_harness.service, service_name).assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "service_name", ["get_session_by_token", "get_sessions_by_admin"]
)
async def test_expired_sessions_remain_readable_for_administrative_history(
    admin_harness: AdminHarness, service_name: str
) -> None:
    """Response serialization must preserve expired records needed by audit views."""
    operation = next(item for item in OPERATIONS if item.service == service_name)
    expired = {**SESSION, "expires_at": "2000-01-01T12:00:00", "is_active": False}
    result = page(item=expired) if service_name == "get_sessions_by_admin" else expired
    getattr(admin_harness.service, service_name).return_value = result
    async with AsyncClient(
        transport=ASGITransport(app=admin_harness.app, raise_app_exceptions=False),
        base_url="https://local.test",
    ) as client:
        response = await client.get(
            "/api/v1" + operation.path,
            params=operation.params,
            headers=operation.headers,
        )
    assert response.status_code == 200, response.text
    assert response.json() == result


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "params",
    [
        {"action": "invented-action"},
        {"action": "a" * 51},
        {"resource": "r" * 51},
    ],
)
async def test_admin_log_filter_validation_returns_422_before_service_access(
    admin_harness: AdminHarness, params: JsonObject
) -> None:
    """Invalid query filters are client errors, including schema enum failures."""
    response = await admin_harness.request(
        operation=Operation("GET", "/admin-logs/admin/7", "", None, {}, params=params)
    )
    assert response.status_code == 422, response.text
    assert isinstance(response.json()["detail"], list)
    admin_harness.service.get_logs_by_admin.assert_not_awaited()


@pytest.mark.asyncio
async def test_internal_log_service_schema_failure_stays_a_sanitized_server_error(
    admin_harness: AdminHarness,
) -> None:
    """Distinguish malformed client filters from an invalid internal service result."""
    with pytest.raises(SchemaValidationError) as failure:
        AdminLogFilter(action="invalid-internal-action")
    admin_harness.service.get_logs_by_admin.side_effect = failure.value
    response = await admin_harness.request(
        operation=Operation("GET", "/admin-logs/admin/7", "", None, {})
    )
    assert response.status_code == 500, response.text
    assert "invalid-internal-action" not in response.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "service_name",
    [
        "get_session_by_token",
        "get_active_session",
        "get_session_status",
        "update_activity",
        "deactivate_session",
        "extend_session",
    ],
)
@pytest.mark.parametrize("outcome", ["success", "missing", "unexpected"])
async def test_session_http_application_logs_exclude_token_prefixes(
    admin_harness: AdminHarness,
    caplog: pytest.LogCaptureFixture,
    service_name: str,
    outcome: str,
) -> None:
    """Keep credential material out of application logs on success and failures."""
    caplog.set_level(logging.INFO, logger=logger.name)
    operation = next(item for item in OPERATIONS if item.service == service_name)
    method = getattr(admin_harness.service, service_name)
    method.return_value = operation.result
    expected = operation.status
    if outcome == "missing":
        method.side_effect = NotFoundError("Missing session")
        expected = 404
    elif outcome == "unexpected":
        method.side_effect = RuntimeError("Private persistence failure")
        expected = 500
    response = await admin_harness.request(operation=operation)
    assert response.status_code == expected, response.text
    records = [record for record in caplog.records if record.name == logger.name]
    assert records
    captured = json.dumps([record.__dict__ for record in records], default=str)
    assert TOKEN[:12] not in captured


@pytest.mark.asyncio
async def test_bulk_session_deactivation_does_not_log_the_excluded_credential(
    admin_harness: AdminHarness, caplog: pytest.LogCaptureFixture
) -> None:
    """Keep the preserved-session header credential out of administrative event logs."""
    caplog.set_level(logging.INFO, logger=logger.name)
    operation = next(
        item for item in OPERATIONS if item.service == "deactivate_all_sessions"
    )
    response = await admin_harness.request(operation=operation)
    assert response.status_code == 204, response.text
    records = [record for record in caplog.records if record.name == logger.name]
    assert records
    captured = json.dumps([record.__dict__ for record in records], default=str)
    assert TOKEN[:12] not in captured


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "service_name",
    [
        "create_session",
        "get_session_by_token",
        "get_active_session",
        "get_session_status",
        "update_activity",
        "deactivate_session",
        "extend_session",
        "deactivate_all_sessions",
    ],
)
async def test_session_http_does_not_log_bound_credentials_from_storage_errors(
    admin_harness: AdminHarness,
    caplog: pytest.LogCaptureFixture,
    service_name: str,
) -> None:
    """SQLAlchemy exception strings and tracebacks can contain credential values."""
    caplog.set_level(logging.INFO, logger=logger.name)
    operation = next(item for item in OPERATIONS if item.service == service_name)
    getattr(admin_harness.service, service_name).side_effect = StatementError(
        "Session storage failed",
        "SELECT session_token FROM admin_sessions",
        {"session_token": TOKEN},
        RuntimeError("Sensitive driver failure"),
    )
    response = await admin_harness.request(operation=operation)
    assert response.status_code == 500, response.text
    assert TOKEN not in response.text
    records = [record for record in caplog.records if record.name == logger.name]
    assert records
    serialized = json.dumps([record.__dict__ for record in records], default=str)
    assert TOKEN[:12] not in caplog.text
    assert TOKEN[:12] not in serialized


# ==============================================
# HEADER-ONLY SESSION CREDENTIAL CONTRACTS
# ==============================================


SESSION_LOOKUPS = tuple(
    item for item in OPERATIONS if item.path.startswith("/admin-sessions/lookup")
)
SESSION_CREDENTIAL_OPERATIONS = (
    *SESSION_LOOKUPS,
    next(item for item in OPERATIONS if item.service == "deactivate_all_sessions"),
)


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", SESSION_LOOKUPS, ids=lambda item: item.service)
@pytest.mark.parametrize("credential", [None, "", "   ", "s" * 256])
async def test_session_lookup_rejects_missing_or_invalid_header_before_service(
    admin_harness: AdminHarness,
    operation: Operation,
    credential: str | None,
) -> None:
    """Bound credential headers without allowing malformed input to reach storage."""
    headers = {} if credential is None else {"X-Admin-Session-Token": credential}
    response = await admin_harness.request(
        operation=replace(operation, headers=headers)
    )
    assert response.status_code == 422, response.text
    getattr(admin_harness.service, operation.service).assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "operation", SESSION_CREDENTIAL_OPERATIONS, ids=lambda item: item.service
)
async def test_session_credentials_are_normalized_without_entering_request_url(
    admin_harness: AdminHarness,
    caplog: pytest.LogCaptureFixture,
    operation: Operation,
) -> None:
    """Keep credentials out of HTTP request URLs and standard HTTPX request logs."""
    caplog.set_level(logging.INFO, logger="httpx")
    assert operation.headers is not None
    headers = {name: f" {value} " for name, value in operation.headers.items()}
    method = getattr(admin_harness.service, operation.service)
    method.return_value = operation.result
    response = await admin_harness.request(
        operation=replace(operation, headers=headers)
    )
    assert response.status_code == operation.status, response.text
    assert TOKEN not in str(response.request.url)
    assert TOKEN not in response.request.url.path
    assert not response.request.url.query
    assert method.await_args.kwargs == operation.kwargs
    records = [record for record in caplog.records if record.name == "httpx"]
    assert records
    assert TOKEN not in json.dumps([record.__dict__ for record in records], default=str)


@pytest.mark.asyncio
@pytest.mark.parametrize("credential", ["", "   ", "s" * 256])
async def test_bulk_session_deactivation_rejects_invalid_preservation_header(
    admin_harness: AdminHarness, credential: str
) -> None:
    """Reject invalid preservation input instead of revoking every active session."""
    operation = SESSION_CREDENTIAL_OPERATIONS[-1]
    response = await admin_harness.request(
        operation=replace(operation, headers={"X-Preserve-Session-Token": credential})
    )
    assert response.status_code == 422, response.text
    admin_harness.service.deactivate_all_sessions.assert_not_awaited()


@pytest.mark.asyncio
async def test_bulk_session_deactivation_allows_omitting_preservation_header(
    admin_harness: AdminHarness,
) -> None:
    """Keep explicit all-session revocation available to authorized administrators."""
    operation = SESSION_CREDENTIAL_OPERATIONS[-1]
    response = await admin_harness.request(operation=replace(operation, headers={}))
    assert response.status_code == 204, response.text
    admin_harness.service.deactivate_all_sessions.assert_awaited_once_with(
        admin_id=7, except_session_token=None
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,suffix",
    [
        ("GET", ""),
        ("GET", "/active"),
        ("GET", "/status"),
        ("PATCH", "/activity"),
        ("DELETE", ""),
    ],
)
async def test_retired_session_credential_paths_do_not_resolve(
    admin_harness: AdminHarness, method: str, suffix: str
) -> None:
    """Expose no compatibility routes that could continue leaking URL credentials."""
    response = await admin_harness.request(
        operation=Operation(
            method, f"/admin-sessions/token/{TOKEN}{suffix}", "", None, {}
        )
    )
    assert response.status_code == 404, response.text
    for operation in OPERATIONS:
        getattr(admin_harness.service, operation.service).assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("query_name", ["session_token", "except_session_token"])
@pytest.mark.parametrize(
    "operation", SESSION_CREDENTIAL_OPERATIONS, ids=lambda item: item.service
)
async def test_session_credential_queries_are_rejected_without_mutation(
    admin_harness: AdminHarness, operation: Operation, query_name: str
) -> None:
    """Fail visibly for retired query callers rather than silently ignoring a token."""
    response = await admin_harness.request(
        operation=replace(operation, params={query_name: TOKEN})
    )
    assert response.status_code == 422, response.text
    assert TOKEN not in response.text
    getattr(admin_harness.service, operation.service).assert_not_awaited()


def test_admin_session_openapi_declares_credentials_only_in_headers(
    admin_harness: AdminHarness,
) -> None:
    """Publish bounded header parameters and no session credentials in URL inputs."""
    paths = admin_harness.app.openapi()["paths"]
    for path, operations in paths.items():
        if not path.startswith("/api/v1/admin-sessions"):
            continue
        assert "{session_token}" not in path
        assert "/token/" not in path
        for operation in operations.values():
            for parameter in operation.get("parameters", []):
                assert not (
                    parameter["in"] in {"path", "query"}
                    and "token" in parameter["name"].lower()
                )
    for operation in SESSION_CREDENTIAL_OPERATIONS:
        path = operation.path.replace("/admin/7/all", "/admin/{admin_id}/all")
        parameters = paths["/api/v1" + path][operation.method.lower()]["parameters"]
        assert operation.headers is not None
        header = next(iter(operation.headers))
        documented = next(item for item in parameters if item["name"] == header)
        assert documented["in"] == "header"
        assert documented["required"] is (header == "X-Admin-Session-Token")
        schema = documented["schema"]
        if "anyOf" in schema:
            schema = next(item for item in schema["anyOf"] if item["type"] == "string")
        assert schema["minLength"] == 1
        assert schema["maxLength"] == 255
