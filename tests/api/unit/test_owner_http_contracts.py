# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Exercise owner HTTP responses, administrative gates, and domain failures."""

# ==============================================
# IMPORTS AND CONTRACT CASES
# ==============================================

from dataclasses import dataclass
from datetime import (
    datetime,
    timezone,
)
from typing import (
    Any,
    TypeAlias,
)
from unittest.mock import (
    Mock,
    create_autospec,
)

import pytest
from fastapi import (
    FastAPI,
    HTTPException,
)
from httpx import (
    ASGITransport,
    AsyncClient,
    Response,
)

from app.api.auth import OwnerPrincipal
from app.api.v1 import owners
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.schemas.owner import OwnerResponse
from app.services.business.owner_service import OwnerService

JsonObject: TypeAlias = dict[str, Any]
APPLICATION = FastAPI()
APPLICATION.include_router(owners.router, prefix="/api/v1")


@dataclass(frozen=True)
class OwnerOperation:
    """Describe an explicit public request and its principal business boundary."""

    method: str
    path: str
    operation: str
    expected_status: int = 200
    body: JsonObject | None = None
    administrative: bool = False


OPERATIONS = (
    OwnerOperation("POST", "/", "create_owner", 201, {"chat_id": 1011}, True),
    OwnerOperation("GET", "/stats", "get_owner_statistics", administrative=True),
    OwnerOperation("GET", "/search?query=owner", "search_owners", administrative=True),
    OwnerOperation("GET", "/11", "get_owner_by_id"),
    OwnerOperation("GET", "/chat/1011", "get_owner_by_id"),
    OwnerOperation("GET", "/", "get_all_owners", administrative=True),
    OwnerOperation(
        "GET", "/status/pending", "get_owners_by_status", administrative=True
    ),
    OwnerOperation("PATCH", "/11", "update_owner", body={"full_name": "Updated Owner"}),
    OwnerOperation(
        "PATCH",
        "/11/status",
        "update_owner_status",
        body={"registration_status": "approved"},
        administrative=True,
    ),
    OwnerOperation("POST", "/11/approve", "approve_owner", administrative=True),
    OwnerOperation("POST", "/11/reject", "reject_owner", administrative=True),
    OwnerOperation("DELETE", "/11", "delete_owner", 204),
)


@dataclass
class OwnerHarness:
    """Retain real routing and schemas while recording business operations."""

    service: Mock

    async def request(self, case: OwnerOperation) -> Response:
        """Send a request entirely within the ASGI process."""
        async with AsyncClient(
            transport=ASGITransport(app=APPLICATION, raise_app_exceptions=False),
            base_url="https://offline.test",
        ) as client:
            return await client.request(
                case.method, "/api/v1/owners" + case.path, json=case.body
            )


@pytest.fixture
def owner_http(monkeypatch: pytest.MonkeyPatch) -> OwnerHarness:
    """Isolate overrides and create a fresh recorder for each HTTP assertion."""
    monkeypatch.setattr(APPLICATION, "dependency_overrides", {})
    record = OwnerResponse(
        id=11,
        chat_id=1011,
        full_name="Test Owner",
        registration_status="pending",
        trial_used=False,
        created_at=datetime(2026, 10, 16, tzinfo=timezone.utc),
        updated_at=datetime(2026, 10, 16, tzinfo=timezone.utc),
    )
    service = create_autospec(OwnerService, instance=True)
    for name in (
        "create_owner",
        "get_owner_by_id",
        "update_owner",
        "update_owner_status",
        "approve_owner",
        "reject_owner",
    ):
        getattr(service, name).return_value = record
    for name in ("search_owners", "get_all_owners", "get_owners_by_status"):
        getattr(service, name).return_value = [record]
    service.count_owners.return_value = 8
    service.get_owner_statistics.return_value = {
        "total": 8,
        "pending": 3,
        "approved": 4,
        "rejected": 1,
        "trial_used": 2,
        "trial_available": 6,
    }

    def inert_service() -> Mock:
        """Prevent construction of a storage-backed service."""
        return service

    def trusted_owner() -> OwnerPrincipal:
        """Represent the identity already validated by independent auth tests."""
        return OwnerPrincipal(owner_id=11)

    def trusted_administrator() -> None:
        """Model a completed administrative permission dependency."""
        return

    APPLICATION.dependency_overrides[owners.get_owner_service] = inert_service
    APPLICATION.dependency_overrides[owners.get_current_owner] = trusted_owner
    APPLICATION.dependency_overrides[owners.ADMIN_DEPENDENCIES[0].dependency] = (
        trusted_administrator
    )
    return OwnerHarness(service)


