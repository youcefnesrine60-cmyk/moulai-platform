# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MANUAL SUBSCRIPTION CHECKOUT
# Create owned server-priced pending invoices and reuse only compatible pending
# requests.
# ==============================================

"""Coordinate server pricing, pending subscriptions, and manual invoices."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Declare the standard-library, framework and project dependencies used below.
# ==============================================

from datetime import (
    datetime,
    timezone,
)
from typing import (
    TypeAlias,
    TypeVar,
)

from sqlalchemy import (
    Select,
    func,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload
from sqlalchemy.sql.elements import ColumnElement

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.models.base import BaseModel
from app.models.payment import Payment
from app.models.restaurant import Restaurant
from app.models.subscription import (
    Subscription,
    SubscriptionPlan,
)
from app.models.subscription_pricing import SubscriptionPricingSnapshot
from app.repositories.subscription_queries import base_select
from app.schemas.manual_payment import ManualSubscriptionCheckout
from app.schemas.payment import (
    PaymentCreate,
    PaymentResponse,
)
from app.services.business import subscription_metrics
from app.services.business.payment_providers import get_payment_provider
from app.services.business.payment_service import PaymentService
from app.services.business.payment_transaction import payment_transaction
from app.services.business.pricing_service import plan_features
from app.services.business.subscription_service import SubscriptionService
from app.services.business.subscription_types import JsonValue

# ==============================================
# TYPE ALIASES
# Name reusable type contracts to keep signatures consistent.
# ==============================================

CheckoutModel = TypeVar("CheckoutModel", bound=BaseModel)
CheckoutFilter: TypeAlias = ColumnElement[bool]


# ==============================================
# SUBSCRIPTION CHECKOUT SERVICE
# Create owned pending subscriptions and server-priced transfer invoices.
# ==============================================


class SubscriptionCheckoutService:
    """Create owned pending subscriptions and server-priced transfer invoices.

    Restaurant locking serializes concurrent checkouts. Subscription and
    payment services retain ownership of their respective domain writes.
    """

    # ==============================================
    # INIT
    # Bind checkout operations to one async SQLAlchemy billing session.
    # ==============================================

    def __init__(self, *, session: AsyncSession) -> None:
        """Bind checkout operations to one async SQLAlchemy billing session."""

        self.session = session

    # ==============================================
    # BASE SELECT
    # Build a base query for scalar projections or explicit ORM reads.
    # ==============================================

    def _select(self, *, model: type[CheckoutModel]) -> Select[tuple[CheckoutModel]]:
        """Build a base query for scalar projections or explicit ORM reads."""

        return base_select(model)

    # ==============================================
    # COUNT SERVER PRICING INPUTS
    # Count rows using SQL filters supplied by the tenant-scoped checkout.
    # ==============================================

    async def _count(self, model: type[BaseModel], *filters: CheckoutFilter) -> int:
        """Count rows using SQL filters supplied by the tenant-scoped checkout."""

        query = (
            self._select(model=model)
            .with_only_columns(func.count())
            .select_from(model)
            .where(*filters)
        )
        return int((await self.session.execute(query)).scalar_one())

    # ==============================================
    # CREATE OR REUSE PENDING CHECKOUT
    # Return an owned manual invoice using authoritative subscription pricing.
    # ==============================================

    async def create(
        self,
        *,
        owner_id: int,
        data: ManualSubscriptionCheckout,
        replacement_evidence: dict[str, JsonValue] | None = None,
    ) -> PaymentResponse:
        """Return an owned manual invoice using authoritative subscription pricing.

        Exact pending retries reuse their invoice. Other current
        subscriptions or incompatible checkouts fail with a conflict.
        Receipt evidence and settlement remain separate later operations.
        """

        provider = get_payment_provider(method=data.payment_method)
        async with payment_transaction(session=self.session):
            restaurant = (
                await self.session.execute(
                    self._select(model=Restaurant)
                    .with_only_columns(Restaurant.id)
                    .where(
                        Restaurant.id == data.restaurant_id,
                        Restaurant.owner_id == owner_id,
                    )
                    .with_for_update()
                )
            ).scalar_one_or_none()
            if restaurant is None:
                raise NotFoundError(message="Restaurant not found")
            # ==============================================
            # SERVER-SELECTED COUNTRY FOR RETRY AND RENEWAL
            # Compare pending offers against the same validated context used by new quotations.
            # ==============================================

            from app.repositories.subscription_configuration import country_storage_enabled  # isort: skip  # fmt: skip

            applicable_market = data.market
            versioned = await country_storage_enabled(session=self.session)
            if versioned:
                from app.services.business.billing_country import (
                    require_pending_country_context,
                    validated_country_for_subscription,
                )

                country, _decision, _starts = await validated_country_for_subscription(
                    session=self.session,
                    owner_id=owner_id,
                    restaurant_id=restaurant,
                    currency=data.currency,
                )
                if applicable_market is not None and applicable_market != country:
                    raise ValueError("billing_country_market_mismatch")
                applicable_market = country
            plan = (
                await self.session.execute(
                    self._select(model=SubscriptionPlan)
                    .with_only_columns(SubscriptionPlan.id)
                    .where(
                        SubscriptionPlan.id == data.plan_id,
                        SubscriptionPlan.active.is_(True),
                    )
                )
            ).scalar_one_or_none()
            if plan is None:
                raise NotFoundError(message="Subscription plan not found")
            current = (
                (
                    await self.session.execute(
                        self._select(model=Subscription)
                        .options(raiseload("*"))
                        .where(
                            Subscription.restaurant_id == restaurant,
                            Subscription.status.in_(
                                ["pending", "pending_payment", "active", "trial"]
                            ),
                        )
                    )
                )
                .scalars()
                .all()
            )
            if any(s.status in {"pending", "pending_payment"} for s in current):
                pending = [
                    s for s in current if s.status in {"pending", "pending_payment"}
                ]
                if (
                    len(pending) == 1
                    and pending[0].plan_id == data.plan_id
                    and pending[0].billing_cycle == data.billing_cycle
                    and pending[0].currency == data.currency
                    and pending[0].market == applicable_market
                ):
                    invoice = (
                        await self.session.execute(
                            self._select(model=Payment)
                            .options(raiseload("*"))
                            .where(
                                Payment.subscription_id == pending[0].id,
                                Payment.owner_id == owner_id,
                                Payment.status == "pending",
                                Payment.payment_method == data.payment_method,
                                Payment.payment_provider == provider.code,
                            )
                        )
                    ).scalar_one_or_none()
                    if invoice is not None:
                        snapshot = (
                            await self.session.execute(
                                base_select(SubscriptionPricingSnapshot)
                                .with_only_columns(
                                    SubscriptionPricingSnapshot.parameters
                                )
                                .where(
                                    SubscriptionPricingSnapshot.subscription_id
                                    == pending[0].id
                                )
                            )
                        ).scalar_one_or_none()
                        _, _, included = await plan_features(
                            session=self.session, plan_id=data.plan_id
                        )
                        selected = sorted(set(data.additional_feature_ids) - included)
                        if (
                            snapshot is not None
                            and snapshot["additional_feature_ids"] == selected
                        ):
                            if versioned:
                                await require_pending_country_context(
                                    session=self.session, subscription=pending[0]
                                )
                            return PaymentResponse.model_validate(invoice)
                        raise ConflictError(message="Pending checkout features differ")
                raise ConflictError(
                    message="Restaurant already has a current subscription or checkout"
                )

            now = datetime.now(timezone.utc).replace(tzinfo=None)
            _ref, inputs = await subscription_metrics.pricing_inputs(
                session=self.session,
                owner_id=owner_id,
                restaurant_id=restaurant,
                now=now,
            )
            subscriptions = SubscriptionService(session=self.session)
            subscriptions.repo.query_options = [raiseload("*")]
            subscription = await subscriptions.create_pending_subscription(
                owner_id=owner_id,
                restaurant_id=restaurant,
                plan_id=plan,
                billing_cycle=data.billing_cycle,
                payment_method=(
                    "cash" if data.payment_method == "cash" else "electronic"
                ),
                **inputs,
                additional_feature_ids=data.additional_feature_ids,
                currency=data.currency,
                market=data.market,
                replacement_evidence=replacement_evidence,
            )
            amount = subscription["pricing"]["final_amount_due"]
            if amount <= 0:
                raise ValidationError(message="Subscription price must be positive")
            # The subscription owns the canonical amount after rounding to DZD cents.
            stored_amount = (
                await self.session.execute(
                    self._select(model=Subscription)
                    .with_only_columns(Subscription.amount)
                    .where(Subscription.id == subscription["subscription_id"])
                )
            ).scalar_one()
            result = await PaymentService(session=self.session).create_payment(
                payment_data=PaymentCreate(
                    owner_id=owner_id,
                    restaurant_id=restaurant,
                    subscription_id=subscription["subscription_id"],
                    payment_method=data.payment_method,
                    amount=stored_amount,
                )
            )
        return result
