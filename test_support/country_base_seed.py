# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# RETAINED O2 QUOTATION REHEARSAL FIXTURE
# Create explicit synthetic history before testing the forward country-base migration.
# ==============================================

"""Disposable test data only; never invoked by the operational review or migration."""

from datetime import (
    datetime,
    timedelta,
    timezone,
)
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Subscription
from app.models.subscription_pricing import SubscriptionPricingSnapshot
from test_support.subscription_fixtures import (
    put,
    seed_graph,
)

# ==============================================
# FROZEN PRE-MIGRATION COMMERCIAL EVIDENCE
# Keep synthetic plan prices in this marked test database; no fixture is exported as commercial configuration.
# ==============================================


async def seed_retained_quote(*, session: AsyncSession) -> dict[str, int]:
    """Stage a synthetic active period and pricing snapshot; the rehearsal caller owns commit."""
    await session.execute(text("UPDATE branch_pricing SET active=false"))
    graph = await seed_graph(session)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    subscription = await put(
        session,
        Subscription,
        owner_id=graph.owner,
        restaurant_id=graph.restaurant,
        plan_id=graph.plans["basic"],
        billing_cycle="monthly",
        status="active",
        amount=Decimal(3000),
        currency="DZD",
        starts_at=now - timedelta(days=1),
        expires_at=now + timedelta(days=29),
    )
    snapshot = await put(
        session,
        SubscriptionPricingSnapshot,
        owner_id=graph.owner,
        restaurant_id=graph.restaurant,
        subscription_id=subscription,
        source_subscription_id=subscription,
        reference_start=now - timedelta(days=30),
        reference_end=now,
        context="renewal",
        products_count=0,
        categories_count=0,
        monthly_orders=0,
        average_order_value=Decimal(0),
        calculated_at=now,
        pricing={"final_amount_due": "3000.00"},
        parameters={
            "B": "3000.00",
            "base_revision": "legacy:subscription_pricing_config:1",
        },
    )
    await session.flush()
    return {
        "subscription": subscription,
        "snapshot": snapshot,
        "plan": graph.plans["basic"],
    }
