# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# APPROVED SUBSCRIPTION RULE REGRESSIONS
# Compare configured calculations and stored evidence against approved commercial
# expectations.
# ==============================================

"""Approved commercial expectations against services and persisted synthetic rows.

Original diagnostic assertions are retained; calendar, branch and promotion
characterizations were updated only for explicit 29 October business decisions.
"""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Declare the standard-library, framework and project dependencies used below.
# ==============================================

import json
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from decimal import Decimal
from itertools import product
from pathlib import Path

import pytest
from sqlalchemy import (
    insert,
    select,
    text,
    update,
)
from sqlalchemy.orm import raiseload

from app.models.loyalty_discount import Promotion
from app.models.order import Order
from app.models.owner import Owner
from app.models.restaurant import Restaurant
from app.models.restaurant_metric import RestaurantMetric
from app.models.subscription import (
    Subscription,
    SubscriptionFeature,
    SubscriptionPlan,
)
from app.schemas.manual_payment import ManualSubscriptionCheckout
from app.services.business import pricing_service as p

from app.services.business.subscription_checkout_service import SubscriptionCheckoutService  # isort: skip  # fmt: skip
from app.services.business.subscription_service import SubscriptionService

# ==============================================
# CONFIGURATION AND CONSTANTS
# Group the existing configuration values without changing their defaults.
# ==============================================

HERE = Path("artifacts/subscription-correction-20261029")
HERE.mkdir(parents=True, exist_ok=True)

# ==============================================
# CONFIGURATION AND CONSTANTS
# Group the existing configuration values without changing their defaults.
# ==============================================

OBSERVATIONS = []


# ==============================================
# RECORD
# Persist the observed calculation and assert equality after numeric normalization.
# ==============================================


