# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Exercise agent HTTP contracts using inert service and database boundaries.

These tests cover routing, validation, serialization, and error translation.
They do not establish authorization or database tenant isolation guarantees.
"""

# ==============================================
# IMPORTS
# ==============================================

from collections.abc import AsyncIterator
from dataclasses import (
    dataclass,
    field,
)
from types import ModuleType
from typing import (
    Any,
    TypeAlias,
)
from unittest.mock import (
    AsyncMock,
    Mock,
    create_autospec,
)

import pytest
from fastapi import (
    FastAPI,
    HTTPException,
)
from fastapi.routing import APIRoute
from httpx import (
    ASGITransport,
    AsyncClient,
    Response,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import (
    OwnerPrincipal,
    get_current_owner,
    get_owner_tenant_db,
)
from app.api.v1.agent import (
    agent,
    channel,
    conversation,
    message,
)
from app.core.database import get_db
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.schemas.agent import (
    AgentConfigUpdate,
    AgentCreate,
    AgentUpdate,
    ChannelCreate,
    ChannelUpdate,
    ConversationCreate,
    ConversationUpdate,
    MessageCreate,
    MessageUpdate,
)

# ==============================================
# EXPLICIT HTTP AND SERVICE CONTRACTS
# ==============================================

JsonObject: TypeAlias = dict[str, Any]
QueryParameters: TypeAlias = dict[str, Any]

AGENT_BODY: JsonObject = {"restaurant_id": 31, "name": "Order assistant"}
CHANNEL_BODY: JsonObject = {"agent_id": 7, "type": "telegram", "name": "Orders"}
CONVERSATION_BODY: JsonObject = {
    "agent_id": 7,
    "channel_id": 9,
    "user_id": "customer-41",
}
MESSAGE_BODY: JsonObject = {
    "conversation_id": 11,
    "role": "user",
    "content": "A table for two",
}
TIMESTAMPS: JsonObject = {
    "created_at": "2026-10-16T12:00:00Z",
    "updated_at": "2026-10-16T12:05:00Z",
}
RECORDS: dict[str, JsonObject] = {
    "agent": {
        **AGENT_BODY,
        **TIMESTAMPS,
        "id": 7,
        "language": "ar",
        "tone": "professional",
        "description": None,
        "is_active": True,
        "config": {},
        "ai_config": {},
    },
    "channel": {**CHANNEL_BODY, **TIMESTAMPS, "id": 9, "is_active": True, "config": {}},
    "conversation": {
        **CONVERSATION_BODY,
        **TIMESTAMPS,
        "id": 11,
        "user_name": None,
        "status": "active",
        "is_active": True,
        "context": {},
    },
    "message": {
        **MESSAGE_BODY,
        **TIMESTAMPS,
        "id": 13,
        "content_type": "text",
        "intent": None,
        "confidence": None,
        "entities": {},
        "meta_data": {},
    },
}
STATISTICS: dict[str, JsonObject] = {
    "agent": {
        "total_agents": 3,
        "active_agents": 2,
        "inactive_agents": 1,
        "language_distribution": {"ar": 2, "en": 1},
        "tone_distribution": {"professional": 3},
    },
    "channel": {
        "total_channels": 3,
        "active_channels": 2,
        "inactive_channels": 1,
        "types_summary": [{"type": "telegram", "count": 3}],
    },
    "conversation": {
        "total_conversations": 3,
        "active_conversations": 2,
        "inactive_conversations": 1,
        "status_summary": [{"status": "active", "count": 2}],
    },
    "message": {
        "total_messages": 3,
        "user_messages": 1,
        "assistant_messages": 1,
        "system_messages": 1,
        "role_summary": [{"role": "user", "count": 1}],
    },
}
MODULES: dict[str, ModuleType] = {
    "agent": agent,
    "channel": channel,
    "conversation": conversation,
    "message": message,
}


@dataclass(frozen=True)
class HttpOperation:
    """Specify a request and its expected business call independently of routing."""

    resource: str
    method: str
    path: str
    service_method: str
    arguments: JsonObject
    parameters: QueryParameters = field(default_factory=dict)
    body: Any = None
    result_kind: str = "record"
    not_found: bool = False
    invalid: bool = False
    conflict: bool = False

    @property
    def identifier(self) -> str:
        """Name each operation clearly in the test report."""
        return f"{self.method} {self.resource}{self.path}"

    @property
    def url(self) -> str:
        """Use the actual router prefix without importing the application lifespan."""
        return "/api/v1" + MODULES[self.resource].router.prefix + self.path


OPERATIONS = (
    HttpOperation(
        "agent",
        "POST",
        "/",
        "create",
        {"agent_data": AgentCreate(**AGENT_BODY)},
        body=AGENT_BODY,
        invalid=True,
        conflict=True,
    ),
    HttpOperation(
        "agent",
        "GET",
        "/7",
        "get_by_id",
        {"agent_id": 7, "include_inactive": True},
        {"include_inactive": True},
        not_found=True,
    ),
    HttpOperation(
        "agent",
        "GET",
        "/7/with-channels",
        "get_with_channels",
        {"agent_id": 7, "include_inactive": False},
        not_found=True,
    ),
    HttpOperation(
        "agent",
        "GET",
        "/restaurant/31",
        "get_by_restaurant",
        {"restaurant_id": 31, "only_active": False, "skip": 5, "limit": 10},
        {"only_active": False, "skip": 5, "limit": 10},
        result_kind="list",
    ),
    HttpOperation(
        "agent",
        "GET",
        "/status",
        "get_by_status",
        {"restaurant_id": 31, "is_active": False, "skip": 5, "limit": 10},
        {"restaurant_id": 31, "is_active": False, "skip": 5, "limit": 10},
        result_kind="list",
    ),
    HttpOperation(
        "agent",
        "GET",
        "/search",
        "search",
        {
            "query": "orders",
            "restaurant_id": None,
            "only_active": True,
            "skip": 0,
            "limit": 100,
        },
        {"query": "orders"},
        result_kind="list",
    ),
    HttpOperation(
        "agent",
        "PATCH",
        "/7",
        "update",
        {"agent_id": 7, "update_data": AgentUpdate(name="New name")},
        body={"name": "New name"},
        not_found=True,
        invalid=True,
        conflict=True,
    ),
    HttpOperation(
        "agent",
        "PATCH",
        "/7/config",
        "update_config",
        {"agent_id": 7, "config_data": AgentConfigUpdate(config={"max_items": 5})},
        body={"config": {"max_items": 5}},
        not_found=True,
    ),
    HttpOperation(
        "agent",
        "PATCH",
        "/7/toggle-status",
        "toggle_active",
        {"agent_id": 7},
        not_found=True,
    ),
    HttpOperation(
        "agent",
        "PATCH",
        "/bulk/toggle-status",
        "bulk_toggle_active",
        {"agent_ids": [7, 8], "is_active": False},
        {"agent_ids": [7, 8], "is_active": False},
        result_kind="count",
    ),
    HttpOperation(
        "agent",
        "DELETE",
        "/7",
        "delete",
        {"agent_id": 7, "permanent": True},
        {"permanent": True},
        result_kind="none",
        not_found=True,
        invalid=True,
    ),
    HttpOperation(
        "agent",
        "GET",
        "/statistics/31",
        "get_statistics",
        {"restaurant_id": 31},
        result_kind="statistics",
    ),
    HttpOperation(
        "channel",
        "POST",
        "/",
        "create",
        {"channel_data": ChannelCreate(**CHANNEL_BODY)},
        body=CHANNEL_BODY,
        not_found=True,
        invalid=True,
        conflict=True,
    ),
    HttpOperation(
        "channel",
        "GET",
        "/9",
        "get_by_id",
        {"channel_id": 9, "include_inactive": False},
        not_found=True,
    ),
    HttpOperation(
        "channel",
        "GET",
        "/agent/7",
        "get_by_agent",
        {"agent_id": 7, "only_active": False, "skip": 5, "limit": 10},
        {"only_active": False, "skip": 5, "limit": 10},
        result_kind="list",
        not_found=True,
    ),
    HttpOperation(
        "channel",
        "GET",
        "/type",
        "get_by_type",
        {"agent_id": 7, "channel_type": "telegram", "only_active": False},
        {"agent_id": 7, "channel_type": "telegram", "only_active": False},
    ),
    HttpOperation(
        "channel",
        "GET",
        "/search",
        "search",
        {
            "query": "orders",
            "agent_id": 7,
            "only_active": True,
            "skip": 0,
            "limit": 100,
        },
        {"query": "orders", "agent_id": 7},
        result_kind="list",
    ),
    HttpOperation(
        "channel",
        "PATCH",
        "/9",
        "update",
        {"channel_id": 9, "update_data": ChannelUpdate(name="New channel")},
        body={"name": "New channel"},
        not_found=True,
        invalid=True,
    ),
    HttpOperation(
        "channel",
        "PATCH",
        "/9/config",
        "update_config",
        {"channel_id": 9, "config": {"language": "en"}},
        body={"language": "en"},
        not_found=True,
    ),
    HttpOperation(
        "channel",
        "PATCH",
        "/9/toggle-status",
        "toggle_active",
        {"channel_id": 9},
        not_found=True,
    ),
    HttpOperation(
        "channel",
        "DELETE",
        "/9",
        "delete",
        {"channel_id": 9, "permanent": False},
        result_kind="none",
        not_found=True,
        invalid=True,
    ),
    HttpOperation(
        "channel",
        "DELETE",
        "/agent/7",
        "delete_by_agent",
        {"agent_id": 7, "permanent": True},
        {"permanent": True},
        result_kind="none",
        not_found=True,
    ),
    HttpOperation(
        "channel",
        "GET",
        "/statistics/7",
        "get_statistics",
        {"agent_id": 7},
        result_kind="statistics",
        not_found=True,
    ),
    HttpOperation(
        "conversation",
        "POST",
        "/",
        "create",
        {"conversation_data": ConversationCreate(**CONVERSATION_BODY)},
        body=CONVERSATION_BODY,
        not_found=True,
        invalid=True,
    ),
    HttpOperation(
        "conversation",
        "GET",
        "/11",
        "get_by_id",
        {"conversation_id": 11, "include_inactive": True},
        {"include_inactive": True},
        not_found=True,
    ),
    HttpOperation(
        "conversation",
        "GET",
        "/11/with-messages",
        "get_with_messages",
        {"conversation_id": 11, "include_inactive": False},
        not_found=True,
    ),
    HttpOperation(
        "conversation",
        "GET",
        "/user",
        "get_by_user",
        {"agent_id": 7, "user_id": "customer-41", "only_active": False},
        {"agent_id": 7, "user_id": "customer-41", "only_active": False},
    ),
    HttpOperation(
        "conversation",
        "GET",
        "/agent/7",
        "get_by_agent",
        {"agent_id": 7, "only_active": True, "skip": 0, "limit": 100},
        result_kind="list",
        not_found=True,
    ),
    HttpOperation(
        "conversation",
        "GET",
        "/status/closed",
        "get_by_status",
        {"agent_id": 7, "status": "closed", "skip": 5, "limit": 10},
        {"agent_id": 7, "skip": 5, "limit": 10},
        result_kind="list",
        invalid=True,
    ),
    HttpOperation(
        "conversation",
        "GET",
        "/search",
        "search",
        {
            "query": "orders",
            "agent_id": 7,
            "only_active": False,
            "skip": 5,
            "limit": 10,
        },
        {
            "query": "orders",
            "agent_id": 7,
            "only_active": False,
            "skip": 5,
            "limit": 10,
        },
        result_kind="list",
    ),
    HttpOperation(
        "conversation",
        "PATCH",
        "/11",
        "update",
        {"conversation_id": 11, "update_data": ConversationUpdate(status="closed")},
        body={"status": "closed"},
        not_found=True,
        invalid=True,
    ),
    HttpOperation(
        "conversation",
        "PATCH",
        "/11/context",
        "update_context",
        {"conversation_id": 11, "context": {"order_id": 21}},
        body={"order_id": 21},
        not_found=True,
    ),
    HttpOperation(
        "conversation",
        "PATCH",
        "/11/status",
        "update_status",
        {"conversation_id": 11, "status": "closed"},
        {"status": "closed"},
        not_found=True,
        invalid=True,
    ),
    HttpOperation(
        "conversation",
        "PATCH",
        "/11/toggle-status",
        "deactivate",
        {"conversation_id": 11},
        not_found=True,
    ),
    HttpOperation(
        "conversation",
        "DELETE",
        "/11",
        "delete",
        {"conversation_id": 11, "permanent": True},
        {"permanent": True},
        result_kind="none",
        not_found=True,
        invalid=True,
    ),
    HttpOperation(
        "conversation",
        "GET",
        "/statistics/7",
        "get_statistics",
        {"agent_id": 7},
        result_kind="statistics",
        not_found=True,
    ),
    HttpOperation(
        "message",
        "POST",
        "/",
        "create",
        {"message_data": MessageCreate(**MESSAGE_BODY)},
        body=MESSAGE_BODY,
        not_found=True,
        invalid=True,
    ),
    HttpOperation(
        "message",
        "POST",
        "/user",
        "create_user_message",
        {
            "conversation_id": 11,
            "content": "Hello",
            "content_type": "image",
            "intent": "greeting",
            "confidence": 0.75,
        },
        {
            "conversation_id": 11,
            "content": "Hello",
            "content_type": "image",
            "intent": "greeting",
            "confidence": 0.75,
        },
        not_found=True,
        invalid=True,
    ),
    HttpOperation(
        "message",
        "POST",
        "/assistant",
        "create_assistant_message",
        {
            "conversation_id": 11,
            "content": "Welcome",
            "content_type": "text",
            "intent": None,
            "confidence": None,
        },
        {"conversation_id": 11, "content": "Welcome"},
        not_found=True,
        invalid=True,
    ),
    HttpOperation(
        "message",
        "POST",
        "/system",
        "create_system_message",
        {
            "conversation_id": 11,
            "content": "Context",
            "intent": None,
            "confidence": None,
        },
        {"conversation_id": 11, "content": "Context"},
        not_found=True,
        invalid=True,
    ),
    HttpOperation(
        "message",
        "POST",
        "/bulk",
        "bulk_create_messages",
        {"conversation_id": 11, "messages": [{"role": "user", "content": "Hello"}]},
        {"conversation_id": 11},
        body=[{"role": "user", "content": "Hello"}],
        result_kind="bulk",
        not_found=True,
        invalid=True,
    ),
    HttpOperation(
        "message", "GET", "/13", "get_by_id", {"message_id": 13}, not_found=True
    ),
    HttpOperation(
        "message",
        "GET",
        "/conversation/11",
        "get_by_conversation",
        {"conversation_id": 11, "skip": 5, "limit": 10},
        {"skip": 5, "limit": 10},
        result_kind="list",
        not_found=True,
    ),
    HttpOperation(
        "message",
        "GET",
        "/conversation/11/role/user",
        "get_by_role",
        {"conversation_id": 11, "role": "user", "skip": 0, "limit": 100},
        result_kind="list",
        invalid=True,
    ),
    HttpOperation(
        "message",
        "GET",
        "/conversation/11/type/image",
        "get_by_content_type",
        {"conversation_id": 11, "content_type": "image", "skip": 0, "limit": 100},
        result_kind="list",
        invalid=True,
    ),
    HttpOperation(
        "message",
        "GET",
        "/conversation/11/last",
        "get_last_message",
        {"conversation_id": 11},
    ),
    HttpOperation(
        "message",
        "GET",
        "/conversation/11/first",
        "get_first_message",
        {"conversation_id": 11},
    ),
    HttpOperation(
        "message",
        "GET",
        "/search",
        "search",
        {
            "query": "table",
            "conversation_id": 11,
            "role": "user",
            "skip": 5,
            "limit": 10,
        },
        {
            "query": "table",
            "conversation_id": 11,
            "role": "user",
            "skip": 5,
            "limit": 10,
        },
        result_kind="list",
    ),
    HttpOperation(
        "message",
        "PATCH",
        "/13",
        "update",
        {"message_id": 13, "update_data": MessageUpdate(content="A table for three")},
        body={"content": "A table for three"},
        not_found=True,
        invalid=True,
    ),
    HttpOperation(
        "message",
        "DELETE",
        "/13",
        "delete",
        {"message_id": 13},
        result_kind="none",
        not_found=True,
    ),
    HttpOperation(
        "message",
        "DELETE",
        "/conversation/11",
        "delete_by_conversation",
        {"conversation_id": 11},
        result_kind="none",
        not_found=True,
    ),
    HttpOperation(
        "message",
        "DELETE",
        "/conversation/11/old",
        "delete_old_messages",
        {"conversation_id": 11, "keep_count": 25},
        {"keep_count": 25},
        result_kind="none",
        not_found=True,
    ),
    HttpOperation(
        "message",
        "GET",
        "/statistics/11",
        "get_statistics",
        {"conversation_id": 11},
        result_kind="statistics",
        not_found=True,
    ),
)


@dataclass
class AgentHarness:
    """Expose the real routers while prohibiting real storage or business effects."""

    app: FastAPI
    services: dict[str, Mock]
    factories: dict[str, Mock]
    session: AsyncMock

    async def request(self, *, operation: HttpOperation) -> Response:
        """Send a real ASGI HTTP request without starting the application lifespan."""
        async with AsyncClient(
            transport=ASGITransport(app=self.app),
            base_url="https://local.test",
        ) as client:
            return await client.request(
                operation.method,
                operation.url,
                params=operation.parameters,
                json=operation.body,
            )

    def assert_no_storage(self) -> None:
        """Verify that all storage methods remain untouched by HTTP contract tests."""
        assert self.session.mock_calls == []


@pytest.fixture(scope="module")
def api_application() -> FastAPI:
    """Assemble immutable router definitions once while isolating each test's IO."""
    app = FastAPI()
    for module in MODULES.values():
        app.include_router(module.router, prefix="/api/v1")
    return app


