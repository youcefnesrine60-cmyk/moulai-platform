# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Coordinate server pricing, pending subscriptions, and manual invoices."""

# ==============================================
# IMPORTS
# ==============================================

from datetime import (
    datetime,
    timedelta,
    timezone,
)
from typing import (
    TypeAlias,
    TypeVar,
)

from sqlalchemy import (
    Select,
    func,
    select,
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
from app.models.branch import Branch
from app.models.category import Category
from app.models.order import Order
from app.models.owner import Owner
from app.models.payment import Payment
from app.models.product import Product
from app.models.restaurant import Restaurant
from app.models.subscription import (
    Subscription,
    SubscriptionPlan,
)
from app.schemas.manual_payment import ManualSubscriptionCheckout
from app.schemas.payment import (
    PaymentCreate,
    PaymentResponse,
)
from app.services.business.payment_providers import get_payment_provider
from app.services.business.payment_service import PaymentService
from app.services.business.payment_transaction import payment_transaction
from app.services.business.subscription_service import SubscriptionService

# ==============================================
# TYPE ALIASES
# ==============================================

CheckoutModel = TypeVar("CheckoutModel", bound=BaseModel)
CheckoutFilter: TypeAlias = ColumnElement[bool]


# ==============================================
# SUBSCRIPTION CHECKOUT SERVICE
# ==============================================


class SubscriptionCheckoutService:
    """Create owned pending subscriptions and server-priced transfer invoices.

    Restaurant locking serializes concurrent checkouts. Subscription and
    payment services retain ownership of their respective domain writes.
    """

    # ==========================================
    # INIT
    # ==========================================

    def __init__(self, *, session: AsyncSession) -> None:
        """Bind checkout operations to one async SQLAlchemy billing session."""

        self.session = session

    # ==========================================
    # BASE SELECT
    # ==========================================

    def _select(self, model: type[CheckoutModel]) -> Select[tuple[CheckoutModel]]:
        """Build a base query for scalar projections or explicit ORM reads."""

        return select(model)

    # ==========================================
    # COUNT SERVER PRICING INPUTS
    # ==========================================

    async def _count(self, model: type[BaseModel], *filters: CheckoutFilter) -> int:
        """Count rows using SQL filters supplied by the tenant-scoped checkout."""

        query = (
            self._select(model)
            .with_only_columns(func.count())
            .select_from(model)
            .where(*filters)
        )
        return int((await self.session.execute(query)).scalar_one())

    # ==========================================
    # CREATE OR REUSE PENDING CHECKOUT
    # ==========================================

    async def create(
        self, *, owner_id: int, data: ManualSubscriptionCheckout
    ) -> PaymentResponse:
        """Return an owned manual invoice using authoritative subscription pricing.

        Exact pending retries reuse their invoice. Other current
        subscriptions or incompatible checkouts fail with a conflict.
        Receipt evidence and settlement remain separate later operations.
        """

        get_payment_provider(method=data.payment_method)
        async with payment_transaction(session=self.session):
            restaurant = (
                await self.session.execute(
                    self._select(Restaurant)
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
            plan = (
                await self.session.execute(
                    self._select(SubscriptionPlan)
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
                        self._select(Subscription)
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
            if current:
                pending = [
                    s for s in current if s.status in {"pending", "pending_payment"}
                ]
                if (
                    len(pending) == 1
                    and pending[0].plan_id == data.plan_id
                    and pending[0].billing_cycle == data.billing_cycle
                ):
                    invoice = (
                        await self.session.execute(
                            self._select(Payment)
                            .options(raiseload("*"))
                            .where(
                                Payment.subscription_id == pending[0].id,
                                Payment.owner_id == owner_id,
                                Payment.status == "pending",
                                Payment.payment_method == data.payment_method,
                                Payment.payment_provider == "manual_transfer",
                            )
                        )
                    ).scalar_one_or_none()
                    if invoice is not None:
                        return PaymentResponse.model_validate(invoice)
                raise ConflictError(
                    message="Restaurant already has a current subscription or checkout"
                )

            now = datetime.now(timezone.utc).replace(tzinfo=None)
            created_at = (
                await self.session.execute(
                    self._select(Owner)
                    .with_only_columns(Owner.created_at)
                    .where(Owner.id == owner_id)
                )
            ).scalar_one()
            if created_at.tzinfo is not None:
                created_at = created_at.astimezone(timezone.utc).replace(tzinfo=None)
            average = (
                await self.session.execute(
                    self._select(Order)
                    .with_only_columns(func.avg(Order.total_amount))
                    .where(
                        Order.restaurant_id == restaurant, Order.status == "completed"
                    )
                )
            ).scalar_one() or 0
            subscriptions = SubscriptionService(session=self.session)
            subscriptions.repo.query_options = [raiseload("*")]
            subscription = await subscriptions.create_pending_subscription(
                owner_id=owner_id,
                restaurant_id=restaurant,
                plan_id=plan,
                billing_cycle=data.billing_cycle,
                payment_method="electronic",
                restaurants_count=await self._count(
                    Restaurant, Restaurant.owner_id == owner_id
                ),
                branches_count=await self._count(
                    Branch, Branch.restaurant_id == restaurant
                ),
                products_count=await self._count(
                    Product, Product.restaurant_id == restaurant
                ),
                categories_count=await self._count(
                    Category, Category.restaurant_id == restaurant
                ),
                monthly_orders=await self._count(
                    Order,
                    Order.restaurant_id == restaurant,
                    Order.created_at >= now - timedelta(days=30),
                ),
                years_with_platform=max(0, (now - created_at).days // 365),
                average_order_value=float(average),
            )
            amount = subscription["pricing"]["final_amount_due"]
            if amount <= 0:
                raise ValidationError(message="Subscription price must be positive")
            # The subscription owns the canonical amount after rounding to DZD cents.
            stored_amount = (
                await self.session.execute(
                    self._select(Subscription)
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
