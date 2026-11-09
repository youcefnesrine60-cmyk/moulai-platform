# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# STAFF-CONTROLLED PUBLIC LINKS AND VISIT INSTALLATION
# Public reads reuse immutable source documents; only a signed human can install a party.
# ==============================================

"""No scan, QR print, customer signal or descriptive function is staff authority."""

from __future__ import annotations

# isort: split
# ==============================================
# SCOPED SOURCE AND HISTORY CONTRACTS
# Link existing entities without copying identities or inventing financial documents.
# ==============================================

import secrets
from uuid import uuid4

from sqlalchemy import select

from app.models.branch import Branch
from app.models.dining import (
    DiningInvoice,
    DiningOccupation,
    DiningQuote,
    DiningReceipt,
    DiningTable,
)
from app.models.dining_service import (
    DiningPresenceSignal,
    DiningPublicLink,
    DiningVisit,
    DiningVisitOrder,
)
from app.models.order import Order
from app.models.restaurant import Restaurant
from app.repositories.subscription_queries import base_select
from app.schemas.dining import JsonObject
from app.schemas.dining_public import (
    PresenceInstallationInput,
    PublicKind,
    PublicLinkInput,
    VisitOrderTransition,
)
from app.services.business.dining.billing import DiningBilling
from app.services.business.dining.occupancy import DiningOccupancy
from app.services.business.dining.values import (
    DiningError,
    content_digest,
)
from app.services.business.dining.views import (
    confirmation_snapshot,
    record_data,
)
from app.services.business.orders.transaction import order_transaction
from app.services.business.orders.update import transition_locked_order

# ==============================================
# EXPLICIT RESOURCE TARGET VOCABULARY
# No generic caller-controlled model, field name or arbitrary document type is accepted.
# ==============================================

TARGET_COLUMNS = {
    "table": "table_id",
    "reservation": "request_id",
    "food_invoice": "invoice_id",
    "receipt": "receipt_id",
}


# ==============================================
# STAFF MANAGEMENT MIXIN
# The existing DiningService owns tenant authorization, branch locking and the commit.
# ==============================================


