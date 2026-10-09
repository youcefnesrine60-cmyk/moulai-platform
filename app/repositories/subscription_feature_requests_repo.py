# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🧾 SUBSCRIPTION FEATURE REQUEST REPOSITORY
# عمليات قاعدة البيانات لطلبات ميزات الاشتراك باستخدام SQLAlchemy
# Async SQLAlchemy Version
# ==============================================

"""MoulAI operational module for subscription feature requests repo.

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
from app.models.subscription import SubscriptionFeatureRequest
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

SubscriptionFeatureRequestData = Dict[str, Any]
SubscriptionFeatureRequestUpdateData = Dict[str, Any]
SubscriptionFeatureRequestList = List[SubscriptionFeatureRequest]

# ==============================================
# 🧾 SUBSCRIPTION FEATURE REQUEST REPOSITORY
# ==============================================


class SubscriptionFeatureRequestRepository(
    BaseRepository[
        SubscriptionFeatureRequest,
        SubscriptionFeatureRequestData,
        SubscriptionFeatureRequestUpdateData,
    ]
):
    """
    مستودع طلبات ميزات الاشتراك - يوفر عمليات خاصة بها.

    مسؤول عن:
        - عمليات CRUD الأساسية لطلبات الميزات
        - جلب طلبات اشتراك معين
        - التحقق من وجود طلب مسبق
        - حذف طلبات اشتراك معين

    Attributes:
        model: نموذج SubscriptionFeatureRequest
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
        تهيئة مستودع طلبات ميزات الاشتراك.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(SubscriptionFeatureRequest, session)

    # ==========================================
    # 🔍 BASE QUERY
    # ==========================================

    def _build_base_query(self):
        """
        بناء الاستعلام الأساسي لطلبات ميزات الاشتراك.

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
    ) -> SubscriptionFeatureRequestList:
        """
        الحصول على جميع طلبات الميزات لاشتراك معين.

        Args:
            subscription_id: معرف الاشتراك

        Returns:
            قائمة طلبات الميزات
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
                "subscription_feature_request_repo_get_by_subscription_failed",
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
    ) -> Optional[SubscriptionFeatureRequest]:
        """
        الحصول على طلب محدد بين اشتراك وميزة.

        Args:
            subscription_id: معرف الاشتراك
            feature_id: معرف الميزة

        Returns:
            كائن SubscriptionFeatureRequest أو None
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
                "subscription_feature_request_repo_get_by_subscription_and_feature_failed",
                extra={
                    "subscription_id": subscription_id,
                    "feature_id": feature_id,
                    "error": str(e),
                },
            )
            raise

    # ==========================================
    # ✅ EXISTENCE CHECKS
    # ==============================================

    # ==============================================
    # REQUEST EXISTS
    # ==============================================

    async def request_exists(
        self,
        *,
        subscription_id: int,
        feature_id: int,
    ) -> bool:
        """
        التحقق من وجود طلب ميزة لاشتراك معين.

        Args:
            subscription_id: معرف الاشتراك
            feature_id: معرف الميزة

        Returns:
            True إذا كان الطلب موجوداً
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
                "subscription_feature_request_repo_exists_failed",
                extra={
                    "subscription_id": subscription_id,
                    "feature_id": feature_id,
                    "error": str(e),
                },
            )
            raise

    # ==========================================
    # ✏️ MUTATIONS
    # ==============================================

    # ==============================================
    # CREATE REQUEST
    # ==============================================

    async def create_request(
        self,
        *,
        subscription_id: int,
        feature_id: int,
    ) -> SubscriptionFeatureRequest:
        """
        إنشاء طلب ميزة جديد لاشتراك (إذا لم يكن موجوداً).

        Args:
            subscription_id: معرف الاشتراك
            feature_id: معرف الميزة

        Returns:
            كائن SubscriptionFeatureRequest (الجديد أو الموجود)
        """
        # ✅ التحقق من وجود طلب مسبق
        existing = await self.get_by_subscription_and_feature(
            subscription_id=subscription_id,
            feature_id=feature_id,
        )

        if existing:
            logger.info(
                "subscription_feature_request_already_exists",
                extra={
                    "request_id": existing.id,
                    "subscription_id": subscription_id,
                    "feature_id": feature_id,
                },
            )
            return existing

        request = await self.create(
            data={
                "subscription_id": subscription_id,
                "feature_id": feature_id,
            },
        )

        logger.info(
            "subscription_feature_request_created",
            extra={
                "request_id": request.id,
                "subscription_id": subscription_id,
                "feature_id": feature_id,
            },
        )

        return request

    # ==============================================
    # DELETE BY SUBSCRIPTION
    # ==============================================

    async def delete_by_subscription(
        self,
        *,
        subscription_id: int,
    ) -> int:
        """
        حذف جميع طلبات الميزات لاشتراك معين.

        Args:
            subscription_id: معرف الاشتراك

        Returns:
            عدد الطلبات المحذوفة
        """
        requests = await self.get_by_subscription(
            subscription_id=subscription_id,
        )

        count = 0

        for request in requests:
            await self.delete(id=request.id)
            count += 1

        logger.info(
            "subscription_feature_requests_deleted",
            extra={
                "subscription_id": subscription_id,
                "deleted_count": count,
            },
        )

        return count

    # ==========================================
    # 📊 STATISTICS
    # ==============================================

    # ==============================================
    # COUNT BY SUBSCRIPTION
    # ==============================================

    async def count_by_subscription(
        self,
        *,
        subscription_id: int,
    ) -> int:
        """
        حساب عدد طلبات الميزات لاشتراك معين.

        Args:
            subscription_id: معرف الاشتراك

        Returns:
            عدد الطلبات
        """
        return await self.count(
            filters={"subscription_id": subscription_id},
        )


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# دوال متوافقة مع الاستيرادات القديمة (Psycopg3)
# ==============================================

