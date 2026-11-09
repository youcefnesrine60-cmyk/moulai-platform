# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# EXPLICIT OWNED OFFER REPLACEMENT
# Preview current server terms and replace only an unpaid offer without evidence.
# ==============================================

"""Retain immutable quotations and payment lineage without moving receipts or funds."""

from __future__ import annotations

# isort: split
# ==============================================
# AUTHORITATIVE DOMAIN DEPENDENCIES
# Reuse pricing, checkout and their transaction; never accept browser amounts.
# ==============================================

import hashlib
import json
from datetime import (
    datetime,
    timezone,
)

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload

from app.core.logger import logger
from app.core.security.oidc import OIDCPrincipal
from app.models.manual_payment import ManualPaymentReceipt
from app.models.payment import Payment
from app.models.restaurant import Restaurant
from app.models.subscription import Subscription
from app.models.subscription_pricing import SubscriptionPricingSnapshot
from app.repositories.subscription_queries import base_select
from app.schemas.manual_payment import ManualSubscriptionCheckout
from app.schemas.payment import PaymentResponse
from app.services.business import subscription_metrics
from app.services.business.billing_country import validated_country_for_subscription
from app.services.business.payment_transaction import payment_transaction
from app.services.business.pricing_service import calculate_subscription_pricing

from app.services.business.subscription_checkout_service import SubscriptionCheckoutService  # isort: skip  # fmt: skip
from app.services.business.subscription_types import JsonValue

# ==============================================
# STABLE REVIEW FINGERPRINT
# Ignore only the diagnostic clock, keeping every monetary and source selection.
# ==============================================


def review_digest(*, value: dict[str, JsonValue]) -> str:
    """Bind confirmation to the displayed amounts, currency, lineage and versions."""
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


# ==============================================
# LOCKED PREVIEW AND EXPLICIT CONFIRMATION
# Scope all reads before returning terms; preserve evidence-bearing cases for administration.
# ==============================================


