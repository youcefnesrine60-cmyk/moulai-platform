# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Verify order HTTP contracts with real ownership guards and inert storage."""

# ==============================================
# IMPORTS
# ==============================================

from collections.abc import AsyncIterator
from dataclasses import (
    dataclass,
    field,
)
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
from fastapi import FastAPI
from httpx import (
    ASGITransport,
    AsyncClient,
    Response,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import auth
from app.api.v1 import orders
from app.core.database import get_db
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.schemas.order import (
    OrderCreate,
    OrderResponse,
    OrderStatusUpdate,
    OrderUpdate,
)

# ==============================================
# EXPLICIT REQUEST AND RESPONSE CONTRACTS
# ==============================================

JsonObject: TypeAlias = dict[str, Any]
OWNER = auth.OwnerPrincipal(owner_id=17)
CREATE_BODY: JsonObject = {
    "restaurant_id": 31,
    "order_type": "takeaway",
    "customer_name": "Test customer",
    "items": [
        {
            "product_id": 41,
            "product_name": "Soup",
            "unit_price": 200,
            "quantity": 2,
            "total_price": 400,
        }
    ],
}
ORDER = OrderResponse(
    id=21,
    restaurant_id=31,
    order_number="ORD-0021",
    order_type="takeaway",
    customer_name="Test customer",
    subtotal_amount=400,
    total_amount=400,
    created_at="2026-10-16T12:00:00Z",
    updated_at="2026-10-16T12:05:00Z",
)
SUMMARY: JsonObject = {
    "total_orders": 4,
    "pending_orders": 1,
    "confirmed_orders": 0,
    "preparing_orders": 1,
    "ready_orders": 0,
    "delivering_orders": 0,
    "delivered_orders": 0,
    "completed_orders": 1,
    "cancelled_orders": 1,
    "total_revenue": 400.0,
    "avg_order_value": 400.0,
}


@dataclass(frozen=True)
class OrderOperation:
    """Declare an HTTP request and the business method it must invoke."""

    method: str
    path: str
    service_method: str
    arguments: JsonObject
    parameters: JsonObject = field(default_factory=dict)
    body: Any = None
    result_kind: str = "record"
    restaurant_guard: bool = False
    not_found: bool = True
    invalid: bool = True
    conflict: bool = False

    @property
    def identifier(self) -> str:
        """Expose route and filter differences in the test report."""
        return f"{self.method} {self.path} {self.service_method}"


OPERATIONS = (
    OrderOperation(
        "GET",
        "/",
        "get_by_restaurant",
        {"restaurant_id": 31, "skip": 5, "limit": 10},
        {"restaurant_id": 31, "skip": 5, "limit": 10},
        result_kind="list",
        restaurant_guard=True,
        not_found=False,
    ),
    OrderOperation(
        "GET",
        "/",
        "get_by_status",
        {"restaurant_id": 31, "status": "pending", "skip": 0, "limit": 100},
        {"restaurant_id": 31, "status": "pending"},
        result_kind="list",
        restaurant_guard=True,
        not_found=False,
    ),
    OrderOperation(
        "GET",
        "/21",
        "get_with_details",
        {"order_id": 21},
        result_kind="details",
        invalid=False,
    ),
    OrderOperation(
        "POST",
        "/",
        "create_order",
        {"order_data": OrderCreate(**CREATE_BODY)},
        body=CREATE_BODY,
        restaurant_guard=True,
        conflict=True,
    ),
    OrderOperation(
        "PATCH",
        "/21",
        "update_order",
        {"order_id": 21, "update_data": OrderUpdate(customer_note="No salt")},
        body={"customer_note": "No salt"},
    ),
    OrderOperation(
        "PATCH",
        "/21/status",
        "update_order_status",
        {
            "order_id": 21,
            "status_data": OrderStatusUpdate(status="confirmed", employee_id=51),
        },
        body={"status": "confirmed", "employee_id": 51},
    ),
    OrderOperation(
        "POST",
        "/21/complete",
        "complete_order",
        {"order_id": 21, "employee_id": 51, "note": "Served"},
        {"employee_id": 51, "note": "Served"},
    ),
    OrderOperation(
        "POST",
        "/21/cancel",
        "cancel_order",
        {"order_id": 21, "employee_id": None, "reason": "Customer requested"},
        {"reason": "Customer requested"},
    ),
    OrderOperation(
        "POST",
        "/21/paid",
        "mark_as_paid",
        {"order_id": 21, "restaurant_id": 31, "payment_id": 61},
        {"payment_id": 61},
    ),
    OrderOperation(
        "DELETE",
        "/21",
        "delete_order",
        {"order_id": 21, "permanent": True},
        {"permanent": True},
        result_kind="none",
    ),
    OrderOperation(
        "GET",
        "/stats/summary",
        "get_order_summary",
        {"restaurant_id": 31},
        {"restaurant_id": 31},
        result_kind="summary",
        restaurant_guard=True,
        not_found=False,
        invalid=False,
    ),
)


@dataclass
class OrderHarness:
    """Hold fresh mocks behind a shared immutable router assembly."""

    app: FastAPI
    service: Mock
    items: Mock
    session: AsyncMock
    restaurant_guard: AsyncMock
    order_guard: AsyncMock

    async def request(self, *, operation: OrderOperation) -> Response:
        """Exercise FastAPI validation and serialization over in-process HTTP."""
        async with AsyncClient(
            transport=ASGITransport(app=self.app), base_url="https://local.test"
        ) as client:
            return await client.request(
                operation.method,
                "/api/v1/orders" + operation.path,
                params=operation.parameters,
                json=operation.body,
            )


@pytest.fixture(scope="module")
def order_application() -> FastAPI:
    """Build the real order router once without application startup effects."""
    app = FastAPI()
    app.include_router(orders.router, prefix="/api/v1")
    return app


@pytest.fixture
def order_harness(
    monkeypatch: pytest.MonkeyPatch, order_application: FastAPI
) -> OrderHarness:
    """Explicitly trust one test owner while recording ownership and service calls."""
    session = AsyncMock(spec=AsyncSession, name="isolated_order_session")
    service = create_autospec(orders.OrderService, instance=True)
    service.session = session
    items = create_autospec(orders.OrderItemsService, instance=True)
    items.session = session
    items.get_by_order.return_value = []
    monkeypatch.setattr(orders, "OrderService", Mock(return_value=service))
    monkeypatch.setattr(orders, "OrderItemsService", Mock(return_value=items))
    restaurant_guard = AsyncMock(return_value=None)
    order_guard = AsyncMock(return_value=31)
    monkeypatch.setattr(orders, "require_owned_restaurant", restaurant_guard)
    monkeypatch.setattr(orders, "require_owned_order", order_guard)

    async def database_boundary() -> AsyncIterator[AsyncMock]:
        """Provide a session double without opening storage."""
        yield session

    async def trusted_owner() -> auth.OwnerPrincipal:
        """Override completed identity verification only for HTTP contract tests."""
        return OWNER

    monkeypatch.setitem(
        order_application.dependency_overrides, get_db, database_boundary
    )
    monkeypatch.setitem(
        order_application.dependency_overrides, auth.get_current_owner, trusted_owner
    )
    return OrderHarness(
        order_application, service, items, session, restaurant_guard, order_guard
    )


def operation_result(*, operation: OrderOperation) -> Any:
    """Return a representative application response for each response family."""
    if operation.result_kind == "list":
        return {
            "items": [ORDER],
            "total": 21,
            "skip": operation.arguments["skip"],
            "limit": operation.arguments["limit"],
        }
    if operation.result_kind == "summary":
        return SUMMARY
    if operation.result_kind == "none":
        return None
    return ORDER


# ==============================================
# AUTHORIZED HTTP CONTRACTS AND BUSINESS FAILURES
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", OPERATIONS, ids=lambda item: item.identifier)
async def test_order_http_success_preserves_tenant_and_business_arguments(
    order_harness: OrderHarness, operation: OrderOperation
) -> None:
    """Forward validated filters, bodies, and authoritative restaurant identity."""
    boundary = getattr(order_harness.service, operation.service_method)
    boundary.return_value = operation_result(operation=operation)
    response = await order_harness.request(operation=operation)
    expected_status = (
        204
        if operation.method == "DELETE"
        else 201 if operation.service_method == "create_order" else 200
    )
    assert response.status_code == expected_status, response.text
    boundary.assert_awaited_once_with(**operation.arguments)
    if operation.restaurant_guard:
        order_harness.restaurant_guard.assert_awaited_once_with(
            restaurant_id=31, owner=OWNER, session=order_harness.session
        )
        order_harness.order_guard.assert_not_awaited()
    else:
        order_harness.order_guard.assert_awaited_once_with(
            order_id=21, owner=OWNER, session=order_harness.session
        )
        order_harness.restaurant_guard.assert_not_awaited()
    if operation.result_kind == "none":
        assert response.content == b""
    elif operation.result_kind == "list":
        assert response.json() == {
            "items": [ORDER.model_dump(mode="json")],
            "total": 21,
            "skip": operation.arguments["skip"],
            "limit": operation.arguments["limit"],
        }
    elif operation.result_kind == "summary":
        assert response.json() == SUMMARY
    elif operation.result_kind == "details":
        assert response.json() == {
            **ORDER.model_dump(mode="json"),
            "items": [],
            "payments": [],
            "status_history": [],
        }
        order_harness.items.get_by_order.assert_awaited_once_with(order_id=21)
    else:
        assert response.json() == ORDER.model_dump(mode="json")
    assert order_harness.session.mock_calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", OPERATIONS, ids=lambda item: item.identifier)
async def test_order_internal_failure_returns_sanitized_500(
    order_harness: OrderHarness, operation: OrderOperation
) -> None:
    """Every service failure must preserve the HTTP error boundary."""
    boundary = getattr(order_harness.service, operation.service_method)
    boundary.side_effect = RuntimeError("internal-order-diagnostic")
    response = await order_harness.request(operation=operation)
    assert response.status_code == 500, response.text
    assert "internal-order-diagnostic" not in response.text
    boundary.assert_awaited_once_with(**operation.arguments)
    assert order_harness.session.mock_calls == []


DOMAIN_ERRORS = tuple(
    (operation, kind, expected)
    for operation in OPERATIONS
    for applies, kind, expected in (
        (operation.not_found, NotFoundError, 404),
        (
            operation.invalid,
            ValidationError,
            400 if operation.result_kind == "list" else 422,
        ),
        (operation.conflict, ConflictError, 409),
    )
    if applies
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("operation", "kind", "expected_status"),
    DOMAIN_ERRORS,
    ids=[f"{item.identifier}-{kind.__name__}" for item, kind, _ in DOMAIN_ERRORS],
)
async def test_order_domain_errors_have_stable_http_status(
    order_harness: OrderHarness,
    operation: OrderOperation,
    kind: type[Exception],
    expected_status: int,
) -> None:
    """Translate known domain failures without losing their intended semantics."""
    boundary = getattr(order_harness.service, operation.service_method)
    boundary.side_effect = kind(message="Order action rejected")
    response = await order_harness.request(operation=operation)
    assert response.status_code == expected_status, response.text
    assert response.json() == {"detail": "Order action rejected"}
    assert order_harness.session.mock_calls == []


# ==============================================
# REAL OWNERSHIP GUARDS BEFORE BUSINESS OPERATIONS
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", OPERATIONS, ids=lambda item: item.identifier)
async def test_missing_owned_record_is_404_before_order_service(
    monkeypatch: pytest.MonkeyPatch,
    order_harness: OrderHarness,
    operation: OrderOperation,
) -> None:
    """Execute real ownership guards against an inert empty tenant-scoped query."""
    monkeypatch.setattr(
        orders, "require_owned_restaurant", auth.require_owned_restaurant
    )
    monkeypatch.setattr(orders, "require_owned_order", auth.require_owned_order)
    result = Mock()
    result.scalar_one_or_none.return_value = None
    order_harness.session.execute.return_value = result
    response = await order_harness.request(operation=operation)
    assert response.status_code == 404, response.text
    assert response.json() == {
        "detail": (
            "Restaurant not found" if operation.restaurant_guard else "Order not found"
        )
    }
    order_harness.session.execute.assert_awaited_once()
    statement = order_harness.session.execute.await_args.args[0]
    query_values = statement.compile().params
    assert OWNER.owner_id in query_values.values()
    assert (31 if operation.restaurant_guard else 21) in query_values.values()
    assert order_harness.service.mock_calls == []
    assert order_harness.items.mock_calls == []
    order_harness.session.commit.assert_not_awaited()
    order_harness.session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_order_listing_requires_explicit_restaurant(
    order_harness: OrderHarness,
) -> None:
    """An authenticated owner cannot obtain an unscoped cross-restaurant listing."""
    response = await order_harness.request(operation=OrderOperation("GET", "/", "", {}))
    assert response.status_code == 400, response.text
    order_harness.restaurant_guard.assert_not_awaited()
    order_harness.order_guard.assert_not_awaited()
    assert order_harness.service.mock_calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path", "parameters", "body", "location"),
    [
        ("GET", "/", {"restaurant_id": 31, "limit": 201}, None, ["query", "limit"]),
        ("GET", "/", {"restaurant_id": 31, "skip": -1}, None, ["query", "skip"]),
        ("GET", "/", {"restaurant_id": 0}, None, ["query", "restaurant_id"]),
        ("GET", "/0", {}, None, ["path", "order_id"]),
        (
            "POST",
            "/",
            {},
            {**CREATE_BODY, "restaurant_id": 0},
            ["body", "restaurant_id"],
        ),
        (
            "POST",
            "/",
            {},
            {**CREATE_BODY, "order_type": "invalid"},
            ["body", "order_type"],
        ),
        (
            "POST",
            "/",
            {},
            {**CREATE_BODY, "total_amount": -1},
            ["body", "total_amount"],
        ),
        ("PATCH", "/21/status", {}, {"status": "invalid"}, ["body", "status"]),
        ("POST", "/21/paid", {"payment_id": 0}, None, ["query", "payment_id"]),
        ("POST", "/21/paid", {}, None, ["query", "payment_id"]),
        ("POST", "/21/complete", {"employee_id": 0}, None, ["query", "employee_id"]),
        ("POST", "/21/cancel", {"reason": "x" * 501}, None, ["query", "reason"]),
    ],
)
async def test_invalid_order_request_never_reaches_tenant_or_business_boundary(
    order_harness: OrderHarness,
    method: str,
    path: str,
    parameters: JsonObject,
    body: Any,
    location: list[str],
) -> None:
    """Reject malformed identifiers, order status, totals, and query limits early."""
    response = await order_harness.request(
        operation=OrderOperation(method, path, "", {}, parameters, body)
    )
    assert response.status_code == 422, response.text
    assert any(error["loc"] == location for error in response.json()["detail"])
    order_harness.restaurant_guard.assert_not_awaited()
    order_harness.order_guard.assert_not_awaited()
    assert order_harness.service.mock_calls == []
    assert order_harness.session.mock_calls == []
