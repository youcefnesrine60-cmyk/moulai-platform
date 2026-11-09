# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# OPT-IN DINING ORM REGISTRY
# Map the frozen D1 schema without altering the validated legacy/S1a registry.
# ==============================================

"""Typed dining records on independent metadata; importing them performs no DDL.

External tables are FK references only. Runtime admission and migrations remain
explicit, so importing dining tests never adds required tables to legacy Base.
"""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND INDEPENDENT METADATA
# Keep JSON and monetary annotations explicit and avoid eager legacy relationships.
# ==============================================

from datetime import (
    date,
    datetime,
)
from decimal import Decimal
from typing import TYPE_CHECKING

from pydantic import JsonValue
from sqlalchemy import (
    CheckConstraint,
    String,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
)

from migration_support.dining_d1_schema import dining_schema
from migration_support.dining_d1d import (
    CAPABILITY_CHECK,
    add_service_schema,
)

D1_METADATA = dining_schema()
add_service_schema(metadata=D1_METADATA)
# The application overlays D1b; the frozen D1a factory remains unchanged.
_grant_table = D1_METADATA.tables["dining_grants"]
_grant_table.c.capability.type = String(64)
for _constraint in tuple(_grant_table.constraints):
    if _constraint.name == "ck_dining_capability":
        _grant_table.constraints.remove(_constraint)
_grant_table.append_constraint(
    CheckConstraint(CAPABILITY_CHECK, name="ck_dining_capability")
)

# ==============================================
# INDEPENDENT DECLARATIVE BASE
# Expose no create_all helper and perform no connection or configuration reads.
# ==============================================


class DiningBase(DeclarativeBase):
    """Own only dining mappings; existing application Base remains unchanged."""

    metadata = D1_METADATA

    if TYPE_CHECKING:
        # Every D1 record declares these mapped fields explicitly at runtime.
        # Keep their generic repository contract visible to static analyzers.
        id: Mapped[int]
        restaurant_id: Mapped[int]
        branch_id: Mapped[int]


# ==============================================
# DININGPOLICY
# Owner-configured branch timezone and explicit operational policies.
# ==============================================


class DiningPolicy(DiningBase):
    """Owner-configured branch timezone and explicit operational policies."""

    __table__ = D1_METADATA.tables["dining_policies"]

    id: Mapped[int]
    restaurant_id: Mapped[int]
    branch_id: Mapped[int]
    created_at: Mapped[datetime]
    timezone: Mapped[str]
    settings: Mapped[dict[str, JsonValue]]


# ==============================================
# DININGREFERENCE
# Localized branch reference vocabulary with distinct semantic kinds.
# ==============================================


class DiningReference(DiningBase):
    """Localized branch reference vocabulary with distinct semantic kinds."""

    __table__ = D1_METADATA.tables["dining_references"]

    id: Mapped[int]
    restaurant_id: Mapped[int]
    branch_id: Mapped[int]
    created_at: Mapped[datetime]
    kind: Mapped[str]
    code: Mapped[str]
    labels: Mapped[dict[str, JsonValue]]
    active: Mapped[bool]
    pricing_ref: Mapped[str | None]


# ==============================================
# DININGGRANT
# Explicit dining capabilities, independent of SaaS payment permissions.
# ==============================================


class DiningGrant(DiningBase):
    """Explicit dining capabilities, independent of SaaS payment permissions."""

    __table__ = D1_METADATA.tables["dining_grants"]

    id: Mapped[int]
    restaurant_id: Mapped[int]
    branch_id: Mapped[int]
    created_at: Mapped[datetime]
    membership_id: Mapped[int]
    capability: Mapped[str]
    actor_kind: Mapped[str]
    active: Mapped[bool]
    granted_by: Mapped[int]


# ==============================================
# DININGCALENDAR
# Weekly services and overriding dated opening exceptions.
# ==============================================


class DiningCalendar(DiningBase):
    """Weekly services and overriding dated opening exceptions."""

    __table__ = D1_METADATA.tables["dining_calendar"]

    id: Mapped[int]
    restaurant_id: Mapped[int]
    branch_id: Mapped[int]
    created_at: Mapped[datetime]
    weekday: Mapped[int | None]
    service_date: Mapped[date | None]
    windows: Mapped[list[dict[str, JsonValue]]]


# ==============================================
# DININGTABLE
# Descriptive capacity and independent physical table state.
# ==============================================


