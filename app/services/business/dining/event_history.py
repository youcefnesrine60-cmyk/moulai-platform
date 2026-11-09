# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# READ-ONLY DINING HISTORY
# Page the existing append-only journal under its existing scope and capabilities.
# ==============================================

"""History projections never reconstruct missing facts, change grants or append events."""

from __future__ import annotations

# isort: split
# ==============================================
# SCOPED QUERIES AND BOUNDED PUBLIC CONTRACTS
# Keep profile names and financial values behind their existing read eligibility.
# ==============================================

import re
from datetime import (
    date,
    time,
    timedelta,
)
from zoneinfo import ZoneInfo

from sqlalchemy import (
    case,
    func,
    literal,
    select,
)

from app.core.security.tenant_types import TenantAccessDenied
from app.models.dining import (
    DiningEvent,
    DiningGrant,
)
from app.models.dining_service import DiningStaffProfile
from app.schemas.dining import JsonObject
from app.services.business.dining.calendar import local_instant
from app.services.business.dining.core import DiningCore
from app.services.business.dining.values import (
    DiningError,
    utc,
)

HISTORY_CAPABILITIES = frozenset(
    {
        "service",
        "assistant",
        "collect",
        "finance.read",
        "configure",
        "reservations.cancel_before_arrival",
    }
)
AUTHOR_PATTERN = re.compile(r"(?:member:[1-9][0-9]{0,17}|kind:[a-z][a-z_-]{0,39})\Z")
DETAIL_KEYS = frozenset(
    {
        "reason",
        "origin",
        "kind",
        "state",
        "initial_state",
        "active",
        "actor_kind",
        "capability",
        "policy_id",
        "membership_id",
        "reference_id",
        "calendar_id",
        "table_id",
        "table_ids",
        "combination_id",
        "blackout_id",
        "tariff_id",
        "occupation_id",
        "quote_id",
        "receipt_id",
        "invoice_id",
        "allocation_id",
        "confirmation_id",
        "human_confirmation_id",
        "visit_id",
        "presence_id",
        "order_id",
        "link_id",
        "outbox_id",
        "identifier",
        "version",
        "generation",
        "arrived_at",
        "expected_end",
        "previous_expected_end",
        "actual_departure",
        "cleaning_expected_end",
        "previous_cleaning_expected_end",
        "expires_at",
        "late",
        "mode",
        "before",
        "after",
        "old",
        "new",
        "from",
        "to",
    }
)

# ==============================================
# SAFE RECORDED VALUES
# Only allow known audit facts; nested credentials or contacts never become technical UI data.
# ==============================================


def history_details(*, raw: JsonObject, finance: bool, level: int = 0) -> JsonObject:
    """Return recorded facts only; finance eligibility does not expose arbitrary JSON."""
    allowed = DETAIL_KEYS | ({"currency", "amount", "balance"} if finance else set())
    result: JsonObject = {}
    if level >= 3:
        return result
    for key, value in raw.items():
        if key not in allowed:
            continue
        if value is None or isinstance(value, (bool, int, float)):
            result[key] = value
        elif isinstance(value, str):
            result[key] = value[:1000]
        elif isinstance(value, dict):
            result[key] = history_details(raw=value, finance=finance, level=level + 1)
        elif isinstance(value, list):
            result[key] = [
                item
                for item in value[:30]
                if item is None or isinstance(item, (str, bool, int, float))
            ]
    return result


# ==============================================
# STABLE AUTHOR REFERENCE
# A missing member is not silently treated as a customer.
# ==============================================


def history_author_key(*, author: JsonObject) -> str:
    """Use a recorded membership or category; keep unknown authors explicitly unknown."""
    member = author.get("membership_id")
    if type(member) is int and member > 0:
        return f"member:{member}"
    kind = author.get("kind")
    key = f"kind:{kind}" if isinstance(kind, str) else "kind:unknown"
    return key if AUTHOR_PATTERN.fullmatch(key) else "kind:unknown"


# ==============================================
# SNAPSHOT-PINNED JOURNAL PAGE
# Authorize every read; a maximum event ID prevents new inserts shifting existing pages.
# ==============================================


