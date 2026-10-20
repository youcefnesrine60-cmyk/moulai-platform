# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Exercise order item HTTP operations and real tenant guards without a database."""

from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.api.auth import (
    OwnerPrincipal,
    get_current_owner,
)
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

ITEM_BODY = {
    "order_id": 91,
    "product_id": 31,
    "product_name": "Soup",
    "unit_price": 450.0,
    "quantity": 2,
    "total_price": 900.0,
}
ITEM = {**ITEM_BODY, "id": 101, "created_at": "2026-10-16T12:00:00Z"}
ITEM_LIST = {"items": [ITEM], "total": 1, "skip": 0, "limit": 100}
SUMMARY = {
    "total_items": 1,
    "total_quantity": 2,
    "subtotal": 900.0,
    "total_options_price": 0.0,
    "total_price": 900.0,
}
OWNER = OwnerPrincipal(owner_id=81)


@dataclass(frozen=True)
class OrderItemOperation:
    """Keep the HTTP request and expected protected business call together."""

    method: str
    url: str
    service_method: str
    expected: dict[str, object]
    reply: object
    scope_key: str
    scope_id: int
    body: object | None = None
    status: int = 200


OPERATIONS = (
    OrderItemOperation(
        "GET",
        "/order-items/?order_id=91",
        "get_by_order",
        {"order_id": 91, "skip": 0, "limit": 100},
        ITEM_LIST,
        "orders_id",
        91,
    ),
    OrderItemOperation(
        "GET",
        "/order-items/101",
        "get_with_options",
        {"order_item_id": 101},
        {**ITEM, "options": []},
        "order_items_id",
        101,
    ),
    OrderItemOperation(
        "POST",
        "/order-items/",
        "add_item",
        {"item_data": ITEM_BODY},
        ITEM,
        "orders_id",
        91,
        ITEM_BODY,
        201,
    ),
    OrderItemOperation(
        "PATCH",
        "/order-items/101/quantity?quantity=3",
        "update_quantity",
        {"order_item_id": 101, "quantity": 3},
        {**ITEM, "quantity": 3, "total_price": 1350.0},
        "order_items_id",
        101,
    ),
    OrderItemOperation(
        "PATCH",
        "/order-items/101/unit-price?unit_price=500",
        "update_unit_price",
        {"order_item_id": 101, "unit_price": 500.0},
        {**ITEM, "unit_price": 500.0, "total_price": 1000.0},
        "order_items_id",
        101,
    ),
    OrderItemOperation(
        "DELETE",
        "/order-items/101",
        "remove_item",
        {"order_item_id": 101},
        None,
        "order_items_id",
        101,
        status=204,
    ),
    OrderItemOperation(
        "DELETE",
        "/order-items/order/91",
        "remove_all_items",
        {"order_id": 91},
        None,
        "orders_id",
        91,
        status=204,
    ),
    OrderItemOperation(
        "GET",
        "/order-items/stats/summary?order_id=91",
        "get_item_summary",
        {"order_id": 91},
        SUMMARY,
        "orders_id",
        91,
    ),
    OrderItemOperation(
        "POST",
        "/order-items/batch",
        "add_items",
        {"items": [ITEM_BODY]},
        ITEM_LIST,
        "orders_id",
        91,
        [ITEM_BODY],
        201,
    ),
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "operation", OPERATIONS, ids=lambda case: f"{case.method}:{case.url}"
)
async def test_order_items_verify_owner_before_business_call(
    operation: OrderItemOperation,
) -> None:
    """Execute the real tenant SELECT guard before each protected operation."""
    module = api_module(name="order_item")
    service = service_double(
        dependency=module.get_order_items_service, methods=(operation.service_method,)
    )
    service.session.execute.return_value = SimpleNamespace(
        scalar_one_or_none=lambda: 11
    )
    method: AsyncMock = getattr(service, operation.service_method)
    method.return_value = operation.reply
    app = make_app(
        module=module,
        dependencies={
            module.get_order_items_service: service,
            module.get_order_item_options_service: object(),
            get_current_owner: OWNER,
        },
    )
    response = await request(
        app=app, method=operation.method, url=operation.url, body=operation.body
    )
    assert response.status_code == operation.status, response.text
    service.session.execute.assert_awaited_once()
    statement = service.session.execute.await_args.args[0]
    parameters = statement.compile().params
    assert OWNER.owner_id in parameters.values()
    assert operation.scope_id in parameters.values()
    assert "restaurants.owner_id" in str(statement)
    assert_call_fields(method=method, expected=operation.expected)
    if operation.status == 204:
        assert response.content == b""


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "operation", OPERATIONS, ids=lambda case: f"{case.method}:{case.url}"
)
async def test_order_items_hide_foreign_tenant_before_business_call(
    operation: OrderItemOperation,
) -> None:
    """A failed ownership SELECT returns 404 and never invokes the service."""
    module = api_module(name="order_item")
    service = service_double(
        dependency=module.get_order_items_service, methods=(operation.service_method,)
    )
    service.session.execute.return_value = SimpleNamespace(
        scalar_one_or_none=lambda: None
    )
    app = make_app(
        module=module,
        dependencies={
            module.get_order_items_service: service,
            module.get_order_item_options_service: object(),
            get_current_owner: OWNER,
        },
    )
    response = await request(
        app=app, method=operation.method, url=operation.url, body=operation.body
    )
    assert response.status_code == 404, response.text
    getattr(service, operation.service_method).assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "operation", OPERATIONS, ids=lambda case: f"{case.method}:{case.url}"
)
async def test_order_items_require_bearer_identity(
    operation: OrderItemOperation,
) -> None:
    """Knowing an order ID or item ID cannot substitute for a verified identity."""
    module = api_module(name="order_item")
    service = service_double(
        dependency=module.get_order_items_service, methods=(operation.service_method,)
    )
    app = make_app(
        module=module,
        dependencies={
            module.get_order_items_service: service,
            module.get_order_item_options_service: object(),
        },
    )
    response = await request(
        app=app, method=operation.method, url=operation.url, body=operation.body
    )
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    getattr(service, operation.service_method).assert_not_awaited()
    service.session.execute.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "operation", OPERATIONS, ids=lambda case: f"{case.method}:{case.url}"
)
@pytest.mark.parametrize(
    "error,status_code", [(NotFoundError, 404), (RuntimeError, 500)]
)
async def test_order_item_service_failure_status(
    operation: OrderItemOperation, error: type[Exception], status_code: int
) -> None:
    """Keep domain missing-resource failures distinct from sanitized storage errors."""
    module = api_module(name="order_item")
    service = service_double(
        dependency=module.get_order_items_service, methods=(operation.service_method,)
    )
    service.session.execute.return_value = SimpleNamespace(
        scalar_one_or_none=lambda: 11
    )
    getattr(service, operation.service_method).side_effect = error(
        "private item diagnostic"
    )
    app = make_app(
        module=module,
        dependencies={
            module.get_order_items_service: service,
            module.get_order_item_options_service: object(),
            get_current_owner: OWNER,
        },
    )
    response = await request(
        app=app, method=operation.method, url=operation.url, body=operation.body
    )
    assert response.status_code == status_code, response.text
    if status_code == 500:
        assert "private item diagnostic" not in response.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body,detail",
    [
        ([], "No items provided"),
        (
            [ITEM_BODY, {**ITEM_BODY, "order_id": 92}],
            "All items must belong to the same order",
        ),
    ],
)
async def test_order_item_batch_rejects_empty_or_mixed_orders(
    body: list[dict[str, object]], detail: str
) -> None:
    """Reject invalid batch scopes before a tenant lookup or any write."""
    module = api_module(name="order_item")
    service = service_double(
        dependency=module.get_order_items_service, methods=("add_items",)
    )
    app = make_app(
        module=module,
        dependencies={
            module.get_order_items_service: service,
            get_current_owner: OWNER,
        },
    )
    response = await request(
        app=app, method="POST", url="/order-items/batch", body=body
    )
    assert response.status_code == 400
    assert response.json()["detail"] == detail
    service.add_items.assert_not_awaited()
    service.session.execute.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    [
        "/order-items/101/quantity?quantity=0",
        "/order-items/101/unit-price?unit_price=-1",
    ],
)
async def test_order_item_invalid_prices_and_quantities(url: str) -> None:
    """Reject negative prices or zero quantities before touching the protected service."""
    module = api_module(name="order_item")
    service = service_double(
        dependency=module.get_order_items_service,
        methods=("update_quantity", "update_unit_price"),
    )
    app = make_app(
        module=module,
        dependencies={
            module.get_order_items_service: service,
            get_current_owner: OWNER,
        },
    )
    response = await request(app=app, method="PATCH", url=url)
    assert response.status_code == 422
    service.update_quantity.assert_not_awaited()
    service.update_unit_price.assert_not_awaited()
    service.session.execute.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error,status_code", [(ConflictError, 409), (ValidationError, 422)]
)
@pytest.mark.parametrize("batch", [False, True])
async def test_order_item_creation_domain_failure(
    error: type[Exception], status_code: int, batch: bool
) -> None:
    """Expose expected creation conflicts and validation failures as client errors."""
    module = api_module(name="order_item")
    method_name = "add_items" if batch else "add_item"
    service = service_double(
        dependency=module.get_order_items_service, methods=(method_name,)
    )
    service.session.execute.return_value = SimpleNamespace(
        scalar_one_or_none=lambda: 11
    )
    getattr(service, method_name).side_effect = error("Invalid item submission")
    app = make_app(
        module=module,
        dependencies={
            module.get_order_items_service: service,
            get_current_owner: OWNER,
        },
    )
    response = await request(
        app=app,
        method="POST",
        url="/order-items/batch" if batch else "/order-items/",
        body=[ITEM_BODY] if batch else ITEM_BODY,
    )
    assert response.status_code == status_code, response.text
