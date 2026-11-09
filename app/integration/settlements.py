# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# CONTROLLED FINAL FOOD RECEIPTS
# Explain the actual invoice balance and record a human-verified full settlement exactly once.
# ==============================================

"""No partial settlement, conversion, refund, gateway or implicit collection permission."""

from __future__ import annotations

# isort: split
# ==============================================
# SCOPED EXACT CONTRACTS
# Reuse existing tenant authority, human collection and frozen invoices instead of creating a second invoice.
# ==============================================

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dining import (
    DiningAllocation,
    DiningInvoice,
)
from app.models.dining_service import DiningVisit
from app.models.dining_settlement import DiningSettlement
from app.repositories.subscription_queries import base_select
from app.schemas.dining import (
    DiningInput,
    ExactDecimal,
    JsonObject,
)
from app.services.business.dining.public_service import (
    PublicDiningService,
    visit_hash,
)
from app.services.business.dining.service import DiningUnit
from app.services.business.dining.values import (
    DiningError,
    utc,
)
from app.services.business.tenant_foundation import tenant_unit_of_work

# ==============================================
# VERIFIED HUMAN INPUT
# The client supplies receipt facts, never author identity, invoice total or an approval role.
# ==============================================


class SettlementInput(DiningInput):
    """Record only an observed full remaining balance; the server verifies currency and amount."""

    amount: ExactDecimal = Field(gt=0, max_digits=24, decimal_places=8)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    mode: str = Field(min_length=1, max_length=40)
    reference: str = Field(min_length=1, max_length=160)
    received_at: datetime
    observed: Literal[True]


# ==============================================
# FINALIZED INVOICE BALANCE
# Sales stay unchanged while existing verified advances and the final receipt reduce the amount due.
# ==============================================


async def invoice_balance(
    *, session: AsyncSession, invoice: DiningInvoice
) -> JsonObject:
    """Read exact scoped amounts without deriving money from the legacy Float bridge."""
    advances = await session.scalar(
        base_select(DiningAllocation)
        .with_only_columns(func.coalesce(func.sum(DiningAllocation.amount), 0))
        .where(
            DiningAllocation.invoice_id == invoice.id,
            DiningAllocation.restaurant_id == invoice.restaurant_id,
            DiningAllocation.branch_id == invoice.branch_id,
        )
    )
    receipt = await session.scalar(
        base_select(DiningSettlement).where(
            DiningSettlement.invoice_id == invoice.id,
            DiningSettlement.restaurant_id == invoice.restaurant_id,
            DiningSettlement.branch_id == invoice.branch_id,
        )
    )
    paid = receipt.amount if receipt else Decimal(0)
    return {
        "status": invoice.status,
        "invoice_id": invoice.id,
        "currency": invoice.currency,
        "total": format(invoice.total, ".8f"),
        "advance": format(advances, ".8f"),
        "paid": format(paid, ".8f"),
        "balance": format(invoice.total - advances - paid, ".8f"),
        "settlement_id": receipt.id if receipt else None,
    }


# ==============================================
# SERIALIZED HUMAN COLLECTION
# Lock the same invoice used by advance allocation; idempotent repeats retain the original author and receipt.
# ==============================================


async def record_settlement(
    *, unit: DiningUnit, invoice_id: int, data: SettlementInput
) -> JsonObject:
    """Stage a receipt and event inside the caller's one tenant transaction, or reject without a payment."""
    await unit.guard(capability="collect", human=True)
    invoice = await unit.repo.one(model=DiningInvoice, identifier=invoice_id, lock=True)
    previous = await unit.session.scalar(
        base_select(DiningSettlement).where(
            DiningSettlement.invoice_id == invoice_id,
            DiningSettlement.restaurant_id == invoice.restaurant_id,
            DiningSettlement.branch_id == invoice.branch_id,
        )
    )
    received = utc(value=data.received_at)
    if previous:
        if (
            previous.amount,
            previous.currency,
            previous.mode,
            previous.reference,
            previous.received_at,
        ) != (data.amount, data.currency, data.mode, data.reference, received):
            raise DiningError(code="dining_settlement_replay_mismatch")
        return await invoice_balance(session=unit.session, invoice=invoice)
    policy = await unit.policy()
    balance = await invoice_balance(session=unit.session, invoice=invoice)
    if (
        invoice.status != "finalized"
        or data.currency != invoice.currency
        or data.amount != Decimal(str(balance["balance"]))
        or data.mode not in policy.payment_instructions
        or received > unit.now()
        or not data.reference.strip()
    ):
        raise DiningError(
            code="dining_exact_final_balance_and_verified_receipt_required"
        )
    receipt = DiningSettlement(
        **unit.scope(),
        invoice_id=invoice.id,
        invoice_revision=invoice.revision,
        invoice_total=invoice.total,
        advance_amount=Decimal(str(balance["advance"])),
        amount=data.amount,
        currency=data.currency,
        mode=data.mode,
        reference=data.reference,
        received_at=received,
        author_membership_id=unit.context.membership_id,
    )
    unit.session.add(receipt)
    await unit.session.flush()
    await unit.event(
        kind="invoice.settled",
        request_id=invoice.request_id,
        details={
            "invoice_id": invoice.id,
            "settlement_id": receipt.id,
            "amount": str(data.amount),
            "currency": data.currency,
        },
    )
    return await invoice_balance(session=unit.session, invoice=invoice)


# ==============================================
# CUSTOMER'S OWN FROZEN INVOICE
# A staff cookie is irrelevant: the separate visit proof must match this current public table link.
# ==============================================


async def own_invoice(
    *, session: AsyncSession, public_id: str, token: str
) -> JsonObject:
    """Allow the same visitor to read their finalized balance after departure, without reopening ordering."""
    async with tenant_unit_of_work(session=session):
        public = PublicDiningService(session=session)
        link, repo = await public._target(public_id=public_id, write=False)
        visit = await session.scalar(
            repo.statement(model=DiningVisit).where(
                DiningVisit.public_link_id == link.id,
                DiningVisit.token_hash == visit_hash(token=token),
            )
        )
        if visit is None:
            raise DiningError(code="dining_visit_secret_invalid")
        invoice = await session.scalar(
            repo.statement(model=DiningInvoice).where(
                DiningInvoice.occupation_id == visit.occupation_id,
                DiningInvoice.status == "finalized",
            )
        )
        if invoice is None:
            return {"status": "not_issued"}
        return await invoice_balance(session=session, invoice=invoice)