class DiningTable(DiningBase):
    """Descriptive capacity and independent physical table state."""

    __table__ = D1_METADATA.tables["dining_tables"]

    id: Mapped[int]
    restaurant_id: Mapped[int]
    branch_id: Mapped[int]
    created_at: Mapped[datetime]
    code: Mapped[str]
    name: Mapped[str | None]
    min_capacity: Mapped[int]
    max_capacity: Mapped[int]
    shape_id: Mapped[int]
    category_id: Mapped[int]
    zone_id: Mapped[int]
    location_id: Mapped[int]
    description: Mapped[str]
    floor_label: Mapped[str | None]
    room_label: Mapped[str | None]
    photos: Mapped[list[str]]
    pricing_ref: Mapped[str]
    in_service: Mapped[bool]
    physical_state: Mapped[str]
    revision: Mapped[int]


# ==============================================
# DININGTRAIT
# Distinct view, proximity and feature links for one scoped table.
# ==============================================


class DiningTrait(DiningBase):
    """Distinct view, proximity and feature links for one scoped table."""

    __table__ = D1_METADATA.tables["dining_traits"]

    id: Mapped[int]
    restaurant_id: Mapped[int]
    branch_id: Mapped[int]
    created_at: Mapped[datetime]
    table_id: Mapped[int]
    reference_id: Mapped[int]
    kind: Mapped[str]


# ==============================================
# DININGCOMBINATION
# Explicit authorized grouping capacity and its own tariff reference.
# ==============================================


class DiningCombination(DiningBase):
    """Explicit authorized grouping capacity and its own tariff reference."""

    __table__ = D1_METADATA.tables["dining_combinations"]

    id: Mapped[int]
    restaurant_id: Mapped[int]
    branch_id: Mapped[int]
    created_at: Mapped[datetime]
    code: Mapped[str]
    min_capacity: Mapped[int]
    max_capacity: Mapped[int]
    pricing_ref: Mapped[str]
    active: Mapped[bool]


# ==============================================
# DININGMEMBER
# Scoped membership of one approved table combination.
# ==============================================


class DiningMember(DiningBase):
    """Scoped membership of one approved table combination."""

    __table__ = D1_METADATA.tables["dining_members"]

    id: Mapped[int]
    restaurant_id: Mapped[int]
    branch_id: Mapped[int]
    created_at: Mapped[datetime]
    combination_id: Mapped[int]
    table_id: Mapped[int]


# ==============================================
# DININGBLACKOUT
# Dated branch, zone or table unavailability.
# ==============================================


class DiningBlackout(DiningBase):
    """Dated branch, zone or table unavailability."""

    __table__ = D1_METADATA.tables["dining_blackouts"]

    id: Mapped[int]
    restaurant_id: Mapped[int]
    branch_id: Mapped[int]
    created_at: Mapped[datetime]
    table_id: Mapped[int | None]
    zone_id: Mapped[int | None]
    starts_at: Mapped[datetime]
    ends_at: Mapped[datetime]
    kind: Mapped[str]
    reason: Mapped[str]
    active: Mapped[bool]


# ==============================================
# DININGREQUEST
# Customer demand, interval, identity and reservation lifecycle.
# ==============================================


class DiningRequest(DiningBase):
    """Customer demand, interval, identity and reservation lifecycle."""

    __table__ = D1_METADATA.tables["dining_requests"]

    id: Mapped[int]
    restaurant_id: Mapped[int]
    branch_id: Mapped[int]
    created_at: Mapped[datetime]
    reference: Mapped[str]
    customer_issuer: Mapped[str]
    customer_subject: Mapped[str]
    customer_name: Mapped[str]
    contact: Mapped[str]
    starts_at: Mapped[datetime]
    ends_at: Mapped[datetime]
    party_size: Mapped[int]
    event_id: Mapped[int | None]
    preparation: Mapped[bool]
    criteria: Mapped[dict[str, JsonValue]]
    menu: Mapped[list[dict[str, JsonValue]]]
    status: Mapped[str]
    transmitted_at: Mapped[datetime | None]
    confirmed_at: Mapped[datetime | None]
    qr_token: Mapped[str | None]
    qr_hash: Mapped[str | None]


# ==============================================
# DININGREQUESTTABLE
# Requested table set, separate from actual occupation.
# ==============================================


class DiningRequestTable(DiningBase):
    """Requested table set, separate from actual occupation."""

    __table__ = D1_METADATA.tables["dining_request_tables"]

    id: Mapped[int]
    restaurant_id: Mapped[int]
    branch_id: Mapped[int]
    created_at: Mapped[datetime]
    request_id: Mapped[int]
    table_id: Mapped[int]


# ==============================================
# DININGCONFIRMATION
# Immutable human availability evidence with table revisions.
# ==============================================


class DiningConfirmation(DiningBase):
    """Immutable human availability evidence with table revisions."""

    __table__ = D1_METADATA.tables["dining_confirmations"]

    id: Mapped[int]
    restaurant_id: Mapped[int]
    branch_id: Mapped[int]
    created_at: Mapped[datetime]
    request_id: Mapped[int | None]
    starts_at: Mapped[datetime]
    ends_at: Mapped[datetime]
    valid_until: Mapped[datetime]
    table_versions: Mapped[dict[str, int]]
    membership_id: Mapped[int]
    origin: Mapped[str]


