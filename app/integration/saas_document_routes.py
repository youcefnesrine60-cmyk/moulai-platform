# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# SCOPED SAAS DOCUMENT HTTP CONTRACTS
# Separate owner consultation, independent platform decisions and minimal read-only public verification.
# ==============================================

"""No funds mutation, bank evidence disclosure, role inference or public documentary issuance."""

from __future__ import annotations

# isort: split
# ==============================================
# BOUNDED AUTHENTICATED REQUEST CONTRACTS
# Reject client financial facts and use only server-retained references.
# ==============================================

import time
from collections import deque
from typing import Literal

from fastapi import (
    FastAPI,
    HTTPException,
)
from fastapi.params import Depends
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.integration.identity import BrowserIdentity
from app.models.payment import Payment
from app.models.restaurant import Restaurant
from app.models.subscription_document import SubscriptionDocument
from app.repositories.restaurant_context import company_column
from app.repositories.subscription_queries import base_select
from app.services.business.platform_authority import require_platform_permission
from app.services.business.subscription_documents import SubscriptionDocumentService
from app.services.business.tenant_access import TenantAccessService

# ==============================================
# CLOSED DOCUMENT COMMANDS
# Explicit confirmation is distinct from a display action or possession of a public reference.
# ==============================================


class IssueDocumentInput(BaseModel):
    """Issue the server-selected paid source; optionally name an invalidated predecessor."""

    model_config = ConfigDict(extra="forbid")
    replaces_id: int | None = Field(default=None, strict=True, gt=0)


class InvalidateDocumentInput(BaseModel):
    """Require a deliberate confirmation and a bounded meaningful reason."""

    model_config = ConfigDict(extra="forbid")
    confirmed: Literal[True]
    reason: str = Field(min_length=3, max_length=2000)


class VerifyDocumentInput(BaseModel):
    """Opaque verification reference only; never a session or payment token."""

    model_config = ConfigDict(extra="forbid")
    reference: str = Field(max_length=100)


# ==============================================
# DISTINCT SAAS HTTP COMPOSITION
# Existing O4 readers continue working; only this new circuit requires the additive O5 schema.
# ==============================================


