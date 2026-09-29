# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🔗 SUBSCRIPTION FEATURE REPOSITORY
# عمليات قاعدة البيانات لميزات الاشتراكات باستخدام SQLAlchemy
# Async SQLAlchemy Version
# ==============================================

from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from sqlalchemy import (
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logger import logger
from app.models.subscription import SubscriptionFeature
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

SubscriptionFeatureData = Dict[str, Any]
SubscriptionFeatureUpdateData = Dict[str, Any]
SubscriptionFeatureList = List[SubscriptionFeature]

# ==============================================
# 🔗 SUBSCRIPTION FEATURE REPOSITORY
# ==============================================


class SubscriptionFeatureRepository(
    BaseRepository[
        SubscriptionFeature,
        SubscriptionFeatureData,
        SubscriptionFeatureUpdateData,
    ]
):
    """
    مستودع ميزات الاشتراك - يوفر عمليات ربط الميزات بالاشتراكات.

    مسؤول عن:
        - إضافة ميزة إلى اشتراك
        - إزالة ميزة من اشتراك
        - جلب ميزات اشتراك معين
        - التحقق من وجود ميزة في اشتراك

    Attributes:
        model: نموذج SubscriptionFeature
        session: جلسة قاعدة البيانات غير المتزامنة
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة مستودع ميزات الاشتراك.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(SubscriptionFeature, session)

    # ==========================================
    # 🔍 BASE QUERY
    # ==========================================

    def _build_base_query(self):
        """
        بناء الاستعلام الأساسي لميزات الاشتراك.

        Returns:
            Select: استعلام SQLAlchemy الأساسي
        """
        return select(self.model)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET BY SUBSCRIPTION
    # ==============================================

    async def get_by_subscription(
        self,
        *,
        subscription_id: int,
    ) -> SubscriptionFeatureList:
        """
        الحصول على جميع ميزات اشتراك معين.

        Args:
            subscription_id: معرف الاشتراك

        Returns:
            قائمة ميزات الاشتراك
        """
        try:
            query = (
                self._build_base_query()
                .where(self.model.subscription_id == subscription_id)
                .order_by(self.model.id.asc())
            )

            result = await self.session.execute(query)

            return list(result.scalars().all())

        except Exception as e:
            logger.exception(
                "subscription_feature_repo_get_by_subscription_failed",
                extra={
                    "subscription_id": subscription_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET BY SUBSCRIPTION WITH FEATURE
    # ==============================================

    async def get_by_subscription_with_feature(
        self,
        *,
        subscription_id: int,
    ) -> SubscriptionFeatureList:
        """
        الحصول على ميزات اشتراك مع بيانات الميزة (Feature) محمّلة مسبقاً.

        Args:
            subscription_id: معرف الاشتراك

        Returns:
            قائمة ميزات الاشتراك مع بيانات الميزة
        """
        try:
            query = (
                self._build_base_query()
                .where(self.model.subscription_id == subscription_id)
                .options(selectinload(self.model.feature))
                .order_by(self.model.id.asc())
            )

            result = await self.session.execute(query)

            return list(result.scalars().all())

        except Exception as e:
            logger.exception(
                "subscription_feature_repo_get_with_feature_failed",
                extra={
                    "subscription_id": subscription_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET BY SUBSCRIPTION AND FEATURE
    # ==============================================

    async def get_by_subscription_and_feature(
        self,
        *,
        subscription_id: int,
        feature_id: int,
    ) -> Optional[SubscriptionFeature]:
        """
        الحصول على ربط محدد بين اشتراك وميزة.

        Args:
            subscription_id: معرف الاشتراك
            feature_id: معرف الميزة

        Returns:
            كائن SubscriptionFeature أو None
        """
        try:
            query = (
                self._build_base_query()
                .where(
                    self.model.subscription_id == subscription_id,
                    self.model.feature_id == feature_id,
                )
                .limit(1)
            )

            result = await self.session.execute(query)

            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(
                "subscription_feature_repo_get_by_subscription_and_feature_failed",
                extra={
                    "subscription_id": subscription_id,
                    "feature_id": feature_id,
                    "error": str(e),
                },
            )
            raise

    # ==========================================
    # ✅ EXISTENCE CHECKS
    # ==========================================

    # ==============================================
    # SUBSCRIPTION HAS FEATURE
    # ==============================================

    async def subscription_has_feature(
        self,
        *,
        subscription_id: int,
        feature_id: int,
    ) -> bool:
        """
        التحقق من وجود ميزة في اشتراك.

        Args:
            subscription_id: معرف الاشتراك
            feature_id: معرف الميزة

        Returns:
            True إذا كانت الميزة موجودة
        """
        try:
            query = (
                select(self.model.id)
                .where(
                    self.model.subscription_id == subscription_id,
                    self.model.feature_id == feature_id,
                )
                .limit(1)
            )

            result = await self.session.execute(query)

            return result.scalar_one_or_none() is not None

        except Exception as e:
            logger.exception(
                "subscription_feature_repo_has_feature_failed",
                extra={
                    "subscription_id": subscription_id,
                    "feature_id": feature_id,
                    "error": str(e),
                },
            )
            raise

    # ==========================================
    # ✏️ MUTATIONS
    # ==========================================

    # ==============================================
    # CREATE SUBSCRIPTION FEATURE
    # ==============================================

    async def create_subscription_feature(
        self,
        *,
        subscription_id: int,
        feature_id: int,
    ) -> SubscriptionFeature:
        """
        إضافة ميزة إلى اشتراك (إذا لم تكن موجودة مسبقاً).

        Args:
            subscription_id: معرف الاشتراك
            feature_id: معرف الميزة

        Returns:
            كائن SubscriptionFeature (الجديد أو الموجود)
        """
        # ✅ التحقق من وجود ربط مسبق
        existing = await self.get_by_subscription_and_feature(
            subscription_id=subscription_id,
            feature_id=feature_id,
        )

        if existing:
            logger.info(
                "subscription_feature_already_exists",
                extra={
                    "subscription_id": subscription_id,
                    "feature_id": feature_id,
                },
            )
            return existing

        subscription_feature = await self.create(
            data={
                "subscription_id": subscription_id,
                "feature_id": feature_id,
            },
        )

        logger.info(
            "subscription_feature_created",
            extra={
                "subscription_feature_id": subscription_feature.id,
                "subscription_id": subscription_id,
                "feature_id": feature_id,
            },
        )

        return subscription_feature

    # ==============================================
    # DELETE SUBSCRIPTION FEATURE
    # ==============================================

    async def delete_subscription_feature(
        self,
        *,
        subscription_id: int,
        feature_id: int,
    ) -> bool:
        """
        إزالة ميزة من اشتراك.

        Args:
            subscription_id: معرف الاشتراك
            feature_id: معرف الميزة

        Returns:
            True إذا تم الحذف، False إذا لم يوجد الربط
        """
        existing = await self.get_by_subscription_and_feature(
            subscription_id=subscription_id,
            feature_id=feature_id,
        )

        if not existing:
            logger.warning(
                "subscription_feature_not_found_for_delete",
                extra={
                    "subscription_id": subscription_id,
                    "feature_id": feature_id,
                },
            )
            return False

        await self.delete(id=existing.id)

        logger.info(
            "subscription_feature_deleted",
            extra={
                "subscription_feature_id": existing.id,
                "subscription_id": subscription_id,
                "feature_id": feature_id,
            },
        )

        return True

    # ==============================================
    # DELETE ALL BY SUBSCRIPTION
    # ==============================================

    async def delete_all_by_subscription(
        self,
        *,
        subscription_id: int,
    ) -> int:
        """
        حذف جميع ميزات اشتراك معين.

        Args:
            subscription_id: معرف الاشتراك

        Returns:
            عدد الميزات المحذوفة
        """
        features = await self.get_by_subscription(
            subscription_id=subscription_id,
        )

        count = 0

        for sf in features:
            await self.delete(id=sf.id)
            count += 1

        logger.info(
            "subscription_features_deleted",
            extra={
                "subscription_id": subscription_id,
                "deleted_count": count,
            },
        )

        return count

    # ==========================================
    # 📊 STATISTICS
    # ==========================================

    # ==============================================
    # COUNT BY SUBSCRIPTION
    # ==============================================

    async def count_by_subscription(
        self,
        *,
        subscription_id: int,
    ) -> int:
        """
        حساب عدد ميزات اشتراك معين.

        Args:
            subscription_id: معرف الاشتراك

        Returns:
            عدد الميزات
        """
        return await self.count(
            filters={"subscription_id": subscription_id},
        )


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# دوال متوافقة مع الاستيرادات القديمة (Psycopg3)
# ==============================================

# ==============================================
# CREATE SUBSCRIPTION FEATURE (COMPATIBILITY)
# ==============================================

async def create_subscription_feature(
    *,
    subscription_id: int,
    feature_id: int,
    session: AsyncSession,
) -> int:
    """
    إضافة ميزة إلى اشتراك (دالة متوافقة مع الإصدار القديم).

    Args:
        subscription_id: معرف الاشتراك
        feature_id: معرف الميزة
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        معرف SubscriptionFeature
    """
    repo = SubscriptionFeatureRepository(session=session)

    subscription_feature = await repo.create_subscription_feature(
        subscription_id=subscription_id,
        feature_id=feature_id,
    )

    return subscription_feature.id


# ==============================================
# GET SUBSCRIPTION FEATURES (COMPATIBILITY)
# ==============================================

async def get_subscription_features(
    *,
    subscription_id: int,
    session: AsyncSession,
) -> List[Dict[str, Any]]:
    """
    الحصول على ميزات اشتراك (دالة متوافقة مع الإصدار القديم).

    Args:
        subscription_id: معرف الاشتراك
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        قائمة ميزات الاشتراك
    """
    repo = SubscriptionFeatureRepository(session=session)

    subscription_features = await repo.get_by_subscription_with_feature(
        subscription_id=subscription_id,
    )

    result = []

    for sf in subscription_features:
        feature = sf.feature

        result.append({
            "id": sf.id,
            "subscription_id": sf.subscription_id,
            "feature_id": sf.feature_id,
            "feature_code": feature.code if feature else None,
            "feature_name": feature.name if feature else None,
            "feature_description": feature.description if feature else None,
        })

    return result


# ==============================================
# DELETE SUBSCRIPTION FEATURE (COMPATIBILITY)
# ==============================================

async def delete_subscription_feature(
    *,
    subscription_id: int,
    feature_id: int,
    session: AsyncSession,
) -> None:
    """
    إزالة ميزة من اشتراك (دالة متوافقة مع الإصدار القديم).

    Args:
        subscription_id: معرف الاشتراك
        feature_id: معرف الميزة
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = SubscriptionFeatureRepository(session=session)

    await repo.delete_subscription_feature(
        subscription_id=subscription_id,
        feature_id=feature_id,
    )


# ==============================================
# SUBSCRIPTION HAS FEATURE (COMPATIBILITY)
# ==============================================

async def subscription_has_feature(
    *,
    subscription_id: int,
    feature_id: int,
    session: AsyncSession,
) -> bool:
    """
    التحقق من وجود ميزة في اشتراك (دالة متوافقة مع الإصدار القديم).

    Args:
        subscription_id: معرف الاشتراك
        feature_id: معرف الميزة
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        True إذا كانت الميزة موجودة
    """
    repo = SubscriptionFeatureRepository(session=session)

    return await repo.subscription_has_feature(
        subscription_id=subscription_id,
        feature_id=feature_id,
    )
