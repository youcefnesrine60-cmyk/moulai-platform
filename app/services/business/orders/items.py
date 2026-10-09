# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / SERVICES / BUSINESS / ORDERS / ITEMS
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for items.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.repositories.orders_repo import lock_order
from app.services.business.orders.pricing import (
    catalog_item,
    item_total,
    MAX_ITEMS_PER_ORDER,
)
from app.services.business.orders.transaction import transactional_order

# ==============================================
# 📦 ORDERS SERVICE - ITEMS
# إدارة عناصر الطلب
# (add_item_to_order, remove_item_from_order)
# ==============================================

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
    ValidationError,
)

from app.core.logger import logger
from app.models.order_item import OrderItem
from app.repositories.order_item_options_repo import (
    OrderItemOptionsRepository,
)
from app.repositories.order_items_repo import OrderItemsRepository
from app.services.business.orders.helpers import check_order_editable

# ==============================================
# 🧩 CONSTANTS
# ==============================================


# ==============================================
# 🧩 TYPES
# ==============================================

OrderOptionPayload = Dict[str, Any]
OrderItemList = List[OrderItem]


# ==============================================
# ➕ ADD ITEM TO ORDER
# ==============================================


@transactional_order
async def add_item_to_order(
    *,
    order_id: int,
    product_id: int,
    product_name: str,
    unit_price: float,
    quantity: int,
    total_price: float,
    options: Optional[List[OrderOptionPayload]] = None,
    session: AsyncSession,
) -> OrderItem:
    """
    إضافة عنصر إلى طلب موجود.

    Args:
        order_id: معرف الطلب
        product_id: معرف المنتج
        product_name: اسم المنتج
        unit_price: سعر الوحدة
        quantity: الكمية
        total_price: السعر الإجمالي
        options: قائمة الخيارات (اختياري)
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        OrderItem: كائن OrderItem المنشأ

    Raises:
        NotFoundError: إذا لم يتم العثور على الطلب
        ValidationError: إذا كانت الكمية غير صالحة أو تم تجاوز الحد الأقصى
    """
    logger.info(
        "add_item_to_order_started",
        extra={
            "order_id": order_id,
            "product_id": product_id,
            "quantity": quantity,
        },
    )

    # 1️⃣ جلب الطلب للتحقق
    order = await lock_order(order_id=order_id, session=session)

    if not order:
        logger.error(
            "add_item_to_order_order_not_found",
            extra={"order_id": order_id},
        )
        raise NotFoundError(
            message=f"الطلب بـ ID '{order_id}' غير موجود",
        )

    # 2️⃣ التحقق من إمكانية التعديل
    check_order_editable(order)

    normalized = await catalog_item(
        restaurant_id=order.restaurant_id,
        payload=dict(product_id=product_id, quantity=quantity, options=options),
        session=session,
    )
    product_name, unit_price, total_price = (
        normalized["product_name"],
        normalized["unit_price"],
        normalized["total_price"],
    )

    # 4️⃣ التحقق من عدد العناصر في الطلب
    items_repo = OrderItemsRepository(session=session)
    current_items_count = await items_repo.count_by_order(order_id=order_id)

    if current_items_count >= MAX_ITEMS_PER_ORDER:
        raise ValidationError(
            message=f"تجاوزت الحد الأقصى لعناصر الطلب ({MAX_ITEMS_PER_ORDER})",
            details={
                "order_id": order_id,
                "current_items": current_items_count,
                "max_items": MAX_ITEMS_PER_ORDER,
            },
        )

    # 5️⃣ التحقق من عدم وجود منتج مكرر في الطلب
    existing_item = await items_repo.get_by_product_and_order(
        order_id=order_id,
        product_id=product_id,
    )

    if existing_item:
        raise ValidationError(
            message=f"المنتج '{product_name}' موجود بالفعل في الطلب",
            details={
                "order_id": order_id,
                "product_id": product_id,
                "existing_item_id": existing_item.id,
                "existing_quantity": existing_item.quantity,
            },
        )

    # 6️⃣ إنشاء عنصر الطلب
    item_data: Dict[str, Any] = {
        "order_id": order_id,
        "product_id": product_id,
        "product_name": product_name,
        "unit_price": unit_price,
        "quantity": quantity,
        "total_price": total_price,
    }

    order_item = await items_repo.create(data=item_data)

    # 7️⃣ إنشاء الخيارات إن وجدت
    if options:
        options_repo = OrderItemOptionsRepository(session=session)

        for option in options:
            if not option.get("option_group_name") or not option.get("option_name"):
                logger.warning(
                    "invalid_option_skipped",
                    extra={
                        "order_item_id": order_item.id,
                        "option": option,
                    },
                )
                continue

            option_data: Dict[str, Any] = {
                "order_item_id": order_item.id,
                "option_group_name": option["option_group_name"],
                "option_name": option["option_name"],
                "additional_price": option.get("additional_price", 0),
            }

            await options_repo.create(data=option_data)

    # 8️⃣ تحديث إجمالي الطلب
    await _recalculate_order_total(order_id=order_id, session=session)

    logger.info(
        "order_item_added_successfully",
        extra={
            "order_id": order_id,
            "order_item_id": order_item.id,
            "product_id": product_id,
            "quantity": quantity,
        },
    )

    return order_item


