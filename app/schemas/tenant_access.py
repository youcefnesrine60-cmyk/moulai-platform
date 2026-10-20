# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Immutable output records; none of these objects grants tenant authority."""

from dataclasses import dataclass
from typing import (
    Literal,
    TypeAlias,
)

from app.core.security.tenant_types import (
    RestaurantAccessMode,
    TenantRoleCode,
)

MembershipStatus: TypeAlias = Literal["pending", "active", "suspended", "revoked"]
RestaurantRecord: TypeAlias = tuple[int, str, str, str, bool | None]


@dataclass(frozen=True, slots=True, kw_only=True)
class MembershipSummary:
    """Expose only the authenticated identity's own membership metadata."""

    id: int
    organization_id: int
    role: TenantRoleCode
    access_mode: RestaurantAccessMode
    status: MembershipStatus
    revision: int


@dataclass(frozen=True, slots=True, kw_only=True)
class RestaurantSummary:
    """Detach a bounded authorized projection from the database transaction."""

    id: int
    name: str
    type: str
    wilaya: str
    is_active: bool | None
