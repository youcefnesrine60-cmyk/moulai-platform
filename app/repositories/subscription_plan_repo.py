# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 💳 SUBSCRIPTION PLAN REPOSITORY
# عمليات قاعدة البيانات لخطط الاشتراك باستخدام SQLAlchemy
# قراءة الباقات (Basic, Professional, Enterprise, Trial)
# قراءة السعر الأساسي
# قراءة نسبة التخفيض
# قراءة الكود
# ==============================================

"""MoulAI operational module for subscription plan repo.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models.subscription import SubscriptionPlan
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

SubscriptionPlanData = Dict[str, Any]
SubscriptionPlanUpdateData = Dict[str, Any]
SubscriptionPlanList = List[SubscriptionPlan]

# ==============================================
# 💳 SUBSCRIPTION PLAN REPOSITORY
# ==============================================


class SubscriptionPlanRepository(
    BaseRepository[
        SubscriptionPlan,
        SubscriptionPlanData,
        SubscriptionPlanUpdateData,
    ]
):
    """
    مستودع خطط الاشتراك - يوفر عمليات خاصة بخطط الاشتراك.

    مسؤول عن:
        - عمليات CRUD الأساسية لخطط الاشتراك
        - البحث بالكود
        - إدارة حالة النشاط
        - حساب الأسعار بعد التخفيض

    Attributes:
        model: نموذج SubscriptionPlan
        session: جلسة قاعدة البيانات غير المتزامنة
    """

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة مستودع خطط الاشتراك.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(SubscriptionPlan, session)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET BY CODE
    # ==============================================

    async def get_by_code(
        self,
        *,
        code: str,
    ) -> Optional[SubscriptionPlan]:
        """
        الحصول على خطة اشتراك بواسطة الكود.

        Args:
            code: كود الخطة (trial, basic, pro, enterprise)

        Returns:
            كائن SubscriptionPlan أو None
        """
        try:
            result = await self.session.execute(
                select(self.model).where(self.model.code == code).limit(1),
            )

            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(
                "subscription_plan_repo_get_by_code_failed",
                extra={
                    "code": code,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET ACTIVE
    # ==============================================

    async def get_active(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> SubscriptionPlanList:
        """
        الحصول على خطط الاشتراك النشطة.

        Args:
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة خطط الاشتراك النشطة
        """
        try:
            query = (
                select(self.model)
                .where(self.model.active == True)
                .order_by(
                    self.model.display_order.asc(),
                    self.model.id.asc(),
                )
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "subscription_plan_repo_get_active_failed",
                extra={"error": str(e)},
            )
            raise

    # ==============================================
    # GET TRIAL PLAN
    # ==============================================

    async def get_trial_plan(
        self,
    ) -> Optional[SubscriptionPlan]:
        """
        الحصول على خطة التجربة المجانية.

        Returns:
            كائن SubscriptionPlan أو None
        """
        return await self.get_by_code(code="trial")

    # ==============================================
    # GET BY DISPLAY ORDER
    # ==============================================

    async def get_by_display_order(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> SubscriptionPlanList:
        """
        الحصول على خطط الاشتراك مرتبة حسب ترتيب العرض.

        Args:
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة خطط الاشتراك
        """
        try:
            query = (
                select(self.model)
                .order_by(
                    self.model.display_order.asc(),
                    self.model.id.asc(),
                )
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "subscription_plan_repo_get_by_display_order_failed",
                extra={"error": str(e)},
            )
            raise

    # ==========================================
    # ✏️ UPDATES
    # ==========================================

    # ==============================================
    # UPDATE PRICE
    # ==============================================

    async def update_price(
        self,
        *,
        plan_id: int,
        base_price: float,
    ) -> Optional[SubscriptionPlan]:
        """
        تحديث السعر الأساسي للخطة.

        Args:
            plan_id: معرف الخطة
            base_price: السعر الأساسي الجديد

        Returns:
            كائن SubscriptionPlan المحدث أو None
        """
        logger.info(
            "subscription_plan_repo_update_price",
            extra={
                "plan_id": plan_id,
                "base_price": base_price,
            },
        )

        return await self.update(
            id=plan_id,
            data={"base_price": base_price},
        )

    # ==============================================
    # UPDATE DISCOUNT
    # ==============================================

    async def update_discount(
        self,
        *,
        plan_id: int,
        plan_discount_percent: float,
    ) -> Optional[SubscriptionPlan]:
        """
        تحديث نسبة التخفيض للخطة.

        Args:
            plan_id: معرف الخطة
            plan_discount_percent: نسبة التخفيض الجديدة

        Returns:
            كائن SubscriptionPlan المحدث أو None
        """
        logger.info(
            "subscription_plan_repo_update_discount",
            extra={
                "plan_id": plan_id,
                "plan_discount_percent": plan_discount_percent,
            },
        )

        return await self.update(
            id=plan_id,
            data={"plan_discount_percent": plan_discount_percent},
        )

    # ==============================================
    # ACTIVATE
    # ==============================================

    async def activate(
        self,
        *,
        plan_id: int,
    ) -> Optional[SubscriptionPlan]:
        """
        تفعيل خطة اشتراك.

        Args:
            plan_id: معرف الخطة

        Returns:
            كائن SubscriptionPlan المحدث أو None
        """
        logger.info(
            "subscription_plan_repo_activate",
            extra={"plan_id": plan_id},
        )

        return await self.update(
            id=plan_id,
            data={"active": True},
        )

    # ==============================================
    # DEACTIVATE
    # ==============================================

    async def deactivate(
        self,
        *,
        plan_id: int,
    ) -> Optional[SubscriptionPlan]:
        """
        إلغاء تفعيل خطة اشتراك.

        Args:
            plan_id: معرف الخطة

        Returns:
            كائن SubscriptionPlan المحدث أو None
        """
        logger.info(
            "subscription_plan_repo_deactivate",
            extra={"plan_id": plan_id},
        )

        return await self.update(
            id=plan_id,
            data={"active": False},
        )

    # ==============================================
    # UPDATE DISPLAY ORDER
    # ==============================================

    async def update_display_order(
        self,
        *,
        plan_id: int,
        display_order: int,
    ) -> Optional[SubscriptionPlan]:
        """
        تحديث ترتيب عرض الخطة.

        Args:
            plan_id: معرف الخطة
            display_order: ترتيب العرض الجديد

        Returns:
            كائن SubscriptionPlan المحدث أو None
        """
        logger.info(
            "subscription_plan_repo_update_display_order",
            extra={
                "plan_id": plan_id,
                "display_order": display_order,
            },
        )

        return await self.update(
            id=plan_id,
            data={"display_order": display_order},
        )

    # ==========================================
    # 💰 CALCULATIONS
    # ==========================================

    # ==============================================
    # CALCULATE PRICE
    # ==============================================

    async def calculate_price(
        self,
        *,
        plan_id: int,
    ) -> float:
        """
        حساب السعر النهائي للخطة بعد التخفيض.

        Args:
            plan_id: معرف الخطة

        Returns:
            السعر النهائي

        Raises:
            ValueError: إذا لم يتم العثور على الخطة
        """
        plan = await self.get_by_id(id=plan_id)

        if not plan:
            raise ValueError(f"Subscription plan {plan_id} not found")

        base_price = float(plan.base_price)
        discount = float(plan.plan_discount_percent)

        final_price = base_price - (base_price * discount / 100)

        return round(final_price, 2)


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# دوال متوافقة مع الاستيرادات القديمة
# ==============================================

# ==============================================
# CREATE SUBSCRIPTION PLAN (COMPATIBILITY)
# ==============================================


async def create_subscription_plan(
    *,
    code: str,
    name: str,
    base_price: float,
    plan_discount_percent: float = 0,
    display_order: int = 0,
    description: Optional[str] = None,
    active: bool = True,
    session: AsyncSession,
) -> int:
    """
    إنشاء خطة اشتراك جديدة (دالة متوافقة مع الإصدار القديم).

    Args:
        code: كود الخطة
        name: اسم الخطة
        base_price: السعر الأساسي
        plan_discount_percent: نسبة التخفيض
        display_order: ترتيب العرض
        description: وصف الخطة
        active: حالة النشاط
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        معرف الخطة
    """
    repo = SubscriptionPlanRepository(session=session)

    data: SubscriptionPlanData = {
        "code": code,
        "name": name,
        "base_price": base_price,
        "plan_discount_percent": plan_discount_percent,
        "display_order": display_order,
        "description": description,
        "active": active,
    }

    plan = await repo.create(data=data)

    logger.info(
        "subscription_plan_created",
        extra={
            "plan_id": plan.id,
            "code": code,
        },
    )

    return plan.id


# ==============================================
# GET SUBSCRIPTION PLAN BY ID (COMPATIBILITY)
# ==============================================


async def get_subscription_plan_by_id(
    *,
    plan_id: int,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على خطة اشتراك بالمعرف (دالة متوافقة مع الإصدار القديم).

    Args:
        plan_id: معرف الخطة
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        قاموس بيانات الخطة أو None
    """
    repo = SubscriptionPlanRepository(session=session)

    plan = await repo.get_by_id(id=plan_id)

    if not plan:
        logger.warning(
            "subscription_plan_not_found",
            extra={"plan_id": plan_id},
        )
        return None

    return {
        "id": plan.id,
        "code": plan.code,
        "name": plan.name,
        "active": plan.active,
        "created_at": plan.created_at,
        "plan_discount_percent": float(plan.plan_discount_percent),
        "display_order": plan.display_order,
        "description": plan.description,
        "base_price": float(plan.base_price),
    }


