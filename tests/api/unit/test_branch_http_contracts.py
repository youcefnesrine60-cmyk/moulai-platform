# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Exercise standalone branch HTTP contracts without database or network IO.

Authorized contract fixtures supply an explicit owner principal. Separate
security tests retain the real identity dependency and execute scoped SQL.
"""

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

from app.api.v1 import branches
from app.api.auth import (
    OwnerPrincipal,
    get_current_owner,
    get_owner_tenant_db,
)
from app.core.exceptions import (
    BranchLimitExceededError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)
from app.schemas.branch import (
    BranchCreate,
    BranchResponse,
    BranchStatusUpdate,
    BranchUpdate,
)

# ==============================================
# REPRESENTATIVE RECORDS AND REQUESTS
# ==============================================

JsonObject: TypeAlias = dict[str, Any]
CREATE_BODY: JsonObject = {"name": "Central", "wilaya": "Alger"}
BRANCH = BranchResponse(
    id=21,
    restaurant_id=31,
    name="Central",
    wilaya="Alger",
    created_at="2026-10-16T12:00:00Z",
    updated_at="2026-10-16T12:05:00Z",
)
SUMMARY: JsonObject = {
    "total_branches": 3,
    "active_branches": 2,
    "inactive_branches": 1,
    "total_cost": 300.0,
    "branches_per_wilaya": {"Alger": 2, "Oran": 1},
}


@dataclass(frozen=True)
class BranchOperation:
    """Describe one documented branch HTTP operation and service boundary."""

    method: str
    path: str
    boundary: str
    arguments: JsonObject
    parameters: JsonObject = field(default_factory=dict)
    body: JsonObject | None = None
    response_kind: str = "record"
    not_found: bool = True
    invalid: bool = False
    conflict: bool = False

    @property
    def identifier(self) -> str:
        """Identify the route and selected filtering path in Pytest reports."""
        return f"{self.method} {self.path} {self.boundary}"


OPERATIONS = (
    BranchOperation(
        "GET",
        "/",
        "search",
        {"query": "Central", "restaurant_id": 31, "skip": 5, "limit": 10},
        {
            "search": "Central",
            "restaurant_id": 31,
            "wilaya": "Oran",
            "skip": 5,
            "limit": 10,
        },
        response_kind="list",
    ),
    BranchOperation(
        "GET",
        "/",
        "get_by_restaurant",
        {"restaurant_id": 31, "skip": 5, "limit": 10, "only_active": False},
        {"restaurant_id": 31, "skip": 5, "limit": 10, "only_active": False},
        response_kind="list",
    ),
    BranchOperation("GET", "/21", "get_by_id", {"branch_id": 21}),
    BranchOperation(
        "POST",
        "/",
        "create_branch",
        {"restaurant_id": 31, "branch_data": BranchCreate(**CREATE_BODY)},
        {"restaurant_id": 31},
        CREATE_BODY,
        not_found=False,
        invalid=True,
        conflict=True,
    ),
    BranchOperation(
        "PATCH",
        "/21",
        "update_branch",
        {"branch_id": 21, "update_data": BranchUpdate(name="Central")},
        body={"name": "Central"},
        invalid=True,
        conflict=True,
    ),
    BranchOperation(
        "PATCH",
        "/21/status",
        "update_branch_status",
        {"branch_id": 21, "status_data": BranchStatusUpdate(is_active=False)},
        body={"is_active": False},
    ),
    BranchOperation("POST", "/21/activate", "activate_branch", {"branch_id": 21}),
    BranchOperation("POST", "/21/deactivate", "deactivate_branch", {"branch_id": 21}),
    BranchOperation(
        "DELETE",
        "/21",
        "delete_branch",
        {"branch_id": 21, "permanent": True},
        {"permanent": True},
        response_kind="empty",
        invalid=True,
    ),
    BranchOperation(
        "GET",
        "/stats/summary",
        "get_branch_summary",
        {"restaurant_id": 31},
        {"restaurant_id": 31},
        response_kind="summary",
    ),
    BranchOperation(
        "GET",
        "/restaurant/31",
        "get_by_restaurant",
        {"restaurant_id": 31, "skip": 0, "limit": 100, "only_active": True},
        response_kind="list",
        not_found=False,
    ),
)


@dataclass
class BranchHarness:
    """Hold service and session doubles behind real HTTP validation."""

    app: FastAPI
    service: Mock
    repository: Mock
    session: AsyncMock

    async def request(
        self,
        *,
        method: str,
        path: str,
        parameters: JsonObject | None = None,
        body: JsonObject | None = None,
    ) -> Response:
        """Send an in-process HTTP request without the deployed lifespan."""
        async with AsyncClient(
            transport=ASGITransport(app=self.app), base_url="https://local.test"
        ) as client:
            return await client.request(
                method, "/api/v1/branches" + path, params=parameters, json=body
            )


@pytest.fixture(scope="module")
def branch_application() -> FastAPI:
    """Assemble only the real standalone router without operational startup."""
    application = FastAPI()
    application.include_router(branches.router, prefix="/api/v1")
    return application


@pytest.fixture
def branch_harness(
    monkeypatch: pytest.MonkeyPatch,
    branch_application: FastAPI,
) -> BranchHarness:
    """Replace storage and business execution while retaining service construction."""
    session = AsyncMock(spec=AsyncSession)
    service = create_autospec(branches.BranchService, instance=True)
    repository = Mock(
        get_by_wilaya=AsyncMock(return_value=[BRANCH]),
        count_by_wilaya=AsyncMock(return_value=3),
        get_all=AsyncMock(return_value=[BRANCH]),
        count=AsyncMock(return_value=3),
    )
    service.repo = repository
    monkeypatch.setattr(branches, "BranchService", Mock(return_value=service))

    async def storage_boundary() -> AsyncIterator[AsyncMock]:
        """Provide an inert ORM session without a live database connection."""
        yield session

    monkeypatch.setitem(
        branch_application.dependency_overrides, get_owner_tenant_db, storage_boundary
    )
    monkeypatch.setitem(
        branch_application.dependency_overrides,
        get_current_owner,
        lambda: OwnerPrincipal(owner_id=7),
    )
    return BranchHarness(branch_application, service, repository, session)


def operation_result(*, operation: BranchOperation) -> Any:
    """Supply records matching the actual response model of each operation."""
    if operation.response_kind == "empty":
        return None
    if operation.response_kind == "summary":
        return SUMMARY
    if operation.response_kind == "list":
        return {
            "items": [BRANCH],
            "total": 3,
            "skip": operation.arguments["skip"],
            "limit": operation.arguments["limit"],
        }
    return BRANCH


# ==============================================
# HTTP SUCCESS AND SERVICE ERROR CONTRACTS
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", OPERATIONS, ids=lambda item: item.identifier)
async def test_branch_success_preserves_business_arguments(
    branch_harness: BranchHarness,
    operation: BranchOperation,
) -> None:
    """Validate route status, serialization, filters, and explicit service arguments."""
    boundary = getattr(branch_harness.service, operation.boundary)
    boundary.return_value = operation_result(operation=operation)
    response = await branch_harness.request(
        method=operation.method,
        path=operation.path,
        parameters=operation.parameters,
        body=operation.body,
    )
    assert response.status_code == (
        204
        if operation.method == "DELETE"
        else 201 if operation.method == "POST" and operation.path == "/" else 200
    ), response.text
    boundary.assert_awaited_once_with(**operation.arguments)
    if operation.response_kind == "empty":
        assert response.content == b""
    elif operation.response_kind == "list":
        assert response.json() == {
            "items": [BRANCH.model_dump(mode="json")],
            "total": 3,
            "skip": operation.arguments["skip"],
            "limit": operation.arguments["limit"],
        }
    else:
        assert response.json() == (
            SUMMARY
            if operation.response_kind == "summary"
            else BRANCH.model_dump(mode="json")
        )
    assert branch_harness.session.mock_calls == []


DOMAIN_CASES = tuple(
    (operation, error_type, expected)
    for operation in OPERATIONS
    for applies, error_type, expected in (
        (operation.not_found, NotFoundError, 404),
        (operation.invalid, ValidationError, 422),
        (operation.conflict, ConflictError, 409),
        (True, RuntimeError, 500),
    )
    if applies
)


@pytest.mark.asyncio
@pytest.mark.parametrize(("operation", "error_type", "expected_status"), DOMAIN_CASES)
async def test_branch_service_errors_keep_documented_http_status(
    branch_harness: BranchHarness,
    operation: BranchOperation,
    error_type: type[Exception],
    expected_status: int,
) -> None:
    """Map known domain errors and sanitize unanticipated internal failures."""
    boundary = getattr(branch_harness.service, operation.boundary)
    boundary.side_effect = (
        RuntimeError("private-branch-diagnostic")
        if error_type is RuntimeError
        else error_type(message="Branch action rejected")
    )
    response = await branch_harness.request(
        method=operation.method,
        path=operation.path,
        parameters=operation.parameters,
        body=operation.body,
    )
    assert response.status_code == expected_status, response.text
    if expected_status == 500:
        assert "private-branch-diagnostic" not in response.text
        assert isinstance(response.json()["detail"], str)
    else:
        assert response.json() == {"detail": "Branch action rejected"}
    boundary.assert_awaited_once_with(**operation.arguments)
    assert branch_harness.session.mock_calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "limited", [False, True], ids=["feature-denied", "capacity-limit"]
)
async def test_branch_creation_respects_business_feature_and_capacity_denials(
    branch_harness: BranchHarness,
    limited: bool,
) -> None:
    """Retain explicit feature error codes and branch capacity denial status."""
    error = (
        BranchLimitExceededError(message="Branch capacity exhausted")
        if limited
        else ForbiddenError(
            message="Feature unavailable", error_code="FEATURE_DISABLED"
        )
    )
    branch_harness.service.create_branch.side_effect = error
    response = await branch_harness.request(
        method="POST",
        path="/",
        parameters={"restaurant_id": 31},
        body=CREATE_BODY,
    )
    assert response.status_code == (400 if limited else 403), response.text
    assert response.json() == {
        "detail": (
            "Branch capacity exhausted"
            if limited
            else {
                "code": "FEATURE_DISABLED",
                "message": "Feature unavailable",
            }
        )
    }
    assert branch_harness.session.mock_calls == []


# ==============================================
# LIST FILTERS AND BRANCH COST CALCULATION
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("active", [False, True])
@pytest.mark.parametrize("wilaya", [None, "Alger"])
async def test_branch_repository_listing_uses_exact_filters_and_pagination(
    branch_harness: BranchHarness,
    active: bool,
    wilaya: str | None,
) -> None:
    """Cover regional and unfiltered listings without discarding active filters."""
    parameters: JsonObject = {"skip": 5, "limit": 10, "only_active": active}
    if wilaya is not None:
        parameters["wilaya"] = wilaya
    response = await branch_harness.request(
        method="GET", path="/", parameters=parameters
    )
    assert response.status_code == 200, response.text
    assert response.json() == {
        "items": [BRANCH.model_dump(mode="json")],
        "total": 3,
        "skip": 5,
        "limit": 10,
    }
    if wilaya is not None:
        branch_harness.repository.get_by_wilaya.assert_awaited_once_with(
            wilaya="Alger",
            skip=5,
            limit=10,
            only_active=active,
        )
        branch_harness.repository.count_by_wilaya.assert_awaited_once_with(
            wilaya="Alger",
            only_active=active,
        )
        branch_harness.repository.get_all.assert_not_awaited()
    else:
        filters = {"is_active": True} if active else {}
        branch_harness.repository.get_all.assert_awaited_once_with(
            skip=5,
            limit=10,
            filters=filters,
            order_by="name",
        )
        branch_harness.repository.count.assert_awaited_once_with(filters=filters)
        branch_harness.repository.get_by_wilaya.assert_not_awaited()
    assert branch_harness.session.mock_calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("count", [0, 3])
async def test_branch_cost_uses_record_restaurant_and_handles_empty_count(
    branch_harness: BranchHarness,
    count: int,
) -> None:
    """Use the stored restaurant association and avoid division by zero."""
    branch_harness.service.get_by_id.return_value = BRANCH
    branch_harness.service.get_branch_cost.return_value = 300.0
    branch_harness.service.count_by_restaurant.return_value = count
    response = await branch_harness.request(
        method="GET",
        path="/21/cost",
        parameters={"restaurant_id": 999},
    )
    assert response.status_code == 200, response.text
    assert response.json() == {
        "branch_id": 21,
        "restaurant_id": 31,
        "branch_name": "Central",
        "total_branches": count,
        "total_cost": 300.0,
        "avg_cost_per_branch": 100.0 if count else 0,
    }
    branch_harness.service.get_by_id.assert_awaited_once_with(branch_id=21)
    branch_harness.service.get_branch_cost.assert_awaited_once_with(restaurant_id=31)
    branch_harness.service.count_by_restaurant.assert_awaited_once_with(
        restaurant_id=31
    )
    assert branch_harness.session.mock_calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("missing", [False, True])
async def test_branch_cost_sanitizes_internal_failure_or_reports_missing_record(
    branch_harness: BranchHarness,
    missing: bool,
) -> None:
    """Stop cost queries after a missing or inaccessible branch lookup."""
    branch_harness.service.get_by_id.side_effect = (
        NotFoundError(message="Branch absent")
        if missing
        else RuntimeError("private-cost")
    )
    response = await branch_harness.request(method="GET", path="/21/cost")
    assert response.status_code == (404 if missing else 500), response.text
    assert "private-cost" not in response.text
    branch_harness.service.get_branch_cost.assert_not_awaited()
    branch_harness.service.count_by_restaurant.assert_not_awaited()
    assert branch_harness.session.mock_calls == []


# ==============================================
# REQUEST VALIDATION
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path", "parameters", "body", "location"),
    [
        ("GET", "/", {"restaurant_id": 0}, None, ["query", "restaurant_id"]),
        ("GET", "/", {"skip": -1}, None, ["query", "skip"]),
        ("GET", "/", {"limit": 201}, None, ["query", "limit"]),
        ("GET", "/", {"limit": 0}, None, ["query", "limit"]),
        ("GET", "/", {"search": ""}, None, ["query", "search"]),
        ("GET", "/", {"wilaya": "x" * 101}, None, ["query", "wilaya"]),
        ("GET", "/0", {}, None, ["path", "branch_id"]),
        ("POST", "/", {}, CREATE_BODY, ["query", "restaurant_id"]),
        ("POST", "/", {"restaurant_id": 31}, {}, ["body", "name"]),
        ("POST", "/", {"restaurant_id": 31}, {"name": "x" * 256}, ["body", "name"]),
        ("PATCH", "/21", {}, {"phone": "x" * 21}, ["body", "phone"]),
        ("PATCH", "/21/status", {}, {}, ["body", "is_active"]),
        ("GET", "/restaurant/0", {}, None, ["path", "restaurant_id"]),
        ("GET", "/stats/summary", {}, None, ["query", "restaurant_id"]),
    ],
)
async def test_branch_invalid_request_never_reaches_business_operation(
    branch_harness: BranchHarness,
    method: str,
    path: str,
    parameters: JsonObject,
    body: JsonObject | None,
    location: list[str],
) -> None:
    """Reject malformed identifiers, oversized fields, and invalid pagination."""
    response = await branch_harness.request(
        method=method,
        path=path,
        parameters=parameters,
        body=body,
    )
    assert response.status_code == 422, response.text
    assert any(item["loc"] == location for item in response.json()["detail"])
    assert branch_harness.service.mock_calls == []
    assert branch_harness.session.mock_calls == []
