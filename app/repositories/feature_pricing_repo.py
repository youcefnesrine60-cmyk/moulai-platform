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
)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models.feature_pricing import FeaturePricing
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

FeaturePricingData = dict[str, Any]
FeaturePricingUpdateData = dict[str, Any]
FeaturePricingList = list[FeaturePricing]

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
    ) -> FeaturePricing | None:
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
    ) -> FeaturePricing | None:
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
    ) -> FeaturePricing | None:
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
    ) -> FeaturePricing | None:
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
