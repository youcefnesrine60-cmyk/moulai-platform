# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# SUBSCRIPTION PLAN REPOSITORY
# Read active plan definitions and delegate current base-price calculation.
# ==============================================

"""Read active plan definitions and delegate current base-price calculation."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Declare the standard-library, framework and project dependencies used below.
# ==============================================

from decimal import Decimal
from typing import (
    Any,
    TypeAlias,
)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models.subscription import SubscriptionPlan
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# Describe shared input, update and result structures for this module.
# ==============================================

SubscriptionPlanData: TypeAlias = dict[str, Any]
SubscriptionPlanUpdateData: TypeAlias = dict[str, Any]
SubscriptionPlanList: TypeAlias = list[SubscriptionPlan]


# ==============================================
# 💳 SUBSCRIPTION PLAN REPOSITORY
# مستودع خطط الاشتراك - يوفر عمليات خاصة بخطط الاشتراك.
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
    # INIT
    # تهيئة مستودع خطط الاشتراك.
    # ==============================================

    def __init__(
        self,
        *,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة مستودع خطط الاشتراك.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(SubscriptionPlan, session)

    # ==============================================
    # 📖 QUERIES
    # Read persisted records through the existing repository selection rules.
    # ==============================================

    # ==============================================
    # GET BY CODE
    # الحصول على خطة اشتراك بواسطة الكود.
    # ==============================================

    async def get_by_code(
        self,
        *,
        code: str,
    ) -> SubscriptionPlan | None:
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
    # الحصول على خطط الاشتراك النشطة.
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
    # الحصول على خطة التجربة المجانية.
    # ==============================================

    async def get_trial_plan(
        self,
    ) -> SubscriptionPlan | None:
        """
        الحصول على خطة التجربة المجانية.

        Returns:
            كائن SubscriptionPlan أو None
        """
        return await self.get_by_code(code="trial")

    # ==============================================
    # GET BY DISPLAY ORDER
    # الحصول على خطط الاشتراك مرتبة حسب ترتيب العرض.
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

    # ==============================================
    # ✏️ UPDATES
    # تحديث السعر الأساسي للخطة.
    # ==============================================

    # ==============================================
    # UPDATE PRICE
    # تحديث السعر الأساسي للخطة.
    # ==============================================

    async def update_price(
        self,
        *,
        plan_id: int,
        base_price: float,
    ) -> SubscriptionPlan | None:
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
    # تحديث نسبة التخفيض للخطة.
    # ==============================================

    async def update_discount(
        self,
        *,
        plan_id: int,
        plan_discount_percent: float,
    ) -> SubscriptionPlan | None:
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
    # تفعيل خطة اشتراك.
    # ==============================================

    async def activate(
        self,
        *,
        plan_id: int,
    ) -> SubscriptionPlan | None:
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
    # إلغاء تفعيل خطة اشتراك.
    # ==============================================

    async def deactivate(
        self,
        *,
        plan_id: int,
    ) -> SubscriptionPlan | None:
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
    # تحديث ترتيب عرض الخطة.
    # ==============================================

    async def update_display_order(
        self,
        *,
        plan_id: int,
        display_order: int,
    ) -> SubscriptionPlan | None:
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

    # ==============================================
    # 💰 CALCULATIONS
    # حساب السعر النهائي للخطة بعد التخفيض.
    # ==============================================

    # ==============================================
    # CALCULATE PRICE
    # حساب السعر النهائي للخطة بعد التخفيض.
    # ==============================================

    async def calculate_price(
        self,
        *,
        plan_id: int,
    ) -> Decimal:
        """
        حساب السعر النهائي للخطة بعد التخفيض.

        Args:
            plan_id: معرف الخطة

        Returns:
            السعر النهائي

        Raises:
            ValueError: إذا لم يتم العثور على الخطة
        """
        from app.services.business.pricing_service import calculate_plan_base_price

        return await calculate_plan_base_price(
            session=self.session, plan_id=plan_id, billing_cycle="monthly"
        )
