from app.services.business.orders.transaction import transactional_order
# ==============================================
# 📦 ORDERS SERVICE - TOTALS
# حساب الإجماليات 
# (calculate_order_totals, update_order_totals)
# ==============================================

from typing import Tuple

from sqlalchemy.ext.asyncio import AsyncSession

# ✅ استيراد الاستثناءات
from app.core.exceptions import (
    NotFoundError,
    ValidationError,
)

from app.core.logger import logger
from app.models.order import Order
from app.repositories.order_items_repo import OrderItemsRepository
from app.repositories.orders_repo import OrdersRepository
from app.repositories.order_item_options_repo import OrderItemOptionsRepository
from app.services.business.orders.helpers import check_order_editable

# ==============================================
# 🧩 TYPES
# ==============================================

OrderTotals = Tuple[float, float, float, float, float]
OrderTotalsWithOptions = Tuple[float, float, float, float, float, float]


# ==============================================
# 🧮 CALCULATE ORDER TOTALS
# ==============================================


def compute_order_totals(*, subtotal, discount=0, tax=0, delivery=0) -> OrderTotals:
    """Single arithmetic rule shared by customer and restaurant operations."""
    import math
    try:
        subtotal, discount, tax, delivery = map(float, (subtotal, discount, tax, delivery))
    except (TypeError, ValueError) as exc:
        raise ValidationError(message="Invalid order amounts") from exc
    if any(not math.isfinite(value) or value < 0 for value in (subtotal, discount, tax, delivery)):
        raise ValidationError(message="Invalid order amounts")
    total = subtotal - discount + tax + delivery
    if total < 0:
        raise ValidationError(message="Discount exceeds the payable amount")
    return tuple(round(value, 2) for value in (subtotal, discount, tax, delivery, total))


@transactional_order
async def calculate_order_totals(
    *,
    order_id: int,
    session: AsyncSession,
    include_options: bool = False,
) -> OrderTotals:
    """
    حساب إجماليات الطلب من عناصره.
    
    Args:
        order_id: معرف الطلب
        session: جلسة قاعدة البيانات غير المتزامنة
        include_options: تضمين أسعار الخيارات في الحساب
        
    Returns:
        OrderTotals: (subtotal, discount, tax, delivery, total)
        
    Raises:
        NotFoundError: إذا لم يتم العثور على الطلب
    """
    logger.info(
        "calculate_order_totals_started",
        extra={
            "order_id": order_id,
            "include_options": include_options,
        },
    )

    # 1️⃣ جلب الطلب
    orders_repo = OrdersRepository(session=session)
    order = await orders_repo.get_by_id(id=order_id)

    if not order:
        logger.error(
            "calculate_order_totals_order_not_found",
            extra={"order_id": order_id},
        )
        raise NotFoundError(
            message=f"الطلب بـ ID '{order_id}' غير موجود",
        )

    # 2️⃣ جلب عناصر الطلب
    items_repo = OrderItemsRepository(session=session)
    items = await items_repo.get_by_order_id(order_id=order_id)

    # 3️⃣ حساب المجموع الفرعي من العناصر
    subtotal = sum(float(item.total_price) for item in items)

    # 4️⃣ حساب أسعار الخيارات إذا كان مطلوباً
    options_total = 0.0

    if include_options:
        options_repo = OrderItemOptionsRepository(session=session)
        for item in items:
            options = await options_repo.get_by_order_item_id(order_item_id=item.id)
            options_total += sum(float(opt.additional_price) for opt in options)

        subtotal += options_total

    # 5️⃣ جلب الخصم والضريبة والتوصيل من الطلب
    discount = float(order.discount_amount or 0)
    tax = float(order.tax_amount or 0)
    delivery = float(order.delivery_amount or 0)

    # 6️⃣ حساب المجموع الكلي
    subtotal, discount, tax, delivery, total = compute_order_totals(
        subtotal=subtotal, discount=discount, tax=tax, delivery=delivery,
    )

    # 7️⃣ تحديث إجماليات الطلب
    await orders_repo.update(
        id=order_id,
        data={
            "subtotal_amount": round(subtotal, 2),
            "discount_amount": round(discount, 2),
            "tax_amount": round(tax, 2),
            "delivery_amount": round(delivery, 2),
            "total_amount": round(total, 2),
        },
    )

    logger.info(
        "order_totals_calculated_successfully",
        extra={
            "order_id": order_id,
            "subtotal": round(subtotal, 2),
            "discount": round(discount, 2),
            "tax": round(tax, 2),
            "delivery": round(delivery, 2),
            "total": round(total, 2),
            "items_count": len(items),
            "options_total": round(options_total, 2) if include_options else None,
        },
    )

    return (round(subtotal, 2), round(discount, 2), round(tax, 2), round(delivery, 2), round(total, 2))


