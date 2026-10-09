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
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models.subscription import Subscription
from app.repositories.owner_repo import OwnerRepository
from app.repositories.payment_repo import PaymentRepository
from app.repositories.subscription_plan_repo import (
    SubscriptionPlanRepository,
)
from app.repositories.subscription_repo import (
    SubscriptionRepository,
)
from app.services.business.pricing_service import (
    calculate_subscription_pricing,
)

# ==============================================
# 🧩 TYPES
# ==============================================

PricingResult = Dict[str, Any]
SubscriptionResult = Dict[str, Any]
SubscriptionList = List[Subscription]

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
        payment_repo: مستودع المدفوعات
    """

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة خدمة الاشتراكات.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        self.session = session
        self.repo = SubscriptionRepository(session)
        self.plan_repo = SubscriptionPlanRepository(session)
        self.owner_repo = OwnerRepository(session)
        self.payment_repo = PaymentRepository(session)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET BY ID
    # ==============================================

    async def get_by_id(
        self,
        *,
        subscription_id: int,
    ) -> Optional[Subscription]:
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
    ) -> Optional[Subscription]:
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
    ) -> Optional[Dict[str, Any]]:
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
        starts_at = datetime.now(timezone.utc)
        expires_at = starts_at + timedelta(days=30)

        # 4️⃣ إنشاء الاشتراك
        subscription_data: Dict[str, Any] = {
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
    # CREATE PAID SUBSCRIPTION
    # ==============================================

    async def create_paid_subscription(
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
        additional_feature_ids: Optional[List[int]] = None,
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
        subscription_data: Dict[str, Any] = {
            "owner_id": owner_id,
            "restaurant_id": restaurant_id,
            "plan_id": plan_id,
            "billing_cycle": billing_cycle,
            "amount": pricing["final_amount_due"],
            "starts_at": None,
            "expires_at": None,
            "status": "pending_payment",
        }

        subscription = await self.repo.create(data=subscription_data)

        # 3️⃣ إنشاء الدفع
        payment_data: Dict[str, Any] = {
            "owner_id": owner_id,
            "restaurant_id": restaurant_id,
            "subscription_id": subscription.id,
            "payment_method": payment_method,
            "amount": pricing["final_amount_due"],
            "status": "pending",
        }

        payment = await self.payment_repo.create(data=payment_data)

        logger.info(
            "paid_subscription_created",
            extra={
                "subscription_id": subscription.id,
                "payment_id": payment.id,
                "restaurant_id": restaurant_id,
                "amount": pricing["final_amount_due"],
            },
        )

        return {
            "subscription_id": subscription.id,
            "payment_id": payment.id,
            "pricing": pricing,
        }

    # ==============================================
    # ACTIVATE SUBSCRIPTION
    # ==============================================

    async def activate_subscription(
        self,
        *,
        subscription_id: int,
    ) -> Optional[Subscription]:
        """
        تفعيل اشتراك (تغيير الحالة إلى active).

        Args:
            subscription_id: معرف الاشتراك

        Returns:
            كائن Subscription المحدث أو None
        """
        logger.info(
            "subscription_service_activate",
            extra={"subscription_id": subscription_id},
        )

        subscription = await self.repo.get_by_id(id=subscription_id)

        if not subscription:
            return None

        # تحديث الحالة إلى active
        updated = await self.repo.update_status(
            subscription_id=subscription_id,
            status="active",
        )

        # تحديث تاريخ البدء إذا كان None
        if updated and updated.starts_at is None:
            await self.repo.update(
                id=subscription_id,
                data={"starts_at": datetime.now(timezone.utc)},
            )
            await self.session.refresh(updated)

        logger.info(
            "subscription_activated",
            extra={"subscription_id": subscription_id},
        )

        return updated

    # ==============================================
    # CANCEL SUBSCRIPTION
    # ==============================================

    async def cancel_subscription(
        self,
        *,
        subscription_id: int,
    ) -> Optional[Subscription]:
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
    ) -> Optional[Subscription]:
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


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# دوال متوافقة مع الاستيرادات القديمة
# ==============================================

# ==============================================
# CREATE TRIAL SUBSCRIPTION (COMPATIBILITY)
# ==============================================


async def create_trial_subscription(
    *,
    owner_id: int,
    restaurant_id: int,
    payment_method: str = "cash",
    session: AsyncSession,
) -> int:
    """
    إنشاء اشتراك تجريبي (دالة متوافقة مع الإصدار القديم).

    Args:
        owner_id: معرف المالك
        restaurant_id: معرف المطعم
        payment_method: طريقة الدفع
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        معرف الاشتراك
    """
    service = SubscriptionService(session=session)

    subscription = await service.create_trial_subscription(
        owner_id=owner_id,
        restaurant_id=restaurant_id,
        payment_method=payment_method,
    )

    return subscription.id


# ==============================================
# CREATE PAID SUBSCRIPTION (COMPATIBILITY)
# ==============================================


async def create_paid_subscription(
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
    additional_feature_ids: Optional[List[int]] = None,
    session: AsyncSession,
) -> SubscriptionResult:
    """
    إنشاء اشتراك مدفوع (دالة متوافقة مع الإصدار القديم).

    Args:
        owner_id: معرف المالك
        restaurant_id: معرف المطعم
        plan_id: معرف الخطة
        billing_cycle: دورة الفوترة
        payment_method: طريقة الدفع
        restaurants_count: عدد المطاعم
        branches_count: عدد الفروع
        years_with_platform: عدد سنوات التعامل مع المنصة
        products_count: عدد المنتجات
        categories_count: عدد التصنيفات
        monthly_orders: عدد الطلبات الشهرية
        average_order_value: متوسط قيمة الطلب
        additional_feature_ids: قائمة معرفات الميزات الإضافية
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        قاموس نتائج الإنشاء
    """
    service = SubscriptionService(session=session)

    return await service.create_paid_subscription(
        owner_id=owner_id,
        restaurant_id=restaurant_id,
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
        additional_feature_ids=additional_feature_ids,
    )


# ==============================================
# PREVIEW SUBSCRIPTION PRICING (COMPATIBILITY)
# ==============================================


async def preview_subscription_pricing(
    *,
    session: AsyncSession,  # ✅ أضفنا session
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
    additional_feature_ids: Optional[List[int]] = None,
) -> PricingResult:
    """
    معاينة تسعير الاشتراك (دالة متوافقة مع الإصدار القديم).

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        plan_id: معرف الخطة
        billing_cycle: دورة الفوترة
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
        قاموس تفاصيل التسعير
    """
    return await calculate_subscription_pricing(
        session=session,  # ✅ تمرير session
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


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "SubscriptionService",
    "PricingResult",
    "SubscriptionResult",
    "SubscriptionList",
    "create_trial_subscription",
    "create_paid_subscription",
    "preview_subscription_pricing",
]
