# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# VERIFIED SAAS DOCUMENT LIFECYCLE
# Issue immutable local documents from paid snapshots, with independent grants and no financial side effects.
# ==============================================

"""The request owns commit; document preparation never activates, refunds or changes a subscription."""

from __future__ import annotations

# isort: split
# ==============================================
# EXACT SOURCE AND AUTHORITY CONTRACTS
# Read explicit projections to avoid legacy ORM fields absent from historical DDL.
# ==============================================

import hashlib
import json
import logging
import secrets
from decimal import Decimal

from fastapi import HTTPException
from pydantic import JsonValue
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.oidc import OIDCPrincipal
from app.models.admin import Admin
from app.models.cash_collection import CashCollection
from app.models.manual_payment import ManualPaymentReceipt
from app.models.payment import Payment
from app.models.restaurant import Restaurant
from app.models.subscription import Subscription
from app.models.subscription_document import (
    SubscriptionDocument,
    SubscriptionDocumentEvent,
)
from app.models.subscription_pricing import SubscriptionPricingSnapshot
from app.repositories.restaurant_context import company_column
from app.repositories.subscription_queries import base_select
from app.services.business.document_qr import (
    public_read_url,
    svg_for_public_url,
    valid_public_id,
)
from app.services.business.enrollment_documents import require_document_rehearsal
from app.services.business.platform_authority import require_platform_permission

logger = logging.getLogger(__name__)

# ==============================================
# DETERMINISTIC RETAINED CONTENT DIGEST
# Stable JSON includes exact decimal strings and source versions, never current tariffs.
# ==============================================


