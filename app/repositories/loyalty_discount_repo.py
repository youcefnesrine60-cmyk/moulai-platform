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
    Dict,
    List,
    Optional,
)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models.loyalty_discount import LoyaltyDiscount
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

LoyaltyDiscountData = Dict[str, Any]
LoyaltyDiscountUpdateData = Dict[str, Any]
LoyaltyDiscountList = List[LoyaltyDiscount]

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
    ) -> Optional[LoyaltyDiscount]:
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


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# دوال متوافقة مع الاستيرادات القديمة (Psycopg3)
# ==============================================

# ==============================================
# CREATE LOYALTY DISCOUNT (COMPATIBILITY)
# ==============================================


async def create_loyalty_discount(
    *,
    years_required: int,
    discount_percent: float,
    session: AsyncSession,
) -> int:
    """
    إنشاء خصم ولاء جديد (دالة متوافقة مع الإصدار القديم).

    Args:
        years_required: عدد السنوات المطلوبة
        discount_percent: نسبة الخصم
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        معرف الخصم
    """
    repo = LoyaltyDiscountRepository(session=session)

    data: LoyaltyDiscountData = {
        "years_required": years_required,
        "discount_percent": discount_percent,
    }

    discount = await repo.create(data=data)

    logger.info(
        "loyalty_discount_created",
        extra={
            "discount_id": discount.id,
            "years_required": years_required,
            "discount_percent": discount_percent,
        },
    )

    return discount.id


# ==============================================
# GET LOYALTY DISCOUNT BY ID (COMPATIBILITY)
# ==============================================


async def get_loyalty_discount_by_id(
    *,
    discount_id: int,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على خصم ولاء بالمعرف (دالة متوافقة مع الإصدار القديم).

    Args:
        discount_id: معرف الخصم
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        قاموس بيانات الخصم أو None
    """
    repo = LoyaltyDiscountRepository(session=session)

    discount = await repo.get_by_id(id=discount_id)

    if not discount:
        return None

    return {
        "id": discount.id,
        "owner_id": discount.owner_id,
        "years_required": discount.years_required,
        "discount_percent": float(discount.discount_percent),
    }


# ==============================================
# GET ALL LOYALTY DISCOUNTS (COMPATIBILITY)
# ==============================================


async def get_all_loyalty_discounts(
    session: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    الحصول على جميع خصومات الولاء (دالة متوافقة مع الإصدار القديم).

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات

    Returns:
        قائمة خصومات الولاء
    """
    repo = LoyaltyDiscountRepository(session=session)

    discounts = await repo.get_all_ordered(skip=skip, limit=limit)

    result = []

    for discount in discounts:
        result.append(
            {
                "id": discount.id,
                "owner_id": discount.owner_id,
                "years_required": discount.years_required,
                "discount_percent": float(discount.discount_percent),
            }
        )

    return result


# ==============================================
# GET LOYALTY DISCOUNT FOR YEARS (COMPATIBILITY)
# ==============================================


async def get_loyalty_discount_for_years(
    *,
    years: int,
    session: AsyncSession,
) -> float:
    """
    حساب نسبة الخصم المطبقة لعدد سنوات (دالة متوافقة مع الإصدار القديم).

    Args:
        years: عدد سنوات التعامل مع المنصة
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        نسبة الخصم (0.0 إذا لم يوجد خصم مطابق)
    """
    repo = LoyaltyDiscountRepository(session=session)

    return await repo.get_discount_for_years(years=years)


# ==============================================
# UPDATE LOYALTY DISCOUNT (COMPATIBILITY)
# ==============================================


async def update_loyalty_discount(
    *,
    discount_id: int,
    discount_percent: float,
    session: AsyncSession,
) -> None:
    """
    تحديث نسبة خصم الولاء (دالة متوافقة مع الإصدار القديم).

    Args:
        discount_id: معرف الخصم
        discount_percent: نسبة الخصم الجديدة
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = LoyaltyDiscountRepository(session=session)

    await repo.update_discount_percent(
        discount_id=discount_id,
        discount_percent=discount_percent,
    )


# ==============================================
# DELETE LOYALTY DISCOUNT (COMPATIBILITY)
# ==============================================


async def delete_loyalty_discount(
    *,
    discount_id: int,
    session: AsyncSession,
) -> None:
    """
    حذف خصم ولاء (دالة متوافقة مع الإصدار القديم).

    Args:
        discount_id: معرف الخصم
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = LoyaltyDiscountRepository(session=session)

    await repo.delete(id=discount_id)

    logger.info(
        "loyalty_discount_deleted",
        extra={"discount_id": discount_id},
    )
