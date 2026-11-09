# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# ATOMIC PRE-ARRIVAL CANCELLATION
# Honor the dedicated owner-assigned grant while preserving all financial facts.
# ==============================================

"""No implied service-role authority, refund, receipt deletion or physical release."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND EXPLICIT LOCAL CONTRACTS
# Reuse typed module dependencies without creating a connection or enabling a transport.
# ==============================================

from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dining import (
    DiningClaim,
    DiningEvent,
    DiningGrant,
    DiningInvoice,
    DiningOccupation,
    DiningOutbox,
    DiningReceipt,
)
from app.repositories.dining_repo import DiningRepository
from app.schemas.dining import JsonObject
from app.services.business.dining.core import DiningCore
from app.services.business.dining.values import DiningError
from migration_support.dining_d1b import (
    CANCEL_CAPABILITY,
    D1B_REVISION,
)
from migration_support.dining_d1c import D1C_REVISION
from migration_support.operational_revisions import DINING_SERVICE_REVISIONS

# ==============================================
# DININGCANCELLATION
# Cancel only unarrived/unbilled requests under the common branch lock.
# ==============================================


class DiningCancellation(DiningCore):
    """Cancel only unarrived/unbilled requests under the common branch lock."""

    # ==============================================
    # CANCEL BEFORE ARRIVAL
    # Serialize cancellation with arrival/invoicing and return repeated success once.
    # ==============================================

    async def cancel_before_arrival(
        self, *, request_id: int, reason: str, origin: str
    ) -> dict[str, str | int]:
        """Serialize cancellation with arrival/invoicing and return repeated success once."""
        await self.guard(capability=CANCEL_CAPABILITY, human=True)
        await self.policy()
        if await self.session.scalar(
            text("SELECT version_num FROM alembic_version")
        ) not in {D1B_REVISION, D1C_REVISION, *DINING_SERVICE_REVISIONS}:
            raise DiningError(code="dining_cancellation_upgrade_required")
        if (
            not reason.strip()
            or len(reason) > 1000
            or origin not in {"human", "customer", "assistant"}
        ):
            raise DiningError(code="dining_cancellation_reason_required")
        request = await self.request(identifier=request_id)
        if request.status == "cancelled":
            return {"request_id": request.id, "status": "cancelled"}
        occupied = (
            await self.session.execute(
                self.repo.statement(model=DiningOccupation)
                .where(DiningOccupation.request_id == request_id)
                .limit(1)
            )
        ).scalar_one_or_none()
        invoice = (
            await self.session.execute(
                self.repo.statement(model=DiningInvoice)
                .where(DiningInvoice.request_id == request_id)
                .limit(1)
            )
        ).scalar_one_or_none()
        if (
            occupied is not None
            or invoice is not None
            or request.status in {"arrived", "served"}
        ):
            raise DiningError(
                code="dining_cancellation_after_arrival_or_invoice_requires_policy"
            )
        if request.status not in {"pending", "held", "confirmed", "manual_review"}:
            raise DiningError(code="dining_cancellation_state_invalid")
        claims = tuple(
            (
                await self.session.execute(
                    self.repo.statement(model=DiningClaim)
                    .where(
                        DiningClaim.request_id == request_id,
                        DiningClaim.active.is_(True),
                    )
                    .with_for_update()
                )
            ).scalars()
        )
        for claim in claims:
            claim.active = False
        for table in await self.tables(
            identifiers=await self.selected(request_id=request_id)
        ):
            table.revision += 1
        request.status = "cancelled"
        jobs = tuple(
            (
                await self.session.execute(
                    self.repo.statement(model=DiningOutbox)
                    .where(
                        DiningOutbox.request_id == request_id,
                        DiningOutbox.status.in_(("pending", "failed")),
                    )
                    .with_for_update()
                )
            ).scalars()
        )
        for job in jobs:
            job.status = "cancelled"
            job.delivery_reference = "obsolete_after_authorized_cancellation"
        receipts = tuple(
            (
                await self.session.execute(
                    self.repo.statement(model=DiningReceipt).where(
                        DiningReceipt.request_id == request_id
                    )
                )
            ).scalars()
        )
        await self.session.flush()
        await self.event(
            kind="reservation.cancelled",
            request_id=request_id,
            details={
                "reason": reason.strip(),
                "origin": origin,
                "received_funds_retained": bool(receipts),
                "receipt_ids": [row.id for row in receipts],
                "financial_treatment": "requires_separate_authority_and_policy",
                "physical_state_unchanged": True,
            },
        )
        if receipts:
            await self.alert(
                request_id=request_id,
                event_key="cancellation.funds_review",
                details={"refund_performed": False, "funds_reusable": False},
            )
        return {"request_id": request.id, "status": "cancelled"}


# ==============================================
# NON-AUTHORITATIVE CANCELLATION REQUEST FORWARDING
# Only explicit active human cancellation grants supply eligible destinations.
# ==============================================


async def queue_cancellation_signal(
    *,
    session: AsyncSession,
    repo: DiningRepository,
    request_id: int,
    origin: str,
    reason: str,
    author: JsonObject,
    at: datetime,
) -> JsonObject:
    """Preserve a signal and queue it for empowered people, without executing cancellation."""
    if not reason.strip() or len(reason) > 1000:
        raise DiningError(code="dining_cancellation_reason_required")
    event = await repo.persist(
        record=DiningEvent(
            restaurant_id=repo.restaurant_id,
            branch_id=repo.branch_id,
            request_id=request_id,
            kind="cancellation.requested",
            author=author,
            details={"origin": origin, "reason": reason.strip(), "not_cancelled": True},
            occurred_at=at,
        )
    )
    grants = tuple(
        (
            await session.execute(
                repo.statement(model=DiningGrant).where(
                    DiningGrant.capability == CANCEL_CAPABILITY,
                    DiningGrant.actor_kind == "human",
                    DiningGrant.active.is_(True),
                )
            )
        ).scalars()
    )
    from app.services.business.dining.notifications import _recipient_current

    eligible = 0
    for grant in grants:
        if not await _recipient_current(
            session=session,
            repo=repo,
            target=f"membership:{grant.membership_id}",
            request_id=request_id,
            required_capability=CANCEL_CAPABILITY,
        ):
            continue
        eligible += 1
        await repo.persist(
            record=DiningOutbox(
                restaurant_id=repo.restaurant_id,
                branch_id=repo.branch_id,
                request_id=request_id,
                event_key=f"cancellation.request:{event.id}",
                target=f"membership:{grant.membership_id}",
                payload={
                    "kind": "cancellation.requested",
                    "request_id": request_id,
                    "origin": origin,
                    "requires_dedicated_human": True,
                },
                due_at=at,
                status="pending",
                attempts=0,
            )
        )
    return {
        "status": "requested",
        "forwarded_to_habilitated": eligible,
        "cancelled": False,
    }
