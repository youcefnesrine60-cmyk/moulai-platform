# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# COUNTRY-AWARE SAAS CHECKOUT REGRESSIONS
# Exercise the existing administration, checkout and transfer settlement services against an attested disposable O4 database.
# ==============================================

"""Only this test fixture advances synthetic service dates; no retained review history is fabricated or changed."""

from __future__ import annotations

# isort: split
# ==============================================
# REAL LOCAL SERVICE CONTRACTS
# Reuse the account-scoped enrollment fixtures and keep commercial test values inside this disposable cluster.
# ==============================================

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
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)
from test_billing_country_postgres import (
    accept_required,
    declaration,
    draft,
    reviewer,
)

from test_billing_country_postgres import factory as factory  # noqa: PLC0414  # isort: skip  # fmt: skip

from app.core.config import settings
from app.integration.identity import BrowserIdentity
from app.integration.saas_payment_routes import mount_saas_payment_routes
from app.models.admin import Admin
from app.models.billing_country import EnrollmentDocument
from app.models.restaurant import Restaurant
from app.models.subscription import Subscription
from app.repositories.subscription_queries import base_select
from app.schemas.billing_country import (
    CountryDeclaration,
    CountryReview,
)
from app.schemas.manual_payment import (
    ManualPaymentReview,
    ManualSubscriptionCheckout,
)
from app.schemas.saas_pricing import BasePriceCommand
from app.services.business import subscription_metrics
from app.services.business.billing_country import (
    BillingCountryService,
    validated_country_for_subscription,
)
from app.services.business.enrollment import EnrollmentService
from app.services.business.enrollment_documents import (
    document_digest,
    require_document_responses,
    respond_to_document,
)
from app.services.business.manual_payment_service import ManualPaymentService
from app.services.business.saas_pricing_admin import SaasPricingAdministration

from app.services.business.subscription_checkout_service import SubscriptionCheckoutService  # isort: skip  # fmt: skip
from app.services.business.tenant_foundation import tenant_unit_of_work

# ==============================================
# DEDICATED O4 CHECKOUT REHEARSAL
# Database cases run under the fresh O4 launcher, while pure contracts remain available to the general offline campaign.
# ==============================================

pytestmark = pytest.mark.country_rehearsal

# ==============================================
# EXISTING ADMINISTRATION EDITOR
# A country version replaces the scalar while retained calculations and the committed audit remain immutable.
# ==============================================


