# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# SYNTHETIC SUBSCRIPTION FIXTURES
# Build explicit synthetic owners, restaurants, tariffs and service history for isolated
# tests.
# ==============================================

"""MoulAI subscription fixtures definitions and explicit contracts."""

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
from types import SimpleNamespace

from sqlalchemy import (
    insert,
    select,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload

from app.models.base import BaseModel
from app.models.feature_pricing import (
    BranchPricing,
    FeaturePricing,
)
from app.models.loyalty_discount import (
    LoyaltyDiscount,
    MultiRestaurantDiscount,
)
from app.models.owner import Owner
from app.models.restaurant import Restaurant
from app.models.subscription import (
    Feature,
    PlanFeature,
    Subscription,
    SubscriptionPlan,
)

from app.models.subscription_pricing_legacy import LegacySubscriptionPricingConfig as SubscriptionPricingConfig  # isort: skip  # fmt: skip
from app.services.business import subscription_metrics

# ==============================================
# PUT
# Insert one synthetic fixture row and return its database-generated identifier.
# ==============================================


async def put(s: AsyncSession, model: type[BaseModel], **data: object) -> int:
    """Insert one synthetic fixture row and return its database-generated identifier."""

    return (
        await s.execute(insert(model.__table__).values(**data).returning(model.id))
    ).scalar_one()


# ==============================================
# SEED GRAPH
# Build explicit synthetic owners, plans, features and tariffs in the supplied test
# session.
# ==============================================


async def seed_graph(db_session: AsyncSession) -> SimpleNamespace:
    """Build explicit synthetic owners, plans, features and tariffs in the supplied test session."""

    s = db_session
    await s.execute(
        update(SubscriptionPricingConfig)
        .where(SubscriptionPricingConfig.id == 1)
        .values(
            base_price=3000,
            policies={
                "currencies": {"DZD": {"decimals": 2}},
                "reminder_days": [14, 7, 1, 0],
                "payment_adjustment_rates": {"electronic": "-0.02", "cash": "0.02"},
                "moulai_responsible_chat_id": "9901002",
            },
        )
    )
    plans = {}
    for code, discount in [
        ("basic", 0),
        ("professional", 5),
        ("enterprise", 10),
        ("trial", 0),
    ]:
        plans[code] = await put(
            s,
            SubscriptionPlan,
            code=code,
            name=code,
            base_price=3000,
            plan_discount_percent=discount,
        )
    costs = {
        "qr_menu": 0,
        "categories": 0,
        "products": 0,
        "hosting": 0,
        "dashboard": 0,
        "basic_support": 0,
        "orders": 1000,
        "reviews": 600,
        "best_customer": 400,
        "analytics": 500,
        "delivery": 500,
        "whatsapp": 300,
        "multi_branch": 200,
        "extra": 500,
        "extra_two": 250,
    }
    features = {}
    keys = list(costs)
    for key, price in costs.items():
        features[key] = await put(s, Feature, code=key, name=key)
        for cycle in ["monthly", "quarterly", "semiannual", "yearly"]:
            await put(
                s,
                FeaturePricing,
                feature_id=features[key],
                billing_cycle=cycle,
                price=price,
                active=True,
            )
    for code, included in [
        ("basic", keys[:6]),
        ("professional", keys[:9]),
        ("enterprise", keys[:13]),
        ("trial", keys[:6] + ["orders", "delivery"]),
    ]:
        for key in included:
            await put(
                s,
                PlanFeature,
                plan_id=plans[code],
                feature_id=features[key],
                included=True,
            )
    for years, rate in [(1, 2), (2, 5), (3, 8), (4, 11), (5, 15), (10, 20), (15, 25)]:
        await put(s, LoyaltyDiscount, years_required=years, discount_percent=rate)
    for count, rate in [(3, 5), (10, 15)]:
        await put(
            s, MultiRestaurantDiscount, min_restaurants=count, discount_percent=rate
        )
    for low, high, price in [(2, 5, 500), (6, 20, 400), (21, None, 300)]:
        await put(
            s,
            BranchPricing,
            min_branches=low,
            max_branches=high,
            price_per_branch=price,
            active=True,
        )
    owner = await put(
        s, Owner, chat_id=9900001, full_name="Synthetic pricing owner", trial_used=False
    )
    restaurants = []
    for i in range(2):
        restaurants.append(
            await put(
                s,
                Restaurant,
                owner_id=owner,
                name=f"Synthetic {i}",
                type="restaurant",
                phone=f"000000000{i}",
                wilaya="Synthetic",
            )
        )
    await s.commit()
    return SimpleNamespace(
        quote_time=datetime.now(timezone.utc).replace(tzinfo=None),
        s=s,
        plans=plans,
        f=features,
        owner=owner,
        restaurant=restaurants[0],
        second=restaurants[1],
    )


# ==============================================
# CLOSED TRIAL
# Synthetic boundary capture, never a production backfill.
# ==============================================


async def closed_trial(g: SimpleNamespace, *, end: datetime | None = None) -> int:
    """Synthetic boundary capture, never a production backfill."""
    end = end or datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=1)
    sid = await put(
        g.s,
        Subscription,
        owner_id=g.owner,
        restaurant_id=g.restaurant,
        plan_id=g.plans["trial"],
        billing_cycle="trial",
        status="expired",
        amount=0,
        starts_at=end - timedelta(days=30),
        expires_at=end,
    )
    source = (
        await g.s.execute(
            select(Subscription).options(raiseload("*")).where(Subscription.id == sid)
        )
    ).scalar_one()
    await subscription_metrics.capture_active_month(
        session=g.s,
        owner_id=g.owner,
        restaurant_id=g.restaurant,
        source=source,
        now=end,
    )
    await g.s.commit()
    return sid
