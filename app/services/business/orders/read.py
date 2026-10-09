# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / SERVICES / BUSINESS / ORDERS / READ
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for read.

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
from app.core.exceptions import (
    NotFoundError,
)

from app.core.logger import logger
from app.models.order import Order
from app.repositories.orders_repo import OrdersRepository
from app.services.business.orders.constants import is_valid_status

# ==============================================
# 🧩 TYPES
# ==============================================

OrderDict = Dict[str, Any]
OrderList = List[Order]


# ==============================================
# 🔍 GET ORDER
# ==============================================


async def get_restaurant_order(
    *,
    order_id: int,
    session: AsyncSession,
) -> Optional[Order]:
    """
    جلب بيانات طلب معين.

    Args:
        order_id: معرف الطلب
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        Optional[Order]: كائن الطلب أو None
    """
    logger.info(
        "get_restaurant_order_started",
        extra={"order_id": order_id},
    )

    orders_repo = OrdersRepository(session=session)
    order = await orders_repo.get_by_id(id=order_id)

    if order:
        logger.info(
            "get_restaurant_order_found",
            extra={
                "order_id": order_id,
                "order_number": getattr(order, "order_number", "N/A"),
                "status": order.status,
            },
        )
    else:
        logger.info(
            "get_restaurant_order_not_found",
            extra={"order_id": order_id},
        )

    return order


# ==============================================
# 🔍 GET ORDER (WITH ERROR)
# ==============================================


async def get_restaurant_order_or_raise(
    *,
    order_id: int,
    session: AsyncSession,
) -> Order:
    """
    جلب بيانات طلب معين ورفع خطأ إذا لم يتم العثور عليه.

    Args:
        order_id: معرف الطلب
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        Order: كائن الطلب

    Raises:
        NotFoundError: إذا لم يتم العثور على الطلب
    """
    order = await get_restaurant_order(
        order_id=order_id,
        session=session,
    )

    if not order:
        raise NotFoundError(
            message=f"الطلب بـ ID '{order_id}' غير موجود",
        )

    return order


# ==============================================
# 🔍 GET ORDER BY NUMBER
# ==============================================


async def get_order_by_number(
    *,
    restaurant_id: int,
    order_number: str,
    session: AsyncSession,
) -> Optional[Order]:
    """
    جلب طلب حسب رقمه.

    Args:
        restaurant_id: معرف المطعم
        order_number: رقم الطلب
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        Optional[Order]: كائن الطلب أو None
    """
    logger.info(
        "get_order_by_number_started",
        extra={
            "restaurant_id": restaurant_id,
            "order_number": order_number,
        },
    )

    orders_repo = OrdersRepository(session=session)
    order = await orders_repo.get_by_order_number(
        restaurant_id=restaurant_id,
        order_number=order_number,
    )

    if order:
        logger.info(
            "get_order_by_number_found",
            extra={
                "restaurant_id": restaurant_id,
                "order_number": order_number,
                "order_id": order.id,
            },
        )
    else:
        logger.info(
            "get_order_by_number_not_found",
            extra={
                "restaurant_id": restaurant_id,
                "order_number": order_number,
            },
        )

    return order


# ==============================================
# 🔍 GET ORDER BY NUMBER (WITH ERROR)
# ==============================================


async def get_order_by_number_or_raise(
    *,
    restaurant_id: int,
    order_number: str,
    session: AsyncSession,
) -> Order:
    """
    جلب طلب حسب رقمه ورفع خطأ إذا لم يتم العثور عليه.

    Args:
        restaurant_id: معرف المطعم
        order_number: رقم الطلب
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        Order: كائن الطلب

    Raises:
        NotFoundError: إذا لم يتم العثور على الطلب
    """
    order = await get_order_by_number(
        restaurant_id=restaurant_id,
        order_number=order_number,
        session=session,
    )

    if not order:
        raise NotFoundError(
            message=f"الطلب بـ رقم '{order_number}' غير موجود للمطعم {restaurant_id}",
        )

    return order


