# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# REAL O5 DOCUMENTARY TRANSACTION REGRESSIONS
# Exercise actual HTTP routes and committed PostgreSQL state using isolated synthetic principals and financial evidence.
# ==============================================

"""Authentication transport is injected; permission checks, transactions and persisted financial services are real."""

from __future__ import annotations

# isort: split
# ==============================================
# ISOLATED HTTP AND FINANCIAL DEPENDENCIES
# No fixture-wide rollback can conceal a partially committed issuance or invalidation.
# ==============================================

import asyncio
import os
from collections.abc import AsyncIterator
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import (
    Depends,
    FastAPI,
)
from httpx import (
    ASGITransport,
    AsyncClient,
)
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)
from starlette.requests import Request
from starlette.responses import JSONResponse
from test_billing_country_postgres import reviewer
from test_followup_postgres import pending_offer

from test_billing_country_postgres import factory as factory  # noqa: PLC0414  # isort: skip  # fmt: skip

from app.core.config import settings
from app.core.security.oidc import OIDCPrincipal
from app.core.security.tenant_types import TenantAccessDenied
from app.integration.identity import BrowserIdentity
from app.integration.saas_document_routes import mount_saas_document_routes
from app.integration.saas_payment_routes import mount_saas_payment_routes
from app.models.admin import Admin
from app.repositories.subscription_queries import base_select
from app.schemas.cash_collection import CashConfirmation
from app.schemas.manual_payment import ManualPaymentReview
from app.services.business.cash_collection_service import CashCollectionService
from app.services.business.manual_payment_service import ManualPaymentService
from app.services.business.subscription_documents import SubscriptionDocumentService

pytestmark = pytest.mark.country_rehearsal

# ==============================================
# INDEPENDENT REQUEST SESSION COMPOSITION
# Only identity verification is substituted; every route checks the exact stored permission itself.
# ==============================================


def client_for(
    *, factory: async_sessionmaker[AsyncSession], principal: OIDCPrincipal
) -> AsyncClient:
    """Return an ASGI client whose every request obtains its own real database transaction."""
    app = FastAPI()

    # ==============================================
    # SAME TENANT REFUSAL AS THE BROWSER HOST
    # Translate a domain denial without weakening or replacing its real authorization query.
    # ==============================================

    @app.exception_handler(TenantAccessDenied)
    async def denied(_request: Request, _error: TenantAccessDenied) -> JSONResponse:
        """Expose the host's bounded refusal status rather than a test transport exception."""
        return JSONResponse({"detail": "Tenant access denied"}, status_code=403)

    # ==============================================
    # EXPLICIT TEST PRINCIPAL
    # This fixture is not evidence of a new Keycloak login or JWT verification.
    # ==============================================

    async def identity() -> BrowserIdentity:
        """Supply the named synthetic principal without bypassing database authorization."""
        return BrowserIdentity(
            principal=principal,
            name="Synthetic document tester",
            access_token="OFFLINE",
        )

    # ==============================================
    # PER-REQUEST PERSISTENCE BOUNDARY
    # No external transaction encloses application writes.
    # ==============================================

    async def sessions() -> AsyncIterator[AsyncSession]:
        """Yield a fresh session and let the actual route own its commit or rollback."""
        async with factory() as session:
            yield session

    mount_saas_document_routes(
        app=app,
        identity_dep=Depends(identity),
        session_dep=Depends(sessions),
        marker=os.environ["COUNTRY_BASE_TEST_MARKER"],
        origin="https://127.0.0.1:5180",
    )
    mount_saas_payment_routes(
        app=app, identity_dep=Depends(identity), session_dep=Depends(sessions)
    )
    return AsyncClient(
        transport=ASGITransport(app=app), base_url="http://offline-document"
    )


# ==============================================
# ACTUAL TRANSFER REVIEW
# Prepare a pending offer through existing enrollment and checkout, then independently verify synthetic funds.
# ==============================================


