# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Manual evidence submission and independently authorized settlement."""

# ==============================================
# IMPORTS
# ==============================================

import hashlib
import re
from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.core.logger import logger
from app.models.manual_payment import ManualPaymentReceipt
from app.models.payment import Payment
from app.repositories.manual_payment_repo import ManualPaymentRepository
from app.schemas.manual_payment import (
    ManualPaymentReview,
    ManualReceiptStatus,
    ReceiptResponse,
)
from app.schemas.payment import PaymentResponse
from app.services.business.admin.admin_service import AdminService
from app.services.business.payment_providers import get_payment_provider

from app.services.business.payment_providers.manual_transfer import ManualTransferProvider  # isort: skip  # fmt: skip
from app.services.business.payment_service import PaymentService
from app.services.business.payment_transaction import payment_transaction

# ==============================================
# CONSTANTS
# ==============================================

MAX_RECEIPT_BYTES: int = 2_097_152


# ==============================================
# NORMALIZE TRANSFER REFERENCE
# ==============================================


def normalize_transfer_reference(*, value: str) -> str:
    """Normalize a bounded postal transfer reference for global deduplication."""

    if not re.fullmatch(r"[A-Za-z0-9 ./_-]{3,120}", value):
        raise ValidationError(message="Invalid transfer reference")
    normalized = re.sub(r"[ ./_-]", "", value).upper()
    if len(normalized) < 3:
        raise ValidationError(message="Invalid transfer reference")
    return normalized


# ==============================================
# VALIDATE PRIVATE RECEIPT CONTENT
# ==============================================


def validate_receipt_content(*, content: bytes, media_type: str) -> None:
    """Reject unsupported media, missing file signatures, and oversized evidence."""

    signatures = {
        "image/png": content.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/jpeg": content.startswith(b"\xff\xd8\xff")
        and content.endswith(b"\xff\xd9"),
        "application/pdf": content.startswith(b"%PDF-") and b"%%EOF" in content[-1024:],
    }
    if not 0 < len(content) <= MAX_RECEIPT_BYTES or not signatures.get(
        media_type, False
    ):
        raise ValidationError(
            message="Receipt must be a PNG, JPEG, or PDF of at most 2 MiB"
        )


# ==============================================
# MANUAL PAYMENT SERVICE
# ==============================================


