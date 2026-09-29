# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📦 PLAN FEATURE REPOSITORY
# عمليات قاعدة البيانات لميزات الخطط باستخدام SQLAlchemy
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
from app.models.subscription import PlanFeature
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

PlanFeatureData = Dict[str, Any]
PlanFeatureUpdateData = Dict[str, Any]
PlanFeatureList = List[PlanFeature]

# ==============================================
# 📦 PLAN FEATURE REPOSITORY
# ==============================================


class PlanFeatureRepository(
    BaseRepository[
        PlanFeature,
        PlanFeatureData,
        PlanFeatureUpdateData,
    ]
):
    """
    مستودع ميزات الخطة - يوفر عمليات ربط الميزات بالخطط.

    مسؤول عن:
        - إضافة/إزالة الميزات من الخطط
        - التحقق من وجود ميزة في خطة
        - جلب ميزات خطة معينة
        - تحديث حالة التضمين

    Attributes:
        model: نموذج PlanFeature
        session: جلسة قاعدة البيانات غير المتزامنة
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة مستودع ميزات الخطة.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(PlanFeature, session)

    # ==========================================
    # 🔍 BASE QUERY
    # ==========================================

    def _build_base_query(self):
        """
        بناء الاستعلام الأساسي لميزات الخطط.

        Returns:
            Select: استعلام SQLAlchemy الأساسي
        """
        return select(self.model)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET BY PLAN
    # ==============================================

    async def get_by_plan(
        self,
        *,
        plan_id: int,
    ) -> PlanFeatureList:
        """
        الحصول على جميع ميزات خطة معينة.

        Args:
            plan_id: معرف الخطة

        Returns:
            قائمة ميزات الخطة
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
                "plan_feature_repo_get_by_plan_failed",
                extra={
                    "plan_id": plan_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET INCLUDED BY PLAN
    # ==============================================

    async def get_included_by_plan(
        self,
        *,
        plan_id: int,
    ) -> PlanFeatureList:
        """
        الحصول على الميزات المدرجة فقط في خطة معينة.

        Args:
            plan_id: معرف الخطة

        Returns:
            قائمة ميزات الخطة المدرجة
        """
        try:
            query = (
                self._build_base_query()
                .where(
                    self.model.plan_id == plan_id,
                    self.model.included.is_(True),
                )
                .order_by(self.model.id.asc())
            )

            result = await self.session.execute(query)

            return list(result.scalars().all())

        except Exception as e:
            logger.exception(
                "plan_feature_repo_get_included_failed",
                extra={
                    "plan_id": plan_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET BY PLAN AND FEATURE
    # ==============================================

    async def get_by_plan_and_feature(
        self,
        *,
        plan_id: int,
        feature_id: int,
    ) -> Optional[PlanFeature]:
        """
        الحصول على ربط محدد بين خطة وميزة.

        Args:
            plan_id: معرف الخطة
            feature_id: معرف الميزة

        Returns:
            كائن PlanFeature أو None
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
                "plan_feature_repo_get_by_plan_and_feature_failed",
                extra={
                    "plan_id": plan_id,
                    "feature_id": feature_id,
                    "error": str(e),
                },
            )
            raise

    # ==========================================
    # ✅ EXISTENCE CHECKS
    # ==========================================

    # ==============================================
    # PLAN HAS FEATURE
    # ==============================================

    async def plan_has_feature(
        self,
        *,
        plan_id: int,
        feature_id: int,
    ) -> bool:
        """
        التحقق من أن خطة تحتوي على ميزة مدرجة.

        Args:
            plan_id: معرف الخطة
            feature_id: معرف الميزة

        Returns:
            True إذا كانت الميزة مدرجة
        """
        try:
            query = (
                select(self.model.id)
                .where(
                    self.model.plan_id == plan_id,
                    self.model.feature_id == feature_id,
                    self.model.included.is_(True),
                )
                .limit(1)
            )

            result = await self.session.execute(query)

            return result.scalar_one_or_none() is not None

        except Exception as e:
            logger.exception(
                "plan_feature_repo_has_feature_failed",
                extra={
                    "plan_id": plan_id,
                    "feature_id": feature_id,
                    "error": str(e),
                },
            )
            raise

    # ==========================================
    # ✏️ MUTATIONS
    # ==========================================

    # ==============================================
    # ADD FEATURE TO PLAN
    # ==============================================

    async def add_feature_to_plan(
        self,
        *,
        plan_id: int,
        feature_id: int,
        included: bool = True,
    ) -> PlanFeature:
        """
        إضافة ميزة إلى خطة (أو تحديث الحالة إذا كانت موجودة).

        Args:
            plan_id: معرف الخطة
            feature_id: معرف الميزة
            included: هل الميزة مدرجة

        Returns:
            كائن PlanFeature
        """
        existing = await self.get_by_plan_and_feature(
            plan_id=plan_id,
            feature_id=feature_id,
        )

        if existing:
            updated = await self.update(
                id=existing.id,
                data={"included": included},
            )

            logger.info(
                "plan_feature_updated",
                extra={
                    "plan_id": plan_id,
                    "feature_id": feature_id,
                    "included": included,
                },
            )

            return updated

        plan_feature = await self.create(
            data={
                "plan_id": plan_id,
                "feature_id": feature_id,
                "included": included,
            },
        )

        logger.info(
            "plan_feature_created",
            extra={
                "plan_feature_id": plan_feature.id,
                "plan_id": plan_id,
                "feature_id": feature_id,
            },
        )

        return plan_feature

    # ==============================================
    # UPDATE INCLUDED STATUS
    # ==============================================

    async def update_included_status(
        self,
        *,
        plan_id: int,
        feature_id: int,
        included: bool,
    ) -> Optional[PlanFeature]:
        """
        تحديث حالة تضمين الميزة في الخطة.

        Args:
            plan_id: معرف الخطة
            feature_id: معرف الميزة
            included: الحالة الجديدة

        Returns:
            كائن PlanFeature المحدث أو None
        """
        existing = await self.get_by_plan_and_feature(
            plan_id=plan_id,
            feature_id=feature_id,
        )

        if not existing:
            return None

        updated = await self.update(
            id=existing.id,
            data={"included": included},
        )

        logger.info(
            "plan_feature_included_updated",
            extra={
                "plan_id": plan_id,
                "feature_id": feature_id,
                "included": included,
            },
        )

        return updated

    # ==============================================
    # REMOVE FEATURE FROM PLAN
    # ==============================================

    async def remove_feature_from_plan(
        self,
        *,
        plan_id: int,
        feature_id: int,
    ) -> bool:
        """
        إزالة ميزة من خطة.

        Args:
            plan_id: معرف الخطة
            feature_id: معرف الميزة

        Returns:
            True إذا تم الحذف
        """
        existing = await self.get_by_plan_and_feature(
            plan_id=plan_id,
            feature_id=feature_id,
        )

        if not existing:
            return False

        await self.delete(id=existing.id)

        logger.info(
            "feature_removed_from_plan",
            extra={
                "plan_id": plan_id,
                "feature_id": feature_id,
            },
        )

        return True

    # ==========================================
    # 📊 STATISTICS
    # ==========================================

    # ==============================================
    # COUNT BY PLAN
    # ==============================================

    async def count_by_plan(
        self,
        *,
        plan_id: int,
    ) -> int:
        """
        حساب عدد الميزات في خطة.

        Args:
            plan_id: معرف الخطة

        Returns:
            عدد الميزات
        """
        return await self.count(filters={"plan_id": plan_id})


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# دوال متوافقة مع الاستيرادات القديمة (Psycopg3)
# ==============================================

# ==============================================
# ADD FEATURE TO PLAN (COMPATIBILITY)
# ==============================================

async def add_feature_to_plan(
    *,
    plan_id: int,
    feature_id: int,
    included: bool = True,
    session: AsyncSession,
) -> int:
    """
    إضافة ميزة إلى خطة (دالة متوافقة مع الإصدار القديم).

    Args:
        plan_id: معرف الخطة
        feature_id: معرف الميزة
        included: هل الميزة مدرجة
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        معرف PlanFeature
    """
    repo = PlanFeatureRepository(session=session)

    plan_feature = await repo.add_feature_to_plan(
        plan_id=plan_id,
        feature_id=feature_id,
        included=included,
    )

    return plan_feature.id


# ==============================================
# GET PLAN FEATURES (COMPATIBILITY)
# ==============================================

async def get_plan_features(
    *,
    plan_id: int,
    session: AsyncSession,
) -> List[Dict[str, Any]]:
    """
    الحصول على ميزات خطة (دالة متوافقة مع الإصدار القديم).

    Args:
        plan_id: معرف الخطة
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        قائمة ميزات الخطة
    """
    repo = PlanFeatureRepository(session=session)

    plan_features = await repo.get_by_plan(plan_id=plan_id)

    result = []

    for pf in plan_features:
        result.append({
            "id": pf.id,
            "plan_id": pf.plan_id,
            "feature_id": pf.feature_id,
            "included": pf.included,
            "created_at": pf.created_at,
        })

    return result


# ==============================================
# GET INCLUDED FEATURES (COMPATIBILITY)
# ==============================================

async def get_included_features(
    *,
    plan_id: int,
    session: AsyncSession,
) -> List[Dict[str, Any]]:
    """
    الحصول على الميزات المدرجة في خطة (دالة متوافقة مع الإصدار القديم).

    Args:
        plan_id: معرف الخطة
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        قائمة الميزات المدرجة
    """
    repo = PlanFeatureRepository(session=session)

    plan_features = await repo.get_included_by_plan(plan_id=plan_id)

    result = []

    for pf in plan_features:
        result.append({
            "id": pf.id,
            "plan_id": pf.plan_id,
            "feature_id": pf.feature_id,
            "included": pf.included,
            "created_at": pf.created_at,
        })

    return result


# ==============================================
# PLAN HAS FEATURE (COMPATIBILITY)
# ==============================================

async def plan_has_feature(
    *,
    plan_id: int,
    feature_id: int,
    session: AsyncSession,
) -> bool:
    """
    التحقق من وجود ميزة في خطة (دالة متوافقة مع الإصدار القديم).

    Args:
        plan_id: معرف الخطة
        feature_id: معرف الميزة
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        True إذا كانت الميزة موجودة ومدرجة
    """
    repo = PlanFeatureRepository(session=session)

    return await repo.plan_has_feature(
        plan_id=plan_id,
        feature_id=feature_id,
    )


# ==============================================
# REMOVE FEATURE FROM PLAN (COMPATIBILITY)
# ==============================================

async def remove_feature_from_plan(
    *,
    plan_id: int,
    feature_id: int,
    session: AsyncSession,
) -> None:
    """
    إزالة ميزة من خطة (دالة متوافقة مع الإصدار القديم).

    Args:
        plan_id: معرف الخطة
        feature_id: معرف الميزة
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = PlanFeatureRepository(session=session)

    await repo.remove_feature_from_plan(
        plan_id=plan_id,
        feature_id=feature_id,
    )


# ==============================================
# UPDATE FEATURE INCLUDED STATUS (COMPATIBILITY)
# ==============================================

async def update_feature_included_status(
    *,
    plan_id: int,
    feature_id: int,
    included: bool,
    session: AsyncSession,
) -> None:
    """
    تحديث حالة تضمين الميزة (دالة متوافقة مع الإصدار القديم).

    Args:
        plan_id: معرف الخطة
        feature_id: معرف الميزة
        included: الحالة الجديدة
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = PlanFeatureRepository(session=session)

    await repo.update_included_status(
        plan_id=plan_id,
        feature_id=feature_id,
        included=included,
    )