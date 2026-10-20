# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Verify payment HTTP ownership, error translation, and immutable ledger rules."""

# ==============================================
# IMPORTS AND INERT HTTP HARNESS
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
    AsyncMock,
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
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import OwnerPrincipal
from app.api.v1 import payments
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.repositories.payment_repo import PaymentRepository
from app.schemas.payment import PaymentResponse
from app.services.business.payment_service import PaymentService

JsonObject: TypeAlias = dict[str, Any]


@dataclass
class PaymentHarness:
    """Expose HTTP requests and independently observable service boundaries."""

    app: FastAPI
    service: Mock
    owned_payment: AsyncMock
    owned_restaurant: AsyncMock
    owned_subscription: AsyncMock

    async def request(self, method: str, path: str, **arguments: Any) -> Response:
        """Execute an in-process request without a TCP connection or lifespan."""
        async with AsyncClient(
            transport=ASGITransport(app=self.app, raise_app_exceptions=False),
            base_url="https://offline.test",
        ) as client:
            return await client.request(method, "/api/v1/payments" + path, **arguments)


def payment_record(*, status: str = "pending") -> PaymentResponse:
    """Build a valid response whose identity and amount assertions are explicit."""
    now = datetime(2026, 10, 16, tzinfo=timezone.utc)
    return PaymentResponse(
        id=41,
        owner_id=11,
        restaurant_id=21,
        subscription_id=31,
        payment_method="ccp",
        payment_provider="manual_transfer",
        currency="DZD",
        amount=1200,
        status=status,
        created_at=now,
        updated_at=now,
        paid_at=now if status == "paid" else None,
    )


@pytest.fixture
def payment_http(monkeypatch: pytest.MonkeyPatch) -> PaymentHarness:
    """Replace storage and trusted principal resolution, retaining real routes."""
    application = FastAPI()
    application.include_router(payments.router, prefix="/api/v1")
    service = create_autospec(PaymentService, instance=True)
    service.session = AsyncMock(spec=AsyncSession)
    service.repo = create_autospec(PaymentRepository, instance=True)
    service.repo.get_all.return_value = [payment_record()]
    service.repo.count.return_value = 12
    service.get_by_id.return_value = payment_record()
    service.get_by_subscription.return_value = [payment_record()]
    service.create_payment.return_value = payment_record()

    def inert_service() -> Mock:
        """Provide the recorder without constructing a live business service."""
        return service

    def trusted_owner() -> OwnerPrincipal:
        """Model a previously authenticated owner for authorized route tests."""
        return OwnerPrincipal(owner_id=11)

    application.dependency_overrides[payments.get_payment_service] = inert_service
    application.dependency_overrides[payments.get_current_owner] = trusted_owner
    guards = [AsyncMock() for _ in range(3)]
    for name, guard in zip(
        (
            "require_owned_payment",
            "require_owned_restaurant",
            "require_owned_subscription",
        ),
        guards,
        strict=True,
    ):
        monkeypatch.setattr(payments, name, guard)
    return PaymentHarness(application, service, *guards)


# ==============================================
# OWNERSHIP AND AUTHORITATIVE LIST FILTERS
# ==============================================


@pytest.mark.asyncio
async def test_payment_list_enforces_owner_and_preserves_filtered_total(
    payment_http: PaymentHarness,
) -> None:
    """Client filters cannot replace the principal and count is not page length."""
    response = await payment_http.request(
        "GET",
        "/",
        params={"restaurant_id": 21, "status": "pending", "skip": 4, "limit": 2},
    )
    assert response.status_code == 200, response.text
    assert response.json()["total"] == 12
    assert response.json()["items"][0]["id"] == 41
    filters = {"owner_id": 11, "restaurant_id": 21, "status": "pending"}
    payment_http.service.repo.get_all.assert_awaited_once_with(
        skip=4, limit=2, filters=filters
    )
    payment_http.service.repo.count.assert_awaited_once_with(filters=filters)
    payment_http.owned_restaurant.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/", "/stats/summary"])
