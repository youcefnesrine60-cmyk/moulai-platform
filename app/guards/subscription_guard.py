# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🛡️ SUBSCRIPTION GUARD
# طبقة التحقق من صلاحية الاشتراك
#
# Async SQLAlchemy Version
# ==============================================

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models.subscription import Subscription
from app.repositories.subscription_repo import SubscriptionRepository

# ==============================================
# 🧩 TYPES
# ==============================================

SubscriptionResult = Subscription

# ==============================================
# ✅ REQUIRE ACTIVE SUBSCRIPTION
# ==============================================

async def require_active_subscription(
    *,
    session: AsyncSession,
    restaurant_id: int,
) -> Subscription:
    """
    طلب اشتراك نشط (يرفع استثناء إذا لم يوجد).

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        restaurant_id: معرف المطعم

    Returns:
        كائن Subscription النشط

    Raises:
        ValueError: إذا لم يوجد اشتراك نشط
    """
    repo = SubscriptionRepository(session=session)

    subscription = await repo.get_active_by_restaurant(
        restaurant_id=restaurant_id,
    )

    if not subscription:
        logger.warning(
            "active_subscription_required",
            extra={"restaurant_id": restaurant_id},
        )
        raise ValueError("active_subscription_required")

    return subscription


# ==============================================
# 🔍 HAS ACTIVE SUBSCRIPTION
# ==============================================

async def has_active_subscription(
    *,
    session: AsyncSession,
    restaurant_id: int,
) -> bool:
    """
    التحقق من وجود اشتراك نشط.

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        restaurant_id: معرف المطعم

    Returns:
        True إذا كان هناك اشتراك نشط
    """
    repo = SubscriptionRepository(session=session)

    return await repo.has_active_subscription(
        restaurant_id=restaurant_id,
    )


# ==============================================
# 🔍 GET ACTIVE SUBSCRIPTION
# ==============================================

async def get_active_subscription(
    *,
    session: AsyncSession,
    restaurant_id: int,
) -> Optional[Subscription]:
    """
    الحصول على الاشتراك النشط (إن وُجد).

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        restaurant_id: معرف المطعم

    Returns:
        كائن Subscription النشط أو None
    """
    repo = SubscriptionRepository(session=session)

    return await repo.get_active_by_restaurant(
        restaurant_id=restaurant_id,
    )


# ==============================================
# 🔍 GET VALID SUBSCRIPTION (ALIAS)
# ==============================================

async def get_valid_subscription(
    *,
    session: AsyncSession,
    restaurant_id: int,
) -> Optional[Subscription]:
    """
    الحصول على اشتراك صالح (alias لـ get_active_subscription).

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        restaurant_id: معرف المطعم

    Returns:
        كائن Subscription الصالح أو None
    """
    return await get_active_subscription(
        session=session,
        restaurant_id=restaurant_id,
    )


# ==============================================
# 🔍 IS TRIAL SUBSCRIPTION
# ==============================================

async def is_trial_subscription(
    *,
    session: AsyncSession,
    restaurant_id: int,
) -> bool:
    """
    التحقق من أن الاشتراك الحالي تجريبي.

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        restaurant_id: معرف المطعم

    Returns:
        True إذا كان الاشتراك تجريبي
    """
    subscription = await get_active_subscription(
        session=session,
        restaurant_id=restaurant_id,
    )

    if not subscription:
        return False

    return subscription.status == "trial"


# ==============================================
# 🔍 IS PAID SUBSCRIPTION
# ==============================================

async def is_paid_subscription(
    *,
    session: AsyncSession,
    restaurant_id: int,
) -> bool:
    """
    التحقق من أن الاشتراك الحالي مدفوع (نشط).

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        restaurant_id: معرف المطعم

    Returns:
        True إذا كان الاشتراك مدفوع
    """
    subscription = await get_active_subscription(
        session=session,
        restaurant_id=restaurant_id,
    )

    if not subscription:
        return False

    return subscription.status == "active"


# ==============================================
# 🔍 GET SUBSCRIPTION PLAN CODE
# ==============================================

async def get_subscription_plan_code(
    *,
    session: AsyncSession,
    restaurant_id: int,
) -> Optional[str]:
    """
    الحصول على كود خطة الاشتراك النشط.

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        restaurant_id: معرف المطعم

    Returns:
        كود الخطة أو None
    """
    subscription = await get_active_subscription(
        session=session,
        restaurant_id=restaurant_id,
    )

    if not subscription:
        return None

    # ✅ استخدام العلاقة plan (selectin) لجلب الكود
    if subscription.plan:
        return subscription.plan.code

    return None


# ==============================================
# 🔍 GET SUBSCRIPTION PLAN ID
# ==============================================

async def get_subscription_plan_id(
    *,
    session: AsyncSession,
    restaurant_id: int,
) -> Optional[int]:
    """
    الحصول على معرف خطة الاشتراك النشط.

    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        restaurant_id: معرف المطعم

    Returns:
        معرف الخطة أو None
    """
    subscription = await get_active_subscription(
        session=session,
        restaurant_id=restaurant_id,
    )

    if not subscription:
        return None

    return subscription.plan_id


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "SubscriptionResult",
    "require_active_subscription",
    "has_active_subscription",
    "get_active_subscription",
    "get_valid_subscription",
    "is_trial_subscription",
    "is_paid_subscription",
    "get_subscription_plan_code",
    "get_subscription_plan_id",
]