class ManualPaymentService:
    """Authorize receipt access and settle independently verified bank transfers.

    A receipt is evidence for review only. Payment settlement, subscription
    activation, receipt decisions, and audit events share one transaction.
    """

    # ==========================================
    # INIT
    # ==========================================

    def __init__(self, *, session: AsyncSession) -> None:
        """Bind payment and evidence operations to the caller's async session."""

        self.session = session
        self.repo = ManualPaymentRepository(session=session)

    # ==========================================
    # READ OWNED INVOICE
    # ==========================================

    async def get_invoice(self, *, payment_id: int, owner_id: int) -> PaymentResponse:
        """Return an invoice only after persisted tenant ownership validation."""

        payment = await self._payment(payment_id=payment_id, owner_id=owner_id)
        return PaymentResponse.model_validate(payment)

    # ==========================================
    # AUTHORIZE ACTIVE PAYMENT REVIEWER
    # ==========================================

    async def require_reviewer(self, *, admin_id: int) -> None:
        """Require an active administrator with the current payments.review grant."""

        await AdminService(self.session).check_admin_permission(
            admin_id=admin_id, required_permission="payments.review"
        )

    # ==========================================
    # VALIDATE MANUAL SUBSCRIPTION INVOICE
    # ==========================================

    async def _payment(
        self,
        *,
        payment_id: int,
        owner_id: int | None,
        lock: bool = False,
    ) -> Payment:
        """Read tenant-scoped transfer terms before accepting or exposing evidence.

        Existing invoices remain readable when a method is disabled; new
        submissions separately require an enabled provider configuration.
        """

        payment = await self.repo.get_payment(
            payment_id=payment_id, owner_id=owner_id, lock=lock
        )
        if payment is None:
            raise NotFoundError(message="Payment not found")
        if payment.payment_provider != "manual_transfer" or not payment.subscription_id:
            raise ValidationError(
                message="Payment is not a manual subscription transfer"
            )
        provider = ManualTransferProvider()
        provider.prepare_payment(
            method=payment.payment_method,
            amount=Decimal(str(payment.amount)),
            currency=payment.currency,
        )
        return payment

    # ==========================================
    # SUBMIT PRIVATE RECEIPT EVIDENCE
    # ==========================================

    async def submit_receipt(
        self,
        *,
        payment_id: int,
        owner_id: int,
        transaction_reference: str,
        content: bytes,
        media_type: str,
    ) -> ReceiptResponse:
        """Attach one globally unique receipt without marking an invoice paid.

        Exact retries return the existing receipt. Reused content or bank
        references fail without exposing evidence owned by another tenant.
        """

        reference = normalize_transfer_reference(value=transaction_reference)
        validate_receipt_content(content=content, media_type=media_type)
        digest = hashlib.sha256(content).hexdigest()
        try:
            async with payment_transaction(session=self.session):
                payment = await self._payment(
                    payment_id=payment_id, owner_id=owner_id, lock=True
                )
                get_payment_provider(method=payment.payment_method)
                existing = await self.repo.get_receipt(payment_id=payment_id)
                if existing is not None:
                    if (
                        existing.transaction_reference == reference
                        and existing.sha256 == digest
                    ):
                        return ReceiptResponse.model_validate(existing)
                    raise ConflictError(message="Payment already has receipt evidence")
                if payment.status != "pending":
                    raise ValidationError(
                        message="Only pending payments accept receipt evidence"
                    )
                receipt = await self.repo.create_receipt(
                    payment_id=payment_id,
                    transaction_reference=reference,
                    sha256=digest,
                    media_type=media_type,
                    content=content,
                )
                payment.external_reference = reference
                await self.repo.append_audit(
                    payment_id=payment_id,
                    receipt_id=receipt.id,
                    owner_id=owner_id,
                    admin_id=None,
                    action="receipt_submitted",
                    details={"sha256": digest, "transaction_reference": reference},
                )
                result = ReceiptResponse.model_validate(receipt)
            logger.info(
                "manual_payment_receipt_submitted",
                extra={
                    "payment_id": payment_id,
                    "owner_id": owner_id,
                    "receipt_id": result.id,
                },
            )
            return result
        except IntegrityError as error:
            raise ConflictError(
                message="Receipt evidence or reference has already been submitted"
            ) from error

    # ==========================================
    # READ AUTHORIZED PRIVATE RECEIPT
    # ==========================================

    async def get_receipt(
        self,
        *,
        payment_id: int,
        owner_id: int | None,
        admin_id: int | None = None,
        content: bool = False,
    ) -> ManualPaymentReceipt:
        """Expose receipt evidence only to its owner or an active reviewer."""

        if owner_id is None:
            if admin_id is None:
                raise NotFoundError(message="Payment not found")
            await self.require_reviewer(admin_id=admin_id)
        await self._payment(payment_id=payment_id, owner_id=owner_id)
        receipt = await self.repo.get_receipt(payment_id=payment_id, content=content)
        if receipt is None:
            raise NotFoundError(message="Receipt not found")
        return receipt

    # ==========================================
    # REVIEW INDEPENDENTLY VERIFIED TRANSFER
    # ==========================================

    async def review(
        self, *, payment_id: int, admin_id: int, data: ManualPaymentReview
    ) -> ReceiptResponse:
        """Persist one final decision and its financial effects atomically.

        Approval requires matching funds, currency, and bank reference.
        Exact retries preserve the original settlement and audit history.
        """

        async with payment_transaction(session=self.session):
            await self.require_reviewer(admin_id=admin_id)
            payment = await self._payment(
                payment_id=payment_id, owner_id=None, lock=True
            )
            receipt = await self.repo.get_receipt(payment_id=payment_id, lock=True)
            if receipt is None:
                raise NotFoundError(message="Receipt not found")
            decision: ManualReceiptStatus = (
                "approved" if data.decision == "approve" else "rejected"
            )
            reference = (
                normalize_transfer_reference(value=data.bank_transaction_reference)
                if data.bank_transaction_reference
                else None
            )
            if decision == "approved" and (
                reference != receipt.transaction_reference
                or data.received_amount != Decimal(str(payment.amount))
                or data.received_currency != payment.currency
            ):
                raise ValidationError(
                    message="Verified funds do not match the subscription payment"
                )
            if receipt.review_status != "pending":
                if (
                    receipt.review_status == decision
                    and receipt.received_amount == data.received_amount
                    and receipt.received_currency == data.received_currency
                    and receipt.review_note == data.note
                ):
                    return ReceiptResponse.model_validate(receipt)
                raise ConflictError(message="Receipt already has a final review")
            if payment.status != "pending":
                raise ConflictError(message="Payment is no longer pending")
            if decision == "approved":
                await PaymentService(session=self.session).confirm_payment(
                    payment_id=payment_id
                )
            else:
                await PaymentService(session=self.session).fail_payment(
                    payment_id=payment_id
                )
            receipt.review_status = decision
            receipt.reviewed_by = admin_id
            receipt.reviewed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            receipt.received_amount = data.received_amount
            receipt.received_currency = data.received_currency
            receipt.review_note = data.note
            await self.repo.append_audit(
                payment_id=payment_id,
                receipt_id=receipt.id,
                owner_id=payment.owner_id,
                admin_id=admin_id,
                action="receipt_" + decision,
                details={
                    "sha256": receipt.sha256,
                    "funds_received": data.funds_received,
                    "reviewer_admin_id": admin_id,
                    "bank_reference": reference,
                    "received_amount": str(data.received_amount)
                    if data.received_amount
                    else None,
                    "currency": data.received_currency,
                    "note": data.note,
                },
            )
            result = ReceiptResponse.model_validate(receipt)
        logger.info(
            "manual_payment_review_recorded",
            extra={
                "payment_id": payment_id,
                "admin_id": admin_id,
                "receipt_id": result.id,
                "review_status": result.review_status,
            },
        )
        return result
