# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# SUBSCRIPTION LIFECYCLE REGRESSIONS
# Check trial uniqueness, renewals, immutable history and preserved service coverage.
# ==============================================

"""Real PostgreSQL regressions for approved subscription rules and evidence."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Declare the standard-library, framework and project dependencies used below.
# ==============================================

import asyncio
from datetime import (
    datetime,
    timedelta,
    timezone,
    tzinfo,
)
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import (
    func,
    insert,
    select,
    text,
    update,
)
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import raiseload

from app.models.admin import Admin
from app.models.branch import Branch
from app.models.category import Category
from app.models.loyalty_discount import Promotion
from app.models.order import Order
from app.models.order_item import OrderStatusHistory
from app.models.owner import Owner
from app.models.payment import Payment
from app.models.product import Product
from app.models.rbac import (
    Permission,
    Role,
    role_permissions,
)
from app.models.restaurant import Restaurant
from app.models.subscription import (
    Subscription,
    SubscriptionFeature,
)
from app.models.subscription_pricing import SubscriptionPricingSnapshot

from app.models.subscription_pricing_legacy import LegacySubscriptionPricingConfig as SubscriptionPricingConfig  # isort: skip  # fmt: skip
from app.schemas.manual_payment import (
    ManualPaymentReview,
    ManualSubscriptionCheckout,
)
from app.schemas.payment import PaymentResponse
from app.services.business import subscription_metrics as metrics
from app.services.business.manual_payment_service import ManualPaymentService
from app.services.business.payment_transaction import payment_transaction

from app.services.business.subscription_checkout_service import SubscriptionCheckoutService  # isort: skip  # fmt: skip
from app.services.business.subscription_service import SubscriptionService
from test_support.subscription_fixtures import (
    closed_trial,
    put,
    seed_graph,
)

# ==============================================
# GRAPH
# Reuse the shared synthetic subscription graph for the requested test case.
# ==============================================


@pytest.fixture
async def graph(db_session: AsyncSession) -> SimpleNamespace:
    """Reuse the shared synthetic subscription graph for the requested test case."""

    return await seed_graph(db_session)


# ==============================================
# SETTLE
# Create synthetic review authority and submit matching manual transfer evidence for
# settlement.
# ==============================================


async def settle(
    g: SimpleNamespace, invoice: PaymentResponse
) -> tuple[ManualPaymentService, int]:
    """Create synthetic review authority and submit matching manual transfer evidence for settlement."""

    role = await put(
        g.s, Role, code="synthetic-reviewer", name="Synthetic reviewer", is_active=True
    )
    permission = await put(g.s, Permission, code="payments.review", name="Review")
    await g.s.execute(
        insert(role_permissions).values(role_id=role, permission_id=permission)
    )
    admin = await put(g.s, Admin, chat_id=999999, role_id=role)
    await g.s.commit()
    manual = ManualPaymentService(session=g.s)
    await manual.submit_receipt(
        payment_id=invoice.id,
        owner_id=g.owner,
        transaction_reference="SYNTHETIC-ONLY",
        content=b"\x89PNG\r\n\x1a\nsynthetic",
        media_type="image/png",
    )
    await manual.review(
        payment_id=invoice.id,
        admin_id=admin,
        data=ManualPaymentReview(
            decision="approve",
            funds_received=True,
            bank_transaction_reference="SYNTHETIC-ONLY",
            received_amount=Decimal(str(invoice.amount)),
            received_currency="DZD",
            note="Local synthetic ledger only",
        ),
    )
    return manual, admin


# ==============================================
# TEST COMPLETE GOLDEN INVOICE HISTORY GRANTS AND STABILITY
# Verify complete golden invoice history grants and stability.
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "code,years,count,expected",
    [
        ("professional", 2, 3, Decimal(71540)),
        ("enterprise", 3, 10, Decimal("70207.20")),
    ],
)
async def test_complete_golden_invoice_history_grants_and_stability(
    graph: SimpleNamespace, code: str, years: int, count: int, expected: object
) -> None:
    """Verify complete golden invoice history grants and stability."""

    g = graph
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    await g.s.execute(
        update(Owner)
        .where(Owner.id == g.owner)
        .values(created_at=now - timedelta(days=365 * years + 10), trial_used=True)
    )
    for i in range(2, count):
        await put(
            g.s,
            Restaurant,
            owner_id=g.owner,
            name=f"Synthetic {i}",
            type="restaurant",
            phone=f"000000{i}",
            wilaya="Synthetic",
        )
    cats = []
    for i in range(10):
        cats.append(
            await put(g.s, Category, restaurant_id=g.restaurant, name=f"Category {i}")
        )
    await g.s.execute(
        insert(Product.__table__),
        [
            {
                "restaurant_id": g.restaurant,
                "category_id": cats[i % 10],
                "name": f"Product {i}",
                "price": 100,
            }
            for i in range(100)
        ],
    )
    for i in range(3):
        await put(g.s, Branch, restaurant_id=g.restaurant, name=f"Branch {i}")
    ids = (
        (
            await g.s.execute(
                insert(Order.__table__).returning(Order.id),
                [
                    {
                        "restaurant_id": g.restaurant,
                        "order_number": f"SYN-{i}",
                        "order_type": "dine_in",
                        "status": "completed",
                        "subtotal_amount": 2100,
                        "discount_amount": 100,
                        "total_amount": 2500,
                        "tax_amount": 100,
                        "delivery_amount": 400,
                        "created_at": now - timedelta(days=2),
                    }
                    for i in range(1000)
                ],
            )
        )
        .scalars()
        .all()
    )
    await g.s.execute(
        insert(OrderStatusHistory.__table__),
        [
            {
                "order_id": oid,
                "new_status": "completed",
                "created_at": now - timedelta(days=1),
            }
            for oid in ids
        ],
    )
    await put(g.s, Promotion, name="Synthetic golden", discount_percent=10, active=True)
    await g.s.commit()
    from app.services.business.subscription_calendar import add_months

    end = now - timedelta(seconds=1)
    last = None
    for index in range(years):
        start = add_months(start=end, months=-12 * (years - index))
        finish = add_months(start=end, months=-12 * (years - index - 1))
        last = await put(
            g.s,
            Subscription,
            owner_id=g.owner,
            restaurant_id=g.restaurant,
            plan_id=g.plans["basic"],
            billing_cycle="yearly",
            status="expired",
            amount=1,
            starts_at=start,
            expires_at=finish,
        )
        await put(
            g.s,
            Payment,
            owner_id=g.owner,
            restaurant_id=g.restaurant,
            subscription_id=last,
            payment_method="ccp",
            amount=1,
            status="paid",
            paid_at=start,
        )
    source = (
        await g.s.execute(
            select(Subscription).options(raiseload("*")).where(Subscription.id == last)
        )
    ).scalar_one()
    await metrics.capture_active_month(
        session=g.s,
        owner_id=g.owner,
        restaurant_id=g.restaurant,
        source=source,
        now=end,
    )
    await g.s.commit()
    data = ManualSubscriptionCheckout(
        restaurant_id=g.restaurant,
        plan_id=g.plans[code],
        billing_cycle="yearly",
        payment_method="ccp",
        additional_feature_ids=[g.f["extra"]],
    )
    checkout = SubscriptionCheckoutService(session=g.s)
    invoice = await checkout.create(owner_id=g.owner, data=data)
    assert Decimal(str(invoice.amount)) == expected
    evidence = (
        await g.s.execute(
            select(SubscriptionPricingSnapshot).where(
                SubscriptionPricingSnapshot.subscription_id == invoice.subscription_id
            )
        )
    ).scalar_one()
    assert [
        evidence.products_count,
        evidence.categories_count,
        evidence.monthly_orders,
        evidence.average_order_value,
    ] == [100, 10, 1000, 2000]
    assert Decimal(evidence.pricing["base_price"]) == (
        5375 if code == "professional" else 6700
    )
    assert Decimal(evidence.pricing["restaurant_score"]) == 2500
    assert evidence.parameters["B"] == "3000.00"
    assert evidence.context == "return"
    assert (await checkout.create(owner_id=g.owner, data=data)).id == invoice.id
    before = (
        await g.s.execute(
            select(func.count())
            .select_from(SubscriptionFeature)
            .where(SubscriptionFeature.subscription_id == invoice.subscription_id)
        )
    ).scalar_one()
    assert before == 0
    manual, admin = await settle(g, invoice)
    granted = set(
        (
            await g.s.execute(
                select(SubscriptionFeature.feature_id).where(
                    SubscriptionFeature.subscription_id == invoice.subscription_id
                )
            )
        ).scalars()
    )
    from app.services.business.subscription_contract import INCLUDED

    assert granted == {g.f[key] for key in INCLUDED[code]} | {g.f["extra"]}
    from app.guards.feature_guard import require_feature

    for feature_id in granted:
        allowed = await require_feature(
            session=g.s, restaurant_id=g.restaurant, feature_id=feature_id
        )
        assert allowed.id == invoice.subscription_id
    sub = (
        await g.s.execute(
            select(Subscription)
            .options(raiseload("*"))
            .where(Subscription.id == invoice.subscription_id)
        )
    ).scalar_one()
    dates = (sub.starts_at, sub.expires_at)
    assert dates[1] == add_months(start=dates[0], months=12)
    await g.s.execute(update(SubscriptionPricingConfig).values(base_price=9999))
    await g.s.commit()
    assert (
        await g.s.execute(select(Subscription.amount).where(Subscription.id == sub.id))
    ).scalar_one() == expected
    assert Decimal(evidence.pricing["final_amount_due"]) == expected
    # Repeated approval cannot duplicate rights, restart a period or recalculate amount.
    await manual.review(
        payment_id=invoice.id,
        admin_id=admin,
        data=ManualPaymentReview(
            decision="approve",
            funds_received=True,
            bank_transaction_reference="SYNTHETIC-ONLY",
            received_amount=expected,
            received_currency="DZD",
            note="Local synthetic ledger only",
        ),
    )
    assert (
        await g.s.execute(
            select(func.count())
            .select_from(SubscriptionFeature)
            .where(SubscriptionFeature.subscription_id == sub.id)
        )
    ).scalar_one() == len(granted)
    assert (
        await g.s.execute(
            select(Subscription.starts_at, Subscription.expires_at).where(
                Subscription.id == sub.id
            )
        )
    ).one() == dates


# ==============================================
# TEST CONCURRENT TRIAL SAME OWNER DIFFERENT RESTAURANTS
# Verify concurrent trial same owner different restaurants.
# ==============================================


@pytest.mark.asyncio
async def test_concurrent_trial_same_owner_different_restaurants(
    graph: SimpleNamespace,
) -> None:
    """Verify concurrent trial same owner different restaurants."""

    g = graph
    sessions = async_sessionmaker(g.s.bind, expire_on_commit=False)

    # ==============================================
    # ATTEMPT
    # Attempt synthetic trial creation and retain either its identifier or the observed
    # conflict.
    # ==============================================

    async def attempt(s: AsyncSession, restaurant: int) -> tuple[str, int | str]:
        """Attempt synthetic trial creation and retain either its identifier or the observed conflict."""

        try:
            sub = await SubscriptionService(session=s).create_trial_subscription(
                owner_id=g.owner, restaurant_id=restaurant
            )
            return ("created", sub.id)
        except ValueError as error:
            return ("refused", str(error))

    async with sessions() as first, sessions() as second:
        # Connection establishment is not the concurrent business operation.
        # Prepare both independent connections before its bounded race window.
        await first.execute(select(1))
        await second.execute(select(1))
        results = await asyncio.wait_for(
            asyncio.gather(attempt(first, g.restaurant), attempt(second, g.second)),
            timeout=30,
        )
    assert sorted(x[0] for x in results) == ["created", "refused"]
    assert ("refused", "trial_already_used") in results
    assert (
        await g.s.execute(select(func.count()).select_from(Subscription))
    ).scalar_one() == 1
    assert (
        await g.s.execute(select(func.count()).select_from(SubscriptionFeature))
    ).scalar_one() == 8


# ==============================================
# TEST TRIAL IGNORES STALE OWNER CACHE AND CANNOT BE REGRANTED AFTER FLAG RESET
# Verify trial ignores stale owner cache and cannot be regranted after flag reset.
# ==============================================


@pytest.mark.asyncio
async def test_trial_ignores_stale_owner_cache_and_cannot_be_regranted_after_flag_reset(
    graph: SimpleNamespace,
) -> None:
    """Verify trial ignores stale owner cache and cannot be regranted after flag reset."""

    g = graph
    stale = (
        await g.s.execute(
            select(Owner).options(raiseload("*")).where(Owner.id == g.owner)
        )
    ).scalar_one()
    assert not stale.trial_used
    await g.s.commit()
    sessions = async_sessionmaker(g.s.bind, expire_on_commit=False)
    async with sessions() as other:
        await SubscriptionService(session=other).create_trial_subscription(
            owner_id=g.owner, restaurant_id=g.restaurant
        )
    assert not stale.trial_used
    with pytest.raises(ValueError, match="trial_already_used"):
        await SubscriptionService(session=g.s).create_trial_subscription(
            owner_id=g.owner, restaurant_id=g.second
        )
    await g.s.execute(update(Owner).where(Owner.id == g.owner).values(trial_used=False))
    await g.s.commit()
    with pytest.raises(ValueError, match="trial_already_used"):
        await SubscriptionService(session=g.s).create_trial_subscription(
            owner_id=g.owner, restaurant_id=g.second
        )


# ==============================================
# TEST FRACTIONAL AVERAGE SURVIVES PERSISTED HISTORY WITHOUT INTERMEDIATE ROUNDING
# Verify fractional average survives persisted history without intermediate rounding.
# ==============================================


@pytest.mark.asyncio
async def test_fractional_average_survives_persisted_history_without_intermediate_rounding(
    graph: SimpleNamespace,
) -> None:
    """Verify fractional average survives persisted history without intermediate rounding."""

    g = graph
    end = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=1)
    for index, amount in enumerate([1, 0, 0]):
        oid = await put(
            g.s,
            Order,
            restaurant_id=g.restaurant,
            order_number=f"FRACTION-{index}",
            order_type="dine_in",
            status="completed",
            subtotal_amount=amount,
            discount_amount=0,
            total_amount=amount,
        )
        await put(
            g.s,
            OrderStatusHistory,
            order_id=oid,
            new_status="completed",
            created_at=end - timedelta(days=1),
        )
    await closed_trial(g, end=end)
    sessions = async_sessionmaker(g.s.bind, expire_on_commit=False)
    async with sessions() as s:
        restored = await metrics.reference(
            session=s,
            owner_id=g.owner,
            restaurant_id=g.restaurant,
            now=end + timedelta(days=1),
        )
        assert restored["average_order_value"] == Decimal(1) / Decimal(3)
        assert restored["monthly_orders"] == 3


# ==============================================
# TEST CONTINUOUS RENEWAL WINDOW AND SINGLE PENDING INVOICE
# Verify continuous renewal window and single pending invoice.
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "cycle,days",
    [("monthly", 30), ("quarterly", 90), ("semiannual", 180), ("yearly", 365)],
)
async def test_continuous_renewal_window_and_single_pending_invoice(
    graph: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, cycle: str, days: int
) -> None:
    """Verify continuous renewal window and single pending invoice."""

    g = graph
    instant = datetime(2026, 10, 29, 12, tzinfo=timezone.utc).replace(tzinfo=None)
    from app.services.business.subscription_calendar import add_months

    months = {"monthly": 1, "quarterly": 3, "semiannual": 6, "yearly": 12}[cycle]
    old = await put(
        g.s,
        Subscription,
        owner_id=g.owner,
        restaurant_id=g.restaurant,
        plan_id=g.plans["basic"],
        billing_cycle=cycle,
        amount=1,
        status="active",
        starts_at=add_months(start=instant, months=-months),
        expires_at=instant,
    )

    # Fixed clock gives a boundary, not an approximation based on current catalog data.

    # ==============================================
    # CLOCK
    # Provide a fixed UTC clock for exact boundary assertions.
    # ==============================================

    class Clock(datetime):
        """Provide a fixed UTC clock for exact boundary assertions."""

        # ==============================================
        # NOW
        # Return the fixed test instant using the timezone form requested by the caller.
        # ==============================================

        @classmethod
        def now(cls, tz: tzinfo | None = None) -> datetime:
            """Return the fixed test instant using the timezone form requested by the caller."""

            return instant.replace(tzinfo=timezone.utc) if tz else instant

    from app.services.business import (
        subscription_checkout_service,
        subscription_service,
    )

    monkeypatch.setattr(subscription_checkout_service, "datetime", Clock)
    monkeypatch.setattr(subscription_service, "datetime", Clock)
    await g.s.commit()
    checkout = SubscriptionCheckoutService(session=g.s)
    data = ManualSubscriptionCheckout(
        restaurant_id=g.restaurant,
        plan_id=g.plans["basic"],
        billing_cycle=cycle,
        payment_method="baridimob",
    )
    first = await checkout.create(owner_id=g.owner, data=data)
    second = await checkout.create(owner_id=g.owner, data=data)
    assert first.id == second.id
    snap = (
        await g.s.execute(
            select(SubscriptionPricingSnapshot).where(
                SubscriptionPricingSnapshot.subscription_id == first.subscription_id
            )
        )
    ).scalar_one()
    assert snap.context == "renewal"
    assert snap.reference_end - snap.reference_start == timedelta(days=30)
    assert snap.reference_end == instant
    # Exercise the verified-payment activation boundary, without any provider.
    async with payment_transaction(session=g.s):
        await g.s.execute(
            update(Payment)
            .where(Payment.id == first.id)
            .values(status="paid", paid_at=instant)
        )
        pay = (
            await g.s.execute(
                select(Payment).options(raiseload("*")).where(Payment.id == first.id)
            )
        ).scalar_one()
        await SubscriptionService(session=g.s).activate_for_verified_payment(
            payment=pay
        )
        await SubscriptionService(session=g.s).activate_for_verified_payment(
            payment=pay
        )
    active = (
        await g.s.execute(
            select(Subscription.starts_at, Subscription.expires_at).where(
                Subscription.id == first.subscription_id
            )
        )
    ).one()
    from app.services.business.subscription_calendar import add_months

    assert active == (
        instant,
        add_months(
            start=instant,
            months={"monthly": 1, "quarterly": 3, "semiannual": 6, "yearly": 12}[cycle],
        ),
    )
    assert (
        await g.s.execute(select(Subscription.status).where(Subscription.id == old))
    ).scalar_one() == "expired"


# ==============================================
# TEST SNAPSHOT IMMUTABLE EVEN WITH DIRECT SQL
# Verify snapshot immutable even with direct sql.
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("mutation", ["update", "delete"])
async def test_snapshot_immutable_even_with_direct_sql(
    graph: SimpleNamespace, mutation: str
) -> None:
    """Verify snapshot immutable even with direct sql."""

    await closed_trial(graph)
    try:
        async with graph.s.begin_nested():
            await graph.s.execute(
                text(
                    "UPDATE subscription_pricing_snapshots SET monthly_orders=99"
                    if mutation == "update"
                    else "DELETE FROM subscription_pricing_snapshots"
                )
            )
    except DBAPIError:
        pass
    else:
        pytest.fail("database allowed mutation of history")
    assert (
        await graph.s.execute(
            select(func.count()).select_from(SubscriptionPricingSnapshot)
        )
    ).scalar_one() == 1


# ==============================================
# TEST BEST PROMOTION IS SELECTED WITHOUT AN UNAPPROVED POLICY
# Verify best promotion is selected without an unapproved policy.
# ==============================================


@pytest.mark.asyncio
async def test_best_promotion_is_selected_without_an_unapproved_policy(
    graph: SimpleNamespace,
) -> None:
    """Verify best promotion is selected without an unapproved policy."""

    from app.services.business.pricing_service import calculate_promotion_discount

    for i in range(2):
        await put(
            graph.s,
            Promotion,
            name=f"Synthetic {i}",
            discount_percent=10 + i * 5,
            active=True,
        )
    await graph.s.commit()
    assert (
        await calculate_promotion_discount(session=graph.s, amount=Decimal(100)) == 15
    )


# ==============================================
# TEST MISSING COMPLETION TIMESTAMP NEVER GUESSED
# Verify missing completion timestamp never guessed.
# ==============================================


@pytest.mark.asyncio
async def test_missing_completion_timestamp_never_guessed(
    graph: SimpleNamespace,
) -> None:
    """Verify missing completion timestamp never guessed."""

    await put(
        graph.s,
        Order,
        restaurant_id=graph.restaurant,
        order_number="SYN-MISSING",
        order_type="dine_in",
        status="completed",
        subtotal_amount=100,
        total_amount=100,
    )
    with pytest.raises(ValueError, match="order_completion_evidence_missing"):
        await metrics.collect(
            session=graph.s,
            owner_id=graph.owner,
            restaurant_id=graph.restaurant,
            end=datetime.now(timezone.utc),
        )


# ==============================================
# TEST RETURNING OWNER CANNOT CLAIM TRIAL FROM INCOMPLETE LEGACY FLAG
# Verify returning owner cannot claim trial from incomplete legacy flag.
# ==============================================


@pytest.mark.asyncio
async def test_returning_owner_cannot_claim_trial_from_incomplete_legacy_flag(
    graph: SimpleNamespace,
) -> None:
    """Verify returning owner cannot claim trial from incomplete legacy flag."""

    g = graph
    end = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=60)
    await put(
        g.s,
        Subscription,
        owner_id=g.owner,
        restaurant_id=g.restaurant,
        plan_id=g.plans["basic"],
        billing_cycle="monthly",
        amount=3000,
        status="expired",
        starts_at=end - timedelta(days=30),
        expires_at=end,
    )
    await g.s.commit()
    with pytest.raises(ValueError, match="trial_already_used"):
        await SubscriptionService(session=g.s).create_trial_subscription(
            owner_id=g.owner, restaurant_id=g.second
        )
    assert (
        await g.s.execute(select(func.count()).select_from(Subscription))
    ).scalar_one() == 1
