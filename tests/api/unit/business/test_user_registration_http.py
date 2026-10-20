# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Test administrator-gated global user and registration HTTP contracts offline."""

from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import (
    AsyncMock,
    NonCallableMagicMock,
)

import pytest
from fastapi import FastAPI

from app.core.config import settings
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from tests.api.unit.business._support import (
    api_module,
    assert_call_fields,
    make_app,
    request,
    service_double,
)

TIMESTAMP = "2026-10-16T12:00:00Z"
USER = {
    "id": 61,
    "chat_id": 7001,
    "customer_name": "Test Customer",
    "consent": False,
    "created_at": TIMESTAMP,
    "updated_at": TIMESTAMP,
}
REGISTRATION_BODY = {
    "chat_id": 7001,
    "full_name": "Test Owner",
    "owner_phone": "0555123456",
    "restaurant_name": "Test Kitchen",
    "restaurant_type": "Pizza",
    "restaurant_phone": "0555987654",
}
REGISTRATION = {
    **REGISTRATION_BODY,
    "id": 71,
    "status": "pending",
    "created_at": TIMESTAMP,
    "updated_at": TIMESTAMP,
}


@dataclass(frozen=True)
class ProfileOperation:
    """Capture one HTTP operation and its expected application service arguments."""

    module: str
    method: str
    url: str
    service_method: str
    expected: dict[str, object]
    reply: object
    body: object | None = None
    status: int = 200


OPERATIONS = (
    ProfileOperation("user", "GET", "/users/61", "get_by_id", {"user_id": 61}, USER),
    ProfileOperation(
        "user", "GET", "/users/chat/7001", "get_by_chat_id", {"chat_id": 7001}, USER
    ),
    ProfileOperation(
        "user",
        "POST",
        "/users/",
        "create_user",
        {"user_data": {"chat_id": 7001, "customer_name": "Test Customer"}},
        USER,
        {"chat_id": 7001, "customer_name": "Test Customer"},
        201,
    ),
    ProfileOperation(
        "user",
        "PATCH",
        "/users/61",
        "update_user",
        {"chat_id": 7001, "update_data": {"customer_name": "Updated Customer"}},
        {**USER, "customer_name": "Updated Customer"},
        {"customer_name": "Updated Customer"},
    ),
    ProfileOperation(
        "user",
        "PATCH",
        "/users/chat/7001/consent",
        "update_consent",
        {"chat_id": 7001, "consent_data": {"consent": True}},
        {**USER, "consent": True},
        {"consent": True},
    ),
    ProfileOperation(
        "user",
        "DELETE",
        "/users/61",
        "delete_user",
        {"chat_id": 7001},
        None,
        status=204,
    ),
    ProfileOperation(
        "registration_request",
        "GET",
        "/registration-requests/71",
        "get_by_id",
        {"request_id": 71},
        REGISTRATION,
    ),
    ProfileOperation(
        "registration_request",
        "GET",
        "/registration-requests/chat/7001",
        "get_by_chat_id",
        {"chat_id": 7001},
        REGISTRATION,
    ),
    ProfileOperation(
        "registration_request",
        "POST",
        "/registration-requests/",
        "create",
        {"request_data": REGISTRATION_BODY},
        REGISTRATION,
        REGISTRATION_BODY,
        201,
    ),
    ProfileOperation(
        "registration_request",
        "PATCH",
        "/registration-requests/71",
        "update",
        {"request_id": 71, "update_data": {"restaurant_name": "New Kitchen"}},
        {**REGISTRATION, "restaurant_name": "New Kitchen"},
        {"restaurant_name": "New Kitchen"},
    ),
    ProfileOperation(
        "registration_request",
        "PATCH",
        "/registration-requests/71/status?owner_id=81",
        "approve",
        {"request_id": 71, "owner_id": 81},
        {**REGISTRATION, "status": "approved", "owner_id": 81},
        {"status": "approved"},
    ),
    ProfileOperation(
        "registration_request",
        "PATCH",
        "/registration-requests/71/status",
        "reject",
        {"request_id": 71},
        {**REGISTRATION, "status": "rejected"},
        {"status": "rejected"},
    ),
    ProfileOperation(
        "registration_request",
        "POST",
        "/registration-requests/71/approve?owner_id=81",
        "approve",
        {"request_id": 71, "owner_id": 81},
        {**REGISTRATION, "status": "approved", "owner_id": 81},
    ),
    ProfileOperation(
        "registration_request",
        "POST",
        "/registration-requests/71/reject",
        "reject",
        {"request_id": 71},
        {**REGISTRATION, "status": "rejected"},
    ),
    ProfileOperation(
        "registration_request",
        "DELETE",
        "/registration-requests/71",
        "delete",
        {"request_id": 71},
        None,
        status=204,
    ),
)


