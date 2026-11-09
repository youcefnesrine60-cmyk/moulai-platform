# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# SCOPED PLANNING READ PROJECTIONS
# Keep physical facts, confirmed planning, holds and closed periods distinct.
# ==============================================

"""Bounded staff projections; no write or customer contact is exposed by planning."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND CURRENT-DAY COVERAGE
# Closed time is excluded before deciding whether opening time is fully reserved.
# ==============================================

from datetime import (
    date,
    datetime,
    time,
)
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.branch import Branch
from app.models.dining import (
    DiningAcceptance,
    DiningAllocation,
    DiningBase,
    DiningBlackout,
    DiningCalendar,
    DiningClaim,
    DiningCombination,
    DiningConfirmation,
    DiningEvent,
    DiningGrant,
    DiningInvoice,
    DiningInvoiceOrder,
    DiningMember,
    DiningOccupation,
    DiningOccupationTable,
    DiningOutbox,
    DiningPolicy,
    DiningQuote,
    DiningReceipt,
    DiningReference,
    DiningRequest,
    DiningRequestTable,
    DiningTable,
    DiningTariff,
    DiningTrait,
)
from app.models.dining_service import (
    DiningPresenceSignal,
    DiningPublicLink,
    DiningStaffAssignment,
    DiningStaffFunction,
    DiningStaffProfile,
    DiningVisit,
    DiningVisitOrder,
)
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.restaurant import Restaurant
from app.models.tenant.schema import OrganizationMembership
from app.repositories.dining_repo import DiningRepository
from app.schemas.dining import (
    JsonObject,
    OpeningWindow,
)
from app.services.business.dining.calendar import opening_periods
from app.services.business.dining.core import DiningCore
from app.services.business.dining.event_history import HISTORY_CAPABILITIES
from app.services.business.dining.values import (
    DiningError,
    Period,
)

# ==============================================
# DININGVIEWS
# Present current physical facts alongside independent future claims.
# ==============================================


class DiningViews(DiningCore):
    """Present current physical facts alongside independent future claims."""

    # ==============================================
    # PLANNING
    # Return bounded scoped tables, opening intervals and overlapping claims.
    # ==============================================

    async def planning(self, *, period: Period) -> tuple[JsonObject, ...]:
        """Return bounded scoped tables, opening intervals and overlapping claims.

        Fully reserved means all open time in the selected interval is covered
        by confirmed reservation claims, never by holds or closed hours.
        Expired holds are omitted without modifying persisted history.
        """
        await self.guard(capability="read")
        policy = await self.policy(lock=False)
        entries = tuple(
            (
                await self.session.execute(self.repo.statement(model=DiningCalendar))
            ).scalars()
        )
        weekly = {
            row.weekday: tuple(
                OpeningWindow.model_validate(item) for item in row.windows
            )
            for row in entries
            if row.weekday is not None
        }
        dated: dict[date, tuple[OpeningWindow, ...]] = {
            row.service_date: tuple(
                OpeningWindow.model_validate(item) for item in row.windows
            )
            for row in entries
            if row.service_date is not None
        }
        opened = opening_periods(
            period=period, timezone_name=policy.timezone, weekly=weekly, dated=dated
        )
        tables = tuple(
            (
                await self.session.execute(
                    self.repo.statement(model=DiningTable)
                    .order_by(DiningTable.id)
                    .limit(250)
                )
            ).scalars()
        )
        claims = tuple(
            (
                await self.session.execute(
                    self.repo.statement(model=DiningClaim)
                    .where(
                        DiningClaim.active.is_(True),
                        DiningClaim.starts_at < period.end,
                        DiningClaim.ends_at > period.start,
                    )
                    .order_by(DiningClaim.starts_at)
                )
            ).scalars()
        )
        occupations = tuple(
            (
                await self.session.execute(
                    self.repo.statement(model=DiningOccupationTable).where(
                        DiningOccupationTable.active.is_(True)
                    )
                )
            ).scalars()
        )
        result: list[JsonObject] = []
        for table in tables:
            active = [
                claim
                for claim in claims
                if claim.table_id == table.id
                and (
                    claim.kind != "hold"
                    or (claim.expires_at is not None and claim.expires_at > self.now())
                )
            ]
            confirmed = [
                Period(start=claim.starts_at, end=claim.ends_at)
                for claim in active
                if claim.kind == "reservation"
            ]
            fully_reserved = bool(opened) and all(
                _covered(period=window, reservations=confirmed) for window in opened
            )
            actual: JsonObject | None = None
            assignment = next(
                (row for row in occupations if row.table_id == table.id), None
            )
            if assignment is not None:
                occupation = await self.repo.one(
                    model=DiningOccupation, identifier=assignment.occupation_id
                )
                actual = {
                    "id": occupation.id,
                    "arrived_at": occupation.arrived_at.isoformat(),
                    "expected_end": occupation.expected_end.isoformat(),
                    "departed_at": (
                        occupation.departed_at.isoformat()
                        if occupation.departed_at
                        else None
                    ),
                    "cleaning_expected_end": occupation.cleaning_expected_end.isoformat(),
                }
            result.append(
                {
                    "id": table.id,
                    "code": table.code,
                    "physical_state": table.physical_state,
                    "in_service": table.in_service,
                    "capacity_min": table.min_capacity,
                    "capacity_max": table.max_capacity,
                    "fully_reserved": fully_reserved,
                    "closed": not opened,
                    "occupation": actual,
                    "opening": [
                        {
                            "start": window.start.isoformat(),
                            "end": window.end.isoformat(),
                        }
                        for window in opened
                    ],
                    "claims": [
                        {
                            "kind": claim.kind,
                            "start": claim.starts_at.isoformat(),
                            "end": claim.ends_at.isoformat(),
                            "request_id": claim.request_id,
                        }
                        for claim in active
                    ],
                }
            )
        return tuple(result)

    # ==============================================
    # CONFIRMATION DOCUMENT
    # Return the printable frozen confirmation only to owner/service authority.
    # ==============================================

    async def confirmation_document(self, *, request_id: int) -> JsonObject:
        """Return the printable frozen confirmation only to owner/service authority.

        Public QR verification uses a separate redacted projection. Cleaners and
        assistant read tools never obtain this personal confirmation document.
        """
        if self.context.role_code == "owner":
            await self.guard(capability="configure")
        else:
            await self.guard(capability="service", human=True)
        await self.guard(capability="finance.read", human=True)
        request = await self.request(identifier=request_id)
        return await confirmation_snapshot(
            session=self.session, repo=self.repo, request=request
        )

    # ==============================================
    # WORKSPACE
    # Return actual scoped rows; cleaners receive neither customer nor financial data.
    # ==============================================

    async def workspace(self) -> JsonObject:
        """Return actual scoped rows; cleaners receive neither customer nor financial data."""
        await self.guard(capability="read")
        grants = tuple(
            (
                await self.session.execute(
                    self.repo.statement(model=DiningGrant).where(
                        DiningGrant.membership_id == self.context.membership_id,
                        DiningGrant.active.is_(True),
                    )
                )
            ).scalars()
        )
        capabilities = {row.capability for row in grants}
        capabilities.add("read")
        if self.context.role_code == "owner":
            capabilities.add("configure")
        policy = (
            await self.session.execute(self.repo.statement(model=DiningPolicy))
        ).scalar_one_or_none()
        result: JsonObject = {
            "source": "postgres-local",
            "restaurant_id": self.repo.restaurant_id,
            "branch_id": self.repo.branch_id,
            "capabilities": sorted(capabilities),
            "server_time": self.now().isoformat(),
            "policy": (
                {"timezone": policy.timezone, **policy.settings} if policy else None
            ),
        }
        models: dict[str, type[DiningBase]] = {
            "references": DiningReference,
            "tables": DiningTable,
            "traits": DiningTrait,
            "combinations": DiningCombination,
            "members": DiningMember,
            "calendar": DiningCalendar,
            "blackouts": DiningBlackout,
            "occupations": DiningOccupation,
            "occupation_tables": DiningOccupationTable,
            "claims": DiningClaim,
        }
        can_service = bool(capabilities & HISTORY_CAPABILITIES)
        can_finance = "finance.read" in capabilities
        if can_service:
            models.update(
                {
                    "requests": DiningRequest,
                    "request_tables": DiningRequestTable,
                    "confirmations": DiningConfirmation,
                    "quotes": DiningQuote,
                    "acceptances": DiningAcceptance,
                }
            )
        if can_finance:
            models.update(
                {
                    "receipts": DiningReceipt,
                    "invoices": DiningInvoice,
                    "invoice_orders": DiningInvoiceOrder,
                    "allocations": DiningAllocation,
                }
            )
        if "configure" in capabilities:
            models.update({"tariffs": DiningTariff, "grants": DiningGrant})
            models.update(
                {
                    "staff_profiles": DiningStaffProfile,
                    "staff_functions": DiningStaffFunction,
                    "staff_assignments": DiningStaffAssignment,
                }
            )
        if can_service:
            models.update({"events": DiningEvent, "outbox": DiningOutbox})
        if capabilities & {"service", "configure"}:
            models.update(
                {"presence_signals": DiningPresenceSignal, "visits": DiningVisit}
            )
        if capabilities & {
            "orders.read",
            "orders.approve",
            "orders.prepare",
            "orders.complete",
            "finance.read",
        }:
            models.update({"visit_orders": DiningVisitOrder})
        if capabilities & {"configure", "documents.issue", "finance.read"}:
            models.update({"public_links": DiningPublicLink})
        for name, model in models.items():
            rows = tuple(
                (
                    await self.session.execute(
                        self.repo.statement(model=model)
                        .order_by(model.id.desc())
                        .limit(100)
                    )
                ).scalars()
            )
            excluded = {
                "customer_issuer",
                "customer_subject",
                "qr_token",
                "qr_hash",
                "token_hash",
                "snapshot",
            }
            if not capabilities & {"service", "assistant", "configure"}:
                excluded.update({"customer_name", "contact"})
            result[name] = [
                record_data(record=row, exclude=excluded) for row in reversed(rows)
            ]
        if "configure" in capabilities:
            membership_rows = (
                await self.session.execute(
                    select(
                        OrganizationMembership.id,
                        OrganizationMembership.role_code,
                        OrganizationMembership.status,
                        OrganizationMembership.revision,
                        OrganizationMembership.enrollment_generation,
                    )
                    .where(
                        OrganizationMembership.organization_id
                        == self.context.organization_id
                    )
                    .order_by(OrganizationMembership.id)
                )
            ).all()
            result["memberships"] = [
                {
                    "id": row.id,
                    "role": row.role_code,
                    "status": row.status,
                    "revision": row.revision,
                    "enrollment_generation": row.enrollment_generation,
                }
                for row in membership_rows
            ]
        if can_service:
            products = tuple(
                (
                    await self.session.execute(
                        select(Product)
                        .where(Product.restaurant_id == self.repo.restaurant_id)
                        .order_by(Product.id)
                        .limit(100)
                    )
                ).scalars()
            )
            result["products"] = [
                {
                    "id": row.id,
                    "name": row.name,
                    "is_available": row.is_available,
                    "legacy_price": str(row.price),
                }
                for row in products
            ]
        if capabilities & {
            "finance.read",
            "orders.read",
            "orders.approve",
            "orders.prepare",
            "orders.complete",
        }:
            orders = tuple(
                (
                    await self.session.execute(
                        select(Order)
                        .where(
                            Order.restaurant_id == self.repo.restaurant_id,
                            Order.branch_id == self.repo.branch_id,
                        )
                        .order_by(Order.id)
                        .limit(100)
                    )
                ).scalars()
            )
            items = tuple(
                (
                    await self.session.execute(
                        select(OrderItem)
                        .where(OrderItem.order_id.in_(tuple(row.id for row in orders)))
                        .order_by(OrderItem.id)
                    )
                ).scalars()
            )
            result["food_orders"] = [
                {
                    "id": row.id,
                    "table_id": row.table_id,
                    "status": row.status,
                    "legacy_total": str(row.total_amount),
                    "items": [
                        {
                            "id": line.id,
                            "description": line.product_name,
                            "quantity": line.quantity,
                            "legacy_unit_price": str(line.unit_price),
                        }
                        for line in items
                        if line.order_id == row.id
                    ],
                }
                for row in orders
            ]
        # Operational inboxes are persisted local events, not sent notifications.
        # Kitchen/cleaning projections omit customer text, amounts and bearer hashes.
        event_prefixes: set[str] = set()
        if capabilities & {"service", "orders.approve", "orders.complete"}:
            event_prefixes.update({"presence.", "visit.", "occupation."})
        if "orders.prepare" in capabilities:
            event_prefixes.add("visit.order.")
        if "clean" in capabilities:
            event_prefixes.update({"occupation.departure", "cleaning."})
        if can_finance:
            event_prefixes.update({"invoice.", "advance.", "receipt."})
        if "configure" in capabilities:
            event_prefixes.update(
                {
                    "presence.",
                    "visit.",
                    "occupation.",
                    "cleaning.",
                    "invoice.",
                    "advance.",
                    "receipt.",
                }
            )
        events = tuple(
            (
                await self.session.execute(
                    self.repo.statement(model=DiningEvent)
                    .order_by(DiningEvent.id.desc())
                    .limit(250)
                )
            ).scalars()
        )
        public_detail_keys = {
            "table_id",
            "presence_id",
            "visit_id",
            "occupation_id",
            "order_id",
            "invoice_id",
            "receipt_id",
        }
        result["service_events"] = [
            {
                "id": row.id,
                "kind": row.kind,
                "occurred_at": row.occurred_at.isoformat(),
                "details": {
                    key: value
                    for key, value in row.details.items()
                    if key in public_detail_keys
                },
            }
            for row in events
            if any(row.kind.startswith(prefix) for prefix in event_prefixes)
        ][:100]
        result["event_transport"] = "local-persisted-no-delivery"
        if policy is not None and not can_finance:
            result["policy"] = {
                "timezone": policy.timezone,
                **policy.settings,
                "payment_instructions": {},
            }
            result["redacted_fields"] = ["policy.payment_instructions"]
        return result


# ==============================================
# COVERED
# Merge confirmed coverage across adjacent claims without filling real gaps.
# ==============================================


def _covered(*, period: Period, reservations: list[Period]) -> bool:
    """Merge confirmed coverage across adjacent claims without filling real gaps."""
    cursor = period.start
    for reservation in sorted(reservations, key=lambda row: row.start):
        if reservation.end <= cursor:
            continue
        if reservation.start > cursor:
            return False
        cursor = max(cursor, reservation.end)
        if cursor >= period.end:
            return True
    return False


# ==============================================
# EXACT JSON SERIALIZATION OF PERSISTED RECORDS
# Decimal money remains text, while dates and instants keep their ISO provenance.
# ==============================================


def record_data(*, record: DiningBase, exclude: set[str]) -> JsonObject:
    """Project explicit model columns only, with no lazy relationships or secrets."""
    result: JsonObject = {}
    for column in record.__table__.columns:
        if column.name in exclude:
            continue
        value = getattr(record, column.name)
        if isinstance(value, Decimal):
            # Fixed notation preserves exact values, including Numeric zero (0E-8).
            result[column.name] = format(value, "f")
        elif isinstance(value, (datetime, date, time)):
            result[column.name] = value.isoformat()
        else:
            result[column.name] = value
    return result


# ==============================================
# COMMON AUTHORIZED CONFIRMATION PROJECTION
# Staff and the verified owning customer share one immutable quote/receipt reader.
# ==============================================


async def confirmation_snapshot(
    *, session: AsyncSession, repo: DiningRepository, request: DiningRequest
) -> JsonObject:
    """Build a read document only after the caller has proven staff/customer authority."""
    if request.status not in {"confirmed", "arrived", "served"} or not request.qr_token:
        raise DiningError(code="dining_confirmed_ticket_required")
    receipts = tuple(
        (
            await session.execute(
                repo.statement(model=DiningReceipt).where(
                    DiningReceipt.request_id == request.id,
                    DiningReceipt.status == "verified",
                )
            )
        ).scalars()
    )
    if len(receipts) != 1:
        raise DiningError(code="dining_confirmation_receipt_inconsistent")
    receipt = receipts[0]
    quote = await repo.one(model=DiningQuote, identifier=receipt.quote_id)
    links = tuple(
        (
            await session.execute(
                repo.statement(model=DiningRequestTable).where(
                    DiningRequestTable.request_id == request.id
                )
            )
        ).scalars()
    )
    tables = tuple(
        (
            await session.execute(
                repo.statement(model=DiningTable)
                .where(DiningTable.id.in_(tuple(link.table_id for link in links)))
                .order_by(DiningTable.id)
            )
        ).scalars()
    )
    restaurant_name = await session.scalar(
        select(Restaurant.name).where(Restaurant.id == repo.restaurant_id)
    )
    branch_name = await session.scalar(
        select(Branch.name).where(
            Branch.id == repo.branch_id, Branch.restaurant_id == repo.restaurant_id
        )
    )
    return {
        "reference": request.reference,
        "status": request.status,
        "restaurant": restaurant_name,
        "branch": branch_name,
        "tables": [row.code for row in tables],
        "customer": request.customer_name,
        "party_size": request.party_size,
        "starts_at": request.starts_at.isoformat(),
        "ends_at": request.ends_at.isoformat(),
        "duration_seconds": int((request.ends_at - request.starts_at).total_seconds()),
        "event_id": request.event_id,
        "menu": quote.components,
        "advance": str(receipt.received_amount),
        "currency": receipt.currency,
        "terms": quote.terms,
        "qr_token": request.qr_token,
    }