def content_digest(*, content: dict[str, JsonValue]) -> str:
    """Hash the immutable documentary content without transport or credentials."""
    return hashlib.sha256(
        json.dumps(
            content,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()


# ==============================================
# OWNED DOCUMENT OPERATIONS
# Serialize emission on the existing payment row and invalidation on the retained document.
# ==============================================


class SubscriptionDocumentService:
    """Use caller-owned transactions and exact server-side permission checks on every operation."""

    # ==============================================
    # TRANSACTION AND SYNTHETIC ENVIRONMENT BINDING
    # The marker is reattested before documentary operations; it is never a caller-selected tenant identity.
    # ==============================================

    def __init__(self, *, session: AsyncSession, marker: str) -> None:
        """Bind the request session and explicit local rehearsal marker."""
        self.session = session
        self.marker = marker

    # ==============================================
    # ADDITIVE SCHEMA ADMISSION
    # Keep an O4 application usable before cutover while refusing document requests requiring missing storage.
    # ==============================================

    async def ready(self) -> None:
        """Reject production or a wrong database before checking the exact required revision."""
        await require_document_rehearsal(session=self.session, marker=self.marker)
        revision = await self.session.scalar(
            text("SELECT version_num FROM public.alembic_version")
        )
        if revision != "o520261111":
            raise HTTPException(
                status_code=409,
                detail={"code": "subscription_document_migration_required"},
            )

    # ==============================================
    # RETAINED FUNDS AND PERIOD PROJECTION
    # Lock payment and service period together; uploaded evidence alone is not proof of received funds.
    # ==============================================

    async def retained(self, *, payment_id: int) -> dict[str, JsonValue]:
        """Validate coherent paid sources; refuse unsupported or incomplete historical records."""
        row = (
            await self.session.execute(
                base_select(Payment)
                .with_only_columns(
                    Payment.id,
                    Payment.owner_id,
                    Payment.restaurant_id,
                    Payment.subscription_id,
                    Payment.status,
                    Payment.amount,
                    Payment.currency,
                    Payment.payment_method,
                    Payment.payment_provider,
                    Payment.paid_at,
                    Subscription.amount.label("service_amount"),
                    Subscription.currency.label("service_currency"),
                    Subscription.owner_id.label("service_owner"),
                    Subscription.restaurant_id.label("service_restaurant"),
                    Subscription.starts_at,
                    Subscription.expires_at,
                    Subscription.status.label("service_status"),
                    Subscription.billing_cycle,
                    company_column().label("organization_id"),
                    Restaurant.name,
                    Restaurant.owner_id.label("restaurant_owner"),
                )
                .join(Subscription, Subscription.id == Payment.subscription_id)
                .join(Restaurant, Restaurant.id == Payment.restaurant_id)
                .where(Payment.id == payment_id)
                .with_for_update(of=(Payment, Subscription))
            )
        ).one_or_none()
        if row is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "subscription_document_source_unavailable"},
            )
        if row.status != "paid" or row.paid_at is None:
            raise HTTPException(
                status_code=409,
                detail={"code": "subscription_document_funds_unverified"},
            )
        if (
            row.service_status not in {"active", "scheduled", "expired"}
            or row.starts_at is None
            or row.expires_at is None
            or row.expires_at <= row.starts_at
            or row.service_amount != row.amount
            or row.service_currency != row.currency
            or row.service_owner != row.owner_id
            or row.service_restaurant != row.restaurant_id
            or row.restaurant_owner != row.owner_id
            or row.organization_id is None
            or row.amount <= 0
        ):
            raise HTTPException(
                status_code=409,
                detail={"code": "subscription_document_period_incoherent"},
            )
        if row.payment_method == "cash" and row.payment_provider == "manual_cash":
            verified = await self.session.scalar(
                base_select(CashCollection)
                .with_only_columns(CashCollection.id)
                .where(
                    CashCollection.payment_id == payment_id,
                    CashCollection.subscription_id == row.subscription_id,
                    CashCollection.received_amount == row.amount,
                    CashCollection.expected_amount == row.amount,
                    CashCollection.currency == row.currency,
                    CashCollection.confirmed_at.is_not(None),
                )
                .with_for_update(read=True, of=CashCollection)
            )
        elif (
            row.payment_method in {"ccp", "baridimob"}
            and row.payment_provider == "manual_transfer"
        ):
            verified = await self.session.scalar(
                base_select(ManualPaymentReceipt)
                .with_only_columns(ManualPaymentReceipt.id)
                .where(
                    ManualPaymentReceipt.payment_id == payment_id,
                    ManualPaymentReceipt.review_status == "approved",
                    ManualPaymentReceipt.received_amount == row.amount,
                    ManualPaymentReceipt.received_currency == row.currency,
                    ManualPaymentReceipt.reviewed_at.is_not(None),
                )
                .with_for_update(read=True, of=ManualPaymentReceipt)
            )
        else:
            verified = None
        if verified is None:
            raise HTTPException(
                status_code=409,
                detail={"code": "subscription_document_funds_unverified"},
            )
        snapshot = await self.session.scalar(
            base_select(SubscriptionPricingSnapshot).where(
                SubscriptionPricingSnapshot.subscription_id == row.subscription_id,
                SubscriptionPricingSnapshot.restaurant_id == row.restaurant_id,
                SubscriptionPricingSnapshot.owner_id == row.owner_id,
            )
        )
        if snapshot is None:
            raise HTTPException(
                status_code=409,
                detail={"code": "subscription_document_snapshot_missing"},
            )
        if not isinstance(snapshot.pricing, dict) or not isinstance(
            snapshot.parameters, dict
        ):
            raise HTTPException(
                status_code=409,
                detail={"code": "subscription_document_snapshot_incoherent"},
            )
        try:
            retained_amount = Decimal(str(snapshot.pricing["final_amount_due"]))
        except (KeyError, ValueError, ArithmeticError):
            raise HTTPException(
                status_code=409,
                detail={"code": "subscription_document_snapshot_incoherent"},
            ) from None
        if not retained_amount.is_finite() or retained_amount != row.amount:
            raise HTTPException(
                status_code=409,
                detail={"code": "subscription_document_snapshot_incoherent"},
            )
        return {
            "organization_id": row.organization_id,
            "restaurant_id": row.restaurant_id,
            "restaurant_name": row.name,
            "payment_id": row.id,
            "subscription_id": row.subscription_id,
            "snapshot_id": snapshot.id,
            "amount": str(row.amount),
            "currency": row.currency,
            "starts_at": row.starts_at.isoformat(),
            "expires_at": row.expires_at.isoformat(),
            "period_status_at_issue": row.service_status,
            "billing_cycle": row.billing_cycle,
            "paid_at": row.paid_at.isoformat(),
            "pricing": snapshot.pricing,
            "parameters": snapshot.parameters,
            "issuer": "MoulAI™",
            "synthetic": True,
        }

    # ==============================================
    # EXPLICIT ADMINISTRATIVE AUTHOR SNAPSHOT
    # Keep the known display name without exposing identity subjects or relying on account survival.
    # ==============================================

    async def author_name(self, *, admin_id: int) -> str:
        """Return a retained author label; an absent display name remains explicitly unidentified."""
        name = await self.session.scalar(
            base_select(Admin)
            .with_only_columns(Admin.full_name)
            .where(Admin.id == admin_id)
        )
        return name.strip() if name and name.strip() else "MoulAI administrator"

    # ==============================================
    # SINGLE IDEMPOTENT EMISSION
    # Replacement requires an already invalidated original and preserves its exact financial content and lineage.
    # ==============================================

    async def issue(
        self,
        *,
        principal: OIDCPrincipal,
        payment_id: int,
        replaces_id: int | None = None,
    ) -> SubscriptionDocument:
        """Prepare a single version and audit atomically; no commit or notification occurs here."""
        admin = await require_platform_permission(
            session=self.session,
            principal=principal,
            permission="subscriptions.documents.issue",
        )
        await self.ready()
        content = await self.retained(payment_id=payment_id)
        latest = await self.session.scalar(
            base_select(SubscriptionDocument)
            .where(SubscriptionDocument.payment_id == payment_id)
            .order_by(SubscriptionDocument.version.desc())
            .limit(1)
        )
        if replaces_id is None and latest is not None:
            return latest
        if replaces_id is not None:
            if latest is not None and latest.replaces_id == replaces_id:
                return latest
            if (
                latest is None
                or latest.id != replaces_id
                or not await self.invalidated(document_id=latest.id)
            ):
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "subscription_document_replacement_requires_invalidated_original"
                    },
                )
            # A documentary replacement cannot authorize a changed amount, period or pricing history.
            preserved = {
                key: value
                for key, value in content.items()
                if key != "period_status_at_issue"
            }
            original = {
                key: value
                for key, value in latest.content.items()
                if key != "period_status_at_issue"
            }
            if preserved != original:
                raise HTTPException(
                    status_code=409,
                    detail={"code": "subscription_document_financial_review_required"},
                )
        name = await self.author_name(admin_id=admin)
        document = SubscriptionDocument(
            public_id=secrets.token_urlsafe(32),
            organization_id=int(content["organization_id"]),
            restaurant_id=int(content["restaurant_id"]),
            payment_id=payment_id,
            subscription_id=int(content["subscription_id"]),
            snapshot_id=int(content["snapshot_id"]),
            version=latest.version + 1 if latest else 1,
            replaces_id=replaces_id,
            content=content,
            sha256=content_digest(content=content),
            author_admin_id=admin,
            author_name=name,
        )
        self.session.add(document)
        await self.session.flush()
        self.session.add(
            SubscriptionDocumentEvent(
                document_id=document.id,
                event="issued",
                author_admin_id=admin,
                author_name=name,
                reason="Verified paid snapshot",
            )
        )
        await self.session.flush()
        logger.info(
            "SaaS document prepared in caller transaction",
            extra={
                "document_id": document.id,
                "payment_id": payment_id,
                "version": document.version,
            },
        )
        return document

    # ==============================================
    # AUDITED INVALIDATION STATE
    # A separate event changes validity without rewriting the issued original or its financial sources.
    # ==============================================

    async def invalidated(self, *, document_id: int) -> bool:
        """Read the retained invalidation fact; absence never implies financial confirmation."""
        return (
            await self.session.scalar(
                base_select(SubscriptionDocumentEvent)
                .with_only_columns(SubscriptionDocumentEvent.id)
                .where(
                    SubscriptionDocumentEvent.document_id == document_id,
                    SubscriptionDocumentEvent.event == "invalidated",
                )
            )
            is not None
        )

    # ==============================================
    # EXPLICIT CONFIRMED INVALIDATION
    # The independent permission and reason are checked even for a repeated request.
    # ==============================================

    async def invalidate(
        self,
        *,
        principal: OIDCPrincipal,
        document_id: int,
        reason: str,
        confirmed: bool,
    ) -> SubscriptionDocument:
        """Append one decision, or reject inconsistent repeats; never refund, suspend or erase anything."""
        admin = await require_platform_permission(
            session=self.session,
            principal=principal,
            permission="subscriptions.documents.invalidate",
        )
        await self.ready()
        if not confirmed or not 3 <= len(reason.strip()) <= 2000:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "subscription_document_reason_and_confirmation_required"
                },
            )
        document = await self.session.scalar(
            base_select(SubscriptionDocument)
            .where(SubscriptionDocument.id == document_id)
            .with_for_update()
        )
        if document is None:
            raise HTTPException(
                status_code=404, detail={"code": "subscription_document_unavailable"}
            )
        existing = await self.session.scalar(
            base_select(SubscriptionDocumentEvent).where(
                SubscriptionDocumentEvent.document_id == document_id,
                SubscriptionDocumentEvent.event == "invalidated",
            )
        )
        if existing is not None:
            if existing.reason != reason.strip() or existing.author_admin_id != admin:
                raise HTTPException(
                    status_code=409,
                    detail={"code": "subscription_document_already_invalidated"},
                )
            return document
        self.session.add(
            SubscriptionDocumentEvent(
                document_id=document_id,
                event="invalidated",
                author_admin_id=admin,
                author_name=await self.author_name(admin_id=admin),
                reason=reason.strip(),
            )
        )
        await self.session.flush()
        logger.info(
            "SaaS invalidation prepared in caller transaction",
            extra={"document_id": document_id, "admin_id": admin},
        )
        return document

    # ==============================================
    # AUTHORIZED DETAILED PROJECTION
    # Callers must first prove tenant consultation or exact platform documentary authority.
    # ==============================================

    async def projection(
        self, *, document: SubscriptionDocument, origin: str, locale: str
    ) -> dict[str, JsonValue]:
        """Return frozen content and current validity, with a read-only QR and retained audit."""
        invalidated = await self.invalidated(document_id=document.id)
        url = public_read_url(
            origin=origin,
            page="verify-saas-document",
            public_id=document.public_id,
            locale=locale,
        )
        events = (
            await self.session.scalars(
                base_select(SubscriptionDocumentEvent)
                .where(SubscriptionDocumentEvent.document_id == document.id)
                .order_by(SubscriptionDocumentEvent.id)
            )
        ).all()
        return {
            "id": document.id,
            "reference": document.public_id,
            "version": document.version,
            "replaces_id": document.replaces_id,
            "state": "invalidated" if invalidated else "valid",
            "issued_at": document.issued_at.isoformat(),
            "issuer": "MoulAI™",
            "content": document.content,
            "sha256": document.sha256,
            "verification_url": url,
            "svg": svg_for_public_url(value=url),
            "events": [
                {
                    "event": event.event,
                    "author": event.author_name,
                    "at": event.occurred_at.isoformat(),
                    "reason": event.reason,
                }
                for event in events
            ],
        }

    # ==============================================
    # MINIMAL NONENUMERABLE PUBLIC VERIFICATION
    # Do not expose tenant, payment, amount, bank evidence, author identity or subscription details.
    # ==============================================

    async def verify(self, *, reference: str) -> dict[str, JsonValue]:
        """Return the approved four verification facts, or one indistinguishable unknown state."""
        await self.ready()
        if not valid_public_id(value=reference):
            return {"state": "unknown"}
        document = await self.session.scalar(
            base_select(SubscriptionDocument).where(
                SubscriptionDocument.public_id == reference
            )
        )
        if document is None:
            return {"state": "unknown"}
        return {
            "reference": document.public_id,
            "issuer": "MoulAI™",
            "issued_at": document.issued_at.isoformat(),
            "state": (
                "invalidated"
                if await self.invalidated(document_id=document.id)
                else "valid"
            ),
        }
