# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Test private billing HTTP contracts without bank, identity, or storage IO."""

# ==============================================
# IMPORTS
# ==============================================

from collections.abc import AsyncIterator
from dataclasses import dataclass
from hashlib import sha256
from types import SimpleNamespace
from typing import (
    Any,
    TypeAlias,
    get_args,
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
from app.api.v1 import manual_payments as billing
from app.core.database import get_db
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from app.schemas.manual_payment import (
    ManualPaymentReview,
    ManualSubscriptionCheckout,
    ReceiptResponse,
)
from app.schemas.payment import PaymentResponse

# ==============================================
# REPRESENTATIVE PRIVATE EVIDENCE AND IDENTITIES
# ==============================================

JsonObject: TypeAlias = dict[str, Any]
OWNER = auth.OwnerPrincipal(owner_id=17)
REVIEWER = auth.AdminPrincipal(admin_id=37)
REVIEWER_DEPENDENCY = get_args(billing.Reviewer)[1].dependency
CONTENT = b"\x89PNG\r\n\x1a\nprivate-receipt-evidence"
RECEIPT = ReceiptResponse(
    id=81,
    payment_id=61,
    transaction_reference="TRANSFER-061",
    sha256=sha256(CONTENT).hexdigest(),
    media_type="image/png",
    review_status="pending",
    reviewed_by=None,
    reviewed_at=None,
    received_amount=None,
    received_currency=None,
    review_note=None,
)
PAYMENT = PaymentResponse(
    id=61,
    owner_id=17,
    restaurant_id=31,
    subscription_id=71,
    payment_method="ccp",
    payment_provider="manual_transfer",
    amount=1200.0,
    currency="DZD",
    status="pending",
    created_at="2026-10-16T12:00:00Z",
    updated_at="2026-10-16T12:05:00Z",
)
AUDIT: JsonObject = {
    "id": 91,
    "action": "receipt_submitted",
    "owner_id": 17,
    "admin_id": None,
    "created_at": "2026-10-16T12:05:00Z",
    "details": {"payment_id": 61, "currency": "DZD"},
}
CHECKOUT: JsonObject = {
    "restaurant_id": 31,
    "plan_id": 41,
    "billing_cycle": "monthly",
    "payment_method": "ccp",
}
APPROVAL: JsonObject = {
    "decision": "approve",
    "funds_received": True,
    "bank_transaction_reference": "BANK-061",
    "received_amount": "1200.00",
    "received_currency": "DZD",
    "note": "Bank account credited independently",
}


@dataclass
class BillingHarness:
    """Isolate completed identity dependencies and every billing business effect."""

    app: FastAPI
    service: Mock
    checkout: Mock
    session: AsyncMock
    ownership: AsyncMock
    repository: Mock

    async def request(
        self,
        *,
        method: str,
        path: str,
        body: Any = None,
        parameters: JsonObject | None = None,
        content: bytes | AsyncIterator[bytes] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Response:
        """Call real ASGI endpoints without a lifespan or outbound HTTP client."""
        async with AsyncClient(
            transport=ASGITransport(app=self.app, raise_app_exceptions=False),
            base_url="https://local.test",
        ) as client:
            return await client.request(
                method,
                "/api/v1" + path,
                json=body,
                params=parameters,
                content=content,
                headers=headers,
            )

    def assert_no_storage(self) -> None:
        """Confirm no real ORM session method has been requested."""
        assert self.session.mock_calls == []


@pytest.fixture(scope="module")
def billing_application() -> FastAPI:
    """Build immutable route definitions without the deployed application."""
    app = FastAPI()
    app.include_router(billing.router, prefix="/api/v1")
    return app


@pytest.fixture
def billing_harness(
    monkeypatch: pytest.MonkeyPatch, billing_application: FastAPI
) -> BillingHarness:
    """Use explicit test principals rather than treating numeric IDs as login."""
    session = AsyncMock(spec=AsyncSession)
    service = create_autospec(billing.ManualPaymentService, instance=True)
    checkout = create_autospec(billing.SubscriptionCheckoutService, instance=True)
    repository = Mock(
        get_payment=AsyncMock(return_value=PAYMENT),
        get_audit=AsyncMock(return_value=[AUDIT]),
        list_pending=AsyncMock(return_value=[RECEIPT]),
    )
    service.repo = repository
    service.get_receipt.return_value = SimpleNamespace(
        **RECEIPT.model_dump(), content=CONTENT
    )
    service.submit_receipt.return_value = RECEIPT
    service.review.return_value = RECEIPT
    checkout.create.return_value = PAYMENT
    monkeypatch.setattr(billing, "ManualPaymentService", Mock(return_value=service))
    monkeypatch.setattr(
        billing, "SubscriptionCheckoutService", Mock(return_value=checkout)
    )
    ownership = AsyncMock(return_value=31)
    monkeypatch.setattr(billing, "require_owned_payment", ownership)

    async def database_boundary() -> AsyncIterator[AsyncMock]:
        """Provide a session double without connecting to any database."""
        yield session

    async def trusted_owner() -> auth.OwnerPrincipal:
        """Stand in for a separately verified owner only inside this test app."""
        return OWNER

    async def trusted_reviewer() -> auth.AdminPrincipal:
        """Stand in for a completed identity and payments.review permission guard."""
        return REVIEWER

    monkeypatch.setitem(
        billing_application.dependency_overrides, get_db, database_boundary
    )
    monkeypatch.setitem(
        billing_application.dependency_overrides, auth.get_current_owner, trusted_owner
    )
    monkeypatch.setitem(
        billing_application.dependency_overrides, REVIEWER_DEPENDENCY, trusted_reviewer
    )
    return BillingHarness(
        billing_application, service, checkout, session, ownership, repository
    )


# ==============================================
# CHECKOUT AND AUTHENTICATED RECEIPT METADATA
# ==============================================


@pytest.mark.asyncio
async def test_manual_checkout_uses_verified_owner_and_server_pricing(
    billing_harness: BillingHarness,
) -> None:
    """An owner query parameter cannot replace the verified invoice owner."""
    response = await billing_harness.request(
        method="POST",
        path="/billing/subscriptions",
        body=CHECKOUT,
        parameters={"owner_id": 999},
    )
    assert response.status_code == 201, response.text
    assert response.json() == PAYMENT.model_dump(mode="json")
    billing_harness.checkout.create.assert_awaited_once_with(
        owner_id=17, data=ManualSubscriptionCheckout(**CHECKOUT)
    )
    assert billing_harness.service.mock_calls == []
    billing_harness.assert_no_storage()


@pytest.mark.asyncio
async def test_owner_receipt_metadata_excludes_private_content(
    billing_harness: BillingHarness,
) -> None:
    """Serialize only permitted metadata and retain the authenticated owner scope."""
    response = await billing_harness.request(
        method="GET",
        path="/payments/61/receipt",
        parameters={"owner_id": 999, "admin_id": 999},
    )
    assert response.status_code == 200, response.text
    assert response.json() == RECEIPT.model_dump(mode="json")
    assert "content" not in response.json()
    billing_harness.service.get_receipt.assert_awaited_once_with(
        payment_id=61, owner_id=17
    )
    billing_harness.assert_no_storage()


@pytest.mark.asyncio
async def test_review_context_combines_authorized_invoice_evidence_and_audit(
    billing_harness: BillingHarness,
) -> None:
    """Only the explicitly trusted reviewer identity reaches review-context reads."""
    response = await billing_harness.request(
        method="GET", path="/admin/manual-payments/61", parameters={"admin_id": 999}
    )
    assert response.status_code == 200, response.text
    assert response.json() == {
        "payment": PAYMENT.model_dump(mode="json"),
        "receipt": RECEIPT.model_dump(mode="json"),
        "audit": [AUDIT],
    }
    billing_harness.service.get_receipt.assert_awaited_once_with(
        payment_id=61, owner_id=None, admin_id=37
    )
    billing_harness.repository.get_payment.assert_awaited_once_with(
        payment_id=61, owner_id=None
    )
    billing_harness.repository.get_audit.assert_awaited_once_with(payment_id=61)
    billing_harness.assert_no_storage()


@pytest.mark.asyncio
@pytest.mark.parametrize("parameters", [{}, {"skip": 5, "limit": 10}])
async def test_pending_queue_is_bounded_and_contains_metadata_only(
    billing_harness: BillingHarness, parameters: JsonObject
) -> None:
    """Forward documented queue pagination without returning receipt binary data."""
    response = await billing_harness.request(
        method="GET", path="/admin/manual-payments", parameters=parameters
    )
    assert response.status_code == 200, response.text
    assert response.json() == [RECEIPT.model_dump(mode="json")]
    billing_harness.repository.list_pending.assert_awaited_once_with(
        skip=parameters.get("skip", 0), limit=parameters.get("limit", 50)
    )
    billing_harness.assert_no_storage()


# ==============================================
# BOUNDED STREAMING UPLOADS AND PRIVATE DOWNLOADS
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "media_type",
    ["image/png", "IMAGE/PNG; charset=binary", " application/pdf ; charset=binary"],
)
async def test_receipt_upload_preserves_bytes_and_normalizes_media_type(
    billing_harness: BillingHarness, media_type: str
) -> None:
    """Authorize first and forward the exact bounded body and transfer reference."""
    response = await billing_harness.request(
        method="POST",
        path="/payments/61/receipt",
        content=CONTENT,
        headers={"Content-Type": media_type, "X-Transaction-Reference": "TRANSFER-061"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["review_status"] == "pending"
    billing_harness.ownership.assert_awaited_once_with(
        payment_id=61, owner=OWNER, session=billing_harness.session
    )
    billing_harness.service.submit_receipt.assert_awaited_once_with(
        payment_id=61,
        owner_id=17,
        transaction_reference="TRANSFER-061",
        content=CONTENT,
        media_type=media_type.split(";", 1)[0].strip().lower(),
    )
    billing_harness.service.review.assert_not_awaited()
    billing_harness.checkout.create.assert_not_awaited()
    billing_harness.assert_no_storage()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "overflow", [False, True], ids=["exact-limit", "one-byte-over"]
)
async def test_receipt_stream_enforces_limit_across_chunks(
    billing_harness: BillingHarness, overflow: bool
) -> None:
    """Bound cumulative chunks even when Content-Length is absent."""
    first = b"x" * (billing.MAX_RECEIPT_BYTES - 1)

    async def chunks() -> AsyncIterator[bytes]:
        """Yield a streaming request exactly at or one byte beyond the size cap."""
        yield first
        yield b"xy" if overflow else b"x"

    response = await billing_harness.request(
        method="POST",
        path="/payments/61/receipt",
        content=chunks(),
        headers={
            "Content-Type": "image/png",
            "X-Transaction-Reference": "TRANSFER-061",
        },
    )
    assert response.status_code == (413 if overflow else 200), response.text
    if overflow:
        assert response.json() == {"detail": "Receipt exceeds 2 MiB"}
        billing_harness.service.submit_receipt.assert_not_awaited()
    else:
        submitted = billing_harness.service.submit_receipt.await_args.kwargs
        assert submitted["content"] == first + b"x"
        assert len(submitted["content"]) == billing.MAX_RECEIPT_BYTES
    billing_harness.assert_no_storage()


@pytest.mark.asyncio
async def test_unowned_payment_is_rejected_before_reading_receipt_stream(
    monkeypatch: pytest.MonkeyPatch, billing_harness: BillingHarness
) -> None:
    """Run the real tenant guard and ensure unauthorized bodies are never consumed."""
    monkeypatch.setattr(billing, "require_owned_payment", auth.require_owned_payment)
    result = Mock()
    result.scalar_one_or_none.return_value = None
    billing_harness.session.execute.return_value = result
    consumed: list[bool] = []

    async def forbidden_body() -> AsyncIterator[bytes]:
        """Record any attempt to read a body before ownership is established."""
        consumed.append(True)
        yield CONTENT

    response = await billing_harness.request(
        method="POST",
        path="/payments/61/receipt",
        content=forbidden_body(),
        headers={
            "Content-Type": "image/png",
            "X-Transaction-Reference": "TRANSFER-061",
        },
    )
    assert response.status_code == 404, response.text
    assert consumed == []
    billing_harness.service.submit_receipt.assert_not_awaited()
    billing_harness.session.execute.assert_awaited_once()
    billing_harness.session.commit.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "reviewer", [False, True], ids=["owner", "authorized-reviewer"]
)
@pytest.mark.parametrize(
    ("media_type", "extension"),
    [("image/png", "png"), ("image/jpeg", "jpg"), ("application/pdf", "pdf")],
)
async def test_private_receipt_download_sets_attachment_and_no_store_headers(
    billing_harness: BillingHarness, reviewer: bool, media_type: str, extension: str
) -> None:
    """Verify content integrity and private caching headers for both download paths."""
    billing_harness.service.get_receipt.return_value = SimpleNamespace(
        **{**RECEIPT.model_dump(), "media_type": media_type}, content=CONTENT
    )
    path = (
        "/admin/manual-payments/61/receipt/file"
        if reviewer
        else "/payments/61/receipt/file"
    )
    response = await billing_harness.request(method="GET", path=path)
    assert response.status_code == 200, response.text
    assert response.content == CONTENT
    assert response.headers["content-type"] == media_type
    assert (
        response.headers["content-disposition"]
        == f'attachment; filename="receipt-81.{extension}"'
    )
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    expected = (
        {"payment_id": 61, "owner_id": None, "admin_id": 37, "content": True}
        if reviewer
        else {"payment_id": 61, "owner_id": 17, "content": True}
    )
    billing_harness.service.get_receipt.assert_awaited_once_with(**expected)
    billing_harness.assert_no_storage()


# ==============================================
# INDEPENDENT REVIEW INPUT AND DOMAIN FAILURES
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body", [APPROVAL, {"decision": "reject", "note": "Funds not received"}]
)
async def test_review_forwards_only_verified_reviewer_and_validated_evidence(
    billing_harness: BillingHarness, body: JsonObject
) -> None:
    """Validate full bank confirmation or rejection before requesting a decision."""
    response = await billing_harness.request(
        method="POST",
        path="/admin/manual-payments/61/review",
        body=body,
        parameters={"admin_id": 999},
    )
    assert response.status_code == 200, response.text
    billing_harness.service.review.assert_awaited_once_with(
        payment_id=61, admin_id=37, data=ManualPaymentReview(**body)
    )
    assert response.json() == RECEIPT.model_dump(mode="json")
    billing_harness.assert_no_storage()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "body"),
    [
        ("/billing/subscriptions", {**CHECKOUT, "amount": 1}),
        ("/billing/subscriptions", {**CHECKOUT, "owner_id": 999}),
        ("/billing/subscriptions", {**CHECKOUT, "payment_method": "stripe"}),
        ("/billing/subscriptions", {**CHECKOUT, "restaurant_id": 0}),
        (
            "/admin/manual-payments/61/review",
            {"decision": "approve", "note": "Receipt looks valid"},
        ),
        ("/admin/manual-payments/61/review", {**APPROVAL, "funds_received": "true"}),
        ("/admin/manual-payments/61/review", {**APPROVAL, "received_currency": "USD"}),
        ("/admin/manual-payments/61/review", {**APPROVAL, "admin_id": 999}),
        (
            "/admin/manual-payments/61/review",
            {
                "decision": "reject",
                "funds_received": True,
                "note": "Contradictory evidence",
            },
        ),
    ],
)
async def test_untrusted_checkout_and_incomplete_review_fields_are_rejected(
    billing_harness: BillingHarness, path: str, body: JsonObject
) -> None:
    """Reject client pricing, spoofed identities, and receipt-only approvals."""
    response = await billing_harness.request(method="POST", path=path, body=body)
    assert response.status_code == 422, response.text
    assert billing_harness.service.mock_calls == []
    assert billing_harness.checkout.mock_calls == []
    billing_harness.assert_no_storage()


