# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# SHARED POLICY AND EXPLICIT SCHEMA CONTRACT
# Read policy independently of B and guard the historical compatibility path before touching a removed column.
# ==============================================

"""The actual database revision controls legacy admission; JSON alone never enables an old reader on O3."""

from decimal import Decimal

from pydantic import TypeAdapter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription_pricing import SubscriptionPricingConfig
from app.models.subscription_pricing_legacy import LegacySubscriptionPricingConfig
from app.repositories.subscription_queries import base_select
from app.services.business.subscription_types import PricingPolicies

LEGACY_REVISIONS = frozenset(
    {
        "s1a20261028",
        "s1b20261028",
        "d1a20261102",
        "d1b20261103",
        "d1c20261104",
        "d1d20261105",
        "o120261108",
        "o220261108",
    }
)
COUNTRY_REVISIONS = frozenset({"o320261108", "o420261108", "o520261111"})

# ==============================================
# GLOBAL POLICY READ
# A reminder editor must not select or reversion a country's price.
# ==============================================


async def read_pricing_policy(
    *, session: AsyncSession, lock: bool = False
) -> PricingPolicies:
    """Read the singleton's policies using BASE SELECT without the removed price column."""
    statement = (
        base_select(SubscriptionPricingConfig)
        .with_only_columns(SubscriptionPricingConfig.policies)
        .where(SubscriptionPricingConfig.id == 1)
    )
    if lock:
        statement = statement.with_for_update()
    policy = await session.scalar(statement)
    if policy is None:
        raise ValueError("subscription_pricing_configuration_missing")
    return TypeAdapter(PricingPolicies).validate_python(policy)


# ==============================================
# EXPLICIT CURRENT STORAGE ADMISSION
# An unrecognized database is never treated as an older singleton by default.
# ==============================================


async def country_storage_enabled(*, session: AsyncSession) -> bool:
    """Resolve the known schema revision, refusing unknown or inconsistent migration states."""
    revisions = (
        await session.scalars(text("SELECT version_num FROM public.alembic_version"))
    ).all()
    if len(revisions) != 1:
        raise ValueError("subscription_pricing_schema_not_supported")
    revision = revisions[0]
    if revision in COUNTRY_REVISIONS:
        return True
    if revision not in LEGACY_REVISIONS:
        raise ValueError("subscription_pricing_schema_not_supported")
    return False


# ==============================================
# GUARDED HISTORICAL SCALAR READ
# Keep old-profile regressions runnable without querying base_price after O3 has removed it.
# ==============================================


async def legacy_base(
    *, session: AsyncSession, currency: str, policies: PricingPolicies
) -> Decimal:
    """Allow only physically legacy schemas; the compatibility data is not copied elsewhere."""
    if await country_storage_enabled(session=session):
        raise ValueError("validated_billing_country_required")
    value = (
        (
            await session.scalar(
                base_select(LegacySubscriptionPricingConfig)
                .with_only_columns(LegacySubscriptionPricingConfig.base_price)
                .where(LegacySubscriptionPricingConfig.id == 1)
            )
        )
        if currency == "DZD"
        else policies.get("currency_bases", {}).get(currency)
    )
    if value is None:
        raise ValueError("currency_base_missing")
    result = Decimal(str(value))
    if not result.is_finite() or result < 0:
        raise ValueError("invalid_pricing_input")
    return result
