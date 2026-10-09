# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / SERVICES / BUSINESS / ORDERS / CUSTOMER
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for customer.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.services.business.orders.pricing import item_total
from app.services.business.orders.update import transition_locked_order
from app.services.business.orders.transaction import transactional_order

# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🛒 CUSTOMER ORDER OPERATIONS
# عمليات الطلبات الخاصة بالعميل
# يتضمن: جلب الطلب، إلغاء الطلب، تعديل الكمية
# ==============================================

from typing import Any, Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.core.logger import logger
from app.core.exceptions import NotFoundError, ValidationError
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.user import User
from app.services.business.orders.pricing import validate_quantity
from app.services.business.orders.totals import compute_order_totals

# ==============================================
# 📋 TYPE ALIASES
# ==============================================

OrderReference = Any
"""مرجع الطلب: يمكن أن يكون رقم الطلب أو المعرف الرقمي."""

ProductName = Optional[str]
"""اسم المنتج: اختياري لتحديد عنصر الطلب."""

Quantity = int
"""الكمية: عدد صحيح موجب ضمن الحدود المسموح بها."""

# ==============================================
# 🔍 BASE SELECT
# استعلام أساسي لجلب الطلبات مع ربط المستخدم
# ==============================================


# ==============================================
#  BASE ORDER SELECT
# ==============================================


def _base_order_select() -> Select:
    """
    بناء استعلام أساسي لجلب الطلبات مع ربط المستخدم.

    Returns:
        Select: استعلام SQLAlchemy الأساسي مع join على جدول المستخدم.
    """
    return select(Order).join(User, Order.user_id == User.id)


# ==============================================
# 📦 GET CUSTOMER ORDER
# جلب طلب العميل بواسطة مرجع الطلب
# ==============================================


# ==============================================
# GET CUSTOMER ORDER
# ==============================================


async def get_customer_order(
    *,
    chat_id: int,
    order_reference: OrderReference,
    session: AsyncSession,
    lock: bool = False,
    restaurant_id: Optional[int] = None,
) -> Optional[Order]:
    """
    جلب طلب العميل بناءً على معرف المحادثة ومرجع الطلب.

    Args:
        chat_id: معرف المحادثة في تيليجرام.
        order_reference: مرجع الطلب (رقم الطلب أو المعرف الرقمي).
        session: جلسة قاعدة البيانات غير المتزامنة.
        lock: هل يتم قفل السجل لمنع التعديل المتزامن.

    Returns:
        Optional[Order]: كائن الطلب إذا وُجد، وإلا None.
    """
    if order_reference is None or not str(order_reference).strip():
        return None

    reference = str(order_reference).strip()
    conditions = [Order.order_number == reference]
    if reference.isdigit():
        conditions.append(Order.id == int(reference))

    statement = (
        _base_order_select().where(User.chat_id == chat_id, or_(*conditions)).limit(1)
    )
    if lock:
        statement = statement.with_for_update(of=Order).execution_options(
            populate_existing=True
        )
    if restaurant_id is not None:
        statement = statement.where(Order.restaurant_id == restaurant_id)

    result = await session.execute(statement)
    return result.scalar_one_or_none()


# ==============================================
# ❌ CANCEL CUSTOMER ORDER
# إلغاء طلب العميل مع تسجيل سبب الإلغاء
# ==============================================


# ==============================================
# CANCEL CUSTOMER ORDER
# ==============================================


@transactional_order
async def cancel_customer_order(
    *,
    chat_id: int,
    order_reference: OrderReference,
    reason: Optional[str],
    session: AsyncSession,
    restaurant_id: Optional[int] = None,
) -> tuple[Order, str]:
    """
    إلغاء طلب العميل مع التحقق من الحالة وتسجيل السبب.

    Args:
        chat_id: معرف المحادثة في تيليجرام.
        order_reference: مرجع الطلب (رقم الطلب أو المعرف الرقمي).
        reason: سبب الإلغاء (اختياري).
        session: جلسة قاعدة البيانات غير المتزامنة.

    Returns:
        tuple[Order, str]: كائن الطلب بعد الإلغاء والحالة السابقة.

    Raises:
        NotFoundError: إذا لم يتم العثور على الطلب.
        ValidationError: إذا كانت حالة الطلب لا تسمح بالإلغاء.
    """
    order = await get_customer_order(
        chat_id=chat_id,
        order_reference=order_reference,
        session=session,
        lock=True,
        restaurant_id=restaurant_id,
    )
    if not order:
        raise NotFoundError(
            message="لم أجد هذا الطلب ضمن طلبات حسابك.",
            error_code="ORDER_NOT_FOUND",
        )
    if order.status not in {"pending", "confirmed"}:
        raise ValidationError(
            message="لا يمكن إلغاء الطلب في حالته الحالية.",
            details={"status": order.status},
            error_code="ORDER_NOT_CANCELLABLE",
        )

    previous_status = order.status
    await transition_locked_order(
        order=order,
        new_status="cancelled",
        session=session,
        note=reason or "Cancelled by customer via agent",
    )

    logger.info(
        "Customer order cancelled",
        extra={
            "chat_id": chat_id,
            "order_id": order.id,
            "previous_status": previous_status,
            "reason": reason,
        },
    )

    return order, previous_status


