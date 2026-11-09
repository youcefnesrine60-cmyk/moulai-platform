# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# EXCLUSIVE HOLDS AND ATOMIC BOOKING CONFIRMATION
# Require exact consent, independent received funds and valid human authority.
# ==============================================

"""No silence-as-consent, receipt fabrication or automatic late-payment revival."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND SEPARATE HUMAN/ASSISTANT ENTRY POINTS
# Row locks and exclusion constraints protect the same resource across requests.
# ==============================================

import hashlib
import secrets
from datetime import timedelta
from typing import Literal

from app.models.dining import (
    DiningClaim,
    DiningReceipt,
)
from app.services.business.dining.pricing import DiningPricing
from app.services.business.dining.requests import DiningRequests
from app.services.business.dining.values import (
    DiningError,
    Period,
)

# ==============================================
# CLAIM LIFECYCLE AND DEFINITIVE CONFIRMATION
# The transaction owner commits the complete reservation and outbox together.
# ==============================================


class DiningReservations(DiningRequests, DiningPricing):
    """Prepare exclusive time claims, then finalize only if every condition holds."""

    async def hold(self, *, request_id: int, quote_id: int) -> dict[str, str | int]:
        """Recheck the full period before exposing explicit payment instructions."""
        actor = await self._operator()
        policy = await self.policy()
        await self.expire_holds()
        request = await self.request(identifier=request_id)
        if request.status not in {"pending", "held"}:
            raise DiningError(code="dining_hold_request_state_invalid")
        quote = await self.quote(
            identifier=quote_id, request=request, require_acceptance=True
        )
        identifiers = await self.selected(request_id=request_id)
        period = Period(start=request.starts_at, end=request.ends_at)
        await self.availability(
            identifiers=identifiers,
            period=period,
            party_size=request.party_size,
            ignore_request=request_id,
        )
        existing = (
            (
                await self.session.execute(
                    self.repo.statement(model=DiningClaim)
                    .where(
                        DiningClaim.request_id == request_id,
                        DiningClaim.active.is_(True),
                        DiningClaim.kind == "hold",
                    )
                    .with_for_update()
                )
            )
            .scalars()
            .all()
        )
        if existing:
            if {row.table_id for row in existing} != set(identifiers) or any(
                row.expires_at is None or row.expires_at <= self.now()
                for row in existing
            ):
                raise DiningError(code="dining_hold_inconsistent")
            expires = min(
                row.expires_at for row in existing if row.expires_at is not None
            )
        else:
            await self.assert_unpaid(request_id=request_id)
            expires = min(
                self.now() + timedelta(seconds=policy.hold_seconds),
                quote.expires_at,
                period.start,
            )
            if expires <= self.now():
                raise DiningError(code="dining_hold_deadline_invalid")
            expanded = await self.expanded(period=period)
            for identifier in identifiers:
                await self.repo.persist(
                    record=DiningClaim(
                        **self.scope(),
                        request_id=request_id,
                        table_id=identifier,
                        starts_at=expanded.start,
                        ends_at=expanded.end,
                        kind="hold",
                        expires_at=expires,
                        active=True,
                    )
                )
            request.status = "held"
            await self.session.flush()
            await self.event(
                kind="hold.created",
                request_id=request_id,
                details={"quote_id": quote_id, "expires_at": expires.isoformat()},
                author_kind=actor,
            )
        # The caller obtains instructions only after an exclusive hold exists.
        return {
            "request_id": request_id,
            "quote_id": quote_id,
            "amount": str(quote.amount),
            "currency": quote.currency,
            "expires_at": expires.isoformat(),
            **{
                f"instruction_{mode}": value
                for mode, value in policy.payment_instructions.items()
            },
        }

    # ==============================================
    # FINALIZE HUMAN
    # Human service entry point; explicit current authority remains mandatory.
    # ==============================================

    async def finalize_human(
        self, *, request_id: int, quote_id: int, receipt_id: int
    ) -> dict[str, str | int]:
        """Human service entry point; explicit current authority remains mandatory."""
        await self.guard(capability="service", human=True)
        return await self._finalize(
            request_id=request_id,
            quote_id=quote_id,
            receipt_id=receipt_id,
            mode="human",
        )

    # ==============================================
    # FINALIZE ASSISTANT
    # Always enforce the autonomy exception, even if an identity has other grants.
    # ==============================================

    async def finalize_assistant(
        self, *, request_id: int, quote_id: int, receipt_id: int
    ) -> dict[str, str | int]:
        """Always enforce the autonomy exception, even if an identity has other grants."""
        await self.guard(capability="assistant")
        return await self._finalize(
            request_id=request_id,
            quote_id=quote_id,
            receipt_id=receipt_id,
            mode="assistant",
        )

    # ==============================================
    # FINALIZE
    # Transform all holds atomically; failed confirmation never deletes receipts.
    # ==============================================

    async def _finalize(
        self,
        *,
        request_id: int,
        quote_id: int,
        receipt_id: int,
        mode: Literal["human", "assistant"],
    ) -> dict[str, str | int]:
        """Transform all holds atomically; failed confirmation never deletes receipts."""
        policy = await self.policy()
        await self.expire_holds()
        request = await self.request(identifier=request_id)
        receipt = await self.repo.one(
            model=DiningReceipt, identifier=receipt_id, lock=True
        )
        if (
            receipt.request_id != request_id
            or receipt.quote_id != quote_id
            or receipt.status != "verified"
        ):
            raise DiningError(code="dining_verified_matching_receipt_required")
        if request.status in {"confirmed", "arrived", "served"}:
            if not request.qr_token:
                raise DiningError(code="dining_confirmation_ticket_missing")
            return {
                "request_id": request.id,
                "reference": request.reference,
                "status": request.status,
                "qr_token": request.qr_token,
            }
        if request.status != "held":
            raise DiningError(code="dining_active_hold_required")
        quote = await self.quote(
            identifier=quote_id, request=request, require_acceptance=True
        )
        if quote.amount <= 0:
            raise DiningError(code="dining_zero_advance_requires_explicit_policy")
        if (
            receipt.currency != quote.currency
            or receipt.received_amount != quote.amount
            or receipt.expected_amount != quote.amount
        ):
            raise DiningError(code="dining_receipt_amount_or_currency_mismatch")
        identifiers = await self.selected(request_id=request_id)
        tables = await self.availability(
            identifiers=identifiers,
            period=Period(start=request.starts_at, end=request.ends_at),
            party_size=request.party_size,
            ignore_request=request_id,
        )
        confirmation = await self.human_confirmation(request=request, tables=tables)
        if mode == "assistant":
            if request.transmitted_at is None:
                raise DiningError(code="dining_effective_transmission_required")
            if self.now() < request.transmitted_at + timedelta(
                seconds=policy.response_seconds
            ):
                raise DiningError(code="dining_human_response_deadline_not_elapsed")
        claims = (
            (
                await self.session.execute(
                    self.repo.statement(model=DiningClaim)
                    .where(
                        DiningClaim.request_id == request_id,
                        DiningClaim.active.is_(True),
                    )
                    .order_by(DiningClaim.id)
                    .with_for_update()
                )
            )
            .scalars()
            .all()
        )
        if (
            {claim.table_id for claim in claims} != set(identifiers)
            or len(claims) != len(identifiers)
            or any(
                claim.kind != "hold"
                or claim.expires_at is None
                or claim.expires_at <= self.now()
                for claim in claims
            )
        ):
            raise DiningError(code="dining_current_exclusive_hold_required")
        for claim in claims:
            claim.kind, claim.expires_at = "reservation", None
        for table in tables:
            table.revision += 1
        token = secrets.token_urlsafe(32)
        request.status, request.confirmed_at = "confirmed", self.now()
        request.qr_token = token
        request.qr_hash = hashlib.sha256(token.encode("ascii")).hexdigest()
        await self.session.flush()
        await self.event(
            kind="reservation.confirmed",
            request_id=request_id,
            details={
                "quote_id": quote_id,
                "receipt_id": receipt_id,
                "human_confirmation_id": confirmation.id,
                "mode": mode,
            },
            author_kind=mode,
        )
        await self.queue(
            request_id=request_id,
            event_key=f"reservation.confirmed:{request_id}",
            target=f"customer:{request_id}",
            payload={"kind": "reservation.confirmed", "request_id": request_id},
            due_at=self.now(),
        )
        return {
            "request_id": request.id,
            "reference": request.reference,
            "status": request.status,
            "qr_token": token,
        }

    # ==============================================
    # PROCESS DEADLINES
    # Queue configured timeout/arrival alerts without freeing or cancelling tables.
    # ==============================================

    async def process_deadlines(self) -> tuple[int, ...]:
        """Queue configured timeout/arrival alerts without freeing or cancelling tables."""
        await self._operator()
        policy = await self.policy()
        await self.expire_holds()
        from app.models.dining import DiningRequest

        requests = (
            (
                await self.session.execute(
                    self.repo.statement(model=DiningRequest)
                    .where(DiningRequest.status.in_(["pending", "held", "confirmed"]))
                    .order_by(DiningRequest.id)
                    .limit(250)
                )
            )
            .scalars()
            .all()
        )
        alerted: list[int] = []
        for request in requests:
            if (
                request.status in {"pending", "held"}
                and request.transmitted_at is not None
            ):
                deadline = request.transmitted_at + timedelta(
                    seconds=policy.response_seconds
                )
                for offset in policy.alert_offsets_seconds:
                    if self.now() >= deadline + timedelta(seconds=offset):
                        await self.alert(
                            request_id=request.id,
                            event_key=f"human_response.timeout:{offset}",
                            details={"request_stays_pending": True},
                        )
                        alerted.append(request.id)
            if (
                request.status == "confirmed"
                and self.now()
                >= request.starts_at + timedelta(seconds=policy.lateness_seconds)
            ):
                await self.alert(
                    request_id=request.id,
                    event_key="arrival.late",
                    details={"not_cancelled": True},
                )
                alerted.append(request.id)
        await self.scan_occupancy_delays()
        return tuple(sorted(set(alerted)))