def record(name: str, actual: object, expected: object) -> None:
    """Persist the observed calculation and assert equality after numeric normalization."""

    if (
        isinstance(actual, dict)
        and isinstance(expected, dict)
        and set(expected) <= set(actual)
    ):
        actual = {key: actual[key] for key in expected}

    # ==============================================
    # CANONICAL
    # Normalize nested numeric values to Decimal while preserving booleans and
    # structure.
    # ==============================================

    def canonical(value: object) -> object:
        """Normalize nested numeric values to Decimal while preserving booleans and structure."""

        if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
            return Decimal(str(value))
        if isinstance(value, dict):
            return {key: canonical(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [canonical(item) for item in value]
        return value

    OBSERVATIONS.append(
        {
            "case": name,
            "actual": actual,
            "expected": expected,
            "pass": canonical(actual) == canonical(expected),
        }
    )
    (HERE / "observations.json").write_text(
        json.dumps(OBSERVATIONS, indent=2, default=str), encoding="utf-8"
    )
    assert canonical(actual) == canonical(
        expected
    ), f"{name}: actual={actual!r}; expected={expected!r}"


# ==============================================
# PUT
# Insert one synthetic fixture row and return its database-generated identifier.
# ==============================================


async def put(s: AsyncSession, model: type[BaseModel], **data: object) -> int:
    """Insert one synthetic fixture row and return its database-generated identifier."""

    return (
        await s.execute(insert(model.__table__).values(**data).returning(model.id))
    ).scalar_one()


from datetime import tzinfo
from types import SimpleNamespace

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import BaseModel
from app.models.subscription_pricing import SubscriptionPricingSnapshot

from app.models.subscription_pricing_legacy import LegacySubscriptionPricingConfig as SubscriptionPricingConfig  # isort: skip  # fmt: skip

from app.schemas.payment import PaymentResponse
from app.services.business.subscription_types import (
    NumericInput,
    PricingResult,
)
from test_support.subscription_fixtures import (
    closed_trial,
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
# QUOTE
# Calculate a synthetic quotation with explicit scenario overrides and record rejected
# inputs.
# ==============================================


async def quote(
    g: SimpleNamespace, code: str = "basic", **changes: object
) -> PricingResult:
    """Calculate a synthetic quotation with explicit scenario overrides and record rejected inputs."""

    args = {
        "session": g.s,
        "now": g.quote_time,
        "owner_id": g.owner,
        "restaurant_id": g.restaurant,
        "plan_id": g.plans[code],
        "billing_cycle": "monthly",
        "payment_method": "electronic",
        "restaurants_count": 1,
        "branches_count": 1,
        "years_with_platform": 0,
        "products_count": 100,
        "categories_count": 10,
        "monthly_orders": 1000,
        "average_order_value": 2000,
        "additional_feature_ids": [g.f["extra"]],
    }
    args.update(changes)
    try:
        return await p.calculate_subscription_pricing(**args)
    except ValueError as e:
        return {"error": str(e)}


# Constants independently supplied/calculated from the user's golden monthly amounts.

# ==============================================
# CONFIGURATION AND CONSTANTS
# Group the existing configuration values without changing their defaults.
# ==============================================

MATRIX = {
    "basic": [(5880, 6120), (17640, 18360), (35280, 36720), (58800, 61200)],
    "professional": [
        (7717.5, 8032.5),
        (23152.5, 24097.5),
        (46305, 48195),
        (77175, 80325),
    ],
    "enterprise": [(9016, 9384), (27048, 28152), (54096, 56304), (90160, 93840)],
}
CYCLES = ["monthly", "quarterly", "semiannual", "yearly"]


# ==============================================
# TEST 24 COMMERCIAL COMBINATIONS
# Verify 24 commercial combinations.
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "code,cycle_index,mode_index", list(product(MATRIX, range(4), range(2)))
)
async def test_24_commercial_combinations(
    graph: SimpleNamespace, code: str, cycle_index: int, mode_index: int
) -> None:
    """Verify 24 commercial combinations."""

    mode = ["electronic", "cash"][mode_index]
    result = await quote(
        graph, code, billing_cycle=CYCLES[cycle_index], payment_method=mode
    )
    record(
        f"matrix:{code}:{CYCLES[cycle_index]}:{mode}",
        result.get("final_amount_due", result),
        MATRIX[code][cycle_index][mode_index],
    )


# ==============================================
# TEST GOLDEN BREAKDOWN
# Verify golden breakdown.
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "code,years,count,expected",
    [
        (
            "professional",
            2,
            3,
            {
                "base_price": 5375,
                "restaurant_score": 2500,
                "value_before_discounts": 7875,
                "loyalty_discount": 393.75,
                "multi_restaurant_discount": 393.75,
                "promotion_discount": 787.5,
                "discount_price": 1575,
                "multi_branch_cost": 1000,
                "final_price": 73000,
                "payment_adjustment": -1460,
                "final_amount_due": 71540,
            },
        ),
        (
            "enterprise",
            3,
            10,
            {
                "base_price": 6700,
                "restaurant_score": 2500,
                "value_before_discounts": 9200,
                "loyalty_discount": 736,
                "multi_restaurant_discount": 1380,
                "promotion_discount": 920,
                "discount_price": 3036,
                "multi_branch_cost": 1000,
                "final_price": 71640,
                "payment_adjustment": -1432.8,
                "final_amount_due": 70207.2,
            },
        ),
    ],
)
async def test_golden_breakdown(
    graph: SimpleNamespace, code: str, years: int, count: int, expected: object
) -> None:
    """Verify golden breakdown."""

    await put(
        graph.s, Promotion, name="Synthetic promotion", discount_percent=10, active=True
    )
    await graph.s.commit()
    actual = await quote(
        graph,
        code,
        billing_cycle="yearly",
        years_with_platform=years,
        restaurants_count=count,
        branches_count=3,
    )
    cash = await quote(
        graph,
        code,
        billing_cycle="yearly",
        payment_method="cash",
        years_with_platform=years,
        restaurants_count=count,
        branches_count=3,
    )
    OBSERVATIONS.append(
        {
            "case": f"golden-cash:{code}",
            "actual": cash,
            "expected_due": 74460 if code == "professional" else 73072.8,
        }
    )
    record(f"golden:{code}", actual, expected)


# ==============================================
# TEST BASIC ZERO ORDERS
# Verify basic zero orders.
# ==============================================


@pytest.mark.asyncio
async def test_basic_zero_orders(graph: SimpleNamespace) -> None:
    """Verify basic zero orders."""

    a = await quote(
        graph,
        products_count=50,
        categories_count=5,
        monthly_orders=0,
        average_order_value=0,
    )
    b = await quote(
        graph,
        products_count=50,
        categories_count=5,
        monthly_orders=0,
        average_order_value=0,
        payment_method="cash",
    )
    record(
        "basic-zero-orders",
        [
            a["base_price"],
            a["restaurant_score"],
            a["final_amount_due"],
            b["final_amount_due"],
        ],
        [3500, 650, 4067, 4233],
    )


# ==============================================
# TEST FEATURE LAYERS AND DEDUP
# Verify feature layers and dedup.
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "code,extras,expected",
    [
        ("basic", [], 3000),
        ("basic", ["extra"], 3500),
        ("basic", ["extra", "extra_two"], 3750),
        ("professional", [], 4900),
        ("professional", ["analytics"], 5375),
        ("professional", ["extra", "extra_two"], 5612.5),
        ("enterprise", [], 6250),
        ("enterprise", ["extra"], 6700),
        ("enterprise", ["extra", "extra_two"], 6925),
        ("basic", ["extra", "extra"], 3500),
        ("professional", ["orders"], 4900),
        ("enterprise", ["analytics"], 6250),
    ],
)
async def test_feature_layers_and_dedup(
    graph: SimpleNamespace, code: str, extras: list[str], expected: object
) -> None:
    """Verify feature layers and dedup."""

    a = await quote(graph, code, additional_feature_ids=[graph.f[k] for k in extras])
    record(f"features:{code}:{extras}", a["base_price"], expected)