async def test_foreign_owner_query_is_forbidden_before_reading_payments(
    payment_http: PaymentHarness, path: str
) -> None:
    """A forged owner_id must return 403 instead of broadening tenant access."""
    response = await payment_http.request("GET", path, params={"owner_id": 99})
    assert response.status_code == 403, response.text
    payment_http.service.repo.get_all.assert_not_awaited()
    payment_http.service.get_payment_summary.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/41", "/41/status", "/subscription/31"])
async def test_foreign_resource_is_hidden_before_service_read(
    payment_http: PaymentHarness, path: str
) -> None:
    """Tenant denial must remain 404 and prevent all ledger reads."""
    denial = HTTPException(status_code=404, detail="Payment not found")
    payment_http.owned_payment.side_effect = denial
    payment_http.owned_subscription.side_effect = denial
    response = await payment_http.request("GET", path)
    assert response.status_code == 404
    payment_http.service.get_by_id.assert_not_awaited()
    payment_http.service.get_by_subscription.assert_not_awaited()


# ==============================================
# PAYMENT READS, CREATION, AND DOMAIN ERRORS
# ==============================================


@pytest.mark.asyncio
async def test_get_payment_returns_owned_dzd_record(
    payment_http: PaymentHarness,
) -> None:
    """Serialize the actual payment response schema after tenant authorization."""
    response = await payment_http.request("GET", "/41")
    assert response.status_code == 200
    assert response.json()["owner_id"] == 11
    assert response.json()["currency"] == "DZD"
    payment_http.service.get_by_id.assert_awaited_once_with(payment_id=41)


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["pending", "paid", "failed", "cancelled"])
async def test_payment_status_flags_match_the_ledger(
    payment_http: PaymentHarness, state: str
) -> None:
    """Each status response exposes consistent flags and the recorded amount."""
    payment_http.service.get_by_id.return_value = payment_record(status=state)
    response = await payment_http.request("GET", "/41/status")
    assert response.status_code == 200
    data = response.json()
    assert data["payment_id"] == 41 and data["amount"] == 1200
    for value in ("pending", "paid", "failed", "cancelled"):
        assert data[f"is_{value}"] is (state == value)


def checkout_payload() -> JsonObject:
    """Provide owner-supplied input without settlement or approval fields."""
    return {
        "owner_id": 11,
        "restaurant_id": 21,
        "subscription_id": 31,
        "payment_method": "ccp",
        "amount": 1200,
    }


@pytest.mark.asyncio
async def test_create_payment_checks_all_related_ownership(
    payment_http: PaymentHarness,
) -> None:
    """Invoice creation checks restaurant and subscription and remains pending."""
    response = await payment_http.request("POST", "/", json=checkout_payload())
    assert response.status_code == 201, response.text
    assert response.json()["status"] == "pending"
    payment_http.owned_restaurant.assert_awaited_once()
    payment_http.owned_subscription.assert_awaited_once()
    data = payment_http.service.create_payment.await_args.kwargs["payment_data"]
    assert data.owner_id == 11 and data.restaurant_id == 21 and data.amount == 1200


@pytest.mark.asyncio
async def test_create_payment_rejects_spoofed_owner(
    payment_http: PaymentHarness,
) -> None:
    """A body owner identifier never overrides the authenticated principal."""
    response = await payment_http.request(
        "POST", "/", json={**checkout_payload(), "owner_id": 99}
    )
    assert response.status_code == 403
    payment_http.service.create_payment.assert_not_awaited()
    payment_http.owned_restaurant.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("failure", "expected"),
    [(NotFoundError, 404), (ConflictError, 409), (ValidationError, 422)],
)
async def test_creation_domain_errors_preserve_http_contract(
    payment_http: PaymentHarness, failure: type[Exception], expected: int
) -> None:
    """Domain errors are translated without leaking a generic server failure."""
    payment_http.service.create_payment.side_effect = failure(
        message="invoice_rejected"
    )
    response = await payment_http.request("POST", "/", json=checkout_payload())
    assert response.status_code == expected
    assert response.json()["detail"] == "invoice_rejected"


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/41", "/41/status"])
async def test_missing_payment_is_404(payment_http: PaymentHarness, path: str) -> None:
    """A record disappearing after the ownership check remains a 404."""
    payment_http.service.get_by_id.side_effect = NotFoundError(
        message="payment_missing"
    )
    response = await payment_http.request("GET", path)
    assert response.status_code == 404
    assert response.json()["detail"] == "payment_missing"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path", ["/", "/41", "/41/status", "/stats/summary", "/subscription/31"]
)
async def test_payment_read_failures_do_not_expose_internal_details(
    payment_http: PaymentHarness, path: str
) -> None:
    """Database failure text must stay out of every public error body."""
    for method in (
        payment_http.service.repo.get_all,
        payment_http.service.get_by_id,
        payment_http.service.get_by_subscription,
        payment_http.service.get_payment_summary,
    ):
        method.side_effect = RuntimeError("private_database_diagnostic")
    response = await payment_http.request("GET", path)
    assert response.status_code == 500
    assert "private_database_diagnostic" not in response.text
    assert response.headers["content-type"].startswith("application/json")