# ==============================================
# ❌ REMOVE ITEM FROM ORDER
# ==============================================


@transactional_order
async def remove_item_from_order(
    *,
    order_id: int,
    order_item_id: int,
    session: AsyncSession,
) -> None:
    """
    حذف عنصر من طلب.

    Args:
        order_id: معرف الطلب
        order_item_id: معرف عنصر الطلب
        session: جلسة قاعدة البيانات غير المتزامنة

    Raises:
        NotFoundError: إذا لم يتم العثور على الطلب أو العنصر
        ValidationError: إذا كان الطلب مقفلاً
    """
    logger.info(
        "remove_item_from_order_started",
        extra={
            "order_id": order_id,
            "order_item_id": order_item_id,
        },
    )

    # 1️⃣ جلب الطلب للتحقق
    order = await lock_order(order_id=order_id, session=session)

    if not order:
        logger.error(
            "remove_item_from_order_order_not_found",
            extra={"order_id": order_id},
        )
        raise NotFoundError(
            message=f"الطلب بـ ID '{order_id}' غير موجود",
        )

    # 2️⃣ التحقق من إمكانية التعديل
    check_order_editable(order)

    # 3️⃣ التحقق من وجود العنصر
    items_repo = OrderItemsRepository(session=session)
    item = await items_repo.get_by_id(id=order_item_id)

    if not item:
        raise NotFoundError(
            message=f"عنصر الطلب بـ ID '{order_item_id}' غير موجود",
        )

    if item.order_id != order_id:
        raise ValidationError(
            message=f"عنصر الطلب '{order_item_id}' لا ينتمي إلى الطلب '{order_id}'",
        )

    # 4️⃣ حذف خيارات العنصر أولاً
    options_repo = OrderItemOptionsRepository(session=session)
    await options_repo.delete_by_order_item(order_item_id=order_item_id)

    # 5️⃣ حذف عنصر الطلب
    await items_repo.delete(id=order_item_id)

    # 6️⃣ تحديث إجمالي الطلب
    await _recalculate_order_total(order_id=order_id, session=session)

    logger.info(
        "order_item_removed_successfully",
        extra={
            "order_id": order_id,
            "order_item_id": order_item_id,
        },
    )


# ==============================================
# 🔍 GET ORDER ITEMS
# ==============================================


async def get_order_items_list(
    *,
    order_id: int,
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
) -> OrderItemList:
    """
    جلب جميع عناصر طلب معين.

    Args:
        order_id: معرف الطلب
        session: جلسة قاعدة البيانات غير المتزامنة
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات

    Returns:
        OrderItemList: قائمة عناصر الطلب
    """
    logger.info(
        "get_order_items_list_started",
        extra={
            "order_id": order_id,
            "skip": skip,
            "limit": limit,
        },
    )

    items_repo = OrderItemsRepository(session=session)
    items = await items_repo.get_by_order_id(
        order_id=order_id,
        skip=skip,
        limit=limit,
    )

    logger.info(
        "order_items_list_retrieved",
        extra={
            "order_id": order_id,
            "count": len(items),
        },
    )

    return items


# ==============================================
# 🔍 GET ORDER ITEM BY ID
# ==============================================