@pytest.fixture
def harness(
    monkeypatch: pytest.MonkeyPatch,
    api_application: FastAPI,
) -> AgentHarness:
    """Keep actual service dependencies and replace their constructors with mocks."""
    session = AsyncMock(spec=AsyncSession)
    services: dict[str, Mock] = {}
    factories: dict[str, Mock] = {}

    async def database_boundary() -> AsyncIterator[AsyncMock]:
        """Provide a session double without opening any database connection."""
        yield session

    async def owner_boundary() -> OwnerPrincipal:
        """Authenticate the contract fixture without exercising JWT or storage."""
        return OwnerPrincipal(owner_id=1)

    monkeypatch.setitem(
        api_application.dependency_overrides,
        get_owner_tenant_db,
        database_boundary,
    )
    monkeypatch.setitem(
        api_application.dependency_overrides,
        get_current_owner,
        owner_boundary,
    )
    for resource, module in MODULES.items():
        class_name = resource.title() + "Service"
        service_class = getattr(module, class_name)
        service = create_autospec(service_class, instance=True)
        factory = Mock(return_value=service)
        monkeypatch.setattr(module, class_name, factory)
        services[resource] = service
        factories[resource] = factory
    return AgentHarness(api_application, services, factories, session)


def successful_result(*, operation: HttpOperation) -> Any:
    """Provide representative serialized records, pagination, statistics, or counts."""
    record = RECORDS[operation.resource]
    if operation.result_kind == "list":
        return {
            "items": [record],
            "total": 21,
            "skip": operation.arguments["skip"],
            "limit": operation.arguments["limit"],
        }
    if operation.result_kind == "statistics":
        return STATISTICS[operation.resource]
    if operation.result_kind == "bulk":
        return [record]
    if operation.result_kind == "count":
        return 2
    if operation.result_kind == "none":
        return None
    return record