# ==============================================
# 🔍 GET RESTAURANT ORDERS
# ==============================================


async def get_orders(
    *,
    restaurant_id: int,
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
) -> OrderList:
    """
    جلب جميع طلبات مطعم معين.

    Args:
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        status: حالة الطلب (اختياري)

    Returns:
        OrderList: قائمة الطلبات
    """
    logger.info(
        "get_orders_started",
        extra={
            "restaurant_id": restaurant_id,
            "skip": skip,
            "limit": limit,
            "status": status,
        },
    )

    # التحقق من صحة الحالة إذا تم تمريرها
    if status and not is_valid_status(status):
        logger.warning(
            "get_orders_invalid_status",
            extra={
                "restaurant_id": restaurant_id,
                "status": status,
            },
        )

    orders_repo = OrdersRepository(session=session)
    orders = await orders_repo.get_by_restaurant_id(
        restaurant_id=restaurant_id,
        skip=skip,
        limit=limit,
        status=status,
    )

    logger.info(
        "get_orders_retrieved",
        extra={
            "restaurant_id": restaurant_id,
            "count": len(orders),
            "status": status,
        },
    )

    return orders


# ==============================================
# 🔍 GET ORDERS BY STATUS
# ==============================================


async def get_orders_by_status(
    *,
    restaurant_id: int,
    status: str,
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
) -> OrderList:
    """
    جلب طلبات مطعم حسب الحالة.

    Args:
        restaurant_id: معرف المطعم
        status: حالة الطلب
        session: جلسة قاعدة البيانات غير المتزامنة
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات

    Returns:
        OrderList: قائمة الطلبات

    Raises:
        ValueError: إذا كانت الحالة غير صالحة
    """
    logger.info(
        "get_orders_by_status_started",
        extra={
            "restaurant_id": restaurant_id,
            "status": status,
            "skip": skip,
            "limit": limit,
        },
    )

    # التحقق من صحة الحالة
    if not is_valid_status(status):
        logger.error(
            "get_orders_by_status_invalid_status",
            extra={
                "restaurant_id": restaurant_id,
                "status": status,
            },
        )
        raise ValueError(f"الحالة '{status}' غير صالحة")

    orders_repo = OrdersRepository(session=session)
    orders = await orders_repo.get_by_status(
        status=status,
        restaurant_id=restaurant_id,
        skip=skip,
        limit=limit,
    )

    logger.info(
        "get_orders_by_status_retrieved",
        extra={
            "restaurant_id": restaurant_id,
            "status": status,
            "count": len(orders),
        },
    )

    return orders


# ==============================================
# 🔍 GET ORDER WITH DETAILS
# ==============================================


async def get_order_with_details(
    *,
    order_id: int,
    session: AsyncSession,
) -> Optional[Order]:
    """
    جلب طلب مع جميع علاقاته (عناصر، خيارات، مدفوعات، تاريخ الحالة).

    Args:
        order_id: معرف الطلب
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        Optional[Order]: كائن الطلب مع العلاقات أو None
    """
    logger.info(
        "get_order_with_details_started",
        extra={"order_id": order_id},
    )

    orders_repo = OrdersRepository(session=session)
    order = await orders_repo.get_with_relations(order_id=order_id)

    if order:
        logger.info(
            "get_order_with_details_found",
            extra={
                "order_id": order_id,
                "order_number": getattr(order, "order_number", "N/A"),
                "items_count": (
                    len(order.items) if hasattr(order, "items") and order.items else 0
                ),
                "payments_count": (
                    len(order.payments)
                    if hasattr(order, "payments") and order.payments
                    else 0
                ),
            },
        )
    else:
        logger.info(
            "get_order_with_details_not_found",
            extra={"order_id": order_id},
        )

    return order


# ==============================================
# 🔍 GET ORDER WITH DETAILS (WITH ERROR)
# ==============================================