# ==============================================
# TEST BASE IS DATABASE CONFIGURABLE
# Verify base is database configurable.
# ==============================================


@pytest.mark.asyncio
async def test_base_is_database_configurable(graph: SimpleNamespace) -> None:
    """Verify base is database configurable."""

    before = await quote(graph)
    await graph.s.execute(
        update(SubscriptionPricingConfig)
        .where(SubscriptionPricingConfig.id == 1)
        .values(base_price=3200)
    )
    await graph.s.commit()
    after = await quote(graph)
    record("persisted-base-change", after["base_price"] - before["base_price"], 200)


# ==============================================
# TEST RESTAURANT TIERS
# Verify restaurant tiers.
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "count,expected", [(1, 0), (2, 0), (3, 300), (9, 300), (10, 900), (11, 900)]
)
async def test_restaurant_tiers(
    graph: SimpleNamespace, count: int, expected: object
) -> None:
    """Verify restaurant tiers."""

    value = await p.calculate_multi_restaurant_discount(
        session=graph.s, restaurants_count=count, amount=Decimal(6000)
    )
    record(f"restaurant-tier:{count}", float(value), expected)


# ==============================================
# TEST LOYALTY THRESHOLDS
# Verify loyalty thresholds.
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "threshold,rate", [(1, 2), (2, 5), (3, 8), (4, 11), (5, 15), (10, 20), (15, 25)]
)
async def test_loyalty_thresholds(
    graph: SimpleNamespace, threshold: int, rate: int
) -> None:
    # Service accepts years, not anniversary dates: probe just below/exactly/above.
    """Verify loyalty thresholds."""

    values = []
    for years in [threshold - 0.0001, threshold, threshold + 0.0001]:
        values.append(
            float(
                await p.calculate_loyalty_discount(
                    session=graph.s, years_with_platform=years, amount=Decimal(100)
                )
            )
        )
    prior = {1: 0, 2: 2, 3: 5, 4: 8, 5: 11, 10: 15, 15: 20}[threshold]
    record(f"loyalty-current-inclusive:{threshold}", values, [prior, rate, rate])


