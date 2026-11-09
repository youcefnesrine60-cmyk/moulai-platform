# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# SHARED SUBSCRIPTION TYPE CONTRACTS
# Describe pricing, metrics, service periods and injected transports without performing
# I/O.
# ==============================================

"""Shared subscription contracts; importing types performs no service operation."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Declare the standard-library, framework and project dependencies used below.
# ==============================================

from collections.abc import (
    Awaitable,
    Callable,
    Mapping,
)
from datetime import datetime
from decimal import Decimal
from typing import (
    Protocol,
    TypeAlias,
    TypedDict,
)

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

# ==============================================
# NUMERIC, JSON AND TRANSACTION CONTRACTS
# Share exact numeric, serialized evidence and session-factory types.
# ==============================================

NumericInput: TypeAlias = Decimal | int | float | str
JsonValue: TypeAlias = (
    str | int | float | bool | None | list["JsonValue"] | dict[str, "JsonValue"]
)
SessionFactory: TypeAlias = async_sessionmaker[AsyncSession]
ServicePeriod: TypeAlias = tuple[datetime, datetime]
WorkerResults: TypeAlias = list[tuple[int, str]]
BranchTariff: TypeAlias = dict[str, str | int | None]
BranchGrid: TypeAlias = list[BranchTariff]
FeatureCosts: TypeAlias = dict[int, "FeatureCost"]
HistoricalValues: TypeAlias = Mapping[str, NumericInput]


# ==============================================
# CURRENCY POLICY
# Persisted monetary precision of an explicitly configured currency.
# ==============================================


class CurrencyPolicy(TypedDict):
    """Persisted monetary precision of an explicitly configured currency."""

    # ==============================================
    # CONTRACT FIELDS
    # Describe the fields accepted or returned by this declared data contract.
    # ==============================================

    decimals: int


# ==============================================
# COUNTRY BASE SELECTION EVIDENCE
# Retain the exact country-specific source used by a calculation without another live price store.
# ==============================================


class BaseSelectionEvidence(TypedDict):
    """Retained O3 country/currency source selected for a calculation, not a second live tariff."""

    id: int
    country_code: str
    currency: str
    amount: str
    effective_from: str
    effective_until: str | None


# ==============================================
# SHARED POLICIES AND RESOLVED CALCULATION INPUTS
# base_selection is returned evidence only; O3 never persists it as another price store.
# ==============================================


class PricingPolicies(TypedDict, total=False):
    """Known configuration keys; commercial defaults are never inferred here."""

    # ==============================================
    # CONTRACT FIELDS
    # Describe the fields accepted or returned by this declared data contract.
    # ==============================================

    currencies: dict[str, CurrencyPolicy]
    base_storage: str
    policy_revision: str
    currency_bases: dict[str, NumericInput]
    base_revision: str
    base_selection: BaseSelectionEvidence
    payment_adjustment_rates: dict[str, str]
    reminder_days: list[int]
    moulai_responsible_chat_id: str | int


# ==============================================
# FEATURE COST
# Exact monthly tariff and persistent source retained for one feature.
# ==============================================


class FeatureCost(TypedDict):
    """Exact monthly tariff and persistent source retained for one feature."""

    # ==============================================
    # CONTRACT FIELDS
    # Describe the fields accepted or returned by this declared data contract.
    # ==============================================

    price_id: int
    price: str
    currency: str


# ==============================================
# PRICING PARAMETERS
# Inputs and selections frozen with a subscription quotation.
# ==============================================


class PricingParameters(TypedDict, total=False):
    """Inputs and selections frozen with a subscription quotation."""

    # ==============================================
    # CONTRACT FIELDS
    # Describe the fields accepted or returned by this declared data contract.
    # ==============================================

    B: str
    base_revision: str
    base_selection: BaseSelectionEvidence
    P: str
    E: str
    A: str
    plan: str
    currency: str
    decimals: int
    included_feature_ids: list[int]
    additional_feature_ids: list[int]
    currency_policy: CurrencyPolicy
    feature_costs: FeatureCosts
    layer_rates: dict[str, str]
    billing_cycle: str
    payment_method: str
    payment_adjustment_rates: dict[str, str]
    payment_adjustment_rate: str
    replacement: dict[str, JsonValue]
    payable_months: int
    restaurants_count: int
    branches_count: int
    years_with_platform: NumericInput
    loyalty_rate: str
    multi_restaurant_rate: str
    promotion_rate: str
    promotion_id: int | None
    promotion_priority: int | None
    branch_grid: BranchGrid
    market: str | None
    calculation_time: str
    billing_country_decision_id: int


# ==============================================
# PRICING AMOUNTS
# Decimal-only calculation chain, including the final rounded amount.
# ==============================================


class PricingAmounts(TypedDict):
    """Decimal-only calculation chain, including the final rounded amount."""

    # ==============================================
    # CONTRACT FIELDS
    # Describe the fields accepted or returned by this declared data contract.
    # ==============================================

    base_price: Decimal
    restaurant_score: Decimal
    value_before_discounts: Decimal
    loyalty_discount: Decimal
    multi_restaurant_discount: Decimal
    promotion_discount: Decimal
    discount_price: Decimal
    multi_branch_cost: Decimal
    monthly_price: Decimal
    final_price: Decimal
    payment_adjustment: Decimal
    final_amount_due: Decimal


# ==============================================
# PRICING RESULT
# Calculation and exact serialized evidence returned to the checkout.
# ==============================================


class PricingResult(PricingAmounts):
    """Calculation and exact serialized evidence returned to the checkout."""

    # ==============================================
    # CONTRACT FIELDS
    # Describe the fields accepted or returned by this declared data contract.
    # ==============================================

    parameters: PricingParameters
    exact: dict[str, str]


# ==============================================
# SUBSCRIPTION RESULT
# Persisted pending subscription and its complete server quotation.
# ==============================================


class SubscriptionResult(TypedDict):
    """Persisted pending subscription and its complete server quotation."""

    # ==============================================
    # CONTRACT FIELDS
    # Describe the fields accepted or returned by this declared data contract.
    # ==============================================

    subscription_id: int
    pricing: PricingResult


# ==============================================
# METRIC VALUES
# Four authoritative inputs from the same recorded measurement window.
# ==============================================


class MetricValues(TypedDict):
    """Four authoritative inputs from the same recorded measurement window."""

    # ==============================================
    # CONTRACT FIELDS
    # Describe the fields accepted or returned by this declared data contract.
    # ==============================================

    products_count: int
    categories_count: int
    monthly_orders: int
    average_order_value: Decimal


# ==============================================
# PERIOD METRICS
# Metrics with an inclusive start and exclusive end.
# ==============================================


class PeriodMetrics(MetricValues):
    """Metrics with an inclusive start and exclusive end."""

    # ==============================================
    # CONTRACT FIELDS
    # Describe the fields accepted or returned by this declared data contract.
    # ==============================================

    reference_start: datetime
    reference_end: datetime


# ==============================================
# REFERENCE METRICS
# An owned source period and the reason it is used for quotation.
# ==============================================


class ReferenceMetrics(PeriodMetrics):
    """An owned source period and the reason it is used for quotation."""

    # ==============================================
    # CONTRACT FIELDS
    # Describe the fields accepted or returned by this declared data contract.
    # ==============================================

    source_subscription_id: int
    context: str


# ==============================================
# PRICING INPUTS
# Metrics enriched with persisted restaurant and paid-service counters.
# ==============================================


class PricingInputs(MetricValues):
    """Metrics enriched with persisted restaurant and paid-service counters."""

    # ==============================================
    # CONTRACT FIELDS
    # Describe the fields accepted or returned by this declared data contract.
    # ==============================================

    restaurants_count: int
    branches_count: int
    years_with_platform: int


# ==============================================
# CASH COLLECTION RESULT
# Committed physical cash receipt or an exact idempotent repetition.
# ==============================================


class CashCollectionResult(TypedDict):
    """Committed physical cash receipt or an exact idempotent repetition."""

    # ==============================================
    # CONTRACT FIELDS
    # Describe the fields accepted or returned by this declared data contract.
    # ==============================================

    payment_id: int
    collection_id: int
    result: str


# ==============================================
# INJECTED TRANSPORT INTERFACES
# An authorized transport; no client or connection is created by this contract.
# ==============================================


class ReminderTransport(Protocol):
    """An authorized transport; no client or connection is created by this contract."""

    # ==============================================
    # CONTRACT FIELDS
    # Describe the fields accepted or returned by this declared data contract.
    # ==============================================

    send: Callable[..., Awaitable[None]]


# ==============================================
# TELEGRAM TRANSPORT
# Existing Telegram client/module injected by an authorized caller.
# ==============================================


class TelegramTransport(Protocol):
    """Existing Telegram client/module injected by an authorized caller."""

    # ==============================================
    # CONTRACT FIELDS
    # Describe the fields accepted or returned by this declared data contract.
    # ==============================================

    send_message: Callable[..., Awaitable[object]]