@pytest.mark.asyncio
@pytest.mark.parametrize("parameters", [{"skip": -1}, {"limit": 0}, {"limit": 101}])
async def test_review_queue_rejects_invalid_pagination(
    billing_harness: BillingHarness, parameters: JsonObject
) -> None:
    """Invalid administrative pagination cannot invoke a queue query."""
    response = await billing_harness.request(
        method="GET", path="/admin/manual-payments", parameters=parameters
    )
    assert response.status_code == 422, response.text
    billing_harness.repository.list_pending.assert_not_awaited()
    billing_harness.assert_no_storage()


DOMAIN_CASES = (
    ("POST", "/billing/subscriptions", "create", CHECKOUT, NotFoundError, 404),
    ("POST", "/billing/subscriptions", "create", CHECKOUT, ConflictError, 409),
    ("POST", "/billing/subscriptions", "create", CHECKOUT, ValidationError, 422),
    *(
        ("GET", path, "get_receipt", None, kind, code)
        for path in ("/payments/61/receipt", "/payments/61/receipt/file")
        for kind, code in ((NotFoundError, 404), (ValidationError, 422))
    ),
    *(
        ("GET", path, "get_receipt", None, kind, code)
        for path in (
            "/admin/manual-payments/61",
            "/admin/manual-payments/61/receipt/file",
        )
        for kind, code in (
            (NotFoundError, 404),
            (ValidationError, 422),
            (UnauthorizedError, 403),
        )
    ),
    *(
        ("POST", "/admin/manual-payments/61/review", "review", APPROVAL, kind, code)
        for kind, code in (
            (NotFoundError, 404),
            (ConflictError, 409),
            (ValidationError, 422),
            (UnauthorizedError, 403),
            (ValueError, 409),
        )
    ),
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path", "boundary_name", "body", "kind", "expected_status"), DOMAIN_CASES
)
async def test_manual_billing_domain_failures_preserve_http_semantics(
    billing_harness: BillingHarness,
    method: str,
    path: str,
    boundary_name: str,
    body: JsonObject | None,
    kind: type[Exception],
    expected_status: int,
) -> None:
    """Map storage-independent business rejections consistently for each operation."""
    boundary = (
        billing_harness.checkout.create
        if boundary_name == "create"
        else getattr(billing_harness.service, boundary_name)
    )
    boundary.side_effect = (
        kind("Billing action rejected")
        if kind is ValueError
        else kind(message="Billing action rejected")
    )
    response = await billing_harness.request(method=method, path=path, body=body)
    assert response.status_code == expected_status, response.text
    assert response.json() == {"detail": "Billing action rejected"}
    billing_harness.assert_no_storage()


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", [NotFoundError, ConflictError, ValidationError])
async def test_receipt_submission_domain_errors_are_translated(
    billing_harness: BillingHarness, kind: type[Exception]
) -> None:
    """Receipt duplicates, invalid content, and missing invoices keep their statuses."""
    billing_harness.service.submit_receipt.side_effect = kind(
        message="Receipt rejected"
    )
    response = await billing_harness.request(
        method="POST",
        path="/payments/61/receipt",
        content=CONTENT,
        headers={
            "X-Transaction-Reference": "TRANSFER-061",
            "Content-Type": "image/png",
        },
    )
    assert (
        response.status_code
        == {NotFoundError: 404, ConflictError: 409, ValidationError: 422}[kind]
    ), response.text
    assert response.json() == {"detail": "Receipt rejected"}
    billing_harness.assert_no_storage()


@pytest.mark.asyncio
@pytest.mark.parametrize("reference", [None, "ab", "x" * 121])
async def test_receipt_requires_bounded_transaction_reference(
    billing_harness: BillingHarness, reference: str | None
) -> None:
    """Header validation runs before ownership and receipt business operations."""
    headers = {"Content-Type": "image/png"}
    if reference is not None:
        headers["X-Transaction-Reference"] = reference
    response = await billing_harness.request(
        method="POST", path="/payments/61/receipt", content=CONTENT, headers=headers
    )
    assert response.status_code == 422, response.text
    billing_harness.ownership.assert_not_awaited()
    billing_harness.service.submit_receipt.assert_not_awaited()
    billing_harness.assert_no_storage()
