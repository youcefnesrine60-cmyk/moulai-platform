# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# OWNER OFFER CONSULTATION AND SIMULATION
# Use current authorized restaurant data and the existing pricing engine without granting administrative editing.
# ==============================================

"""Missing plans, history or commercial tariffs remain explicit blockers; no offer or payment is fabricated."""

from __future__ import annotations

import os

# isort: split
# ==============================================
# CLOSED READ CONTRACTS
# The owner selects a plan and cycle, never a base price, coefficient, owner identifier or internal metric.
# ==============================================

from datetime import (
    datetime,
    timezone,
)
from typing import (
    Annotated,
    Literal,
)

from pydantic import Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.restaurant import Restaurant
from app.models.subscription import SubscriptionPlan
from app.models.subscription_base_price import SubscriptionBasePrice
from app.repositories.subscription_configuration import country_storage_enabled
from app.repositories.subscription_queries import base_select
from app.schemas.dining import (
    DiningInput,
    JsonObject,
)
from app.services.business import subscription_metrics
from app.services.business.pricing_service import (
    calculate_subscription_pricing,
    configuration,
)

# ==============================================
# EXPLICIT PLAN SELECTION
# Client-supplied amounts and role fields are rejected by the inherited closed input model.
# ==============================================


class OfferInput(DiningInput):
    """Request a nonbinding server simulation for one already authorized restaurant."""

    plan_id: int = Field(strict=True, gt=0)
    billing_cycle: Literal["monthly", "quarterly", "semiannual", "yearly"]
    payment_method: Literal["electronic", "cash"]
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    market: str | None = Field(default=None, max_length=10)
    additional_feature_ids: list[Annotated[int, Field(strict=True, gt=0)]] = Field(
        default_factory=list, max_length=100
    )


# ==============================================
# CONFIGURATION READINESS
# Return only public plan names and the current reference parameter, never another tenant's calculation.
# ==============================================


async def available_offer(*, session: AsyncSession, restaurant_id: int) -> JsonObject:
    """Read within the caller's existing authorized billing transaction; do not manufacture a plan."""
    base = None
    currency: str | None = None
    country: str | None = None
    currencies: list[str] = []
    blockers: list[str] = []
    if await country_storage_enabled(session=session):
        from app.services.business.billing_country import validated_country_for_subscription  # isort: skip  # fmt: skip

        owner = await session.scalar(
            base_select(Restaurant)
            .with_only_columns(Restaurant.owner_id)
            .where(Restaurant.id == restaurant_id)
        )
        if owner is None:
            raise ValueError("restaurant_owner_unavailable")
        try:
            country, _decision, _starts = await validated_country_for_subscription(
                session=session,
                owner_id=owner,
                restaurant_id=restaurant_id,
                currency=None,
            )
            now = datetime.now(timezone.utc)
            versions = (
                await session.scalars(
                    base_select(SubscriptionBasePrice)
                    .where(
                        SubscriptionBasePrice.country_code == country,
                        SubscriptionBasePrice.effective_from <= now,
                        (SubscriptionBasePrice.effective_until.is_(None))
                        | (SubscriptionBasePrice.effective_until > now),
                    )
                    .order_by(SubscriptionBasePrice.currency)
                )
            ).all()
            currencies = [version.currency for version in versions]
            if len(versions) == 1:
                base, currency = versions[0].amount, versions[0].currency
            if not versions:
                blockers.append("country_base_missing")
        except ValueError:
            blockers.append("validated_billing_country_required")
    else:
        base, _policies = await configuration(session=session, currency="DZD")
        currency = "DZD"
        currencies = [currency]
    plans = (
        await session.scalars(
            base_select(SubscriptionPlan)
            .where(
                SubscriptionPlan.active.is_(True),
                SubscriptionPlan.code.in_(
                    ["basic", "professional", "enterprise", "pro"]
                ),
            )
            .order_by(SubscriptionPlan.id)
        )
    ).all()
    return {
        "base_reference": str(base) if base is not None else None,
        "currency": currency,
        "country_code": country,
        "currencies": currencies,
        "plans": [{"id": row.id, "name": row.name, "code": row.code} for row in plans],
        "blockers": blockers + ([] if plans else ["subscription_plans_missing"]),
        "binding_quote": False,
        # This describes the local route, never commercial/legal production readiness.
        "registration_connected": await session.scalar(
            text("SELECT version_num FROM public.alembic_version")
        )
        == "o420261108",
        "registration_scope": (
            "isolated_staging_fictitious_documents_only"
            if os.environ.get("APP_ENV") == "staging"
            else "local_fictitious_documents_only"
        ),
    }


# ==============================================
# NONBINDING SINGLE-ENGINE SIMULATION
# Undo any metric-capture staging performed by the existing calculator; no subscription, receipt or historical rewrite remains.
# ==============================================


async def simulate_offer(
    *, session: AsyncSession, restaurant_id: int, data: OfferInput
) -> JsonObject:
    """Use authoritative history and live parameters; missing history never becomes zero metrics."""
    owner = await session.scalar(
        base_select(Restaurant)
        .with_only_columns(Restaurant.owner_id)
        .where(Restaurant.id == restaurant_id)
    )
    if owner is None:
        raise ValueError("restaurant_owner_unavailable")
    savepoint = await session.begin_nested()
    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        country_code: str | None = None
        market = data.market
        if await country_storage_enabled(session=session):
            from app.services.business.billing_country import validated_country_for_subscription  # isort: skip  # fmt: skip

            country_code, _decision, _service_start = (
                await validated_country_for_subscription(
                    session=session,
                    owner_id=owner,
                    restaurant_id=restaurant_id,
                    currency=data.currency,
                )
            )
            if market is not None and market != country_code:
                raise ValueError("billing_country_market_mismatch")
            market = country_code
        _reference, inputs = await subscription_metrics.pricing_inputs(
            session=session, owner_id=owner, restaurant_id=restaurant_id, now=now
        )
        result = await calculate_subscription_pricing(
            session=session,
            plan_id=data.plan_id,
            billing_cycle=data.billing_cycle,
            payment_method=data.payment_method,
            currency=data.currency,
            country_code=country_code,
            market=market,
            additional_feature_ids=data.additional_feature_ids,
            owner_id=owner,
            restaurant_id=restaurant_id,
            now=now,
            **inputs,
        )
        evidence = subscription_metrics.json_evidence(value=result)
        return {"binding_quote": False, "pricing": evidence}
    finally:
        await savepoint.rollback()
