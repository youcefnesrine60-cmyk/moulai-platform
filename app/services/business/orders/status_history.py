# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / SERVICES / BUSINESS / ORDERS / STATUS HISTORY
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for status history.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from sqlalchemy.ext.asyncio import AsyncSession

# ✅ استيراد الاستثناءات
from app.core.exceptions import ValidationError
from app.core.logger import logger
from app.models.order_item import OrderStatusHistory
from app.repositories.order_status_history_repo import (
    OrderStatusHistoryRepository,
)
from app.services.business.orders.constants import (
    get_status_display_name,
    is_valid_status,
    ALL_STATUSES,
)

# ==============================================
# 🧩 TYPES
# ==============================================

StatusHistoryDict = Dict[str, Any]
StatusHistoryList = List[OrderStatusHistory]
StatusDistribution = Dict[str, int]


# ==============================================
# 📜 STATUS HISTORY
# ==============================================


async def get_status_history(
    *,
    order_id: int,
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
) -> StatusHistoryList:
    """
    جلب سجل حالات الطلب.

    Args:
        order_id: معرف الطلب
        session: جلسة قاعدة البيانات غير المتزامنة
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات

    Returns:
        StatusHistoryList: قائمة سجل الحالات
    """
    logger.info(
        "get_status_history_started",
        extra={
            "order_id": order_id,
            "skip": skip,
            "limit": limit,
        },
    )

    history_repo = OrderStatusHistoryRepository(session=session)
    history = await history_repo.get_by_order_id(
        order_id=order_id,
        skip=skip,
        limit=limit,
    )

    logger.info(
        "get_status_history_retrieved",
        extra={
            "order_id": order_id,
            "count": len(history),
        },
    )

    return history


# ==============================================
# 📈 STATUS TIMELINE
# ==============================================


async def get_order_timeline(
    *,
    order_id: int,
    session: AsyncSession,
) -> List[Dict[str, Any]]:
    """
    جلب الخط الزمني لحالات الطلب مع أسماء الحالات المعروضة.

    Args:
        order_id: معرف الطلب
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        List[Dict[str, Any]]: قائمة الخط الزمني
    """
    logger.info(
        "get_order_timeline_started",
        extra={"order_id": order_id},
    )

    history_repo = OrderStatusHistoryRepository(session=session)
    timeline = await history_repo.get_status_timeline(order_id=order_id)

    # إضافة الأسماء المعروضة
    enriched_timeline = []

    for item in timeline:
        enriched_item = dict(item)
        enriched_item["status_display"] = get_status_display_name(
            item.get("new_status", item.get("status", "unknown")),
        )
        enriched_timeline.append(enriched_item)

    logger.info(
        "get_order_timeline_retrieved",
        extra={
            "order_id": order_id,
            "count": len(enriched_timeline),
        },
    )

    return enriched_timeline


# ==============================================
# 🔍 LAST STATUS CHANGE
# ==============================================


async def get_last_status(
    *,
    order_id: int,
    session: AsyncSession,
) -> Optional[OrderStatusHistory]:
    """
    جلب آخر تغيير في حالة الطلب.

    Args:
        order_id: معرف الطلب
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        Optional[OrderStatusHistory]: بيانات آخر تغيير أو None
    """
    logger.info(
        "get_last_status_started",
        extra={"order_id": order_id},
    )

    history_repo = OrderStatusHistoryRepository(session=session)
    last_status = await history_repo.get_last_status_change(order_id=order_id)

    if last_status:
        logger.info(
            "get_last_status_found",
            extra={
                "order_id": order_id,
                "status": last_status.new_status,
                "created_at": last_status.created_at,
            },
        )
    else:
        logger.info(
            "get_last_status_not_found",
            extra={"order_id": order_id},
        )

    return last_status


# ==============================================
# 🔍 GET STATUS HISTORY COUNT
# ==============================================


async def get_status_history_count(
    *,
    order_id: int,
    session: AsyncSession,
) -> int:
    """
    حساب عدد تغييرات حالة الطلب.

    Args:
        order_id: معرف الطلب
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        int: عدد التغييرات
    """
    logger.info(
        "get_status_history_count_started",
        extra={"order_id": order_id},
    )

    history_repo = OrderStatusHistoryRepository(session=session)
    count = await history_repo.count_status_changes(order_id=order_id)

    logger.info(
        "get_status_history_count_result",
        extra={
            "order_id": order_id,
            "count": count,
        },
    )

    return count


# ==============================================
# 🔍 GET ORDERS REACHED STATUS
# ==============================================