# ==============================================
# SUCCESS, SERIALIZATION, AND EXCEPTION TRANSLATION
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", OPERATIONS, ids=lambda item: item.identifier)
async def test_http_operation_forwards_validated_contract(
    harness: AgentHarness,
    operation: HttpOperation,
) -> None:
    """Every operation must dispatch correct filters and produce its declared body."""
    boundary = getattr(harness.services[operation.resource], operation.service_method)
    boundary.return_value = successful_result(operation=operation)
    response = await harness.request(operation=operation)
    expected_status = {"POST": 201, "DELETE": 204}.get(operation.method, 200)
    assert response.status_code == expected_status, response.text
    boundary.assert_awaited_once_with(**operation.arguments)
    harness.factories[operation.resource].assert_called_once_with(
        session=harness.session, owner_id=1
    )
    harness.assert_no_storage()
    if operation.result_kind == "none":
        assert response.content == b""
    elif operation.result_kind == "count":
        assert response.json() == {"updated_count": 2, "is_active": False}
    else:
        assert response.json() == successful_result(operation=operation)


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", OPERATIONS, ids=lambda item: item.identifier)
async def test_unexpected_service_failure_is_sanitized(
    harness: AgentHarness,
    operation: HttpOperation,
) -> None:
    """Internal service details must not leak through a failed HTTP response."""
    boundary = getattr(harness.services[operation.resource], operation.service_method)
    boundary.side_effect = RuntimeError("internal-service-diagnostic")
    response = await harness.request(operation=operation)
    assert response.status_code == 500, response.text
    assert isinstance(response.json()["detail"], str)
    assert "internal-service-diagnostic" not in response.text
    boundary.assert_awaited_once_with(**operation.arguments)
    harness.assert_no_storage()


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", OPERATIONS, ids=lambda item: item.identifier)
async def test_tenant_access_denial_preserves_http_status(
    harness: AgentHarness,
    operation: HttpOperation,
) -> None:
    """A storage-level tenant denial must not become a misleading server error."""
    boundary = getattr(harness.services[operation.resource], operation.service_method)
    boundary.side_effect = HTTPException(status_code=404, detail="Resource not found")
    response = await harness.request(operation=operation)
    assert response.status_code == 404, response.text
    assert response.json() == {"detail": "Resource not found"}
    boundary.assert_awaited_once_with(**operation.arguments)
    harness.assert_no_storage()


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", OPERATIONS, ids=lambda item: item.identifier)
async def test_every_agent_operation_requires_trusted_identity(
    *,
    api_application: FastAPI,
    monkeypatch: pytest.MonkeyPatch,
    operation: HttpOperation,
) -> None:
    """Knowing an owner, administrator, or Telegram ID cannot authenticate HTTP."""
    session = AsyncMock(spec=AsyncSession)

    async def database_boundary() -> AsyncIterator[AsyncMock]:
        """Fail the assertion if unauthenticated access attempts actual storage."""
        yield session

    monkeypatch.setitem(
        api_application.dependency_overrides,
        get_db,
        database_boundary,
    )
    async with AsyncClient(
        transport=ASGITransport(app=api_application),
        base_url="https://local.test",
    ) as client:
        response = await client.request(
            operation.method,
            operation.url,
            params={
                **operation.parameters,
                "owner_id": 1,
                "admin_id": 1,
                "chat_id": 425,
            },
            json=operation.body,
        )

    assert response.status_code == 401, response.text
    assert response.headers["www-authenticate"] == "Bearer"
    assert session.mock_calls == []


