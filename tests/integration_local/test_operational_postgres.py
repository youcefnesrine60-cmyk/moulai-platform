# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# HISTORY AND FOOD SETTLEMENT POSTGRESQL REGRESSIONS
# Observe committed audit retention and pricing history from independent sessions on a fresh test cluster.
# ==============================================

"""Synthetic commercial fixtures are confined to a separately marked disposable cluster."""

from __future__ import annotations

# isort: split
# ==============================================
# ISOLATED TEST CONTRACTS
# No shared conftest, permanent database, identity provider or external transport is used.
# ==============================================

import asyncio
import json
import os
from collections.abc import AsyncIterator
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import (
    insert,
    select,
    text,
    update,
)
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.security.oidc import OIDCPrincipal
from app.core.security.tenant_types import TenantAccessDenied
from app.integration.config import IntegrationConfig
from app.integration.offers import (
    OfferInput,
    simulate_offer,
)
from app.integration.settlements import (
    SettlementInput,
    record_settlement,
)
from app.models.admin import Admin
from app.models.admin_log import AdminLog
from app.models.owner import Owner
from app.models.payment import Payment
from app.models.rbac import (
    Permission,
    Role,
    role_permissions,
)
from app.models.subscription import Subscription
from app.models.subscription_pricing import SubscriptionPricingSnapshot
from app.schemas.dining import JsonObject
from app.schemas.manual_payment import (
    ManualPaymentReview,
    ManualSubscriptionCheckout,
)
from app.schemas.payment import PaymentResponse
from app.schemas.saas_pricing import BasePriceCommand
from app.services.business import subscription_metrics
from app.services.business.dining.service import DiningUnit
from app.services.business.dining.values import DiningError
from app.services.business.manual_payment_service import ManualPaymentService
from app.services.business.pricing_service import base_breakdown
from app.services.business.saas_pricing_admin import SaasPricingAdministration
from app.services.business.subscription_checkout_service import (
    SubscriptionCheckoutService,  # fmt: skip
)
from test_support.subscription_fixtures import (
    put,
    seed_graph,
)
from tests.dining.test_invoices import invoicing_graph

# ==============================================
# DEDICATED O2 EXECUTION SCOPE
# Keep this older schema's database cases out of unrelated live or local profiles; only its attested disposable runner admits writes.
# ==============================================

pytestmark = pytest.mark.operational_rehearsal

# ==============================================
# EXISTING LOCAL PAYMENT REVIEW PATH
# Reuse the seeded permission rather than assuming a blank historical RBAC catalogue.
# ==============================================


async def settle_fixture(
    *, session: AsyncSession, owner_id: int, invoice: PaymentResponse
) -> None:
    """Record explicit synthetic bank evidence and validate it through the actual manual-payment service."""
    role = await put(
        session,
        Role,
        code="o1-bank-reviewer",
        name="Disposable reviewer",
        is_active=True,
    )
    permission = await session.scalar(
        select(Permission.id).where(Permission.code == "payments.review")
    )
    assert permission is not None
    await session.execute(
        insert(role_permissions).values(role_id=role, permission_id=permission)
    )
    admin = await put(
        session,
        Admin,
        chat_id=-820004,
        role_id=role,
        full_name="Disposable bank reviewer",
    )
    await session.commit()
    service = ManualPaymentService(session=session)
    await service.submit_receipt(
        payment_id=invoice.id,
        owner_id=owner_id,
        transaction_reference="O1-SYNTHETIC-NO-FUNDS",
        content=b"\x89PNG\r\n\x1a\nsynthetic",
        media_type="image/png",
    )
    await service.review(
        payment_id=invoice.id,
        admin_id=admin,
        data=ManualPaymentReview(
            decision="approve",
            funds_received=True,
            bank_transaction_reference="O1-SYNTHETIC-NO-FUNDS",
            received_amount=Decimal(str(invoice.amount)),
            received_currency="DZD",
            note="Disposable test ledger only; no actual funds",
        ),
    )


# ==============================================
# FRESH CLUSTER ADMISSION
# The launcher marks this instance for destructive synthetic testing and never makes it the active application.
# ==============================================