def profile_service(
    *, module_name: str, methods: tuple[str, ...]
) -> NonCallableMagicMock:
    """Create a signature-checked double for the selected profile dependency."""
    module = api_module(name=module_name)
    dependency = (
        module.get_user_service
        if module_name == "user"
        else module.get_registration_request_service
    )
    return service_double(dependency=dependency, methods=methods)


def profile_app(*, module_name: str, service: NonCallableMagicMock) -> FastAPI:
    """Replace business IO and grant administrator permission in this fixture only."""
    module = api_module(name=module_name)
    dependency = (
        module.get_user_service
        if module_name == "user"
        else module.get_registration_request_service
    )
    dependencies = {dependency: service}
    if module_name in {"registration_request", "user"}:
        dependencies[module.router.dependencies[0].dependency] = object()
    return make_app(module=module, dependencies=dependencies)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "operation", OPERATIONS, ids=lambda case: f"{case.method}:{case.url}"
)
@pytest.mark.parametrize("failing", [False, True])
async def test_profile_and_registration_http_contracts(
    operation: ProfileOperation, failing: bool
) -> None:
    """Validate service arguments, statuses, response filtering and sanitized errors."""
    service = profile_service(
        module_name=operation.module,
        methods=tuple({operation.service_method, "get_by_id"}),
    )
    service.get_by_id.return_value = (
        SimpleNamespace(**USER) if operation.module == "user" else REGISTRATION
    )
    method: AsyncMock = getattr(service, operation.service_method)
    method.return_value = (
        SimpleNamespace(**operation.reply)
        if operation.service_method == "update_consent"
        and isinstance(operation.reply, dict)
        else operation.reply
    )
    if failing:
        method.side_effect = RuntimeError("private identity storage diagnostic")
    app = profile_app(module_name=operation.module, service=service)
    response = await request(
        app=app, method=operation.method, url=operation.url, body=operation.body
    )
    assert response.status_code == (500 if failing else operation.status), response.text
    assert "private identity storage diagnostic" not in response.text
    assert_call_fields(method=method, expected=operation.expected)
    if not failing:
        if operation.status == 204:
            assert response.content == b""
        else:
            assert isinstance(operation.reply, dict)
            if operation.service_method == "update_consent":
                assert response.json()["chat_id"] == 7001
                assert response.json()["has_consent"] is True
            else:
                assert response.json()["id"] == operation.reply["id"]
            if "status" in operation.reply:
                assert response.json()["status"] == operation.reply["status"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "operation",
    [
        case
        for case in OPERATIONS
        if case.service_method not in {"create", "create_user"}
    ],
    ids=lambda case: f"{case.method}:{case.url}",
)
async def test_missing_profile_or_registration(operation: ProfileOperation) -> None:
    """Return missing-resource responses instead of leaking storage failures."""
    service = profile_service(
        module_name=operation.module,
        methods=tuple({operation.service_method, "get_by_id"}),
    )
    service.get_by_id.return_value = SimpleNamespace(**USER)
    getattr(service, operation.service_method).side_effect = NotFoundError(
        "Missing requested identity"
    )
    app = profile_app(module_name=operation.module, service=service)
    response = await request(
        app=app, method=operation.method, url=operation.url, body=operation.body
    )
    assert response.status_code == 404, response.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "module_name,url,method_name,body",
    [
        ("user", "/users/", "create_user", {"chat_id": 7001}),
        (
            "registration_request",
            "/registration-requests/",
            "create",
            REGISTRATION_BODY,
        ),
    ],
)
@pytest.mark.parametrize(
    "exception,status_code", [(ConflictError, 409), (ValidationError, 422)]
)
async def test_profile_creation_rejects_domain_errors(
    module_name: str,
    url: str,
    method_name: str,
    body: dict[str, object],
    exception: type[Exception],
    status_code: int,
) -> None:
    """Domain conflicts and invalid submissions have an explicit client error status."""
    service = profile_service(module_name=module_name, methods=(method_name,))
    getattr(service, method_name).side_effect = exception("Invalid profile submission")
    app = profile_app(module_name=module_name, service=service)
    response = await request(app=app, method="POST", url=url, body=body)
    assert response.status_code == status_code, response.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query,method_name,expected",
    [
        ("search=Test", "search_by_name", {"name": "Test", "skip": 2, "limit": 5}),
        (
            "has_consent=false",
            "get_by_consent",
            {"has_consent": False, "skip": 2, "limit": 5},
        ),
        (
            "",
            "repo",
            {"skip": 2, "limit": 5, "order_by": "created_at", "descending": True},
        ),
    ],
)
async def test_user_list_filters(
    query: str, method_name: str, expected: dict[str, object]
) -> None:
    """Serialize paged users and send consent/name filters to their correct methods."""
    service = profile_service(
        module_name="user", methods=("search_by_name", "get_by_consent")
    )
    method = (
        service.repo.get_all if method_name == "repo" else getattr(service, method_name)
    )
    method.return_value = [USER]
    service.repo.count.return_value = 9
    app = profile_app(module_name="user", service=service)
    response = await request(
        app=app, method="GET", url=f"/users/?{query}&skip=2&limit=5"
    )
    assert response.status_code == 200, response.text
    assert response.json()["items"][0]["chat_id"] == 7001
    assert response.json()["total"] == (9 if method_name == "repo" else 1)
    assert_call_fields(method=method, expected=expected)


