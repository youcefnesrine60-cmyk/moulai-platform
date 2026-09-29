# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📊 FEATURE USAGE LIMITS ENGINE
# Business Layer - محرك حدود استخدام الميزات
#
# Async SQLAlchemy Version
# ==============================================

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.guards.subscription_guard import (
    require_active_subscription,
)
from app.repositories.feature_usage_limits_repo import (
    FeatureUsageLimitRepository,
)

# ==============================================
# 🔍 GET FEATURE LIMIT
# ==============================================

async def get_feature_limit(
    *,
    session: AsyncSession,
    restaurant_id: int,
    feature_id: int,
) -> Optional[int]:
    """
    الحصول على الحد الشهري لميزة في الاشتراك النشط.

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        restaurant_id: معرف المطعم
        feature_id: معرف الميزة

    Returns:
        الحد الشهري أو None (غير محدود)

    Raises:
        ValueError: إذا لم يوجد اشتراك نشط
    """
    # 1️⃣ التحقق من الاشتراك النشط
    subscription = await require_active_subscription(
        session=session,
        restaurant_id=restaurant_id,
    )

    # 2️⃣ جلب حد الاستخدام للخطة/الميزة
    limit_repo = FeatureUsageLimitRepository(session=session)

    limit_obj = await limit_repo.get_plan_feature_limit(
        plan_id=subscription.plan_id,
        feature_id=feature_id,
    )

    if not limit_obj:
        return None

    if limit_obj.monthly_limit is None:
        return None

    return int(limit_obj.monthly_limit)


# ==============================================
# 🔍 HAS AVAILABLE USAGE
# ==============================================

async def has_available_usage(
    *,
    session: AsyncSession,
    restaurant_id: int,
    feature_id: int,
    current_usage: int,
) -> bool:
    """
    التحقق من إمكانية استخدام إضافي (بناءً على الحد الشهري).

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        restaurant_id: معرف المطعم
        feature_id: معرف الميزة
        current_usage: الاستخدام الحالي

    Returns:
        True إذا كان الاستخدام الإضافي مسموحاً
    """
    limit_value = await get_feature_limit(
        session=session,
        restaurant_id=restaurant_id,
        feature_id=feature_id,
    )

    # ✅ غير محدود
    if limit_value is None:
        return True

    return current_usage < limit_value


# ==============================================
# 🚫 REQUIRE AVAILABLE USAGE
# ==============================================

async def require_available_usage(
    *,
    session: AsyncSession,
    restaurant_id: int,
    feature_id: int,
    current_usage: int,
) -> None:
    """
    طلب توفّر استخدام إضافي (يرفع استثناء إذا تجاوز الحد).

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        restaurant_id: معرف المطعم
        feature_id: معرف الميزة
        current_usage: الاستخدام الحالي

    Raises:
        ValueError: إذا تجاوز الاستخدام الحد الشهري
    """
    allowed = await has_available_usage(
        session=session,
        restaurant_id=restaurant_id,
        feature_id=feature_id,
        current_usage=current_usage,
    )

    if allowed:
        return

    logger.warning(
        "feature_usage_limit_exceeded",
        extra={
            "restaurant_id": restaurant_id,
            "feature_id": feature_id,
            "current_usage": current_usage,
        },
    )

    raise ValueError("feature_usage_limit_exceeded")


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "get_feature_limit",
    "has_available_usage",
    "require_available_usage",
]