@pytest.fixture
async def factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Refuse the active integrated database even when a caller supplies its correct local credentials."""
    if os.environ.get("COUNTRY_BASE_TEST_PROFILE") == "operational-o2":
        url = make_url(os.environ["COUNTRY_BASE_TEST_URL"])
        assert (url.drivername, url.host, url.port, url.database, url.username) == (
            "postgresql+asyncpg",
            "127.0.0.1",
            55434,
            "moulai_base_rehearsal",
            "moulai_base_rehearsal",
        )
        marker = os.environ["COUNTRY_BASE_TEST_MARKER"]
        assert len(marker) == 32 and all(c in "0123456789abcdef" for c in marker)
        expected_comment = "moulai-country-base:" + marker
    else:
        directory = Path(os.environ["MOULAI_O1_TEST_INSTANCE"])
        assert (directory / "disposable-test-only").read_text(encoding="ascii") == "o1"
        active = json.loads(
            (directory.parent / "active.json").read_text(encoding="utf-8")
        )
        assert Path(active["directory"]).resolve() != directory.resolve()
        configuration = IntegrationConfig.load(directory=directory)
        url = make_url(configuration.database_url)
        expected_comment = "moulai-operational-local:" + configuration.instance_id
    engine = create_async_engine(url, hide_parameters=True, connect_args={"ssl": False})
    async with engine.connect() as connection:
        assert (
            await connection.scalar(
                text(
                    "SELECT shobj_description(oid,'pg_database') FROM pg_database WHERE datname=current_database()"
                )
            )
            == expected_comment
        )
        assert (
            await connection.scalar(text("SELECT version_num FROM alembic_version"))
            == "o220261108"
        )
    try:
        yield async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    finally:
        await engine.dispose()


# ==============================================
# ACCOUNT LIFECYCLE DOES NOT ERASE DECISIONS
# SQL and loaded ORM deletion must both retain the original actor and frozen audit contents.
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("deletion", ["sql", "orm"])
async def test_administrator_deactivation_and_deletion_retain_history(
    factory: async_sessionmaker[AsyncSession], deletion: str
) -> None:
    """Commit each stage and use a new session for every state assertion, without an outer rollback."""
    async with factory() as session, session.begin():
        admin = Admin(
            chat_id=-820001 if deletion == "sql" else -820002,
            full_name="Original local author",
            role="admin",
            is_active=True,
        )
        session.add(admin)
        await session.flush()
        audit = AdminLog(
            admin_id=admin.id,
            action="pricing.retention.proof",
            resource="saas_base",
            resource_id=1,
            details='{"decision":"original"}',
            timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        session.add(audit)
        await session.flush()
        identifier, actor = audit.id, admin.id
    async with factory() as session, session.begin():
        await session.execute(
            update(Admin)
            .where(Admin.id == actor)
            .values(is_active=False, full_name="Renamed inactive account")
        )
    async with factory() as observer:
        audit = await observer.get(AdminLog, identifier)
        assert audit is not None and audit.actor_admin_id == actor
        assert (
            audit.actor_name == "Original local author"
            and audit.details == '{"decision":"original"}'
        )
    async with factory() as session, session.begin():
        if deletion == "sql":
            await session.execute(
                text("DELETE FROM admins WHERE id=:id"), {"id": actor}
            )
        else:
            admin = await session.get(Admin, actor)
            assert admin is not None and len(admin.logs) == 1
            await session.delete(admin)
    async with factory() as observer:
        audit = await observer.get(AdminLog, identifier)
        assert audit is not None and audit.admin_id is None
        assert (
            audit.actor_admin_id == actor
            and audit.actor_name == "Original local author"
        )
        assert audit.details == '{"decision":"original"}'
    for sql in [
        "UPDATE admin_logs SET details='{}' WHERE id=:id",
        "DELETE FROM admin_logs WHERE id=:id",
        "TRUNCATE admin_logs",
    ]:
        async with factory() as session:
            with pytest.raises(IntegrityError):
                async with session.begin():
                    await session.execute(
                        text(sql), {"id": identifier} if ":id" in sql else {}
                    )
    async with factory() as observer:
        audit = await observer.get(AdminLog, identifier)
        assert audit is not None and audit.details == '{"decision":"original"}'


# ==============================================
# IMMEDIATE BASE AFFECTS NEW CALCULATIONS ONLY
# Verify actual checkout, reviewed settlement, retained quotation, running coverage and renewal recalculation.
# ==============================================


@pytest.mark.asyncio
async def test_base_change_preserves_paid_invoice_and_coverage_and_reprices_renewal(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    """Use explicit synthetic tariffs only here; no fixture is exported to the integrated application."""
    async with factory() as session:
        # This fixture owns a fresh marked cluster; its replacement grids are never exported.
        await session.execute(text("UPDATE branch_pricing SET active=false"))
        graph = await seed_graph(session)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        trial_id = await put(
            session,
            Subscription,
            owner_id=graph.owner,
            restaurant_id=graph.restaurant,
            plan_id=graph.plans["trial"],
            billing_cycle="trial",
            status="expired",
            amount=0,
            starts_at=now - timedelta(days=31),
            expires_at=now - timedelta(days=1),
        )
        await session.execute(
            update(Owner).where(Owner.id == graph.owner).values(trial_used=True)
        )
        source = await session.get(Subscription, trial_id)
        assert source is not None
        await subscription_metrics.capture_active_month(
            session=session,
            owner_id=graph.owner,
            restaurant_id=graph.restaurant,
            source=source,
            now=source.expires_at,
        )
        await session.commit()
        data = ManualSubscriptionCheckout(
            restaurant_id=graph.restaurant,
            plan_id=graph.plans["basic"],
            payment_method="ccp",
        )
        invoice = await SubscriptionCheckoutService(session=session).create(
            owner_id=graph.owner, data=data
        )
        await settle_fixture(session=session, owner_id=graph.owner, invoice=invoice)
        await session.commit()
        invoice_id, subscription_id = invoice.id, invoice.subscription_id
    async with factory() as observer:
        original_snapshot = (
            await observer.scalars(
                select(SubscriptionPricingSnapshot).where(
                    SubscriptionPricingSnapshot.subscription_id == subscription_id
                )
            )
        ).one()
        frozen_pricing, frozen_parameters = (
            original_snapshot.pricing,
            original_snapshot.parameters,
        )
        paid = await observer.get(Payment, invoice_id)
        current = await observer.get(Subscription, subscription_id)
        assert (
            paid is not None
            and current is not None
            and paid.status == "paid"
            and current.status == "active"
        )
        frozen_amount, starts, expires = (
            paid.amount,
            current.starts_at,
            current.expires_at,
        )
        assert frozen_parameters["B"] == "3000.00"
    async with factory() as session:
        role = await put(
            session,
            Role,
            code="o1-exact-pricing",
            name="Local test only",
            is_active=True,
        )
        permission = await put(
            session,
            Permission,
            code="subscriptions.pricing.manage",
            name="Local pricing test",
        )
        await session.execute(
            insert(role_permissions).values(role_id=role, permission_id=permission)
        )
        await put(
            session,
            Admin,
            chat_id=-820003,
            full_name="Local pricing author",
            role_id=role,
            auth_subject="o1-pricing-test",
        )
        await session.commit()
    principal = OIDCPrincipal(
        subject="o1-pricing-test",
        issuer="https://127.0.0.1:8444/realms/moulai-local",
        realm_roles=frozenset(),
    )
    async with factory() as session:
        before = await SaasPricingAdministration(session=session).current_base(
            principal=principal
        )
    async with factory() as session:
        after = await SaasPricingAdministration(session=session).change_base(
            principal=principal,
            command=BasePriceCommand(
                amount="3100.00",
                expected_sha256=before["sha256"],
                effective="on_commit",
                reason="Disposable test only: prove renewal recalculation",
            ),
        )
    assert after["revision"] != before["revision"]
    async with factory() as observer:
        monthly, parameters = await base_breakdown(
            session=observer, plan_id=graph.plans["basic"], billing_cycle="monthly"
        )
        assert (
            monthly == Decimal("3100.00")
            and parameters["base_revision"] == after["revision"]
        )
        old_snapshot = (
            await observer.scalars(
                select(SubscriptionPricingSnapshot).where(
                    SubscriptionPricingSnapshot.subscription_id == subscription_id
                )
            )
        ).one()
        paid = await observer.get(Payment, invoice_id)
        current = await observer.get(Subscription, subscription_id)
        assert (
            old_snapshot.pricing == frozen_pricing
            and old_snapshot.parameters == frozen_parameters
        )
        assert (
            paid is not None and paid.amount == frozen_amount and paid.status == "paid"
        )
        assert current is not None and (
            current.amount,
            current.starts_at,
            current.expires_at,
            current.status,
        ) == (frozen_amount, starts, expires, "active")
    async with factory() as session:
        renewed = await SubscriptionCheckoutService(session=session).create(
            owner_id=graph.owner, data=data
        )
    async with factory() as observer:
        snapshot = (
            await observer.scalars(
                select(SubscriptionPricingSnapshot).where(
                    SubscriptionPricingSnapshot.subscription_id
                    == renewed.subscription_id
                )
            )
        ).one()
        assert snapshot.context == "renewal"
        assert (
            snapshot.parameters["B"] == "3100.00"
            and snapshot.parameters["base_revision"] == after["revision"]
        )
        assert snapshot.reference_end - snapshot.reference_start == timedelta(days=30)
        old = await observer.get(Subscription, subscription_id)
        assert old is not None and old.expires_at == expires
    async with factory() as session:
        history = await SaasPricingAdministration(session=session).history(
            principal=principal, resource="saas_base", identifier=1
        )
        assert history[0]["author_name"] == "Local pricing author"
        assert history[0]["details"]["after"]["revision"] == after["revision"]


# ==============================================
# EXACT INVOICE BALANCE AND CONCURRENT RECEIPT
# Existing verified advances reduce the due amount; explicit human grants and invoice locks prevent double collection.
# ==============================================


@pytest.mark.asyncio
async def test_food_settlement_permissions_currency_concurrency_and_retention(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    """Observe every refusal and the single committed receipt through fresh PostgreSQL sessions."""
    engine = factory.kw["bind"]
    assert isinstance(engine, AsyncEngine)
    graph, _, advance_id, invoice_id = await invoicing_graph(engine=engine)
    async with graph.unit(actor="owner") as unit:
        await unit.finalize_invoice(invoice_id=invoice_id, expected_revision=1)
    data = SettlementInput(
        amount="4500",
        currency="DZD",
        mode="cash",
        reference="O2-SYNTHETIC-ONLY",
        received_at=graph.clock.value,
        observed=True,
    )
    with pytest.raises(TenantAccessDenied):
        async with graph.unit(actor="service") as unit:
            await record_settlement(unit=unit, invoice_id=invoice_id, data=data)
    for changed in [{"amount": "4499"}, {"currency": "USD"}]:
        with pytest.raises(DiningError):
            async with graph.unit(actor="collector") as unit:
                await record_settlement(
                    unit=unit,
                    invoice_id=invoice_id,
                    data=SettlementInput.model_validate(
                        {**data.model_dump(), **changed}
                    ),
                )
    async with factory() as observer:
        assert (
            await observer.scalar(
                text("SELECT count(*) FROM dining_settlements WHERE invoice_id=:id"),
                {"id": invoice_id},
            )
            == 0
        )

    # ==============================================
    # SEPARATE CONCURRENT TRANSACTIONS
    # Identical human intents return the same receipt rather than collecting a second balance.
    # ==============================================

    async def receive() -> dict[str, object]:
        """Commit one actually authorized request using its own session and scope."""
        async with graph.unit(actor="collector") as unit:
            return await record_settlement(unit=unit, invoice_id=invoice_id, data=data)

    first, repeated = await asyncio.gather(receive(), receive())
    assert first == repeated and Decimal(str(first["balance"])) == 0
    assert (
        Decimal(str(first["total"])) == 6000 and Decimal(str(first["advance"])) == 1500
    )
    async with factory() as observer:
        assert (
            await observer.scalar(
                text("SELECT count(*) FROM dining_settlements WHERE invoice_id=:id"),
                {"id": invoice_id},
            )
            == 1
        )
        assert (
            await observer.scalar(
                text("SELECT received_amount FROM dining_receipts WHERE id=:id"),
                {"id": advance_id},
            )
            == 1500
        )
        assert (
            await observer.scalar(
                text("SELECT total FROM dining_invoices WHERE id=:id"),
                {"id": invoice_id},
            )
            == 6000
        )
    async with factory() as session:
        with pytest.raises(IntegrityError, match="food_invoice_already_settled"):
            async with session.begin():
                await session.execute(
                    text(
                        "INSERT INTO dining_allocations(restaurant_id,branch_id,request_id,receipt_id,invoice_id,invoice_revision,invoice_total,other_paid,amount,currency,balance) SELECT restaurant_id,branch_id,request_id,receipt_id,invoice_id,invoice_revision,invoice_total,other_paid,amount,currency,balance FROM dining_allocations WHERE invoice_id=:id"
                    ),
                    {"id": invoice_id},
                )


# ==============================================
# FAILED RECEIPT TRANSACTION LEAVES NO PARTIAL SETTLEMENT
# A late event failure must not consume the remaining balance or erase an earlier advance.
# ==============================================


@pytest.mark.asyncio
async def test_food_settlement_late_failure_rolls_back(
    factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Inject failure after receipt INSERT and inspect durable state from an independent observer."""
    engine = factory.kw["bind"]
    assert isinstance(engine, AsyncEngine)
    graph, _, advance_id, invoice_id = await invoicing_graph(engine=engine)
    async with graph.unit(actor="owner") as unit:
        await unit.finalize_invoice(invoice_id=invoice_id, expected_revision=1)
    original = DiningUnit.event

    # ==============================================
    # POST-INSERT FAILURE
    # Preserve the original event implementation for all unrelated operations.
    # ==============================================

    async def fail_event(
        self: DiningUnit,
        *,
        kind: str,
        details: JsonObject,
        request_id: int | None = None,
        author_kind: str = "human",
    ) -> None:
        """Raise only for this receipt event after the new row has been flushed."""
        if kind == "invoice.settled":
            raise RuntimeError("injected_post_receipt_failure")
        await original(
            self,
            kind=kind,
            details=details,
            request_id=request_id,
            author_kind=author_kind,
        )

    monkeypatch.setattr(DiningUnit, "event", fail_event)
    with pytest.raises(RuntimeError, match="injected_post_receipt_failure"):
        async with graph.unit(actor="collector") as unit:
            await record_settlement(
                unit=unit,
                invoice_id=invoice_id,
                data=SettlementInput(
                    amount="4500",
                    currency="DZD",
                    mode="cash",
                    reference="O2-FAILED-ONLY",
                    received_at=graph.clock.value,
                    observed=True,
                ),
            )
    async with factory() as observer:
        assert (
            await observer.scalar(
                text("SELECT count(*) FROM dining_settlements WHERE invoice_id=:id"),
                {"id": invoice_id},
            )
            == 0
        )
        assert (
            await observer.scalar(
                text("SELECT received_amount FROM dining_receipts WHERE id=:id"),
                {"id": advance_id},
            )
            == 1500
        )


