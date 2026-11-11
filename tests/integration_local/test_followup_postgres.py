# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================


# ==============================================
# REAL O4 PRICING AND REPLACEMENT REGRESSIONS
# Inspect committed rows through independent sessions on the marked disposable database.
# ==============================================

"""Synthetic accounts, tariffs and service clocks belong exclusively to the O4 test cluster."""

from __future__ import annotations

# isort: split
# ==============================================
# REAL TRANSACTION AND DOMAIN CONTRACTS
# Reuse the attested enrollment fixture and server pricing without mocks of persistence.
# ==============================================

import asyncio
import os
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from decimal import Decimal
from typing import Literal
from uuid import uuid4

import pytest
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
from app.core.security.oidc import OIDCPrincipal
from app.models.payment import Payment
from app.models.restaurant import Restaurant
from app.models.subscription import Subscription
from app.models.subscription_pricing import SubscriptionPricingSnapshot
from app.repositories.subscription_queries import base_select
from app.schemas.billing_country import (
    CountryDeclaration,
    CountryReview,
)
from app.schemas.manual_payment import ManualSubscriptionCheckout
from app.schemas.registration_request import RegistrationRequestResponse
from app.schemas.saas_pricing import BasePriceCommand
from app.services.business import subscription_metrics
from app.services.business.billing_country import (
    BillingCountryService,
    validated_country_for_subscription,
)
from app.services.business.enrollment import EnrollmentService
from app.services.business.manual_payment_service import ManualPaymentService
from app.services.business.payment_service import PaymentService
from app.services.business.pricing_service import calculate_subscription_pricing

from app.services.business.registration_request_service import RegistrationRequestService  # isort: skip  # fmt: skip
from app.services.business.saas_pricing_admin import SaasPricingAdministration
from app.services.business.tenant_foundation import tenant_unit_of_work

from app.services.business.subscription_checkout_service import SubscriptionCheckoutService  # isort: skip  # fmt: skip
from app.services.business.subscription_requote import replace_offer

pytestmark = pytest.mark.country_rehearsal

# ==============================================
# AUTHENTICATED OWNED PENDING OFFER
# Expire only this synthetic trial after preserving its actual thirty-day empty metrics.
# ==============================================