# ==============================================
# TEST BRANCH TIERS
# Verify branch tiers.
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "count,expected",
    [(0, 0), (1, 0), (2, 500), (3, 1000), (4, 1500), (9, 3600), (10, 4000), (11, 4400)],
)
async def test_branch_tiers(
    graph: SimpleNamespace, count: int, expected: object
) -> None:
    """Verify branch tiers."""

    a = await p.calculate_multi_branch_cost(session=graph.s, branches_count=count)
    record(f"branch-approved-progressive-tier:{count}", float(a), expected)


# ==============================================
# TEST DISCOUNTS SHARE VAL
# Verify discounts share val.
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "rates",
    [
        (True, False, False),
        (False, True, False),
        (False, False, True),
        (True, True, False),
        (True, False, True),
        (False, True, True),
        (True, True, True),
    ],
)
async def test_discounts_share_val(
    graph: SimpleNamespace, rates: tuple[bool, bool, bool]
) -> None:
    """Verify discounts share val."""

    l, m, promo = rates
    if promo:
        await put(
            graph.s, Promotion, name="Synthetic", discount_percent=10, active=True
        )
        await graph.s.commit()
    a = await quote(
        graph,
        years_with_platform=2 if l else 0,
        restaurants_count=3 if m else 1,
        branches_count=3,
    )
    # Val is independently 6000 in the Basic fixture.
    expected = (
        6000 - (300 if l else 0) - (300 if m else 0) - (600 if promo else 0) + 1000
    )
    record(f"same-Val:{rates}", a["final_price"], expected)


# ==============================================
# TEST PROMOTION SELECTION
# Verify promotion selection.
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kind,expected",
    [
        ("none", 0),
        ("active", 600),
        ("future", 0),
        ("expired", 0),
        ("simultaneous", 1200),
        ("foreign-restaurant", 0),
    ],
)
async def test_promotion_selection(
    graph: SimpleNamespace, kind: str, expected: object
) -> None:
    """Verify promotion selection."""

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if kind != "none":
        values = {"name": kind, "discount_percent": 10, "active": True}
        if kind == "future":
            values["starts_at"] = now + timedelta(days=1)
        if kind == "expired":
            values["expires_at"] = now - timedelta(days=1)
        if kind == "foreign-restaurant":
            values["restaurant_id"] = graph.second
        await put(graph.s, Promotion, **values)
        if kind == "simultaneous":
            await put(
                graph.s, Promotion, name="latest", discount_percent=20, active=True
            )
        await graph.s.commit()
    a = await quote(graph)
    record(f"promotion:{kind}", a["promotion_discount"], expected)


# ==============================================
# TEST SCORES
# Verify scores.
# ==============================================


@pytest.mark.parametrize(
    "metrics,expected",
    [
        (
            {
                "products_count": 0,
                "categories_count": 0,
                "monthly_orders": 0,
                "average_order_value": 0,
            },
            0,
        ),
        (
            {
                "products_count": 1,
                "categories_count": 1,
                "monthly_orders": 1,
                "average_order_value": 100,
            },
            51,
        ),
        (
            {
                "products_count": 100,
                "categories_count": 10,
                "monthly_orders": 1000,
                "average_order_value": 2000,
            },
            2500,
        ),
        (
            {
                "products_count": 100000,
                "categories_count": 10000,
                "monthly_orders": 1000000,
                "average_order_value": 100000,
            },
            2310000,
        ),
    ],
)
def test_scores(metrics: dict[str, NumericInput], expected: object) -> None:
    """Verify scores."""

    record(f"score:{metrics}", float(p.calculate_restaurant_score(**metrics)), expected)


# ==============================================
# TEST INVALID METRICS REJECTED
# Verify invalid metrics rejected.
# ==============================================