# ==============================================
# NONBINDING OWNER SIMULATION DOES NOT PERSIST A QUOTATION
# Even when the legacy calculator stages current-month evidence, the wrapper rolls it back before returning.
# ==============================================


@pytest.mark.asyncio
async def test_owner_simulation_keeps_only_the_result_not_metric_writes(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    """Verify the existing calculator on configured test data and inspect committed snapshot counts independently."""
    async with factory() as session:
        restaurant = await session.scalar(
            text(
                "SELECT id FROM restaurants WHERE owner_id=(SELECT id FROM owners WHERE chat_id=9900001) ORDER BY id LIMIT 1"
            )
        )
        plan = await session.scalar(
            text("SELECT id FROM subscription_plans WHERE code='basic'")
        )
        before = await session.scalar(
            text("SELECT count(*) FROM subscription_pricing_snapshots")
        )
        before_subscriptions = await session.scalar(
            text("SELECT count(*) FROM subscriptions")
        )
        result = await simulate_offer(
            session=session,
            restaurant_id=restaurant,
            data=OfferInput(
                plan_id=plan,
                billing_cycle="monthly",
                payment_method="electronic",
                currency="DZD",
            ),
        )
        assert result["binding_quote"] is False
        assert result["pricing"]["parameters"]["B"] == "3100.00"
        await session.commit()
    async with factory() as observer:
        assert (
            await observer.scalar(
                text("SELECT count(*) FROM subscription_pricing_snapshots")
            )
            == before
        )
        assert (
            await observer.scalar(text("SELECT count(*) FROM subscriptions"))
            == before_subscriptions
        )
