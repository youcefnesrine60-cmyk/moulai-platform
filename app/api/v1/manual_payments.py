# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Phase-one billing API: private uploads and RBAC-controlled manual review."""

# ==============================================
# IMPORTS
# ==============================================

from typing import (
    Annotated,
    TypeAlias,
)

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import (
    AdminPrincipal,
    OwnerPrincipal,
    get_current_owner,
    require_admin_permission,
    require_owned_payment,
)
from app.core.database import get_db
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from app.models.manual_payment import ManualPaymentReceipt
from app.schemas.manual_payment import (
    ManualPaymentReview,
    ManualSubscriptionCheckout,
    PaymentAuditResponse,
    PaymentReviewContext,
    ReceiptResponse,
)
from app.schemas.payment import PaymentResponse
from app.services.business.manual_payment_service import (
    MAX_RECEIPT_BYTES,
    ManualPaymentService,
)

from app.services.business.subscription_checkout_service import SubscriptionCheckoutService  # isort: skip  # fmt: skip

# ==============================================
# ROUTER AND AUTHORIZED DEPENDENCIES
# ==============================================

router = APIRouter(tags=["Manual billing"])
Session: TypeAlias = Annotated[AsyncSession, Depends(get_db)]
Owner: TypeAlias = Annotated[OwnerPrincipal, Depends(get_current_owner)]
Reviewer: TypeAlias = Annotated[
    AdminPrincipal, Depends(require_admin_permission("payments.review"))
]


# ==============================================
# MAP DOMAIN ERRORS
# ==============================================


def payment_error(*, error: Exception) -> HTTPException:
    """Map expected billing failures without exposing another tenant's evidence."""

    status = {
        NotFoundError: 404,
        ConflictError: 409,
        ValidationError: 422,
        UnauthorizedError: 403,
    }
    return HTTPException(status_code=status.get(type(error), 409), detail=str(error))


# ==============================================
# CREATE OWNED MANUAL SUBSCRIPTION INVOICE
# ==============================================


@router.post("/billing/subscriptions", response_model=PaymentResponse, status_code=201)
async def create_manual_subscription(
    *, data: ManualSubscriptionCheckout, owner: Owner, session: Session
) -> PaymentResponse:
    """Create or reuse a tenant-scoped invoice using authoritative server pricing."""

    try:
        return await SubscriptionCheckoutService(session=session).create(
            owner_id=owner.owner_id, data=data
        )
    except (NotFoundError, ConflictError, ValidationError) as error:
        raise payment_error(error=error) from error


# ==============================================
# SUBMIT BOUNDED PRIVATE RECEIPT
# ==============================================


@router.post(
    "/payments/{payment_id}/receipt",
    response_model=ReceiptResponse,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                media: {"schema": {"type": "string", "format": "binary"}}
                for media in ("image/png", "image/jpeg", "application/pdf")
            },
        }
    },
)
async def submit_receipt(
    *,
    payment_id: int,
    request: Request,
    owner: Owner,
    session: Session,
    transaction_reference: Annotated[
        str, Header(alias="X-Transaction-Reference", min_length=3, max_length=120)
    ],
) -> ReceiptResponse:
    """Authorize the invoice before streaming a bounded receipt upload."""

    # Authorization precedes accepting the bounded raw file body.
    service = ManualPaymentService(session=session)
    try:
        await require_owned_payment(payment_id=payment_id, owner=owner, session=session)
        content = bytearray()
        async for chunk in request.stream():
            if len(content) + len(chunk) > MAX_RECEIPT_BYTES:
                raise HTTPException(status_code=413, detail="Receipt exceeds 2 MiB")
            content.extend(chunk)
        return await service.submit_receipt(
            payment_id=payment_id,
            owner_id=owner.owner_id,
            transaction_reference=transaction_reference,
            content=bytes(content),
            media_type=request.headers.get("content-type", "")
            .split(";", 1)[0]
            .strip()
            .lower(),
        )
    except (NotFoundError, ConflictError, ValidationError) as error:
        raise payment_error(error=error) from error


# ==============================================
# READ OWNED RECEIPT METADATA
# ==============================================


@router.get("/payments/{payment_id}/receipt", response_model=ReceiptResponse)
async def get_receipt(
    *, payment_id: int, owner: Owner, session: Session
) -> ReceiptResponse:
    """Read receipt metadata belonging to the authenticated owner."""

    try:
        receipt = await ManualPaymentService(session=session).get_receipt(
            payment_id=payment_id, owner_id=owner.owner_id
        )
        return ReceiptResponse.model_validate(receipt)
    except (NotFoundError, ValidationError) as error:
        raise payment_error(error=error) from error


