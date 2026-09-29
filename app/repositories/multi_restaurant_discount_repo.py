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

from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models.loyalty_discount import MultiRestaurantDiscount
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

MultiRestaurantDiscountData = Dict[str, Any]
MultiRestaurantDiscountUpdateData = Dict[str, Any]
MultiRestaurantDiscountList = List[MultiRestaurantDiscount]

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
    ) -> Optional[MultiRestaurantDiscount]:
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
    ) -> Optional[MultiRestaurantDiscount]:
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


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# دوال متوافقة مع الاستيرادات القديمة (Psycopg3)
# ==============================================

# ==============================================
# CREATE MULTI RESTAURANT DISCOUNT (COMPATIBILITY)
# ==============================================

async def create_multi_restaurant_discount(
    *,
    min_restaurants: int,
    discount_percent: float,
    session: AsyncSession,
) -> int:
    """
    إنشاء خصم مطاعم متعددة جديد (دالة متوافقة مع الإصدار القديم).

    Args:
        min_restaurants: الحد الأدنى لعدد المطاعم
        discount_percent: نسبة الخصم
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        معرف الخصم
    """
    repo = MultiRestaurantDiscountRepository(session=session)

    data: MultiRestaurantDiscountData = {
        "min_restaurants": min_restaurants,
        "discount_percent": discount_percent,
    }

    discount = await repo.create(data=data)

    logger.info(
        "multi_restaurant_discount_created",
        extra={
            "discount_id": discount.id,
            "min_restaurants": min_restaurants,
        },
    )

    return discount.id


# ==============================================
# GET BY ID (COMPATIBILITY)
# ==============================================

async def get_multi_restaurant_discount_by_id(
    *,
    discount_id: int,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على خصم مطاعم متعددة بالمعرف (دالة متوافقة مع الإصدار القديم).

    Args:
        discount_id: معرف الخصم
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        قاموس بيانات الخصم أو None
    """
    repo = MultiRestaurantDiscountRepository(session=session)

    discount = await repo.get_by_id(id=discount_id)

    if not discount:
        return None

    return {
        "id": discount.id,
        "min_restaurants": discount.min_restaurants,
        "discount_percent": float(discount.discount_percent),
    }


# ==============================================
# GET ALL (COMPATIBILITY)
# ==============================================

async def get_all_multi_restaurant_discounts(
    session: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    الحصول على جميع خصومات المطاعم المتعددة (دالة متوافقة مع الإصدار القديم).

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات

    Returns:
        قائمة الخصومات
    """
    repo = MultiRestaurantDiscountRepository(session=session)

    discounts = await repo.get_all_ordered(skip=skip, limit=limit)

    result = []

    for discount in discounts:
        result.append({
            "id": discount.id,
            "min_restaurants": discount.min_restaurants,
            "discount_percent": float(discount.discount_percent),
        })

    return result


# ==============================================
# GET APPLICABLE DISCOUNT (COMPATIBILITY)
# ==============================================

async def get_multi_restaurant_discount_for_count(
    *,
    restaurants_count: int,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على الخصم المطبق لعدد مطاعم (دالة متوافقة مع الإصدار القديم).

    Args:
        restaurants_count: عدد المطاعم
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        قاموس بيانات الخصم أو None
    """
    repo = MultiRestaurantDiscountRepository(session=session)

    discount = await repo.get_discount_for_count(
        restaurants_count=restaurants_count,
    )

    if not discount:
        return None

    return {
        "id": discount.id,
        "min_restaurants": discount.min_restaurants,
        "discount_percent": float(discount.discount_percent),
    }


# ==============================================
# GET DISCOUNT PERCENT (COMPATIBILITY)
# ==============================================

async def get_multi_restaurant_discount_percent(
    *,
    restaurants_count: int,
    session: AsyncSession,
) -> float:
    """
    حساب نسبة الخصم لعدد مطاعم (دالة متوافقة مع الإصدار القديم).

    Args:
        restaurants_count: عدد المطاعم
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        نسبة الخصم (0.0 إذا لم يوجد)
    """
    repo = MultiRestaurantDiscountRepository(session=session)

    return await repo.get_discount_percent_for_count(
        restaurants_count=restaurants_count,
    )


# ==============================================
# UPDATE DISCOUNT (COMPATIBILITY)
# ==============================================

async def update_multi_restaurant_discount(
    *,
    discount_id: int,
    min_restaurants: int,
    discount_percent: float,
    session: AsyncSession,
) -> None:
    """
    تحديث خصم المطاعم المتعددة (دالة متوافقة مع الإصدار القديم).

    Args:
        discount_id: معرف الخصم
        min_restaurants: الحد الأدنى لعدد المطاعم
        discount_percent: نسبة الخصم الجديدة
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = MultiRestaurantDiscountRepository(session=session)

    await repo.update_discount(
        discount_id=discount_id,
        min_restaurants=min_restaurants,
        discount_percent=discount_percent,
    )


# ==============================================
# DELETE DISCOUNT (COMPATIBILITY)
# ==============================================

async def delete_multi_restaurant_discount(
    *,
    discount_id: int,
    session: AsyncSession,
) -> None:
    """
    حذف خصم مطاعم متعددة (دالة متوافقة مع الإصدار القديم).

    Args:
        discount_id: معرف الخصم
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = MultiRestaurantDiscountRepository(session=session)

    await repo.delete(id=discount_id)

    logger.info(
        "multi_restaurant_discount_deleted",
        extra={"discount_id": discount_id},
    )