@pytest.mark.asyncio
@pytest.mark.parametrize("consent", [True, False])
async def test_user_consent_response(consent: bool) -> None:
    """Return a boolean consent state with the requested chat identifier."""
    service = profile_service(module_name="user", methods=("has_consent",))
    service.has_consent.return_value = consent
    response = await request(
        app=profile_app(module_name="user", service=service),
        method="GET",
        url="/users/chat/7001/consent",
    )
    assert response.status_code == 200
    assert response.json()["has_consent"] is consent
    assert response.json()["chat_id"] == 7001
    service.has_consent.assert_awaited_once_with(chat_id=7001)


@pytest.mark.asyncio
async def test_user_search_uses_validated_pagination() -> None:
    """Pass a typed search payload and preserve its list envelope."""
    service = profile_service(module_name="user", methods=("search",))
    service.search.return_value = {"items": [USER], "total": 1, "skip": 2, "limit": 5}
    payload = {"query": "Customer", "skip": 2, "limit": 5}
    response = await request(
        app=profile_app(module_name="user", service=service),
        method="POST",
        url="/users/search",
        body=payload,
    )
    assert response.status_code == 200
    assert response.json()["skip"] == 2
    assert_call_fields(method=service.search, expected={"search_params": payload})


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "module_name,url",
    [("user", "/users/0"), ("registration_request", "/registration-requests/0")],
)
async def test_invalid_profile_id_does_not_call_service(
    module_name: str, url: str
) -> None:
    """Reject nonpositive path identifiers at HTTP validation."""
    service = profile_service(module_name=module_name, methods=("get_by_id",))
    response = await request(
        app=profile_app(module_name=module_name, service=service), method="GET", url=url
    )
    assert response.status_code == 422
    service.get_by_id.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query,method_name,expected",
    [
        ("chat_id=7001", "get_by_chat_id", {"chat_id": 7001}),
        ("search=Kitchen", "search", {"query": "Kitchen", "skip": 2, "limit": 5}),
        (
            "status=pending",
            "get_by_status",
            {"status": "pending", "skip": 2, "limit": 5},
        ),
        ("", "get_all", {"skip": 2, "limit": 5}),
    ],
)
async def test_registration_list_filters(
    query: str, method_name: str, expected: dict[str, object]
) -> None:
    """Keep registration filtering and returned pagination consistent."""
    service = profile_service(
        module_name="registration_request",
        methods=(
            "get_by_chat_id",
            "search",
            "get_by_status",
            "get_all",
            "count_by_status",
        ),
    )
    method = getattr(service, method_name)
    method.return_value = (
        REGISTRATION if method_name == "get_by_chat_id" else [REGISTRATION]
    )
    service.count_by_status.return_value = 7
    response = await request(
        app=profile_app(module_name="registration_request", service=service),
        method="GET",
        url=f"/registration-requests/?{query}&skip=2&limit=5",
    )
    assert response.status_code == 200, response.text
    assert response.json()["items"][0]["id"] == 71
    assert response.json()["total"] == (7 if method_name == "get_by_status" else 1)
    assert_call_fields(method=method, expected=expected)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure,status_code", [(ValidationError, 400), (RuntimeError, 500)]
)
@pytest.mark.parametrize("query", ["", "status=pending"])
async def test_registration_list_error_status_is_not_shadowed_by_query(
    failure: type[Exception], status_code: int, query: str
) -> None:
    """A status filter must not replace the imported HTTP status constants."""
    method_name = "get_by_status" if query else "get_all"
    service = profile_service(
        module_name="registration_request", methods=(method_name, "count_by_status")
    )
    getattr(service, method_name).side_effect = failure(
        "private registration diagnostic"
    )
    response = await request(
        app=profile_app(module_name="registration_request", service=service),
        method="GET",
        url=f"/registration-requests/?{query}",
    )
    assert response.status_code == status_code, response.text
    if status_code == 500:
        assert "private registration diagnostic" not in response.text


