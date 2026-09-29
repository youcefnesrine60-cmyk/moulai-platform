# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🔐 FEATURE GUARD
# Subscription + Limits Protection Layer
# طبقة حماية الميزات والاشتراكات
#
# Async SQLAlchemy Version
# ==============================================

from datetime import (
    datetime,
    timezone,
)

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models.subscription import Subscription
from app.repositories.feature_usage_counter_repo import (
    FeatureUsageCounterRepository,
)
from app.repositories.feature_usage_limits_repo import (
    FeatureUsageLimitRepository,
)
from app.repositories.subscription_features_repo import (
    SubscriptionFeatureRepository,
)
from app.repositories.subscription_repo import (
    SubscriptionRepository,
)

# ==============================================
# 🧩 TYPES
# ==============================================

SubscriptionResult = Subscription

# ==============================================
# 🔍 CURRENT PERIOD
# ==============================================

def _current_period() -> tuple[int, int]:
    """
    الحصول على السنة والشهر الحاليين بتوقيت UTC.

    Returns:
        tuple[int, int]: (السنة، الشهر)
    """
    now = datetime.now(timezone.utc)

    return (now.year, now.month)


# ==============================================
# 🔍 CHECK FEATURE ACCESS
# ==============================================

async def check_feature_access(
    *,
    session: AsyncSession,
    restaurant_id: int,
    feature_id: int,
) -> bool:
    """
    التحقق من إمكانية الوصول للميزة (دون رفع استثناء).

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        restaurant_id: معرف المطعم
        feature_id: معرف الميزة

    Returns:
        True إذا كان الوصول مسموحاً، False خلاف ذلك
    """
    try:
        await require_feature(
            session=session,
            restaurant_id=restaurant_id,
            feature_id=feature_id,
        )
        return True
    except ValueError:
        return False


# ==============================================
# 🚫 REQUIRE FEATURE
# ==============================================

async def require_feature(
    *,
    session: AsyncSession,
    restaurant_id: int,
    feature_id: int,
) -> SubscriptionResult:
    """
    طلب الوصول لميزة (يرفع استثناء إذا لم يكن مسموحاً).

    الخطوات:
        1. التحقق من وجود اشتراك نشط
        2. التحقق من أن الميزة مدرجة في الخطة
        3. التحقق من حدود الاستخدام الشهرية

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        restaurant_id: معرف المطعم
        feature_id: معرف الميزة

    Returns:
        كائن Subscription النشط

    Raises:
        ValueError: في الحالات التالية:
            - no_active_subscription
            - feature_not_available
            - feature_limit_reached
    """
    # ==========================================
    # 1️⃣ GET ACTIVE SUBSCRIPTION
    # ==========================================

    subscription_repo = SubscriptionRepository(session=session)

    subscription = await subscription_repo.get_active_by_restaurant(
        restaurant_id=restaurant_id,
    )

    if not subscription:
        logger.warning(
            "no_active_subscription",
            extra={
                "restaurant_id": restaurant_id,
                "feature_id": feature_id,
            },
        )
        raise ValueError("no_active_subscription")

    # ==========================================
    # 2️⃣ CHECK PLAN FEATURE ACCESS
    # ==========================================

    feature_repo = SubscriptionFeatureRepository(session=session)

    has_feature = await feature_repo.subscription_has_feature(
        subscription_id=subscription.id,
        feature_id=feature_id,
    )

    if not has_feature:
        logger.warning(
            "feature_not_available",
            extra={
                "restaurant_id": restaurant_id,
                "subscription_id": subscription.id,
                "feature_id": feature_id,
            },
        )
        raise ValueError("feature_not_available")

    # ==========================================
    # 3️⃣ CHECK USAGE LIMITS
    # ==========================================

    limit_repo = FeatureUsageLimitRepository(session=session)

    limit_obj = await limit_repo.get_plan_feature_limit(
        plan_id=subscription.plan_id,
        feature_id=feature_id,
    )

    # ✅ إذا لم يوجد حد، أو الحد None → لا حدود
    if not limit_obj or limit_obj.monthly_limit is None:
        return subscription

    # ✅ جلب الاستخدام الحالي في الشهر الحالي
    year, month = _current_period()

    counter_repo = FeatureUsageCounterRepository(session=session)

    current_usage = await counter_repo.get_current_usage(
        restaurant_id=restaurant_id,
        feature_id=feature_id,
        period_year=year,
        period_month=month,
    )

    # ✅ التحقق من عدم تجاوز الحد
    if (current_usage + 1) > limit_obj.monthly_limit:
        logger.warning(
            "feature_limit_reached",
            extra={
                "restaurant_id": restaurant_id,
                "subscription_id": subscription.id,
                "feature_id": feature_id,
                "current_usage": current_usage,
                "monthly_limit": limit_obj.monthly_limit,
            },
        )
        raise ValueError("feature_limit_reached")

    # ==========================================
    # ✅ SUCCESS
    # ==========================================

    return subscription


# ==============================================
# 🔍 HAS FEATURE (SHORTCUT)
# ==============================================

async def has_feature(
    *,
    session: AsyncSession,
    restaurant_id: int,
    feature_id: int,
) -> bool:
    """
    اختصار: التحقق من إمكانية الوصول للميزة (بدون رفع استثناء).

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        restaurant_id: معرف المطعم
        feature_id: معرف الميزة

    Returns:
        True إذا كان الوصول مسموحاً
    """
    try:
        await require_feature(
            session=session,
            restaurant_id=restaurant_id,
            feature_id=feature_id,
        )
        return True
    except ValueError:
        return False


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "SubscriptionResult",
    "check_feature_access",
    "require_feature",
    "has_feature",
]