# ==============================================
# DININGTARIFF
# Explicit currency-specific price versions and nonoverlapping validity.
# ==============================================


class DiningTariff(DiningBase):
    """Explicit currency-specific price versions and nonoverlapping validity."""

    __table__ = D1_METADATA.tables["dining_tariffs"]

    id: Mapped[int]
    restaurant_id: Mapped[int]
    branch_id: Mapped[int]
    created_at: Mapped[datetime]
    reference: Mapped[str]
    component: Mapped[str]
    currency: Mapped[str]
    unit: Mapped[str]
    unit_price: Mapped[Decimal]
    valid_from: Mapped[datetime]
    valid_until: Mapped[datetime | None]


# ==============================================
# DININGQUOTE
# Immutable exact-decimal proposal snapshots.
# ==============================================


class DiningQuote(DiningBase):
    """Immutable exact-decimal proposal snapshots."""

    __table__ = D1_METADATA.tables["dining_quotes"]

    id: Mapped[int]
    restaurant_id: Mapped[int]
    branch_id: Mapped[int]
    created_at: Mapped[datetime]
    request_id: Mapped[int]
    version: Mapped[int]
    currency: Mapped[str]
    amount: Mapped[Decimal]
    components: Mapped[list[dict[str, JsonValue]]]
    terms: Mapped[str]
    menu_digest: Mapped[str]
    digest: Mapped[str]
    expires_at: Mapped[datetime]


# ==============================================
# DININGACCEPTANCE
# Customer and restaurant acceptance of the exact same proposal digest.
# ==============================================


class DiningAcceptance(DiningBase):
    """Customer and restaurant acceptance of the exact same proposal digest."""

    __table__ = D1_METADATA.tables["dining_acceptances"]

    id: Mapped[int]
    restaurant_id: Mapped[int]
    branch_id: Mapped[int]
    created_at: Mapped[datetime]
    quote_id: Mapped[int]
    party: Mapped[str]
    digest: Mapped[str]
    author: Mapped[dict[str, JsonValue]]


# ==============================================
# DININGCLAIM
# Exclusive held, reserved or walk-in time ranges.
# ==============================================


class DiningClaim(DiningBase):
    """Exclusive held, reserved or walk-in time ranges."""

    __table__ = D1_METADATA.tables["dining_claims"]

    id: Mapped[int]
    restaurant_id: Mapped[int]
    branch_id: Mapped[int]
    created_at: Mapped[datetime]
    request_id: Mapped[int | None]
    table_id: Mapped[int]
    starts_at: Mapped[datetime]
    ends_at: Mapped[datetime]
    kind: Mapped[str]
    expires_at: Mapped[datetime | None]
    active: Mapped[bool]


# ==============================================
# DININGOCCUPATION
# Actual arrival, departure and planned/actual cleaning evidence.
# ==============================================


class DiningOccupation(DiningBase):
    """Actual arrival, departure and planned/actual cleaning evidence."""

    __table__ = D1_METADATA.tables["dining_occupations"]

    id: Mapped[int]
    restaurant_id: Mapped[int]
    branch_id: Mapped[int]
    created_at: Mapped[datetime]
    request_id: Mapped[int | None]
    party_size: Mapped[int]
    arrived_at: Mapped[datetime]
    expected_end: Mapped[datetime]
    departed_at: Mapped[datetime | None]
    cleaning_expected_start: Mapped[datetime]
    cleaning_actual_start: Mapped[datetime | None]
    cleaning_expected_end: Mapped[datetime]
    cleaning_actual_end: Mapped[datetime | None]
    status: Mapped[str]
    installed_by: Mapped[int]
    departure_by: Mapped[int | None]
    cleaned_by: Mapped[int | None]


# ==============================================
# DININGOCCUPATIONTABLE
# Physical assignment without automatic release at predicted end.
# ==============================================


class DiningOccupationTable(DiningBase):
    """Physical assignment without automatic release at predicted end."""

    __table__ = D1_METADATA.tables["dining_occupation_tables"]

    id: Mapped[int]
    restaurant_id: Mapped[int]
    branch_id: Mapped[int]
    created_at: Mapped[datetime]
    occupation_id: Mapped[int]
    table_id: Mapped[int]
    active: Mapped[bool]


# ==============================================
# DININGRECEIPT
# Committed restaurant receipt facts retained independently of confirmation.
# ==============================================