async def settle(
    *, factory: async_sessionmaker[AsyncSession], owner: int, payment: int
) -> None:
    """Commit the existing receipt/review/activation workflow; no bank or provider is contacted."""
    reference = "LOCAL-DOCUMENT-" + uuid4().hex
    principal = await reviewer(factory=factory, permission="payments.review")
    async with factory() as observer:
        existing_reference = await observer.scalar(
            text(
                "SELECT transaction_reference FROM manual_payment_receipts WHERE payment_id=:p"
            ),
            {"p": payment},
        )
    if existing_reference is not None:
        reference = existing_reference
    async with factory() as session, session.begin():
        if existing_reference is None:
            await ManualPaymentService(session=session).submit_receipt(
                payment_id=payment,
                owner_id=owner,
                transaction_reference=reference,
                content=b"%PDF-1.4\nFICTITIOUS TEST EVIDENCE "
                + reference.encode()
                + b"\n%%EOF",
                media_type="application/pdf",
            )
    async with factory() as session, session.begin():
        admin = await session.scalar(
            base_select(Admin)
            .with_only_columns(Admin.id)
            .where(Admin.auth_subject == principal.subject)
        )
        amount = await session.scalar(
            text("SELECT amount FROM payments WHERE id=:p"), {"p": payment}
        )
        assert admin is not None
        await ManualPaymentService(session=session).review(
            payment_id=payment,
            admin_id=admin,
            data=ManualPaymentReview(
                decision="approve",
                funds_received=True,
                received_amount=Decimal(str(amount)),
                received_currency="DZD",
                bank_transaction_reference=reference,
                note="Fictitious local funds only",
            ),
        )


# ==============================================
# EMISSION ADMISSION AND DOCUMENTARY AUTHORITY
# Payment review and administrative role names must never confer the new independent grants.
# ==============================================


