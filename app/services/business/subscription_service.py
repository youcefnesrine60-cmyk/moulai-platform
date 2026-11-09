# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# SUBSCRIPTION BUSINESS SERVICE
# Coordinate owned trial, quotation and paid-service lifecycle operations and their
# evidence.
# ==============================================

"""Coordinate owned trial, quotation and paid-service lifecycle operations and their evidence."""

from __future__ import annotations

# isort: split
# ==============================================
# 💳 SUBSCRIPTION SERVICE
# Business Logic Layer - منطق الأعمال للاشتراكات
#
# - إنشاء الاشتراك التجريبي (trial)
# - إنشاء الاشتراك المدفوع (monthly, yearly)
# - تفعيل/إلغاء/انتهاء الاشتراك
# - حساب تاريخ الانتهاء
# - منع تكرار التجربة المجانية
#
# Async SQLAlchemy Version
# ==============================================

from datetime import (
    datetime,
    timedelta,
    timezone,
)
from decimal import Decimal
from typing import (
    Any,
    TypeAlias,
)

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload

from app.core.logger import logger
from app.models.owner import Owner
from app.models.payment import Payment
from app.models.restaurant import Restaurant
from app.models.subscription import (
    Feature,
    Subscription,
    SubscriptionFeature,
    SubscriptionFeatureRequest,
    SubscriptionPlan,
)
from app.models.subscription_pricing import SubscriptionPricingSnapshot
from app.repositories.owner_repo import OwnerRepository
from app.services.business import subscription_metrics
from app.services.business.payment_transaction import payment_transaction
from app.services.business.pricing_service import plan_features
from app.services.business.subscription_reminders import reminder_configuration

from app.repositories.subscription_feature_requests_repo import SubscriptionFeatureRequestRepository  # isort: skip  # fmt: skip
from app.repositories.subscription_features_repo import SubscriptionFeatureRepository
from app.repositories.subscription_plan_repo import SubscriptionPlanRepository
from app.repositories.subscription_queries import base_select
from app.repositories.subscription_repo import SubscriptionRepository
from app.services.business.pricing_service import calculate_subscription_pricing
from app.services.business.subscription_types import (
    JsonValue,
    NumericInput,
    PricingResult,
    SubscriptionResult,
)

# ==============================================
# 🧩 TYPES
# Describe shared input, update and result structures for this module.
# ==============================================

SubscriptionList: TypeAlias = list[Subscription]


# ==============================================
# 💳 SUBSCRIPTION SERVICE
# خدمة الاشتراكات.
# ==============================================


