# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 💰 FEATURE PRICING REPOSITORY
# عمليات قاعدة البيانات لتسعير الميزات باستخدام SQLAlchemy
# Async SQLAlchemy Version
# ==============================================

"""MoulAI operational module for feature pricing repo.

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
from app.models.feature_pricing import FeaturePricing
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

FeaturePricingData = Dict[str, Any]
FeaturePricingUpdateData = Dict[str, Any]
FeaturePricingList = List[FeaturePricing]

# ==============================================
# 💰 FEATURE PRICING REPOSITORY
# ==============================================


class FeaturePricingRepository(
    BaseRepository[
        FeaturePricing,
        FeaturePricingData,
        FeaturePricingUpdateData,
    ]
):
    """
    مستودع تسعير الميزات - يوفر عمليات خاصة بتسعير الميزات.

    مسؤول عن:
        - عمليات CRUD الأساسية لتسعير الميزات
        - البحث حسب الميزة ودورة الفوترة
        - إدارة حالة النشاط (active)
        - تحديث السعر

    Attributes:
        model: نموذج FeaturePricing
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
        تهيئة مستودع تسعير الميزات.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(FeaturePricing, session)

    # ==========================================
    # 🔍 BASE QUERY
    # ==========================================

    def _build_base_query(self):
        """
        بناء الاستعلام الأساسي لتسعير الميزات.

        Returns:
            Select: استعلام SQLAlchemy الأساسي
        """
        return select(self.model)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET BY FEATURE AND CYCLE
    # ==============================================

    async def get_by_feature_and_cycle(
        self,
        *,
        feature_id: int,
        billing_cycle: str,
        only_active: bool = True,
    ) -> Optional[FeaturePricing]:
        """
        الحصول على تسعير ميزة حسب دورة الفوترة.

        Args:
            feature_id: معرف الميزة
            billing_cycle: دورة الفوترة (monthly, yearly)
            only_active: جلب التسعير النشط فقط

        Returns:
            كائن FeaturePricing أو None
        """
        try:
            query = self._build_base_query().where(
                self.model.feature_id == feature_id,
                self.model.billing_cycle == billing_cycle,
            )

            if only_active:
                query = query.where(self.model.active.is_(True))

            query = query.limit(1)

            result = await self.session.execute(query)

            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(
                "feature_pricing_repo_get_by_feature_and_cycle_failed",
                extra={
                    "feature_id": feature_id,
                    "billing_cycle": billing_cycle,
                    "only_active": only_active,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET LIST BY FEATURE
    # ==============================================

    async def get_list_by_feature(
        self,
        *,
        feature_id: int,
    ) -> FeaturePricingList:
        """
        الحصول على جميع أسعار ميزة معينة.

        Args:
            feature_id: معرف الميزة

        Returns:
            قائمة أسعار الميزة
        """
        try:
            query = (
                self._build_base_query()
                .where(self.model.feature_id == feature_id)
                .order_by(self.model.id.asc())
            )

            result = await self.session.execute(query)

            return list(result.scalars().all())

        except Exception as e:
            logger.exception(
                "feature_pricing_repo_get_list_by_feature_failed",
                extra={
                    "feature_id": feature_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET ALL ACTIVE
    # ==============================================

    async def get_all_active(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> FeaturePricingList:
        """
        الحصول على جميع أسعار الميزات النشطة.

        Args:
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة أسعار الميزات النشطة
        """
        try:
            query = (
                self._build_base_query()
                .where(self.model.active.is_(True))
                .order_by(self.model.id.asc())
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(query)

            return list(result.scalars().all())

        except Exception as e:
            logger.exception(
                "feature_pricing_repo_get_all_active_failed",
                extra={"error": str(e)},
            )
            raise

    # ==========================================
    # ✏️ MUTATIONS
    # ==========================================

    # ==============================================
    # UPDATE PRICE
    # ==============================================

    async def update_price(
        self,
        *,
        pricing_id: int,
        price: float,
    ) -> Optional[FeaturePricing]:
        """
        تحديث سعر ميزة.

        Args:
            pricing_id: معرف التسعير
            price: السعر الجديد

        Returns:
            كائن FeaturePricing المحدث أو None
        """
        logger.info(
            "feature_pricing_repo_update_price",
            extra={
                "pricing_id": pricing_id,
                "price": price,
            },
        )

        return await self.update(
            id=pricing_id,
            data={"price": price},
        )

    # ==============================================
    # ACTIVATE
    # ==============================================

    async def activate(
        self,
        *,
        pricing_id: int,
    ) -> Optional[FeaturePricing]:
        """
        تفعيل تسعير ميزة.

        Args:
            pricing_id: معرف التسعير

        Returns:
            كائن FeaturePricing المحدث أو None
        """
        logger.info(
            "feature_pricing_repo_activate",
            extra={"pricing_id": pricing_id},
        )

        return await self.update(
            id=pricing_id,
            data={"active": True},
        )

    # ==============================================
    # DEACTIVATE
    # ==============================================

    async def deactivate(
        self,
        *,
        pricing_id: int,
    ) -> Optional[FeaturePricing]:
        """
        إلغاء تفعيل تسعير ميزة.

        Args:
            pricing_id: معرف التسعير

        Returns:
            كائن FeaturePricing المحدث أو None
        """
        logger.info(
            "feature_pricing_repo_deactivate",
            extra={"pricing_id": pricing_id},
        )

        return await self.update(
            id=pricing_id,
            data={"active": False},
        )

    # ==========================================
    # 📊 STATISTICS
    # ==============================================

    # ==============================================
    # COUNT BY FEATURE
    # ==============================================

    async def count_by_feature(
        self,
        *,
        feature_id: int,
        only_active: bool = True,
    ) -> int:
        """
        حساب عدد أسعار ميزة معينة.

        Args:
            feature_id: معرف الميزة
            only_active: حساب التسعير النشط فقط

        Returns:
            عدد الأسعار
        """
        filters = {"feature_id": feature_id}

        if only_active:
            filters["active"] = True

        return await self.count(filters=filters)


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# دوال متوافقة مع الاستيرادات القديمة (Psycopg3)
# ==============================================

# ==============================================
# CREATE FEATURE PRICING (COMPATIBILITY)
# ==============================================


async def create_feature_pricing(
    *,
    feature_id: int,
    billing_cycle: str,
    price: float,
    active: bool = True,
    session: AsyncSession,
) -> int:
    """
    إنشاء تسعير ميزة جديدة (دالة متوافقة مع الإصدار القديم).

    Args:
        feature_id: معرف الميزة
        billing_cycle: دورة الفوترة
        price: السعر
        active: حالة النشاط
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        معرف التسعير
    """
    repo = FeaturePricingRepository(session=session)

    data: FeaturePricingData = {
        "feature_id": feature_id,
        "billing_cycle": billing_cycle,
        "price": price,
        "active": active,
    }

    pricing = await repo.create(data=data)

    logger.info(
        "feature_pricing_created",
        extra={
            "pricing_id": pricing.id,
            "feature_id": feature_id,
            "billing_cycle": billing_cycle,
        },
    )

    return pricing.id


# ==============================================
# GET FEATURE PRICING BY ID (COMPATIBILITY)
# ==============================================


async def get_feature_pricing_by_id(
    *,
    pricing_id: int,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على تسعير ميزة بالمعرف (دالة متوافقة مع الإصدار القديم).

    Args:
        pricing_id: معرف التسعير
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        قاموس بيانات التسعير أو None
    """
    repo = FeaturePricingRepository(session=session)

    pricing = await repo.get_by_id(id=pricing_id)

    if not pricing:
        logger.warning(
            "feature_pricing_not_found",
            extra={"pricing_id": pricing_id},
        )
        return None

    return {
        "id": pricing.id,
        "feature_id": pricing.feature_id,
        "billing_cycle": pricing.billing_cycle,
        "price": float(pricing.price),
        "active": pricing.active,
    }


# ==============================================
# GET FEATURE PRICING (COMPATIBILITY)
# ==============================================


async def get_feature_pricing(
    *,
    feature_id: int,
    billing_cycle: str,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على تسعير ميزة حسب دورة الفوترة (دالة متوافقة مع الإصدار القديم).

    Args:
        feature_id: معرف الميزة
        billing_cycle: دورة الفوترة
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        قاموس بيانات التسعير أو None
    """
    repo = FeaturePricingRepository(session=session)

    pricing = await repo.get_by_feature_and_cycle(
        feature_id=feature_id,
        billing_cycle=billing_cycle,
    )

    if not pricing:
        return None

    return {
        "id": pricing.id,
        "feature_id": pricing.feature_id,
        "billing_cycle": pricing.billing_cycle,
        "price": float(pricing.price),
        "active": pricing.active,
    }


# ==============================================
# GET FEATURE PRICING LIST (COMPATIBILITY)
# ==============================================


async def get_feature_pricing_list(
    *,
    feature_id: int,
    session: AsyncSession,
) -> List[Dict[str, Any]]:
    """
    الحصول على قائمة أسعار ميزة (دالة متوافقة مع الإصدار القديم).

    Args:
        feature_id: معرف الميزة
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        قائمة أسعار الميزة
    """
    repo = FeaturePricingRepository(session=session)

    pricings = await repo.get_list_by_feature(feature_id=feature_id)

    result = []

    for pricing in pricings:
        result.append(
            {
                "id": pricing.id,
                "feature_id": pricing.feature_id,
                "billing_cycle": pricing.billing_cycle,
                "price": float(pricing.price),
                "active": pricing.active,
            }
        )

    return result


# ==============================================
# GET ALL FEATURE PRICING (COMPATIBILITY)
# ==============================================


async def get_all_feature_pricing(
    session: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    الحصول على جميع أسعار الميزات النشطة (دالة متوافقة مع الإصدار القديم).

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات

    Returns:
        قائمة أسعار الميزات
    """
    repo = FeaturePricingRepository(session=session)

    pricings = await repo.get_all_active(skip=skip, limit=limit)

    result = []

    for pricing in pricings:
        result.append(
            {
                "id": pricing.id,
                "feature_id": pricing.feature_id,
                "billing_cycle": pricing.billing_cycle,
                "price": float(pricing.price),
                "active": pricing.active,
            }
        )

    return result


# ==============================================
# UPDATE FEATURE PRICE (COMPATIBILITY)
# ==============================================


async def update_feature_price(
    *,
    pricing_id: int,
    price: float,
    session: AsyncSession,
) -> None:
    """
    تحديث سعر ميزة (دالة متوافقة مع الإصدار القديم).

    Args:
        pricing_id: معرف التسعير
        price: السعر الجديد
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = FeaturePricingRepository(session=session)

    await repo.update_price(
        pricing_id=pricing_id,
        price=price,
    )


# ==============================================
# ACTIVATE FEATURE PRICING (COMPATIBILITY)
# ==============================================


async def activate_feature_pricing(
    *,
    pricing_id: int,
    session: AsyncSession,
) -> None:
    """
    تفعيل تسعير ميزة (دالة متوافقة مع الإصدار القديم).

    Args:
        pricing_id: معرف التسعير
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = FeaturePricingRepository(session=session)

    await repo.activate(pricing_id=pricing_id)


# ==============================================
# DEACTIVATE FEATURE PRICING (COMPATIBILITY)
# ==============================================


async def deactivate_feature_pricing(
    *,
    pricing_id: int,
    session: AsyncSession,
) -> None:
    """
    إلغاء تفعيل تسعير ميزة (دالة متوافقة مع الإصدار القديم).

    Args:
        pricing_id: معرف التسعير
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = FeaturePricingRepository(session=session)

    await repo.deactivate(pricing_id=pricing_id)


# ==============================================
# DELETE FEATURE PRICING (COMPATIBILITY)
# ==============================================


async def delete_feature_pricing(
    *,
    pricing_id: int,
    session: AsyncSession,
) -> None:
    """
    حذف تسعير ميزة (دالة متوافقة مع الإصدار القديم).

    Args:
        pricing_id: معرف التسعير
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = FeaturePricingRepository(session=session)

    await repo.delete(id=pricing_id)

    logger.info(
        "feature_pricing_deleted",
        extra={"pricing_id": pricing_id},
    )
