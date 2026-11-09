# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# DINING INPUT AND FINANCIAL CONTRACTS
# Reject ambiguous time, currency and monetary inputs before scoped operations.
# ==============================================

"""Strict dining request contracts; missing business policies have no defaults."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND SHARED CONTRACT TYPES
# Represent money as Decimal and use timezone-aware instants throughout.
# ==============================================

from datetime import (
    datetime,
    time,
)
from decimal import Decimal
from typing import (
    Annotated,
    Literal,
    TypeAlias,
)
from zoneinfo import (
    ZoneInfo,
    ZoneInfoNotFoundError,
)

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    JsonValue,
    field_validator,
    model_validator,
)
from pydantic_core import PydanticCustomError

# ==============================================
# LOSSLESS MONEY INPUT
# A float is already imprecise and cannot become an authoritative new amount.
# ==============================================


def decimal_input(value: object) -> object:
    """Reject floats and booleans; Decimal parsing then validates exact input."""
    if isinstance(value, (float, bool)):
        raise PydanticCustomError(
            "dining_exact_decimal_required", "Exact decimal input required"
        )
    return value


ExactDecimal: TypeAlias = Annotated[Decimal, BeforeValidator(decimal_input)]
Capability: TypeAlias = Literal[
    "read",
    "service",
    "clean",
    "collect",
    "assistant",
    "reservations.cancel_before_arrival",
    "finance.read",
    "invoices.create",
    "invoices.finalize",
    "advances.allocate",
    "orders.read",
    "orders.approve",
    "orders.prepare",
    "orders.complete",
    "documents.issue",
]
PhysicalState: TypeAlias = Literal[
    "available", "occupied", "dirty", "maintenance", "out_of_service"
]
ReferenceKind: TypeAlias = Literal[
    "shape", "category", "zone", "location", "view", "proximity", "feature", "event"
]
JsonObject: TypeAlias = dict[str, JsonValue]


# ==============================================
# COMMON CLOSED REQUEST MODEL
# Refuse extra fields such as client-supplied authority, approval or server time.
# ==============================================


class DiningInput(BaseModel):
    """Accept only documented fields and preserve caller-provided exact values."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


# ==============================================
# EXPLICIT OPENING WINDOW
# Crossing midnight and ambiguous DST folds require intentional configuration.
# ==============================================


class OpeningWindow(DiningInput):
    """One local service; the branch timezone converts it to concrete instants."""

    start: time
    end: time
    next_day: bool
    start_fold: Literal[0, 1] | None = None
    end_fold: Literal[0, 1] | None = None

    # ==============================================
    # VALIDATE WINDOW
    # Reject offsets on wall-clock fields and empty/nonpositive services.
    # ==============================================

    @model_validator(mode="after")
    def validate_window(self) -> OpeningWindow:
        """Reject offsets on wall-clock fields and empty/nonpositive services."""
        if (
            self.start.tzinfo
            or self.end.tzinfo
            or (not self.next_day and self.end <= self.start)
        ):
            raise ValueError("dining_opening_window_invalid")
        return self


# ==============================================
# PERSISTED RESTAURANT POLICY
# Every timing and recipient choice is supplied by an authorized owner.
# ==============================================


class DiningPolicyInput(DiningInput):
    """Define operational timings and approved currency precision without seeds."""

    timezone: str = Field(min_length=1, max_length=100)
    response_seconds: int = Field(strict=True, gt=0)
    hold_seconds: int = Field(strict=True, gt=0)
    lateness_seconds: int = Field(strict=True, ge=0)
    preparation_seconds: int = Field(strict=True, ge=0)
    cleaning_seconds: int = Field(strict=True, ge=0)
    confirmation_seconds: int = Field(strict=True, gt=0)
    confirmation_scope: Literal["tables"]
    alert_offsets_seconds: tuple[int, ...]
    service_recipients: tuple[int, ...]
    escalation_recipients: tuple[int, ...]
    currencies: dict[str, int]
    payment_instructions: dict[str, str]
    terms: str = Field(min_length=1, max_length=8000)

    # ==============================================
    # VALIDATE POLICY
    # Require IANA timezone, explicit recipients and unambiguous precisions.
    # ==============================================

    @model_validator(mode="after")
    def validate_policy(self) -> DiningPolicyInput:
        """Require IANA timezone, explicit recipients and unambiguous precisions."""
        try:
            ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as error:
            raise ValueError("dining_timezone_unknown") from error
        if (
            not self.currencies
            or not self.service_recipients
            or not self.alert_offsets_seconds
            or not self.payment_instructions
            or any(type(x) is not int or x < 0 for x in self.alert_offsets_seconds)
            or any(
                type(x) is not int or x <= 0
                for x in (*self.service_recipients, *self.escalation_recipients)
            )
            or any(
                len(code) != 3
                or not code.isascii()
                or not code.isalpha()
                or code != code.upper()
                or type(precision) is not int
                or not 0 <= precision <= 8
                for code, precision in self.currencies.items()
            )
            or any(
                not key or not value for key, value in self.payment_instructions.items()
            )
        ):
            raise ValueError("dining_explicit_policy_required")
        return self