@pytest.mark.parametrize(
    "field,value",
    [
        ("products_count", -1),
        ("categories_count", -1),
        ("monthly_orders", -1),
        ("average_order_value", -1),
        ("average_order_value", float("nan")),
        ("average_order_value", float("inf")),
    ],
)
def test_invalid_metrics_rejected(field: str, value: object) -> None:
    """Verify invalid metrics rejected."""

    args = {
        "products_count": 0,
        "categories_count": 0,
        "monthly_orders": 0,
        "average_order_value": 0,
    }
    args[field] = value
    try:
        p.calculate_restaurant_score(**args)
        rejected = False
    except (ValueError, TypeError, ArithmeticError):
        rejected = True
    record(f"invalid-metric:{field}:{value}", rejected, True)


# ==============================================
# SERVICE
# Bind the subscription service and its query options to the synthetic test session.
# ==============================================


def service(g: SimpleNamespace) -> SubscriptionService:
    """Bind the subscription service and its query options to the synthetic test session."""

    svc = SubscriptionService(session=g.s)
    for repo in [svc.repo, svc.owner_repo, svc.plan_repo]:
        repo.query_options = [raiseload("*")]
    return svc


# ==============================================
# TEST TRIAL ONCE PER OWNER SEQUENTIALLY
# Verify trial once per owner sequentially.
# ==============================================


@pytest.mark.asyncio
async def test_trial_once_per_owner_sequentially(graph: SimpleNamespace) -> None:
    """Verify trial once per owner sequentially."""

    svc = service(graph)
    first = await svc.create_trial_subscription(
        owner_id=graph.owner, restaurant_id=graph.restaurant
    )
    await graph.s.execute(
        update(Subscription).where(Subscription.id == first.id).values(status="expired")
    )
    await graph.s.commit()
    outcomes = []
    for restaurant in [graph.restaurant, graph.second]:
        try:
            await svc.create_trial_subscription(
                owner_id=graph.owner, restaurant_id=restaurant
            )
            outcomes.append("accepted")
        except ValueError as e:
            outcomes.append(str(e))
    record("trial-once-owner", outcomes, ["trial_already_used", "trial_already_used"])


# ==============================================
# TEST TRIAL EFFECTIVE FEATURES
# Verify trial effective features.
# ==============================================


@pytest.mark.asyncio
async def test_trial_effective_features(graph: SimpleNamespace) -> None:
    """Verify trial effective features."""

    first = await service(graph).create_trial_subscription(
        owner_id=graph.owner, restaurant_id=graph.restaurant
    )
    active = list(
        (
            await graph.s.execute(
                select(SubscriptionFeature.feature_id).where(
                    SubscriptionFeature.subscription_id == first.id
                )
            )
        ).scalars()
    )
    record(
        "trial-effective-grants",
        sorted(active),
        sorted(
            graph.f[k]
            for k in [
                "qr_menu",
                "categories",
                "products",
                "hosting",
                "dashboard",
                "basic_support",
                "orders",
                "delivery",
            ]
        ),
    )


# ==============================================
# CHECKOUT WITH CAPTURE
# Run synthetic checkout while capturing the actual pricing inputs passed by the
# service.
# ==============================================


async def checkout_with_capture(
    g: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, cycle: str = "monthly"
) -> tuple[PaymentResponse, dict[str, object]]:
    """Run synthetic checkout while capturing the actual pricing inputs passed by the service."""

    from app.services.business import subscription_checkout_service as checkout_module

    if not (
        await g.s.execute(
            select(Subscription.id).where(Subscription.restaurant_id == g.restaurant)
        )
    ).first():
        end = checkout_module.datetime.now(timezone.utc).replace(
            tzinfo=None
        ) - timedelta(microseconds=1)
        await closed_trial(g, end=end)
    captured = {}
    original = SubscriptionService.create_pending_subscription

    # ==============================================
    # TRACED
    # Capture delegated keyword arguments and execute the original test-bound operation.
    # ==============================================

    async def traced(self, **kwargs: object) -> dict[str, object]:
        """Capture delegated keyword arguments and execute the original test-bound operation."""

        captured.update(kwargs)
        return await original(self, **kwargs)

    monkeypatch.setattr(SubscriptionService, "create_pending_subscription", traced)
    result = await SubscriptionCheckoutService(session=g.s).create(
        owner_id=g.owner,
        data=ManualSubscriptionCheckout(
            restaurant_id=g.restaurant,
            plan_id=g.plans["basic"],
            billing_cycle=cycle,
            payment_method="ccp",
        ),
    )
    return result, captured


