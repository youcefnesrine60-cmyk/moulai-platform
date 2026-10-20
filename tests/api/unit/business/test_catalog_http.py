# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Exercise catalog HTTP serialization, validation and service error contracts.

Contract fixtures explicitly provide the verified owner dependency. Separate
authorization tests exercise missing identities and real tenant-scoped SQL.
"""

from dataclasses import dataclass
from types import ModuleType
from typing import Any
from unittest.mock import (
    AsyncMock,
    NonCallableMagicMock,
)

import pytest

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

# ==============================================
# RESPONSE FIXTURES
# ==============================================

TIMESTAMP = "2026-10-16T12:00:00Z"
PRODUCT = {
    "id": 31,
    "restaurant_id": 11,
    "category_id": 21,
    "name": "Soup",
    "price": 450.0,
    "created_at": TIMESTAMP,
    "updated_at": TIMESTAMP,
}
CATEGORY = {
    "id": 21,
    "restaurant_id": 11,
    "name": "Lunch",
    "created_at": TIMESTAMP,
    "updated_at": TIMESTAMP,
}
GROUP = {
    "id": 41,
    "product_id": 31,
    "name": "Extras",
    "created_at": TIMESTAMP,
    "updated_at": TIMESTAMP,
}
OPTION = {
    "id": 51,
    "group_id": 41,
    "name": "Cheese",
    "extra_price": 50.0,
    "created_at": TIMESTAMP,
    "updated_at": TIMESTAMP,
}
DEPENDENCIES = {
    "products": "get_product_service",
    "categories": "get_category_service",
    "option_group": "get_option_groups_service",
    "product_option": "get_product_option_service",
}


def catalog_service(
    *, module: ModuleType, methods: tuple[str, ...]
) -> NonCallableMagicMock:
    """Resolve the router's actual service contract before constructing its double."""
    module_name = module.__name__.rsplit(".", 1)[-1]
    return service_double(
        dependency=getattr(module, DEPENDENCIES[module_name]), methods=methods
    )


@dataclass(frozen=True)
class CatalogOperation:
    """Describe a public HTTP contract and the expected validated service call."""

    module: str
    method: str
    url: str
    service_method: str
    expected: dict[str, object]
    reply: object
    body: object | None = None
    status: int = 200


