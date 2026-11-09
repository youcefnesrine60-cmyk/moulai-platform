# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# AUTHENTICATED CUSTOMER PROPOSAL CONSENT
# Bind only the verified customer to an exact immutable current quotation.
# ==============================================

"""Customer consent grants no staff capability, receipt approval or availability."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND CLEAN CUSTOMER TRANSACTION
# Scope both resource keys and identity; return the same denial for foreign data.
# ==============================================

from collections.abc import Callable
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.oidc import OIDCPrincipal
from app.models.dining import (
    DiningAcceptance,
    DiningEvent,
    DiningQuote,
    DiningRequest,
    DiningRequestTable,
)
from app.repositories.dining_repo import DiningRepository
from app.schemas.dining import JsonObject
from app.services.business.dining.values import (
    DiningError,
    Period,
    content_digest,
    utc,
    utc_now,
)

# ==============================================
# ONE CUSTOMER'S EXACT PROPOSAL ACCEPTANCE
# A customer's assertion cannot certify funds or bypass restaurant menu consent.
# ==============================================


async def accept_customer_quote(
    *,
    session: AsyncSession,
    principal: OIDCPrincipal,
    restaurant_id: int,
    branch_id: int,
    quote_id: int,
    expected_digest: str,
    clock: Callable[[], datetime] = utc_now,
) -> int:
    """Commit only the customer's consent after complete content/identity matching."""
    if session.in_transaction() or session.new or session.dirty or session.deleted:
        raise DiningError(code="dining_customer_clean_transaction_required")
    if not isinstance(principal, OIDCPrincipal):
        raise DiningError(code="dining_verified_customer_identity_required")
    now = utc(value=clock())
    repo = DiningRepository(
        session=session, restaurant_id=restaurant_id, branch_id=branch_id
    )
    async with session.begin():
        await repo.policy(lock=True)
        quote = await repo.one(model=DiningQuote, identifier=quote_id)
        request = await repo.one(
            model=DiningRequest, identifier=quote.request_id, lock=True
        )
        if (request.customer_issuer, request.customer_subject) != (
            principal.issuer,
            principal.subject,
        ):
            raise DiningError(code="dining_resource_unavailable")
        latest = (
            await session.execute(
                repo.statement(model=DiningQuote)
                .where(DiningQuote.request_id == request.id)
                .order_by(DiningQuote.version.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if (
            latest is None
            or latest.id != quote_id
            or quote.expires_at <= now
            or quote.digest != expected_digest
            or request.status not in {"pending", "held"}
        ):
            raise DiningError(code="dining_current_exact_proposal_required")
        assigned = tuple(
            (
                await session.execute(
                    repo.statement(model=DiningRequestTable)
                    .where(DiningRequestTable.request_id == request.id)
                    .order_by(DiningRequestTable.table_id)
                )
            ).scalars()
        )
        table_line = next(
            (line for line in quote.components if line.get("kind") == "table"), None
        )
        period = Period(start=request.starts_at, end=request.ends_at)
        if (
            table_line is None
            or table_line.get("table_ids") != [row.table_id for row in assigned]
            or table_line.get("starts_at") != period.start.isoformat()
            or table_line.get("ends_at") != period.end.isoformat()
            or table_line.get("party_size") != request.party_size
            or quote.menu_digest != content_digest(value=request.menu)
        ):
            raise DiningError(code="dining_quote_content_changed_new_consent_required")
        previous = (
            await session.execute(
                repo.statement(model=DiningAcceptance).where(
                    DiningAcceptance.quote_id == quote_id,
                    DiningAcceptance.party == "customer",
                )
            )
        ).scalar_one_or_none()
        if previous is not None:
            return previous.id
        row = await repo.persist(
            record=DiningAcceptance(
                restaurant_id=restaurant_id,
                branch_id=branch_id,
                quote_id=quote_id,
                party="customer",
                digest=quote.digest,
                author={
                    "kind": "customer",
                    "issuer": principal.issuer,
                    "subject": principal.subject,
                },
            )
        )
        await repo.persist(
            record=DiningEvent(
                restaurant_id=restaurant_id,
                branch_id=branch_id,
                request_id=request.id,
                kind="quote.customer_accepted",
                author={
                    "kind": "customer",
                    "issuer": principal.issuer,
                    "subject": principal.subject,
                },
                details={"quote_id": quote_id},
                occurred_at=now,
            )
        )
        return row.id


# ==============================================
# CUSTOMER-OWNED READ AND SIGNAL BOUNDARY
# A valid token never grants staff access or authority to cancel a reservation.
# ==============================================


async def customer_workspace(
    *,
    session: AsyncSession,
    principal: OIDCPrincipal,
    restaurant_id: int,
    branch_id: int,
) -> JsonObject:
    """Read only this exact customer's requests and accepted financial proposals."""
    from app.models.dining import DiningReceipt
    from app.services.business.dining.views import record_data

    if session.in_transaction():
        raise DiningError(code="dining_clean_customer_transaction_required")
    async with session.begin():
        repo = DiningRepository(
            session=session, restaurant_id=restaurant_id, branch_id=branch_id
        )
        requests = tuple(
            (
                await session.execute(
                    repo.statement(model=DiningRequest)
                    .where(
                        DiningRequest.customer_issuer == principal.issuer,
                        DiningRequest.customer_subject == principal.subject,
                    )
                    .order_by(DiningRequest.id)
                    .limit(100)
                )
            ).scalars()
        )
        ids = tuple(row.id for row in requests)
        quotes = tuple(
            (
                await session.execute(
                    repo.statement(model=DiningQuote)
                    .where(DiningQuote.request_id.in_(ids))
                    .order_by(DiningQuote.id)
                )
            ).scalars()
        )
        acceptances = tuple(
            (
                await session.execute(
                    repo.statement(model=DiningAcceptance).where(
                        DiningAcceptance.quote_id.in_(tuple(row.id for row in quotes))
                    )
                )
            ).scalars()
        )
        receipts = tuple(
            (
                await session.execute(
                    repo.statement(model=DiningReceipt).where(
                        DiningReceipt.request_id.in_(ids)
                    )
                )
            ).scalars()
        )
        excluded = {"customer_issuer", "customer_subject", "qr_hash", "qr_token"}
        return {
            "source": "postgres-local",
            "capabilities": ["customer"],
            "requests": [record_data(record=row, exclude=excluded) for row in requests],
            "quotes": [record_data(record=row, exclude=set()) for row in quotes],
            "acceptances": [
                record_data(record=row, exclude=set()) for row in acceptances
            ],
            "receipts": [
                {
                    "id": row.id,
                    "request_id": row.request_id,
                    "received_amount": str(row.received_amount),
                    "currency": row.currency,
                    "status": row.status,
                }
                for row in receipts
            ],
        }


# ==============================================
# CUSTOMER CONFIRMATION
# Permit the owning customer to print, without granting any business mutation.
# ==============================================


async def customer_confirmation(
    *,
    session: AsyncSession,
    principal: OIDCPrincipal,
    restaurant_id: int,
    branch_id: int,
    request_id: int,
) -> JsonObject:
    """Permit the owning customer to print, without granting any business mutation."""
    from app.services.business.dining.views import confirmation_snapshot

    if session.in_transaction():
        raise DiningError(code="dining_clean_customer_transaction_required")
    async with session.begin():
        repo = DiningRepository(
            session=session, restaurant_id=restaurant_id, branch_id=branch_id
        )
        request = await repo.one(model=DiningRequest, identifier=request_id)
        if (request.customer_issuer, request.customer_subject) != (
            principal.issuer,
            principal.subject,
        ):
            raise DiningError(code="dining_resource_unavailable")
        return await confirmation_snapshot(session=session, repo=repo, request=request)


# ==============================================
# CUSTOMER SIGNAL
# Record a cancellation request for a dedicated human; never cancel by customer authority.
# ==============================================


async def customer_signal(
    *,
    session: AsyncSession,
    principal: OIDCPrincipal,
    restaurant_id: int,
    branch_id: int,
    request_id: int,
    reason: str,
    clock: Callable[[], datetime] = utc_now,
) -> JsonObject:
    """Record a cancellation request for a dedicated human; never cancel by customer authority."""
    from app.services.business.dining.cancellation import queue_cancellation_signal

    if session.in_transaction():
        raise DiningError(code="dining_clean_customer_transaction_required")
    async with session.begin():
        repo = DiningRepository(
            session=session, restaurant_id=restaurant_id, branch_id=branch_id
        )
        request = await repo.one(model=DiningRequest, identifier=request_id, lock=True)
        if (request.customer_issuer, request.customer_subject) != (
            principal.issuer,
            principal.subject,
        ):
            raise DiningError(code="dining_resource_unavailable")
        return await queue_cancellation_signal(
            session=session,
            repo=repo,
            request_id=request_id,
            origin="customer",
            reason=reason,
            author={"kind": "customer", "subject": principal.subject},
            at=utc(value=clock()),
        )