class SubscriptionService:
    """
    خدمة الاشتراكات.

    مسؤولة عن:
        - إنشاء وإدارة الاشتراكات (تجريبي ومدفوع)
        - تفعيل وإلغاء الاشتراكات
        - حساب التسعير
        - التحقق من صلاحية الاشتراكات

    Attributes:
        session: جلسة قاعدة البيانات غير المتزامنة
        repo: مستودع الاشتراكات
        plan_repo: مستودع خطط الاشتراك
        owner_repo: مستودع المالكين
    """

    # ==============================================
    # INIT
    # تهيئة خدمة الاشتراكات.
    # ==============================================

    def __init__(
        self,
        *,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة خدمة الاشتراكات.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        self.session = session
        self.repo = SubscriptionRepository(session=session)
        self.plan_repo = SubscriptionPlanRepository(session=session)
        self.owner_repo = OwnerRepository(session=session)

    # ==============================================
    # 📖 QUERIES
    # Read persisted records through the existing repository selection rules.
    # ==============================================

    # ==============================================
    # ACTIVATE FOR VERIFIED PAYMENT
    # Activate or schedule purchased calendar coverage, only after verified settlement.
    # ==============================================

    async def activate_for_verified_payment(self, *, payment: Payment) -> None:
        """Activate or schedule purchased calendar coverage, only after verified settlement."""
        if payment.status != "paid" or not self.session.info.get(
            "defer_repository_commit"
        ):
            raise ValueError("verified_payment_transaction_required")
        if not payment.subscription_id or payment.paid_at is None:
            raise ValueError("payment_settlement_date_required")
        await self.session.execute(
            base_select(Restaurant)
            .with_only_columns(Restaurant.id)
            .where(Restaurant.id == payment.restaurant_id)
            .with_for_update()
        )
        sub = (
            await self.session.execute(
                base_select(Subscription)
                .options(raiseload("*"))
                .where(Subscription.id == payment.subscription_id)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if sub is None:
            raise ValueError("subscription_not_found")
        if (
            sub.owner_id != payment.owner_id
            or sub.restaurant_id != payment.restaurant_id
        ):
            raise ValueError("payment_subscription_scope_mismatch")
        if Decimal(str(sub.amount)) != Decimal(str(payment.amount)):
            raise ValueError("payment_subscription_amount_mismatch")
        if sub.status not in {"pending", "pending_payment", "active", "scheduled"}:
            raise ValueError("subscription_not_pending")
        from app.services.business.subscription_calendar import add_months
        from app.services.business.subscription_contract import SERVICE_MONTHS
        from app.services.business.subscription_reminders import schedule

        if sub.billing_cycle not in SERVICE_MONTHS:
            raise ValueError("unsupported_billing_cycle")
        if sub.status in {"pending", "pending_payment"}:
            from app.repositories.subscription_configuration import country_storage_enabled  # isort: skip  # fmt: skip

            if await country_storage_enabled(session=self.session):
                from app.services.business.billing_country import require_pending_country_context  # isort: skip  # fmt: skip

                await require_pending_country_context(
                    session=self.session, subscription=sub
                )
            await self.session.execute(
                base_select(Restaurant)
                .with_only_columns(Restaurant.id)
                .where(Restaurant.id == sub.restaurant_id)
                .with_for_update()
            )
            paid_at = subscription_metrics.utc(value=payment.paid_at)
            previous = (
                (
                    await self.session.execute(
                        base_select(Subscription)
                        .options(raiseload("*"))
                        .where(
                            Subscription.restaurant_id == sub.restaurant_id,
                            Subscription.id != sub.id,
                            Subscription.status.in_(["active", "trial", "scheduled"]),
                            Subscription.expires_at.is_not(None),
                        )
                        .order_by(Subscription.expires_at.desc())
                        .with_for_update()
                    )
                )
                .scalars()
                .all()
            )
            latest = previous[0] if previous else None
            starts = max(paid_at, latest.expires_at) if latest else paid_at
            anchor = (
                (latest.calendar_anchor or latest.starts_at)
                if latest and latest.expires_at >= paid_at
                else starts
            )
            sub.calendar_anchor = anchor
            sub.starts_at = starts
            sub.expires_at = add_months(
                start=starts,
                months=SERVICE_MONTHS[sub.billing_cycle],
                anchor_day=anchor.day,
            )
            sub.status = "scheduled" if starts > paid_at else "active"
            if sub.status == "active":
                for old in previous:
                    if old.expires_at <= starts:
                        old.status = "expired"
            await self.session.flush()
        features = SubscriptionFeatureRepository(self.session)
        requests = SubscriptionFeatureRequestRepository(self.session)
        features.query_options = [raiseload("*")]
        requests.query_options = [raiseload("*")]
        for request in await requests.get_by_subscription(subscription_id=sub.id):
            await features.create_subscription_feature(
                subscription_id=sub.id, feature_id=request.feature_id
            )
        await requests.delete_by_subscription(subscription_id=sub.id)
        await schedule(session=self.session, subscription=sub)

    # ==============================================
    # GET BY ID
    # الحصول على اشتراك بالمعرف.
    # ==============================================

    async def get_by_id(
        self,
        *,
        subscription_id: int,
    ) -> Subscription | None:
        """
        الحصول على اشتراك بالمعرف.

        Args:
            subscription_id: معرف الاشتراك

        Returns:
            كائن Subscription أو None
        """
        logger.info(
            "subscription_service_get_by_id",
            extra={"subscription_id": subscription_id},
        )

        return await self.repo.get_by_id(
            id=subscription_id,
        )

    # ==============================================
    # GET BY RESTAURANT
    # الحصول على اشتراكات مطعم معين.
    # ==============================================

    async def get_by_restaurant(
        self,
        *,
        restaurant_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> SubscriptionList:
        """
        الحصول على اشتراكات مطعم معين.

        Args:
            restaurant_id: معرف المطعم
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة الاشتراكات
        """
        logger.info(
            "subscription_service_get_by_restaurant",
            extra={
                "restaurant_id": restaurant_id,
                "skip": skip,
                "limit": limit,
            },
        )

        return await self.repo.get_by_restaurant_id(
            restaurant_id=restaurant_id,
            skip=skip,
            limit=limit,
        )

    # ==============================================
    # GET ACTIVE BY RESTAURANT
    # الحصول على الاشتراك النشط لمطعم معين.
    # ==============================================

    async def get_active_by_restaurant(
        self,
        *,
        restaurant_id: int,
    ) -> Subscription | None:
        """
        الحصول على الاشتراك النشط لمطعم معين.

        Args:
            restaurant_id: معرف المطعم

        Returns:
            كائن Subscription أو None
        """
        logger.info(
            "subscription_service_get_active_by_restaurant",
            extra={"restaurant_id": restaurant_id},
        )

        return await self.repo.get_active_by_restaurant(
            restaurant_id=restaurant_id,
        )

    # ==============================================
    # GET BY OWNER
    # الحصول على اشتراكات مالك معين.
    # ==============================================

    async def get_by_owner(
        self,
        *,
        owner_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> SubscriptionList:
        """
        الحصول على اشتراكات مالك معين.

        Args:
            owner_id: معرف المالك
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة الاشتراكات
        """
        logger.info(
            "subscription_service_get_by_owner",
            extra={
                "owner_id": owner_id,
                "skip": skip,
                "limit": limit,
            },
        )

        return await self.repo.get_by_owner_id(
            owner_id=owner_id,
            skip=skip,
            limit=limit,
        )

    # ==============================================
    # GET BY STATUS
    # الحصول على اشتراكات حسب الحالة.
    # ==============================================

    async def get_by_status(
        self,
        *,
        status: str,
        skip: int = 0,
        limit: int = 100,
    ) -> SubscriptionList:
        """
        الحصول على اشتراكات حسب الحالة.

        Args:
            status: حالة الاشتراك (trial, active, expired, cancelled)
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة الاشتراكات
        """
        logger.info(
            "subscription_service_get_by_status",
            extra={
                "status": status,
                "skip": skip,
                "limit": limit,
            },
        )

        return await self.repo.get_all(
            skip=skip,
            limit=limit,
            filters={"status": status},
            order_by="created_at",
            descending=True,
        )

    # ==============================================
    # GET PLAN BY CODE
    # الحصول على خطة اشتراك بواسطة الكود.
    # ==============================================

    async def get_plan_by_code(
        self,
        *,
        code: str,
    ) -> dict[str, Any] | None:
        """
        الحصول على خطة اشتراك بواسطة الكود.

        Args:
            code: كود الخطة (trial, basic, pro, enterprise)

        Returns:
            قاموس بيانات الخطة أو None
        """
        logger.info(
            "subscription_service_get_plan_by_code",
            extra={"plan_code": code},
        )

        plan = await self.plan_repo.get_by_code(code=code)

        if not plan:
            return None

        from app.repositories.subscription_configuration import country_storage_enabled

        # O3 keeps the old plan column solely for physical compatibility. An
        # unscoped plan read cannot present it as a binding country-specific B.
        country_quotation_required = await country_storage_enabled(session=self.session)

        return {
            "id": plan.id,
            "code": plan.code,
            "name": plan.name,
            "description": plan.description,
            "base_price": (
                None if country_quotation_required else float(plan.base_price)
            ),
            "base_price_requires_country_quotation": country_quotation_required,
            "plan_discount_percent": float(plan.plan_discount_percent),
            "active": plan.active,
        }

    # ==============================================
    # ✏️ MUTATIONS
    # Group persistence changes while retaining the caller's transaction contract.
    # ==============================================

    # ==============================================
    # TRIAL CONFIGURATION BEFORE DOMAIN WRITES
    # Lock the active plan and required feature rows, then validate reminder policies.
    # ==============================================

    async def validate_trial_configuration(self) -> tuple[int, set[int]]:
        """Return the existing trial plan and entitlements without creating domain records.

        Missing plans, inactive plans, missing required features or invalid reminder
        policies abort before registration creates an owner or restaurant.
        """
        trial_plan = (
            await self.session.execute(
                base_select(SubscriptionPlan)
                .options(raiseload("*"))
                .where(SubscriptionPlan.code == "trial")
                .with_for_update(read=True)
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        if trial_plan is None:
            raise ValueError("trial_plan_not_found")
        _, _, included = await plan_features(
            session=self.session, plan_id=trial_plan.id
        )
        locked_features = set(
            (
                await self.session.execute(
                    base_select(Feature)
                    .with_only_columns(Feature.id)
                    .where(Feature.id.in_(included))
                    .order_by(Feature.id)
                    .with_for_update(read=True)
                )
            ).scalars()
        )
        if locked_features != included:
            raise ValueError("mandatory_feature_configuration_missing")
        await reminder_configuration(session=self.session)
        return trial_plan.id, included

    # ==============================================
    # SERIALIZED SINGLE-TRIAL ELIGIBILITY
    # Refresh and lock the owner before inspecting their consumed right and paid/trial history.
    # ==============================================

    async def require_trial_eligibility(self, *, owner_id: int) -> None:
        """Reject a missing owner or previously consumed trial while holding their row lock."""

        owner = (
            await self.session.execute(
                base_select(Owner)
                .options(raiseload("*"))
                .where(Owner.id == owner_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        if owner is None:
            raise ValueError("owner_not_found")
        if owner.trial_used:
            raise ValueError("trial_already_used")
        previous_trial = (
            await self.session.execute(
                base_select(Subscription)
                .with_only_columns(Subscription.id)
                .where(
                    Subscription.owner_id == owner_id,
                    (Subscription.billing_cycle == "trial")
                    | Subscription.starts_at.is_not(None),
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if previous_trial is not None:
            raise ValueError("trial_already_used")

    # ==============================================
    # CREATE TRIAL SUBSCRIPTION
    # Create the owner's single trial after checking ownership and existing coverage.
    # ==============================================

    async def create_trial_subscription(
        self,
        *,
        owner_id: int,
        restaurant_id: int,
        payment_method: str = "cash",
    ) -> Subscription:
        """Create the owner's single trial after checking ownership and existing coverage."""

        async with payment_transaction(session=self.session):
            await self.require_trial_eligibility(owner_id=owner_id)
            restaurant = (
                await self.session.execute(
                    base_select(Restaurant)
                    .with_only_columns(Restaurant.id)
                    .where(
                        Restaurant.id == restaurant_id, Restaurant.owner_id == owner_id
                    )
                    .with_for_update()
                )
            ).scalar_one_or_none()
            if restaurant is None:
                raise ValueError("restaurant_owner_mismatch")
            trial_plan_id, included = await self.validate_trial_configuration()
            starts_at = datetime.now(timezone.utc).replace(tzinfo=None)
            self.repo.query_options = [raiseload("*")]
            subscription = await self.repo.create(
                data={
                    "owner_id": owner_id,
                    "restaurant_id": restaurant_id,
                    "plan_id": trial_plan_id,
                    "billing_cycle": "trial",
                    "amount": 0,
                    "starts_at": starts_at,
                    "expires_at": starts_at + timedelta(days=30),
                    "status": "trial",
                }
            )
            self.session.add_all(
                SubscriptionFeature(subscription_id=subscription.id, feature_id=fid)
                for fid in included
            )
            await self.session.execute(
                update(Owner).where(Owner.id == owner_id).values(trial_used=True)
            )
            await self.session.flush()
            from app.services.business.subscription_reminders import schedule

            await schedule(session=self.session, subscription=subscription)
        return subscription

    # ==============================================
    # CREATE PENDING PAID SUBSCRIPTION
    # Persist owned pending coverage and its server-calculated immutable quotation.
    # ==============================================

    async def create_pending_subscription(
        self,
        *,
        owner_id: int,
        restaurant_id: int,
        plan_id: int,
        billing_cycle: str,
        payment_method: str,
        restaurants_count: int,
        branches_count: int,
        years_with_platform: int,
        products_count: int,
        categories_count: int,
        monthly_orders: int,
        average_order_value: NumericInput,
        additional_feature_ids: list[int] | None = None,
        currency: str = "DZD",
        market: str | None = None,
        replacement_evidence: dict[str, JsonValue] | None = None,
    ) -> SubscriptionResult:
        """Persist owned pending coverage and its server-calculated immutable quotation."""

        from app.services.business.pricing_service import number

        for value in (
            restaurants_count,
            branches_count,
            products_count,
            categories_count,
            monthly_orders,
        ):
            number(value=value, integer=True)
        number(value=years_with_platform)
        number(value=average_order_value)
        async with payment_transaction(session=self.session):
            owned = (
                await self.session.execute(
                    base_select(Restaurant)
                    .with_only_columns(Restaurant.id)
                    .where(
                        Restaurant.id == restaurant_id, Restaurant.owner_id == owner_id
                    )
                    .with_for_update()
                )
            ).scalar_one_or_none()
            if owned is None:
                raise ValueError("restaurant_owner_mismatch")
            # ==============================================
            # AUTHORITATIVE COUNTRY BEFORE BINDING QUOTATION
            # O3/O4 forbid the historical singleton fallback; the owner cannot choose a cheaper market.
            # ==============================================

            from app.repositories.subscription_configuration import country_storage_enabled  # isort: skip  # fmt: skip

            country_code: str | None = None
            country_decision: int | None = None
            if await country_storage_enabled(session=self.session):
                from app.services.business.billing_country import validated_country_for_subscription  # isort: skip  # fmt: skip

                country_code, country_decision, _service_start = (
                    await validated_country_for_subscription(
                        session=self.session,
                        owner_id=owner_id,
                        restaurant_id=restaurant_id,
                        currency=currency,
                    )
                )
                if market is not None and market != country_code:
                    raise ValueError("billing_country_market_mismatch")
                market = country_code
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            ref, inputs = await subscription_metrics.pricing_inputs(
                session=self.session,
                owner_id=owner_id,
                restaurant_id=restaurant_id,
                now=now,
            )
            pricing = await calculate_subscription_pricing(
                session=self.session,
                plan_id=plan_id,
                billing_cycle=billing_cycle,
                payment_method=payment_method,
                currency=currency,
                country_code=country_code,
                market=market,
                now=now,
                **inputs,
                additional_feature_ids=additional_feature_ids or [],
                owner_id=owner_id,
                restaurant_id=restaurant_id,
            )
            existing = (
                (
                    await self.session.execute(
                        base_select(Subscription)
                        .with_only_columns(Subscription.id)
                        .where(
                            Subscription.restaurant_id == restaurant_id,
                            Subscription.status.in_(["pending", "pending_payment"]),
                        )
                    )
                )
                .scalars()
                .all()
            )
            if existing:
                raise ValueError("subscription_checkout_already_pending")
            self.repo.query_options = [raiseload("*")]
            subscription = await self.repo.create(
                data={
                    "owner_id": owner_id,
                    "restaurant_id": restaurant_id,
                    "plan_id": plan_id,
                    "billing_cycle": billing_cycle,
                    "amount": pricing["final_amount_due"],
                    "starts_at": None,
                    "expires_at": None,
                    "status": "pending",
                    "currency": currency,
                    "market": market,
                }
            )
            parameters = pricing["parameters"]
            if replacement_evidence is not None:
                parameters["replacement"] = replacement_evidence
            if country_code is not None:
                from sqlalchemy import text

                parameters["billing_country_decision_id"] = country_decision
                await self.session.execute(
                    text(
                        "UPDATE subscriptions SET billing_country_code=:country,billing_country_decision_id=:decision WHERE id=:id AND owner_id=:owner"
                    ),
                    {
                        "country": country_code,
                        "decision": country_decision,
                        "id": subscription.id,
                        "owner": owner_id,
                    },
                )
            feature_ids = set(parameters["included_feature_ids"]) | set(
                parameters["additional_feature_ids"]
            )
            self.session.add_all(
                SubscriptionFeatureRequest(
                    subscription_id=subscription.id, feature_id=fid
                )
                for fid in feature_ids
            )
            self.session.add(
                SubscriptionPricingSnapshot(
                    owner_id=owner_id,
                    restaurant_id=restaurant_id,
                    subscription_id=subscription.id,
                    calculated_at=now,
                    pricing=subscription_metrics.json_evidence(value=pricing),
                    parameters=subscription_metrics.json_evidence(value=parameters),
                    **ref,
                )
            )
            await self.session.flush()
        return {"subscription_id": subscription.id, "pricing": pricing}

    # ==============================================
    # ACTIVATE SUBSCRIPTION
    # إلغاء اشتراك.
    # ==============================================

    # ==============================================
    # CANCEL SUBSCRIPTION
    # إلغاء اشتراك.
    # ==============================================

    async def cancel_subscription(
        self,
        *,
        subscription_id: int,
    ) -> Subscription | None:
        """
        إلغاء اشتراك.

        Args:
            subscription_id: معرف الاشتراك

        Returns:
            كائن Subscription المحدث أو None
        """
        logger.info(
            "subscription_service_cancel",
            extra={"subscription_id": subscription_id},
        )

        return await self.repo.update(
            id=subscription_id,
            data={
                "status": "cancelled",
                "cancelled_at": datetime.now(timezone.utc).replace(tzinfo=None),
            },
        )

    # ==============================================
    # EXPIRE SUBSCRIPTION
    # انتهاء اشتراك.
    # ==============================================

    async def expire_subscription(
        self,
        *,
        subscription_id: int,
    ) -> Subscription | None:
        """
        انتهاء اشتراك.

        Args:
            subscription_id: معرف الاشتراك

        Returns:
            كائن Subscription المحدث أو None
        """
        logger.info(
            "subscription_service_expire",
            extra={"subscription_id": subscription_id},
        )

        return await self.repo.update_status(
            subscription_id=subscription_id,
            status="expired",
        )

    # ==============================================
    # 📊 STATISTICS
    # Aggregate persisted counts and values through the existing query paths.
    # ==============================================

    # ==============================================
    # COUNT BY STATUS
    # حساب عدد الاشتراكات حسب الحالة.
    # ==============================================

    async def count_by_status(
        self,
        *,
        status: str,
    ) -> int:
        """
        حساب عدد الاشتراكات حسب الحالة.

        Args:
            status: حالة الاشتراك

        Returns:
            عدد الاشتراكات
        """
        return await self.repo.count(filters={"status": status})

    # ==============================================
    # COUNT ACTIVE
    # حساب عدد الاشتراكات النشطة.
    # ==============================================

    async def count_active(self) -> int:
        """
        حساب عدد الاشتراكات النشطة.

        Returns:
            عدد الاشتراكات النشطة
        """
        return await self.repo.count(filters={"status": "active"})


# ==============================================
# EXPORTS
# Declare the public names intentionally exposed to importing modules.
# ==============================================

__all__ = [
    "PricingResult",
    "SubscriptionList",
    "SubscriptionResult",
    "SubscriptionService",
]