@pytest.mark.asyncio
async def test_existing_base_editor_publishes_country_version(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    """Exercise BasePriceCommand and the administration facade, then restore the disposable starting amount."""
    principal = await reviewer(
        factory=factory, permission="subscriptions.pricing.manage"
    )
    async with factory() as session:
        contexts = await SaasPricingAdministration(session=session).base_contexts(
            principal=principal
        )
        assert {"country_code": "DZ", "currency": "DZD"} in contexts
    async with factory() as session:
        before = await SaasPricingAdministration(session=session).current_base(
            principal=principal
        )
    async with factory() as session:
        after = await SaasPricingAdministration(session=session).change_base(
            principal=principal,
            command=BasePriceCommand(
                amount="3001",
                country_code="DZ",
                currency="DZD",
                expected_sha256=before["sha256"],
                effective="on_commit",
                reason="DISPOSABLE TEST VALUE — NOT COMMERCIAL",
            ),
        )
    assert after["revision"] != before["revision"]
    assert after["country_code"] == "DZ" and after["amount"] == "3001.00"
    async with factory() as session:
        history = await SaasPricingAdministration(session=session).history(
            principal=principal, resource="saas_base", identifier=1
        )
        assert any(row["action"] == "pricing.base.country.change" for row in history)
    async with factory() as session:
        await SaasPricingAdministration(session=session).change_base(
            principal=principal,
            command=BasePriceCommand(
                amount=before["amount"],
                country_code="DZ",
                currency="DZD",
                expected_sha256=after["sha256"],
                effective="on_commit",
                reason="Restore disposable original amount",
            ),
        )


# ==============================================
# UNIQUE COUNTRY-AWARE TRANSFER ACTIVATION
# The boundary snapshot is collected from actual empty test tables; no historical metrics are substituted in a retained database.
# ==============================================


@pytest.mark.asyncio
async def test_country_checkout_and_manual_activation_are_single(
    factory: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Upload alone keeps payment pending; repeated verified review creates one service period and one entitlement set."""
    principal, organization = await draft(factory=factory)
    await accept_required(factory=factory, principal=principal)
    state = await declaration(
        factory=factory, principal=principal, organization=organization
    )
    authorized = await reviewer(
        factory=factory, permission="tenant.billing_country.manage"
    )
    async with factory() as session, session.begin():
        await BillingCountryService(session=session).review(
            principal=authorized,
            request_id=state["requests"][0]["id"],
            data=CountryReview(
                decision="approve",
                expected_revision=state["revision"],
                justification="Fictitious proof review",
                evidence_checked=True,
                same_legal_entity=True,
            ),
        )
        result = await EnrollmentService(
            session=session, marker=os.environ["COUNTRY_BASE_TEST_MARKER"]
        ).finalize(principal=principal)
    restaurant_id = result["restaurant_id"]
    async with factory() as session, session.begin():
        restaurant = await session.get(Restaurant, restaurant_id)
        trial = await session.scalar(
            base_select(Subscription).where(Subscription.restaurant_id == restaurant_id)
        )
        assert restaurant is not None and trial is not None
        owner_id = restaurant.owner_id
        end = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=1)
        trial.starts_at = end - timedelta(days=30)
        trial.expires_at = end
        await subscription_metrics.capture_active_month(
            session=session,
            owner_id=owner_id,
            restaurant_id=restaurant_id,
            source=trial,
            now=end,
        )
        trial.status = "expired"
        plan_id = await session.scalar(
            text("SELECT id FROM subscription_plans WHERE code='basic'")
        )
    monkeypatch.setattr(settings, "MANUAL_CCP_ENABLED", True)
    data = ManualSubscriptionCheckout(
        restaurant_id=restaurant_id,
        plan_id=plan_id,
        payment_method="ccp",
        currency="DZD",
        billing_cycle="monthly",
    )
    async with factory() as session, session.begin():
        invoice = await SubscriptionCheckoutService(session=session).create(
            owner_id=owner_id, data=data
        )
    async with factory() as session, session.begin():
        repeated = await SubscriptionCheckoutService(session=session).create(
            owner_id=owner_id, data=data
        )
        assert repeated.id == invoice.id
    async with factory() as session:
        assert (
            await session.scalar(
                text("SELECT status FROM payments WHERE id=:id"), {"id": invoice.id}
            )
            == "pending"
        )
        assert (
            await session.scalar(
                text("SELECT status FROM subscriptions WHERE id=:id"),
                {"id": invoice.subscription_id},
            )
            == "pending"
        )
    reference = "LOCAL-FAKE-TRANSFER-" + uuid4().hex
    async with factory() as session, session.begin():
        await ManualPaymentService(session=session).submit_receipt(
            payment_id=invoice.id,
            owner_id=owner_id,
            transaction_reference=reference,
            content=b"%PDF-1.4\nFICTITIOUS BANK RECEIPT "
            + reference.encode()
            + b"\n%%EOF",
            media_type="application/pdf",
        )
    payment_reviewer = await reviewer(factory=factory, permission="payments.review")

    # ==============================================
    # REAL HTTP QUEUE WITH MULTIPLE PERSISTED PRICING RECORDS
    # A receipt must occur once even when unrelated subscriptions and snapshots exist.
    # ==============================================

    app = FastAPI()

    # ==============================================
    # INJECTED TEST IDENTITY
    # Signature verification is outside this route test; database authority stays real.
    # ==============================================

    async def queue_identity() -> BrowserIdentity:
        """Supply the test principal; the actual route still checks its database permission."""
        return BrowserIdentity(
            principal=payment_reviewer,
            name="Disposable reviewer",
            access_token="OFFLINE-NO-PROVIDER",
        )

    # ==============================================
    # INDEPENDENT DATABASE SESSION
    # The HTTP request cannot inherit an external rollback-only test transaction.
    # ==============================================

    async def queue_sessions() -> AsyncIterator[AsyncSession]:
        """Observe committed checkout data from independent real sessions."""
        async with factory() as queue_session:
            yield queue_session

    mount_saas_payment_routes(
        app=app,
        identity_dep=Depends(queue_identity),
        session_dep=Depends(queue_sessions),
    )
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://offline-route"
    ) as client:
        response = await client.get("/api/web/platform/saas-payments")
        assert response.status_code == 200
        queue = response.json()
        identifiers = [record["id"] for record in queue]
        assert len(identifiers) == len(set(identifiers))
        assert identifiers.count(invoice.id) == 1
        entry = next(record for record in queue if record["id"] == invoice.id)
        assert entry["currency"] == "DZD"
        assert entry["status"] == "pending"
        assert entry["receipt_status"] == "pending"
        assert "parameters" not in entry and "pricing" not in entry

    async with factory() as session:
        reviewer_id = await session.scalar(
            base_select(Admin)
            .with_only_columns(Admin.id)
            .where(Admin.auth_subject == payment_reviewer.subject)
        )
    review = ManualPaymentReview(
        decision="approve",
        funds_received=True,
        bank_transaction_reference=reference,
        received_amount=Decimal(str(invoice.amount)),
        received_currency="DZD",
        note="Synthetic local funds verification; no bank operation",
    )
    for _attempt in range(2):
        async with factory() as session, session.begin():
            receipt = await ManualPaymentService(session=session).review(
                payment_id=invoice.id, admin_id=reviewer_id, data=review
            )
            assert receipt.review_status == "approved"
    async with factory() as session:
        assert (
            await session.scalar(
                text("SELECT status FROM payments WHERE id=:id"), {"id": invoice.id}
            )
            == "paid"
        )
        assert (
            await session.scalar(
                text(
                    "SELECT count(*) FROM subscriptions WHERE restaurant_id=:id AND status='active'"
                ),
                {"id": restaurant_id},
            )
            == 1
        )
        assert (
            await session.scalar(
                text(
                    "SELECT count(*) FROM subscription_features WHERE subscription_id=:id"
                ),
                {"id": invoice.subscription_id},
            )
            == 6
        )


# ==============================================
# OBSOLETE DOCUMENTS DO NOT TRANSFER ACCEPTANCE
# Retire a test version without rewriting its content or the exact old account response.
# ==============================================


@pytest.mark.asyncio
async def test_retired_document_requires_new_acceptance(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    """Keep the old accepted version immutable while rejecting its reuse for the newly published terms."""
    principal, _organization = await draft(factory=factory)
    await accept_required(factory=factory, principal=principal)
    marker = os.environ["COUNTRY_BASE_TEST_MARKER"]
    async with factory() as session, session.begin():
        old = await session.scalar(
            base_select(EnrollmentDocument)
            .where(
                EnrollmentDocument.purpose == "test-contract",
                EnrollmentDocument.retired_at.is_(None),
            )
            .with_for_update()
        )
        assert old is not None
        old_id, old_version, old_sha = old.id, old.version, old.sha256
        old.retired_at = datetime.now(timezone.utc)
        contents = {
            locale: str(content).replace(old.version, "LOCAL-TEST-20261108-v2")
            for locale, content in old.contents.items()
        }
        await session.flush()
        session.add(
            EnrollmentDocument(
                purpose=old.purpose,
                version="LOCAL-TEST-20261108-v2",
                response_kind=old.response_kind,
                contents=contents,
                sha256=document_digest(contents=contents),
                required=True,
                synthetic=True,
                published_at=datetime.now(timezone.utc),
            )
        )
    async with factory() as session:
        with pytest.raises(ValueError, match="document_version_unavailable"):
            async with session.begin():
                await respond_to_document(
                    session=session,
                    principal=principal,
                    marker=marker,
                    document_id=old_id,
                    version=old_version,
                    sha256=old_sha,
                    locale="fr",
                    action="accepted",
                )
    async with factory() as session:
        with pytest.raises(ValueError, match="current_acceptance_required"):
            async with session.begin():
                await require_document_responses(
                    session=session, principal=principal, marker=marker
                )
    await accept_required(factory=factory, principal=principal)
    async with factory() as session, session.begin():
        await require_document_responses(
            session=session, principal=principal, marker=marker
        )
        assert (
            await session.scalar(
                text(
                    "SELECT count(*) FROM enrollment_document_events e JOIN identities i ON i.id=e.identity_id WHERE i.subject=:subject AND e.document_id=:document AND event='accepted'"
                ),
                {"subject": principal.subject, "document": old_id},
            )
            == 1
        )


# ==============================================
# OUTER ENROLLMENT FAILURE AFTER TRIAL CREATION
# A successfully released inner registration savepoint must still roll back when tenant attachment fails.
# ==============================================


@pytest.mark.asyncio
async def test_enrollment_attachment_failure_leaves_no_partial_graph(
    factory: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Check persisted owner, restaurant, trial, rights and original dossier from an independent post-failure session."""
    import app.services.business.enrollment as enrollment_module
    from app.models.tenant.schema import OrganizationMembership

    principal, organization = await draft(factory=factory)
    await accept_required(factory=factory, principal=principal)
    state = await declaration(
        factory=factory, principal=principal, organization=organization
    )
    authorized = await reviewer(
        factory=factory, permission="tenant.billing_country.manage"
    )
    async with factory() as session, session.begin():
        await BillingCountryService(session=session).review(
            principal=authorized,
            request_id=state["requests"][0]["id"],
            data=CountryReview(
                decision="approve",
                expected_revision=state["revision"],
                justification="Fictitious local verification",
                evidence_checked=True,
                same_legal_entity=True,
            ),
        )

    # ==============================================
    # DELIBERATE LATE LOCAL FAILURE
    # Fail only after the reused registration service has staged its complete trial graph.
    # ==============================================

    def reject_attachment(**_fields: object) -> OrganizationMembership:
        """Inject a test failure at tenant attachment without changing the actual registration service."""
        raise ValueError("intentional_enrollment_attachment_failure")

    monkeypatch.setattr(enrollment_module, "OrganizationMembership", reject_attachment)
    async with factory() as session:
        with pytest.raises(
            ValueError, match="intentional_enrollment_attachment_failure"
        ):
            async with session.begin():
                await EnrollmentService(
                    session=session, marker=os.environ["COUNTRY_BASE_TEST_MARKER"]
                ).finalize(principal=principal)
    async with factory() as observer:
        assert (
            await observer.scalar(
                text("SELECT count(*) FROM owners WHERE auth_subject=:subject"),
                {"subject": principal.subject},
            )
            == 0
        )
        assert (
            await observer.scalar(
                text(
                    "SELECT count(*) FROM restaurants WHERE organization_id=:organization OR name='Local test restaurant' AND owner_id IN (SELECT id FROM owners WHERE auth_subject=:subject)"
                ),
                {"organization": organization, "subject": principal.subject},
            )
            == 0
        )
        assert (
            await observer.scalar(
                text(
                    "SELECT status FROM enrollment_dossiers WHERE organization_id=:organization"
                ),
                {"organization": organization},
            )
            == "draft"
        )


# ==============================================
# COUNTRY CHANGE AT THE NEXT COVERAGE BOUNDARY
# A reviewed new country must not rewrite current service or imply that its currency pair is commercially configured.
# ==============================================


@pytest.mark.asyncio
async def test_country_change_preserves_current_trial_and_requires_exact_pair(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    """Reject missing evidence, retain both decisions and refuse checkout without the new country's explicit tariff."""
    principal, organization = await draft(factory=factory)
    await accept_required(factory=factory, principal=principal)
    state = await declaration(
        factory=factory, principal=principal, organization=organization
    )
    authorized = await reviewer(
        factory=factory, permission="tenant.billing_country.manage"
    )
    async with factory() as session, session.begin():
        await BillingCountryService(session=session).review(
            principal=authorized,
            request_id=state["requests"][0]["id"],
            data=CountryReview(
                decision="approve",
                expected_revision=state["revision"],
                justification="Fictitious initial review",
                evidence_checked=True,
                same_legal_entity=True,
            ),
        )
        completed = await EnrollmentService(
            session=session, marker=os.environ["COUNTRY_BASE_TEST_MARKER"]
        ).finalize(principal=principal)
    restaurant = int(completed["restaurant_id"])
    async with factory() as observer:
        before = (
            (
                await observer.execute(
                    text(
                        "SELECT id,owner_id,status,starts_at,expires_at,amount,currency FROM subscriptions WHERE restaurant_id=:id"
                    ),
                    {"id": restaurant},
                )
            )
            .mappings()
            .one()
        )
        before = dict(before)
        state = await BillingCountryService(session=observer).view(
            organization_id=organization
        )
    change = CountryDeclaration(
        declared_country="FR",
        legal_entity_reference="LOCAL-FAKE-" + principal.subject,
        evidence_id=uuid4().hex,
        reason="Fictitious change of establishment, same entity",
        expected_revision=state["revision"],
        idempotency_key=uuid4().hex,
    )
    async with factory() as session:
        with pytest.raises(ValueError, match="billing_country_proof_required"):
            async with tenant_unit_of_work(session=session):
                await BillingCountryService(session=session).declare(
                    principal=principal, organization_id=organization, data=change
                )
    async with factory() as session, tenant_unit_of_work(session=session):
        service = BillingCountryService(session=session)
        proof = await service.store_evidence(
            principal=principal,
            organization_id=organization,
            content=b"%PDF-1.4\nLOCAL-FAKE CHANGED ESTABLISHMENT\n%%EOF",
            filename="LOCAL-FAKE-country-change.pdf",
            media_type="application/pdf",
            synthetic=True,
        )
        state = await service.declare(
            principal=principal,
            organization_id=organization,
            data=change.model_copy(update={"evidence_id": proof}),
        )
    async with factory() as session, session.begin():
        state = await BillingCountryService(session=session).review(
            principal=authorized,
            request_id=state["requests"][0]["id"],
            data=CountryReview(
                decision="approve",
                expected_revision=state["revision"],
                justification="Fictitious same-entity country review",
                evidence_checked=True,
                same_legal_entity=True,
            ),
        )
        assert state["validated_country"] == "FR" and state["pending_country"] is None
        assert state["pending_effective_at"] is None
        country, _decision, starts = await validated_country_for_subscription(
            session=session,
            owner_id=before["owner_id"],
            restaurant_id=restaurant,
            currency=None,
        )
        assert country == "FR" and starts.replace(tzinfo=None) == before["expires_at"]
    async with factory() as session:
        with pytest.raises(ValueError, match="country_base_missing"):
            async with session.begin():
                await validated_country_for_subscription(
                    session=session,
                    owner_id=before["owner_id"],
                    restaurant_id=restaurant,
                    currency="DZD",
                )
    async with factory() as observer:
        after = (
            (
                await observer.execute(
                    text(
                        "SELECT id,owner_id,status,starts_at,expires_at,amount,currency FROM subscriptions WHERE restaurant_id=:id"
                    ),
                    {"id": restaurant},
                )
            )
            .mappings()
            .one()
        )
        assert dict(after) == before
        assert (
            await observer.scalar(
                text(
                    "SELECT count(*) FROM billing_country_decisions WHERE organization_id=:id"
                ),
                {"id": organization},
            )
            == 2
        )