@pytest.mark.asyncio
async def test_emission_requires_funds_and_exact_permission(
    factory: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Refuse before funds, refuse a payments reviewer, then emit only for the explicit issuer."""
    monkeypatch.setattr(settings, "MANUAL_CCP_ENABLED", True)
    owner, organization, owner_id, restaurant, payment = await pending_offer(
        factory=factory
    )
    issuer = await reviewer(factory=factory, permission="subscriptions.documents.issue")
    reviewer_only = await reviewer(factory=factory, permission="payments.review")
    async with client_for(factory=factory, principal=issuer) as client:
        response = await client.post(
            f"/api/web/platform/saas-payments/{payment}/documents", json={}
        )
        assert (
            response.status_code == 409
            and response.json()["detail"]["code"]
            == "subscription_document_funds_unverified"
        )
    async with factory() as observer:
        assert (
            await observer.scalar(
                text("SELECT count(*) FROM subscription_documents WHERE payment_id=:p"),
                {"p": payment},
            )
            == 0
        )
    async with factory() as session, session.begin():
        reference = "DOCUMENT-PROOF-ONLY-" + uuid4().hex
        await ManualPaymentService(session=session).submit_receipt(
            payment_id=payment,
            owner_id=owner_id,
            transaction_reference=reference,
            content=b"%PDF-1.4\n" + reference.encode() + b"\n%%EOF",
            media_type="application/pdf",
        )
    async with client_for(factory=factory, principal=issuer) as client:
        assert (
            await client.post(
                f"/api/web/platform/saas-payments/{payment}/documents", json={}
            )
        ).status_code == 409
    await settle(factory=factory, owner=owner_id, payment=payment)
    async with client_for(factory=factory, principal=reviewer_only) as client:
        assert (
            await client.post(
                f"/api/web/platform/saas-payments/{payment}/documents", json={}
            )
        ).status_code == 403
        assert (await client.get("/api/web/platform/saas-documents")).status_code == 403
    async with client_for(factory=factory, principal=owner) as client:
        assert (
            await client.post(
                f"/api/web/platform/saas-payments/{payment}/documents", json={}
            )
        ).status_code == 403
    async with client_for(factory=factory, principal=issuer) as client:
        issued = await client.post(
            f"/api/web/platform/saas-payments/{payment}/documents", json={}
        )
        assert issued.status_code == 200, issued.text
        document = issued.json()
        assert document["content"]["synthetic"] is True and document["state"] == "valid"
        assert (
            "/verify-saas-document?locale=fr#" in document["verification_url"]
            and "<svg" in document["svg"]
        )
        assert (
            await client.post(
                f"/api/web/platform/saas-documents/{document['id']}/invalidate",
                json={"confirmed": True, "reason": "Issuer lacks invalidation grant"},
            )
        ).status_code == 403
    async with client_for(factory=factory, principal=owner) as client:
        summary = await client.get(
            f"/api/web/organizations/{organization}/restaurants/{restaurant}/saas-payments?payment_id={payment}"
        )
        assert summary.status_code == 200 and [row["id"] for row in summary.json()] == [
            payment
        ]
        owned = await client.get(
            f"/api/web/organizations/{organization}/restaurants/{restaurant}/saas-payments/{payment}/documents?locale=ar"
        )
        assert owned.status_code == 200 and owned.json()[0]["id"] == document["id"]
        assert "locale=ar" in owned.json()[0]["verification_url"]


# ==============================================
# CONCURRENT IDEMPOTENT ISSUANCE AND TENANT ISOLATION
# Serialize actual requests on the payment rather than relying on browser disablement.
# ==============================================


@pytest.mark.asyncio
async def test_concurrent_emission_is_single_and_owned(
    factory: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two HTTP emissions commit one version/event; another company cannot consult it."""
    monkeypatch.setattr(settings, "MANUAL_CCP_ENABLED", True)
    _, organization, owner, restaurant, payment = await pending_offer(factory=factory)
    foreign, _, _, _, _ = await pending_offer(factory=factory)
    await settle(factory=factory, owner=owner, payment=payment)
    issuer = await reviewer(factory=factory, permission="subscriptions.documents.issue")
    async with client_for(factory=factory, principal=issuer) as client:
        first, second = await asyncio.gather(
            *(
                client.post(
                    f"/api/web/platform/saas-payments/{payment}/documents", json={}
                )
                for _ in range(2)
            )
        )
        assert first.status_code == second.status_code == 200
        assert first.json()["id"] == second.json()["id"]
    async with factory() as observer:
        assert (
            await observer.scalar(
                text("SELECT count(*) FROM subscription_documents WHERE payment_id=:p"),
                {"p": payment},
            )
            == 1
        )
        assert (
            await observer.scalar(
                text(
                    "SELECT count(*) FROM subscription_document_events WHERE document_id=:d AND event='issued'"
                ),
                {"d": first.json()["id"]},
            )
            == 1
        )
    async with client_for(factory=factory, principal=foreign) as client:
        assert (
            await client.get(
                f"/api/web/organizations/{organization}/restaurants/{restaurant}/saas-payments/{payment}/documents"
            )
        ).status_code == 403


# ==============================================
# INDEPENDENT INVALIDATION AND REPLACEMENT LINEAGE
# Keep funds, service dates, original document and pricing unchanged after the validity decision.
# ==============================================


@pytest.mark.asyncio
async def test_invalidation_preserves_finances_and_original(
    factory: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Invalidate with its own grant, verify minimal public output, then issue one linked replacement."""
    monkeypatch.setattr(settings, "MANUAL_CCP_ENABLED", True)
    _, _, owner, _, payment = await pending_offer(factory=factory)
    await settle(factory=factory, owner=owner, payment=payment)
    issuer = await reviewer(factory=factory, permission="subscriptions.documents.issue")
    invalidator = await reviewer(
        factory=factory, permission="subscriptions.documents.invalidate"
    )
    async with client_for(factory=factory, principal=issuer) as client:
        response = await client.post(
            f"/api/web/platform/saas-payments/{payment}/documents", json={}
        )
        assert response.status_code == 200
        document = response.json()
    async with factory() as observer:
        before = await observer.scalar(
            text(
                "SELECT to_jsonb(p)::text || to_jsonb(s)::text || to_jsonb(h)::text FROM payments p JOIN subscriptions s ON s.id=p.subscription_id JOIN subscription_pricing_snapshots h ON h.subscription_id=s.id WHERE p.id=:p"
            ),
            {"p": payment},
        )
    async with client_for(factory=factory, principal=invalidator) as client:
        assert (
            await client.post(
                f"/api/web/platform/saas-payments/{payment}/documents", json={}
            )
        ).status_code == 403
        queue = await client.get("/api/web/platform/saas-documents")
        assert queue.status_code == 200 and all(
            row["documents"] for row in queue.json()
        )
        route = f"/api/web/platform/saas-documents/{document['id']}/invalidate"
        assert (
            await client.post(route, json={"confirmed": False, "reason": "Test reason"})
        ).status_code == 422
        assert (
            await client.post(route, json={"confirmed": True, "reason": "   "})
        ).status_code == 422
        data = {"confirmed": True, "reason": "Fictitious documentary correction"}
        first = await client.post(route, json=data)
        repeated = await client.post(route, json=data)
        assert (
            first.status_code == repeated.status_code == 200
            and first.json()["state"] == "invalidated"
        )
        verified = (
            await client.post(
                "/api/web/saas-documents/verify",
                json={"reference": document["reference"]},
            )
        ).json()
        assert set(verified) == {"reference", "issuer", "issued_at", "state"}
        assert verified["state"] == "invalidated"
        assert (
            await client.post(
                "/api/web/saas-documents/verify", json={"reference": "A" * 43}
            )
        ).json() == {"state": "unknown"}
    async with client_for(factory=factory, principal=issuer) as client:
        replacement = await client.post(
            f"/api/web/platform/saas-payments/{payment}/documents",
            json={"replaces_id": document["id"]},
        )
        assert replacement.status_code == 200
        assert (
            replacement.json()["version"] == 2
            and replacement.json()["replaces_id"] == document["id"]
        )
        assert replacement.json()["content"] == document["content"]
        assert (
            await client.post(
                f"/api/web/platform/saas-payments/{payment}/documents",
                json={"replaces_id": document["id"]},
            )
        ).json()["id"] == replacement.json()["id"]
    async with factory() as observer:
        after = await observer.scalar(
            text(
                "SELECT to_jsonb(p)::text || to_jsonb(s)::text || to_jsonb(h)::text FROM payments p JOIN subscriptions s ON s.id=p.subscription_id JOIN subscription_pricing_snapshots h ON h.subscription_id=s.id WHERE p.id=:p"
            ),
            {"p": payment},
        )
        assert after == before
        assert (
            await observer.scalar(
                text(
                    "SELECT count(*) FROM subscription_document_events WHERE document_id=:d"
                ),
                {"d": document["id"]},
            )
            == 2
        )
        assert (
            await observer.scalar(
                text("SELECT content FROM subscription_documents WHERE id=:d"),
                {"d": document["id"]},
            )
            == document["content"]
        )


# ==============================================
# FUTURE PERIOD AND REAL ROLLBACK
# A controlled scheduled fixture tests representation; an interrupted caller transaction leaves no partial document.
# ==============================================


@pytest.mark.asyncio
async def test_scheduled_period_and_rollback(
    factory: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Preserve scheduled status, then inject a late error and inspect independent committed state."""
    monkeypatch.setattr(settings, "MANUAL_CCP_ENABLED", True)
    _, _, owner, _, payment = await pending_offer(factory=factory)
    # Keep a synthetic unpaid trial open so the actual settlement service schedules
    # purchased coverage after it; never rewrite an already purchased period.
    start = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=5)
    async with factory() as session, session.begin():
        await session.execute(
            text(
                "UPDATE subscriptions SET status='trial',starts_at=:start,expires_at=:end WHERE restaurant_id=(SELECT restaurant_id FROM payments WHERE id=:p) AND status='expired' AND plan_id=(SELECT id FROM subscription_plans WHERE code='trial')"
            ),
            {"p": payment, "start": start - timedelta(days=30), "end": start},
        )
    await settle(factory=factory, owner=owner, payment=payment)
    issuer = await reviewer(factory=factory, permission="subscriptions.documents.issue")
    with pytest.raises(RuntimeError, match="late_local_failure"):
        async with factory() as session, session.begin():
            document = await SubscriptionDocumentService(
                session=session, marker=os.environ["COUNTRY_BASE_TEST_MARKER"]
            ).issue(principal=issuer, payment_id=payment)
            assert document.content["period_status_at_issue"] == "scheduled"
            raise RuntimeError("late_local_failure")
    async with factory() as observer:
        assert (
            await observer.scalar(
                text("SELECT count(*) FROM subscription_documents WHERE payment_id=:p"),
                {"p": payment},
            )
            == 0
        )
        assert (
            await observer.scalar(
                text("SELECT status FROM payments WHERE id=:p"), {"p": payment}
            )
            == "paid"
        )
    async with client_for(factory=factory, principal=issuer) as client:
        document = (
            await client.post(
                f"/api/web/platform/saas-payments/{payment}/documents", json={}
            )
        ).json()
        assert document["content"]["period_status_at_issue"] == "scheduled"
    for statement in (
        "UPDATE subscription_documents SET version=99 WHERE id=:d",
        "DELETE FROM subscription_documents WHERE id=:d",
        "DELETE FROM subscription_document_events WHERE document_id=:d",
    ):
        with pytest.raises(IntegrityError, match="history_immutable"):
            async with factory() as session, session.begin():
                await session.execute(text(statement), {"d": document["id"]})
    invalidator = await reviewer(
        factory=factory, permission="subscriptions.documents.invalidate"
    )
    with pytest.raises(RuntimeError, match="late_invalidation_failure"):
        async with factory() as session, session.begin():
            await SubscriptionDocumentService(
                session=session, marker=os.environ["COUNTRY_BASE_TEST_MARKER"]
            ).invalidate(
                principal=invalidator,
                document_id=document["id"],
                reason="Rollback documentary decision",
                confirmed=True,
            )
            raise RuntimeError("late_invalidation_failure")
    async with factory() as observer:
        assert (
            await observer.scalar(
                text(
                    "SELECT count(*) FROM subscription_document_events WHERE document_id=:d AND event='invalidated'"
                ),
                {"d": document["id"]},
            )
            == 0
        )
    async with factory() as session, session.begin():
        await session.execute(
            text("DELETE FROM admins WHERE auth_subject=:s"), {"s": issuer.subject}
        )
    async with factory() as observer:
        assert (
            await observer.scalar(
                text("SELECT author_name FROM subscription_documents WHERE id=:d"),
                {"d": document["id"]},
            )
            == "Synthetic country reviewer"
        )


# ==============================================
# BOUNDED PUBLIC READER
# Invalid references do not disclose source existence and rate limiting does not depend on identity claims.
# ==============================================


@pytest.mark.asyncio
async def test_reader_is_bounded(factory: async_sessionmaker[AsyncSession]) -> None:
    """The thirty-first request is refused without returning a private document projection."""
    principal = await reviewer(factory=factory, permission="payments.review")
    async with client_for(factory=factory, principal=principal) as client:
        for _ in range(30):
            assert (
                await client.post(
                    "/api/web/saas-documents/verify", json={"reference": "invalid"}
                )
            ).json() == {"state": "unknown"}
        assert (
            await client.post(
                "/api/web/saas-documents/verify", json={"reference": "invalid"}
            )
        ).status_code == 429


# ==============================================
# VERIFIED CASH SOURCE WITHOUT BANK PROOF
# Reuse the real physical-collection service and retain the independent documentary grant.
# ==============================================


@pytest.mark.asyncio
async def test_cash_document_requires_real_collection(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    """Issue from cash only after separately authorized synthetic collection is committed."""
    _, _, _, _, payment = await pending_offer(factory=factory, method="cash")
    issuer = await reviewer(factory=factory, permission="subscriptions.documents.issue")
    collector = await reviewer(factory=factory, permission="payments.cash.collect")
    async with client_for(factory=factory, principal=issuer) as client:
        assert (
            await client.post(
                f"/api/web/platform/saas-payments/{payment}/documents", json={}
            )
        ).status_code == 409
    async with factory() as observer:
        amount = await observer.scalar(
            text("SELECT amount FROM payments WHERE id=:p"), {"p": payment}
        )
        admin = await observer.scalar(
            base_select(Admin)
            .with_only_columns(Admin.id)
            .where(Admin.auth_subject == collector.subject)
        )
    assert admin is not None
    await CashCollectionService(session_factory=factory).confirm(
        payment_id=payment,
        admin_id=admin,
        data=CashConfirmation(
            received_amount=amount,
            currency="DZD",
            collected_at=datetime.now(timezone.utc),
            receipt_reference="SYNTHETIC-CASH-" + uuid4().hex,
        ),
    )
    async with client_for(factory=factory, principal=issuer) as client:
        response = await client.post(
            f"/api/web/platform/saas-payments/{payment}/documents", json={}
        )
        assert (
            response.status_code == 200
            and Decimal(response.json()["content"]["amount"]) == amount
        )
    async with factory() as observer:
        assert (
            await observer.scalar(
                text("SELECT count(*) FROM cash_collections WHERE payment_id=:p"),
                {"p": payment},
            )
            == 1
        )
        assert (
            await observer.scalar(
                text(
                    "SELECT count(*) FROM manual_payment_receipts WHERE payment_id=:p"
                ),
                {"p": payment},
            )
            == 0
        )


# ==============================================
# FICTITIOUS DOCUMENT PRODUCTION REFUSAL
# A visual warning or administrative grant cannot substitute for the server-side environment gate.
# ==============================================


@pytest.mark.asyncio
async def test_production_rejects_fictitious_documents(
    factory: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reject an explicitly authorized issuer before any documentary write in production mode."""
    issuer = await reviewer(factory=factory, permission="subscriptions.documents.issue")
    monkeypatch.setattr(settings, "APP_ENV", "production")
    async with factory() as session, session.begin():
        with pytest.raises(
            ValueError, match="fictitious_enrollment_documents_local_only"
        ):
            await SubscriptionDocumentService(
                session=session, marker=os.environ["COUNTRY_BASE_TEST_MARKER"]
            ).issue(principal=issuer, payment_id=1)
