# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# EXACT DINING TIME AND MONEY VALUES
# Share deterministic calculations without configuration, network or database I/O.
# ==============================================

"""Half-open periods, exact durations and stable immutable proposal digests."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND TYPED VALUE CONTRACTS
# Keep instants aware and never introduce float arithmetic into financial values.
# ==============================================

import hashlib
import json
from dataclasses import dataclass
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from decimal import (
    ROUND_HALF_UP,
    Decimal,
    localcontext,
)

from pydantic import JsonValue

# ==============================================
# SCOPED BUSINESS REJECTION
# Return stable machine codes and already-authorized conflict identifiers only.
# ==============================================


class DiningError(ValueError):
    """Reject a known precondition without exposing foreign resources or secrets."""

    def __init__(self, *, code: str, conflicts: tuple[int, ...] = ()) -> None:
        """Retain a code and scoped conflicts; never include raw SQL or client text."""
        super().__init__(code)
        self.code = code
        self.conflicts = conflicts


# ==============================================
# NORMALIZE AN ACTUAL INSTANT
# Naive timestamps cannot silently inherit the workstation or restaurant timezone.
# ==============================================


def utc(*, value: datetime) -> datetime:
    """Return an aware UTC instant, rejecting an unspecified timezone."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise DiningError(code="dining_timezone_aware_instant_required")
    return value.astimezone(timezone.utc)


# ==============================================
# DEFAULT TRUSTED PROCESS CLOCK
# HTTP input never supplies the server time used for deadlines or validity.
# ==============================================


def utc_now() -> datetime:
    """Read the system's aware UTC clock without using a model or external service."""
    return datetime.now(timezone.utc)


# ==============================================
# HALF-OPEN INTERVAL VALUE
# Adjacent bookings are compatible; an empty interval cannot reserve a resource.
# ==============================================


@dataclass(frozen=True, slots=True, kw_only=True)
class Period:
    """Represent [start,end) in UTC, independent of any physical table state."""

    start: datetime
    end: datetime

    # ==============================================
    # POST INIT
    # Canonicalize instants and reject empty or reversed elapsed time.
    # ==============================================

    def __post_init__(self) -> None:
        """Canonicalize instants and reject empty or reversed elapsed time."""
        object.__setattr__(self, "start", utc(value=self.start))
        object.__setattr__(self, "end", utc(value=self.end))
        if self.end <= self.start:
            raise DiningError(code="dining_period_invalid")

    # ==============================================
    # OVERLAPS
    # Test half-open overlap, preserving compatibility at an exact boundary.
    # ==============================================

    def overlaps(self, *, other: Period) -> bool:
        """Test half-open overlap, preserving compatibility at an exact boundary."""
        return self.start < other.end and other.start < self.end

    # ==============================================
    # CONTAINS
    # Require full coverage, including both service margins when supplied.
    # ==============================================

    def contains(self, *, other: Period) -> bool:
        """Require full coverage, including both service margins when supplied."""
        return self.start <= other.start and self.end >= other.end

    # ==============================================
    # HOURS
    # Return exact elapsed hours; ninety minutes is Decimal('1.5').
    # ==============================================

    def hours(self) -> Decimal:
        """Return exact elapsed hours; ninety minutes is Decimal('1.5')."""
        delta = self.end - self.start
        micros = (delta.days * 86400 + delta.seconds) * 1_000_000 + delta.microseconds
        with localcontext() as context:
            context.prec = 64
            return Decimal(micros) / Decimal(3_600_000_000)


# ==============================================
# FINAL MONETARY ROUNDING
# Preserve intermediate rates and quantities; round only the total payable.
# ==============================================


def final_amount(*, value: Decimal, precision: int) -> Decimal:
    """Use the explicitly configured currency precision and ROUND_HALF_UP."""
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise DiningError(code="dining_amount_invalid")
    if type(precision) is not int or not 0 <= precision <= 8:
        raise DiningError(code="dining_currency_precision_invalid")
    with localcontext() as context:
        context.prec = 64
        result = value.quantize(Decimal(1).scaleb(-precision), rounding=ROUND_HALF_UP)
    if result > Decimal("9999999999999999.99999999"):
        raise DiningError(code="dining_amount_storage_limit")
    return result


# ==============================================
# WIDE DECIMAL INTERMEDIATE ARITHMETIC
# Preserve more digits than the complete Numeric(24,8) storage contract requires.
# ==============================================


def exact_product(*, left: Decimal, right: Decimal) -> Decimal:
    """Multiply exact decimal inputs without the default 28-digit intermediate cap."""
    with localcontext() as context:
        context.prec = 64
        return left * right


# ==============================================
# EXACT SUM
# Accumulate unrounded decimal products before final currency quantization.
# ==============================================


def exact_sum(*, values: tuple[Decimal, ...]) -> Decimal:
    """Accumulate unrounded decimal products before final currency quantization."""
    with localcontext() as context:
        context.prec = 64
        return sum(values, Decimal(0))


# ==============================================
# VERSION CONTENT FINGERPRINT
# Consent binds exact serialized content and decimal strings, not mutable prices.
# ==============================================


def content_digest(*, value: JsonValue) -> str:
    """Hash canonical JSON without serializing money through a float converter."""
    raw = json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ==============================================
# ELAPSED CUSTOMER DURATION
# Add elapsed seconds in UTC instead of adding wall time across a DST transition.
# ==============================================


def elapsed_period(*, start: datetime, seconds: int) -> Period:
    """Resolve one bounded actual duration; reject overflow instead of guessing an end."""
    if type(seconds) is not int or not 0 < seconds <= 366 * 86400:
        raise DiningError(code="dining_calendar_single_query_limit")
    beginning = utc(value=start)
    try:
        end = beginning + timedelta(seconds=seconds)
    except OverflowError as error:
        raise DiningError(code="dining_request_end_out_of_range") from error
    return Period(start=beginning, end=end)