# ==============================================
# AUTHORIZED RESPONSES AND SANITIZED ERRORS
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case", OPERATIONS, ids=lambda case: case.operation + case.path
)
async def test_owner_operations_return_their_public_contract(
    owner_http: OwnerHarness, case: OwnerOperation
) -> None:
    """Every maintained operation reaches its service and serializes valid data."""
    response = await owner_http.request(case)
    assert response.status_code == case.expected_status, response.text
    method = getattr(owner_http.service, case.operation)
    method.assert_awaited_once()
    if response.status_code == 204:
        assert response.content == b""
    elif case.operation == "get_owner_statistics":
        assert response.json()["total"] == 8 and response.json()["pending"] == 3
    elif "items" in response.json():
        assert response.json()["items"][0]["id"] == 11
        assert response.json()["total"] == (
            1 if case.operation == "search_owners" else 8
        )
    else:
        assert response.json()["id"] == 11 and response.json()["chat_id"] == 1011
    if case.operation == "get_owner_by_id":
        method.assert_awaited_once_with(owner_id=11)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case", OPERATIONS, ids=lambda case: case.operation + case.path
)
async def test_owner_backend_errors_are_sanitized(
    owner_http: OwnerHarness, case: OwnerOperation
) -> None:
    """A failed service produces a stable JSON error without internal details."""
    getattr(owner_http.service, case.operation).side_effect = RuntimeError(
        "private_owner_storage_detail"
    )
    response = await owner_http.request(case)
    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/json")
    assert "private_owner_storage_detail" not in response.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case",
    [case for case in OPERATIONS if case.administrative],
    ids=lambda case: case.operation,
)
async def test_owner_administration_denial_precedes_business_work(
    owner_http: OwnerHarness, case: OwnerOperation
) -> None:
    """Permission failure prevents every administrative owner operation."""

    def denied_administrator() -> None:
        """Represent a trusted identity lacking the required permission."""
        raise HTTPException(status_code=403, detail="Permission denied")

    APPLICATION.dependency_overrides[owners.ADMIN_DEPENDENCIES[0].dependency] = (
        denied_administrator
    )
    response = await owner_http.request(case)
    assert response.status_code == 403
    assert owner_http.service.mock_calls == []


# ==============================================
# DOMAIN ERRORS AND REQUEST VALIDATION
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("case", "failure", "expected"),
    [
        (OPERATIONS[0], ConflictError, 409),
        (OPERATIONS[0], ValidationError, 422),
        (OPERATIONS[3], NotFoundError, 404),
        (OPERATIONS[7], NotFoundError, 404),
        (OPERATIONS[7], ValidationError, 422),
        (OPERATIONS[8], NotFoundError, 404),
        (OPERATIONS[8], ValidationError, 422),
        (OPERATIONS[9], NotFoundError, 404),
        (OPERATIONS[10], NotFoundError, 404),
        (OPERATIONS[11], NotFoundError, 404),
    ],
)
async def test_owner_domain_failures_have_explicit_http_status(
    owner_http: OwnerHarness,
    case: OwnerOperation,
    failure: type[Exception],
    expected: int,
) -> None:
    """Missing records and rejected changes retain documented domain semantics."""
    getattr(owner_http.service, case.operation).side_effect = failure(
        message="owner_operation_rejected"
    )
    response = await owner_http.request(case)
    assert response.status_code == expected, response.text
    assert response.json()["detail"] == "owner_operation_rejected"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("GET", "/?skip=-1", None),
        ("GET", "/?limit=201", None),
        ("GET", "/search?query=", None),
        ("GET", "/0", None),
        ("POST", "/", {"chat_id": 0}),
        ("PATCH", "/11/status", {"registration_status": "unknown"}),
    ],
)
async def test_invalid_owner_requests_do_not_reach_services(
    owner_http: OwnerHarness, method: str, path: str, body: JsonObject | None
) -> None:
    """Schema and pagination failures reject input before reads or writes."""
    response = await owner_http.request(
        OwnerOperation(method, path, "validation", body=body)
    )
    assert response.status_code == 422
    assert owner_http.service.mock_calls == []