class DiningReceipt(DiningBase):
    """Committed restaurant receipt facts retained independently of confirmation."""

    __table__ = D1_METADATA.tables["dining_receipts"]

    id: Mapped[int]
    restaurant_id: Mapped[int]
    branch_id: Mapped[int]
    created_at: Mapped[datetime]
    request_id: Mapped[int]
    quote_id: Mapped[int]
    expected_amount: Mapped[Decimal]
    received_amount: Mapped[Decimal]
    currency: Mapped[str]
    mode: Mapped[str]
    reference: Mapped[str]
    received_at: Mapped[datetime]
    validated_by: Mapped[int]
    status: Mapped[str]
    review_reason: Mapped[str | None]


# ==============================================
# DININGINVOICE
# Currency-aware food invoice with frozen lines and source provenance.
# ==============================================


class DiningInvoice(DiningBase):
    """Currency-aware food invoice with frozen lines and source provenance."""

    __table__ = D1_METADATA.tables["dining_invoices"]

    id: Mapped[int]
    restaurant_id: Mapped[int]
    branch_id: Mapped[int]
    created_at: Mapped[datetime]
    request_id: Mapped[int | None]
    occupation_id: Mapped[int | None]
    status: Mapped[str]
    currency: Mapped[str]
    precision: Mapped[int]
    revision: Mapped[int]
    lines: Mapped[list[dict[str, JsonValue]]]
    provenance: Mapped[dict[str, JsonValue]]
    total: Mapped[Decimal]
    finalized_by: Mapped[int | None]
    finalized_at: Mapped[datetime | None]


# ==============================================
# DININGINVOICEORDER
# Unique source-order reconciliation retained with the invoice.
# ==============================================


class DiningInvoiceOrder(DiningBase):
    """Unique source-order reconciliation retained with the invoice."""

    __table__ = D1_METADATA.tables["dining_invoice_orders"]

    id: Mapped[int]
    restaurant_id: Mapped[int]
    branch_id: Mapped[int]
    created_at: Mapped[datetime]
    invoice_id: Mapped[int]
    order_id: Mapped[int]
    source_snapshot: Mapped[dict[str, JsonValue]]


# ==============================================
# DININGALLOCATION
# One-time advance application without changing invoice sales totals.
# ==============================================


class DiningAllocation(DiningBase):
    """One-time advance application without changing invoice sales totals."""

    __table__ = D1_METADATA.tables["dining_allocations"]

    id: Mapped[int]
    restaurant_id: Mapped[int]
    branch_id: Mapped[int]
    created_at: Mapped[datetime]
    request_id: Mapped[int]
    receipt_id: Mapped[int]
    invoice_id: Mapped[int]
    invoice_revision: Mapped[int]
    invoice_total: Mapped[Decimal]
    other_paid: Mapped[Decimal]
    amount: Mapped[Decimal]
    currency: Mapped[str]
    balance: Mapped[Decimal]


# ==============================================
# DININGEVENT
# Append-only actor-qualified operational history.
# ==============================================


class DiningEvent(DiningBase):
    """Append-only actor-qualified operational history."""

    __table__ = D1_METADATA.tables["dining_events"]

    id: Mapped[int]
    restaurant_id: Mapped[int]
    branch_id: Mapped[int]
    created_at: Mapped[datetime]
    request_id: Mapped[int | None]
    kind: Mapped[str]
    author: Mapped[dict[str, JsonValue]]
    details: Mapped[dict[str, JsonValue]]
    occurred_at: Mapped[datetime]


# ==============================================
# DININGOUTBOX
# Post-commit delivery jobs with stable deduplication keys.
# ==============================================


class DiningOutbox(DiningBase):
    """Post-commit delivery jobs with stable deduplication keys."""

    __table__ = D1_METADATA.tables["dining_outbox"]

    id: Mapped[int]
    restaurant_id: Mapped[int]
    branch_id: Mapped[int]
    created_at: Mapped[datetime]
    request_id: Mapped[int | None]
    event_key: Mapped[str]
    target: Mapped[str]
    payload: Mapped[dict[str, JsonValue]]
    due_at: Mapped[datetime]
    status: Mapped[str]
    attempts: Mapped[int]
    delivery_reference: Mapped[str | None]


# ==============================================
# PUBLIC OPT-IN MODEL NAMES
# Keep model discovery explicit instead of modifying app.models imports.
# ==============================================

__all__ = [
    "D1_METADATA",
    "DiningAcceptance",
    "DiningAllocation",
    "DiningBase",
    "DiningBlackout",
    "DiningCalendar",
    "DiningClaim",
    "DiningCombination",
    "DiningConfirmation",
    "DiningEvent",
    "DiningGrant",
    "DiningInvoice",
    "DiningInvoiceOrder",
    "DiningMember",
    "DiningOccupation",
    "DiningOccupationTable",
    "DiningOutbox",
    "DiningPolicy",
    "DiningQuote",
    "DiningReceipt",
    "DiningReference",
    "DiningRequest",
    "DiningRequestTable",
    "DiningTable",
    "DiningTariff",
    "DiningTrait",
]