@pytest.mark.asyncio
async def test_registration_empty_chat_filter_returns_empty_list() -> None:
    """A nonexistent chat produces an empty filtered list and a 404 single lookup."""
    service = profile_service(
        module_name="registration_request", methods=("get_by_chat_id",)
    )
    service.get_by_chat_id.return_value = None
    app = profile_app(module_name="registration_request", service=service)
    response = await request(
        app=app, method="GET", url="/registration-requests/?chat_id=7001"
    )
    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total"] == 0
    response = await request(
        app=app, method="GET", url="/registration-requests/chat/7001"
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_profile_summary_routes() -> None:
    """Exercise static user and registration summary URLs through HTTP routing."""
    users = profile_service(module_name="user", methods=("get_user_stats",))
    summary = {
        "total_users": 4,
        "users_with_consent": 2,
        "users_without_consent": 2,
        "users_with_name": 3,
        "users_with_phone": 1,
        "consent_rate": 50.0,
        "profile_completion_rate": 25.0,
    }
    users.get_user_stats.return_value = summary
    response = await request(
        app=profile_app(module_name="user", service=users),
        method="GET",
        url="/users/stats/summary",
    )
    assert response.status_code == 200
    assert response.json() == summary
    registrations = profile_service(
        module_name="registration_request",
        methods=("get_all", "count_pending", "count_by_status"),
    )
    registrations.get_all.return_value = [REGISTRATION, REGISTRATION]
    registrations.count_pending.return_value = 1
    registrations.count_by_status.side_effect = [1, 0]
    response = await request(
        app=profile_app(module_name="registration_request", service=registrations),
        method="GET",
        url="/registration-requests/stats/summary",
    )
    assert response.status_code == 200
    assert response.json() == {"total": 2, "pending": 1, "approved": 1, "rejected": 0}


@pytest.mark.asyncio
async def test_registration_fails_closed_without_trusted_oidc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An admin ID or chat ID cannot grant access when Keycloak is not configured."""
    module = api_module(name="registration_request")
    service = profile_service(module_name="registration_request", methods=("get_all",))
    monkeypatch.setattr(settings, "OIDC_ISSUER", None)
    monkeypatch.setattr(settings, "OIDC_AUDIENCE", None)
    monkeypatch.setattr(settings, "OIDC_JWKS_URL", None)
    app = make_app(
        module=module, dependencies={module.get_registration_request_service: service}
    )
    response = await request(
        app=app, method="GET", url="/registration-requests/?admin_id=1&chat_id=7001"
    )
    assert response.status_code == 503
    service.get_all.assert_not_awaited()