OPERATIONS = (
    CatalogOperation(
        "products", "GET", "/products/31", "get_by_id", {"product_id": 31}, PRODUCT
    ),
    CatalogOperation(
        "products",
        "GET",
        "/products/31/details",
        "get_with_details",
        {"product_id": 31},
        PRODUCT,
    ),
    CatalogOperation(
        "products",
        "POST",
        "/products/?restaurant_id=11",
        "create_product",
        {
            "restaurant_id": 11,
            "product_data": {"category_id": 21, "name": "Soup", "price": 450.0},
        },
        PRODUCT,
        {"category_id": 21, "name": "Soup", "price": 450.0},
        201,
    ),
    CatalogOperation(
        "products",
        "PATCH",
        "/products/31",
        "update_product",
        {"product_id": 31, "update_data": {"price": 500.0}},
        {**PRODUCT, "price": 500.0},
        {"price": 500.0},
    ),
    CatalogOperation(
        "products",
        "PATCH",
        "/products/31/availability",
        "update_availability",
        {"product_id": 31, "availability_data": {"is_available": False}},
        {**PRODUCT, "is_available": False},
        {"is_available": False},
    ),
    CatalogOperation(
        "products",
        "POST",
        "/products/31/enable",
        "enable_product",
        {"product_id": 31},
        PRODUCT,
    ),
    CatalogOperation(
        "products",
        "POST",
        "/products/31/disable",
        "disable_product",
        {"product_id": 31},
        {**PRODUCT, "is_available": False},
    ),
    CatalogOperation(
        "products",
        "DELETE",
        "/products/31",
        "delete_product",
        {"product_id": 31},
        None,
        status=204,
    ),
    CatalogOperation(
        "categories",
        "GET",
        "/categories/21",
        "get_by_id",
        {"category_id": 21},
        CATEGORY,
    ),
    CatalogOperation(
        "categories",
        "POST",
        "/categories/?restaurant_id=11",
        "create_category",
        {"restaurant_id": 11, "category_data": {"name": "Lunch"}},
        CATEGORY,
        {"name": "Lunch"},
        201,
    ),
    CatalogOperation(
        "categories",
        "PATCH",
        "/categories/21",
        "update_category",
        {"category_id": 21, "update_data": {"name": "Dinner"}},
        {**CATEGORY, "name": "Dinner"},
        {"name": "Dinner"},
    ),
    CatalogOperation(
        "categories",
        "DELETE",
        "/categories/21",
        "delete_category",
        {"category_id": 21},
        None,
        status=204,
    ),
    CatalogOperation(
        "option_group",
        "GET",
        "/option-groups/41",
        "get_with_options",
        {"group_id": 41},
        {**GROUP, "options": []},
    ),
    CatalogOperation(
        "option_group",
        "POST",
        "/option-groups/?product_id=31",
        "create_group",
        {"group_data": {"product_id": 31, "name": "Extras"}},
        GROUP,
        {"product_id": 999, "name": "Extras"},
        201,
    ),
    CatalogOperation(
        "option_group",
        "PATCH",
        "/option-groups/41",
        "update_group",
        {"group_id": 41, "update_data": {"name": "Sauce"}},
        {**GROUP, "name": "Sauce"},
        {"name": "Sauce"},
    ),
    CatalogOperation(
        "option_group",
        "PATCH",
        "/option-groups/41/sort-order?sort_order=2",
        "update_sort_order",
        {"group_id": 41, "sort_order": 2},
        {**GROUP, "sort_order": 2},
    ),
    CatalogOperation(
        "option_group",
        "PATCH",
        "/option-groups/41/required?required=true",
        "update_required",
        {"group_id": 41, "required": True},
        {**GROUP, "required": True},
    ),
    CatalogOperation(
        "option_group",
        "PATCH",
        "/option-groups/41/multiple-choice?multiple_choice=true",
        "update_multiple_choice",
        {"group_id": 41, "multiple_choice": True},
        {**GROUP, "multiple_choice": True},
    ),
    CatalogOperation(
        "option_group",
        "DELETE",
        "/option-groups/41",
        "delete_group",
        {"group_id": 41},
        None,
        status=204,
    ),
    CatalogOperation(
        "product_option",
        "GET",
        "/product-options/51",
        "get_by_id",
        {"option_id": 51},
        OPTION,
    ),
    CatalogOperation(
        "product_option",
        "PATCH",
        "/product-options/51",
        "update_option",
        {"option_id": 51, "update_data": {"name": "Olives"}},
        {**OPTION, "name": "Olives"},
        {"name": "Olives"},
    ),
    CatalogOperation(
        "product_option",
        "PATCH",
        "/product-options/51/availability",
        "update_availability",
        {"option_id": 51, "availability_data": {"is_available": False}},
        {**OPTION, "is_available": False},
        {"is_available": False},
    ),
    CatalogOperation(
        "product_option",
        "PATCH",
        "/product-options/51/price?extra_price=75",
        "update_price",
        {"option_id": 51, "extra_price": 75.0},
        {**OPTION, "extra_price": 75.0},
    ),
    CatalogOperation(
        "product_option",
        "PATCH",
        "/product-options/51/sort-order?sort_order=2",
        "update_sort_order",
        {"option_id": 51, "sort_order": 2},
        {**OPTION, "sort_order": 2},
    ),
    CatalogOperation(
        "product_option",
        "DELETE",
        "/product-options/51",
        "delete_option",
        {"option_id": 51},
        None,
        status=204,
    ),
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "operation", OPERATIONS, ids=lambda case: f"{case.method}:{case.url}"
)
async def test_catalog_http_operations(operation: CatalogOperation) -> None:
    """Validate HTTP status, response projection and exact business call context."""
    module = api_module(name=operation.module)
    service = catalog_service(module=module, methods=(operation.service_method,))
    method: AsyncMock = getattr(service, operation.service_method)
    method.return_value = operation.reply
    app = make_app(
        module=module,
        dependencies={getattr(module, DEPENDENCIES[operation.module]): service},
    )
    response = await request(
        app=app, method=operation.method, url=operation.url, body=operation.body
    )
    assert response.status_code == operation.status, response.text
    assert_call_fields(method=method, expected=operation.expected)
    if operation.status == 204:
        assert response.content == b""
    else:
        assert isinstance(operation.reply, dict)
        for field in (
            "id",
            "name",
            "restaurant_id",
            "product_id",
            "group_id",
            "price",
            "extra_price",
            "is_available",
            "required",
            "multiple_choice",
            "sort_order",
        ):
            if field in operation.reply:
                assert response.json()[field] == operation.reply[field]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "operation", OPERATIONS, ids=lambda case: f"{case.method}:{case.url}"
)
async def test_catalog_unexpected_service_errors_are_sanitized(
    operation: CatalogOperation,
) -> None:
    """Do not expose raw operational exceptions in an HTTP error response."""
    module = api_module(name=operation.module)
    service = catalog_service(module=module, methods=(operation.service_method,))
    getattr(service, operation.service_method).side_effect = RuntimeError(
        "private database diagnostic"
    )
    app = make_app(
        module=module,
        dependencies={getattr(module, DEPENDENCIES[operation.module]): service},
    )
    response = await request(
        app=app, method=operation.method, url=operation.url, body=operation.body
    )
    assert response.status_code == 500
    assert "private database diagnostic" not in response.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "operation",
    [
        case
        for case in OPERATIONS
        if not (
            case.module == "categories" and case.service_method == "create_category"
        )
    ],
    ids=lambda case: f"{case.method}:{case.url}",
)
async def test_catalog_not_found_translation(operation: CatalogOperation) -> None:
    """Translate domain missing-resource errors consistently for CRUD operations."""
    module = api_module(name=operation.module)
    service = catalog_service(module=module, methods=(operation.service_method,))
    getattr(service, operation.service_method).side_effect = NotFoundError(
        message="Missing catalog resource"
    )
    app = make_app(
        module=module,
        dependencies={getattr(module, DEPENDENCIES[operation.module]): service},
    )
    response = await request(
        app=app, method=operation.method, url=operation.url, body=operation.body
    )
    assert response.status_code == 404, response.text
    assert response.json()["detail"] == "Missing catalog resource"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "operation",
    [
        case
        for case in OPERATIONS
        if case.method == "POST"
        and case.status == 201
        or case.method == "PATCH"
        and case.url.count("/") == 2
    ],
    ids=lambda case: f"{case.method}:{case.url}",
)
@pytest.mark.parametrize(
    "exception,status_code", [(ConflictError, 409), (ValidationError, 422)]
)
async def test_catalog_domain_write_failures(
    operation: CatalogOperation, exception: type[Exception], status_code: int
) -> None:
    """Report expected conflicts and domain validation failures without a 500."""
    module = api_module(name=operation.module)
    service = catalog_service(module=module, methods=(operation.service_method,))
    getattr(service, operation.service_method).side_effect = exception(
        "Invalid catalog change"
    )
    app = make_app(
        module=module,
        dependencies={getattr(module, DEPENDENCIES[operation.module]): service},
    )
    response = await request(
        app=app, method=operation.method, url=operation.url, body=operation.body
    )
    assert response.status_code == status_code, response.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "module_name,url,body",
    [
        (
            "products",
            "/products/?restaurant_id=11",
            {"category_id": 21, "name": "Soup", "price": -1},
        ),
        ("categories", "/categories/?restaurant_id=0", {"name": "Lunch"}),
        ("option_group", "/option-groups/?product_id=31", {"name": "Extras"}),
        (
            "product_option",
            "/product-options/?group_id=41",
            {"name": "Cheese", "extra_price": -1},
        ),
    ],
)
async def test_invalid_catalog_requests_do_not_reach_business_layer(
    module_name: str, url: str, body: dict[str, Any]
) -> None:
    """Reject malformed IDs or prices before invoking write operations."""
    module = api_module(name=module_name)
    method_name = {
        "products": "create_product",
        "categories": "create_category",
        "option_group": "create_group",
        "product_option": "create_option",
    }[module_name]
    service = catalog_service(module=module, methods=(method_name,))
    app = make_app(
        module=module,
        dependencies={getattr(module, DEPENDENCIES[module_name]): service},
    )
    response = await request(app=app, method="POST", url=url, body=body)
    assert response.status_code == 422
    getattr(service, method_name).assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bulk", [False, True], ids=["single-query-group", "bulk-body-group"]
)
async def test_product_option_creation_keeps_group_context_outside_option_payload(
    bulk: bool,
) -> None:
    """Preserve the advertised payload while forwarding its validated group ID."""
    module = api_module(name="product_option")
    service = catalog_service(module=module, methods=("create_option",))
    service.create_option.return_value = OPTION
    app = make_app(
        module=module, dependencies={module.get_product_option_service: service}
    )
    option = {"name": "Cheese", "extra_price": 50.0}
    body = {"group_id": 41, "options": [option]} if bulk else option
    url = "/product-options/bulk" if bulk else "/product-options/?group_id=41"
    response = await request(app=app, method="POST", url=url, body=body)
    assert response.status_code == 201, response.text
    assert_call_fields(
        method=service.create_option, expected={"group_id": 41, "option_data": option}
    )
    result = response.json()["items"][0] if bulk else response.json()
    assert result["group_id"] == 41


