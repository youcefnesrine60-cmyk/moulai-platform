# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# OFFLINE DINING TIME AND MONEY REGRESSIONS
# Verify exact arithmetic, explicit policy input and timezone calendar boundaries.
# ==============================================

"""Pure tests: no configuration, database, model provider or transport is accessed."""

# isort: split
# ==============================================
# IMPORTS AND EXPLICIT LOCAL CONTRACTS
# Use concrete data types without activating a remote dependency.
# ==============================================

from datetime import (
    date,
    datetime,
    time,
    timedelta,
    timezone,
)
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from app.schemas.dining import (
    OpeningWindow,
    TariffInput,
)
from app.services.business.dining.calendar import (
    calendar_covers,
    local_instant,
)
from app.services.business.dining.values import (
    DiningError,
    Period,
    exact_product,
    exact_sum,
    final_amount,
)

# ==============================================
# PROPORTIONAL HOURS AND HALF-OPEN BOUNDARIES
# Neither billing nor scheduling rounds a ninety-minute request to two hours.
# ==============================================


@pytest.mark.parametrize(
    "seconds,hours", [(5400, "1.5"), (1800, "0.5"), (3600, "1"), (9000, "2.5")]
)
def test_exact_elapsed_hours(seconds: int, hours: str) -> None:
    """Use elapsed aware UTC seconds and exact Decimal hours."""
    start = datetime(2026, 11, 3, 20, tzinfo=timezone.utc)
    assert Period(
        start=start, end=start + timedelta(seconds=seconds)
    ).hours() == Decimal(hours)


# ==============================================
# TEST ADJACENT PERIODS DO NOT OVERLAP
# A booking may start exactly when the previous protected period ends.
# ==============================================


def test_adjacent_periods_do_not_overlap() -> None:
    """A booking may start exactly when the previous protected period ends."""
    start = datetime(2026, 11, 3, 20, tzinfo=timezone.utc)
    first = Period(start=start, end=start + timedelta(hours=1))
    assert not first.overlaps(
        other=Period(start=first.end, end=first.end + timedelta(hours=1))
    )
    assert first.overlaps(
        other=Period(
            start=first.end - timedelta(microseconds=1),
            end=first.end + timedelta(hours=1),
        )
    )


# ==============================================
# TEST EXPLICIT CURRENCY PRECISION
# The currency's stored precision determines final HALF_UP rounding.
# ==============================================


@pytest.mark.parametrize(
    "precision,expected", [(0, "1"), (2, "1.01"), (3, "1.005"), (8, "1.00500000")]
)
def test_explicit_currency_precision(precision: int, expected: str) -> None:
    """The currency's stored precision determines final HALF_UP rounding."""
    assert final_amount(value=Decimal("1.005"), precision=precision) == Decimal(
        expected
    )


# ==============================================
# TEST NO INTERMEDIATE ROUNDING OR DEFAULT CONTEXT TRUNCATION
# Unrounded half-cent products combine before final rounding.
# ==============================================


def test_no_intermediate_rounding_or_default_context_truncation() -> None:
    """Unrounded half-cent products combine before final rounding."""
    total = exact_sum(
        values=(
            exact_product(left=Decimal("0.005"), right=Decimal(1)),
            exact_product(left=Decimal("0.005"), right=Decimal(1)),
        )
    )
    assert final_amount(value=total, precision=2) == Decimal("0.01")
    assert exact_product(
        left=Decimal("1234567890123456.12345678"), right=Decimal("0.123456")
    ) == Decimal("152414813443081.39917748023168")


# ==============================================
# TEST FLOAT AND BOOLEAN CANNOT BE NEW FINANCIAL INPUTS
# Do not silently convert imprecise JSON floats into authoritative prices.
# ==============================================


