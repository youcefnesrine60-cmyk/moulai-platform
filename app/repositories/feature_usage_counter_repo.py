# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📊 FEATURE USAGE COUNTER REPOSITORY
# عمليات قاعدة البيانات لعدادات استخدام الميزات باستخدام SQLAlchemy
# Async SQLAlchemy Version
# ==============================================

"""MoulAI operational module for feature usage counter repo.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models.feature_pricing import FeatureUsageCounter
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

FeatureUsageCounterData = Dict[str, Any]
FeatureUsageCounterUpdateData = Dict[str, Any]
FeatureUsageCounterList = List[FeatureUsageCounter]

# ==============================================
# 📊 FEATURE USAGE COUNTER REPOSITORY
# ==============================================


class FeatureUsageCounterRepository(
    BaseRepository[
        FeatureUsageCounter,
        FeatureUsageCounterData,
        FeatureUsageCounterUpdateData,
    ]
):
    """
    مستودع عداد استخدام الميزة - يوفر عمليات خاصة بعدادات الاستخدام.

    مسؤول عن:
        - عمليات CRUD الأساسية لعدادات الاستخدام
        - جلب عداد لمطعم/ميزة في فترة معينة
        - إنشاء عداد جديد عند عدم وجوده
        - زيادة/تقليل/إعادة تعيين العداد
        - قراءة الاستخدام الحالي

    Attributes:
        model: نموذج FeatureUsageCounter
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
        تهيئة مستودع عداد استخدام الميزة.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(FeatureUsageCounter, session)

    # ==========================================
    # 🔍 BASE QUERY
    # ==========================================

    def _build_base_query(self):
        """
        بناء الاستعلام الأساسي لعدادات الاستخدام.

        Returns:
            Select: استعلام SQLAlchemy الأساسي
        """
        return select(self.model)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET COUNTER
    # ==============================================

    async def get_counter(
        self,
        *,
        restaurant_id: int,
        feature_id: int,
        period_year: Optional[int] = None,
        period_month: Optional[int] = None,
    ) -> Optional[FeatureUsageCounter]:
        """
        الحصول على عداد استخدام لمطعم وميزة في فترة محددة.

        Args:
            restaurant_id: معرف المطعم
            feature_id: معرف الميزة
            period_year: السنة (اختياري - None يعني فترة غير سنوية)
            period_month: الشهر (اختياري - None يعني فترة غير شهرية)

        Returns:
            كائن FeatureUsageCounter أو None
        """
        try:
            query = self._build_base_query().where(
                self.model.restaurant_id == restaurant_id,
                self.model.feature_id == feature_id,
            )

            # ✅ معالجة period_year
            if period_year is None:
                query = query.where(self.model.period_year.is_(None))
            else:
                query = query.where(self.model.period_year == period_year)

            # ✅ معالجة period_month
            if period_month is None:
                query = query.where(self.model.period_month.is_(None))
            else:
                query = query.where(self.model.period_month == period_month)

            query = query.limit(1)

            result = await self.session.execute(query)

            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(
                "feature_usage_counter_repo_get_counter_failed",
                extra={
                    "restaurant_id": restaurant_id,
                    "feature_id": feature_id,
                    "period_year": period_year,
                    "period_month": period_month,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET CURRENT USAGE
    # ==============================================

    async def get_current_usage(
        self,
        *,
        restaurant_id: int,
        feature_id: int,
        period_year: Optional[int] = None,
        period_month: Optional[int] = None,
    ) -> int:
        """
        قراءة الاستخدام الحالي لمطعم/ميزة في فترة محددة.

        Args:
            restaurant_id: معرف المطعم
            feature_id: معرف الميزة
            period_year: السنة (اختياري)
            period_month: الشهر (اختياري)

        Returns:
            عدد مرات الاستخدام (0 إذا لم يوجد عداد)
        """
        counter = await self.get_counter(
            restaurant_id=restaurant_id,
            feature_id=feature_id,
            period_year=period_year,
            period_month=period_month,
        )

        if not counter:
            return 0

        return int(counter.usage_count)

    # ==============================================
    # GET COUNTERS BY RESTAURANT
    # ==============================================

    async def get_by_restaurant(
        self,
        *,
        restaurant_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> FeatureUsageCounterList:
        """
        الحصول على عدادات الاستخدام لمطعم معين.

        Args:
            restaurant_id: معرف المطعم
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة عدادات الاستخدام
        """
        try:
            query = (
                self._build_base_query()
                .where(self.model.restaurant_id == restaurant_id)
                .order_by(self.model.id.asc())
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(query)

            return list(result.scalars().all())

        except Exception as e:
            logger.exception(
                "feature_usage_counter_repo_get_by_restaurant_failed",
                extra={
                    "restaurant_id": restaurant_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET COUNTERS BY FEATURE
    # ==============================================

    async def get_by_feature(
        self,
        *,
        feature_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> FeatureUsageCounterList:
        """
        الحصول على عدادات الاستخدام لميزة معينة.

        Args:
            feature_id: معرف الميزة
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة عدادات الاستخدام
        """
        try:
            query = (
                self._build_base_query()
                .where(self.model.feature_id == feature_id)
                .order_by(self.model.id.asc())
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(query)

            return list(result.scalars().all())

        except Exception as e:
            logger.exception(
                "feature_usage_counter_repo_get_by_feature_failed",
                extra={
                    "feature_id": feature_id,
                    "error": str(e),
                },
            )
            raise

    # ==========================================
    # ✏️ MUTATIONS
    # ==========================================

    # ==============================================
    # CREATE COUNTER
    # ==============================================

    async def create_counter(
        self,
        *,
        restaurant_id: int,
        feature_id: int,
        usage_count: int = 0,
        period_year: Optional[int] = None,
        period_month: Optional[int] = None,
    ) -> FeatureUsageCounter:
        """
        إنشاء عداد استخدام جديد.

        Args:
            restaurant_id: معرف المطعم
            feature_id: معرف الميزة
            usage_count: عدد مرات الاستخدام الابتدائي
            period_year: السنة (اختياري)
            period_month: الشهر (اختياري)

        Returns:
            كائن FeatureUsageCounter المنشأ
        """
        logger.info(
            "feature_usage_counter_repo_create",
            extra={
                "restaurant_id": restaurant_id,
                "feature_id": feature_id,
                "period_year": period_year,
                "period_month": period_month,
            },
        )

        data: FeatureUsageCounterData = {
            "restaurant_id": restaurant_id,
            "feature_id": feature_id,
            "usage_count": usage_count,
            "period_year": period_year,
            "period_month": period_month,
        }

        counter = await self.create(data=data)

        logger.info(
            "feature_usage_counter_created",
            extra={
                "counter_id": counter.id,
                "restaurant_id": restaurant_id,
                "feature_id": feature_id,
            },
        )

        return counter

    # ==============================================
    # INCREMENT COUNTER
    # ==============================================

    async def increment_counter(
        self,
        *,
        counter_id: int,
        amount: int = 1,
    ) -> Optional[FeatureUsageCounter]:
        """
        زيادة عداد الاستخدام بمقدار معين.

        Args:
            counter_id: معرف العداد
            amount: مقدار الزيادة (افتراضي: 1)

        Returns:
            كائن FeatureUsageCounter المحدث أو None
        """
        logger.info(
            "feature_usage_counter_repo_increment",
            extra={
                "counter_id": counter_id,
                "amount": amount,
            },
        )

        counter = await self.get_by_id(id=counter_id)

        if not counter:
            logger.warning(
                "feature_usage_counter_not_found",
                extra={"counter_id": counter_id},
            )
            return None

        new_count = (counter.usage_count or 0) + amount

        return await self.update(
            id=counter_id,
            data={"usage_count": new_count},
        )

    # ==============================================
    # DECREMENT COUNTER
    # ==============================================

    async def decrement_counter(
        self,
        *,
        counter_id: int,
        amount: int = 1,
    ) -> Optional[FeatureUsageCounter]:
        """
        تقليل عداد الاستخدام بمقدار معين (بدون النزول تحت الصفر).

        Args:
            counter_id: معرف العداد
            amount: مقدار النقصان (افتراضي: 1)

        Returns:
            كائن FeatureUsageCounter المحدث أو None
        """
        logger.info(
            "feature_usage_counter_repo_decrement",
            extra={
                "counter_id": counter_id,
                "amount": amount,
            },
        )

        counter = await self.get_by_id(id=counter_id)

        if not counter:
            logger.warning(
                "feature_usage_counter_not_found",
                extra={"counter_id": counter_id},
            )
            return None

        new_count = max(0, (counter.usage_count or 0) - amount)

        return await self.update(
            id=counter_id,
            data={"usage_count": new_count},
        )

    # ==============================================
    # RESET COUNTER
    # ==============================================

    async def reset_counter(
        self,
        *,
        counter_id: int,
    ) -> Optional[FeatureUsageCounter]:
        """
        إعادة تعيين عداد الاستخدام إلى الصفر.

        Args:
            counter_id: معرف العداد

        Returns:
            كائن FeatureUsageCounter المحدث أو None
        """
        logger.info(
            "feature_usage_counter_repo_reset",
            extra={"counter_id": counter_id},
        )

        counter = await self.get_by_id(id=counter_id)

        if not counter:
            logger.warning(
                "feature_usage_counter_not_found",
                extra={"counter_id": counter_id},
            )
            return None

        return await self.update(
            id=counter_id,
            data={"usage_count": 0},
        )

    # ==============================================
    # INCREMENT BY RESTAURANT AND FEATURE
    # (ينشئ العداد إذا لم يكن موجوداً)
    # ==============================================

    # ==============================================
    # INCREMENT FOR RESTAURANT FEATURE
    # ==============================================

    async def increment_for_restaurant_feature(
        self,
        *,
        restaurant_id: int,
        feature_id: int,
        period_year: Optional[int] = None,
        period_month: Optional[int] = None,
        amount: int = 1,
    ) -> FeatureUsageCounter:
        """
        زيادة عداد استخدام لمطعم/ميزة (ينشئ العداد إن لم يكن موجوداً).

        Args:
            restaurant_id: معرف المطعم
            feature_id: معرف الميزة
            period_year: السنة (اختياري)
            period_month: الشهر (اختياري)
            amount: مقدار الزيادة (افتراضي: 1)

        Returns:
            كائن FeatureUsageCounter المحدث أو المنشأ
        """
        counter = await self.get_counter(
            restaurant_id=restaurant_id,
            feature_id=feature_id,
            period_year=period_year,
            period_month=period_month,
        )

        if not counter:
            counter = await self.create_counter(
                restaurant_id=restaurant_id,
                feature_id=feature_id,
                usage_count=amount,
                period_year=period_year,
                period_month=period_month,
            )

            logger.info(
                "feature_usage_counter_created_and_incremented",
                extra={
                    "counter_id": counter.id,
                    "restaurant_id": restaurant_id,
                    "feature_id": feature_id,
                    "amount": amount,
                },
            )

            return counter

        return await self.increment_counter(
            counter_id=counter.id,
            amount=amount,
        )

    # ==========================================
    # 📊 STATISTICS
    # ==========================================

    # ==============================================
    # GET TOTAL USAGE FOR RESTAURANT
    # ==============================================

    async def get_total_usage_for_restaurant(
        self,
        *,
        restaurant_id: int,
    ) -> int:
        """
        حساب إجمالي الاستخدام لمطعم معين عبر جميع الميزات.

        Args:
            restaurant_id: معرف المطعم

        Returns:
            إجمالي الاستخدام
        """
        try:
            query = select(func.coalesce(func.sum(self.model.usage_count), 0)).where(
                self.model.restaurant_id == restaurant_id
            )

            result = await self.session.execute(query)

            return int(result.scalar_one() or 0)

        except Exception as e:
            logger.exception(
                "feature_usage_counter_repo_total_for_restaurant_failed",
                extra={
                    "restaurant_id": restaurant_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # COUNT BY RESTAURANT
    # ==============================================

    async def count_by_restaurant(
        self,
        *,
        restaurant_id: int,
    ) -> int:
        """
        حساب عدد عدادات الاستخدام لمطعم معين.

        Args:
            restaurant_id: معرف المطعم

        Returns:
            عدد العدادات
        """
        return await self.count(filters={"restaurant_id": restaurant_id})


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# دوال متوافقة مع الاستيرادات القديمة (Psycopg3)
# ==============================================

# ==============================================
# GET FEATURE COUNTER (COMPATIBILITY)
# ==============================================


async def get_feature_counter(
    *,
    restaurant_id: int,
    feature_id: int,
    period_year: Optional[int] = None,
    period_month: Optional[int] = None,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على عداد استخدام (دالة متوافقة مع الإصدار القديم).

    Args:
        restaurant_id: معرف المطعم
        feature_id: معرف الميزة
        period_year: السنة (اختياري)
        period_month: الشهر (اختياري)
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        قاموس بيانات العداد أو None
    """
    repo = FeatureUsageCounterRepository(session=session)

    counter = await repo.get_counter(
        restaurant_id=restaurant_id,
        feature_id=feature_id,
        period_year=period_year,
        period_month=period_month,
    )

    if not counter:
        return None

    return {
        "id": counter.id,
        "restaurant_id": counter.restaurant_id,
        "feature_id": counter.feature_id,
        "usage_count": counter.usage_count,
        "period_year": counter.period_year,
        "period_month": counter.period_month,
        "created_at": counter.created_at,
        "updated_at": counter.updated_at,
    }


# ==============================================
# CREATE FEATURE COUNTER (COMPATIBILITY)
# ==============================================


async def create_feature_counter(
    *,
    restaurant_id: int,
    feature_id: int,
    usage_count: int = 0,
    period_year: Optional[int] = None,
    period_month: Optional[int] = None,
    session: AsyncSession,
) -> int:
    """
    إنشاء عداد استخدام جديد (دالة متوافقة مع الإصدار القديم).

    Args:
        restaurant_id: معرف المطعم
        feature_id: معرف الميزة
        usage_count: عدد الاستخدام الابتدائي
        period_year: السنة (اختياري)
        period_month: الشهر (اختياري)
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        معرف العداد
    """
    repo = FeatureUsageCounterRepository(session=session)

    counter = await repo.create_counter(
        restaurant_id=restaurant_id,
        feature_id=feature_id,
        usage_count=usage_count,
        period_year=period_year,
        period_month=period_month,
    )

    return counter.id


# ==============================================
# INCREMENT FEATURE COUNTER (COMPATIBILITY)
# ==============================================


async def increment_feature_counter(
    *,
    counter_id: int,
    amount: int = 1,
    session: AsyncSession,
) -> None:
    """
    زيادة عداد الاستخدام (دالة متوافقة مع الإصدار القديم).

    Args:
        counter_id: معرف العداد
        amount: مقدار الزيادة
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = FeatureUsageCounterRepository(session=session)

    await repo.increment_counter(
        counter_id=counter_id,
        amount=amount,
    )


# ==============================================
# DECREMENT FEATURE COUNTER (COMPATIBILITY)
# ==============================================


async def decrement_feature_counter(
    *,
    counter_id: int,
    amount: int = 1,
    session: AsyncSession,
) -> None:
    """
    تقليل عداد الاستخدام (دالة متوافقة مع الإصدار القديم).

    Args:
        counter_id: معرف العداد
        amount: مقدار النقصان
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = FeatureUsageCounterRepository(session=session)

    await repo.decrement_counter(
        counter_id=counter_id,
        amount=amount,
    )


# ==============================================
# RESET FEATURE COUNTER (COMPATIBILITY)
# ==============================================


async def reset_feature_counter(
    *,
    counter_id: int,
    session: AsyncSession,
) -> None:
    """
    إعادة تعيين عداد الاستخدام (دالة متوافقة مع الإصدار القديم).

    Args:
        counter_id: معرف العداد
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = FeatureUsageCounterRepository(session=session)

    await repo.reset_counter(counter_id=counter_id)


# ==============================================
# GET CURRENT USAGE (COMPATIBILITY)
# ==============================================


async def get_current_usage(
    *,
    restaurant_id: int,
    feature_id: int,
    period_year: Optional[int] = None,
    period_month: Optional[int] = None,
    session: AsyncSession,
) -> int:
    """
    قراءة الاستخدام الحالي (دالة متوافقة مع الإصدار القديم).

    Args:
        restaurant_id: معرف المطعم
        feature_id: معرف الميزة
        period_year: السنة (اختياري)
        period_month: الشهر (اختياري)
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        عدد مرات الاستخدام
    """
    repo = FeatureUsageCounterRepository(session=session)

    return await repo.get_current_usage(
        restaurant_id=restaurant_id,
        feature_id=feature_id,
        period_year=period_year,
        period_month=period_month,
    )