# ==============================================
# LIST FILTERS, PAGINATION AND AGGREGATES
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "module_name,item,query,method_name,expected",
    [
        (
            "products",
            PRODUCT,
            "search=Soup&restaurant_id=11",
            "search",
            {"query": "Soup", "restaurant_id": 11, "skip": 2, "limit": 5},
        ),
        (
            "products",
            PRODUCT,
            "category_id=21&only_available=false",
            "get_by_category",
            {"category_id": 21, "skip": 2, "limit": 5, "only_available": False},
        ),
        (
            "products",
            PRODUCT,
            "restaurant_id=11",
            "get_by_restaurant",
            {"restaurant_id": 11, "skip": 2, "limit": 5, "only_available": True},
        ),
        (
            "categories",
            CATEGORY,
            "search=Lunch&restaurant_id=11",
            "search",
            {"query": "Lunch", "restaurant_id": 11, "skip": 2, "limit": 5},
        ),
        (
            "categories",
            CATEGORY,
            "restaurant_id=11",
            "get_by_restaurant",
            {"restaurant_id": 11, "skip": 2, "limit": 5},
        ),
        (
            "option_group",
            GROUP,
            "search=Extras&product_id=31",
            "search",
            {"query": "Extras", "product_id": 31, "skip": 2, "limit": 5},
        ),
        (
            "option_group",
            GROUP,
            "product_id=31",
            "get_by_product",
            {"product_id": 31, "skip": 2, "limit": 5},
        ),
        (
            "product_option",
            OPTION,
            "search=Cheese&group_id=41&only_available=false",
            "search",
            {
                "query": "Cheese",
                "group_id": 41,
                "skip": 2,
                "limit": 5,
                "only_available": False,
            },
        ),
        (
            "product_option",
            OPTION,
            "group_id=41",
            "get_by_group",
            {"group_id": 41, "skip": 2, "limit": 5, "only_available": True},
        ),
    ],
)
async def test_catalog_list_filters_preserve_service_context(
    module_name: str,
    item: dict[str, object],
    query: str,
    method_name: str,
    expected: dict[str, object],
) -> None:
    """Filter and pagination values survive HTTP parsing without losing scope IDs."""
    module = api_module(name=module_name)
    service = catalog_service(module=module, methods=(method_name,))
    reply = {"items": [item], "total": 1, "skip": 2, "limit": 5}
    getattr(service, method_name).return_value = (
        [item] if module_name == "option_group" else reply
    )
    if module_name == "option_group":
        service.count_by_product.return_value = 1
    app = make_app(
        module=module,
        dependencies={getattr(module, DEPENDENCIES[module_name]): service},
    )
    response = await request(
        app=app, method="GET", url=f"{module.router.prefix}/?{query}&skip=2&limit=5"
    )
    assert response.status_code == 200, response.text
    assert response.json()["items"][0]["id"] == item["id"]
    assert response.json()["skip"] == 2
    assert response.json()["limit"] == 5
    assert_call_fields(method=getattr(service, method_name), expected=expected)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "module_name,item",
    [
        ("products", PRODUCT),
        ("categories", CATEGORY),
        ("option_group", GROUP),
        ("product_option", OPTION),
    ],
)
@pytest.mark.parametrize("only_available", [True, False])
async def test_catalog_unfiltered_pagination_and_availability(
    module_name: str, item: dict[str, object], only_available: bool
) -> None:
    """Build list envelopes and repository filters for otherwise unfiltered requests."""
    module = api_module(name=module_name)
    service = catalog_service(module=module, methods=())
    service.repo.get_all.return_value = [item]
    service.repo.count.return_value = 8
    app = make_app(
        module=module,
        dependencies={getattr(module, DEPENDENCIES[module_name]): service},
    )
    response = await request(
        app=app,
        method="GET",
        url=f"{module.router.prefix}/?skip=2&limit=5&only_available={str(only_available).lower()}",
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert (payload["total"], payload["skip"], payload["limit"]) == (8, 2, 5)
    assert payload["items"][0]["id"] == item["id"]
    ordering = "name" if module_name == "products" else "sort_order"
    expected: dict[str, object] = {"skip": 2, "limit": 5, "order_by": ordering}
    if module_name in {"products", "product_option"}:
        expected["filters"] = {"is_available": True} if only_available else {}
        service.repo.count.assert_awaited_once_with(filters=expected["filters"])
    else:
        service.repo.count.assert_awaited_once_with()
    assert_call_fields(method=service.repo.get_all, expected=expected)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "module_name,url,item,service_method,expected",
    [
        (
            "products",
            "/products/restaurant/11?only_available=false",
            PRODUCT,
            "get_by_restaurant",
            {"restaurant_id": 11, "skip": 0, "limit": 100, "only_available": False},
        ),
        (
            "products",
            "/products/category/21",
            PRODUCT,
            "get_by_category",
            {"category_id": 21, "skip": 0, "limit": 100, "only_available": True},
        ),
        (
            "categories",
            "/categories/restaurant/11",
            CATEGORY,
            "get_by_restaurant",
            {"restaurant_id": 11, "skip": 0, "limit": 100},
        ),
        (
            "product_option",
            "/product-options/group/41",
            OPTION,
            "get_by_group",
            {"group_id": 41, "skip": 0, "limit": 100, "only_available": True},
        ),
    ],
)
@pytest.mark.parametrize("failing", [False, True])
async def test_catalog_related_lists(
    module_name: str,
    url: str,
    item: dict[str, object],
    service_method: str,
    expected: dict[str, object],
    failing: bool,
) -> None:
    """Related resources retain their parent context and sanitize list failures."""
    module = api_module(name=module_name)
    service = catalog_service(module=module, methods=(service_method,))
    method = getattr(service, service_method)
    method.return_value = {"items": [item], "total": 1, "skip": 0, "limit": 100}
    if failing:
        method.side_effect = RuntimeError("private list failure")
    app = make_app(
        module=module,
        dependencies={getattr(module, DEPENDENCIES[module_name]): service},
    )
    response = await request(app=app, method="GET", url=url)
    assert response.status_code == (500 if failing else 200)
    assert "private list failure" not in response.text
    assert_call_fields(method=method, expected=expected)


