from app.repositories.orders_repo import lock_order
# ==============================================
# 📦 ORDERS SERVICE - UPDATE
# تحديث الطلب 
# (change_order_status, recalculate_order_totals)
# ==============================================

from typing import (
    Any,
    Dict,
    Optional,
    Tuple,
)

from app.services.business.orders.transaction import transactional_order

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# ✅ استيراد الاستثناءات
from app.core.exceptions import (
    NotFoundError,
    ValidationError,
)

from app.core.logger import logger
from app.models.order import Order
from app.repositories.orders_repo import OrdersRepository
from app.repositories.order_status_history_repo import (
    OrderStatusHistoryRepository,
)
from app.services.business.orders.constants import (
    can_transition,
    get_allowed_transitions,
    is_valid_status,
    get_status_display_name,
)
from app.services.business.orders.helpers import check_order_editable
from app.services.business.orders.read import get_restaurant_order  

# ==============================================
# 🧩 TYPES
# ==============================================

OrderTotals = Tuple[float, float, float, float, float]
OrderUpdateData = Dict[str, Any]


# ==============================================
# 🔄 CHANGE ORDER STATUS
# ==============================================

@transactional_order
async def change_order_status(
    *,
    order_id: int,
    new_status: str,
    employee_id: Optional[int] = None,
    note: Optional[str] = None,
    session: AsyncSession,
) -> Order:
    order, _ = await _change_order_status_in_transaction(
        order_id=order_id, new_status=new_status, employee_id=employee_id,
        note=note, session=session,
    )
    return order


async def _change_order_status_in_transaction(
    *,
    order_id: int,
    new_status: str,
    employee_id: Optional[int] = None,
    note: Optional[str] = None,
    session: AsyncSession,
) -> Tuple[Order, bool]:
    """
    تغيير حالة الطلب.
    
    Args:
        order_id: معرف الطلب
        new_status: الحالة الجديدة
        employee_id: معرف الموظف (اختياري)
        note: ملاحظة (اختياري)
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        Order: الطلب المُحدّث
        
    Raises:
        NotFoundError: إذا لم يتم العثور على الطلب
        ValidationError: إذا كانت الحالة غير صالحة أو الانتقال غير مسموح
    """
    logger.info(
        "change_order_status_started",
        extra={
            "order_id": order_id,
            "new_status": new_status,
            "employee_id": employee_id,
        },
    )

    # 1️⃣ التحقق من صحة الحالة
    if not is_valid_status(new_status):
        raise ValidationError(
            message=f"الحالة '{new_status}' غير صالحة",
            details={
                "new_status": new_status,
                "valid_statuses": ["pending", "confirmed", "preparing", "ready", "delivering", "delivered", "completed", "cancelled"],
            },
        )

    # 2️⃣ جلب الطلب
    orders_repo = OrdersRepository(session=session)
    order = await lock_order(order_id=order_id, session=session)

    if not order:
        logger.error(
            "change_order_status_order_not_found",
            extra={"order_id": order_id},
        )
        raise NotFoundError(
            message=f"الطلب بـ ID '{order_id}' غير موجود",
        )

    return await transition_locked_order(
        order=order, new_status=new_status, employee_id=employee_id,
        note=note, session=session,
    )


async def transition_locked_order(*, order, new_status, session,
                                  employee_id=None, note=None):
    """Apply one legal transition to an already locked, authorized order."""
    old_status = order.status
    if old_status == new_status:
        return order, False
    if not can_transition(old_status, new_status):
        raise ValidationError(message=f"Cannot change order from {old_status} to {new_status}")
    order.status = new_status
    await OrderStatusHistoryRepository(session=session).create(data={
        "order_id": order.id, "old_status": old_status, "new_status": new_status,
        "changed_by_employee_id": employee_id, "note": note,
    })
    await session.flush()
    return order, True


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
    from app.services.business.orders.totals import update_order_totals as update_totals

    return await update_totals(
        order_id=order_id,
        subtotal_amount=subtotal_amount,
        discount_amount=discount_amount,
        tax_amount=tax_amount,
        delivery_amount=delivery_amount,
        total_amount=total_amount,
        session=session,
    )


# ==============================================
# 🔄 RECALCULATE ORDER TOTALS (WRAPPER)
# ==============================================

async def recalculate_order_totals(
    *,
    order_id: int,
    session: AsyncSession,
) -> OrderTotals:
    """
    إعادة حساب إجماليات الطلب.
    
    Args:
        order_id: معرف الطلب
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        OrderTotals: (subtotal, discount, tax, delivery, total)
        
    Raises:
        NotFoundError: إذا لم يتم العثور على الطلب
    """
    from app.services.business.orders.totals import recalculate_order_totals as recalculate

    return await recalculate(
        order_id=order_id,
        session=session,
        include_options=False,
    )


# ==============================================
# ✅ UPDATE ORDER
# ==============================================

