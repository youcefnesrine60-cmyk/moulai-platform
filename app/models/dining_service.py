# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# TYPED PROFESSIONAL AND PUBLIC SERVICE RECORDS
# Map the additive D1d contract on the existing scoped dining registry.
# ==============================================

"""No second identity store, password column, implicit grant or startup DDL."""

from __future__ import annotations

# isort: split
# ==============================================
# RECORD TYPES AND EXISTING REGISTRY
# Keep exact numeric and JSON values concrete across the database boundary.
# ==============================================

from datetime import datetime
from decimal import Decimal

from pydantic import JsonValue
from sqlalchemy.orm import Mapped

from app.models.dining import (
    D1_METADATA,
    DiningBase,
)

# ==============================================
# STAFF PROFILE AND DESCRIPTIVE FUNCTION
# Identity and professional activation remain in the existing E1 membership.
# ==============================================


class DiningStaffProfile(DiningBase):
    """Display a professional relation and its independently accepted invitation."""

    __table__ = D1_METADATA.tables["dining_staff_profiles"]
    id: Mapped[int]
    restaurant_id: Mapped[int]
    branch_id: Mapped[int]
    created_at: Mapped[datetime]
    membership_id: Mapped[int]
    employee_code: Mapped[str]
    display_name: Mapped[str]
    enrollment_generation: Mapped[int]
    accepted_at: Mapped[datetime | None]


# ==============================================
# DININGSTAFFFUNCTION
# Describe tasks only; no capability is derived from a function name.
# ==============================================


class DiningStaffFunction(DiningBase):
    """Describe tasks only; no capability is derived from a function name."""

    __table__ = D1_METADATA.tables["dining_staff_functions"]
    id: Mapped[int]
    restaurant_id: Mapped[int]
    branch_id: Mapped[int]
    created_at: Mapped[datetime]
    code: Mapped[str]
    labels: Mapped[dict[str, str]]
    tasks: Mapped[list[str]]
    active: Mapped[bool]


# ==============================================
# DININGSTAFFASSIGNMENT
# Allow multiple descriptive functions in a single exact branch scope.
# ==============================================


class DiningStaffAssignment(DiningBase):
    """Allow multiple descriptive functions in a single exact branch scope."""

    __table__ = D1_METADATA.tables["dining_staff_assignments"]
    id: Mapped[int]
    restaurant_id: Mapped[int]
    branch_id: Mapped[int]
    created_at: Mapped[datetime]
    membership_id: Mapped[int]
    function_id: Mapped[int]
    active: Mapped[bool]
    assigned_by: Mapped[int]


# ==============================================
# PUBLIC ISSUED LINKS AND NON-AUTHORIZING SIGNALS
# Public read identifiers contain no personal data or permission assertions.
# ==============================================


class DiningPublicLink(DiningBase):
    """Retain a stable emitted version; rotation invalidates rather than rewrites it."""

    __table__ = D1_METADATA.tables["dining_public_links"]
    id: Mapped[int]
    restaurant_id: Mapped[int]
    branch_id: Mapped[int]
    created_at: Mapped[datetime]
    public_id: Mapped[str]
    reference: Mapped[str]
    kind: Mapped[str]
    version: Mapped[int]
    generation: Mapped[int]
    active: Mapped[bool]
    table_id: Mapped[int | None]
    request_id: Mapped[int | None]
    invoice_id: Mapped[int | None]
    receipt_id: Mapped[int | None]
    snapshot: Mapped[dict[str, JsonValue]]
    digest: Mapped[str]
    invalidated_reason: Mapped[str | None]


# ==============================================
# DININGPRESENCESIGNAL
# Represent a customer's request for staff observation, never an occupation.
# ==============================================


class DiningPresenceSignal(DiningBase):
    """Represent a customer's request for staff observation, never an occupation."""

    __table__ = D1_METADATA.tables["dining_presence_signals"]
    id: Mapped[int]
    restaurant_id: Mapped[int]
    branch_id: Mapped[int]
    created_at: Mapped[datetime]
    public_link_id: Mapped[int]
    table_id: Mapped[int]
    token_hash: Mapped[str]
    party_size: Mapped[int]
    status: Mapped[str]
    expires_at: Mapped[datetime]


# ==============================================
# CONTROLLED VISITS AND EXACT ORDER PROVENANCE
# Bearer secrets are hashed and checked against the active physical occupation.
# ==============================================


class DiningVisit(DiningBase):
    """Bind one observed presence to one table/occupation without financial authority."""

    __table__ = D1_METADATA.tables["dining_visits"]
    id: Mapped[int]
    restaurant_id: Mapped[int]
    branch_id: Mapped[int]
    created_at: Mapped[datetime]
    public_link_id: Mapped[int]
    presence_id: Mapped[int]
    occupation_id: Mapped[int]
    table_id: Mapped[int]
    token_hash: Mapped[str]
    status: Mapped[str]
    ended_at: Mapped[datetime | None]


# ==============================================
# DININGVISITORDER
# Retain exact tariff-sourced money separately from the explicit legacy Float bridge.
# ==============================================


class DiningVisitOrder(DiningBase):
    """Retain exact tariff-sourced money separately from the explicit legacy Float bridge."""

    __table__ = D1_METADATA.tables["dining_visit_orders"]
    id: Mapped[int]
    restaurant_id: Mapped[int]
    branch_id: Mapped[int]
    created_at: Mapped[datetime]
    visit_id: Mapped[int]
    order_id: Mapped[int]
    idempotency_key: Mapped[str]
    currency: Mapped[str]
    exact_lines: Mapped[list[dict[str, JsonValue]]]
    total: Mapped[Decimal]
    digest: Mapped[str]
