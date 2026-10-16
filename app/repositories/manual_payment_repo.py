# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Tenant-scoped billing reads and flush-only evidence persistence."""

# ==============================================
# IMPORTS
# ==============================================

from typing import (
    TypeAlias,
    TypeVar,
)

from sqlalchemy import (
    Select,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import (
    defer,
    raiseload,
)

from app.models.base import BaseModel
from app.models.manual_payment import (
    ManualPaymentAudit,
    ManualPaymentReceipt,
)
from app.models.payment import Payment
from app.models.restaurant import Restaurant
from app.schemas.manual_payment import PaymentAuditDetails

# ==============================================
# TYPE ALIASES
# ==============================================

BillingModel = TypeVar("BillingModel", bound=BaseModel)
ManualReceiptList: TypeAlias = list[ManualPaymentReceipt]
ManualAuditList: TypeAlias = list[ManualPaymentAudit]


# ==============================================
# MANUAL PAYMENT REPOSITORY
# ==============================================


class ManualPaymentRepository:
    """Read billing entities and flush changes inside a service-owned transaction.

    Owner-facing reads first validate payment and restaurant ownership.
    Unscoped reads are reserved for authorized administrative services.
    """

    # ==========================================
    # INIT
    # ==========================================

    def __init__(self, *, session: AsyncSession) -> None:
        """Bind evidence persistence to the caller's async SQLAlchemy session."""

        self.session = session

    # ==========================================
    # BASE SELECT
    # ==========================================

    def _select(self, model: type[BillingModel]) -> Select[tuple[BillingModel]]:
        """Build a base query without implicitly loading relationship graphs."""

        return select(model).options(raiseload("*"))

    # ==========================================
    # READ OWNED PAYMENT
    # ==========================================

    async def get_payment(
        self,
        *,
        payment_id: int,
        owner_id: int | None,
        lock: bool = False,
    ) -> Payment | None:
        """Read an invoice whose tenant matches the persisted restaurant owner.

        Locked reads refresh cached ORM columns so idempotency decisions
        use the latest committed payment state.
        """

        query = (
            self._select(Payment)
            .join(Restaurant, Restaurant.id == Payment.restaurant_id)
            .where(Payment.id == payment_id, Restaurant.owner_id == Payment.owner_id)
        )
        if owner_id is not None:
            query = query.where(Payment.owner_id == owner_id)
        if lock:
            query = query.with_for_update(of=Payment).execution_options(
                populate_existing=True
            )
        return (await self.session.execute(query)).scalar_one_or_none()

    # ==========================================
    # READ PRIVATE RECEIPT
    # ==========================================

    async def get_receipt(
        self,
        *,
        payment_id: int,
        content: bool = False,
        lock: bool = False,
    ) -> ManualPaymentReceipt | None:
        """Read receipt evidence after the service has authorized its invoice.

        Binary content remains unloaded unless explicitly requested.
        Locked reads refresh cached administrative review state.
        """

        query = self._select(ManualPaymentReceipt).where(
            ManualPaymentReceipt.payment_id == payment_id
        )
        if not content:
            query = query.options(defer(ManualPaymentReceipt.content, raiseload=True))
        if lock:
            query = query.with_for_update().execution_options(populate_existing=True)
        return (await self.session.execute(query)).scalar_one_or_none()

    # ==========================================
    # LIST ADMINISTRATIVE REVIEW QUEUE
    # ==========================================

    async def list_pending(self, *, skip: int, limit: int) -> ManualReceiptList:
        """List pending receipt metadata for an authorized payment reviewer."""

        query = (
            self._select(ManualPaymentReceipt)
            .options(defer(ManualPaymentReceipt.content, raiseload=True))
            .where(ManualPaymentReceipt.review_status == "pending")
            .order_by(ManualPaymentReceipt.id)
            .offset(skip)
            .limit(limit)
        )
        return list((await self.session.execute(query)).scalars().all())

    # ==========================================
    # CREATE RECEIPT EVIDENCE
    # ==========================================

    async def create_receipt(
        self,
        *,
        payment_id: int,
        transaction_reference: str,
        sha256: str,
        media_type: str,
        content: bytes,
    ) -> ManualPaymentReceipt:
        """Flush one pending receipt without committing its billing transaction."""

        receipt = ManualPaymentReceipt(
            payment_id=payment_id,
            transaction_reference=transaction_reference,
            sha256=sha256,
            media_type=media_type,
            content=content,
        )
        self.session.add(receipt)
        await self.session.flush()
        return receipt

    # ==========================================
    # APPEND PAYMENT AUDIT EVENT
    # ==========================================

    async def append_audit(
        self,
        *,
        payment_id: int,
        receipt_id: int,
        owner_id: int,
        admin_id: int | None,
        action: str,
        details: PaymentAuditDetails,
    ) -> None:
        """Append a tenant and actor snapshot in the current billing transaction."""

        self.session.add(
            ManualPaymentAudit(
                payment_id=payment_id,
                receipt_id=receipt_id,
                owner_id=owner_id,
                admin_id=admin_id,
                action=action,
                details=details,
            )
        )
        await self.session.flush()

    # ==========================================
    # READ AUTHORIZED PAYMENT HISTORY
    # ==========================================

    async def get_audit(self, *, payment_id: int) -> ManualAuditList:
        """Read ordered audit events after payment reviewer authorization."""

        query = (
            self._select(ManualPaymentAudit)
            .where(ManualPaymentAudit.payment_id == payment_id)
            .order_by(ManualPaymentAudit.id)
        )
        return list((await self.session.execute(query)).scalars().all())