# ==============================================
# CREATE FEATURE REQUEST (COMPATIBILITY)
# ==============================================


async def create_feature_request(
    *,
    subscription_id: int,
    feature_id: int,
    session: AsyncSession,
) -> int:
    """
    إنشاء طلب ميزة جديد (دالة متوافقة مع الإصدار القديم).

    Args:
        subscription_id: معرف الاشتراك
        feature_id: معرف الميزة
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        معرف الطلب
    """
    repo = SubscriptionFeatureRequestRepository(session=session)

    request = await repo.create_request(
        subscription_id=subscription_id,
        feature_id=feature_id,
    )

    return request.id


# ==============================================
# GET SUBSCRIPTION FEATURE REQUESTS (COMPATIBILITY)
# ==============================================


async def get_subscription_feature_requests(
    *,
    subscription_id: int,
    session: AsyncSession,
) -> List[Dict[str, Any]]:
    """
    الحصول على طلبات ميزات اشتراك (دالة متوافقة مع الإصدار القديم).

    Args:
        subscription_id: معرف الاشتراك
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        قائمة طلبات الميزات
    """
    repo = SubscriptionFeatureRequestRepository(session=session)

    requests = await repo.get_by_subscription(
        subscription_id=subscription_id,
    )

    result = []

    for request in requests:
        result.append(
            {
                "id": request.id,
                "subscription_id": request.subscription_id,
                "feature_id": request.feature_id,
                "created_at": request.created_at,
            }
        )

    return result


# ==============================================
# DELETE SUBSCRIPTION FEATURE REQUESTS (COMPATIBILITY)
# ==============================================


async def delete_subscription_feature_requests(
    *,
    subscription_id: int,
    session: AsyncSession,
) -> None:
    """
    حذف طلبات ميزات اشتراك (دالة متوافقة مع الإصدار القديم).

    Args:
        subscription_id: معرف الاشتراك
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = SubscriptionFeatureRequestRepository(session=session)

    await repo.delete_by_subscription(
        subscription_id=subscription_id,
    )