async def pending_offer(
    *,
    factory: async_sessionmaker[AsyncSession],
    extra_site: bool = False,
    method: Literal["ccp", "baridimob", "cash"] = "ccp",
) -> tuple[OIDCPrincipal, int, int, int, int]:
    """Commit one dossier, validated country and pending invoice without funds or real customers."""
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
                justification="Fictitious evidence checked",
                evidence_checked=True,
                same_legal_entity=True,
            ),
        )
        original_approve = RegistrationRequestService.approve

        # ==============================================
        # MULTI-SITE FIXTURE BEFORE ENFORCEMENT
        # Stage the second site while the real company is still draft; never disable a trigger.
        # ==============================================

        async def approve_with_site(
            self: RegistrationRequestService,
            *,
            request_id: int,
            owner_id: int | None = None,
        ) -> RegistrationRequestResponse:
            """Run actual approval, then construct only the requested synthetic extra site."""
            response = await original_approve(
                self, request_id=request_id, owner_id=owner_id
            )
            if extra_site:
                await self.session.execute(
                    text(
                        "INSERT INTO restaurants(owner_id,name,type,phone,wilaya,organization_id) SELECT owner_id,'SECOND SYNTHETIC SITE',type,phone,wilaya,:org FROM restaurants WHERE owner_id=:owner ORDER BY id DESC LIMIT 1"
                    ),
                    {"org": organization, "owner": response.owner_id},
                )
            return response

        with pytest.MonkeyPatch.context() as fixture_patch:
            fixture_patch.setattr(
                RegistrationRequestService, "approve", approve_with_site
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
    async with factory() as session, session.begin():
        invoice = await SubscriptionCheckoutService(session=session).create(
            owner_id=owner_id,
            data=ManualSubscriptionCheckout(
                restaurant_id=restaurant_id,
                plan_id=plan_id,
                payment_method=method,
                currency="DZD",
                billing_cycle="monthly",
            ),
        )
    return principal, organization, owner_id, restaurant_id, invoice.id


# ==============================================
# IMMUTABLE SUPERSESSION, CONCURRENCY AND ROLLBACK
# Preview changed tariffs; one explicit confirmation creates exactly one successor.
# ==============================================


@pytest.mark.asyncio
async def test_replacement_is_explicit_single_and_preserves_history(
    *, factory: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stale or interrupted review cannot withdraw the original pending offer."""
    monkeypatch.setattr(settings, "MANUAL_CCP_ENABLED", True)
    principal, _organization, owner, restaurant, payment = await pending_offer(
        factory=factory
    )
    admin = await reviewer(factory=factory, permission="subscriptions.pricing.manage")
    async with factory() as session:
        before = await SaasPricingAdministration(session=session).current_base(
            principal=admin
        )
        original = await session.scalar(
            base_select(SubscriptionPricingSnapshot)
            .join(
                Payment,
                Payment.subscription_id == SubscriptionPricingSnapshot.subscription_id,
            )
            .where(Payment.id == payment)
        )
        frozen = (original.pricing, original.parameters)
    async with factory() as session:
        changed = await SaasPricingAdministration(session=session).change_base(
            principal=admin,
            command=BasePriceCommand(
                amount=str(Decimal(before["amount"]) + 1),
                country_code="DZ",
                currency="DZD",
                expected_sha256=before["sha256"],
                effective="on_commit",
                reason="DISPOSABLE TEST TARIFF ONLY",
            ),
        )
    try:
        args = {
            "owner_id": owner,
            "restaurant_id": restaurant,
            "payment_id": payment,
            "currency": "DZD",
            "principal": principal,
        }
        async with factory() as session, session.begin():
            preview = await replace_offer(session=session, **args)
        async with factory() as session:
            assert (
                await session.scalar(
                    text("SELECT status FROM payments WHERE id=:p"), {"p": payment}
                )
                == "pending"
            )
        with pytest.raises(ValueError, match="preview_changed"):
            async with factory() as session, session.begin():
                await replace_offer(session=session, approval="0" * 64, **args)

        # ==============================================
        # FAILURE AFTER THE SUCCESSOR SUBSCRIPTION WAS STAGED
        # The exception must restore the old invoice and remove every new partial row.
        # ==============================================

        async def reject_payment(*_args: object, **_kwargs: object) -> None:
            """Inject a payment failure after actual pending-subscription writes."""
            raise ValueError("intentional_requote_payment_failure")

        with monkeypatch.context() as failure:
            failure.setattr(PaymentService, "create_payment", reject_payment)
            with pytest.raises(ValueError, match="intentional_requote_payment_failure"):
                async with factory() as session, session.begin():
                    await replace_offer(
                        session=session, approval=preview["approval"], **args
                    )
        async with factory() as observer:
            assert (
                await observer.scalar(
                    text("SELECT status FROM payments WHERE id=:p"), {"p": payment}
                )
                == "pending"
            )
            assert (
                await observer.scalar(
                    text(
                        "SELECT count(*) FROM subscriptions WHERE restaurant_id=:r AND status='pending'"
                    ),
                    {"r": restaurant},
                )
                == 1
            )

        async def confirm() -> dict[str, object]:
            """Use independent transactions, as two concurrent HTTP submissions would."""
            async with factory() as session, session.begin():
                return await replace_offer(
                    session=session, approval=preview["approval"], **args
                )

        first, second = await asyncio.gather(confirm(), confirm())
        assert first["payment"]["id"] == second["payment"]["id"]
        assert sorted([first["reused"], second["reused"]]) == [False, True]
        async with factory() as session:
            retained = await session.get(SubscriptionPricingSnapshot, original.id)
            assert (retained.pricing, retained.parameters) == frozen
            assert (
                await session.scalar(
                    text("SELECT status FROM payments WHERE id=:p"), {"p": payment}
                )
                == "cancelled"
            )
            assert (
                await session.scalar(
                    text(
                        "SELECT count(*) FROM subscriptions WHERE restaurant_id=:r AND status='pending'"
                    ),
                    {"r": restaurant},
                )
                == 1
            )
            assert (
                await session.scalar(
                    text(
                        "SELECT count(*) FROM manual_payment_receipts WHERE payment_id=:p"
                    ),
                    {"p": payment},
                )
                == 0
            )
    finally:
        async with factory() as session:
            await SaasPricingAdministration(session=session).change_base(
                principal=admin,
                command=BasePriceCommand(
                    amount=before["amount"],
                    country_code="DZ",
                    currency="DZD",
                    expected_sha256=changed["sha256"],
                    effective="on_commit",
                    reason="Restore disposable tariff",
                ),
            )


# ==============================================
# FINANCIAL EVIDENCE AND FOREIGN OWNERSHIP
# Even an unapproved receipt is never moved, deleted or silently cancelled.
# ==============================================


@pytest.mark.asyncio
async def test_receipt_and_foreign_owner_refuse_replacement(
    *, factory: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Observe the original records independently after each refused request."""
    monkeypatch.setattr(settings, "MANUAL_CCP_ENABLED", True)
    principal, _organization, owner, restaurant, payment = await pending_offer(
        factory=factory
    )
    reference = "LOCAL-REQUOTE-" + uuid4().hex
    async with factory() as session, session.begin():
        await ManualPaymentService(session=session).submit_receipt(
            payment_id=payment,
            owner_id=owner,
            transaction_reference=reference,
            content=b"%PDF-1.4\nFICTITIOUS REQUOTE RECEIPT "
            + reference.encode()
            + b"\n%%EOF",
            media_type="application/pdf",
        )
    for actor, error in [
        (owner, "financial_evidence"),
        (owner + 1000000, "unavailable"),
    ]:
        with pytest.raises(ValueError, match=error):
            async with factory() as session, session.begin():
                await replace_offer(
                    session=session,
                    owner_id=actor,
                    restaurant_id=restaurant,
                    payment_id=payment,
                    currency="DZD",
                    principal=principal,
                )
    async with factory() as session:
        assert (
            await session.scalar(
                text("SELECT status FROM payments WHERE id=:p"), {"p": payment}
            )
            == "pending"
        )
        assert (
            await session.scalar(
                text(
                    "SELECT count(*) FROM manual_payment_receipts WHERE payment_id=:p"
                ),
                {"p": payment},
            )
            == 1
        )


# ==============================================
# COMPANY DECISION AND INDEPENDENT SUBSCRIPTION DEADLINES
# A validated company country applies at each renewal without changing committed periods.
# ==============================================


@pytest.mark.asyncio
async def test_country_transition_two_expiries_retains_periods(
    *, factory: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    """One decision selects the new context for two renewals; unavailable tariffs still refuse finalization."""
    monkeypatch.setattr(settings, "MANUAL_CCP_ENABLED", True)
    principal, organization, owner, restaurant, _payment = await pending_offer(
        factory=factory, extra_site=True
    )
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    async with factory() as session, tenant_unit_of_work(session=session):
        # Two actual subscriptions, not manufactured per-table or per-branch deadlines.
        ids = []
        restaurants = [restaurant]
        second = await session.scalar(
            text("SELECT id FROM restaurants WHERE organization_id=:org AND id<>:r"),
            {"org": organization, "r": restaurant},
        )
        restaurants.append(second)
        for site, days in zip(restaurants, (10, 25), strict=True):
            result = await session.execute(
                text(
                    "INSERT INTO subscriptions(owner_id,restaurant_id,plan_id,billing_cycle,amount,currency,status,starts_at,expires_at,billing_country_code) SELECT owner_id,:site,plan_id,'monthly',amount,'DZD','active',:start,:ending,'DZ' FROM subscriptions WHERE restaurant_id=:r ORDER BY id DESC LIMIT 1 RETURNING id"
                ),
                {
                    "r": restaurant,
                    "site": site,
                    "start": now - timedelta(days=5),
                    "ending": now + timedelta(days=days),
                },
            )
            ids.append(result.scalar_one())
        frozen = (
            await session.execute(
                text(
                    "SELECT id,amount,currency,starts_at,expires_at,billing_country_code FROM subscriptions WHERE id=ANY(:ids) ORDER BY id"
                ),
                {"ids": ids},
            )
        ).all()
        service = BillingCountryService(session=session)
        state = await service.view(organization_id=organization)
        evidence = await service.store_evidence(
            organization_id=organization,
            principal=principal,
            content=b"%PDF-1.4\nFICTITIOUS COUNTRY CHANGE\n%%EOF",
            media_type="application/pdf",
            filename="fictitious.pdf",
            synthetic=True,
        )
        await service.declare(
            organization_id=organization,
            principal=principal,
            data=CountryDeclaration(
                declared_country="FR",
                legal_entity_reference=state["requests"][0]["legal_entity_reference"],
                reason="Synthetic establishment-country test",
                evidence_id=evidence,
                expected_revision=state["revision"],
                idempotency_key=uuid4().hex,
            ),
        )
    authorized = await reviewer(
        factory=factory, permission="tenant.billing_country.manage"
    )
    async with factory() as session, session.begin():
        service = BillingCountryService(session=session)
        state = await service.view(organization_id=organization)
        await service.review(
            principal=authorized,
            request_id=state["requests"][0]["id"],
            data=CountryReview(
                decision="approve",
                expected_revision=state["revision"],
                evidence_checked=True,
                same_legal_entity=True,
                justification="Fictitious same-entity proof reviewed",
            ),
        )
    async with factory() as session, session.begin():
        decisions = []
        for site, days in zip(restaurants, (10, 25), strict=True):
            country, decision, start = await validated_country_for_subscription(
                session=session, owner_id=owner, restaurant_id=site, currency=None
            )
            assert country == "FR" and start.replace(tzinfo=None) == now + timedelta(
                days=days
            )
            decisions.append(decision)
        assert decisions[0] == decisions[1]
        after = (
            await session.execute(
                text(
                    "SELECT id,amount,currency,starts_at,expires_at,billing_country_code FROM subscriptions WHERE id=ANY(:ids) ORDER BY id"
                ),
                {"ids": ids},
            )
        ).all()
        assert after == frozen
        with pytest.raises(ValueError, match="country_base_missing"):
            await validated_country_for_subscription(
                session=session,
                owner_id=owner,
                restaurant_id=restaurant,
                currency="EUR",
            )


# ==============================================
# FULL PRICING PIPELINE WITH A BASIS DISTINCT FROM B
# Additional branch charges enter the subtotal before one electronic adjustment.
# ==============================================


@pytest.mark.asyncio
async def test_payment_basis_in_real_country_pipeline(
    *, factory: async_sessionmaker[AsyncSession]
) -> None:
    """The pre-payment subtotal includes branch cost; the persisted B source remains unchanged."""
    async with factory() as session, session.begin():
        before = (
            await session.execute(
                text(
                    "SELECT id,amount,revision FROM subscription_base_prices ORDER BY id"
                )
            )
        ).all()
        plan = await session.scalar(
            text("SELECT id FROM subscription_plans WHERE code='basic'")
        )
        result = await calculate_subscription_pricing(
            session=session,
            plan_id=plan,
            billing_cycle="monthly",
            payment_method="electronic",
            restaurants_count=1,
            branches_count=2,
            years_with_platform=0,
            products_count=0,
            categories_count=0,
            monthly_orders=0,
            average_order_value=Decimal(0),
            currency="DZD",
            country_code="DZ",
            market="DZ",
        )
        assert result["final_price"] > Decimal(result["parameters"]["B"])
        assert result["payment_adjustment"] == result["final_price"] * Decimal("-0.02")
        assert result["parameters"]["payment_adjustment_rate"] == "-0.02"
        assert result["final_amount_due"] == (
            result["final_price"] * Decimal("0.98")
        ).quantize(Decimal("0.01"), rounding="ROUND_HALF_UP")
        assert (
            await session.execute(
                text(
                    "SELECT id,amount,revision FROM subscription_base_prices ORDER BY id"
                )
            )
        ).all() == before


# ==============================================
# REAL DATABASE CLOCK UNDER AN EXPLICIT SESSION TIMEZONE
# Check the same expression as the historical DDL without changing database-wide settings.
# ==============================================


@pytest.mark.asyncio
async def test_admin_timestamp_matches_database_default(
    *, factory: async_sessionmaker[AsyncSession]
) -> None:
    """Observe the committed timestamp from another session; no historical dates are converted."""
    from app.repositories.admin.admin_repo import AdminRepository

    principal = await reviewer(
        factory=factory, permission="tenant.billing_country.manage"
    )
    async with factory() as session, session.begin():
        await session.execute(text("SET LOCAL TIME ZONE 'Africa/Lagos'"))
        identifier = await session.scalar(
            text("SELECT id FROM admins WHERE auth_subject=:subject"),
            {"subject": principal.subject},
        )
        expected = await session.scalar(text("SELECT now()::timestamp"))
        session.info["defer_repository_commit"] = True
        try:
            await AdminRepository(session=session).update_admin(
                admin_id=identifier, full_name="Synthetic database-clock check"
            )
        finally:
            session.info.pop("defer_repository_commit", None)
    async with factory() as observer:
        assert (
            await observer.scalar(
                text("SELECT updated_at FROM admins WHERE id=:id"), {"id": identifier}
            )
            == expected
        )