# ==============================================
# CONFIGURABLE REFERENCES AND DESCRIPTIVE TABLES
# Keep localized labels and semantic kinds distinct from current physical state.
# ==============================================


class ReferenceInput(DiningInput):
    """Owner-managed structured vocabulary, including separate views/proximities."""

    kind: ReferenceKind
    code: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    labels: dict[Literal["fr", "en", "ar"], str]
    active: bool
    pricing_ref: str | None = Field(default=None, min_length=1, max_length=100)

    # ==============================================
    # VALIDATE LABELS
    # Require actual labels in the three supported interface languages.
    # ==============================================

    @model_validator(mode="after")
    def validate_labels(self) -> ReferenceInput:
        """Require actual labels in the three supported interface languages."""
        if set(self.labels) != {"fr", "en", "ar"} or any(
            not value.strip() for value in self.labels.values()
        ):
            raise ValueError("dining_reference_translations_required")
        if self.kind == "shape" and self.code not in {
            "round",
            "rectangular",
            "square",
            "oval",
        }:
            raise ValueError("dining_shape_unsupported")
        return self


# ==============================================
# TABLEINPUT
# Describe a branch table; installation and cleaning have separate operations.
# ==============================================


class TableInput(DiningInput):
    """Describe a branch table; installation and cleaning have separate operations."""

    code: str = Field(min_length=1, max_length=80)
    name: str | None = Field(default=None, max_length=200)
    min_capacity: int = Field(strict=True, gt=0)
    max_capacity: int = Field(strict=True, gt=0)
    shape_id: int = Field(strict=True, gt=0)
    category_id: int = Field(strict=True, gt=0)
    zone_id: int = Field(strict=True, gt=0)
    location_id: int = Field(strict=True, gt=0)
    description: str = Field(max_length=8000)
    floor_label: str | None = Field(default=None, max_length=160)
    room_label: str | None = Field(default=None, max_length=160)
    photos: tuple[str, ...]
    pricing_ref: str = Field(min_length=1, max_length=100)
    in_service: bool
    trait_ids: tuple[int, ...]

    # ==============================================
    # VALIDATE CAPACITY
    # Reject inverted capacity, duplicate traits and unsafe photo URI schemes.
    # ==============================================

    @model_validator(mode="after")
    def validate_capacity(self) -> TableInput:
        """Reject inverted capacity, duplicate traits and unsafe photo URI schemes."""
        if self.max_capacity < self.min_capacity or len(set(self.trait_ids)) != len(
            self.trait_ids
        ):
            raise ValueError("dining_table_description_invalid")
        if any(
            not (
                photo.startswith("https://")
                or (photo.startswith("/") and not photo.startswith("//"))
            )
            for photo in self.photos
        ):
            raise ValueError("dining_photo_reference_invalid")
        return self


# ==============================================
# COMBINATIONINPUT
# Explicit owner-approved grouping and tariff; never sum capacities silently.
# ==============================================


class CombinationInput(DiningInput):
    """Explicit owner-approved grouping and tariff; never sum capacities silently."""

    code: str = Field(min_length=1, max_length=80)
    table_ids: tuple[int, ...]
    min_capacity: int = Field(strict=True, gt=0)
    max_capacity: int = Field(strict=True, gt=0)
    pricing_ref: str = Field(min_length=1, max_length=100)
    active: bool

    # ==============================================
    # VALIDATE MEMBERS
    # Require a real multi-table set with an intentional capacity range.
    # ==============================================

    @model_validator(mode="after")
    def validate_members(self) -> CombinationInput:
        """Require a real multi-table set with an intentional capacity range."""
        if (
            len(set(self.table_ids)) != len(self.table_ids)
            or len(self.table_ids) < 2
            or self.max_capacity < self.min_capacity
        ):
            raise ValueError("dining_combination_invalid")
        return self


# ==============================================
# CUSTOMER DEMAND AND VERSIONED MENU QUANTITIES
# Compute the end from exact elapsed seconds; identity never comes from this body.
# ==============================================


class MenuItemInput(DiningInput):
    """Reference an existing product with an exact strictly positive quantity."""

    product_id: int = Field(strict=True, gt=0)
    quantity: ExactDecimal = Field(gt=0, max_digits=18, decimal_places=6)


# ==============================================
# REQUESTINPUT
# A customer request is not a reservation or a declaration of available space.
# ==============================================