@pytest.mark.asyncio
async def test_subscription_page_is_scoped_before_read(
    payment_http: PaymentHarness,
) -> None:
    """Subscription lookup checks tenant ownership and forwards pagination."""
    response = await payment_http.request(
        "GET", "/subscription/31", params={"skip": 3, "limit": 2}
    )
    assert response.status_code == 200
    assert response.json()["items"][0]["subscription_id"] == 31
    payment_http.owned_subscription.assert_awaited_once()
    payment_http.service.get_by_subscription.assert_awaited_once_with(
        subscription_id=31, skip=3, limit=2
    )


@pytest.mark.asyncio
async def test_payment_summary_passes_only_the_authenticated_owner(
    payment_http: PaymentHarness,
) -> None:
    """Summary totals retain tenant scope even without an explicit owner filter."""
    payment_http.service.get_payment_summary.return_value = {
        "total_payments": 3,
        "total_paid": 1,
        "total_pending": 2,
        "total_failed": 0,
        "total_cancelled": 0,
        "total_amount": 3600,
        "total_paid_amount": 1200,
        "total_pending_amount": 2400,
    }
    response = await payment_http.request(
        "GET", "/stats/summary", params={"restaurant_id": 21}
    )
    assert response.status_code == 200
    assert response.json()["total_paid_amount"] == 1200
    payment_http.service.get_payment_summary.assert_awaited_once_with(
        restaurant_id=21, owner_id=11
    )
    payment_http.owned_restaurant.assert_awaited_once()


@pytest.mark.asyncio
async def test_payment_filter_domain_validation_is_a_client_error(
    payment_http: PaymentHarness,
) -> None:
    """Domain filter validation must not be masked by the status query value."""
    payment_http.service.repo.get_all.side_effect = ValidationError(
        message="invalid_filter"
    )
    response = await payment_http.request("GET", "/", params={"status": "pending"})
    assert response.status_code == 400
    assert response.json()["detail"] == "invalid_filter"


# ==============================================
# LEDGER IMMUTABILITY AND INPUT VALIDATION
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("PATCH", "/41", {"external_reference": "client-reference"}),
        ("PATCH", "/41/status", {"status": "paid"}),
        ("PATCH", "/41/confirm", None),
        ("PATCH", "/41/fail", None),
        ("PATCH", "/41/cancel", None),
        ("PATCH", "/41/refund", None),
        ("DELETE", "/41", None),
    ],
)
async def test_owner_cannot_mutate_billing_ledger(
    payment_http: PaymentHarness, method: str, path: str, body: JsonObject | None
) -> None:
    """All legacy owner mutation routes require the administrative review flow."""
    response = await payment_http.request(method, path, json=body)
    assert response.status_code == 403, response.text
    assert "administrative" in response.json()["detail"]
    payment_http.owned_payment.assert_awaited_once()
    assert payment_http.service.mock_calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query", [{"skip": -1}, {"limit": 0}, {"limit": 201}, {"restaurant_id": 0}]
)
async def test_invalid_payment_queries_never_reach_storage(
    payment_http: PaymentHarness, query: dict[str, int]
) -> None:
    """FastAPI rejects invalid pagination and identifiers before service IO."""
    response = await payment_http.request("GET", "/", params=query)
    assert response.status_code == 422
    payment_http.service.repo.get_all.assert_not_awaited()