def mount_saas_document_routes(
    *,
    app: FastAPI,
    identity_dep: Depends,
    session_dep: Depends,
    marker: str,
    origin: str,
) -> None:
    """Mount local synthetic document operations without changing any financial endpoint."""
    verification_window: deque[float] = deque()

    # ==============================================
    # OWNED RETAINED VERSIONS
    # A tenant consultation grant never confers emission or invalidation authority.
    # ==============================================

    @app.get(
        "/api/web/organizations/{organization_id}/restaurants/{restaurant_id}/saas-payments/{payment_id}/documents"
    )
    async def own_documents(
        organization_id: int,
        restaurant_id: int,
        payment_id: int,
        locale: Literal["fr", "en", "ar"] = "fr",
        person: BrowserIdentity = identity_dep,
        session: AsyncSession = session_dep,
    ) -> list[dict[str, JsonValue]]:
        """Check tenant, establishment and payment ownership before returning any document content."""
        async with TenantAccessService(session=session).authorized(
            principal=person.principal,
            organization_id=organization_id,
            permission="tenant.billing.read",
        ) as unit:
            await unit.restaurant(restaurant_id=restaurant_id)
            service = SubscriptionDocumentService(session=session, marker=marker)
            await service.ready()
            payment = await session.scalar(
                base_select(Payment)
                .with_only_columns(Payment.id)
                .join(Restaurant, Restaurant.id == Payment.restaurant_id)
                .where(
                    Payment.id == payment_id,
                    Payment.restaurant_id == restaurant_id,
                    company_column() == organization_id,
                )
            )
            if payment is None:
                raise HTTPException(
                    status_code=404,
                    detail={"code": "subscription_document_source_unavailable"},
                )
            documents = (
                await session.scalars(
                    base_select(SubscriptionDocument)
                    .where(
                        SubscriptionDocument.payment_id == payment_id,
                        SubscriptionDocument.organization_id == organization_id,
                        SubscriptionDocument.restaurant_id == restaurant_id,
                    )
                    .order_by(SubscriptionDocument.version.desc())
                )
            ).all()
            return [
                await service.projection(
                    document=document, origin=origin, locale=locale
                )
                for document in documents
            ]

    # ==============================================
    # INDEPENDENT DOCUMENTARY ADMINISTRATION
    # Either explicit documentary grant permits consultation; each command rechecks its own exact grant.
    # ==============================================

    @app.get("/api/web/platform/saas-documents")
    async def queue(
        locale: Literal["fr", "en", "ar"] = "fr",
        person: BrowserIdentity = identity_dep,
        session: AsyncSession = session_dep,
    ) -> list[dict[str, JsonValue]]:
        """Return bounded payment references and documentary versions without exposing bank proofs."""
        async with session.begin():
            can_issue = True
            try:
                await require_platform_permission(
                    session=session,
                    principal=person.principal,
                    permission="subscriptions.documents.issue",
                )
            except HTTPException as error:
                if error.status_code != 403:
                    raise
                can_issue = False
                await require_platform_permission(
                    session=session,
                    principal=person.principal,
                    permission="subscriptions.documents.invalidate",
                )
            service = SubscriptionDocumentService(session=session, marker=marker)
            await service.ready()
            rows = (
                await session.execute(
                    base_select(Payment)
                    .with_only_columns(
                        Payment.id,
                        Payment.amount,
                        Payment.currency,
                        Payment.status,
                        Restaurant.name,
                    )
                    .join(Restaurant, Restaurant.id == Payment.restaurant_id)
                    .where(Payment.subscription_id.is_not(None))
                    .where(
                        True
                        if can_issue
                        else base_select(SubscriptionDocument)
                        .with_only_columns(SubscriptionDocument.id)
                        .where(SubscriptionDocument.payment_id == Payment.id)
                        .exists()
                    )
                    .order_by(Payment.id.desc())
                    .limit(100)
                )
            ).all()
            result: list[dict[str, JsonValue]] = []
            for row in rows:
                documents = (
                    await session.scalars(
                        base_select(SubscriptionDocument)
                        .where(SubscriptionDocument.payment_id == row.id)
                        .order_by(SubscriptionDocument.version.desc())
                    )
                ).all()
                result.append(
                    {
                        "payment_id": row.id,
                        "amount": str(row.amount),
                        "currency": row.currency,
                        "payment_status": row.status,
                        "restaurant_name": row.name,
                        "documents": [
                            await service.projection(
                                document=document, origin=origin, locale=locale
                            )
                            for document in documents
                        ],
                    }
                )
            return result

    # ==============================================
    # ATOMIC EMISSION AND INVALIDATION
    # The outer request commits the document and its event together or rolls both back.
    # ==============================================

    @app.post("/api/web/platform/saas-payments/{payment_id}/documents")
    async def issue(
        payment_id: int,
        data: IssueDocumentInput,
        locale: Literal["fr", "en", "ar"] = "fr",
        person: BrowserIdentity = identity_dep,
        session: AsyncSession = session_dep,
    ) -> dict[str, JsonValue]:
        """Issue only from already committed coherent funds and service records."""
        async with session.begin():
            service = SubscriptionDocumentService(session=session, marker=marker)
            document = await service.issue(
                principal=person.principal,
                payment_id=payment_id,
                replaces_id=data.replaces_id,
            )
            return await service.projection(
                document=document, origin=origin, locale=locale
            )

    # ==============================================
    # DISTINCT INVALIDATION AUTHORITY
    # Confirmation and a reason cannot substitute for the independent stored grant.
    # ==============================================

    @app.post("/api/web/platform/saas-documents/{document_id}/invalidate")
    async def invalidate(
        document_id: int,
        data: InvalidateDocumentInput,
        locale: Literal["fr", "en", "ar"] = "fr",
        person: BrowserIdentity = identity_dep,
        session: AsyncSession = session_dep,
    ) -> dict[str, JsonValue]:
        """Invalidate documentary validity only, after the independent exact permission check."""
        async with session.begin():
            service = SubscriptionDocumentService(session=session, marker=marker)
            document = await service.invalidate(
                principal=person.principal,
                document_id=document_id,
                reason=data.reason,
                confirmed=data.confirmed,
            )
            return await service.projection(
                document=document, origin=origin, locale=locale
            )

    # ==============================================
    # RATE-BOUNDED READ-ONLY VERIFICATION
    # Keep references out of request URLs; the closed staging tester gate remains unchanged.
    # ==============================================

    @app.post("/api/web/saas-documents/verify")
    async def verify(
        data: VerifyDocumentInput, session: AsyncSession = session_dep
    ) -> dict[str, JsonValue]:
        """Expose only reference, issuer, issuance date and validity; bound this reader to thirty requests/minute."""
        now = time.monotonic()
        while verification_window and verification_window[0] <= now - 60:
            verification_window.popleft()
        if len(verification_window) >= 30:
            raise HTTPException(
                status_code=429, detail={"code": "subscription_document_reader_limited"}
            )
        verification_window.append(now)
        async with session.begin():
            return await SubscriptionDocumentService(
                session=session, marker=marker
            ).verify(reference=data.reference)