DOMAIN_FAILURES = tuple(
    (operation, exception_type, expected_status)
    for operation in OPERATIONS
    for applicable, exception_type, expected_status in (
        (operation.not_found, NotFoundError, 404),
        (operation.invalid, ValidationError, 422),
        (operation.conflict, ConflictError, 409),
    )
    if applicable
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("operation", "exception_type", "expected_status"),
    DOMAIN_FAILURES,
    ids=[f"{item.identifier}-{kind.__name__}" for item, kind, _ in DOMAIN_FAILURES],
)
async def test_domain_errors_preserve_intended_http_status(
    harness: AgentHarness,
    operation: HttpOperation,
    exception_type: type[Exception],
    expected_status: int,
) -> None:
    """Translate known business failures consistently without invoking real storage."""
    boundary = getattr(harness.services[operation.resource], operation.service_method)
    boundary.side_effect = exception_type(message="Expected business rejection")
    response = await harness.request(operation=operation)
    assert response.status_code == expected_status, response.text
    assert response.json() == {"detail": "Expected business rejection"}
    boundary.assert_awaited_once_with(**operation.arguments)
    harness.assert_no_storage()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("resource", "path", "parameters", "service_method"),
    [
        ("channel", "/type", {"agent_id": 7, "channel_type": "web"}, "get_by_type"),
        (
            "conversation",
            "/user",
            {"agent_id": 7, "user_id": "missing-user"},
            "get_by_user",
        ),
        ("message", "/conversation/11/last", {}, "get_last_message"),
        ("message", "/conversation/11/first", {}, "get_first_message"),
    ],
)
async def test_optional_lookup_serializes_missing_record_as_null(
    harness: AgentHarness,
    resource: str,
    path: str,
    parameters: QueryParameters,
    service_method: str,
) -> None:
    """Optional lookup contracts must distinguish an empty result from a 500 error."""
    operation = HttpOperation(resource, "GET", path, service_method, {}, parameters)
    boundary = getattr(harness.services[resource], service_method)
    boundary.return_value = None
    response = await harness.request(operation=operation)
    assert response.status_code == 200, response.text
    assert response.json() is None
    boundary.assert_awaited_once()
    harness.assert_no_storage()