# ==============================================
# TEST METRIC WINDOW COMPLETION STATUS NET VALUE
# Verify metric window completion status net value.
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("cycle", ["monthly", "yearly"])
async def test_metric_window_completion_status_net_value(
    graph: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, cycle: str
) -> None:
    """Verify metric window completion status net value."""

    from app.models.order_item import OrderStatusHistory
    from app.services.business import subscription_checkout_service as checkout

    fixed = datetime(2026, 10, 28, 12, tzinfo=timezone.utc).replace(tzinfo=None)

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

            return fixed.replace(tzinfo=timezone.utc) if tz else fixed

    monkeypatch.setattr(checkout, "datetime", Clock)
    start = fixed - timedelta(days=30)
    # created time, completion time, status, gross total, net eligible amount
    rows = [
        (start - timedelta(days=5), start + timedelta(days=1), "completed", 1250, 900),
        (start, start, "completed", 2150, 1800),
        (fixed - timedelta(seconds=1), fixed, "completed", 3050, 2700),
        (fixed + timedelta(days=1), fixed + timedelta(days=1), "completed", 4050, 3600),
        (start + timedelta(days=2), None, "cancelled", 9999, 9999),
        (start + timedelta(days=2), None, "pending", 9999, 9999),
        (
            start - timedelta(days=10),
            start - timedelta(seconds=1),
            "completed",
            5050,
            4500,
        ),
    ]
    for index, (created, completed, status, total, net) in enumerate(rows):
        order = await put(
            graph.s,
            Order,
            restaurant_id=graph.restaurant,
            order_number=f"SYN-{index}",
            order_type="dine_in",
            status=status,
            total_amount=total,
            subtotal_amount=net + 100,
            discount_amount=100,
            tax_amount=100,
            delivery_amount=total - net - 100,
            created_at=created,
        )
        if completed:
            await put(
                graph.s,
                OrderStatusHistory,
                order_id=order,
                new_status="completed",
                created_at=completed,
            )
    await graph.s.commit()
    _invoice, actual = await checkout_with_capture(graph, monkeypatch, cycle)
    record(
        f"checkout-metrics:{cycle}",
        {
            k: actual[k]
            for k in [
                "products_count",
                "categories_count",
                "monthly_orders",
                "average_order_value",
            ]
        },
        {
            "products_count": 0,
            "categories_count": 0,
            "monthly_orders": 2,
            "average_order_value": 1350,
        },
    )


# ==============================================
# TEST RETURN PRESERVES LAST ACTIVE METRICS
# Verify return preserves last active metrics.
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("days", [7, 400])
async def test_return_preserves_last_active_metrics(
    graph: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, days: int
) -> None:
    """Verify return preserves last active metrics."""

    end = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    await put(
        graph.s,
        Subscription,
        owner_id=graph.owner,
        restaurant_id=graph.restaurant,
        plan_id=graph.plans["basic"],
        billing_cycle="monthly",
        amount=1,
        status="expired",
        starts_at=end - timedelta(days=30),
        expires_at=end,
    )
    await graph.s.execute(
        insert(RestaurantMetric.__table__).values(
            restaurant_id=graph.restaurant,
            products_count=100,
            categories_count=10,
            monthly_orders=1000,
            average_order_value=2000,
        )
    )
    source_id = (
        await graph.s.execute(
            select(Subscription.id).where(
                Subscription.restaurant_id == graph.restaurant
            )
        )
    ).scalar_one()
    graph.s.add(
        SubscriptionPricingSnapshot(
            owner_id=graph.owner,
            restaurant_id=graph.restaurant,
            source_subscription_id=source_id,
            reference_start=end - timedelta(days=30),
            reference_end=end,
            context="active_month",
            calculated_at=end,
            products_count=100,
            categories_count=10,
            monthly_orders=1000,
            average_order_value=2000,
            pricing={},
            parameters={},
        )
    )
    await graph.s.execute(
        update(Owner).where(Owner.id == graph.owner).values(trial_used=True)
    )
    await graph.s.commit()
    _, a = await checkout_with_capture(graph, monkeypatch)
    record(
        f"return-historical-metrics:{days}",
        [
            a[k]
            for k in [
                "products_count",
                "categories_count",
                "monthly_orders",
                "average_order_value",
            ]
        ],
        [100, 10, 1000, 2000],
    )