async def get_order_item_by_id(
    *,
    order_item_id: int,
    session: AsyncSession,
) -> Optional[OrderItem]:
    """
    جلب عنصر طلب بالمعرف.

    Args:
        order_item_id: معرف عنصر الطلب
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        Optional[OrderItem]: كائن OrderItem أو None
    """
    logger.info(
        "get_order_item_by_id_started",
        extra={"order_item_id": order_item_id},
    )

    items_repo = OrderItemsRepository(session=session)
    item = await items_repo.get_by_id(id=order_item_id)

    return item


# ==============================================
# 🔢 COUNT ORDER ITEMS
# ==============================================


async def count_order_items(
    *,
    order_id: int,
    session: AsyncSession,
) -> int:
    """
    حساب عدد عناصر طلب معين.

    Args:
        order_id: معرف الطلب
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        int: عدد العناصر
    """
    logger.info(
        "count_order_items_started",
        extra={"order_id": order_id},
    )

    items_repo = OrderItemsRepository(session=session)
    count = await items_repo.count_by_order(order_id=order_id)

    return count


# ==============================================
# 💰 GET ORDER ITEMS SUBTOTAL
# ==============================================


async def get_order_items_subtotal(
    *,
    order_id: int,
    session: AsyncSession,
) -> float:
    """
    حساب المجموع الفرعي لعناصر طلب معين.

    Args:
        order_id: معرف الطلب
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        float: المجموع الفرعي
    """
    logger.info(
        "get_order_items_subtotal_started",
        extra={"order_id": order_id},
    )

    items_repo = OrderItemsRepository(session=session)
    subtotal = await items_repo.get_subtotal(order_id=order_id)

    return subtotal


# ==============================================
# 🛠️ PRIVATE HELPERS
# ==============================================

# ==============================================
# RECALCULATE ORDER TOTAL
# ==============================================


async def _recalculate_order_total(
    *,
    order_id: int,
    session: AsyncSession,
) -> None:
    """
    إعادة حساب إجمالي الطلب بناءً على عناصره.

    Args:
        order_id: معرف الطلب
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    from app.services.business.orders.totals import calculate_order_totals

    await session.flush()
    await calculate_order_totals(order_id=order_id, session=session)


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# ==============================================


# دوال التوافق مع الإصدار القديم
# ==============================================
# ADD ITEM TO ORDER COMPAT
# ==============================================


async def add_item_to_order_compat(
    *,
    order_id: int,
    product_id: int,
    product_name: str,
    unit_price: float,
    quantity: int,
    total_price: float,
    options: Optional[List[OrderOptionPayload]] = None,
    session: AsyncSession,
) -> int:
    """
    دالة متوافقة مع الإصدار القديم (تعيد معرف العنصر).

    Args:
        order_id: معرف الطلب
        product_id: معرف المنتج
        product_name: اسم المنتج
        unit_price: سعر الوحدة
        quantity: الكمية
        total_price: السعر الإجمالي
        options: قائمة الخيارات (اختياري)
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        int: معرف عنصر الطلب
    """
    item = await add_item_to_order(
        order_id=order_id,
        product_id=product_id,
        product_name=product_name,
        unit_price=unit_price,
        quantity=quantity,
        total_price=total_price,
        options=options,
        session=session,
    )
    return item.id


# ==============================================
# CHANGE ITEM AMOUNTS
# ==============================================


@transactional_order
async def change_item_amounts(
    *, order_item_id, session, quantity=None, unit_price=None
):

    items_repo = OrderItemsRepository(session=session)
    item = await items_repo.get_by_id(id=order_item_id)
    if item is None:
        raise NotFoundError(message="Order item not found")
    order = await lock_order(order_id=item.order_id, session=session)
    if order is None:
        raise NotFoundError(message="Order not found")
    check_order_editable(order)
    new_quantity = item.quantity if quantity is None else quantity
    new_price = item.unit_price if unit_price is None else unit_price
    total = item_total(new_price, new_quantity)
    updated = await items_repo.update(
        id=item.id,
        data=dict(quantity=new_quantity, unit_price=new_price, total_price=total),
    )
    await _recalculate_order_total(order_id=order.id, session=session)
    return updated
