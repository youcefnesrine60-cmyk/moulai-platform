# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / SERVICES / BUSINESS
# / FEATURE USAGE COUNTER ENGINE
# ==============================================

"""MoulAI operational module for feature usage counter engine.

Part of MoulAI Platform - Agent-as-a-Service.
"""

# ==============================================
# 📊 FEATURE USAGE COUNTER ENGINE
# Business Logic Layer
#
# ✓ إنشاء العداد تلقائياً إذا لم يوجد
# ✓ قراءة الاستخدام الحالي
# ✓ زيادة الاستخدام
# ✓ إنقاص الاستخدام
# ✓ التحقق من limit قبل الزيادة
# ✓ التكامل مع feature_guard.py
#
# Async SQLAlchemy Version
# ==============================================

from datetime import (
    datetime,
    timezone,
)
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.repositories.feature_usage_counter_repo import (
    FeatureUsageCounterRepository,
)
from app.repositories.feature_usage_limits_repo import (
    FeatureUsageLimitRepository,
)

# ==============================================
# 🔍 CURRENT PERIOD
# ==============================================


def _current_period() -> tuple[int, int]:
    """
    إرجاع السنة والشهر الحاليين بتوقيت UTC.

    Returns:
        tuple[int, int]: (السنة، الشهر)
    """
    now = datetime.now(timezone.utc)

    return (
        now.year,
        now.month,
    )


# ==============================================
# 🔍 GET CURRENT USAGE
# ==============================================


async def get_usage(
    *,
    session: AsyncSession,
    restaurant_id: int,
    feature_id: int,
) -> int:
    """
    قراءة الاستخدام الحالي لميزة في الفترة الحالية.

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        restaurant_id: معرف المطعم
        feature_id: معرف الميزة

    Returns:
        عدد مرات الاستخدام الحالي
    """
    year, month = _current_period()

    repo = FeatureUsageCounterRepository(session=session)

    return await repo.get_current_usage(
        restaurant_id=restaurant_id,
        feature_id=feature_id,
        period_year=year,
        period_month=month,
    )


# ==============================================
# 🔍 CAN USE FEATURE
# ==============================================


async def can_use_feature(
    *,
    session: AsyncSession,
    restaurant_id: int,
    plan_id: int,
    feature_id: int,
    amount: int = 1,
) -> bool:
    """
    التحقق من إمكانية استخدام الميزة (بناءً على الحد الشهري).

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        restaurant_id: معرف المطعم
        plan_id: معرف الخطة
        feature_id: معرف الميزة
        amount: الكمية المطلوبة (افتراضي: 1)

    Returns:
        True إذا كان الاستخدام مسموحاً، False إذا تجاوز الحد
    """
    limit_repo = FeatureUsageLimitRepository(session=session)

    limit_obj = await limit_repo.get_plan_feature_limit(
        plan_id=plan_id,
        feature_id=feature_id,
    )

    # ✅ لا يوجد حد => مسموح
    if not limit_obj:
        return True

    monthly_limit = limit_obj.monthly_limit

    # ✅ لا حد شهري => مسموح
    if monthly_limit is None:
        return True

    current_usage = await get_usage(
        session=session,
        restaurant_id=restaurant_id,
        feature_id=feature_id,
    )

    return (current_usage + amount) <= monthly_limit


# ==============================================
# ➕ INCREASE USAGE
# ==============================================


async def increase_usage(
    *,
    session: AsyncSession,
    restaurant_id: int,
    feature_id: int,
    amount: int = 1,
) -> int:
    """
    زيادة عداد استخدام الميزة (ينشئ العداد إن لم يكن موجوداً).

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        restaurant_id: معرف المطعم
        feature_id: معرف الميزة
        amount: مقدار الزيادة (افتراضي: 1)

    Returns:
        الاستخدام الحالي بعد الزيادة
    """
    year, month = _current_period()

    repo = FeatureUsageCounterRepository(session=session)

    # ✅ زيادة مع إنشاء تلقائي
    counter = await repo.increment_for_restaurant_feature(
        restaurant_id=restaurant_id,
        feature_id=feature_id,
        period_year=year,
        period_month=month,
        amount=amount,
    )

    usage = counter.usage_count if counter else 0

    logger.info(
        "feature_usage_increased",
        extra={
            "restaurant_id": restaurant_id,
            "feature_id": feature_id,
            "usage": usage,
        },
    )

    return usage


# ==============================================
# ➖ DECREASE USAGE
# ==============================================


async def decrease_usage(
    *,
    session: AsyncSession,
    restaurant_id: int,
    feature_id: int,
    amount: int = 1,
) -> int:
    """
    إنقاص عداد استخدام الميزة (بدون النزول تحت الصفر).

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        restaurant_id: معرف المطعم
        feature_id: معرف الميزة
        amount: مقدار النقصان (افتراضي: 1)

    Returns:
        الاستخدام الحالي بعد الإنقاص
    """
    year, month = _current_period()

    repo = FeatureUsageCounterRepository(session=session)

    counter = await repo.get_counter(
        restaurant_id=restaurant_id,
        feature_id=feature_id,
        period_year=year,
        period_month=month,
    )

    if not counter:
        return 0

    updated = await repo.decrement_counter(
        counter_id=counter.id,
        amount=amount,
    )

    usage = updated.usage_count if updated else 0

    logger.info(
        "feature_usage_decreased",
        extra={
            "restaurant_id": restaurant_id,
            "feature_id": feature_id,
            "usage": usage,
        },
    )

    return usage


# ==============================================
# 🔍 GET REMAINING USAGE
# ==============================================


async def get_remaining_usage(
    *,
    session: AsyncSession,
    restaurant_id: int,
    plan_id: int,
    feature_id: int,
) -> Optional[int]:
    """
    حساب الاستخدام المتبقي للميزة في الشهر الحالي.

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        restaurant_id: معرف المطعم
        plan_id: معرف الخطة
        feature_id: معرف الميزة

    Returns:
        الاستخدام المتبقي أو None إذا لم يوجد حد
    """
    limit_repo = FeatureUsageLimitRepository(session=session)

    limit_obj = await limit_repo.get_plan_feature_limit(
        plan_id=plan_id,
        feature_id=feature_id,
    )

    if not limit_obj:
        return None

    monthly_limit = limit_obj.monthly_limit

    if monthly_limit is None:
        return None

    usage = await get_usage(
        session=session,
        restaurant_id=restaurant_id,
        feature_id=feature_id,
    )

    return max(
        monthly_limit - usage,
        0,
    )


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# دوال متوافقة مع الاستيرادات القديمة
#
# ⚠️ مؤقتة فقط — يجب حذفها بعد تحديث كل Callers
# ==============================================

# ==============================================
# GET USAGE (COMPATIBILITY)
# بدون session → يستخدم get_usage
# ⚠️ غير مدعوم في SQLAlchemy — يجب تمرير session
# ==============================================

# ❌ لا يمكن توفير نسخة بدون session في SQLAlchemy
# أي Caller قديم يجب تحديثه لتمرير session


# ==============================================
# INCREASE USAGE (COMPATIBILITY)
# بدون session → يستخدم increase_usage
# ⚠️ غير مدعوم في SQLAlchemy — يجب تمرير session
# ==============================================

# ❌ لا يمكن توفير نسخة بدون session في SQLAlchemy
# أي Caller قديم يجب تحديثه لتمرير session