# ==============================================
# TEST SNAPSHOT PERSISTENCE CONTRACT
# Verify snapshot persistence contract.
# ==============================================


@pytest.mark.asyncio
async def test_snapshot_persistence_contract(graph: SimpleNamespace) -> None:
    """Verify snapshot persistence contract."""

    names = set(
        (
            await graph.s.execute(
                text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
                )
            )
        ).scalars()
    )
    # Search every actual table for the required indicators and reference period.
    columns = (
        await graph.s.execute(
            text(
                "SELECT table_name,column_name FROM information_schema.columns WHERE table_schema='public'"
            )
        )
    ).all()
    mapping = {name: set() for name in names}
    for table, column in columns:
        mapping[table].add(column)
    required = {
        "products_count",
        "categories_count",
        "monthly_orders",
        "average_order_value",
        "owner_id",
        "restaurant_id",
    }
    matches = [table for table, cols in mapping.items() if required <= cols]
    record("historical-snapshot-tables", bool(matches), True)


# ==============================================
# TEST STORED AMOUNT AND CHECKOUT RETRY STABLE
# Verify stored amount and checkout retry stable.
# ==============================================


@pytest.mark.asyncio
async def test_stored_amount_and_checkout_retry_stable(graph: SimpleNamespace) -> None:
    """Verify stored amount and checkout retry stable."""

    await closed_trial(graph)
    data = ManualSubscriptionCheckout(
        restaurant_id=graph.restaurant,
        plan_id=graph.plans["basic"],
        payment_method="ccp",
    )
    checkout = SubscriptionCheckoutService(session=graph.s)
    first = await checkout.create(owner_id=graph.owner, data=data)
    await graph.s.execute(
        update(SubscriptionPlan)
        .where(SubscriptionPlan.id == graph.plans["basic"])
        .values(base_price=9999)
    )
    await graph.s.commit()
    again = await checkout.create(owner_id=graph.owner, data=data)
    record(
        "pending-checkout-idempotency-stored-price",
        [again.id, again.amount],
        [first.id, first.amount],
    )


# ==============================================
# TEST RESTAURANT TYPE INVARIANCE
# Verify restaurant type invariance.
# ==============================================


@pytest.mark.asyncio
async def test_restaurant_type_invariance(graph: SimpleNamespace) -> None:
    """Verify restaurant type invariance."""

    first = await quote(graph)
    await graph.s.execute(
        update(Restaurant)
        .where(Restaurant.id == graph.restaurant)
        .values(type="Enterprise")
    )
    await graph.s.commit()
    second = await quote(graph)
    record("restaurant-type-invariance", second, first)


# ==============================================
# TEST DECIMAL CENT ROUNDING
# Verify decimal cent rounding.
# ==============================================


@pytest.mark.asyncio
async def test_decimal_cent_rounding(graph: SimpleNamespace) -> None:
    """Verify decimal cent rounding."""

    await graph.s.execute(
        update(SubscriptionPricingConfig)
        .where(SubscriptionPricingConfig.id == 1)
        .values(base_price=3000.01)
    )
    await graph.s.commit()
    actual = await quote(
        graph,
        products_count=0,
        categories_count=0,
        monthly_orders=0,
        average_order_value=0,
        additional_feature_ids=[],
    )
    record("pricing-cent-rounding", actual["final_amount_due"], 2940.01)