async def read_event_history(
    *,
    unit: DiningCore,
    from_day: date | None = None,
    until_day: date | None = None,
    kind: str | None = None,
    author: str | None = None,
    page: int = 1,
    page_size: int = 20,
    snapshot_id: int | None = None,
) -> JsonObject:
    """Read the existing history eligibility with civil-day filters in the actual branch zone.

    Unknown events stay readable. Missing policy blocks only civil-day interpretation.
    Professional names, when available, are current labels, not historical assertions.
    """
    await unit.guard(capability="read")
    grants = tuple(
        (
            await unit.session.execute(
                unit.repo.statement(model=DiningGrant).where(
                    DiningGrant.membership_id == unit.context.membership_id,
                    DiningGrant.active.is_(True),
                )
            )
        ).scalars()
    )
    capabilities = {grant.capability for grant in grants}
    if unit.context.role_code == "owner":
        capabilities.add("configure")
    if not capabilities & HISTORY_CAPABILITIES:
        raise TenantAccessDenied("dining_history_access_required")
    if (
        not 1 <= page <= 100000
        or not 1 <= page_size <= 50
        or (snapshot_id is not None and snapshot_id < 0)
    ):
        raise DiningError(code="dining_history_filter_invalid")
    if kind is not None and not re.fullmatch(r"[a-z][a-z0-9_.-]{0,79}", kind):
        raise DiningError(code="dining_history_filter_invalid")
    if author is not None and not AUTHOR_PATTERN.fullmatch(author):
        raise DiningError(code="dining_history_filter_invalid")
    base = unit.repo.statement(model=DiningEvent)
    # Scope the aggregate through the same BASE SELECT, without a second unqualified table.
    scoped = base.subquery()
    maximum = int(await unit.session.scalar(select(func.max(scoped.c.id))) or 0)
    ceiling = min(snapshot_id, maximum) if snapshot_id is not None else maximum
    statement = base.where(DiningEvent.id <= ceiling)
    member = DiningEvent.author["membership_id"].as_string()
    recorded_kind = DiningEvent.author["kind"].as_string()
    author_key = case(
        (member.is_not(None), literal("member:") + member),
        else_=literal("kind:") + func.coalesce(recorded_kind, "unknown"),
    )
    kinds = tuple(
        (
            await unit.session.execute(
                statement.with_only_columns(DiningEvent.kind)
                .distinct()
                .order_by(DiningEvent.kind)
            )
        ).scalars()
    )
    authors = tuple(
        (
            await unit.session.execute(
                statement.with_only_columns(author_key.label("key"))
                .distinct()
                .order_by("key")
                .limit(501)
            )
        ).scalars()
    )
    if from_day is not None or until_day is not None:
        if until_day == date.max or (
            from_day is not None and until_day is not None and from_day > until_day
        ):
            raise DiningError(code="dining_history_filter_invalid")
        policy = await unit.policy(lock=False)
        zone = ZoneInfo(policy.timezone)
        if from_day:
            statement = statement.where(
                DiningEvent.occurred_at
                >= utc(
                    value=local_instant(
                        day=from_day, clock=time.min, zone=zone, fold=None
                    )
                )
            )
        if until_day:
            statement = statement.where(
                DiningEvent.occurred_at
                < utc(
                    value=local_instant(
                        day=until_day + timedelta(days=1),
                        clock=time.min,
                        zone=zone,
                        fold=None,
                    )
                )
            )
    if kind:
        statement = statement.where(DiningEvent.kind == kind)
    if author:
        statement = statement.where(author_key == author)
    total = int(
        await unit.session.scalar(
            select(func.count()).select_from(statement.subquery())
        )
        or 0
    )
    rows = tuple(
        (
            await unit.session.execute(
                statement.order_by(DiningEvent.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).scalars()
    )
    names: dict[str, str] = {}
    if "configure" in capabilities:
        members = {
            int(key[7:])
            for key in authors
            if AUTHOR_PATTERN.fullmatch(key) and key.startswith("member:")
        }
        if members:
            profiles = tuple(
                (
                    await unit.session.execute(
                        unit.repo.statement(model=DiningStaffProfile).where(
                            DiningStaffProfile.membership_id.in_(members)
                        )
                    )
                ).scalars()
            )
            names = {
                f"member:{profile.membership_id}": profile.display_name
                for profile in profiles
            }
    items: list[JsonObject] = []
    for row in rows:
        key = history_author_key(author=row.author)
        items.append(
            {
                "id": row.id,
                "kind": row.kind,
                "occurred_at": row.occurred_at.isoformat(),
                "request_id": row.request_id,
                "author_key": key,
                "author_name": names.get(key),
                "author_name_source": "current_profile" if key in names else None,
                "details": history_details(
                    raw=row.details, finance="finance.read" in capabilities
                ),
            }
        )
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "snapshot_id": ceiling,
        "kinds": list(kinds),
        "authors": [
            {"key": key, "name": names.get(key)}
            for key in authors[:500]
            if AUTHOR_PATTERN.fullmatch(key)
        ],
        "authors_truncated": len(authors) > 500,
    }
