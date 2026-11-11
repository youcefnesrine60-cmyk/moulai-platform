# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# APPROVED COMMERCIAL DECISION REGRESSIONS
# Check paid seniority, progressive grids, promotions, currency rounding and reminders.
# ==============================================

"""Regressions for the explicitly approved 29 October commercial decisions."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Declare the standard-library, framework and project dependencies used below.
# ==============================================

from datetime import (
    datetime,
    timedelta,
    timezone,
)
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import (
    delete,
    select,
    update,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import raiseload

from app.models.feature_pricing import (
    BranchPricing,
    FeaturePricing,
)
from app.models.loyalty_discount import Promotion
from app.models.payment import Payment
from app.models.subscription import Subscription
from app.models.subscription_pricing import SubscriptionReminder

from app.models.subscription_pricing_legacy import LegacySubscriptionPricingConfig as SubscriptionPricingConfig  # isort: skip  # fmt: skip

from app.services.business import pricing_service as pricing
from app.services.business import subscription_reminders as reminders
from app.services.business.payment_transaction import payment_transaction
from app.services.business.subscription_boundaries import process_boundaries
from app.services.business.subscription_branch_pricing import branch_breakdown
from app.services.business.subscription_calendar import (
    add_months,
    completed_paid_years,
)
from app.services.business.subscription_service import SubscriptionService
from test_support.subscription_fixtures import (
    put,
    seed_graph,
)

# ==============================================
# MOMENT
# Construct the requested test date at noon in the naive UTC storage convention.
# ==============================================


def moment(year: int, month: int, day: int) -> datetime:
    """Construct the requested test date at noon in the naive UTC storage convention."""

    return datetime(year, month, day, 12, tzinfo=timezone.utc).replace(tzinfo=None)


# ==============================================
# GRAPH
# Reuse the shared synthetic subscription graph for the requested test case.
# ==============================================


@pytest.fixture
async def graph(db_session: AsyncSession) -> SimpleNamespace:
    """Reuse the shared synthetic subscription graph for the requested test case."""

    return await seed_graph(db_session)


# ==============================================
# TEST PAID CALENDAR ANNIVERSARIES INCLUSIVE
# Verify paid calendar anniversaries inclusive.
# ==============================================


@pytest.mark.parametrize("years", [1, 2, 3, 4, 5, 10, 15])
@pytest.mark.parametrize("delta,expected_delta", [(-1, -1), (0, 0), (1, 0)])
def test_paid_calendar_anniversaries_inclusive(
    years: int, delta: int, expected_delta: int
) -> None:
    """Verify paid calendar anniversaries inclusive."""

    anchor = moment(2020, 2, 29)
    anniversary = add_months(start=anchor, months=12 * years)
    now = anniversary + timedelta(microseconds=delta)
    assert (
        completed_paid_years(
            periods=[(anchor, add_months(start=anchor, months=12 * (years + 1)))],
            now=now,
        )
        == years + expected_delta
    )


# ==============================================
# TEST INTERRUPTIONS PAUSE AND OVERLAPPING COVERAGE IS COUNTED ONCE
# Verify interruptions pause and overlapping coverage is counted once.
# ==============================================


def test_interruptions_pause_and_overlapping_coverage_is_counted_once() -> None:
    """Verify interruptions pause and overlapping coverage is counted once."""

    start = moment(2020, 1, 1)
    assert (
        completed_paid_years(
            periods=[
                (start, moment(2021, 1, 1)),
                (moment(2020, 6, 1), moment(2021, 6, 1)),
            ],
            now=moment(2021, 6, 1),
        )
        == 1
    )
    periods = [
        (moment(2023, 1, 1), moment(2023, 7, 1)),
        (moment(2024, 1, 1), moment(2024, 7, 3)),
    ]
    # Virtual calendar convention: 181 + 184 service days reach the first
    # anniversary of the 2023 anchor. Inactivity contributes no duration.
    assert completed_paid_years(periods=periods, now=moment(2024, 7, 2)) == 0
    assert completed_paid_years(periods=periods, now=moment(2024, 7, 3)) == 1
    assert completed_paid_years(periods=periods, now=moment(2030, 1, 1)) == 1


# ==============================================
# TEST CALENDAR ANCHOR IS NOT LOST IN SHORT MONTHS
# Verify calendar anchor is not lost in short months.
# ==============================================


def test_calendar_anchor_is_not_lost_in_short_months() -> None:
    """Verify calendar anchor is not lost in short months."""

    day = moment(2027, 1, 31)
    result = []
    for _ in range(4):
        day = add_months(start=day, months=1, anchor_day=31)
        result.append((day.month, day.day))
    assert result == [(2, 28), (3, 31), (4, 30), (5, 31)]
    assert add_months(start=moment(2024, 2, 29), months=12) == moment(2025, 2, 28)


# ==============================================
# TEST PROGRESSIVE RANK BOUNDARIES
# Verify progressive rank boundaries.
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "count,expected", [(1, 0), (2, 500), (5, 2000), (6, 2400), (20, 8000), (21, 8300)]
)
async def test_progressive_rank_boundaries(
    graph: SimpleNamespace, count: int, expected: object
) -> None:
    """Verify progressive rank boundaries."""

    actual, details = await branch_breakdown(
        session=graph.s, branches_count=count, plan_id=graph.plans["basic"]
    )
    assert actual == expected
    assert (
        sum(Decimal(row["unit_price"]) * row["quantity"] for row in details) == expected
    )


# ==============================================
# TEST BRANCH CURRENCY DATE MARKET AND AMBIGUITY
# Verify branch currency date market and ambiguity.
# ==============================================


@pytest.mark.asyncio
async def test_branch_currency_date_market_and_ambiguity(
    graph: SimpleNamespace,
) -> None:
    """Verify branch currency date market and ambiguity."""

    g = graph
    now = moment(2026, 10, 29)
    await put(
        g.s,
        BranchPricing,
        min_branches=2,
        max_branches=None,
        price_per_branch=7,
        currency="EUR",
        market="FR",
        grid_code="eur-fr",
        active=True,
        starts_at=now,
        expires_at=now + timedelta(days=1),
    )
    assert (
        await branch_breakdown(
            session=g.s, branches_count=3, currency="EUR", market="FR", now=now
        )
    )[0] == 14
    for kwargs in [
        {"currency": "EUR", "market": "DZ", "now": now},
        {"currency": "EUR", "market": "FR", "now": now + timedelta(days=1)},
        {"currency": "USD", "market": None, "now": now},
    ]:
        with pytest.raises(ValueError, match="branch_grid_missing"):
            await branch_breakdown(session=g.s, branches_count=3, **kwargs)
    await put(
        g.s,
        BranchPricing,
        min_branches=2,
        max_branches=None,
        price_per_branch=8,
        currency="EUR",
        market="FR",
        grid_code="eur-fr-overlapping-grid",
        active=True,
        starts_at=now,
    )
    with pytest.raises(ValueError, match="branch_grid_ambiguous"):
        await branch_breakdown(
            session=g.s, branches_count=3, currency="EUR", market="FR", now=now
        )


# ==============================================
# TEST OVERLAPPING OR GAPPED RANKS REFUSED
# Verify overlapping or gapped ranks refused.
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("second_min", [4, 7])
async def test_overlapping_or_gapped_ranks_refused(
    graph: SimpleNamespace, second_min: int
) -> None:
    """Verify overlapping or gapped ranks refused."""

    await graph.s.execute(delete(BranchPricing))
    for low, high in [(2, 5), (second_min, None)]:
        await put(
            graph.s,
            BranchPricing,
            min_branches=low,
            max_branches=high,
            price_per_branch=100,
            active=True,
            grid_code="invalid",
        )
    with pytest.raises(ValueError, match="branch_grid_overlap_or_gap"):
        await branch_breakdown(session=graph.s, branches_count=9)


# ==============================================
# TEST BEST PROMOTION PRIORITY STABLE ID AND EXCLUSIVE END
# Verify best promotion priority stable id and exclusive end.
# ==============================================


@pytest.mark.asyncio
async def test_best_promotion_priority_stable_id_and_exclusive_end(
    graph: SimpleNamespace,
) -> None:
    """Verify best promotion priority stable id and exclusive end."""

    from app.repositories.promotion_repo import PromotionRepository

    now = moment(2026, 10, 29)
    await put(
        graph.s,
        Promotion,
        name="lower-rate-high-priority",
        discount_percent=20,
        priority=999,
        active=True,
    )
    first = await put(
        graph.s,
        Promotion,
        name="winner",
        discount_percent=30,
        priority=10,
        active=True,
        starts_at=now,
        expires_at=now + timedelta(days=1),
    )
    await put(
        graph.s,
        Promotion,
        name="same-priority-later-id",
        discount_percent=30,
        priority=10,
        active=True,
    )
    await put(
        graph.s,
        Promotion,
        name="wrong-owner",
        discount_percent=99,
        priority=999,
        owner_id=graph.owner,
        active=True,
    )
    rules = await PromotionRepository(session=graph.s).get_active_promotions(now=now)
    assert rules[0].id == first
    assert all(rule.name != "wrong-owner" for rule in rules)
    later = await PromotionRepository(session=graph.s).get_active_promotions(
        now=now + timedelta(days=1)
    )
    assert first not in [rule.id for rule in later]


# ==============================================
# TEST DECIMAL ENTIRE CHAIN AND CURRENCY PRECISION
# Verify decimal entire chain and currency precision.
# ==============================================


@pytest.mark.asyncio
async def test_decimal_entire_chain_and_currency_precision(
    graph: SimpleNamespace,
) -> None:
    """Verify decimal entire chain and currency precision."""

    g = graph
    config = await g.s.get(SubscriptionPricingConfig, 1)
    assert config is not None
    await g.s.execute(
        update(SubscriptionPricingConfig).values(
            base_price=0,
            policies={
                # This case changes currency precision, not the approved payment
                # adjustment or reminder configuration prepared by seed_graph.
                **config.policies,
                "currencies": {"DZD": {"decimals": 2}, "JPY": {"decimals": 0}},
                "currency_bases": {"JPY": "1000"},
                "reminder_days": [14, 7, 1, 0],
            },
        )
    )
    await g.s.execute(
        update(FeaturePricing)
        .where(FeaturePricing.feature_id == g.f["extra"])
        .values(price=Decimal("0.005"))
    )
    common = {
        "session": g.s,
        "plan_id": g.plans["basic"],
        "billing_cycle": "monthly",
        "payment_method": "electronic",
        "restaurants_count": 1,
        "branches_count": 1,
        "years_with_platform": 0,
        "products_count": 0,
        "categories_count": 0,
        "monthly_orders": 0,
        "average_order_value": Decimal(0),
    }
    result = await pricing.calculate_subscription_pricing(
        **common, additional_feature_ids=[g.f["extra"]]
    )
    assert result["final_price"] == Decimal("0.005")
    assert result["payment_adjustment"] == Decimal("-0.0001")
    assert result["final_amount_due"] == Decimal("0.00")
    assert all(
        isinstance(result[key], Decimal)
        for key in result
        if key not in ["parameters", "exact"]
    )
    await put(
        g.s,
        BranchPricing,
        min_branches=2,
        max_branches=None,
        price_per_branch=10,
        currency="JPY",
        active=True,
        grid_code="explicit-jpy",
    )
    yen = await pricing.calculate_subscription_pricing(**common, currency="JPY")
    assert yen["final_amount_due"] == Decimal(980)
    assert yen["final_amount_due"].as_tuple().exponent == 0
    with pytest.raises(ValueError, match="currency_configuration_missing"):
        await pricing.calculate_subscription_pricing(**common, currency="USD")
    with pytest.raises(ValueError, match="invalid_payment_method"):
        await pricing.calculate_subscription_pricing(
            **(common | {"payment_method": "unknown"})
        )
    # Removing the persisted rates must still block quotation: this fixture
    # correction must not introduce a default or weaken the configuration guard.
    await g.s.execute(
        update(SubscriptionPricingConfig).values(
            policies={
                key: value
                for key, value in config.policies.items()
                if key != "payment_adjustment_rates"
            }
        )
    )
    with pytest.raises(ValueError, match="^payment_adjustment_configuration_missing$"):
        await pricing.calculate_subscription_pricing(**common)


# ==============================================
# ACTIVE
# Create synthetic paid service coverage with the selected dates and calendar anchor.
# ==============================================


async def active(
    graph: SimpleNamespace,
    *,
    start: datetime | None = None,
    expiry: datetime | None = None,
) -> Subscription:
    """Create synthetic paid service coverage with the selected dates and calendar anchor."""

    start = start or moment(2026, 10, 1)
    expiry = expiry or moment(2026, 11, 1)
    identifier = await put(
        graph.s,
        Subscription,
        owner_id=graph.owner,
        restaurant_id=graph.restaurant,
        plan_id=graph.plans["basic"],
        billing_cycle="monthly",
        amount=3000,
        status="active",
        starts_at=start,
        expires_at=expiry,
        calendar_anchor=start,
    )
    return (
        await graph.s.execute(
            select(Subscription)
            .options(raiseload("*"))
            .where(Subscription.id == identifier)
        )
    ).scalar_one()


# ==============================================
# SYNTHETIC SENDER
# Controlled local transport recording deliveries and injecting explicit failures.
# ==============================================


class SyntheticSender:
    """Controlled local transport recording deliveries and injecting explicit failures."""

    # ==============================================
    # INIT
    # Bind the explicit dependencies without performing external operations.
    # ==============================================

    def __init__(self, fail_target: str | None = None, uncertain: bool = False) -> None:
        """Bind the explicit dependencies without performing external operations."""

        self.calls = []
        self.fail_target = fail_target
        self.uncertain = uncertain

    # ==============================================
    # SEND
    # Record synthetic delivery and raise only the configured deterministic transport
    # failure.
    # ==============================================

    async def send(self, **message: str) -> None:
        """Record synthetic delivery and raise only the configured deterministic transport failure."""

        self.calls.append(message)
        if message["target"] == self.fail_target:
            if self.uncertain:
                raise TimeoutError("synthetic ambiguous outcome")
            raise reminders.DefinitelyNotDelivered("synthetic refusal")


# ==============================================
# TEST REMINDER BOTH RECIPIENTS FOUR DATES IDEMPOTENCE AND RETRY
# Verify reminder both recipients four dates idempotence and retry.
# ==============================================


@pytest.mark.asyncio
async def test_reminder_both_recipients_four_dates_idempotence_and_retry(
    graph: SimpleNamespace,
) -> None:
    """Verify reminder both recipients four dates idempotence and retry."""

    g = graph
    sub = await active(g)
    await reminders.schedule(session=g.s, subscription=sub)
    await reminders.schedule(session=g.s, subscription=sub)
    await g.s.commit()
    rows = (await g.s.execute(select(SubscriptionReminder))).scalars().all()
    assert len(rows) == 8
    assert {row.offset_days for row in rows} == {14, 7, 1, 0}
    assert {row.recipient for row in rows} == {"owner", "moulai_responsible"}
    assert all(
        row.due_at == sub.expires_at - timedelta(days=row.offset_days) for row in rows
    )
    await g.s.commit()
    sessions = async_sessionmaker(g.s.bind, expire_on_commit=False)
    sender = SyntheticSender(fail_target="9901002")
    await reminders.dispatch(
        session_factory=sessions, sender=sender, now=sub.expires_at
    )
    assert len(sender.calls) == 8
    assert all("prochain prix" in call["message"] for call in sender.calls)
    sender.fail_target = None
    await reminders.dispatch(
        session_factory=sessions, sender=sender, now=sub.expires_at
    )
    assert len(sender.calls) == 12  # only the four failed responsible-recipient sends
    await reminders.dispatch(
        session_factory=sessions, sender=sender, now=sub.expires_at
    )
    assert len(sender.calls) == 12


# ==============================================
# TEST AMBIGUOUS DELIVERY NOT AUTOMATICALLY REPEATED
# Verify ambiguous delivery not automatically repeated.
# ==============================================


@pytest.mark.asyncio
async def test_ambiguous_delivery_not_automatically_repeated(
    graph: SimpleNamespace,
) -> None:
    """Verify ambiguous delivery not automatically repeated."""

    sub = await active(graph)
    await reminders.schedule(session=graph.s, subscription=sub)
    await graph.s.commit()
    sender = SyntheticSender(fail_target="9901002", uncertain=True)
    sessions = async_sessionmaker(graph.s.bind, expire_on_commit=False)
    await reminders.dispatch(
        session_factory=sessions, sender=sender, now=sub.expires_at
    )
    await reminders.dispatch(
        session_factory=sessions, sender=sender, now=sub.expires_at
    )
    assert len(sender.calls) == 8


# ==============================================
# TEST CONFIRMED EARLY RENEWAL PRESERVES DAYS AND REPLACES REMINDERS
# Verify confirmed early renewal preserves days and replaces reminders.
# ==============================================


@pytest.mark.asyncio
async def test_confirmed_early_renewal_preserves_days_and_replaces_reminders(
    graph: SimpleNamespace,
) -> None:
    """Verify confirmed early renewal preserves days and replaces reminders."""

    g = graph
    first = await active(g, start=moment(2027, 1, 31), expiry=moment(2027, 2, 28))
    await reminders.schedule(session=g.s, subscription=first)
    second = await put(
        g.s,
        Subscription,
        owner_id=g.owner,
        restaurant_id=g.restaurant,
        plan_id=g.plans["basic"],
        billing_cycle="monthly",
        amount=2940,
        status="pending",
    )
    await g.s.commit()
    # A request alone leaves all old reminders pending.
    assert set((await g.s.execute(select(SubscriptionReminder.status))).scalars()) == {
        "pending"
    }
    async with payment_transaction(session=g.s):
        pid = await put(
            g.s,
            Payment,
            owner_id=g.owner,
            restaurant_id=g.restaurant,
            subscription_id=second,
            payment_method="ccp",
            amount=2940,
            status="paid",
            paid_at=moment(2027, 2, 15),
        )
        payment = (
            await g.s.execute(
                select(Payment).options(raiseload("*")).where(Payment.id == pid)
            )
        ).scalar_one()
        await SubscriptionService(session=g.s).activate_for_verified_payment(
            payment=payment
        )
    stored = (
        await g.s.execute(
            select(Subscription)
            .options(raiseload("*"))
            .where(Subscription.id == second)
        )
    ).scalar_one()
    assert stored.status == "scheduled"
    assert stored.starts_at == moment(2027, 2, 28)
    assert stored.expires_at == moment(2027, 3, 31)
    assert (
        await g.s.execute(
            select(Subscription.status).where(Subscription.id == first.id)
        )
    ).scalar_one() == "active"
    assert set(
        (
            await g.s.execute(
                select(SubscriptionReminder.status).where(
                    SubscriptionReminder.subscription_id == first.id
                )
            )
        ).scalars()
    ) == {"cancelled"}
    assert (
        len(
            (
                await g.s.execute(
                    select(SubscriptionReminder.id).where(
                        SubscriptionReminder.subscription_id == second
                    )
                )
            ).all()
        )
        == 8
    )
    await process_boundaries(session=g.s, now=moment(2027, 2, 28))
    assert (
        await g.s.execute(select(Subscription.status).where(Subscription.id == second))
    ).scalar_one() == "active"


# ==============================================
# TEST PAID CLOCK IGNORES TRIAL INACTIVITY AND DUPLICATE INTERVALS
# Verify paid clock ignores trial inactivity and duplicate intervals.
# ==============================================


@pytest.mark.asyncio
async def test_paid_clock_ignores_trial_inactivity_and_duplicate_intervals(
    graph: SimpleNamespace,
) -> None:
    """Verify paid clock ignores trial inactivity and duplicate intervals."""

    from app.services.business.subscription_calendar import paid_years

    g = graph
    for cycle, start, end in [
        ("trial", moment(2010, 1, 1), moment(2015, 1, 1)),
        ("yearly", moment(2020, 1, 1), moment(2021, 1, 1)),
        ("yearly", moment(2020, 1, 1), moment(2021, 1, 1)),
    ]:
        sub = await put(
            g.s,
            Subscription,
            owner_id=g.owner,
            restaurant_id=g.restaurant,
            plan_id=g.plans["basic"],
            billing_cycle=cycle,
            amount=1,
            status="expired",
            starts_at=start,
            expires_at=end,
        )
        await put(
            g.s,
            Payment,
            owner_id=g.owner,
            restaurant_id=g.restaurant,
            subscription_id=sub,
            payment_method="ccp",
            amount=1,
            status="paid",
            paid_at=start,
        )
    assert await paid_years(session=g.s, owner_id=g.owner, now=moment(2030, 1, 1)) == 1


# ==============================================
# TEST MANUAL HISTORY REQUIRES REVIEWER AND RETAINS SOURCE AND AUTHOR
# Verify manual history requires reviewer and retains source and author.
# ==============================================


@pytest.mark.asyncio
async def test_manual_history_requires_reviewer_and_retains_source_and_author(
    graph: SimpleNamespace,
) -> None:
    """Verify manual history requires reviewer and retains source and author."""

    from sqlalchemy import insert

    from app.core.exceptions import UnauthorizedError
    from app.models.admin import Admin
    from app.models.rbac import (
        Permission,
        Role,
        role_permissions,
    )
    from app.services.business.subscription_metrics import (
        record_verified_history,
        reference,
    )

    g = graph
    end = moment(2026, 9, 1)
    source = await put(
        g.s,
        Subscription,
        owner_id=g.owner,
        restaurant_id=g.restaurant,
        plan_id=g.plans["basic"],
        billing_cycle="monthly",
        amount=1,
        status="expired",
        starts_at=end - timedelta(days=30),
        expires_at=end,
    )
    role = await put(g.s, Role, code="reviewer", name="Reviewer", is_active=True)
    permission = await put(
        g.s, Permission, code="payments.review", name="Review payments"
    )
    admin = await put(g.s, Admin, chat_id=9903001, role_id=role)
    await g.s.commit()
    with pytest.raises(ValueError, match="subscription_history_missing"):
        await reference(
            session=g.s,
            owner_id=g.owner,
            restaurant_id=g.restaurant,
            now=moment(2026, 10, 29),
        )
    args = {
        "owner_id": g.owner,
        "restaurant_id": g.restaurant,
        "source_subscription_id": source,
        "reference_start": end - timedelta(days=30),
        "reference_end": end,
        "values": {
            "products_count": 100,
            "categories_count": 10,
            "monthly_orders": 1000,
            "average_order_value": Decimal(2000),
        },
        "admin_id": admin,
        "source_reference": "SYNTHETIC-VERIFIED-LEDGER",
        "now": moment(2026, 10, 29),
    }
    with pytest.raises(UnauthorizedError):
        await record_verified_history(session=g.s, **args)
    await g.s.execute(
        insert(role_permissions).values(role_id=role, permission_id=permission)
    )
    await g.s.commit()
    with pytest.raises(ValueError, match="historical_metrics_incomplete"):
        await record_verified_history(
            session=g.s, **(args | {"values": {"products_count": 100}})
        )
    snapshot = await record_verified_history(session=g.s, **args)
    assert snapshot.parameters["manual_reconstruction"] == {
        "author_admin_id": admin,
        "source_reference": "SYNTHETIC-VERIFIED-LEDGER",
    }
    restored = await reference(
        session=g.s,
        owner_id=g.owner,
        restaurant_id=g.restaurant,
        now=moment(2026, 10, 29),
    )
    assert restored["context"] == "return"
    assert restored["monthly_orders"] == 1000


# ==============================================
# TEST CANCELLED COVERAGE USES LAST RECORDED MONTH BEFORE CANCELLATION
# Verify cancelled coverage uses last recorded month before cancellation.
# ==============================================


@pytest.mark.asyncio
async def test_cancelled_coverage_uses_last_recorded_month_before_cancellation(
    graph: SimpleNamespace,
) -> None:
    """Verify cancelled coverage uses last recorded month before cancellation."""

    from app.services.business.subscription_metrics import (
        capture_active_month,
        reference,
    )

    g = graph
    start = moment(2026, 1, 1)
    sub = await active(g, start=start, expiry=moment(2027, 1, 1))
    cancelled = moment(2026, 6, 1)
    await capture_active_month(
        session=g.s,
        owner_id=g.owner,
        restaurant_id=g.restaurant,
        source=sub,
        now=cancelled,
    )
    sub.status = "cancelled"
    sub.cancelled_at = cancelled
    await g.s.commit()
    ref = await reference(
        session=g.s,
        owner_id=g.owner,
        restaurant_id=g.restaurant,
        now=moment(2026, 7, 1),
    )
    assert ref["context"] == "return"
    assert ref["reference_end"] == cancelled
    assert ref["monthly_orders"] == 0


# ==============================================
# TEST TRIAL SCHEDULES BOTH RECIPIENTS AND ZERO LOYALTY IS DECIMAL
# Verify trial schedules both recipients and zero loyalty is decimal.
# ==============================================


@pytest.mark.asyncio
async def test_trial_schedules_both_recipients_and_zero_loyalty_is_decimal(
    graph: SimpleNamespace,
) -> None:
    """Verify trial schedules both recipients and zero loyalty is decimal."""

    from app.repositories.loyalty_discount_repo import LoyaltyDiscountRepository

    sub = await SubscriptionService(session=graph.s).create_trial_subscription(
        owner_id=graph.owner, restaurant_id=graph.restaurant
    )
    rows = list(
        (
            await graph.s.execute(
                select(SubscriptionReminder).where(
                    SubscriptionReminder.subscription_id == sub.id
                )
            )
        ).scalars()
    )
    assert len(rows) == 8
    assert {r.recipient for r in rows} == {"owner", "moulai_responsible"}
    rate = await LoyaltyDiscountRepository(session=graph.s).get_discount_for_years(
        years=0
    )
    assert rate == 0 and isinstance(rate, Decimal)
    from app.models.loyalty_discount import LoyaltyDiscount

    await put(
        graph.s,
        LoyaltyDiscount,
        owner_id=graph.owner,
        years_required=1,
        discount_percent=2,
    )
    assert await LoyaltyDiscountRepository(session=graph.s).get_discount_for_years(
        years=2, owner_id=graph.owner
    ) == Decimal(5)


# ==============================================
# TEST NOTIFICATION CONCURRENT WORKERS AND CONFIGURABLE SCHEDULE
# Verify notification concurrent workers and configurable schedule.
# ==============================================


@pytest.mark.asyncio
async def test_notification_concurrent_workers_and_configurable_schedule(
    graph: SimpleNamespace,
) -> None:
    """Verify notification concurrent workers and configurable schedule."""

    import asyncio

    sub = await active(graph)
    config = (
        await graph.s.execute(
            select(SubscriptionPricingConfig).where(SubscriptionPricingConfig.id == 1)
        )
    ).scalar_one()
    config.policies = {**config.policies, "reminder_days": [3, 0]}
    await reminders.schedule(session=graph.s, subscription=sub)
    await graph.s.commit()
    sender = SyntheticSender()
    sessions = async_sessionmaker(graph.s.bind, expire_on_commit=False)
    await asyncio.gather(
        reminders.dispatch(session_factory=sessions, sender=sender, now=sub.expires_at),
        reminders.dispatch(session_factory=sessions, sender=sender, now=sub.expires_at),
    )
    assert len(sender.calls) == 4
    assert len({call["idempotency_key"] for call in sender.calls}) == 4


# ==============================================
# TEST MISSING RESPONSIBLE RECIPIENT IS EXPLICITLY BLOCKED
# Verify missing responsible recipient is explicitly blocked.
# ==============================================


@pytest.mark.asyncio
async def test_missing_responsible_recipient_is_explicitly_blocked(
    graph: SimpleNamespace,
) -> None:
    """Verify missing responsible recipient is explicitly blocked."""

    sub = await active(graph)
    config = (
        await graph.s.execute(
            select(SubscriptionPricingConfig).where(SubscriptionPricingConfig.id == 1)
        )
    ).scalar_one()
    config.policies = {
        key: value
        for key, value in config.policies.items()
        if key != "moulai_responsible_chat_id"
    }
    await reminders.schedule(session=graph.s, subscription=sub)
    await graph.s.commit()
    blocked = (
        (
            await graph.s.execute(
                select(SubscriptionReminder).where(
                    SubscriptionReminder.recipient == "moulai_responsible"
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(blocked) == 4
    assert all(
        row.status == "blocked" and row.target_chat_id is None for row in blocked
    )


# ==============================================
# TEST MIGRATION CATALOG AND NUMERIC STORAGE
# Verify migration catalog and numeric storage.
# ==============================================


@pytest.mark.asyncio
async def test_migration_catalog_and_numeric_storage(graph: SimpleNamespace) -> None:
    """Verify migration catalog and numeric storage."""

    from sqlalchemy import text

    revision = (
        await graph.s.execute(text("SELECT version_num FROM alembic_version"))
    ).scalar_one()
    from test_support.local_postgres import LocalPostgresSettings

    expected = (
        "s1a20261028" if LocalPostgresSettings().PROFILE == "main" else "s1b20261028"
    )
    assert revision == expected
    for table, column in [
        ("subscriptions", "amount"),
        ("payments", "amount"),
        ("feature_pricing", "price"),
        ("branch_pricing", "price_per_branch"),
    ]:
        value = (
            await graph.s.execute(
                text(
                    "SELECT data_type FROM information_schema.columns WHERE table_name=:table AND column_name=:column"
                ),
                {"table": table, "column": column},
            )
        ).scalar_one()
        assert value == "numeric"
