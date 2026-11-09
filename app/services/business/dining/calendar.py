# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# BRANCH OPENING CALENDAR CALCULATIONS
# Resolve multiple services, dated overrides and midnight across IANA timezones.
# ==============================================

"""Pure calendar availability; a predicted end never certifies physical vacancy."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND EXPLICIT CALENDAR SNAPSHOT
# Work from persisted caller-supplied days and fail on missing or ambiguous rules.
# ==============================================

from collections.abc import Mapping
from datetime import (
    date,
    datetime,
    time,
    timedelta,
    timezone,
)
from zoneinfo import ZoneInfo

from app.schemas.dining import OpeningWindow
from app.services.business.dining.values import (
    DiningError,
    Period,
)

# ==============================================
# VERIFIED LOCAL WALL-CLOCK BOUNDARY
# Refuse nonexistent times and require a fold choice when a DST hour repeats.
# ==============================================


def local_instant(
    *, day: date, clock: time, zone: ZoneInfo, fold: int | None
) -> datetime:
    """Convert a configured wall time to UTC without guessing DST policy."""
    naive = datetime.combine(day, clock)
    candidates: dict[int, datetime] = {}
    for option in (0, 1):
        local = naive.replace(tzinfo=zone, fold=option)
        instant = local.astimezone(timezone.utc)
        if instant.astimezone(zone).replace(tzinfo=None) == naive:
            candidates[option] = instant
    if not candidates:
        raise DiningError(code="dining_calendar_nonexistent_local_time")
    if len(set(candidates.values())) > 1 and fold is None:
        raise DiningError(code="dining_calendar_ambiguous_local_time_requires_fold")
    selected = 0 if fold is None else fold
    if selected not in candidates:
        raise DiningError(code="dining_calendar_fold_invalid")
    return candidates[selected]


# ==============================================
# DATE-SPECIFIC SERVICE RESOLUTION
# An explicit dated record replaces that civil day's weekly service completely.
# ==============================================


def day_windows(
    *,
    day: date,
    weekly: Mapping[int, tuple[OpeningWindow, ...]],
    dated: Mapping[date, tuple[OpeningWindow, ...]],
) -> tuple[OpeningWindow, ...]:
    """Distinguish an explicit closed day (empty tuple) from absent configuration."""
    if day in dated:
        return dated[day]
    if day.weekday() not in weekly:
        raise DiningError(code="dining_calendar_weekday_configuration_missing")
    return weekly[day.weekday()]


# ==============================================
# CONCRETE SERVICES INCLUDING OVERNIGHT ENDS
# Keep the owner's next-day choice explicit instead of inferring it from clocks.
# ==============================================


def services(
    *, day: date, windows: tuple[OpeningWindow, ...], zone: ZoneInfo
) -> tuple[Period, ...]:
    """Return actual UTC services; a repeated/nonexistent boundary fails explicitly."""
    return tuple(
        Period(
            start=local_instant(
                day=day, clock=window.start, zone=zone, fold=window.start_fold
            ),
            end=local_instant(
                day=day + timedelta(days=int(window.next_day)),
                clock=window.end,
                zone=zone,
                fold=window.end_fold,
            ),
        )
        for window in windows
    )


# ==============================================
# COMPLETE PERIOD COVERAGE
# Apply closed-date exceptions to overnight spillover and preserve service breaks.
# ==============================================


def opening_periods(
    *,
    period: Period,
    timezone_name: str,
    weekly: Mapping[int, tuple[OpeningWindow, ...]],
    dated: Mapping[date, tuple[OpeningWindow, ...]],
) -> tuple[Period, ...]:
    """Return clipped opening intervals, without guessing occupancy.

    A single request is bounded to 366 civil days as a technical query limit,
    not a commercial service-duration policy. Dated overrides replace the
    complete civil day, including a previous service's overnight spillover.
    """
    zone = ZoneInfo(timezone_name)
    first = period.start.astimezone(zone).date()
    last = period.end.astimezone(zone).date()
    if (last - first).days > 366:
        raise DiningError(code="dining_calendar_single_query_limit")
    allowed: list[Period] = []
    day = first
    while day <= last:
        lower = local_instant(day=day, clock=time.min, zone=zone, fold=None)
        upper = local_instant(
            day=day + timedelta(days=1), clock=time.min, zone=zone, fold=None
        )
        if upper <= period.start or lower >= period.end:
            day += timedelta(days=1)
            continue
        current = services(
            day=day, windows=day_windows(day=day, weekly=weekly, dated=dated), zone=zone
        )
        candidates = list(current)
        if day not in dated:
            previous = day - timedelta(days=1)
            previous_windows = day_windows(day=previous, weekly=weekly, dated=dated)
            candidates.extend(
                services(day=previous, windows=previous_windows, zone=zone)
            )
        for candidate in candidates:
            start = max(candidate.start, lower, period.start)
            end = min(candidate.end, upper, period.end)
            if start < end:
                allowed.append(Period(start=start, end=end))
        day += timedelta(days=1)
    merged: list[Period] = []
    for available in sorted(allowed, key=lambda value: value.start):
        if merged and available.start <= merged[-1].end:
            merged[-1] = Period(
                start=merged[-1].start, end=max(merged[-1].end, available.end)
            )
        else:
            merged.append(available)
    return tuple(merged)


# ==============================================
# COMPLETE OPENING COVERAGE
# A break between services prevents a request from spanning the closed interval.
# ==============================================


def calendar_covers(
    *,
    period: Period,
    timezone_name: str,
    weekly: Mapping[int, tuple[OpeningWindow, ...]],
    dated: Mapping[date, tuple[OpeningWindow, ...]],
) -> bool:
    """Require one merged open interval to contain the complete requested period."""
    return any(
        window.contains(other=period)
        for window in opening_periods(
            period=period, timezone_name=timezone_name, weekly=weekly, dated=dated
        )
    )