async def get_orders_reached_status(
    *,
    status: str,
    session: AsyncSession,
) -> List[int]:
    """
    الحصول على معرفات الطلبات التي وصلت إلى حالة معينة.

    Args:
        status: حالة الطلب
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        List[int]: قائمة معرفات الطلبات

    Raises:
        ValidationError: إذا كانت الحالة غير صالحة
    """
    if not is_valid_status(status):
        raise ValidationError(
            message=f"الحالة '{status}' غير صالحة",
            details={
                "status": status,
                "valid_statuses": list(ALL_STATUSES),
            },
        )

    logger.info(
        "get_orders_reached_status_started",
        extra={"status": status},
    )

    history_repo = OrderStatusHistoryRepository(session=session)
    order_ids = await history_repo.get_orders_reached_status(status=status)

    logger.info(
        "get_orders_reached_status_result",
        extra={
            "status": status,
            "count": len(order_ids),
        },
    )

    return order_ids


# ==============================================
# 📊 GET STATUS DISTRIBUTION
# ==============================================


async def get_status_distribution(
    *,
    restaurant_id: int,
    session: AsyncSession,
) -> StatusDistribution:
    """
    الحصول على توزيع حالات الطلبات لمطعم معين.

    Args:
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        StatusDistribution: توزيع الحالات
    """
    logger.info(
        "get_status_distribution_started",
        extra={"restaurant_id": restaurant_id},
    )

    # جلب جميع الطلبات
    from app.repositories.orders_repo import OrdersRepository

    orders_repo = OrdersRepository(session=session)
    orders = await orders_repo.get_by_restaurant_id(
        restaurant_id=restaurant_id,
        limit=10000,
    )

    # حساب توزيع الحالات
    distribution: StatusDistribution = {}

    for order in orders:
        status = order.status
        distribution[status] = distribution.get(status, 0) + 1

    # إضافة الحالات التي ليس لها طلبات
    for status in ALL_STATUSES:
        if status not in distribution:
            distribution[status] = 0

    # ترتيب النتائج حسب الترتيب المحدد
    from app.services.business.orders.constants import STATUS_ORDER

    sorted_distribution = {
        status: distribution.get(status, 0)
        for status in sorted(
            distribution.keys(), key=lambda x: STATUS_ORDER.get(x, 999)
        )
    }

    logger.info(
        "get_status_distribution_result",
        extra={
            "restaurant_id": restaurant_id,
            "distribution": sorted_distribution,
        },
    )

    return sorted_distribution


# ==============================================
# ⏱️ GET AVERAGE STATUS DURATION
# ==============================================


async def get_average_status_duration(
    *,
    restaurant_id: int,
    status: str,
    session: AsyncSession,
) -> Optional[float]:
    """
    حساب متوسط مدة البقاء في حالة معينة (بالدقائق).

    Args:
        restaurant_id: معرف المطعم
        status: حالة الطلب
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        Optional[float]: متوسط المدة بالدقائق أو None إذا لم توجد بيانات

    Raises:
        ValidationError: إذا كانت الحالة غير صالحة
    """
    if not is_valid_status(status):
        raise ValidationError(
            message=f"الحالة '{status}' غير صالحة",
            details={
                "status": status,
                "valid_statuses": list(ALL_STATUSES),
            },
        )

    logger.info(
        "get_average_status_duration_started",
        extra={
            "restaurant_id": restaurant_id,
            "status": status,
        },
    )

    history_repo = OrderStatusHistoryRepository(session=session)
    avg_duration = await history_repo.get_average_status_duration(
        restaurant_id=restaurant_id,
        status=status,
    )

    logger.info(
        "get_average_status_duration_result",
        extra={
            "restaurant_id": restaurant_id,
            "status": status,
            "avg_duration_minutes": avg_duration,
        },
    )

    return avg_duration


# ==============================================
# 🔍 GET CURRENT STATUS HISTORY
# ==============================================


async def get_current_status_history(
    *,
    order_id: int,
    session: AsyncSession,
) -> Optional[OrderStatusHistory]:
    """
    الحصول على سجل الحالة الحالية للطلب (آخر تغيير).

    Args:
        order_id: معرف الطلب
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        Optional[OrderStatusHistory]: سجل الحالة الحالية أو None
    """
    return await get_last_status(
        order_id=order_id,
        session=session,
    )


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# ==============================================


# دوال التوافق مع الإصدار القديم
# ==============================================
# GET STATUS HISTORY COMPAT
# ==============================================


async def get_status_history_compat(
    *,
    order_id: int,
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
) -> StatusHistoryList:
    """
    دالة متوافقة مع الإصدار القديم (مغلفة).

    Args:
        order_id: معرف الطلب
        session: جلسة قاعدة البيانات غير المتزامنة
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات

    Returns:
        StatusHistoryList: قائمة سجل الحالات
    """
    return await get_status_history(
        order_id=order_id,
        session=session,
        skip=skip,
        limit=limit,
    )


# ==============================================
# GET LAST STATUS COMPAT
# ==============================================


async def get_last_status_compat(
    *,
    order_id: int,
    session: AsyncSession,
) -> Optional[OrderStatusHistory]:
    """
    دالة متوافقة مع الإصدار القديم (مغلفة).

    Args:
        order_id: معرف الطلب
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        Optional[OrderStatusHistory]: آخر تغيير أو None
    """
    return await get_last_status(
        order_id=order_id,
        session=session,
    )