@pytest.mark.parametrize("value", [1.5, True])
def test_float_and_boolean_cannot_be_new_financial_inputs(value: object) -> None:
    """Do not silently convert imprecise JSON floats into authoritative prices."""
    with pytest.raises(ValidationError, match="exact_decimal"):
        TariffInput(
            reference="synthetic",
            component="table",
            currency="DZD",
            unit="per_hour",
            unit_price=value,
            valid_from=datetime(2026, 11, 2, tzinfo=timezone.utc),
            valid_until=None,
        )


# ==============================================
# MULTIPLE SERVICES AND DATE OVERRIDES
# Explicit closures also cut off the previous day's overnight spillover.
# ==============================================


def test_midnight_and_dated_closure_cover_the_whole_interval() -> None:
    """A Tuesday closure overrides a Monday service continuing after midnight."""
    weekly = {day: () for day in range(7)}
    weekly[0] = (OpeningWindow(start="20:00", end="02:00", next_day=True),)
    period = Period(
        start=datetime(2026, 11, 2, 22, tzinfo=timezone.utc),
        end=datetime(2026, 11, 3, 1, tzinfo=timezone.utc),
    )
    assert calendar_covers(period=period, timezone_name="UTC", weekly=weekly, dated={})
    assert not calendar_covers(
        period=period, timezone_name="UTC", weekly=weekly, dated={date(2026, 11, 3): ()}
    )


# ==============================================
# TEST SERVICE BREAK IS NOT AVAILABLE TIME
# The gap between lunch and dinner cannot become one continuous reservation.
# ==============================================


def test_service_break_is_not_available_time() -> None:
    """The gap between lunch and dinner cannot become one continuous reservation."""
    weekly = {day: () for day in range(7)}
    weekly[1] = (
        OpeningWindow(start="12:00", end="14:00", next_day=False),
        OpeningWindow(start="18:00", end="23:00", next_day=False),
    )
    assert not calendar_covers(
        period=Period(
            start=datetime(2026, 11, 3, 13, tzinfo=timezone.utc),
            end=datetime(2026, 11, 3, 19, tzinfo=timezone.utc),
        ),
        timezone_name="UTC",
        weekly=weekly,
        dated={},
    )


# ==============================================
# TEST MISSING WEEKDAY IS A CONFIGURATION ERROR
# Missing days are not silently treated as open, closed or a zero-duration day.
# ==============================================


def test_missing_weekday_is_a_configuration_error() -> None:
    """Missing days are not silently treated as open, closed or a zero-duration day."""
    with pytest.raises(DiningError, match="configuration_missing"):
        calendar_covers(
            period=Period(
                start=datetime(2026, 11, 3, 13, tzinfo=timezone.utc),
                end=datetime(2026, 11, 3, 14, tzinfo=timezone.utc),
            ),
            timezone_name="UTC",
            weekly={},
            dated={},
        )


# ==============================================
# DST GAP AND REPEATED HOUR
# Require an explicit fold instead of inventing a restaurant scheduling convention.
# ==============================================


def test_nonexistent_dst_boundary_is_rejected() -> None:
    """Europe/Paris skips 02:30 during the spring transition."""
    with pytest.raises(DiningError, match="nonexistent"):
        local_instant(
            day=date(2026, 3, 29),
            clock=time(2, 30),
            zone=ZoneInfo("Europe/Paris"),
            fold=None,
        )


# ==============================================
# TEST REPEATED DST BOUNDARY REQUIRES EXPLICIT FOLD
# The two 02:30 instants are distinct and cannot be chosen implicitly.
# ==============================================


def test_repeated_dst_boundary_requires_explicit_fold() -> None:
    """The two 02:30 instants are distinct and cannot be chosen implicitly."""
    zone = ZoneInfo("Europe/Paris")
    with pytest.raises(DiningError, match="ambiguous"):
        local_instant(day=date(2026, 10, 25), clock=time(2, 30), zone=zone, fold=None)
    first = local_instant(day=date(2026, 10, 25), clock=time(2, 30), zone=zone, fold=0)
    second = local_instant(day=date(2026, 10, 25), clock=time(2, 30), zone=zone, fold=1)
    assert second - first == timedelta(hours=1)
