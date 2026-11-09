# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# TYPED DINING OPERATION DISPATCH
# Map closed form contracts to explicit business methods without reflection.
# ==============================================

"""All authority remains in the transaction-bound services; receipts stay separate."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND EXPLICIT LOCAL CONTRACTS
# Reuse typed module dependencies without creating a connection or enabling a transport.
# ==============================================

from app.core.security.oidc import OIDCPrincipal
from app.schemas.dining import JsonObject
from app.schemas.dining_operations import (
    AllocationOperation,
    ArrivalOperation,
    BlackoutOperation,
    CalendarOperation,
    CancelOperation,
    CloseBlackoutOperation,
    CombinationOperation,
    DeadlineOperation,
    DiningOperation,
    ExtensionOperation,
    FinalizeOperation,
    GrantOperation,
    HoldOperation,
    InvoiceFinalizeOperation,
    InvoiceOperation,
    PhysicalOperation,
    PolicyOperation,
    ProofOperation,
    QuoteOperation,
    ReferenceOperation,
    RequestOperation,
    RestaurantConsentOperation,
    SelectOperation,
    SignalOperation,
    StateOperation,
    TableOperation,
    TariffOperation,
)
from app.services.business.dining.service import DiningUnit
from app.services.business.dining.values import (
    DiningError,
    Period,
)

# ==============================================
# EXPLICIT COMMAND TO SERVICE MAPPING
# Never derive a method name from user input or grant a human power to the model.
# ==============================================


async def execute_operation(
    *, unit: DiningUnit, data: DiningOperation, customer: OIDCPrincipal | None
) -> JsonObject:
    """Execute exactly one validated operation in the existing owned transaction."""
    match data:
        case PolicyOperation():
            return {"identifier": await unit.configure(data=data.data)}
        case ReferenceOperation():
            if data.identifier is None:
                return {"identifier": await unit.create_reference(data=data.data)}
            return {
                "identifier": data.identifier,
                "conflicts": list(
                    await unit.update_reference(
                        identifier=data.identifier,
                        data=data.data,
                        acknowledge_conflicts=data.acknowledge_conflicts,
                    )
                ),
            }
        case TableOperation():
            if data.identifier is None:
                if data.initial_state is None:
                    raise DiningError(code="dining_initial_physical_state_required")
                return {
                    "identifier": await unit.create_table(
                        data=data.data, initial_state=data.initial_state
                    )
                }
            return {
                "identifier": data.identifier,
                "conflicts": list(
                    await unit.update_table(
                        table_id=data.identifier,
                        data=data.data,
                        acknowledge_conflicts=data.acknowledge_conflicts,
                    )
                ),
            }
        case CombinationOperation():
            if data.identifier is None:
                return {"identifier": await unit.create_combination(data=data.data)}
            return {
                "identifier": data.identifier,
                "conflicts": list(
                    await unit.update_combination(
                        identifier=data.identifier,
                        data=data.data,
                        acknowledge_conflicts=data.acknowledge_conflicts,
                    )
                ),
            }
        case CalendarOperation():
            identifier, conflicts = await unit.save_calendar(
                weekday=data.weekday,
                service_date=data.service_date,
                windows=data.windows,
                acknowledge_conflicts=data.acknowledge_conflicts,
            )
            return {"identifier": identifier, "conflicts": list(conflicts)}
        case TariffOperation():
            return {"identifier": await unit.create_tariff(data=data.data)}
        case GrantOperation():
            return {
                "identifier": await unit.grant(
                    membership_id=data.membership_id,
                    capability=data.capability,
                    actor_kind=data.actor_kind,
                    active=data.active,
                )
            }
        case BlackoutOperation():
            identifier, conflicts = await unit.create_blackout(
                period=Period(start=data.starts_at, end=data.ends_at),
                kind=data.kind,
                reason=data.reason,
                table_id=data.table_id,
                zone_id=data.zone_id,
                acknowledge_conflicts=data.acknowledge_conflicts,
            )
            return {"identifier": identifier, "conflicts": list(conflicts)}
        case CloseBlackoutOperation():
            await unit.close_blackout(identifier=data.identifier)
        case RequestOperation():
            if customer is None:
                raise DiningError(code="dining_verified_customer_proof_required")
            return {
                "identifier": await unit.create_request(
                    data=data.data, customer=customer
                )
            }
        case SelectOperation():
            await unit.select_tables(
                request_id=data.request_id, table_ids=data.table_ids
            )
        case ProofOperation():
            return {
                "identifier": await unit.confirm_availability(
                    request_id=data.request_id,
                    table_ids=data.table_ids,
                    period=Period(start=data.starts_at, end=data.ends_at),
                )
            }
        case QuoteOperation():
            return {
                "identifier": await unit.create_quote(
                    request_id=data.request_id,
                    currency=data.currency,
                    expires_at=data.expires_at,
                )
            }
        case RestaurantConsentOperation():
            return {
                "identifier": await unit.accept_restaurant_quote(
                    quote_id=data.quote_id, expected_digest=data.digest
                )
            }
        case HoldOperation():
            return await unit.hold(request_id=data.request_id, quote_id=data.quote_id)
        case FinalizeOperation():
            if data.operation == "confirm_assistant":
                return await unit.finalize_assistant(
                    request_id=data.request_id,
                    quote_id=data.quote_id,
                    receipt_id=data.receipt_id,
                )
            return await unit.finalize_human(
                request_id=data.request_id,
                quote_id=data.quote_id,
                receipt_id=data.receipt_id,
            )
        case ArrivalOperation():
            return {
                "identifier": await unit.install(
                    table_ids=data.table_ids,
                    party_size=data.party_size,
                    expected_end=data.expected_end,
                    request_id=data.request_id,
                )
            }
        case PhysicalOperation():
            if data.operation == "departure":
                await unit.record_departure(occupation_id=data.occupation_id)
            elif data.operation == "start_cleaning":
                await unit.start_cleaning(occupation_id=data.occupation_id)
            else:
                await unit.finish_cleaning(occupation_id=data.occupation_id)
        case ExtensionOperation():
            return {
                "conflicts": list(
                    await unit.extend_occupation(
                        occupation_id=data.occupation_id, expected_end=data.expected_end
                    )
                )
            }
        case StateOperation():
            return {
                "conflicts": list(
                    await unit.set_operational_state(
                        table_id=data.table_id, state=data.state
                    )
                )
            }
        case SignalOperation():
            await unit.report_signal(
                request_id=data.request_id, kind=data.kind, reason=data.reason
            )
        case CancelOperation():
            return await unit.cancel_before_arrival(
                request_id=data.request_id, reason=data.reason, origin=data.origin
            )
        case InvoiceOperation():
            return {"identifier": await unit.prepare_invoice(data=data.data)}
        case InvoiceFinalizeOperation():
            return {
                "total": str(
                    await unit.finalize_invoice(
                        invoice_id=data.invoice_id,
                        expected_revision=data.expected_revision,
                    )
                )
            }
        case AllocationOperation():
            return await unit.allocate_advance(
                invoice_id=data.invoice_id, receipt_id=data.receipt_id
            )
        case DeadlineOperation():
            return {"request_ids": list(await unit.process_deadlines())}
        case _:
            raise DiningError(code="dining_unsupported_operation")
    return {"status": "recorded"}
