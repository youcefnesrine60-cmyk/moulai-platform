# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# PROGRESSIVE BRANCH PRICING
# Select one applicable currency and context grid, reject ambiguity and price marginal
# ranks.
# ==============================================

"""Select a context/currency/date grid, reject ambiguity, then price marginal ranks."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Declare the standard-library, framework and project dependencies used below.
# ==============================================

from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal

from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feature_pricing import BranchPricing
from app.repositories.subscription_queries import base_select
from app.services.business.subscription_types import BranchGrid

# ==============================================
# BRANCH BREAKDOWN
# Select one applicable grid and retain progressive tranche charges as evidence.
# ==============================================


async def branch_breakdown(
    *,
    session: AsyncSession,
    branches_count: int,
    plan_id: int | None = None,
    currency: str = "DZD",
    market: str | None = None,
    now: datetime | None = None,
) -> tuple[Decimal, BranchGrid]:
    """Select one applicable grid and retain progressive tranche charges as evidence."""

    from app.services.business.pricing_service import number

    number(value=branches_count, integer=True)
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    rows = (
        (
            await session.execute(
                base_select(BranchPricing).where(
                    BranchPricing.active.is_(True),
                    BranchPricing.currency == currency,
                    or_(
                        BranchPricing.plan_id.is_(None),
                        BranchPricing.plan_id == plan_id,
                    ),
                    or_(BranchPricing.market.is_(None), BranchPricing.market == market),
                    or_(
                        BranchPricing.starts_at.is_(None),
                        BranchPricing.starts_at <= now,
                    ),
                    or_(
                        BranchPricing.expires_at.is_(None),
                        BranchPricing.expires_at > now,
                    ),
                )
            )
        )
        .scalars()
        .all()
    )
    if not rows:
        raise ValueError("branch_grid_missing")
    groups: dict[
        tuple[str | None, int | None, str, datetime | None, datetime | None],
        list[BranchPricing],
    ] = {}
    for row in rows:
        key = (row.market, row.plan_id, row.grid_code, row.starts_at, row.expires_at)
        groups.setdefault(key, []).append(row)
    specificity = max((key[0] is not None, key[1] is not None) for key in groups)
    candidates = [
        grid
        for key, grid in groups.items()
        if (key[0] is not None, key[1] is not None) == specificity
    ]
    if len(candidates) != 1:
        raise ValueError("branch_grid_ambiguous")
    grid = sorted(candidates[0], key=lambda row: row.min_branches)
    next_rank: int | None = 2
    total = number(value=0)
    evidence: BranchGrid = []
    for i, row in enumerate(grid):
        if row.min_branches != next_rank or (
            row.max_branches is not None and row.max_branches < row.min_branches
        ):
            raise ValueError("branch_grid_overlap_or_gap")
        if row.max_branches is None and i != len(grid) - 1:
            raise ValueError("branch_grid_overlap_or_gap")
        price = number(value=row.price_per_branch)
        last = min(branches_count, row.max_branches or branches_count)
        quantity = max(0, last - row.min_branches + 1)
        total += quantity * price
        evidence.append(
            {
                "id": row.id,
                "grid": row.grid_code,
                "currency": currency,
                "market": row.market,
                "plan_id": row.plan_id,
                "from": row.min_branches,
                "to": row.max_branches,
                "unit_price": str(price),
                "quantity": quantity,
                "starts_at": row.starts_at.isoformat() if row.starts_at else None,
                "expires_at": row.expires_at.isoformat() if row.expires_at else None,
            }
        )
        next_rank = (row.max_branches + 1) if row.max_branches is not None else None
    if grid[-1].max_branches is not None and branches_count > grid[-1].max_branches:
        raise ValueError("branch_grid_incomplete")
    return total, evidence
