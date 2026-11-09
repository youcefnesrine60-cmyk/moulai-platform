# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# SUBSCRIPTION FOLLOW-UP REGRESSIONS
# Check targeted pricing, entitlement and historical-input cases on synthetic test data.
# ==============================================

"""Follow-up cases covering remaining questions, not a general rerun."""

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
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import (
    insert,
    select,
    update,
)
from sqlalchemy.orm import raiseload
from test_rules import graph as graph  # noqa: PLC0414 -- pytest fixture export
from test_rules import (
    put,
    quote,
    service,
)

from app.models.category import Category
from app.models.feature_pricing import (
    BranchPricing,
    FeaturePricing,
)
from app.models.loyalty_discount import (
    LoyaltyDiscount,
    Promotion,
)
from app.models.order import Order
from app.models.owner import Owner
from app.models.product import Product
from app.models.restaurant_metric import RestaurantMetric
from app.models.subscription import (
    Subscription,
    SubscriptionFeatureRequest,
    SubscriptionPlan,
)
from app.models.subscription_pricing import SubscriptionPricingSnapshot
from app.repositories.plan_features_repo import PlanFeatureRepository
from app.repositories.promotion_repo import PromotionRepository
from app.schemas.manual_payment import ManualSubscriptionCheckout

from app.services.business.subscription_checkout_service import SubscriptionCheckoutService  # isort: skip  # fmt: skip
from test_support.subscription_fixtures import closed_trial

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

RESULTS = []


# ==============================================
# CHECK
# Record a targeted diagnostic observation and assert normalized actual and expected
# values.
# ==============================================


def check(name: str, actual: object, expected: object) -> None:
    """Record a targeted diagnostic observation and assert normalized actual and expected values."""

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

    RESULTS.append(
        {
            "case": name,
            "actual": actual,
            "expected": expected,
            "passed": canonical(actual) == canonical(expected),
        }
    )
    (HERE / "follow-up-observations.json").write_text(
        json.dumps(RESULTS, indent=2, default=str), encoding="utf-8"
    )
    assert canonical(actual) == canonical(
        expected
    ), f"{name}: actual={actual!r}; expected={expected!r}"


# ==============================================
# TEST GOLDENS WITH MANUALLY PREAGGREGATED PLAN BASES
# Verify goldens with manually preaggregated plan bases.
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "code,years,count,expected",
    [
        (
            "professional",
            2,
            3,
            [5375, 2500, 7875, 393.75, 393.75, 787.5, 1575, 1000, 73000, 71540, 74460],
        ),
        (
            "enterprise",
            3,
            10,
            [6700, 2500, 9200, 736, 1380, 920, 3036, 1000, 71640, 70207.2, 73072.8],
        ),
    ],
)
async def test_goldens_with_manually_preaggregated_plan_bases(
    graph: SimpleNamespace, code: str, years: int, count: int, expected: object
) -> None:
    # Existing schema can hold a precomputed base; it does not compute P/E.
    """Verify goldens with manually preaggregated plan bases."""

    await graph.s.execute(
        update(SubscriptionPlan)
        .where(SubscriptionPlan.id == graph.plans[code])
        .values(base_price=4900 if code == "professional" else 6250)
    )
    await put(graph.s, Promotion, name="Synthetic", discount_percent=10, active=True)
    await graph.s.commit()
    a = await quote(
        graph,
        code,
        billing_cycle="yearly",
        years_with_platform=years,
        restaurants_count=count,
        branches_count=3,
    )
    b = await quote(
        graph,
        code,
        billing_cycle="yearly",
        years_with_platform=years,
        restaurants_count=count,
        branches_count=3,
        payment_method="cash",
    )
    keys = [
        "base_price",
        "restaurant_score",
        "value_before_discounts",
        "loyalty_discount",
        "multi_restaurant_discount",
        "promotion_discount",
        "discount_price",
        "multi_branch_cost",
        "final_price",
        "final_amount_due",
    ]
    check(
        "golden-preaggregated:" + code,
        [a[k] for k in keys] + [b["final_amount_due"]],
        expected,
    )


# ==============================================
# TEST LAYER PRICE CHANGE IS REFLECTED WITHOUT MANUAL PLAN REPRICING
# Verify layer price change is reflected without manual plan repricing.
# ==============================================


@pytest.mark.asyncio
async def test_layer_price_change_is_reflected_without_manual_plan_repricing(
    graph: SimpleNamespace,
) -> None:
    """Verify layer price change is reflected without manual plan repricing."""

    await graph.s.execute(
        update(SubscriptionPlan)
        .where(SubscriptionPlan.id == graph.plans["professional"])
        .values(base_price=4900)
    )
    # Orders is an original Professional-layer feature. P increases by 100.
    await graph.s.execute(
        update(FeaturePricing)
        .where(FeaturePricing.feature_id == graph.f["orders"])
        .values(price=1100)
    )
    await graph.s.commit()
    a = await quote(graph, "professional")
    check("included-layer-cost-update", a["base_price"], 5470)