# ==============================================
# 💰 UPDATE ORDER TOTALS
# ==============================================

@transactional_order
async def update_order_totals(
    *,
    order_id: int,
    subtotal_amount: float,
    discount_amount: float,
    tax_amount: float,
    delivery_amount: float,
    total_amount: float,
    session: AsyncSession,
) -> Order:
    """
    تحديث إجماليات الطلب.
    
    Args:
        order_id: معرف الطلب
        subtotal_amount: المجموع الفرعي
        discount_amount: مبلغ الخصم
        tax_amount: مبلغ الضريبة
        delivery_amount: مبلغ التوصيل
        total_amount: المجموع الكلي
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        Order: الطلب المُحدّث
        
    Raises:
        NotFoundError: إذا لم يتم العثور على الطلب
        ValidationError: إذا كانت القيم غير صالحة أو الطلب مقفلاً
    """
    logger.info(
        "update_order_totals_started",
        extra={
            "order_id": order_id,
            "subtotal_amount": subtotal_amount,
            "total_amount": total_amount,
        },
    )

    # 1️⃣ التحقق من صحة القيم
    import math
    if not math.isfinite(float(total_amount)) or total_amount < 0:
        raise ValidationError(message="Invalid total amount")
    subtotal_amount, discount_amount, tax_amount, delivery_amount, total_amount = compute_order_totals(
        subtotal=subtotal_amount, discount=discount_amount,
        tax=tax_amount, delivery=delivery_amount)

    # 2️⃣ جلب الطلب
    orders_repo = OrdersRepository(session=session)
    order = await orders_repo.get_by_id(id=order_id)

    if not order:
        logger.error(
            "update_order_totals_order_not_found",
            extra={"order_id": order_id},
        )
        raise NotFoundError(
            message=f"الطلب بـ ID '{order_id}' غير موجود",
        )

    # 3️⃣ التحقق من إمكانية التعديل
    check_order_editable(order)

    # 4️⃣ تحديث الإجماليات
    updated_order = await orders_repo.update(
        id=order_id,
        data={
            "subtotal_amount": round(subtotal_amount, 2),
            "discount_amount": round(discount_amount, 2),
            "tax_amount": round(tax_amount, 2),
            "delivery_amount": round(delivery_amount, 2),
            "total_amount": round(total_amount, 2),
        },
    )

    if not updated_order:
        logger.error(
            "update_order_totals_update_failed",
            extra={"order_id": order_id},
        )
        raise NotFoundError(
            message=f"الطلب بـ ID '{order_id}' غير موجود",
        )

    logger.info(
        "order_totals_updated_successfully",
        extra={
            "order_id": order_id,
            "subtotal_amount": round(subtotal_amount, 2),
            "total_amount": round(total_amount, 2),
        },
    )

    return updated_order


# ==============================================
# 🔄 RECALCULATE ORDER TOTALS
# ==============================================

@transactional_order
async def recalculate_order_totals(
    *,
    order_id: int,
    session: AsyncSession,
    include_options: bool = False,
) -> OrderTotals:
    """
    إعادة حساب إجماليات الطلب (جمع بين calculate و update).
    
    Args:
        order_id: معرف الطلب
        session: جلسة قاعدة البيانات غير المتزامنة
        include_options: تضمين أسعار الخيارات في الحساب
        
    Returns:
        OrderTotals: (subtotal, discount, tax, delivery, total)
        
    Raises:
        NotFoundError: إذا لم يتم العثور على الطلب
    """
    logger.info(
        "recalculate_order_totals_started",
        extra={
            "order_id": order_id,
            "include_options": include_options,
        },
    )

    # حساب الإجماليات (يتم التحديث تلقائياً داخل الدالة)
    totals = await calculate_order_totals(
        order_id=order_id,
        session=session,
        include_options=include_options,
    )

    logger.info(
        "recalculate_order_totals_completed",
        extra={
            "order_id": order_id,
            "subtotal": totals[0],
            "total": totals[4],
        },
    )

    return totals


