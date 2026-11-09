# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# SUBSCRIPTION PRICING SERVICE
# Calculate configured layered prices, discounts and final currency rounding with exact
# evidence.
# ==============================================

"""One layered calculator with legacy currency and prepared O3 country-version inputs."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Declare the standard-library, framework and project dependencies used below.
# ==============================================

from collections.abc import Iterable
from datetime import (
    datetime,
    timezone,
)
from decimal import (
    ROUND_HALF_UP,
    Decimal,
    InvalidOperation,
)
from typing import TypeAlias

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feature_pricing import FeaturePricing
from app.models.subscription import (
    Feature,
    SubscriptionPlan,
)
from app.repositories.loyalty_discount_repo import LoyaltyDiscountRepository
from app.repositories.subscription_configuration import (
    legacy_base,
    read_pricing_policy,
)

from app.repositories.multi_restaurant_discount_repo import MultiRestaurantDiscountRepository  # isort: skip  # fmt: skip
from app.repositories.promotion_repo import PromotionRepository
from app.repositories.subscription_queries import base_select
from app.services.business.subscription_contract import (
    ENTERPRISE,
    INCLUDED,
    PAYABLE_MONTHS,
    PROFESSIONAL,
    plan_code,
)
from app.services.business.subscription_types import (
    FeatureCosts,
    NumericInput,
    PricingAmounts,
    PricingParameters,
    PricingPolicies,
    PricingResult,
)

# ==============================================
# CONFIGURATION AND CONSTANTS
# Group the existing configuration values without changing their defaults.
# ==============================================

PAYMENT_CASH = "cash"
PAYMENT_ELECTRONIC = "electronic"
MONTHLY = "monthly"
YEARLY = "yearly"
FeatureIdsList: TypeAlias = list[int]


# ==============================================
# NUMBER
# Parse a finite, nonnegative Decimal; reject booleans and fractional counts.
# ==============================================


def number(*, value: object, integer: bool = False) -> Decimal:
    """Parse a finite, nonnegative Decimal; reject booleans and fractional counts."""

    try:
        if isinstance(value, bool):
            raise TypeError("invalid_pricing_input")
        result = Decimal(str(value))
        if (
            not result.is_finite()
            or result < 0
            or (integer and result != result.to_integral_value())
        ):
            raise ValueError("invalid_pricing_input")
        return result
    except (InvalidOperation, TypeError):
        raise ValueError("invalid_pricing_input") from None


# ==============================================
# MONEY
# Round only the final amount using the configured precision and HALF_UP.
# ==============================================


def money(*, value: Decimal, decimals: int = 2) -> Decimal:
    """Round only the final amount using the configured precision and HALF_UP."""

    if not isinstance(decimals, int) or not 0 <= decimals <= 8:
        raise ValueError("invalid_currency_precision")
    return number(value=value).quantize(
        Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP
    )


# ==============================================
# CALCULATE RESTAURANT SCORE
# Compute the approved score from validated 30-day metrics without rounding.
# ==============================================


def calculate_restaurant_score(
    *,
    products_count: int,
    categories_count: int,
    monthly_orders: int,
    average_order_value: NumericInput,
) -> Decimal:
    """Compute the approved score from validated 30-day metrics without rounding."""

    return (
        number(value=products_count, integer=True)
        + number(value=categories_count, integer=True) * 3
        + number(value=monthly_orders, integer=True) * Decimal("0.1")
        + number(value=average_order_value) / 100
    ) * 10


# ==============================================
# CONFIGURATION
# Load persisted currency policy and base; fail if configuration is missing.
# ==============================================


async def configuration(
    *,
    session: AsyncSession,
    currency: str = "DZD",
    country_code: str | None = None,
    at: datetime | None = None,
) -> tuple[Decimal, PricingPolicies]:
    """Load the explicit storage contract; O3 requires a country and never falls back.

    O2 callers retain their existing scalar contract until a separately controlled
    cutover. O3 removes that scalar column, so an unadapted caller fails closed.
    """

    if country_code is not None:
        from app.services.business.subscription_country_base import resolve_country_base

        selected = await resolve_country_base(
            session=session,
            country_code=country_code,
            currency=currency,
            at=at or datetime.now(timezone.utc),
        )
        return selected.amount, {
            **selected.policies,
            "base_revision": selected.revision,
            "base_selection": {
                "id": selected.identifier,
                "country_code": selected.country_code,
                "currency": selected.currency,
                "amount": str(selected.amount),
                "effective_from": selected.effective_from.isoformat(),
                "effective_until": (
                    selected.effective_until.isoformat()
                    if selected.effective_until is not None
                    else None
                ),
            },
        }

    policies = await read_pricing_policy(session=session)
    if currency not in policies.get("currencies", {}):
        raise ValueError("currency_configuration_missing")
    base = await legacy_base(session=session, currency=currency, policies=policies)
    return number(value=base), policies


# ==============================================
# PLAN FEATURES
# Resolve an active canonical plan and its required persisted feature IDs.
# ==============================================


async def plan_features(
    *, session: AsyncSession, plan_id: int
) -> tuple[str, dict[str, int], set[int]]:
    """Resolve an active canonical plan and its required persisted feature IDs."""

    code = (
        await session.execute(
            base_select(SubscriptionPlan)
            .with_only_columns(SubscriptionPlan.code)
            .where(SubscriptionPlan.id == plan_id, SubscriptionPlan.active.is_(True))
        )
    ).scalar_one_or_none()
    if code is None:
        raise ValueError("plan_not_found")
    code = plan_code(code=code)
    rows = (
        await session.execute(
            base_select(Feature).with_only_columns(Feature.id, Feature.code)
        )
    ).all()
    by_code = {row.code: row.id for row in rows}
    if not INCLUDED[code] <= by_code.keys():
        raise ValueError("mandatory_feature_configuration_missing")
    return code, by_code, {by_code[key] for key in INCLUDED[code]}


# ==============================================
# CALCULATE ADDITIONAL FEATURES PRICE
# Sum configured feature charges for the requested billing cycle.
# ==============================================


async def calculate_additional_features_price(
    *,
    session: AsyncSession,
    feature_ids: Iterable[int],
    billing_cycle: str,
    currency: str = "DZD",
) -> Decimal:
    """Sum configured feature charges for the requested billing cycle."""

    costs = await feature_costs(
        session=session, feature_ids=feature_ids, currency=currency
    )
    return sum((number(value=row["price"]) for row in costs.values()), Decimal(0))


# ==============================================
# FEATURE COSTS
# Resolve exact currency tariffs, rejecting missing or ambiguous feature prices.
# ==============================================


async def feature_costs(
    *, session: AsyncSession, feature_ids: Iterable[int], currency: str
) -> FeatureCosts:
    """Resolve exact currency tariffs, rejecting missing or ambiguous feature prices."""

    ids = set(feature_ids)
    for fid in ids:
        number(value=fid, integer=True)
    if not ids:
        return {}
    rows = (
        await session.execute(
            base_select(FeaturePricing)
            .with_only_columns(
                FeaturePricing.id, FeaturePricing.feature_id, FeaturePricing.price
            )
            .where(
                FeaturePricing.feature_id.in_(ids),
                FeaturePricing.currency == currency,
                FeaturePricing.billing_cycle == "monthly",
                FeaturePricing.active.is_(True),
            )
        )
    ).all()
    costs: FeatureCosts = {}
    for row in rows:
        if row.feature_id in costs:
            raise ValueError("feature_price_ambiguous")
        costs[row.feature_id] = {
            "price_id": row.id,
            "price": str(number(value=row.price)),
            "currency": currency,
        }
    if costs.keys() != ids:
        raise ValueError("feature_price_missing")
    return costs


# ==============================================
# BASE BREAKDOWN
# Build the layered base and retain the exact selected tariffs as evidence.
# ==============================================


async def base_breakdown(
    *,
    session: AsyncSession,
    plan_id: int,
    billing_cycle: str,
    additional_feature_ids: Iterable[int] | None = None,
    currency: str = "DZD",
    country_code: str | None = None,
    at: datetime | None = None,
) -> tuple[Decimal, PricingParameters]:
    """Build the layered base and retain the exact selected tariffs as evidence."""

    if billing_cycle not in PAYABLE_MONTHS:
        raise ValueError("invalid_billing_cycle")
    code, ids, included = await plan_features(session=session, plan_id=plan_id)
    if code == "trial":
        raise ValueError("trial_is_not_a_paid_plan")
    base, policies = (
        await configuration(session=session, currency=currency)
        if country_code is None
        else await configuration(
            session=session, currency=currency, country_code=country_code, at=at
        )
    )
    extras = set(additional_feature_ids or []) - included
    pro_ids = (
        {ids[key] for key in PROFESSIONAL}
        if code in {"professional", "enterprise"}
        else set()
    )
    enterprise_ids = {ids[key] for key in ENTERPRISE} if code == "enterprise" else set()
    costs = await feature_costs(
        session=session,
        feature_ids=extras | pro_ids | enterprise_ids,
        currency=currency,
    )

    # ==============================================
    # TOTAL
    # Sum distinct selected features using their resolved monthly prices.
    # ==============================================

    def total(*, feature_ids: Iterable[int]) -> Decimal:
        """Sum distinct selected features using their resolved monthly prices."""

        return sum(
            (number(value=costs[fid]["price"]) for fid in feature_ids), Decimal(0)
        )

    a, pro, enterprise = (
        total(feature_ids=extras),
        total(feature_ids=pro_ids),
        total(feature_ids=enterprise_ids),
    )
    value = (
        base
        + pro * Decimal("0.95")
        + enterprise * Decimal("0.90")
        + a
        * {
            "basic": Decimal(1),
            "professional": Decimal("0.95"),
            "enterprise": Decimal("0.90"),
        }[code]
    )
    return value, {
        **(
            {"base_selection": policies["base_selection"]}
            if "base_selection" in policies
            else {}
        ),
        "B": str(base),
        "base_revision": policies.get(
            "base_revision", "legacy:subscription_pricing_config:1"
        ),
        "P": str(pro),
        "E": str(enterprise),
        "A": str(a),
        "plan": code,
        "currency": currency,
        "decimals": policies["currencies"][currency]["decimals"],
        "included_feature_ids": sorted(included),
        "additional_feature_ids": sorted(extras),
        "currency_policy": policies["currencies"][currency],
        "payment_adjustment_rates": policies.get("payment_adjustment_rates", {}),
        "feature_costs": costs,
        "layer_rates": {"professional": "0.95", "enterprise": "0.90"},
    }


# ==============================================
# CALCULATE PLAN BASE PRICE
# Return the monthly layered base, using the shared tariff breakdown.
# ==============================================


async def calculate_plan_base_price(
    *,
    session: AsyncSession,
    plan_id: int,
    billing_cycle: str,
    additional_feature_ids: Iterable[int] | None = None,
    currency: str = "DZD",
    country_code: str | None = None,
    at: datetime | None = None,
) -> Decimal:
    """Return the monthly layered base, using the shared tariff breakdown."""
    return (
        await base_breakdown(
            session=session,
            plan_id=plan_id,
            billing_cycle=billing_cycle,
            additional_feature_ids=additional_feature_ids,
            currency=currency,
            country_code=country_code,
            at=at,
        )
    )[0]


# ==============================================
# CALCULATE LOYALTY DISCOUNT
# Apply the highest eligible persisted loyalty tier to the supplied value.
# ==============================================


async def calculate_loyalty_discount(
    *,
    session: AsyncSession,
    years_with_platform: NumericInput,
    amount: Decimal,
    owner_id: int | None = None,
) -> Decimal:
    """Apply the highest eligible persisted loyalty tier to the supplied value."""

    number(value=years_with_platform)
    rate = await LoyaltyDiscountRepository(session=session).get_discount_for_years(
        years=years_with_platform, owner_id=owner_id
    )
    return amount * number(value=rate) / 100


# ==============================================
# CALCULATE MULTI RESTAURANT DISCOUNT
# Apply the configured restaurant-count discount to the supplied value.
# ==============================================


async def calculate_multi_restaurant_discount(
    *, session: AsyncSession, restaurants_count: int, amount: Decimal
) -> Decimal:
    """Apply the configured restaurant-count discount to the supplied value."""

    number(value=restaurants_count, integer=True)
    rule = await MultiRestaurantDiscountRepository(session).get_discount_for_count(
        restaurants_count=restaurants_count
    )
    return (
        Decimal(0)
        if rule is None
        else amount * number(value=rule.discount_percent) / 100
    )


# ==============================================
# CALCULATE PROMOTION DISCOUNT
# Apply the best eligible campaign using rate, administrative priority and ID.
# ==============================================


async def calculate_promotion_discount(
    *,
    session: AsyncSession,
    amount: Decimal,
    restaurant_id: int | None = None,
    owner_id: int | None = None,
    plan_id: int | None = None,
    now: datetime | None = None,
) -> Decimal:
    """Apply the best eligible campaign using rate, administrative priority and ID."""

    rules = await PromotionRepository(session=session).get_active_promotions(
        restaurant_id=restaurant_id, owner_id=owner_id, plan_id=plan_id, now=now
    )
    return (
        Decimal(0)
        if not rules
        else amount * number(value=rules[0].discount_percent) / 100
    )


# ==============================================
# CALCULATE MULTI BRANCH COST
# Calculate progressive branch charges using the applicable persisted grid.
# ==============================================


async def calculate_multi_branch_cost(
    *,
    session: AsyncSession,
    branches_count: int,
    plan_id: int | None = None,
    currency: str = "DZD",
    market: str | None = None,
    now: datetime | None = None,
) -> Decimal:
    """Calculate progressive branch charges using the applicable persisted grid."""

    from app.services.business.subscription_branch_pricing import branch_breakdown

    return (
        await branch_breakdown(
            session=session,
            branches_count=branches_count,
            plan_id=plan_id,
            currency=currency,
            market=market,
            now=now,
        )
    )[0]


# ==============================================
# CALCULATE BILLING CYCLE PRICE
# Multiply by payable months; reject unsupported billing cycles.
# ==============================================


def calculate_billing_cycle_price(*, amount: Decimal, billing_cycle: str) -> Decimal:
    """Multiply by payable months; reject unsupported billing cycles."""

    if billing_cycle not in PAYABLE_MONTHS:
        raise ValueError("invalid_billing_cycle")
    return number(value=amount) * PAYABLE_MONTHS[billing_cycle]


# ==============================================
# CALCULATE PAYMENT ADJUSTMENT
# Apply the persisted payment rate once to the final pre-adjustment subtotal.
# ==============================================


def calculate_payment_adjustment(
    *, amount: Decimal, payment_method: str, rates: dict[str, str]
) -> Decimal:
    """Apply an explicit persisted rate without defaults or intermediate rounding.

    Missing, nonfinite or wrongly signed rates refuse quotation; B is untouched.
    """

    if payment_method not in {PAYMENT_CASH, PAYMENT_ELECTRONIC}:
        raise ValueError("invalid_payment_method")
    if set(rates) != {PAYMENT_CASH, PAYMENT_ELECTRONIC}:
        raise ValueError("payment_adjustment_configuration_missing")
    try:
        parsed = {key: Decimal(str(value)) for key, value in rates.items()}
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError("payment_adjustment_configuration_invalid") from error
    if any(not value.is_finite() or abs(value) > 1 for value in parsed.values()):
        raise ValueError("payment_adjustment_configuration_invalid")
    if parsed[PAYMENT_ELECTRONIC] > 0 or parsed[PAYMENT_CASH] < 0:
        raise ValueError("payment_adjustment_configuration_invalid")
    return number(value=amount) * parsed[payment_method]


# ==============================================
# CALCULATE SUBSCRIPTION PRICING
# Compute a currency-specific quote and retain its exact calculation evidence.
# ==============================================


async def calculate_subscription_pricing(
    *,
    session: AsyncSession,
    plan_id: int,
    billing_cycle: str,
    payment_method: str,
    restaurants_count: int,
    branches_count: int,
    years_with_platform: NumericInput,
    products_count: int,
    categories_count: int,
    monthly_orders: int,
    average_order_value: NumericInput,
    additional_feature_ids: Iterable[int] | None = None,
    owner_id: int | None = None,
    restaurant_id: int | None = None,
    currency: str = "DZD",
    country_code: str | None = None,
    market: str | None = None,
    now: datetime | None = None,
) -> PricingResult:
    """Compute a currency-specific quote and retain its exact calculation evidence."""

    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    base, parameters = await base_breakdown(
        session=session,
        plan_id=plan_id,
        billing_cycle=billing_cycle,
        additional_feature_ids=additional_feature_ids,
        currency=currency,
        country_code=country_code,
        # Existing measurement dates are UTC-naive; O3 resolution accepts aware instants only.
        at=now.replace(tzinfo=timezone.utc) if now.tzinfo is None else now,
    )
    score = calculate_restaurant_score(
        products_count=products_count,
        categories_count=categories_count,
        monthly_orders=monthly_orders,
        average_order_value=average_order_value,
    )
    val = base + score
    loyalty = await calculate_loyalty_discount(
        session=session,
        years_with_platform=years_with_platform,
        amount=val,
        owner_id=owner_id,
    )
    multi = await calculate_multi_restaurant_discount(
        session=session, restaurants_count=restaurants_count, amount=val
    )
    campaigns = await PromotionRepository(session=session).get_active_promotions(
        restaurant_id=restaurant_id,
        owner_id=owner_id,
        plan_id=plan_id,
        now=now,
        limit=1,
    )
    campaign = campaigns[0] if campaigns else None
    promo = (
        val * number(value=campaign.discount_percent) / 100 if campaign else Decimal(0)
    )
    discount = loyalty + multi + promo
    if discount > val:
        raise ValueError("discount_exceeds_value")
    from app.services.business.subscription_branch_pricing import branch_breakdown

    branches, grid = await branch_breakdown(
        session=session,
        branches_count=branches_count,
        plan_id=plan_id,
        currency=currency,
        market=market,
        now=now,
    )
    monthly = val - discount + branches
    final = calculate_billing_cycle_price(amount=monthly, billing_cycle=billing_cycle)
    adjustment = calculate_payment_adjustment(
        amount=final,
        payment_method=payment_method,
        rates=parameters.get("payment_adjustment_rates", {}),
    )
    result: PricingAmounts = {
        "base_price": base,
        "restaurant_score": score,
        "value_before_discounts": val,
        "loyalty_discount": loyalty,
        "multi_restaurant_discount": multi,
        "promotion_discount": promo,
        "discount_price": discount,
        "multi_branch_cost": branches,
        "monthly_price": monthly,
        "final_price": final,
        "payment_adjustment": adjustment,
        "final_amount_due": money(
            value=final + adjustment, decimals=parameters["decimals"]
        ),
    }
    parameters.update(
        {
            "billing_cycle": billing_cycle,
            "payment_method": payment_method,
            "payment_adjustment_rate": parameters["payment_adjustment_rates"][
                payment_method
            ],
            "payable_months": PAYABLE_MONTHS[billing_cycle],
            "restaurants_count": restaurants_count,
            "branches_count": branches_count,
            "years_with_platform": years_with_platform,
            "loyalty_rate": str(loyalty / val if val else 0),
            "multi_restaurant_rate": str(multi / val if val else 0),
            "promotion_rate": str(promo / val if val else 0),
            "promotion_id": campaign.id if campaign else None,
            "promotion_priority": campaign.priority if campaign else None,
            "branch_grid": grid,
            "market": market,
            "calculation_time": now.isoformat(),
        }
    )
    # Preserve the existing public scalar shape; evidence carries exact decimals separately.
    return {
        **result,
        "parameters": parameters,
        "exact": {key: str(value) for key, value in result.items()},
    }
