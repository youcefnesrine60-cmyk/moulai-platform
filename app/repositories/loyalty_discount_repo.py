# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🎖️ LOYALTY DISCOUNT REPOSITORY
# عمليات قاعدة البيانات لخصومات الولاء باستخدام SQLAlchemy
# Async SQLAlchemy Version
# ==============================================

"""MoulAI operational module for loyalty discount repo.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from typing import (
    Any,
)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models.loyalty_discount import LoyaltyDiscount
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

LoyaltyDiscountData = dict[str, Any]
LoyaltyDiscountUpdateData = dict[str, Any]
LoyaltyDiscountList = list[LoyaltyDiscount]

# ==============================================
# 🎖️ LOYALTY DISCOUNT REPOSITORY
# ==============================================


class LoyaltyDiscountRepository(
    BaseRepository[
        LoyaltyDiscount,
        LoyaltyDiscountData,
        LoyaltyDiscountUpdateData,
    ]
):
    """
    مستودع خصومات الولاء - يوفر عمليات خاصة بخصومات الولاء.

    مسؤول عن:
        - عمليات CRUD الأساسية لخصومات الولاء
        - جلب جميع الخصومات مرتبة حسب عدد السنوات
        - حساب الخصم المطبق لعدد سنوات معين
        - جلب الخصومات حسب المالك

    Attributes:
        model: نموذج LoyaltyDiscount
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
        تهيئة مستودع خصومات الولاء.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(LoyaltyDiscount, session)

    # ==========================================
    # 🔍 BASE QUERY
    # ==========================================

    def _build_base_query(self):
        """
        بناء الاستعلام الأساسي لخصومات الولاء.

        Returns:
            Select: استعلام SQLAlchemy الأساسي
        """
        return select(self.model)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET ALL ORDERED
    # ==============================================

    async def get_all_ordered(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> LoyaltyDiscountList:
        """
        الحصول على جميع خصومات الولاء مرتبة حسب عدد السنوات المطلوبة.

        Args:
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة خصومات الولاء
        """
        try:
            query = (
                self._build_base_query()
                .order_by(self.model.years_required.asc())
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(query)

            return list(result.scalars().all())

        except Exception as e:
            logger.exception(
                "loyalty_discount_repo_get_all_ordered_failed",
                extra={"error": str(e)},
            )
            raise

    # ==============================================
    # GET DISCOUNT FOR YEARS
    # ==============================================

    async def get_discount_for_years(
        self,
        *,
        years: int,
    ) -> float:
        """
        حساب نسبة الخصم المطبقة لعدد سنوات معين.

        Args:
            years: عدد سنوات التعامل مع المنصة

        Returns:
            نسبة الخصم (0.0 إذا لم يوجد خصم مطابق)
        """
        try:
            query = (
                self._build_base_query()
                .where(self.model.years_required <= years)
                .order_by(self.model.years_required.desc())
                .limit(1)
            )

            result = await self.session.execute(query)

            discount = result.scalar_one_or_none()

            if not discount:
                return 0.0

            return float(discount.discount_percent)

        except Exception as e:
            logger.exception(
                "loyalty_discount_repo_get_for_years_failed",
                extra={
                    "years": years,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET BY OWNER
    # ==============================================

    async def get_by_owner(
        self,
        *,
        owner_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> LoyaltyDiscountList:
        """
        الحصول على خصومات الولاء الخاصة بمالك معين.

        Args:
            owner_id: معرف المالك
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة خصومات الولاء
        """
        try:
            query = (
                self._build_base_query()
                .where(self.model.owner_id == owner_id)
                .order_by(self.model.years_required.asc())
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(query)

            return list(result.scalars().all())

        except Exception as e:
            logger.exception(
                "loyalty_discount_repo_get_by_owner_failed",
                extra={
                    "owner_id": owner_id,
                    "error": str(e),
                },
            )
            raise

    # ==========================================
    # ✏️ MUTATIONS
    # ==============================================

    # ==============================================
    # UPDATE DISCOUNT PERCENT
    # ==============================================

    async def update_discount_percent(
        self,
        *,
        discount_id: int,
        discount_percent: float,
    ) -> LoyaltyDiscount | None:
        """
        تحديث نسبة الخصم.

        Args:
            discount_id: معرف الخصم
            discount_percent: نسبة الخصم الجديدة

        Returns:
            كائن LoyaltyDiscount المحدث أو None
        """
        logger.info(
            "loyalty_discount_repo_update_percent",
            extra={
                "discount_id": discount_id,
                "discount_percent": discount_percent,
            },
        )

        return await self.update(
            id=discount_id,
            data={"discount_percent": discount_percent},
        )

    # ==========================================
    # 📊 STATISTICS
    # ==============================================

    # ==============================================
    # COUNT ALL
    # ==============================================

    async def count_all(self) -> int:
        """
        حساب إجمالي عدد خصومات الولاء.

        Returns:
            عدد الخصومات
        """
        return await self.count()