# ==============================================
# GET SUBSCRIPTION PLAN BY CODE (COMPATIBILITY)
# ==============================================


async def get_subscription_plan_by_code(
    *,
    code: str,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على خطة اشتراك بواسطة الكود (دالة متوافقة مع الإصدار القديم).

    Args:
        code: كود الخطة
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        قاموس بيانات الخطة أو None
    """
    repo = SubscriptionPlanRepository(session=session)

    plan = await repo.get_by_code(code=code)

    if not plan:
        return None

    return {
        "id": plan.id,
        "code": plan.code,
        "name": plan.name,
        "active": plan.active,
        "created_at": plan.created_at,
        "plan_discount_percent": float(plan.plan_discount_percent),
        "display_order": plan.display_order,
        "description": plan.description,
        "base_price": float(plan.base_price),
    }


# ==============================================
# GET TRIAL PLAN (COMPATIBILITY)
# ==============================================


async def get_trial_plan(
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على خطة التجربة المجانية (دالة متوافقة مع الإصدار القديم).

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        قاموس بيانات الخطة أو None
    """
    return await get_subscription_plan_by_code(
        code="trial",
        session=session,
    )


# ==============================================
# GET ACTIVE SUBSCRIPTION PLANS (COMPATIBILITY)
# ==============================================


async def get_active_subscription_plans(
    session: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    الحصول على خطط الاشتراك النشطة (دالة متوافقة مع الإصدار القديم).

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات

    Returns:
        قائمة خطط الاشتراك النشطة
    """
    repo = SubscriptionPlanRepository(session=session)

    plans = await repo.get_active(
        skip=skip,
        limit=limit,
    )

    result = []

    for plan in plans:
        result.append(
            {
                "id": plan.id,
                "code": plan.code,
                "name": plan.name,
                "active": plan.active,
                "created_at": plan.created_at,
                "plan_discount_percent": float(plan.plan_discount_percent),
                "display_order": plan.display_order,
                "description": plan.description,
                "base_price": float(plan.base_price),
            }
        )

    logger.info(
        "subscription_plans_fetched",
        extra={"count": len(result)},
    )

    return result


# ==============================================
# GET ALL SUBSCRIPTION PLANS (COMPATIBILITY)
# ==============================================


async def get_all_subscription_plans(
    session: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    الحصول على جميع خطط الاشتراك (دالة متوافقة مع الإصدار القديم).

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات

    Returns:
        قائمة جميع خطط الاشتراك
    """
    repo = SubscriptionPlanRepository(session=session)

    plans = await repo.get_all(
        skip=skip,
        limit=limit,
        order_by="display_order",
    )

    result = []

    for plan in plans:
        result.append(
            {
                "id": plan.id,
                "code": plan.code,
                "name": plan.name,
                "active": plan.active,
                "created_at": plan.created_at,
                "plan_discount_percent": float(plan.plan_discount_percent),
                "display_order": plan.display_order,
                "description": plan.description,
                "base_price": float(plan.base_price),
            }
        )

    return result


# ==============================================
# CALCULATE PLAN PRICE (COMPATIBILITY)
# ==============================================


async def calculate_plan_price(
    *,
    plan_id: int,
    session: AsyncSession,
) -> float:
    """
    حساب السعر النهائي للخطة (دالة متوافقة مع الإصدار القديم).

    Args:
        plan_id: معرف الخطة
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        السعر النهائي

    Raises:
        ValueError: إذا لم يتم العثور على الخطة
    """
    repo = SubscriptionPlanRepository(session=session)

    return await repo.calculate_price(plan_id=plan_id)


# ==============================================
# UPDATE SUBSCRIPTION PLAN PRICE (COMPATIBILITY)
# ==============================================


async def update_subscription_plan_price(
    *,
    plan_id: int,
    base_price: float,
    session: AsyncSession,
) -> None:
    """
    تحديث السعر الأساسي للخطة (دالة متوافقة مع الإصدار القديم).

    Args:
        plan_id: معرف الخطة
        base_price: السعر الأساسي الجديد
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = SubscriptionPlanRepository(session=session)

    await repo.update_price(
        plan_id=plan_id,
        base_price=base_price,
    )

    logger.info(
        "subscription_plan_price_updated",
        extra={
            "plan_id": plan_id,
            "base_price": base_price,
        },
    )


# ==============================================
# UPDATE SUBSCRIPTION PLAN DISCOUNT (COMPATIBILITY)
# ==============================================


async def update_subscription_plan_discount(
    *,
    plan_id: int,
    plan_discount_percent: float,
    session: AsyncSession,
) -> None:
    """
    تحديث نسبة التخفيض للخطة (دالة متوافقة مع الإصدار القديم).

    Args:
        plan_id: معرف الخطة
        plan_discount_percent: نسبة التخفيض الجديدة
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = SubscriptionPlanRepository(session=session)

    await repo.update_discount(
        plan_id=plan_id,
        plan_discount_percent=plan_discount_percent,
    )

    logger.info(
        "subscription_plan_discount_updated",
        extra={
            "plan_id": plan_id,
            "plan_discount_percent": plan_discount_percent,
        },
    )


# ==============================================
# ACTIVATE SUBSCRIPTION PLAN (COMPATIBILITY)
# ==============================================


async def activate_subscription_plan(
    *,
    plan_id: int,
    session: AsyncSession,
) -> None:
    """
    تفعيل خطة اشتراك (دالة متوافقة مع الإصدار القديم).

    Args:
        plan_id: معرف الخطة
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = SubscriptionPlanRepository(session=session)

    await repo.activate(plan_id=plan_id)

    logger.info(
        "subscription_plan_activated",
        extra={"plan_id": plan_id},
    )


# ==============================================
# DEACTIVATE SUBSCRIPTION PLAN (COMPATIBILITY)
# ==============================================


async def deactivate_subscription_plan(
    *,
    plan_id: int,
    session: AsyncSession,
) -> None:
    """
    إلغاء تفعيل خطة اشتراك (دالة متوافقة مع الإصدار القديم).

    Args:
        plan_id: معرف الخطة
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = SubscriptionPlanRepository(session=session)

    await repo.deactivate(plan_id=plan_id)

    logger.info(
        "subscription_plan_deactivated",
        extra={"plan_id": plan_id},
    )