class DiningPublicManagement(DiningOccupancy, DiningBilling):
    """Compose actual observation, exact billing and retained public-document emission."""

    # ==============================================
    # IMMUTABLE DOCUMENT SOURCE
    # Reuse real finalized records and accepted reservation versions, never UI simulations.
    # ==============================================

    async def _link_source(
        self, *, kind: PublicKind, identifier: int
    ) -> tuple[int, JsonObject]:
        """Freeze one supported source version; tables instead retain an immutable target ID."""
        if kind == "table":
            table = await self.repo.one(
                model=DiningTable, identifier=identifier, lock=True
            )
            return 1, {"table_id": table.id}
        if kind == "reservation":
            request = await self.request(identifier=identifier)
            snapshot = await confirmation_snapshot(
                session=self.session, repo=self.repo, request=request
            )
            snapshot.pop("qr_token", None)
            receipt = await self.session.scalar(
                self.repo.statement(model=DiningReceipt).where(
                    DiningReceipt.request_id == request.id,
                    DiningReceipt.status == "verified",
                )
            )
            if receipt is None:
                raise DiningError(code="dining_confirmation_receipt_inconsistent")
            quote = await self.repo.one(model=DiningQuote, identifier=receipt.quote_id)
            return quote.version, snapshot
        if kind == "food_invoice":
            invoice = await self.repo.one(
                model=DiningInvoice, identifier=identifier, lock=True
            )
            if invoice.status != "finalized":
                raise DiningError(code="dining_issued_invoice_must_be_finalized")
            snapshot = record_data(
                record=invoice, exclude={"provenance", "finalized_by"}
            )
            return invoice.revision, snapshot
        receipt = await self.repo.one(
            model=DiningReceipt, identifier=identifier, lock=True
        )
        if receipt.status != "verified":
            raise DiningError(code="dining_issued_receipt_must_be_verified")
        return 1, record_data(record=receipt, exclude={"validated_by", "review_reason"})

    # ==============================================
    # EMIT, REPRINT, ROTATE OR DISABLE ONE OWNED LINK
    # Policy locking serializes competing requests and SQL also excludes duplicate versions.
    # ==============================================

    async def manage_public_link(self, *, data: PublicLinkInput) -> JsonObject:
        """Keep old prints and snapshots intact; rotation never authorizes a payment."""
        if data.kind == "table":
            await self.guard(capability="configure")
        else:
            await self.guard(capability="documents.issue", human=True)
            await self.guard(capability="finance.read", human=True)
            if data.kind == "reservation":
                await self.guard(capability="service", human=True)
        await self.policy(lock=True)
        column = TARGET_COLUMNS[data.kind]
        links = tuple(
            (
                await self.session.execute(
                    self.repo.statement(model=DiningPublicLink)
                    .where(
                        DiningPublicLink.kind == data.kind,
                        getattr(DiningPublicLink, column) == data.resource_id,
                    )
                    .order_by(DiningPublicLink.id)
                    .with_for_update()
                )
            ).scalars()
        )
        active = next((row for row in reversed(links) if row.active), None)
        if data.operation == "disable":
            if active is None:
                if not links:
                    raise DiningError(code="dining_public_link_unavailable")
                return self._link_result(link=links[-1])
            active.active, active.invalidated_reason = False, data.reason
            await self.session.flush()
            await self.event(
                kind="public_link.disabled",
                details={"link_id": active.id, "reason": data.reason},
            )
            return self._link_result(link=active)
        version, snapshot = await self._link_source(
            kind=data.kind, identifier=data.resource_id
        )
        if data.kind == "table":
            snapshot["public_physical_state"] = data.public_physical_state
        if (
            data.operation == "issue"
            and active is not None
            and active.version == version
        ):
            if (
                data.kind == "table"
                and active.snapshot.get("public_physical_state")
                != data.public_physical_state
            ):
                raise DiningError(code="dining_public_link_rotation_required")
            return self._link_result(link=active)
        for row in links:
            if row.active:
                row.active, row.invalidated_reason = False, (
                    "replaced" if row.version != version else data.reason
                )
        await self.session.flush()
        snapshot["restaurant"] = await self.session.scalar(
            select(Restaurant.name).where(Restaurant.id == self.repo.restaurant_id)
        )
        snapshot["branch"] = await self.session.scalar(
            select(Branch.name).where(
                Branch.id == self.repo.branch_id,
                Branch.restaurant_id == self.repo.restaurant_id,
            )
        )
        row = await self.repo.persist(
            record=DiningPublicLink(
                **self.scope(),
                public_id=secrets.token_urlsafe(32),
                reference="DOC-" + uuid4().hex.upper(),
                kind=data.kind,
                version=version,
                generation=max(
                    (link.generation for link in links if link.version == version),
                    default=0,
                )
                + 1,
                active=True,
                snapshot=snapshot,
                digest=content_digest(value=snapshot),
                invalidated_reason=None,
                **{column: data.resource_id},
            )
        )
        await self.event(
            kind="public_link.issued",
            details={
                "link_id": row.id,
                "kind": row.kind,
                "version": version,
                "generation": row.generation,
            },
        )
        return self._link_result(link=row)

    # ==============================================
    # PUBLIC LINK ADMINISTRATIVE RESULT
    # Return no private snapshot or customer identity through management acknowledgements.
    # ==============================================

    def _link_result(self, *, link: DiningPublicLink) -> JsonObject:
        """Expose the printable read reference, which carries no write authority."""
        return {
            "identifier": link.id,
            "public_id": link.public_id,
            "reference": link.reference,
            "kind": link.kind,
            "version": link.version,
            "generation": link.generation,
            "active": link.active,
        }

    # ==============================================
    # READ AN ALREADY ISSUED PRIVATE PRINT
    # Consultation cannot create or rotate a version; finance read remains independent.
    # ==============================================

    async def issued_print(self, *, link_id: int) -> DiningPublicLink:
        """Authorize the exact scope before returning a retained document snapshot."""
        link = await self.repo.one(model=DiningPublicLink, identifier=link_id)
        if link.kind == "table":
            await self.guard(capability="configure")
        else:
            await self.guard(capability="finance.read", human=True)
            if link.kind == "reservation":
                if self.context.role_code == "owner":
                    await self.guard(capability="configure")
                else:
                    await self.guard(capability="service", human=True)
        return link

    # ==============================================
    # CONFIRM ONE CUSTOMER SIGNAL AFTER REAL OBSERVATION
    # Existing installation rechecks capacity, human proof, conflicts and physical vacancy.
    # ==============================================

    async def install_presence(self, *, data: PresenceInstallationInput) -> int:
        """Convert a signal into a controlled visit atomically with actual occupation."""
        await self.guard(capability="service", human=True)
        await self.policy(lock=True)
        signal = await self.repo.one(
            model=DiningPresenceSignal, identifier=data.presence_id, lock=True
        )
        link = await self.repo.one(
            model=DiningPublicLink, identifier=signal.public_link_id, lock=True
        )
        if not link.active or link.kind != "table" or signal.table_id != link.table_id:
            raise DiningError(code="dining_public_link_unavailable")
        existing = await self.session.scalar(
            self.repo.statement(model=DiningVisit)
            .where(DiningVisit.presence_id == signal.id)
            .with_for_update()
        )
        if existing is not None:
            occupation = await self.repo.one(
                model=DiningOccupation, identifier=existing.occupation_id
            )
            if (
                occupation.expected_end != data.expected_end
                or occupation.request_id != data.request_id
            ):
                raise DiningError(code="dining_presence_installation_conflict")
            return existing.id
        if signal.status != "pending" or signal.expires_at <= self.now():
            raise DiningError(code="dining_presence_signal_expired")
        if not data.observed:
            raise DiningError(code="dining_actual_observation_required")
        occupation_id = await self.install(
            table_ids=(signal.table_id,),
            party_size=signal.party_size,
            expected_end=data.expected_end,
            request_id=data.request_id,
        )
        signal.status = "installed"
        visit = await self.repo.persist(
            record=DiningVisit(
                **self.scope(),
                public_link_id=link.id,
                presence_id=signal.id,
                occupation_id=occupation_id,
                table_id=signal.table_id,
                token_hash=signal.token_hash,
                status="active",
                ended_at=None,
            )
        )
        await self.event(
            kind="visit.installed",
            request_id=data.request_id,
            details={
                "visit_id": visit.id,
                "occupation_id": occupation_id,
                "presence_id": signal.id,
                "availability_confirmation_is_separate": True,
            },
        )
        return visit.id

    # ==============================================
    # ORDER RESPONSIBILITY WITH CURRENT EXPLICIT GRANTS
    # Global B1 fulfillment remains closed; this boundary owns the D1 visit-specific actions.
    # ==============================================

    async def transition_visit_order(self, *, data: VisitOrderTransition) -> None:
        """Lock one owned visit order and record exactly one legal human transition."""
        capability = {
            "approve": "orders.approve",
            "prepare": "orders.prepare",
            "ready": "orders.prepare",
            "served": "orders.complete",
        }[data.action]
        await self.guard(capability=capability, human=True)
        await self.policy(lock=True)
        record = await self.session.scalar(
            self.repo.statement(model=DiningVisitOrder)
            .where(DiningVisitOrder.order_id == data.order_id)
            .with_for_update()
        )
        if record is None:
            raise DiningError(code="dining_visit_order_unavailable")
        visit = await self.repo.one(
            model=DiningVisit, identifier=record.visit_id, lock=True
        )
        occupation = await self.repo.one(
            model=DiningOccupation, identifier=visit.occupation_id, lock=True
        )
        if visit.status != "active" or occupation.status != "occupied":
            raise DiningError(code="dining_visit_closed")
        order = await self.session.scalar(
            base_select(Order)
            .where(
                Order.id == record.order_id,
                Order.restaurant_id == self.repo.restaurant_id,
                Order.branch_id == self.repo.branch_id,
                Order.table_id == visit.table_id,
                Order.order_type == "dine_in",
            )
            .with_for_update()
        )
        if order is None:
            raise DiningError(code="dining_visit_order_unavailable")
        before, after = {
            "approve": ("pending", "confirmed"),
            "prepare": ("confirmed", "preparing"),
            "ready": ("preparing", "ready"),
            "served": ("ready", "completed"),
        }[data.action]
        if order.status == after:
            return
        if order.status != before or not data.observed:
            raise DiningError(code="dining_visit_order_transition_invalid")
        async with order_transaction(self.session):
            await transition_locked_order(
                order=order,
                new_status=after,
                session=self.session,
                employee_id=None,
                note="D1 observed " + data.action,
            )
        await self.event(
            kind="visit.order." + data.action,
            request_id=occupation.request_id,
            details={
                "visit_id": visit.id,
                "order_id": order.id,
                "membership_id": self.context.membership_id,
                "role_capability": capability,
            },
        )