async def get_order_with_details_or_raise(
    *,
    order_id: int,
    session: AsyncSession,
) -> Order:
    """
    جلب طلب مع جميع علاقاته ورفع خطأ إذا لم يتم العثور عليه.

    Args:
        order_id: معرف الطلب
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        Order: كائن الطلب مع العلاقات

    Raises:
        NotFoundError: إذا لم يتم العثور على الطلب
    """
    order = await get_order_with_details(
        order_id=order_id,
        session=session,
    )

    if not order:
        raise NotFoundError(
            message=f"الطلب بـ ID '{order_id}' غير موجود",
        )

    return order


# ==============================================
# 🔢 COUNT ORDERS BY RESTAURANT
# ==============================================


async def count_orders_by_restaurant(
    *,
    restaurant_id: int,
    session: AsyncSession,
    status: Optional[str] = None,
) -> int:
    """
    حساب عدد طلبات مطعم معين.

    Args:
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة
        status: حالة الطلب (اختياري)

    Returns:
        int: عدد الطلبات
    """
    logger.info(
        "count_orders_by_restaurant_started",
        extra={
            "restaurant_id": restaurant_id,
            "status": status,
        },
    )

    orders_repo = OrdersRepository(session=session)

    if status:
        if not is_valid_status(status):
            logger.warning(
                "count_orders_by_restaurant_invalid_status",
                extra={
                    "restaurant_id": restaurant_id,
                    "status": status,
                },
            )
            return 0

        count = await orders_repo.count_by_status(
            restaurant_id=restaurant_id,
            status=status,
        )
    else:
        count = await orders_repo.count_by_restaurant(
            restaurant_id=restaurant_id,
        )

    logger.info(
        "count_orders_by_restaurant_result",
        extra={
            "restaurant_id": restaurant_id,
            "status": status,
            "count": count,
        },
    )

    return count


# ==============================================
# 📊 GET ORDER STATUS COUNTS
# ==============================================


async def get_order_status_counts(
    *,
    restaurant_id: int,
    session: AsyncSession,
) -> Dict[str, int]:
    """
    الحصول على عدد الطلبات حسب كل حالة لمطعم معين.

    Args:
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        Dict[str, int]: قاموس يحتوي على عدد الطلبات لكل حالة
    """
    logger.info(
        "get_order_status_counts_started",
        extra={"restaurant_id": restaurant_id},
    )

    from app.services.business.orders.constants import ALL_STATUSES

    orders_repo = OrdersRepository(session=session)
    status_counts = {}

    for status in ALL_STATUSES:
        count = await orders_repo.count_by_status(
            restaurant_id=restaurant_id,
            status=status,
        )
        if count > 0:
            status_counts[status] = count

    logger.info(
        "get_order_status_counts_result",
        extra={
            "restaurant_id": restaurant_id,
            "status_counts": status_counts,
        },
    )

    return status_counts


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# ==============================================


# دوال التوافق مع الإصدار القديم
# ==============================================
# GET RESTAURANT ORDER COMPAT
# ==============================================


async def get_restaurant_order_compat(
    *,
    order_id: int,
    session: AsyncSession,
) -> Optional[Order]:
    """
    دالة متوافقة مع الإصدار القديم (مغلفة).

    Args:
        order_id: معرف الطلب
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        Optional[Order]: كائن الطلب أو None
    """
    return await get_restaurant_order(
        order_id=order_id,
        session=session,
    )


# ==============================================
# GET ORDERS COMPAT
# ==============================================


async def get_orders_compat(
    *,
    restaurant_id: int,
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
) -> OrderList:
    """
    دالة متوافقة مع الإصدار القديم (مغلفة).

    Args:
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات

    Returns:
        OrderList: قائمة الطلبات
    """
    return await get_orders(
        restaurant_id=restaurant_id,
        session=session,
        skip=skip,
        limit=limit,
    )
