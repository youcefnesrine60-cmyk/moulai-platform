# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# PUBLIC READ LINKS AND CONTROLLED VISIT INPUTS
# A public identifier or presence signal never supplies staff or financial authority.
# ==============================================

"""Closed transport contracts; visit secrets belong in redacted headers, not QR URLs."""

from __future__ import annotations

# isort: split
# ==============================================
# BOUNDED RESOURCE CONTRACTS
# Reuse existing strict dining and exact financial schemas without accepting caller prices.
# ==============================================

from datetime import datetime
from typing import (
    Literal,
    TypeAlias,
)

from pydantic import (
    Field,
    model_validator,
)

from app.schemas.dining import DiningInput

PublicKind: TypeAlias = Literal["table", "reservation", "food_invoice", "receipt"]


# ==============================================
# EXPLICIT LINK MANAGEMENT
# Reprints retain the same issued identity; rotation and deactivation are separate writes.
# ==============================================


class PublicLinkInput(DiningInput):
    """Identify one owned resource; table physical status publication is explicit."""

    operation: Literal["issue", "rotate", "disable"]
    kind: PublicKind
    resource_id: int = Field(strict=True, gt=0)
    public_physical_state: bool = Field(strict=True, default=False)
    reason: str = Field(default="", max_length=100)

    # ==============================================
    # EXPLAIN REVOCATION
    # A compromised or disabled print keeps a retained human decision reason.
    # ==============================================

    @model_validator(mode="after")
    def require_reason(self) -> PublicLinkInput:
        """Require an explicit reason before making an existing public print invalid."""
        if self.operation != "issue" and not self.reason:
            raise ValueError("dining_public_link_reason_required")
        return self


# ==============================================
# CUSTOMER PRESENCE SIGNAL
# Quantities describe a request for observation, never proof of a table installation.
# ==============================================


class PresenceInput(DiningInput):
    """Request staff attention for one identified table, without a state transition."""

    party_size: int = Field(strict=True, gt=0, le=1000)


# ==============================================
# STAFF-CONFIRMED INSTALLATION
# Human availability validation remains in the existing D1 service before installation.
# ==============================================


class PresenceInstallationInput(DiningInput):
    """Install one signalled party only after actual staff observation."""

    presence_id: int = Field(strict=True, gt=0)
    expected_end: datetime
    request_id: int | None = Field(default=None, strict=True, gt=0)
    observed: bool = Field(strict=True)


# ==============================================
# CUSTOMER ORDER WITHOUT CALLER-SUPPLIED PRICES
# Match an explicitly reviewed exact menu version and a unique submission identifier.
# ==============================================


class VisitOrderLine(DiningInput):
    """Select a bounded integer quantity of one publicly available restaurant product."""

    product_id: int = Field(strict=True, gt=0)
    quantity: int = Field(strict=True, gt=0, le=100)


# ==============================================
# VISITORDERINPUT
# A visit can request food, but cannot approve preparation, payment or a discount.
# ==============================================


class VisitOrderInput(DiningInput):
    """A visit can request food, but cannot approve preparation, payment or a discount."""

    idempotency_key: str = Field(pattern=r"^[A-Za-z0-9_-]{16,80}$")
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    menu_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    lines: tuple[VisitOrderLine, ...] = Field(min_length=1, max_length=50)

    # ==============================================
    # UNIQUE CART LINES
    # Repeated product IDs cannot bypass quantity bounds or source reconciliation.
    # ==============================================

    @model_validator(mode="after")
    def unique_products(self) -> VisitOrderInput:
        """Require exactly one explicit quantity for each selected product."""
        if len({line.product_id for line in self.lines}) != len(self.lines):
            raise ValueError("dining_visit_duplicate_product")
        return self


# ==============================================
# HUMAN ORDER RESPONSIBILITY
# Kitchen and service use their own independently granted transition powers.
# ==============================================


class VisitOrderTransition(DiningInput):
    """Request one existing-order transition; the service rechecks state and scope."""

    order_id: int = Field(strict=True, gt=0)
    action: Literal["approve", "prepare", "ready", "served"]
    observed: bool = Field(strict=True)
