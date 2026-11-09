# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# CLOSED DINING FORM OPERATIONS
# Validate every local form through a discriminated typed contract.
# ==============================================

"""No caller-supplied actor, restaurant scope, approval or calculated amount."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND EXPLICIT LOCAL CONTRACTS
# Reuse typed module dependencies without creating a connection or enabling a transport.
# ==============================================

from datetime import (
    date,
    datetime,
)
from typing import (
    Annotated,
    Literal,
    TypeAlias,
)

from pydantic import Field

from app.schemas.dining import (
    Capability,
    CombinationInput,
    DiningInput,
    DiningPolicyInput,
    InvoiceInput,
    OpeningWindow,
    ReferenceInput,
    RequestInput,
    TableInput,
    TariffInput,
)

PositiveId: TypeAlias = Annotated[int, Field(strict=True, gt=0)]


# ==============================================
# POLICYOPERATION
# Persist explicitly supplied owner policies, never guessed timings.
# ==============================================


class PolicyOperation(DiningInput):
    """Persist explicitly supplied owner policies, never guessed timings."""

    operation: Literal["policy"]
    data: DiningPolicyInput


# ==============================================
# REFERENCEOPERATION
# Create or amend localized descriptive references without deleting history.
# ==============================================


class ReferenceOperation(DiningInput):
    """Create or amend localized descriptive references without deleting history."""

    operation: Literal["reference"]
    identifier: PositiveId | None = None
    acknowledge_conflicts: bool = False
    data: ReferenceInput


# ==============================================
# TABLEOPERATION
# Describe tables separately from observed physical transitions.
# ==============================================


class TableOperation(DiningInput):
    """Describe tables separately from observed physical transitions."""

    operation: Literal["table"]
    identifier: PositiveId | None = None
    initial_state: Literal["available", "maintenance", "out_of_service"] | None = None
    acknowledge_conflicts: bool = False
    data: TableInput


# ==============================================
# COMBINATIONOPERATION
# Configure explicit multi-table capacity and tariff reference.
# ==============================================


class CombinationOperation(DiningInput):
    """Configure explicit multi-table capacity and tariff reference."""

    operation: Literal["combination"]
    identifier: PositiveId | None = None
    acknowledge_conflicts: bool = False
    data: CombinationInput


# ==============================================
# CALENDAROPERATION
# Choose weekly or dated services explicitly, including a closed empty day.
# ==============================================


class CalendarOperation(DiningInput):
    """Choose weekly or dated services explicitly, including a closed empty day."""

    operation: Literal["calendar"]
    weekday: Annotated[int, Field(strict=True, ge=0, le=6)] | None = None
    service_date: date | None = None
    windows: tuple[OpeningWindow, ...]
    acknowledge_conflicts: bool = False


# ==============================================
# TARIFFOPERATION
# Append an explicit currency-specific rate, not a catalogue Float conversion.
# ==============================================


class TariffOperation(DiningInput):
    """Append an explicit currency-specific rate, not a catalogue Float conversion."""

    operation: Literal["tariff"]
    data: TariffInput


# ==============================================
# GRANTOPERATION
# Owner explicitly assigns one module capability in this branch.
# ==============================================


class GrantOperation(DiningInput):
    """Owner explicitly assigns one module capability in this branch."""

    operation: Literal["grant"]
    membership_id: PositiveId
    capability: Capability
    actor_kind: Literal["human", "assistant"]
    active: bool


# ==============================================
# BLACKOUTOPERATION
# Block a branch, zone or table while retaining affected reservations.
# ==============================================


class BlackoutOperation(DiningInput):
    """Block a branch, zone or table while retaining affected reservations."""

    operation: Literal["blackout"]
    starts_at: datetime
    ends_at: datetime
    kind: Literal["closure", "maintenance", "preparation", "cleaning"]
    reason: str = Field(min_length=1, max_length=500)
    table_id: PositiveId | None = None
    zone_id: PositiveId | None = None
    acknowledge_conflicts: bool = False


# ==============================================
# CLOSEBLACKOUTOPERATION
# Close a planning block; this is never an observed physical release.
# ==============================================


class CloseBlackoutOperation(DiningInput):
    """Close a planning block; this is never an observed physical release."""

    operation: Literal["close_blackout"]
    identifier: PositiveId


# ==============================================
# REQUESTOPERATION
# Collect a request; a separately verified customer proof is still required.
# ==============================================


class RequestOperation(DiningInput):
    """Collect a request; a separately verified customer proof is still required."""

    operation: Literal["request"]
    data: RequestInput


# ==============================================
# SELECTOPERATION
# Select the customer's exact table set before money is received.
# ==============================================


class SelectOperation(DiningInput):
    """Select the customer's exact table set before money is received."""

    operation: Literal["select_tables"]
    request_id: PositiveId
    table_ids: tuple[PositiveId, ...]


# ==============================================
# PROOFOPERATION
# A human service member certifies one complete protected interval.
# ==============================================


class ProofOperation(DiningInput):
    """A human service member certifies one complete protected interval."""

    operation: Literal["human_proof"]
    request_id: PositiveId | None = None
    table_ids: tuple[PositiveId, ...]
    starts_at: datetime
    ends_at: datetime


# ==============================================
# QUOTEOPERATION
# Calculate a version from explicit rates and currency.
# ==============================================


class QuoteOperation(DiningInput):
    """Calculate a version from explicit rates and currency."""

    operation: Literal["quote"]
    request_id: PositiveId
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    expires_at: datetime


