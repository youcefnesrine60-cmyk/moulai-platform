# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# COUNTRY-SPECIFIC BASE RESOLUTION AND PUBLICATION
# Select an exact dated price and preserve each explicitly authorized administrative decision.
# ==============================================

"""Prepared O3 backend; no implicit country, conversion, remote IO or route mounting.

Reads join the existing global currency policy. Publication owns its transaction,
reuses the existing exact permission and records the decision in the retained log.
"""

from __future__ import annotations

# isort: split
# ==============================================
# EXACT INPUTS AND EXISTING AUTHORITY
# Keep business entry points keyword-only and never accept a price from an owner simulation.
# ==============================================

import json
import re
from dataclasses import dataclass
from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal
from uuid import uuid4

from pydantic import TypeAdapter
from sqlalchemy import (
    or_,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.core.security.oidc import OIDCPrincipal
from app.models.admin_log import AdminLog
from app.models.subscription_base_price import SubscriptionBasePrice
from app.models.subscription_pricing import SubscriptionPricingConfig
from app.repositories.subscription_queries import base_select
from app.services.business.saas_pricing_admin import SaasPricingAdministration
from app.services.business.subscription_types import PricingPolicies

# ==============================================
# CLOSED CALCULATION EVIDENCE
# Preserve the selected amount and source rather than reconstructing a historical price later.
# ==============================================


@dataclass(frozen=True, kw_only=True)
class CountryBaseSelection:
    """Exact selected version and shared monetary policy for a single calculation."""

    identifier: int
    country_code: str
    currency: str
    amount: Decimal
    revision: str
    effective_from: datetime
    effective_until: datetime | None
    policies: PricingPolicies


# ==============================================
# EXPLICIT GEOGRAPHIC CONTEXT
# A country is never inferred from a currency, browser language or another market.
# ==============================================


def validate_context(*, country_code: str, currency: str, at: datetime) -> datetime:
    """Require uppercase codes and an aware UTC-convertible instant; reject ambiguity."""
    if (
        re.fullmatch(r"[A-Z]{2}", country_code) is None
        or re.fullmatch(r"[A-Z]{3}", currency) is None
        or at.tzinfo is None
        or at.utcoffset() is None
    ):
        raise ValueError("country_base_context_required")
    return at.astimezone(timezone.utc)


# ==============================================
# EXACT DATED BASE SELECT
# Both country and currency predicates and the half-open interval are mandatory.
# ==============================================


async def resolve_country_base(
    *, session: AsyncSession, country_code: str, currency: str, at: datetime
) -> CountryBaseSelection:
    """Return exactly one applicable version; never fall back to DZ, another currency or zero.

    The caller owns its transaction and tenant authorization. This public price
    configuration read provides no access to another owner's metrics or invoices.
    """
    instant = validate_context(country_code=country_code, currency=currency, at=at)
    rows = (
        await session.scalars(
            base_select(SubscriptionBasePrice).where(
                SubscriptionBasePrice.country_code == country_code,
                SubscriptionBasePrice.currency == currency,
                SubscriptionBasePrice.effective_from <= instant,
                or_(
                    SubscriptionBasePrice.effective_until.is_(None),
                    SubscriptionBasePrice.effective_until > instant,
                ),
            )
        )
    ).all()
    if len(rows) != 1:
        raise ValueError(
            "country_base_missing" if not rows else "country_base_ambiguous"
        )
    policy = await session.scalar(
        base_select(SubscriptionPricingConfig)
        .with_only_columns(SubscriptionPricingConfig.policies)
        .where(SubscriptionPricingConfig.id == 1)
    )
    if policy is None:
        raise ValueError("subscription_pricing_configuration_missing")
    if not isinstance(policy, dict):
        raise TypeError("subscription_pricing_policy_invalid")
    policies = TypeAdapter(PricingPolicies).validate_python(policy)
    decimals = policies.get("currencies", {}).get(currency, {}).get("decimals")
    if (
        isinstance(decimals, bool)
        or not isinstance(decimals, int)
        or not 0 <= decimals <= 8
    ):
        raise ValueError("currency_configuration_missing")
    row = rows[0]
    return CountryBaseSelection(
        identifier=row.id,
        country_code=row.country_code,
        currency=row.currency,
        amount=row.amount,
        revision=row.revision,
        effective_from=row.effective_from,
        effective_until=row.effective_until,
        policies=policies,
    )


# ==============================================
# AUTHORIZED IMMEDIATE VERSION REPLACEMENT
# Serialize all administrative publications on the existing singleton, then close and append atomically.
# ==============================================


async def publish_country_base(
    *,
    session: AsyncSession,
    principal: OIDCPrincipal,
    country_code: str,
    currency: str,
    amount: Decimal,
    expected_revision: str | None,
    source_reference: str,
) -> CountryBaseSelection:
    """Commit a version and its audit once, preserving the caller-independent public transaction."""
    async with session.begin():
        selected = await stage_country_base(
            session=session,
            principal=principal,
            country_code=country_code,
            currency=currency,
            amount=amount,
            expected_revision=expected_revision,
            source_reference=source_reference,
        )
    logger.info(
        "Country base version committed",
        extra={
            "country": country_code,
            "currency": currency,
            "revision": selected.revision,
        },
    )
    return selected


# ==============================================
# CALLER-OWNED AUTHORIZED PRICE PUBLICATION
# Share the write path with the administration facade without committing its transaction early.
# ==============================================


async def stage_country_base(
    *,
    session: AsyncSession,
    principal: OIDCPrincipal,
    country_code: str,
    currency: str,
    amount: Decimal,
    expected_revision: str | None,
    source_reference: str,
) -> CountryBaseSelection:
    """Stage the price and retained audit in an already active transaction; never commit independently."""
    if not session.in_transaction():
        raise RuntimeError("country_base_transaction_required")
    validate_context(
        country_code=country_code, currency=currency, at=datetime.now(timezone.utc)
    )
    if (
        not isinstance(amount, Decimal)
        or not amount.is_finite()
        or amount < 0
        or amount >= Decimal(10000000000000000)
        or amount != amount.quantize(Decimal("0.00000001"))
        or not source_reference.strip()
        or len(source_reference) > 2000
    ):
        raise ValueError("country_base_amount_or_source_invalid")
    author = await SaasPricingAdministration(session=session).authorize(
        principal=principal
    )
    policy = await session.scalar(
        base_select(SubscriptionPricingConfig)
        .with_only_columns(SubscriptionPricingConfig.policies)
        .where(SubscriptionPricingConfig.id == 1)
        .with_for_update()
    )
    if not isinstance(policy, dict) or currency not in policy.get("currencies", {}):
        raise ValueError("currency_configuration_missing")
    at = await session.scalar(text("SELECT clock_timestamp()"))
    if not isinstance(at, datetime):
        raise TypeError("country_base_clock_unavailable")
    versions = (
        await session.scalars(
            base_select(SubscriptionBasePrice)
            .where(
                SubscriptionBasePrice.country_code == country_code,
                SubscriptionBasePrice.currency == currency,
                or_(
                    SubscriptionBasePrice.effective_until.is_(None),
                    SubscriptionBasePrice.effective_until > at,
                ),
            )
            .with_for_update()
        )
    ).all()
    current = versions[0] if len(versions) == 1 else None
    if (
        len(versions) > 1
        or (current is not None and current.effective_from > at)
        or (current.revision if current else None) != expected_revision
        or (current is not None and current.amount == amount)
    ):
        raise ValueError("country_base_version_changed_or_unchanged")
    before = (
        None
        if current is None
        else {
            "id": current.id,
            "amount": str(current.amount),
            "revision": current.revision,
        }
    )
    if current is not None:
        current.effective_until = at
        await session.flush()
    row = SubscriptionBasePrice(
        country_code=country_code,
        currency=currency,
        amount=amount,
        revision=uuid4().hex,
        effective_from=at,
        author_admin_id=author,
        source_reference=source_reference.strip(),
    )
    session.add(row)
    await session.flush()
    selected = await resolve_country_base(
        session=session, country_code=country_code, currency=currency, at=at
    )
    session.add(
        AdminLog(
            admin_id=author,
            action="pricing.base.country.change",
            resource="saas_base_country",
            resource_id=row.id,
            timestamp=at.astimezone(timezone.utc).replace(tzinfo=None),
            details=json.dumps(
                {
                    "country_code": country_code,
                    "currency": currency,
                    "before": before,
                    "after": {
                        "id": row.id,
                        "amount": str(row.amount),
                        "revision": row.revision,
                    },
                    "source_reference": source_reference.strip(),
                    "effective_at": at.isoformat(),
                },
                sort_keys=True,
            ),
        )
    )
    return selected
