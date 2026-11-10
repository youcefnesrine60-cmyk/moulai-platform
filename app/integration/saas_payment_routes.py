# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# LOCAL OWNED SAAS TRANSFER WORKFLOW
# Connect the existing checkout, private receipt and independent funds review without creating a banking integration.
# ==============================================

"""Synthetic local receipt evidence only; no remote payment, notification or inferred financial permission."""

from __future__ import annotations

# isort: split
# ==============================================
# AUTHENTICATED REQUEST CONTRACTS
# Browser-selected amounts, owners and administrator IDs are never accepted by checkout routes.
# ==============================================

from typing import Literal

from fastapi import (
    FastAPI,
    HTTPException,
    Request,
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
from app.models.manual_payment import ManualPaymentReceipt
from app.models.payment import Payment
from app.models.restaurant import Restaurant
from app.models.subscription import Subscription
from app.models.subscription_pricing import SubscriptionPricingSnapshot
from app.repositories.restaurant_context import company_column
from app.repositories.subscription_queries import base_select
from app.schemas.manual_payment import (
    ManualPaymentReview,
    ManualSubscriptionCheckout,
)
from app.services.business.manual_payment_service import ManualPaymentService
from app.services.business.platform_authority import require_platform_permission

from app.services.business.subscription_checkout_service import SubscriptionCheckoutService  # isort: skip  # fmt: skip
from app.services.business.tenant_access import TenantAccessService

# ==============================================
# CLOSED CHECKOUT SELECTION
# The restaurant comes from the authorized route and every payable value comes from the shared pricing engine.
# ==============================================


class SaaSCheckoutInput(BaseModel):
    """Select a current plan and transfer method, without any amount or trusted identity field."""

    model_config = ConfigDict(extra="forbid")
    plan_id: int = Field(strict=True, gt=0)
    billing_cycle: Literal["monthly", "quarterly", "semiannual", "yearly"]
    payment_method: Literal["ccp", "baridimob"]
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    additional_feature_ids: list[int] = Field(default_factory=list, max_length=100)


# ==============================================
# EXPLICIT REVIEW CONFIRMATION
# Only a displayed server digest authorizes replacement; no browser price is trusted.
# ==============================================


class OfferReplacementInput(BaseModel):
    """Preview by currency, then explicitly confirm the exact reviewed terms."""

    model_config = ConfigDict(extra="forbid")
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    approval: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


# ==============================================
# LOCAL HTTP COMPOSITION
# Reuse tenant authority for owner actions and the separate platform payments.review grant for decisions.
# ==============================================


def mount_saas_payment_routes(
    *, app: FastAPI, identity_dep: Depends, session_dep: Depends
) -> None:
    """Expose persisted terms and evidence, never a claim that a transfer was received automatically."""

    # ==============================================
    # OWNER-REVIEWED REPLACEMENT
    # Recheck the same tenant scope and dedicated checkout grant on both phases.
    # ==============================================

    @app.post(
        "/api/web/organizations/{organization_id}/restaurants/{restaurant_id}/saas-payments/{payment_id}/replacement"
    )
    async def replacement(
        organization_id: int,
        restaurant_id: int,
        payment_id: int,
        data: OfferReplacementInput,
        person: BrowserIdentity = identity_dep,
        session: AsyncSession = session_dep,
    ) -> dict[str, JsonValue]:
        """Preview or confirm without transferring receipts, cash or declared funds."""
        from app.services.business.subscription_requote import replace_offer

        async with TenantAccessService(session=session).authorized(
            principal=person.principal,
            organization_id=organization_id,
            permission="tenant.billing.checkout",
        ) as unit:
            await unit.restaurant(restaurant_id=restaurant_id)
            if unit.context.role_code != "owner":
                raise HTTPException(status_code=403, detail="Owner authority required")
            owner = await session.scalar(
                base_select(Restaurant)
                .with_only_columns(Restaurant.owner_id)
                .where(
                    Restaurant.id == restaurant_id, company_column() == organization_id
                )
            )
            if owner is None:
                raise HTTPException(status_code=404, detail="Establishment unavailable")
            return await replace_offer(
                session=session,
                owner_id=owner,
                restaurant_id=restaurant_id,
                payment_id=payment_id,
                currency=data.currency,
                principal=person.principal,
                approval=data.approval,
            )

    # ==============================================
    # OWN TRANSFER TERMS
    # Financial consultation is scoped to the current company and establishment on every request.
    # ==============================================

    @app.get(
        "/api/web/organizations/{organization_id}/restaurants/{restaurant_id}/saas-payments"
    )
    async def payments(
        organization_id: int,
        restaurant_id: int,
        person: BrowserIdentity = identity_dep,
        session: AsyncSession = session_dep,
    ) -> list[dict[str, JsonValue]]:
        """Read bounded owned payments and receipt states; do not expose private receipt bytes."""
        async with TenantAccessService(session=session).authorized(
            principal=person.principal,
            organization_id=organization_id,
            permission="tenant.billing.read",
        ) as unit:
            await unit.restaurant(restaurant_id=restaurant_id)
            rows = (
                await session.execute(
                    base_select(Payment)
                    .with_only_columns(
                        Payment.id,
                        Payment.subscription_id,
                        Payment.amount,
                        Payment.currency,
                        Payment.status,
                        Payment.payment_method,
                        ManualPaymentReceipt.review_status,
                        SubscriptionPricingSnapshot.parameters,
                        SubscriptionPricingSnapshot.pricing,
                        Subscription.starts_at,
                        Subscription.expires_at,
                        Subscription.status.label("subscription_status"),
                    )
                    .outerjoin(
                        ManualPaymentReceipt,
                        ManualPaymentReceipt.payment_id == Payment.id,
                    )
                    .join(Subscription, Subscription.id == Payment.subscription_id)
                    .outerjoin(
                        SubscriptionPricingSnapshot,
                        SubscriptionPricingSnapshot.subscription_id == Subscription.id,
                    )
                    .where(
                        Payment.restaurant_id == restaurant_id,
                        Payment.subscription_id.is_not(None),
                    )
                    .order_by(Payment.id.desc())
                    .limit(50)
                )
            ).all()
            return [
                {
                    "id": row.id,
                    "subscription_id": row.subscription_id,
                    "amount": str(row.amount),
                    "currency": row.currency,
                    "status": row.status,
                    "method": row.payment_method,
                    "receipt_status": row.review_status,
                    "subscription_status": row.subscription_status,
                    "retained_country": (row.parameters or {})
                    .get("base_selection", {})
                    .get("country_code"),
                    "retained_B": (row.parameters or {}).get("B"),
                    "retained_rate": (row.parameters or {}).get(
                        "payment_adjustment_rate"
                    ),
                    "retained_pre_payment": (row.pricing or {})
                    .get("exact", {})
                    .get("final_price"),
                    "starts_at": row.starts_at.isoformat() if row.starts_at else None,
                    "expires_at": (
                        row.expires_at.isoformat() if row.expires_at else None
                    ),
                    "synthetic_local": True,
                }
                for row in rows
            ]

    @app.post(
        "/api/web/organizations/{organization_id}/restaurants/{restaurant_id}/saas-payments"
    )
    async def checkout(
        organization_id: int,
        restaurant_id: int,
        data: SaaSCheckoutInput,
        person: BrowserIdentity = identity_dep,
        session: AsyncSession = session_dep,
    ) -> dict[str, JsonValue]:
        """Create or reuse a server-priced pending invoice; this never activates service."""
        async with TenantAccessService(session=session).authorized(
            principal=person.principal,
            organization_id=organization_id,
            permission="tenant.billing.checkout",
        ) as unit:
            await unit.restaurant(restaurant_id=restaurant_id)
            if unit.context.role_code != "owner":
                raise HTTPException(status_code=403, detail="Owner authority required")
            owner = await session.scalar(
                base_select(Restaurant)
                .with_only_columns(Restaurant.owner_id)
                .where(
                    Restaurant.id == restaurant_id,
                    company_column() == organization_id,
                )
            )
            if owner is None:
                raise HTTPException(status_code=404, detail="Establishment unavailable")
            result = await SubscriptionCheckoutService(session=session).create(
                owner_id=owner,
                data=ManualSubscriptionCheckout(
                    restaurant_id=restaurant_id, **data.model_dump()
                ),
            )
            return result.model_dump(mode="json")

    # ==============================================
    # PRIVATE SYNTHETIC TRANSFER EVIDENCE
    # Upload does not verify funds; any decline or failed activation preserves the existing receipt and its history.
    # ==============================================

    @app.post(
        "/api/web/organizations/{organization_id}/restaurants/{restaurant_id}/saas-payments/{payment_id}/receipt"
    )
    async def receipt(
        organization_id: int,
        restaurant_id: int,
        payment_id: int,
        request: Request,
        reference: str,
        synthetic: bool,
        person: BrowserIdentity = identity_dep,
        session: AsyncSession = session_dep,
    ) -> dict[str, JsonValue]:
        """Bound the stream before storing evidence; require the owner and exact receipt-submission permission."""
        if synthetic is not True:
            raise HTTPException(
                status_code=409, detail="Synthetic local proof required"
            )
        content = bytearray()
        async for chunk in request.stream():
            if len(content) + len(chunk) > 2 * 1024 * 1024:
                raise HTTPException(status_code=413, detail="Receipt too large")
            content.extend(chunk)
        async with TenantAccessService(session=session).authorized(
            principal=person.principal,
            organization_id=organization_id,
            permission="tenant.receipts.submit",
        ) as unit:
            await unit.restaurant(restaurant_id=restaurant_id)
            if unit.context.role_code != "owner":
                raise HTTPException(status_code=403, detail="Owner authority required")
            owner = await session.scalar(
                base_select(Payment)
                .with_only_columns(Payment.owner_id)
                .where(Payment.id == payment_id, Payment.restaurant_id == restaurant_id)
            )
            if owner is None:
                raise HTTPException(status_code=404, detail="Payment unavailable")
            result = await ManualPaymentService(session=session).submit_receipt(
                payment_id=payment_id,
                owner_id=owner,
                transaction_reference=reference,
                content=bytes(content),
                media_type=request.headers.get("content-type", ""),
            )
            return result.model_dump(mode="json")

    # ==============================================
    # INDEPENDENT PLATFORM FUNDS REVIEW
    # A country validator or pricing administrator has no implicit right to confirm a transfer.
    # ==============================================

    @app.get("/api/web/platform/saas-payments")
    async def review_queue(
        person: BrowserIdentity = identity_dep, session: AsyncSession = session_dep
    ) -> list[dict[str, JsonValue]]:
        """Read bounded actual invoice states under the current exact payment-review grant."""
        async with session.begin():
            await require_platform_permission(
                session=session,
                principal=person.principal,
                permission="payments.review",
            )
            rows = (
                await session.execute(
                    base_select(Payment)
                    .with_only_columns(
                        Payment.id,
                        Payment.amount,
                        Payment.currency,
                        Payment.status,
                        Restaurant.name,
                        ManualPaymentReceipt.review_status,
                        ManualPaymentReceipt.transaction_reference,
                    )
                    .join(Restaurant, Restaurant.id == Payment.restaurant_id)
                    .outerjoin(
                        ManualPaymentReceipt,
                        ManualPaymentReceipt.payment_id == Payment.id,
                    )
                    .where(
                        Payment.payment_provider == "manual_transfer",
                        Payment.subscription_id.is_not(None),
                    )
                    .order_by(Payment.id.desc())
                    .limit(100)
                )
            ).all()
            return [
                {
                    "id": row.id,
                    "restaurant_name": row.name,
                    "amount": str(row.amount),
                    "currency": row.currency,
                    "status": row.status,
                    "receipt_status": row.review_status,
                    "reference": row.transaction_reference,
                    "synthetic_local": True,
                }
                for row in rows
            ]

    @app.post("/api/web/platform/saas-payments/{payment_id}/review")
    async def review(
        payment_id: int,
        data: ManualPaymentReview,
        person: BrowserIdentity = identity_dep,
        session: AsyncSession = session_dep,
    ) -> dict[str, JsonValue]:
        """Verify declared synthetic funds facts separately, then atomically reuse the existing settlement service."""
        async with session.begin():
            admin = await require_platform_permission(
                session=session,
                principal=person.principal,
                permission="payments.review",
            )
            result = await ManualPaymentService(session=session).review(
                payment_id=payment_id, admin_id=admin, data=data
            )
            return result.model_dump(mode="json")