# ==============================================
# RESTAURANTCONSENTOPERATION
# Accept the same menu/quote version as the customer, independently.
# ==============================================


class RestaurantConsentOperation(DiningInput):
    """Accept the same menu/quote version as the customer, independently."""

    operation: Literal["restaurant_consent"]
    quote_id: PositiveId
    digest: str = Field(pattern=r"^[a-f0-9]{64}$")


# ==============================================
# HOLDOPERATION
# Protect an accepted proposal before revealing payment instructions.
# ==============================================


class HoldOperation(DiningInput):
    """Protect an accepted proposal before revealing payment instructions."""

    operation: Literal["hold"]
    request_id: PositiveId
    quote_id: PositiveId


# ==============================================
# FINALIZEOPERATION
# Use either the human gate or the full assistant exception, without crossover.
# ==============================================


class FinalizeOperation(DiningInput):
    """Use either the human gate or the full assistant exception, without crossover."""

    operation: Literal["confirm_human", "confirm_assistant"]
    request_id: PositiveId
    quote_id: PositiveId
    receipt_id: PositiveId


# ==============================================
# ARRIVALOPERATION
# Install a party only after actual physical vacancy and applicable checks.
# ==============================================


class ArrivalOperation(DiningInput):
    """Install a party only after actual physical vacancy and applicable checks."""

    operation: Literal["arrival"]
    request_id: PositiveId | None
    table_ids: tuple[PositiveId, ...]
    party_size: Annotated[int, Field(strict=True, gt=0)]
    expected_end: datetime


# ==============================================
# PHYSICALOPERATION
# Keep observed departure, cleaning start and cleaning completion separate.
# ==============================================


class PhysicalOperation(DiningInput):
    """Keep observed departure, cleaning start and cleaning completion separate."""

    operation: Literal["departure", "start_cleaning", "finish_cleaning"]
    occupation_id: PositiveId


# ==============================================
# EXTENSIONOPERATION
# Record a real overrun without deleting a later booking.
# ==============================================


class ExtensionOperation(DiningInput):
    """Record a real overrun without deleting a later booking."""

    operation: Literal["extend"]
    occupation_id: PositiveId
    expected_end: datetime


# ==============================================
# STATEOPERATION
# Human operational state cannot bypass departure or cleaning.
# ==============================================


class StateOperation(DiningInput):
    """Human operational state cannot bypass departure or cleaning."""

    operation: Literal["physical_state"]
    table_id: PositiveId
    state: Literal["available", "maintenance", "out_of_service"]


# ==============================================
# SIGNALOPERATION
# Transmit an operational/customer signal without interpreting it as consent.
# ==============================================


class SignalOperation(DiningInput):
    """Transmit an operational/customer signal without interpreting it as consent."""

    operation: Literal["signal"]
    reason: str = Field(min_length=1, max_length=1000)
    request_id: PositiveId
    kind: Literal[
        "customer_departure",
        "customer_cancellation_requested",
        "late_arrival",
        "expected_end_passed",
    ]


# ==============================================
# CANCELOPERATION
# Require dedicated human authority and retain the cancellation reason/origin.
# ==============================================


class CancelOperation(DiningInput):
    """Require dedicated human authority and retain the cancellation reason/origin."""

    operation: Literal["cancel_before_arrival"]
    request_id: PositiveId
    reason: str = Field(min_length=1, max_length=1000)
    origin: Literal["human", "customer", "assistant"]


# ==============================================
# INVOICEOPERATION
# Reconcile all food lines against explicitly identified exact sources.
# ==============================================


class InvoiceOperation(DiningInput):
    """Reconcile all food lines against explicitly identified exact sources."""

    operation: Literal["invoice"]
    data: InvoiceInput


# ==============================================
# INVOICEFINALIZEOPERATION
# Finalize only the reviewed draft revision, applying verified money once.
# ==============================================


class InvoiceFinalizeOperation(DiningInput):
    """Finalize only the reviewed draft revision, applying verified money once."""

    operation: Literal["finalize_invoice"]
    invoice_id: PositiveId
    expected_revision: PositiveId


# ==============================================
# ALLOCATIONOPERATION
# Idempotently apply a matching verified receipt; never receive money again.
# ==============================================


class AllocationOperation(DiningInput):
    """Idempotently apply a matching verified receipt; never receive money again."""

    operation: Literal["allocate"]
    invoice_id: PositiveId
    receipt_id: PositiveId


# ==============================================
# DEADLINEOPERATION
# Explicitly scan deadlines; this command performs no real delivery.
# ==============================================


class DeadlineOperation(DiningInput):
    """Explicitly scan deadlines; this command performs no real delivery."""

    operation: Literal["scan_deadlines"]


DiningOperation: TypeAlias = Annotated[
    PolicyOperation
    | ReferenceOperation
    | TableOperation
    | CombinationOperation
    | CalendarOperation
    | TariffOperation
    | GrantOperation
    | BlackoutOperation
    | CloseBlackoutOperation
    | RequestOperation
    | SelectOperation
    | ProofOperation
    | QuoteOperation
    | RestaurantConsentOperation
    | HoldOperation
    | FinalizeOperation
    | ArrivalOperation
    | PhysicalOperation
    | ExtensionOperation
    | StateOperation
    | SignalOperation
    | CancelOperation
    | InvoiceOperation
    | InvoiceFinalizeOperation
    | AllocationOperation
    | DeadlineOperation,
    Field(discriminator="operation"),
]