@transactional_order
async def update_order(
    *,
    order_id: int,
    data: OrderUpdateData,
    session: AsyncSession,
) -> Order:
    """
    تحديث بيانات الطلب العامة.
    
    Args:
        order_id: معرف الطلب
        data: بيانات التحديث
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        Order: الطلب المُحدّث
        
    Raises:
        NotFoundError: إذا لم يتم العثور على الطلب
        ValidationError: إذا كان الطلب مقفلاً
    """
    logger.info(
        "update_order_started",
        extra={
            "order_id": order_id,
            "fields": list(data.keys()),
        },
    )

    # 1️⃣ جلب الطلب
    orders_repo = OrdersRepository(session=session)
    order = await lock_order(order_id=order_id, session=session)

    if not order:
        logger.error(
            "update_order_order_not_found",
            extra={"order_id": order_id},
        )
        raise NotFoundError(
            message=f"الطلب بـ ID '{order_id}' غير موجود",
        )

    # 2️⃣ التحقق من إمكانية التعديل
    check_order_editable(order)

    # 3️⃣ منع تحديث الحالة عبر هذه الدالة (استخدم change_order_status)
    if "status" in data:
        logger.warning(
            "update_order_status_field_ignored",
            extra={
                "order_id": order_id,
                "status": data["status"],
            },
        )
        del data["status"]

    if {"customer_name", "customer_phone"}.intersection(data):
        raise ValidationError(message="Customer identity belongs to the customer profile")
    if "restaurant_id" in data or "user_id" in data:
        raise ValidationError(message="Order ownership cannot be changed")
    if "branch_id" in data:
        from app.services.business.orders.create import validate_branch
        await validate_branch(restaurant_id=order.restaurant_id,
                              branch_id=data["branch_id"], session=session)
    amount_fields = {"subtotal_amount", "discount_amount", "tax_amount", "delivery_amount", "total_amount"}
    if amount_fields.intersection(data):
        from app.services.business.orders.totals import compute_order_totals
        subtotal, discount, tax, delivery, total = compute_order_totals(
            subtotal=data.get("subtotal_amount", order.subtotal_amount),
            discount=data.get("discount_amount", order.discount_amount or 0),
            tax=data.get("tax_amount", order.tax_amount or 0),
            delivery=data.get("delivery_amount", order.delivery_amount or 0))
        data.update(subtotal_amount=subtotal, discount_amount=discount,
                    tax_amount=tax, delivery_amount=delivery, total_amount=total)

    # 4️⃣ تحديث الطلب
    updated_order = await orders_repo.update(
        id=order_id,
        data=data,
    )

    if not updated_order:
        logger.error(
            "update_order_update_failed",
            extra={"order_id": order_id},
        )
        raise NotFoundError(
            message=f"الطلب بـ ID '{order_id}' غير موجود",
        )

    logger.info(
        "update_order_successfully",
        extra={
            "order_id": order_id,
            "order_number": order.order_number,
            "fields": list(data.keys()),
        },
    )

    return updated_order


# ==============================================
# 📝 UPDATE ORDER CUSTOMER INFO
# ==============================================

@transactional_order
async def update_order_customer_info(
    *,
    order_id: int,
    customer_name: Optional[str] = None,
    customer_phone: Optional[str] = None,
    delivery_address: Optional[str] = None,
    customer_note: Optional[str] = None,
    session: AsyncSession,
) -> Order:
    """
    تحديث معلومات العميل في الطلب.
    
    Args:
        order_id: معرف الطلب
        customer_name: اسم العميل (اختياري)
        customer_phone: رقم هاتف العميل (اختياري)
        delivery_address: عنوان التوصيل (اختياري)
        customer_note: ملاحظة العميل (اختياري)
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        Order: الطلب المُحدّث
        
    Raises:
        NotFoundError: إذا لم يتم العثور على الطلب
        ValidationError: إذا كان الطلب مقفلاً
    """
    logger.info(
        "update_order_customer_info_started",
        extra={
            "order_id": order_id,
            "customer_name": customer_name,
        },
    )

    data = {}

    if customer_name is not None:
        data["customer_name"] = customer_name

    if customer_phone is not None:
        data["customer_phone"] = customer_phone

    if delivery_address is not None:
        data["delivery_address"] = delivery_address

    if customer_note is not None:
        data["customer_note"] = customer_note

    if not data:
        logger.info(
            "update_order_customer_info_no_fields",
            extra={"order_id": order_id},
        )
        # ✅ استخدام الدالة الموجودة من read.py
        order = await get_restaurant_order(
            order_id=order_id,
            session=session,
        )
        if not order:
            raise NotFoundError(
                message=f"الطلب بـ ID '{order_id}' غير موجود",
            )
        return order

    return await update_order(
        order_id=order_id,
        data=data,
        session=session,
    )


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# ==============================================

# دوال التوافق مع الإصدار القديم
async def change_order_status_compat(
    *,
    order_id: int,
    new_status: str,
    employee_id: Optional[int] = None,
    note: Optional[str] = None,
    session: AsyncSession,
) -> Order:
    """
    دالة متوافقة مع الإصدار القديم (مغلفة).
    
    Args:
        order_id: معرف الطلب
        new_status: الحالة الجديدة
        employee_id: معرف الموظف (اختياري)
        note: ملاحظة (اختياري)
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        Order: الطلب المُحدّث
    """
    return await change_order_status(
        order_id=order_id,
        new_status=new_status,
        employee_id=employee_id,
        note=note,
        session=session,
    )


async def update_order_compat(
    *,
    order_id: int,
    data: OrderUpdateData,
    session: AsyncSession,
) -> Order:
    """
    دالة متوافقة مع الإصدار القديم (مغلفة).
    
    Args:
        order_id: معرف الطلب
        data: بيانات التحديث
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        Order: الطلب المُحدّث
    """
    return await update_order(
        order_id=order_id,
        data=data,
        session=session,
    )