class RequestInput(DiningInput):
    """A customer request is not a reservation or a declaration of available space."""

    customer_name: str = Field(min_length=1, max_length=200)
    contact: str = Field(min_length=1, max_length=300)
    starts_at: datetime
    duration_seconds: int = Field(strict=True, gt=0)
    party_size: int = Field(strict=True, gt=0)
    table_ids: tuple[int, ...]
    criteria: JsonObject
    event_id: int | None = Field(default=None, strict=True, gt=0)
    preparation: bool
    menu: tuple[MenuItemInput, ...]

    # ==============================================
    # VALIDATE PERIOD
    # Reject ambiguous instants, duplicate assignments and unidentified events.
    # ==============================================

    @model_validator(mode="after")
    def validate_period(self) -> RequestInput:
        """Reject ambiguous instants, duplicate assignments and unidentified events."""
        if self.starts_at.tzinfo is None or self.starts_at.utcoffset() is None:
            raise ValueError("dining_timezone_aware_start_required")
        if len(set(self.table_ids)) != len(self.table_ids) or (
            not self.table_ids and not self.criteria
        ):
            raise ValueError("dining_table_selection_required")
        if self.preparation and self.event_id is None:
            raise ValueError("dining_preparation_event_required")
        if len({line.product_id for line in self.menu}) != len(self.menu):
            raise ValueError("dining_menu_product_duplicate")
        return self


# ==============================================
# TARIFF AND PAYMENT FACT INPUTS
# Keep currency and validity explicit; a client upload cannot validate receipt.
# ==============================================


class TariffInput(DiningInput):
    """Append one currency-specific rate version; overlap is also excluded by SQL."""

    reference: str = Field(min_length=1, max_length=100)
    component: Literal["table", "preparation", "menu"]
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    unit: Literal["per_hour", "flat", "per_person", "per_item"]
    unit_price: ExactDecimal = Field(ge=0, max_digits=24, decimal_places=8)
    valid_from: datetime
    valid_until: datetime | None

    # ==============================================
    # VALIDATE VALIDITY
    # Require aware validity bounds and the approved component/unit pairing.
    # ==============================================

    @model_validator(mode="after")
    def validate_validity(self) -> TariffInput:
        """Require aware validity bounds and the approved component/unit pairing."""
        if self.valid_from.tzinfo is None or (
            self.valid_until is not None
            and (self.valid_until.tzinfo is None or self.valid_until <= self.valid_from)
        ):
            raise ValueError("dining_tariff_validity_invalid")
        supported = {
            "table": {"per_hour"},
            "preparation": {"flat", "per_person", "per_hour"},
            "menu": {"per_item"},
        }
        if self.unit not in supported[self.component]:
            raise ValueError("dining_tariff_unit_invalid")
        return self


# ==============================================
# RECEIPTINPUT
# Human-verified facts; atypical amounts/currency remain recorded for review.
# ==============================================


class ReceiptInput(DiningInput):
    """Human-verified facts; atypical amounts/currency remain recorded for review."""

    request_id: int = Field(strict=True, gt=0)
    quote_id: int = Field(strict=True, gt=0)
    received_amount: ExactDecimal = Field(gt=0, max_digits=24, decimal_places=8)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    mode: str = Field(min_length=1, max_length=30)
    reference: str = Field(min_length=1, max_length=120)
    received_at: datetime

    # ==============================================
    # VALIDATE RECEIVED AT
    # A timezone-free receipt cannot establish whether payment was timely.
    # ==============================================

    @field_validator("received_at")
    @classmethod
    def validate_received_at(cls, value: datetime) -> datetime:
        """A timezone-free receipt cannot establish whether payment was timely."""
        if value.tzinfo is None:
            raise ValueError("dining_receipt_timezone_required")
        return value


# ==============================================
# REVIEWED LEGACY FOOD-LINE PROVENANCE
# Decimal values require a named authoritative source, never a float conversion.
# ==============================================


class InvoiceLineInput(DiningInput):
    """One reconciled existing order item and independently verified exact values."""

    order_id: int = Field(strict=True, gt=0)
    order_item_id: int = Field(strict=True, gt=0)
    description: str = Field(min_length=1, max_length=500)
    quantity: ExactDecimal = Field(gt=0, max_digits=18, decimal_places=6)
    unit_price: ExactDecimal = Field(ge=0, max_digits=24, decimal_places=8)
    source_reference: str = Field(min_length=1, max_length=500)


# ==============================================
# INVOICEINPUT
# Prepare one invoice for a reservation, with no implicit currency or fiscal rule.
# ==============================================


class InvoiceInput(DiningInput):
    """Prepare one invoice for a reservation, with no implicit currency or fiscal rule."""

    request_id: int | None = Field(default=None, strict=True, gt=0)
    occupation_id: int | None = Field(default=None, strict=True, gt=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    lines: tuple[InvoiceLineInput, ...]
    currency_source: str = Field(min_length=1, max_length=500)
    rounding_source: str = Field(min_length=1, max_length=500)
    reconciliation_reference: str = Field(min_length=1, max_length=500)
    legacy_discrepancies_acknowledged: bool

    # ==============================================
    # VALIDATE LINES
    # Require a nonempty unique item snapshot before reconciliation can begin.
    # ==============================================

    @model_validator(mode="after")
    def validate_lines(self) -> InvoiceInput:
        """Require a nonempty unique item snapshot before reconciliation can begin."""
        if (self.request_id is None) == (self.occupation_id is None):
            raise ValueError("dining_invoice_exactly_one_context_required")
        if not self.lines or len({x.order_item_id for x in self.lines}) != len(
            self.lines
        ):
            raise ValueError("dining_invoice_lines_invalid")
        return self
