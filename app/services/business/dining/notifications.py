# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# EXPLICIT DINING OUTBOX DISPATCH
# Deliver only committed jobs through an injected transport with stable keys.
# ==============================================

"""No default transport, worker startup or live channel is installed by imports."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND TRANSPORT EVIDENCE CONTRACT
# Distinguish confirmed delivery from a definite failure and an uncertain result.
# ==============================================

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from app.models.dining import (
    DiningEvent,
    DiningGrant,
    DiningOutbox,
    DiningRequest,
)
from app.repositories.dining_repo import DiningRepository
from app.repositories.tenant_repo import (
    IdentityRepository,
    TenantRepository,
)
from app.schemas.dining import JsonObject
from app.services.business.dining.values import (
    DiningError,
    utc,
    utc_now,
)

# ==============================================
# ACTUAL DELIVERY ACKNOWLEDGEMENT
# An enqueue/HTTP-accepted response is not proof of effective human transmission.
# ==============================================


@dataclass(frozen=True, slots=True, kw_only=True)
class DeliveryAcknowledgement:
    """Transport-confirmed delivery with a trace reference and aware actual time."""

    reference: str
    delivered_at: datetime


# ==============================================
# DININGTRANSPORT
# Explicit integration contract; tests supply a clearly simulated transport.
# ==============================================


class DiningTransport(Protocol):
    """Explicit integration contract; tests supply a clearly simulated transport."""

    # ==============================================
    # DELIVER
    # Use the stable deduplication key and return only proven actual delivery.
    # ==============================================

    async def deliver(
        self, *, key: str, target: str, payload: JsonObject
    ) -> DeliveryAcknowledgement:
        """Use the stable deduplication key and return only proven actual delivery."""
        ...


# ==============================================
# DEFINITELYNOTDELIVERED
# A transport must positively prove non-delivery before automatic retry.
# ==============================================


class DefinitelyNotDelivered(Exception):
    """A transport must positively prove non-delivery before automatic retry."""


# ==============================================
# VERIFY THE CURRENT HUMAN DESTINATION
# Revoked, foreign or assistant collection targets cannot receive service requests.
# ==============================================


async def _recipient_current(
    *,
    session: AsyncSession,
    repo: DiningRepository,
    target: str,
    request_id: int | None,
    required_capability: str = "service",
) -> bool:
    """Recheck active membership, identity, organization and explicit service grant."""
    if target.startswith("customer:"):
        return request_id is not None and target == f"customer:{request_id}"
    if (
        not target.startswith("membership:")
        or not target.removeprefix("membership:").isdigit()
    ):
        return False
    membership_id = int(target.split(":", 1)[1])
    authority = TenantRepository(session=session)
    organization_id = await authority.restaurant_company(
        restaurant_id=repo.restaurant_id
    )
    if organization_id is None:
        return False
    organization = await authority.lock_organization(
        organization_id=organization_id, governance=False
    )
    member = await authority.lock_membership(
        organization_id=organization_id, membership_id=membership_id
    )
    if (
        organization is None
        or organization.status != "active"
        or organization.tenant_enforced_at is None
        or member is None
        or member.status != "active"
        or member.accepted_at is None
        or member.activated_at is None
    ):
        return False
    identity = await IdentityRepository(session=session).lock(
        identity_id=member.identity_id
    )
    if identity is None or identity.status != "active":
        return False
    grants = await authority.grants(
        organization_id=organization_id, membership_id=membership_id
    )
    if member.access_mode == "explicit-grants" and repo.restaurant_id not in grants:
        return False
    grant = (
        await session.execute(
            repo.statement(model=DiningGrant)
            .where(
                DiningGrant.membership_id == membership_id,
                DiningGrant.capability == required_capability,
                DiningGrant.actor_kind == "human",
                DiningGrant.active.is_(True),
            )
            .with_for_update(read=True)
        )
    ).scalar_one_or_none()
    return grant is not None


# ==============================================
# EXPLICIT BOUNDED DISPATCH
# Claim jobs in a separate transaction, then retain ambiguous sends for review.
# ==============================================


async def dispatch_outbox(
    *,
    factory: async_sessionmaker[AsyncSession],
    restaurant_id: int,
    branch_id: int,
    transport: DiningTransport,
    timeout_seconds: int,
    limit: int = 100,
    clock: Callable[[], datetime] = utc_now,
) -> dict[str, int]:
    """Send committed jobs without ever rolling back their originating reservation.

    Definite non-delivery becomes retryable failed. Timeouts/unknown exceptions
    become uncertain; automatic repetition is refused. A crash after transport
    receipt leaves sending for reconciliation instead of risking a double send.
    """
    if (
        type(timeout_seconds) is not int
        or timeout_seconds <= 0
        or type(limit) is not int
        or not 1 <= limit <= 250
    ):
        raise DiningError(code="dining_dispatch_bounds_invalid")
    results = {"delivered": 0, "failed": 0, "uncertain": 0}
    processed: set[int] = set()
    for _ in range(limit):
        cancelled = False
        async with factory() as session, session.begin():
            repo = DiningRepository(
                session=session, restaurant_id=restaurant_id, branch_id=branch_id
            )
            job = (
                await session.execute(
                    repo.statement(model=DiningOutbox)
                    .where(
                        DiningOutbox.status.in_(["pending", "failed"]),
                        DiningOutbox.due_at <= utc(value=clock()),
                        DiningOutbox.id.not_in(processed),
                    )
                    .order_by(DiningOutbox.id)
                    .limit(1)
                    .with_for_update(skip_locked=True)
                )
            ).scalar_one_or_none()
            if job is None:
                break
            job.status, job.attempts = "sending", job.attempts + 1
            identifier = job.id
            processed.add(identifier)
        async with factory() as session, session.begin():
            repo = DiningRepository(
                session=session, restaurant_id=restaurant_id, branch_id=branch_id
            )
            job = await repo.one(model=DiningOutbox, identifier=identifier, lock=True)
            if not await _recipient_current(
                session=session,
                repo=repo,
                target=job.target,
                request_id=job.request_id,
                required_capability=(
                    "reservations.cancel_before_arrival"
                    if job.payload.get("kind") == "cancellation.requested"
                    else "service"
                ),
            ):
                job.status, job.delivery_reference = (
                    "uncertain",
                    "recipient_authority_unavailable",
                )
                results["uncertain"] += 1
                continue
            try:
                acknowledgement = await asyncio.wait_for(
                    transport.deliver(
                        key=f"dining:{job.id}", target=job.target, payload=job.payload
                    ),
                    timeout=timeout_seconds,
                )
                delivered_at = utc(value=acknowledgement.delivered_at)
                if (
                    not acknowledgement.reference
                    or len(acknowledgement.reference) > 200
                    or delivered_at > utc(value=clock())
                ):
                    raise DiningError(code="dining_delivery_evidence_invalid")
            except DefinitelyNotDelivered:
                job.status, job.delivery_reference = (
                    "failed",
                    "definitely_not_delivered",
                )
                results["failed"] += 1
            except asyncio.CancelledError:
                job.status, job.delivery_reference = (
                    "uncertain",
                    "delivery_cancelled_unknown",
                )
                results["uncertain"] += 1
                cancelled = True
            except Exception:  # noqa: BLE001
                # An unknown send outcome must be retained, never auto-retried.
                job.status, job.delivery_reference = "uncertain", "delivery_not_proven"
                results["uncertain"] += 1
            else:
                job.status, job.delivery_reference = (
                    "delivered",
                    acknowledgement.reference,
                )
                if (
                    job.payload.get("kind") == "request.transmit"
                    and job.request_id is not None
                ):
                    request = await repo.one(
                        model=DiningRequest, identifier=job.request_id, lock=True
                    )
                    if request.transmitted_at is None:
                        request.transmitted_at = delivered_at
                await session.flush()
                await repo.persist(
                    record=DiningEvent(
                        restaurant_id=restaurant_id,
                        branch_id=branch_id,
                        request_id=job.request_id,
                        kind="transport.delivered",
                        author={"kind": "transport"},
                        details={
                            "outbox_id": job.id,
                            "delivery_reference": acknowledgement.reference,
                        },
                        occurred_at=delivered_at,
                    )
                )
                results["delivered"] += 1
        if cancelled:
            raise asyncio.CancelledError
    return results