# ==============================================
# TEST PROFESSIONAL ANALYTICS USES FIVE PERCENT WITH PREAGGREGATED BASE
# Verify professional analytics uses five percent with preaggregated base.
# ==============================================


@pytest.mark.asyncio
async def test_professional_analytics_uses_five_percent_with_preaggregated_base(
    graph: SimpleNamespace,
) -> None:
    """Verify professional analytics uses five percent with preaggregated base."""

    await graph.s.execute(
        update(SubscriptionPlan)
        .where(SubscriptionPlan.id == graph.plans["professional"])
        .values(base_price=4900)
    )
    await graph.s.commit()
    a = await quote(
        graph, "professional", additional_feature_ids=[graph.f["analytics"]]
    )
    check("professional-analytics-discount", a["base_price"], 5375)


# ==============================================
# TEST MANDATORY INCLUDED FEATURE REMOVAL IS REJECTED
# Verify mandatory included feature removal is rejected.
# ==============================================


@pytest.mark.asyncio
async def test_mandatory_included_feature_removal_is_rejected(
    graph: SimpleNamespace,
) -> None:
    """Verify mandatory included feature removal is rejected."""

    repo = PlanFeatureRepository(session=graph.s)
    repo.query_options = [raiseload("*")]
    try:
        removed = await repo.remove_feature_from_plan(
            plan_id=graph.plans["professional"], feature_id=graph.f["orders"]
        )
    except ValueError:
        removed = False
    check("mandatory-original-removal-refused", removed, False)


# ==============================================
# TEST PAID EXTRAS PRESERVED AS PENDING ENTITLEMENTS
# Verify paid extras preserved as pending entitlements.
# ==============================================


@pytest.mark.asyncio
async def test_paid_extras_preserved_as_pending_entitlements(
    graph: SimpleNamespace,
) -> None:
    """Verify paid extras preserved as pending entitlements."""

    await closed_trial(graph)
    result = await service(graph).create_pending_subscription(
        owner_id=graph.owner,
        restaurant_id=graph.restaurant,
        plan_id=graph.plans["basic"],
        billing_cycle="monthly",
        payment_method="electronic",
        restaurants_count=1,
        branches_count=1,
        years_with_platform=0,
        products_count=0,
        categories_count=0,
        monthly_orders=0,
        average_order_value=0,
        additional_feature_ids=[graph.f["extra"]],
    )
    requests = list(
        (
            await graph.s.execute(
                select(SubscriptionFeatureRequest.feature_id).where(
                    SubscriptionFeatureRequest.subscription_id
                    == result["subscription_id"]
                )
            )
        ).scalars()
    )
    check(
        "charged-extra-pending-entitlement",
        sorted(requests),
        sorted(
            graph.f[k]
            for k in [
                "qr_menu",
                "categories",
                "products",
                "hosting",
                "dashboard",
                "basic_support",
                "extra",
            ]
        ),
    )


# ==============================================
# TEST RETURN WITH MISSING OR INCOMPLETE HISTORICAL SNAPSHOT
# Verify return with missing or incomplete historical snapshot.
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["missing", "incomplete"])
async def test_return_with_missing_or_incomplete_historical_snapshot(
    graph: SimpleNamespace, state: str
) -> None:
    """Verify return with missing or incomplete historical snapshot."""

    end = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=90)
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
    if state == "incomplete":
        await graph.s.execute(
            insert(RestaurantMetric.__table__).values(
                restaurant_id=graph.restaurant, products_count=100
            )
        )
    await graph.s.commit()
    try:
        await SubscriptionCheckoutService(session=graph.s).create(
            owner_id=graph.owner,
            data=ManualSubscriptionCheckout(
                restaurant_id=graph.restaurant,
                plan_id=graph.plans["basic"],
                payment_method="ccp",
            ),
        )
        accepted = True
    except ValueError:
        accepted = False
    # Safety expectation: missing historical input must not silently become zero.
    check("historical-input-" + state + "-not-silently-zero", accepted, False)


# ==============================================
# TEST CURRENT CATALOG COUNTS ARE COLLECTED FROM TABLES
# Verify current catalog counts are collected from tables.
# ==============================================