# ==============================================
# ✏️ CHANGE CUSTOMER ORDER ITEM QUANTITY
# تعديل كمية عنصر في طلب العميل
# ==============================================


# ==============================================
# CHANGE CUSTOMER ORDER ITEM QUANTITY
# ==============================================


@transactional_order
async def change_customer_order_item_quantity(
    *,
    chat_id: int,
    order_reference: OrderReference,
    product_name: ProductName,
    quantity: Quantity,
    session: AsyncSession,
    restaurant_id: Optional[int] = None,
) -> tuple[Order, OrderItem]:
    """
    تعديل كمية عنصر محدد في طلب العميل.

    Args:
        chat_id: معرف المحادثة في تيليجرام.
        order_reference: مرجع الطلب (رقم الطلب أو المعرف الرقمي).
        product_name: اسم المنتج (اختياري إذا كان الطلب يحتوي عنصراً واحداً).
        quantity: الكمية الجديدة.
        session: جلسة قاعدة البيانات غير المتزامنة.

    Returns:
        tuple[Order, OrderItem]: كائن الطلب بعد التعديل وكائن العنصر المعدل.

    Raises:
        ValidationError: إذا كانت الكمية غير صالحة أو الطلب غير قابل للتعديل.
        NotFoundError: إذا لم يتم العثور على الطلب أو العنصر.
    """
    validate_quantity(quantity)

    order = await get_customer_order(
        chat_id=chat_id,
        order_reference=order_reference,
        session=session,
        lock=True,
        restaurant_id=restaurant_id,
    )
    if not order:
        raise NotFoundError(
            message="لم أجد هذا الطلب ضمن طلبات حسابك.",
            error_code="ORDER_NOT_FOUND",
        )
    if order.status != "pending":
        raise ValidationError(
            message="لا يمكن تعديل الطلب إلا عندما تكون حالته قيد الانتظار.",
            details={"status": order.status},
            error_code="ORDER_NOT_MODIFIABLE",
        )

    result = await session.execute(
        select(OrderItem).where(OrderItem.order_id == order.id),
    )
    items = list(result.scalars().all())
    if isinstance(product_name, str) and product_name.strip():
        normalized_name = product_name.strip().casefold()
        matching_items = [
            item
            for item in items
            if item.product_name.strip().casefold() == normalized_name
        ]
    elif len(items) == 1:
        matching_items = items
    else:
        matching_items = []

    if not matching_items:
        error_code = (
            "ORDER_ITEM_AMBIGUOUS"
            if len(items) > 1 and not product_name
            else "ORDER_ITEM_NOT_FOUND"
        )
        raise ValidationError(
            message="حدّد اسم المنتج الموجود في الطلب الذي تريد تعديل كميته.",
            error_code=error_code,
        )
    if len(matching_items) > 1:
        raise ValidationError(
            message="يوجد أكثر من عنصر مطابق في الطلب؛ يرجى تحديده بدقة.",
            error_code="ORDER_ITEM_AMBIGUOUS",
        )

    item = matching_items[0]
    item.quantity = quantity
    item.total_price = item_total(item.unit_price, quantity)
    subtotal = round(sum(float(order_item.total_price) for order_item in items), 2)
    discount = float(order.discount_amount or 0)
    tax = float(order.tax_amount or 0)
    delivery = float(order.delivery_amount or 0)
    totals = compute_order_totals(
        subtotal=subtotal,
        discount=discount,
        tax=tax,
        delivery=delivery,
    )
    order.subtotal_amount, order.total_amount = totals[0], totals[4]
    await session.flush()

    logger.info(
        "Customer order item quantity changed",
        extra={
            "chat_id": chat_id,
            "order_id": order.id,
            "order_item_id": item.id,
            "product_name": item.product_name,
            "new_quantity": quantity,
            "new_total_amount": order.total_amount,
        },
    )

    return order, item