# ==============================================
# 📊 GET ORDER TOTALS
# ==============================================

async def get_order_totals(
    *,
    order_id: int,
    session: AsyncSession,
) -> OrderTotals:
    """
    الحصول على إجماليات الطلب دون إعادة الحساب.
    
    Args:
        order_id: معرف الطلب
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        OrderTotals: (subtotal, discount, tax, delivery, total)
        
    Raises:
        NotFoundError: إذا لم يتم العثور على الطلب
    """
    logger.info(
        "get_order_totals_started",
        extra={"order_id": order_id},
    )

    orders_repo = OrdersRepository(session=session)
    order = await orders_repo.get_by_id(id=order_id)

    if not order:
        logger.error(
            "get_order_totals_order_not_found",
            extra={"order_id": order_id},
        )
        raise NotFoundError(
            message=f"الطلب بـ ID '{order_id}' غير موجود",
        )

    totals = (
        float(order.subtotal_amount or 0),
        float(order.discount_amount or 0),
        float(order.tax_amount or 0),
        float(order.delivery_amount or 0),
        float(order.total_amount or 0),
    )

    logger.info(
        "get_order_totals_retrieved",
        extra={
            "order_id": order_id,
            "subtotal": totals[0],
            "total": totals[4],
        },
    )

    return totals


# ==============================================
# 🧮 CALCULATE ITEM TOTALS
# ==============================================

async def calculate_item_totals(
    *,
    order_item_id: int,
    session: AsyncSession,
) -> Tuple[float, float]:
    """
    حساب إجماليات عنصر طلب معين (السعر الأساسي + الخيارات).
    
    Args:
        order_item_id: معرف عنصر الطلب
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        Tuple[float, float]: (base_total, total_with_options)
        
    Raises:
        NotFoundError: إذا لم يتم العثور على العنصر
    """
    logger.info(
        "calculate_item_totals_started",
        extra={"order_item_id": order_item_id},
    )

    items_repo = OrderItemsRepository(session=session)
    item = await items_repo.get_by_id(id=order_item_id)

    if not item:
        raise NotFoundError(
            message=f"عنصر الطلب بـ ID '{order_item_id}' غير موجود",
        )

    base_total = float(item.total_price)

    # حساب أسعار الخيارات
    options_repo = OrderItemOptionsRepository(session=session)
    options = await options_repo.get_by_order_item_id(order_item_id=order_item_id)
    options_total = sum(float(opt.additional_price) for opt in options)

    total_with_options = base_total + options_total

    logger.info(
        "item_totals_calculated",
        extra={
            "order_item_id": order_item_id,
            "base_total": base_total,
            "options_total": options_total,
            "total_with_options": total_with_options,
        },
    )

    return (base_total, total_with_options)


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# ==============================================

async def calculate_order_totals_compat(
    *,
    order_id: int,
    session: AsyncSession,
) -> OrderTotals:
    """
    دالة متوافقة مع الإصدار القديم (مغلفة).
    
    Args:
        order_id: معرف الطلب
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        OrderTotals: (subtotal, discount, tax, delivery, total)
    """
    return await calculate_order_totals(
        order_id=order_id,
        session=session,
        include_options=False,
    )


async def recalculate_order_totals_compat(
    *,
    order_id: int,
    session: AsyncSession,
) -> OrderTotals:
    """
    دالة متوافقة مع الإصدار القديم (مغلفة).
    
    Args:
        order_id: معرف الطلب
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        OrderTotals: (subtotal, discount, tax, delivery, total)
    """
    return await recalculate_order_totals(
        order_id=order_id,
        session=session,
        include_options=False,
    )