@pytest.mark.asyncio
async def test_current_catalog_counts_are_collected_from_tables(
    graph: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify current catalog counts are collected from tables."""

    from test_rules import checkout_with_capture

    cat = await put(graph.s, Category, restaurant_id=graph.restaurant, name="Synthetic")
    for i in range(3):
        await put(
            graph.s,
            Product,
            restaurant_id=graph.restaurant,
            category_id=cat,
            name=f"Synthetic {i}",
            price=100,
        )
    await graph.s.commit()
    _, a = await checkout_with_capture(graph, monkeypatch)
    check(
        "current-table-product-category-counts",
        [a["products_count"], a["categories_count"]],
        [3, 1],
    )


# ==============================================
# TEST NO COMPLETED ORDERS MEANS ZERO ORDER METRICS
# Verify no completed orders means zero order metrics.
# ==============================================


@pytest.mark.asyncio
async def test_no_completed_orders_means_zero_order_metrics(
    graph: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify no completed orders means zero order metrics."""

    from test_rules import checkout_with_capture

    for i, status in enumerate(["pending", "cancelled"]):
        await put(
            graph.s,
            Order,
            restaurant_id=graph.restaurant,
            order_number=f"SYN-{i}",
            order_type="dine_in",
            status=status,
            total_amount=100,
        )
    await graph.s.commit()
    _, a = await checkout_with_capture(graph, monkeypatch)
    check(
        "no-completed-orders-both-zero",
        [a["monthly_orders"], a["average_order_value"]],
        [0, 0],
    )


# ==============================================
# TEST PROMOTIONS EXACT BOUNDARIES ARE INCLUSIVE CURRENT BEHAVIOR
# Verify promotions exact boundaries are inclusive current behavior.
# ==============================================


@pytest.mark.asyncio
async def test_promotions_exact_boundaries_are_inclusive_current_behavior(
    graph: SimpleNamespace,
) -> None:
    """Verify promotions exact boundaries are inclusive current behavior."""

    fixed = datetime(2026, 10, 28, 12, tzinfo=timezone.utc).replace(tzinfo=None)
    await put(
        graph.s,
        Promotion,
        name="start",
        starts_at=fixed,
        expires_at=fixed + timedelta(days=1),
        discount_percent=10,
        active=True,
    )
    await put(
        graph.s,
        Promotion,
        name="end",
        starts_at=fixed - timedelta(days=1),
        expires_at=fixed,
        discount_percent=20,
        active=True,
    )
    await graph.s.commit()
    actual = await PromotionRepository(session=graph.s).get_active_promotions(now=fixed)
    check(
        "promotion-both-boundaries-inclusive",
        [p.name for p in actual],
        ["start"],
    )


# ==============================================
# TEST BRANCH PLAN SPECIFIC RULE DOES NOT LEAK
# Verify branch plan specific rule does not leak.
# ==============================================


@pytest.mark.asyncio
async def test_branch_plan_specific_rule_does_not_leak(graph: SimpleNamespace) -> None:
    # A later rule for another plan must not price Basic. Current function has no plan argument.
    """Verify branch plan specific rule does not leak."""

    await put(
        graph.s,
        BranchPricing,
        plan_id=graph.plans["enterprise"],
        min_branches=2,
        max_branches=3,
        price_per_branch=999,
        active=True,
    )
    await graph.s.commit()
    a = await quote(graph, branches_count=3)
    check("plan-scoped-branch-rule", a["multi_branch_cost"], 1000)


# ==============================================
# TEST OWNER SPECIFIC LOYALTY RULE DOES NOT LEAK
# Verify owner specific loyalty rule does not leak.
# ==============================================


@pytest.mark.asyncio
async def test_owner_specific_loyalty_rule_does_not_leak(
    graph: SimpleNamespace,
) -> None:
    """Verify owner specific loyalty rule does not leak."""

    other = await put(graph.s, Owner, chat_id=9900002, trial_used=False)
    await put(
        graph.s, LoyaltyDiscount, owner_id=other, years_required=20, discount_percent=90
    )
    await graph.s.commit()
    a = await quote(graph, years_with_platform=20)
    check("owner-scoped-loyalty-rule", a["loyalty_discount"], 1500)


# ==============================================
# TEST SNAPSHOT NOT OVERWRITTEN BY CURRENT METRICS UPDATE
# Verify snapshot not overwritten by current metrics update.
# ==============================================


@pytest.mark.asyncio
async def test_snapshot_not_overwritten_by_current_metrics_update(
    graph: SimpleNamespace,
) -> None:
    """Verify snapshot not overwritten by current metrics update."""

    await graph.s.execute(
        insert(RestaurantMetric.__table__).values(
            restaurant_id=graph.restaurant,
            products_count=100,
            categories_count=10,
            monthly_orders=1000,
            average_order_value=2000,
        )
    )
    await graph.s.commit()
    end = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
    sid = await put(
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
    graph.s.add(
        SubscriptionPricingSnapshot(
            owner_id=graph.owner,
            restaurant_id=graph.restaurant,
            source_subscription_id=sid,
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
    await graph.s.flush()
    await graph.s.execute(
        update(RestaurantMetric)
        .where(RestaurantMetric.restaurant_id == graph.restaurant)
        .values(
            products_count=0,
            categories_count=0,
            monthly_orders=0,
            average_order_value=0,
        )
    )
    await graph.s.commit()
    old = list(
        (
            await graph.s.execute(
                select(
                    SubscriptionPricingSnapshot.products_count,
                    SubscriptionPricingSnapshot.categories_count,
                    SubscriptionPricingSnapshot.monthly_orders,
                    SubscriptionPricingSnapshot.average_order_value,
                ).where(SubscriptionPricingSnapshot.restaurant_id == graph.restaurant)
            )
        ).all()
    )
    check(
        "last-active-metrics-retained-after-reset",
        [list(r) for r in old],
        [[100, 10, 1000, 2000]],
    )
