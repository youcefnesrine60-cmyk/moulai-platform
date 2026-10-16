# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / SERVICES / BUSINESS / SUBSCRIPTION SERVICE
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for subscription service.

Part of MoulAI Platform - Agent-as-a-Service.
"""

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
from decimal import (
    ROUND_HALF_UP,
    Decimal,
)
from typing import (
    Any,
    TypeAlias,
)

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload

from app.core.logger import logger
from app.models.payment import Payment
from app.models.subscription import Subscription
from app.repositories.owner_repo import OwnerRepository

from app.repositories.subscription_feature_requests_repo import SubscriptionFeatureRequestRepository  # fmt: skip # isort: skip
from app.repositories.subscription_features_repo import SubscriptionFeatureRepository
from app.repositories.subscription_plan_repo import SubscriptionPlanRepository
from app.repositories.subscription_repo import SubscriptionRepository
from app.services.business.pricing_service import calculate_subscription_pricing

# ==============================================
# 🧩 TYPES
# ==============================================

PricingResult: TypeAlias = dict[str, Any]
SubscriptionResult: TypeAlias = dict[str, Any]
SubscriptionList: TypeAlias = list[Subscription]

# ==============================================
# 💳 SUBSCRIPTION SERVICE
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
    #   INIT
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
        self.plan_repo = SubscriptionPlanRepository(session)
        self.owner_repo = OwnerRepository(session=session)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # ACTIVATE FOR VERIFIED PAYMENT
    # ==============================================

    async def activate_for_verified_payment(self, *, payment: Payment) -> None:
        """Apply subscription effects inside the payment settlement transaction."""

        if payment.status != "paid" or not self.session.info.get(
            "defer_repository_commit"
        ):
            raise ValueError("verified_payment_transaction_required")
        if not payment.subscription_id:
            raise ValueError("subscription_not_found")
        subscriptions = SubscriptionRepository(session=self.session)
        subscriptions.query_options = [raiseload("*")]
        subscription = await subscriptions.get_by_id_for_update(
            subscription_id=payment.subscription_id
        )
        if subscription is None:
            raise ValueError("subscription_not_found")
        if (
            subscription.owner_id != payment.owner_id
            or subscription.restaurant_id != payment.restaurant_id
        ):
            raise ValueError("payment_subscription_scope_mismatch")
        if Decimal(str(subscription.amount)) != Decimal(str(payment.amount)):
            raise ValueError("payment_subscription_amount_mismatch")
        if subscription.status not in {"pending", "pending_payment", "active"}:
            raise ValueError("subscription_not_pending")
        days = {"monthly": 30, "yearly": 365}.get(subscription.billing_cycle)
        if days is None:
            raise ValueError(f"unsupported_billing_cycle: {subscription.billing_cycle}")
        starts_at = payment.paid_at
        if starts_at is None:
            raise ValueError("payment_settlement_date_required")
        if subscription.status != "active":
            activated = await subscriptions.activate(
                subscription_id=subscription.id,
                starts_at=starts_at,
                expires_at=starts_at + timedelta(days=days),
            )
            if activated is None:
                raise ValueError("subscription_not_found")
        features = SubscriptionFeatureRepository(self.session)
        requests = SubscriptionFeatureRequestRepository(self.session)
        features.query_options = [raiseload("*")]
        requests.query_options = [raiseload("*")]
        for request in await requests.get_by_subscription(
            subscription_id=subscription.id
        ):
            await features.create_subscription_feature(
                subscription_id=subscription.id, feature_id=request.feature_id
            )
        await requests.delete_by_subscription(subscription_id=subscription.id)

    # ==============================================
    # GET BY ID
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

        return {
            "id": plan.id,
            "code": plan.code,
            "name": plan.name,
            "description": plan.description,
            "base_price": float(plan.base_price),
            "plan_discount_percent": float(plan.plan_discount_percent),
            "active": plan.active,
        }

    # ==========================================
    # ✏️ MUTATIONS
    # ==========================================

    # ==============================================
    # CREATE TRIAL SUBSCRIPTION
    # ==============================================

    async def create_trial_subscription(
        self,
        *,
        owner_id: int,
        restaurant_id: int,
        payment_method: str = "cash",
    ) -> Subscription:
        """
        إنشاء اشتراك تجريبي (Trial).

        Args:
            owner_id: معرف المالك
            restaurant_id: معرف المطعم
            payment_method: طريقة الدفع

        Returns:
            كائن Subscription المنشأ

        Raises:
            ValueError: إذا استخدم المالك التجربة مسبقاً
            ValueError: إذا لم يتم العثور على خطة التجربة
        """
        logger.info(
            "subscription_service_create_trial",
            extra={
                "owner_id": owner_id,
                "restaurant_id": restaurant_id,
            },
        )

        # 1️⃣ التحقق من عدم استخدام التجربة مسبقاً
        owner = await self.owner_repo.get_by_id(id=owner_id)

        if not owner:
            raise ValueError(f"owner_not_found:{owner_id}")

        if owner.trial_used:
            raise ValueError("trial_already_used")

        # 2️⃣ الحصول على خطة التجربة
        trial_plan = await self.plan_repo.get_by_code(code="trial")

        if not trial_plan:
            raise ValueError("trial_plan_not_found")

        # 3️⃣ حساب التواريخ
        # SQLAlchemy DateTime columns persist UTC without a timezone offset.
        starts_at = datetime.now(timezone.utc).replace(tzinfo=None)
        expires_at = starts_at + timedelta(days=30)

        # 4️⃣ إنشاء الاشتراك
        subscription_data: dict[str, Any] = {
            "owner_id": owner_id,
            "restaurant_id": restaurant_id,
            "plan_id": trial_plan.id,
            "billing_cycle": "trial",
            "amount": 0,
            "starts_at": starts_at,
            "expires_at": expires_at,
            "status": "trial",
        }

        subscription = await self.repo.create(data=subscription_data)

        # 5️⃣ تعيين trial_used = True
        await self.owner_repo.update(
            id=owner_id,
            data={"trial_used": True},
        )

        logger.info(
            "trial_subscription_created",
            extra={
                "subscription_id": subscription.id,
                "restaurant_id": restaurant_id,
                "owner_id": owner_id,
            },
        )

        return subscription

    # ==============================================
    # CREATE PENDING PAID SUBSCRIPTION
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
        average_order_value: float,
        additional_feature_ids: list[int] | None = None,
    ) -> SubscriptionResult:
        """
        إنشاء اشتراك مدفوع.

        Args:
            owner_id: معرف المالك
            restaurant_id: معرف المطعم
            plan_id: معرف الخطة
            billing_cycle: دورة الفوترة (monthly, yearly)
            payment_method: طريقة الدفع
            restaurants_count: عدد المطاعم
            branches_count: عدد الفروع
            years_with_platform: عدد سنوات التعامل مع المنصة
            products_count: عدد المنتجات
            categories_count: عدد التصنيفات
            monthly_orders: عدد الطلبات الشهرية
            average_order_value: متوسط قيمة الطلب
            additional_feature_ids: قائمة معرفات الميزات الإضافية

        Returns:
            قاموس يحتوي على نتائج الإنشاء
        """
        logger.info(
            "subscription_service_create_paid",
            extra={
                "owner_id": owner_id,
                "restaurant_id": restaurant_id,
                "plan_id": plan_id,
                "billing_cycle": billing_cycle,
            },
        )

        # 1️⃣ حساب التسعير
        pricing = await calculate_subscription_pricing(
            session=self.session,  # ✅ session ممرر
            plan_id=plan_id,
            billing_cycle=billing_cycle,
            payment_method=payment_method,
            restaurants_count=restaurants_count,
            branches_count=branches_count,
            years_with_platform=years_with_platform,
            products_count=products_count,
            categories_count=categories_count,
            monthly_orders=monthly_orders,
            average_order_value=average_order_value,
            additional_feature_ids=additional_feature_ids or [],
        )

        # 2️⃣ إنشاء الاشتراك
        subscription_data: dict[str, Any] = {
            "owner_id": owner_id,
            "restaurant_id": restaurant_id,
            "plan_id": plan_id,
            "billing_cycle": billing_cycle,
            "amount": float(
                Decimal(str(pricing["final_amount_due"])).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
            ),
            "starts_at": None,
            "expires_at": None,
            "status": "pending",
        }

        subscription = await self.repo.create(data=subscription_data)

        return {"subscription_id": subscription.id, "pricing": pricing}

    # ==============================================
    # ACTIVATE SUBSCRIPTION
    # ==============================================

    # ==============================================
    # CANCEL SUBSCRIPTION
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

        return await self.repo.update_status(
            subscription_id=subscription_id,
            status="cancelled",
        )

    # ==============================================
    # EXPIRE SUBSCRIPTION
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

    # ==========================================
    # 📊 STATISTICS
    # ==========================================

    # ==============================================
    # COUNT BY STATUS
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
    # ==============================================

    async def count_active(self) -> int:
        """
        حساب عدد الاشتراكات النشطة.

        Returns:
            عدد الاشتراكات النشطة
        """
        return await self.repo.count(filters={"status": "active"})


__all__ = [
    "PricingResult",
    "SubscriptionList",
    "SubscriptionResult",
    "SubscriptionService",
]
