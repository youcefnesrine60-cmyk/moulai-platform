# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📊 FEATURE USAGE LIMIT REPOSITORY
# عمليات قاعدة البيانات لحدود استخدام الميزات باستخدام SQLAlchemy
# Async SQLAlchemy Version
# ==============================================

"""MoulAI operational module for feature usage limits repo.

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
from app.models.feature_pricing import FeatureUsageLimit
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

FeatureUsageLimitData = Dict[str, Any]
FeatureUsageLimitUpdateData = Dict[str, Any]
FeatureUsageLimitList = List[FeatureUsageLimit]

# ==============================================
# 📊 FEATURE USAGE LIMIT REPOSITORY
# ==============================================


class FeatureUsageLimitRepository(
    BaseRepository[
        FeatureUsageLimit,
        FeatureUsageLimitData,
        FeatureUsageLimitUpdateData,
    ]
):
    """
    مستودع حدود استخدام الميزة - يوفر عمليات خاصة بحدود الاستخدام.

    مسؤول عن:
        - عمليات CRUD الأساسية لحدود الاستخدام
        - جلب حدود خطة معينة
        - جلب حدود ميزة معينة
        - جلب حد محدد لخطة/ميزة
        - تحديث حد شهري ونوع الحد

    Attributes:
        model: نموذج FeatureUsageLimit
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
        تهيئة مستودع حدود استخدام الميزة.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(FeatureUsageLimit, session)

    # ==========================================
    # 🔍 BASE QUERY
    # ==========================================

    def _build_base_query(self):
        """
        بناء الاستعلام الأساسي لحدود الاستخدام.

        Returns:
            Select: استعلام SQLAlchemy الأساسي
        """
        return select(self.model)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET PLAN FEATURE LIMIT
    # ==============================================

    async def get_plan_feature_limit(
        self,
        *,
        plan_id: int,
        feature_id: int,
    ) -> Optional[FeatureUsageLimit]:
        """
        الحصول على حد استخدام محدد لخطة/ميزة.

        Args:
            plan_id: معرف الخطة
            feature_id: معرف الميزة

        Returns:
            كائن FeatureUsageLimit أو None
        """
        try:
            query = (
                self._build_base_query()
                .where(
                    self.model.plan_id == plan_id,
                    self.model.feature_id == feature_id,
                )
                .limit(1)
            )

            result = await self.session.execute(query)

            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(
                "feature_usage_limit_repo_get_plan_feature_failed",
                extra={
                    "plan_id": plan_id,
                    "feature_id": feature_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET PLAN LIMITS
    # ==============================================

    async def get_plan_limits(
        self,
        *,
        plan_id: int,
    ) -> FeatureUsageLimitList:
        """
        الحصول على جميع حدود الاستخدام لخطة معينة.

        Args:
            plan_id: معرف الخطة

        Returns:
            قائمة حدود الاستخدام
        """
        try:
            query = (
                self._build_base_query()
                .where(self.model.plan_id == plan_id)
                .order_by(self.model.id.asc())
            )

            result = await self.session.execute(query)

            return list(result.scalars().all())

        except Exception as e:
            logger.exception(
                "feature_usage_limit_repo_get_plan_limits_failed",
                extra={
                    "plan_id": plan_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET FEATURE LIMITS
    # ==============================================

    async def get_feature_limits(
        self,
        *,
        feature_id: int,
    ) -> FeatureUsageLimitList:
        """
        الحصول على جميع حدود الاستخدام لميزة معينة.

        Args:
            feature_id: معرف الميزة

        Returns:
            قائمة حدود الاستخدام
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
                "feature_usage_limit_repo_get_feature_limits_failed",
                extra={
                    "feature_id": feature_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET ALL LIMITS
    # ==============================================

    async def get_all_limits(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> FeatureUsageLimitList:
        """
        الحصول على جميع حدود الاستخدام.

        Args:
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة حدود الاستخدام
        """
        try:
            query = (
                self._build_base_query()
                .order_by(self.model.id.asc())
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(query)

            return list(result.scalars().all())

        except Exception as e:
            logger.exception(
                "feature_usage_limit_repo_get_all_failed",
                extra={"error": str(e)},
            )
            raise

    # ==========================================
    # ✏️ MUTATIONS
    # ==============================================

    # ==============================================
    # UPDATE LIMIT
    # ==============================================

    async def update_limit(
        self,
        *,
        limit_id: int,
        monthly_limit: Optional[int],
        limit_type: Optional[str],
    ) -> Optional[FeatureUsageLimit]:
        """
        تحديث حد الاستخدام (الحد الشهري ونوع الحد).

        Args:
            limit_id: معرف الحد
            monthly_limit: الحد الشهري الجديد
            limit_type: نوع الحد (hard, soft)

        Returns:
            كائن FeatureUsageLimit المحدث أو None
        """
        logger.info(
            "feature_usage_limit_repo_update",
            extra={
                "limit_id": limit_id,
                "monthly_limit": monthly_limit,
                "limit_type": limit_type,
            },
        )

        return await self.update(
            id=limit_id,
            data={
                "monthly_limit": monthly_limit,
                "limit_type": limit_type,
            },
        )

    # ==========================================
    # 📊 STATISTICS
    # ==============================================

    # ==============================================
    # COUNT BY PLAN
    # ==============================================

    async def count_by_plan(
        self,
        *,
        plan_id: int,
    ) -> int:
        """
        حساب عدد حدود الاستخدام لخطة معينة.

        Args:
            plan_id: معرف الخطة

        Returns:
            عدد الحدود
        """
        return await self.count(filters={"plan_id": plan_id})