# ==============================================
# REQUEST VALIDATION AND COMPLETE ROUTE INVENTORY
# ==============================================


INVALID_BODIES = (
    ("agent", "POST", "/", {**AGENT_BODY, "restaurant_id": 0}, "restaurant_id"),
    ("agent", "POST", "/", {**AGENT_BODY, "name": "   "}, "name"),
    ("agent", "POST", "/", {**AGENT_BODY, "language": "invalid"}, "language"),
    ("agent", "POST", "/", {**AGENT_BODY, "tone": "invalid"}, "tone"),
    ("agent", "PATCH", "/7", {"name": "  "}, "name"),
    ("agent", "PATCH", "/7", {"language": "invalid"}, "language"),
    ("agent", "PATCH", "/7", {"tone": "invalid"}, "tone"),
    ("channel", "POST", "/", {**CHANNEL_BODY, "agent_id": 0}, "agent_id"),
    ("channel", "POST", "/", {**CHANNEL_BODY, "type": "sms"}, "type"),
    ("channel", "POST", "/", {**CHANNEL_BODY, "name": "  "}, "name"),
    ("channel", "PATCH", "/9", {"name": "  "}, "name"),
    ("conversation", "POST", "/", {**CONVERSATION_BODY, "agent_id": 0}, "agent_id"),
    ("conversation", "POST", "/", {**CONVERSATION_BODY, "channel_id": 0}, "channel_id"),
    ("conversation", "POST", "/", {**CONVERSATION_BODY, "user_id": "  "}, "user_id"),
    ("conversation", "POST", "/", {**CONVERSATION_BODY, "status": "unknown"}, "status"),
    ("conversation", "PATCH", "/11", {"status": "unknown"}, "status"),
    ("message", "POST", "/", {**MESSAGE_BODY, "conversation_id": 0}, "conversation_id"),
    ("message", "POST", "/", {**MESSAGE_BODY, "role": "admin"}, "role"),
    ("message", "POST", "/", {**MESSAGE_BODY, "content": "  "}, "content"),
    (
        "message",
        "POST",
        "/",
        {**MESSAGE_BODY, "content_type": "binary"},
        "content_type",
    ),
    ("message", "POST", "/", {**MESSAGE_BODY, "confidence": 1.01}, "confidence"),
    ("message", "POST", "/", {**MESSAGE_BODY, "confidence": -0.01}, "confidence"),
    ("message", "PATCH", "/13", {"content": "  "}, "content"),
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("resource", "method", "path", "body", "field_name"), INVALID_BODIES
)
async def test_invalid_body_is_rejected_before_business_call(
    harness: AgentHarness,
    resource: str,
    method: str,
    path: str,
    body: JsonObject,
    field_name: str,
) -> None:
    """Enforce schema constraints and identify the rejected field over real HTTP."""
    operation = HttpOperation(resource, method, path, "", {}, body=body)
    response = await harness.request(operation=operation)
    assert response.status_code == 422, response.text
    assert any(
        error["loc"] == ["body", field_name] for error in response.json()["detail"]
    )
    assert harness.services[resource].mock_calls == []
    harness.assert_no_storage()