# ==============================================
# BUILD PRIVATE RECEIPT DOWNLOAD
# ==============================================


def download_receipt(*, receipt: ManualPaymentReceipt) -> Response:
    """Return authorized evidence as an attachment with caching disabled."""

    extension = {"image/png": "png", "image/jpeg": "jpg", "application/pdf": "pdf"}[
        receipt.media_type
    ]
    return Response(
        content=receipt.content,
        media_type=receipt.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="receipt-{receipt.id}.{extension}"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store",
        },
    )


# ==============================================
# READ AUTHORIZED PAYMENT REVIEW CONTEXT
# ==============================================


@router.get("/admin/manual-payments/{payment_id}", response_model=PaymentReviewContext)
async def get_review_context(
    *, payment_id: int, admin: Reviewer, session: Session
) -> PaymentReviewContext:
    """Read invoice terms, receipt metadata, and audit events for a reviewer."""

    service = ManualPaymentService(session=session)
    try:
        receipt = await service.get_receipt(
            payment_id=payment_id, owner_id=None, admin_id=admin.admin_id
        )
        payment = await service.repo.get_payment(payment_id=payment_id, owner_id=None)
        return PaymentReviewContext(
            payment=PaymentResponse.model_validate(payment),
            receipt=ReceiptResponse.model_validate(receipt),
            audit=[
                PaymentAuditResponse.model_validate(event)
                for event in await service.repo.get_audit(payment_id=payment_id)
            ],
        )
    except (NotFoundError, ValidationError, UnauthorizedError) as error:
        raise payment_error(error=error) from error


# ==============================================
# DOWNLOAD OWNED PRIVATE RECEIPT
# ==============================================


@router.get("/payments/{payment_id}/receipt/file")
async def get_receipt_file(
    *, payment_id: int, owner: Owner, session: Session
) -> Response:
    """Download receipt content after persisted tenant ownership validation."""

    try:
        receipt = await ManualPaymentService(session=session).get_receipt(
            payment_id=payment_id, owner_id=owner.owner_id, content=True
        )
        return download_receipt(receipt=receipt)
    except (NotFoundError, ValidationError) as error:
        raise payment_error(error=error) from error


# ==============================================
# LIST AUTHORIZED ADMINISTRATIVE REVIEW QUEUE
# ==============================================


@router.get("/admin/manual-payments", response_model=list[ReceiptResponse])
async def list_pending_receipts(
    *,
    admin: Reviewer,
    session: Session,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[ReceiptResponse]:
    """List pending receipt metadata behind the live payments.review dependency."""

    receipts = await ManualPaymentService(session=session).repo.list_pending(
        skip=skip, limit=limit
    )
    return [ReceiptResponse.model_validate(receipt) for receipt in receipts]


# ==============================================
# DOWNLOAD RECEIPT FOR AUTHORIZED REVIEW
# ==============================================


@router.get("/admin/manual-payments/{payment_id}/receipt/file")
async def review_receipt_file(
    *, payment_id: int, admin: Reviewer, session: Session
) -> Response:
    """Download private evidence only for a currently authorized reviewer."""

    try:
        receipt = await ManualPaymentService(session=session).get_receipt(
            payment_id=payment_id, owner_id=None, admin_id=admin.admin_id, content=True
        )
        return download_receipt(receipt=receipt)
    except (NotFoundError, ValidationError, UnauthorizedError) as error:
        raise payment_error(error=error) from error


# ==============================================
# RECORD INDEPENDENTLY VERIFIED PAYMENT DECISION
# ==============================================


@router.post(
    "/admin/manual-payments/{payment_id}/review", response_model=ReceiptResponse
)
async def review_receipt(
    *, payment_id: int, data: ManualPaymentReview, admin: Reviewer, session: Session
) -> ReceiptResponse:
    """Apply a final review with atomic settlement, activation, and audit writes."""

    try:
        return await ManualPaymentService(session=session).review(
            payment_id=payment_id, admin_id=admin.admin_id, data=data
        )
    except (
        NotFoundError,
        ConflictError,
        ValidationError,
        UnauthorizedError,
        ValueError,
    ) as error:
        raise payment_error(error=error) from error
