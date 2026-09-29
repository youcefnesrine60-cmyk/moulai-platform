# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🔢 RESTAURANT ORDER COUNTER COMPATIBILITY
# دوال متوافقة مع الاستيرادات القديمة
# ==============================================

from typing import (
    Any,
    Dict,
    Optional,
)

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.services.business.restaurant.order_counter.service import (
    RestaurantOrderCounterService,
    RestaurantOrderCounterUpdate,
)

# ==============================================
# 📦 COMPATIBILITY FUNCTIONS
# ==============================================

# ==============================================
# INITIALIZE ORDER COUNTER
# ==============================================

async def initialize_order_counter(
    *,
    restaurant_id: int,
    session: AsyncSession,
) -> None:
    """
    تهيئة عداد طلبات جديد لمطعم (دالة متوافقة مع الإصدار القديم).

    Args:
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    service = RestaurantOrderCounterService(session=session)

    await service.initialize_counter(restaurant_id=restaurant_id)

    logger.info(
        "order_counter_initialized",
        extra={"restaurant_id": restaurant_id},
    )


# ==============================================
# GET ORDER COUNTER
# ==============================================

async def get_order_counter(
    *,
    restaurant_id: int,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على عداد طلبات مطعم معين (دالة متوافقة مع الإصدار القديم).

    Args:
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        Optional[Dict[str, Any]]: قاموس بيانات العداد أو None
    """
    service = RestaurantOrderCounterService(session=session)

    try:
        counter = await service.get_counter(restaurant_id=restaurant_id)
        return counter.model_dump()
    except Exception:
        return None


# ==============================================
# UPDATE ORDER COUNTER
# ==============================================

async def update_order_counter(
    *,
    restaurant_id: int,
    data: Dict[str, Any],
    session: AsyncSession,
) -> None:
    """
    تحديث عداد طلبات مطعم (دالة متوافقة مع الإصدار القديم).

    Args:
        restaurant_id: معرف المطعم
        data: بيانات التحديث
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    service = RestaurantOrderCounterService(session=session)

    update_data = RestaurantOrderCounterUpdate(**data)

    await service.update_counter(
        restaurant_id=restaurant_id,
        update_data=update_data,
    )


# ==============================================
# GENERATE NEXT ORDER NUMBER
# ==============================================

async def generate_next_order_number(
    *,
    restaurant_id: int,
    session: AsyncSession,
) -> str:
    """
    توليد رقم الطلب التالي لمطعم (دالة متوافقة مع الإصدار القديم).

    Args:
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        str: رقم الطلب المنسق
    """
    service = RestaurantOrderCounterService(session=session)

    result = await service.generate_next_order_number(
        restaurant_id=restaurant_id,
    )

    # ✅ استخدام الحقل الصحيح: order_number (بدلاً من formatted_number)
    return result.order_number


# ==============================================
# GET ORDER COUNTER SUMMARY
# ==============================================

async def get_order_counter_summary(
    *,
    restaurant_id: int,
    session: AsyncSession,
) -> Dict[str, Any]:
    """
    الحصول على ملخص عداد طلبات مطعم (دالة متوافقة مع الإصدار القديم).

    Args:
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        Dict[str, Any]: ملخص العداد
    """
    service = RestaurantOrderCounterService(session=session)

    summary = await service.get_counter_summary(restaurant_id=restaurant_id)

    return summary.model_dump()


# ==============================================
# RESET ORDER COUNTER
# ==============================================

async def reset_order_counter(
    *,
    restaurant_id: int,
    session: AsyncSession,
) -> None:
    """
    إعادة تعيين عداد طلبات مطعم إلى الصفر (دالة متوافقة مع الإصدار القديم).

    Args:
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    service = RestaurantOrderCounterService(session=session)

    await service.reset_counter(restaurant_id=restaurant_id)

    logger.info(
        "order_counter_reset",
        extra={"restaurant_id": restaurant_id},
    )


# ==============================================
# INCREMENT ORDER COUNTER
# ==============================================

async def increment_order_counter(
    *,
    restaurant_id: int,
    session: AsyncSession,
) -> None:
    """
    زيادة عداد طلبات مطعم بمقدار 1 (دالة متوافقة مع الإصدار القديم).

    Args:
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    service = RestaurantOrderCounterService(session=session)

    await service.increment_counter(restaurant_id=restaurant_id)

    logger.info(
        "order_counter_incremented",
        extra={"restaurant_id": restaurant_id},
    )


# ==============================================
# BUILD ORDER NUMBER
# ==============================================

def build_order_number(
    restaurant_id: int,
    sequence: int,
) -> str:
    """
    بناء رقم طلب منسق (دالة متوافقة مع الإصدار القديم).

    Args:
        restaurant_id: معرف المطعم
        sequence: رقم التسلسل

    Returns:
        str: رقم الطلب المنسق
    """
    return RestaurantOrderCounterService.build_order_number(
        restaurant_id=restaurant_id,
        sequence=sequence,
    )


# ==============================================
# GET CURRENT ORDER NUMBER
# ==============================================

async def get_current_order_number(
    *,
    restaurant_id: int,
    session: AsyncSession,
) -> int:
    """
    الحصول على رقم الطلب الحالي لمطعم معين (دالة متوافقة مع الإصدار القديم).

    Args:
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        int: آخر رقم طلب
    """
    service = RestaurantOrderCounterService(session=session)

    return await service.get_current_number(restaurant_id=restaurant_id)


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "initialize_order_counter",
    "get_order_counter",
    "update_order_counter",
    "generate_next_order_number",
    "get_order_counter_summary",
    "reset_order_counter",
    "increment_order_counter",
    "build_order_number",
    "get_current_order_number",
]