PAGINATED_OPERATIONS = tuple(item for item in OPERATIONS if item.result_kind == "list")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "operation", PAGINATED_OPERATIONS, ids=lambda item: item.identifier
)
@pytest.mark.parametrize(
    ("name", "value"), [("skip", -1), ("limit", 0), ("limit", 201)]
)
async def test_invalid_pagination_never_reaches_service(
    harness: AgentHarness,
    operation: HttpOperation,
    name: str,
    value: int,
) -> None:
    """Reject pagination outside advertised limits for every paginated operation."""
    invalid_operation = HttpOperation(
        operation.resource,
        operation.method,
        operation.path,
        operation.service_method,
        operation.arguments,
        {**operation.parameters, name: value},
        operation.body,
    )
    response = await harness.request(operation=invalid_operation)
    assert response.status_code == 422, response.text
    assert any(error["loc"] == ["query", name] for error in response.json()["detail"])
    assert harness.services[operation.resource].mock_calls == []
    harness.assert_no_storage()


@pytest.mark.asyncio
@pytest.mark.parametrize("resource", tuple(MODULES))
async def test_nonpositive_identifier_is_rejected(
    harness: AgentHarness,
    resource: str,
) -> None:
    """A nonpositive record identifier cannot trigger business or storage access."""
    response = await harness.request(
        operation=HttpOperation(resource, "GET", "/0", "get_by_id", {})
    )
    assert response.status_code == 422, response.text
    assert harness.services[resource].mock_calls == []
    harness.assert_no_storage()


def test_each_agent_http_operation_has_an_explicit_contract() -> None:
    """A newly registered endpoint must receive a request/response contract case."""
    actual = {
        (resource, verb, route.path_format)
        for resource, module in MODULES.items()
        for route in module.router.routes
        if isinstance(route, APIRoute)
        for verb in route.methods
    }
    expected: set[tuple[str, str, str]] = set()
    for operation in OPERATIONS:
        module = MODULES[operation.resource]
        matching_routes = [
            route
            for route in module.router.routes
            if isinstance(route, APIRoute)
            and operation.method in route.methods
            and route.path_regex.fullmatch(module.router.prefix + operation.path)
        ]
        assert matching_routes, operation.identifier
        route = matching_routes[0]
        expected.add((operation.resource, operation.method, route.path_format))
    assert actual == expected