@pytest.mark.asyncio
@pytest.mark.parametrize("required", [True, False])
async def test_product_option_groups_required_filter(required: bool) -> None:
    """Use the required-only query when requested instead of ordinary pagination."""
    module = api_module(name="option_group")
    service = catalog_service(
        module=module,
        methods=("get_required_by_product", "get_by_product", "count_by_product"),
    )
    service.get_required_by_product.return_value = [GROUP]
    service.get_by_product.return_value = [GROUP]
    service.count_by_product.return_value = 3
    app = make_app(
        module=module, dependencies={module.get_option_groups_service: service}
    )
    response = await request(
        app=app,
        method="GET",
        url=f"/option-groups/product/31?only_required={str(required).lower()}",
    )
    assert response.status_code == 200
    assert response.json()["total"] == (1 if required else 3)
    if required:
        service.get_required_by_product.assert_awaited_once_with(product_id=31)
        service.get_by_product.assert_not_awaited()
    else:
        service.get_by_product.assert_awaited_once_with(
            product_id=31, skip=0, limit=100
        )
        service.get_required_by_product.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "module_name,url,method_name,expected",
    [
        (
            "categories",
            "/categories/reorder?restaurant_id=11&category_order=21&category_order=22",
            "reorder_categories",
            {"restaurant_id": 11, "category_order": [21, 22]},
        ),
        (
            "option_group",
            "/option-groups/reorder?product_id=31&group_order=41&group_order=42",
            "reorder_groups",
            {"product_id": 31, "group_order": [41, 42]},
        ),
        (
            "product_option",
            "/product-options/reorder?group_id=41&option_order=51&option_order=52",
            "reorder_options",
            {"group_id": 41, "option_order": [51, 52]},
        ),
    ],
)
@pytest.mark.parametrize(
    "failure,status_code",
    [(None, 204), (NotFoundError, 404), (ValidationError, 422), (RuntimeError, 500)],
)
async def test_catalog_reordering(
    module_name: str,
    url: str,
    method_name: str,
    expected: dict[str, object],
    failure: type[Exception] | None,
    status_code: int,
) -> None:
    """Preserve repeated query IDs and report reordering failures at the HTTP boundary."""
    module = api_module(name=module_name)
    service = catalog_service(module=module, methods=(method_name,))
    method = getattr(service, method_name)
    method.return_value = None
    if failure:
        method.side_effect = failure("Unable to reorder")
    app = make_app(
        module=module,
        dependencies={getattr(module, DEPENDENCIES[module_name]): service},
    )
    response = await request(app=app, method="POST", url=url)
    assert response.status_code == status_code, response.text
    assert_call_fields(method=method, expected=expected)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "module_name,url,method_name,expected",
    [
        (
            "option_group",
            "/option-groups/product/31",
            "delete_by_product",
            {"product_id": 31},
        ),
        (
            "product_option",
            "/product-options/group/41",
            "delete_by_group",
            {"group_id": 41},
        ),
    ],
)
@pytest.mark.parametrize(
    "failure,status_code", [(None, 204), (NotFoundError, 404), (RuntimeError, 500)]
)
async def test_catalog_parent_deletion(
    module_name: str,
    url: str,
    method_name: str,
    expected: dict[str, object],
    failure: type[Exception] | None,
    status_code: int,
) -> None:
    """Delete child collections with a single explicit parent identifier."""
    module = api_module(name=module_name)
    service = catalog_service(module=module, methods=(method_name,))
    method = getattr(service, method_name)
    method.return_value = None
    if failure:
        method.side_effect = failure("Unable to delete children")
    app = make_app(
        module=module,
        dependencies={getattr(module, DEPENDENCIES[module_name]): service},
    )
    response = await request(app=app, method="DELETE", url=url)
    assert response.status_code == status_code, response.text
    assert_call_fields(method=method, expected=expected)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "module_name,url,method_name,expected,summary",
    [
        (
            "products",
            "/products/stats/summary?restaurant_id=11",
            "get_product_summary",
            {"restaurant_id": 11},
            {
                "total_products": 2,
                "available_products": 1,
                "unavailable_products": 1,
                "total_price": 900.0,
                "avg_price": 450.0,
                "min_price": 400.0,
                "max_price": 500.0,
            },
        ),
        (
            "categories",
            "/categories/stats/summary?restaurant_id=11",
            "get_category_summary",
            {"restaurant_id": 11},
            {
                "total_categories": 2,
                "categories_with_products": 1,
                "empty_categories": 1,
                "total_products": 2,
                "avg_products_per_category": 1.0,
            },
        ),
        (
            "option_group",
            "/option-groups/product/31/summary",
            "get_option_group_summary",
            {"product_id": 31},
            {
                "product_id": 31,
                "total_groups": 2,
                "required_groups": 1,
                "optional_groups": 1,
                "total_options": 2,
            },
        ),
        (
            "product_option",
            "/product-options/group/41/summary",
            "get_option_summary",
            {"group_id": 41},
            {
                "group_id": 41,
                "total_options": 2,
                "available_options": 1,
                "unavailable_options": 1,
                "total_extra_price": 100.0,
                "avg_extra_price": 50.0,
                "min_extra_price": 25.0,
                "max_extra_price": 75.0,
            },
        ),
    ],
)
@pytest.mark.parametrize("failing", [False, True])
async def test_catalog_summaries(
    module_name: str,
    url: str,
    method_name: str,
    expected: dict[str, object],
    summary: dict[str, object],
    failing: bool,
) -> None:
    """Return modeled aggregates without shadowing the static summary routes."""
    module = api_module(name=module_name)
    service = catalog_service(module=module, methods=(method_name,))
    method = getattr(service, method_name)
    method.return_value = summary
    if failing:
        method.side_effect = RuntimeError("private aggregate failure")
    dependencies = {getattr(module, DEPENDENCIES[module_name]): service}
    if module_name == "categories":
        dependencies[module.get_product_service] = object()
    app = make_app(module=module, dependencies=dependencies)
    response = await request(app=app, method="GET", url=url)
    assert response.status_code == (500 if failing else 200), response.text
    if not failing:
        assert response.json() == summary
    assert_call_fields(method=method, expected=expected)
