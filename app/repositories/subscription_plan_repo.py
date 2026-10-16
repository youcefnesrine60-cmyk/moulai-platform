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
