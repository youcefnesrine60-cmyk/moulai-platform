# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🏢 MULTI RESTAURANT DISCOUNT REPOSITORY
# عمليات قاعدة البيانات لخصومات المطاعم المتعددة باستخدام SQLAlchemy
# Async SQLAlchemy Version
# ==============================================

"""MoulAI operational module for multi restaurant discount repo.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from typing import (
    Any,
)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models.loyalty_discount import MultiRestaurantDiscount
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

MultiRestaurantDiscountData = dict[str, Any]
MultiRestaurantDiscountUpdateData = dict[str, Any]
MultiRestaurantDiscountList = list[MultiRestaurantDiscount]

# ==============================================
# 🏢 MULTI RESTAURANT DISCOUNT REPOSITORY
# ==============================================


class MultiRestaurantDiscountRepository(
    BaseRepository[
        MultiRestaurantDiscount,
        MultiRestaurantDiscountData,
        MultiRestaurantDiscountUpdateData,
    ]
):
    """
    مستودع خصومات المطاعم المتعددة - يوفر عمليات خاصة بها.

    مسؤول عن:
        - عمليات CRUD الأساسية لخصومات المطاعم المتعددة
        - جلب جميع الخصومات مرتبة حسب الحد الأدنى للمطاعم
        - حساب الخصم المطبق لعدد مطاعم معين
        - تحديث الخصم

    Attributes:
        model: نموذج MultiRestaurantDiscount
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
        تهيئة مستودع خصومات المطاعم المتعددة.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(MultiRestaurantDiscount, session)

    # ==========================================
    # 🔍 BASE QUERY
    # ==========================================

    def _build_base_query(self):
        """
        بناء الاستعلام الأساسي لخصومات المطاعم المتعددة.

        Returns:
            Select: استعلام SQLAlchemy الأساسي
        """
        return select(self.model)

    # ==========================================
    # 📖 QUERIES
    # ==============================================

    # ==============================================
    # GET ALL ORDERED
    # ==============================================

    async def get_all_ordered(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> MultiRestaurantDiscountList:
        """
        الحصول على جميع الخصومات مرتبة حسب الحد الأدنى لعدد المطاعم.

        Args:
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة الخصومات
        """
        try:
            query = (
                self._build_base_query()
                .order_by(self.model.min_restaurants.asc())
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(query)

            return list(result.scalars().all())

        except Exception as e:
            logger.exception(
                "multi_restaurant_discount_repo_get_all_ordered_failed",
                extra={"error": str(e)},
            )
            raise

    # ==============================================
    # GET DISCOUNT FOR COUNT
    # ==============================================

    async def get_discount_for_count(
        self,
        *,
        restaurants_count: int,
    ) -> MultiRestaurantDiscount | None:
        """
        الحصول على الخصم المطبق لعدد مطاعم معين.

        Args:
            restaurants_count: عدد المطاعم

        Returns:
            كائن MultiRestaurantDiscount أو None
        """
        try:
            query = (
                self._build_base_query()
                .where(self.model.min_restaurants <= restaurants_count)
                .order_by(self.model.min_restaurants.desc())
                .limit(1)
            )

            result = await self.session.execute(query)

            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(
                "multi_restaurant_discount_repo_get_for_count_failed",
                extra={
                    "restaurants_count": restaurants_count,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET DISCOUNT PERCENT FOR COUNT
    # ==============================================

    async def get_discount_percent_for_count(
        self,
        *,
        restaurants_count: int,
    ) -> float:
        """
        حساب نسبة الخصم المطبقة لعدد مطاعم معين.

        Args:
            restaurants_count: عدد المطاعم

        Returns:
            نسبة الخصم (0.0 إذا لم يوجد خصم مطابق)
        """
        discount = await self.get_discount_for_count(
            restaurants_count=restaurants_count,
        )

        if not discount:
            return 0.0

        return float(discount.discount_percent)

    # ==========================================
    # ✏️ MUTATIONS
    # ==============================================

    # ==============================================
    # UPDATE DISCOUNT
    # ==============================================

    async def update_discount(
        self,
        *,
        discount_id: int,
        min_restaurants: int,
        discount_percent: float,
    ) -> MultiRestaurantDiscount | None:
        """
        تحديث خصم المطاعم المتعددة.

        Args:
            discount_id: معرف الخصم
            min_restaurants: الحد الأدنى لعدد المطاعم
            discount_percent: نسبة الخصم الجديدة

        Returns:
            كائن MultiRestaurantDiscount المحدث أو None
        """
        logger.info(
            "multi_restaurant_discount_repo_update",
            extra={
                "discount_id": discount_id,
                "min_restaurants": min_restaurants,
                "discount_percent": discount_percent,
            },
        )

        return await self.update(
            id=discount_id,
            data={
                "min_restaurants": min_restaurants,
                "discount_percent": discount_percent,
            },
        )

    # ==========================================
    # 📊 STATISTICS
    # ==============================================

    # ==============================================
    # COUNT ALL
    # ==============================================

    async def count_all(self) -> int:
        """
        حساب إجمالي عدد خصومات المطاعم المتعددة.

        Returns:
            عدد الخصومات
        """
        return await self.count()