async def replace_offer(
    *,
    session: AsyncSession,
    owner_id: int,
    restaurant_id: int,
    payment_id: int,
    currency: str,
    principal: OIDCPrincipal,
    approval: str | None = None,
) -> dict[str, JsonValue]:
    """Preview without writes or atomically supersede after exact explicit approval.

    The enclosing HTTP adapter verifies owner membership and checkout permission.
    Restaurant then payment locks serialize checkout and receipt races. A repeated
    confirmation returns the retained successor, never another invoice. Receipts,
    paid timestamps, references, cash and nonpending funds always block replacement.
    """
    async with payment_transaction(session=session):
        restaurant = await session.scalar(
            base_select(Restaurant)
            .with_only_columns(Restaurant.id)
            .where(Restaurant.id == restaurant_id, Restaurant.owner_id == owner_id)
            .with_for_update()
        )
        if restaurant is None:
            raise ValueError("offer_unavailable")
        payment = await session.scalar(
            base_select(Payment)
            .options(raiseload("*"))
            .where(
                Payment.id == payment_id,
                Payment.owner_id == owner_id,
                Payment.restaurant_id == restaurant_id,
            )
            .with_for_update()
        )
        if payment is None:
            raise ValueError("offer_unavailable")
        successor = await session.scalar(
            base_select(SubscriptionPricingSnapshot).where(
                SubscriptionPricingSnapshot.owner_id == owner_id,
                SubscriptionPricingSnapshot.restaurant_id == restaurant_id,
                SubscriptionPricingSnapshot.parameters["replacement"][
                    "payment_id"
                ].as_integer()
                == payment_id,
            )
        )
        if successor is not None:
            evidence = successor.parameters["replacement"]
            if (
                approval != evidence["approval"]
                or principal.subject != evidence["subject"]
            ):
                raise ValueError("offer_already_replaced")
            result = await session.scalar(
                base_select(Payment)
                .options(raiseload("*"))
                .where(
                    Payment.subscription_id == successor.subscription_id,
                    Payment.owner_id == owner_id,
                    Payment.restaurant_id == restaurant_id,
                )
            )
            if result is None:
                raise ValueError("offer_replacement_integrity_failure")
            return {
                "payment": PaymentResponse.model_validate(result).model_dump(
                    mode="json"
                ),
                "reused": True,
            }
        subscription = await session.scalar(
            base_select(Subscription)
            .options(raiseload("*"))
            .where(
                Subscription.id == payment.subscription_id,
                Subscription.owner_id == owner_id,
                Subscription.restaurant_id == restaurant_id,
            )
            .with_for_update()
        )
        if subscription is None or subscription.status not in {
            "pending",
            "pending_payment",
        }:
            raise ValueError("offer_not_pending")
        receipt = await session.scalar(
            base_select(ManualPaymentReceipt)
            .with_only_columns(ManualPaymentReceipt.id)
            .where(ManualPaymentReceipt.payment_id == payment_id)
        )
        if (
            receipt is not None
            or payment.status != "pending"
            or payment.paid_at is not None
            or payment.external_reference
            or payment.payment_method not in {"ccp", "baridimob"}
        ):
            raise ValueError("offer_financial_evidence_requires_administration")
        snapshot = await session.scalar(
            base_select(SubscriptionPricingSnapshot).where(
                SubscriptionPricingSnapshot.subscription_id == subscription.id,
                SubscriptionPricingSnapshot.owner_id == owner_id,
                SubscriptionPricingSnapshot.restaurant_id == restaurant_id,
            )
        )
        if snapshot is None:
            raise ValueError("offer_history_missing")
        country, decision, _start = await validated_country_for_subscription(
            session=session,
            owner_id=owner_id,
            restaurant_id=restaurant_id,
            currency=currency,
        )
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        # Metrics may stage an active-month snapshot. A preview must not persist it.
        # The outer ownership locks remain held when this nested measurement rolls back.
        async with session.begin_nested() as measurement:
            _reference, inputs = await subscription_metrics.pricing_inputs(
                session=session, owner_id=owner_id, restaurant_id=restaurant_id, now=now
            )
            pricing = await calculate_subscription_pricing(
                session=session,
                plan_id=subscription.plan_id,
                billing_cycle=subscription.billing_cycle,
                payment_method="electronic",
                currency=currency,
                country_code=country,
                market=country,
                now=now,
                additional_feature_ids=snapshot.parameters["additional_feature_ids"],
                owner_id=owner_id,
                restaurant_id=restaurant_id,
                **inputs,
            )
            if approval is None:
                await measurement.rollback()
        parameters = dict(pricing["parameters"])
        parameters.pop("calculation_time", None)
        parameters["billing_country_decision_id"] = decision
        reasons = []
        for field in (
            "base_revision",
            "billing_country_decision_id",
            "payment_adjustment_rates",
        ):
            if snapshot.parameters.get(field) != parameters.get(field):
                reasons.append(field)
        if not reasons and currency == subscription.currency:
            raise ValueError("offer_not_obsolete")
        reviewed = subscription_metrics.json_evidence(
            value={
                "payment_id": payment_id,
                "subscription_id": subscription.id,
                "currency": currency,
                "pricing": pricing["exact"],
                "parameters": parameters,
                "reasons": reasons,
            }
        )
        digest = review_digest(value=reviewed)
        if approval is None:
            return {"review": reviewed, "approval": digest, "reused": False}
        if approval != digest:
            raise ValueError("offer_preview_changed_review_again")
        # Nothing with financial evidence reaches this explicit supersession.
        # Retain both old rows and their prices; only withdraw their pending state.
        subscription.status = "cancelled"
        payment.status = "cancelled"
        await session.flush()
        evidence = {
            "payment_id": payment_id,
            "subscription_id": subscription.id,
            "approval": approval,
            "subject": principal.subject,
            "issuer": principal.issuer,
            "confirmed_at": now.isoformat(),
        }
        result = await SubscriptionCheckoutService(session=session).create(
            owner_id=owner_id,
            data=ManualSubscriptionCheckout(
                restaurant_id=restaurant_id,
                plan_id=subscription.plan_id,
                billing_cycle=subscription.billing_cycle,
                payment_method=payment.payment_method,
                currency=currency,
                additional_feature_ids=snapshot.parameters["additional_feature_ids"],
            ),
            replacement_evidence=evidence,
        )
        created = await session.scalar(
            base_select(SubscriptionPricingSnapshot).where(
                SubscriptionPricingSnapshot.subscription_id == result.subscription_id
            )
        )
        if created is None:
            raise ValueError("offer_replacement_integrity_failure")
        actual = dict(created.parameters)
        actual.pop("calculation_time", None)
        actual.pop("replacement", None)
        if actual != parameters or created.pricing.get("exact") != pricing["exact"]:
            raise ValueError("offer_preview_changed_review_again")
        logger.info(
            "Offer replacement staged in caller transaction",
            extra={"old_payment_id": payment_id, "new_payment_id": result.id},
        )
        return {"payment": result.model_dump(mode="json"), "reused": False}
