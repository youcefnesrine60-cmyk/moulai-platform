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

async def change_order_status(
    *,
    order_id: int,
    new_status: str,
    employee_id: Optional[int] = None,
    note: Optional[str] = None,
    session: AsyncSession,
) -> Order:
    previous_defer_commits = session.info.get("defer_repository_commit")
    had_transaction = session.in_transaction()
    session.info["defer_repository_commit"] = True
    transaction = session.begin_nested() if had_transaction else session.begin()
    try:
        async with transaction:
            order, _ = await _change_order_status_in_transaction(
                order_id=order_id,
                new_status=new_status,
                employee_id=employee_id,
                note=note,
                session=session,
            )
        return order
    finally:
        if previous_defer_commits is None:
            session.info.pop("defer_repository_commit", None)
        else:
            session.info["defer_repository_commit"] = previous_defer_commits


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
    order = (
        await session.execute(
            select(Order)
            .where(Order.id == order_id)
            .with_for_update(),
        )
    ).scalar_one_or_none()

    if not order:
        logger.error(
            "change_order_status_order_not_found",
            extra={"order_id": order_id},
        )
        raise NotFoundError(
            message=f"الطلب بـ ID '{order_id}' غير موجود",
        )

    old_status = order.status

    # 3️⃣ إذا كانت الحالة نفسها، لا تفعل شيئاً
    if old_status == new_status:
        logger.info(
            "change_order_status_same_status",
            extra={
                "order_id": order_id,
                "status": new_status,
            },
        )
        return order, False

    # 4️⃣ التحقق من إمكانية الانتقال
    if not can_transition(old_status, new_status):
        raise ValidationError(
            message=f"لا يمكن تغيير حالة الطلب #{order.order_number} من '{get_status_display_name(old_status)}' إلى '{get_status_display_name(new_status)}'",
            details={
                "order_id": order_id,
                "order_number": order.order_number,
                "old_status": old_status,
                "new_status": new_status,
                "allowed_transitions": list(get_allowed_transitions(old_status)),
            },
        )

    # 5️⃣ تحديث حالة الطلب
    updated_order = await orders_repo.update(
        id=order_id,
        data={"status": new_status},
    )

    if not updated_order:
        logger.error(
            "change_order_status_update_failed",
            extra={"order_id": order_id},
        )
        raise NotFoundError(
            message=f"الطلب بـ ID '{order_id}' غير موجود",
        )

    # 6️⃣ إنشاء سجل في تاريخ الحالة
    history_repo = OrderStatusHistoryRepository(session=session)
    await history_repo.create(
        data={
            "order_id": order_id,
            "old_status": old_status,
            "new_status": new_status,
            "changed_by_employee_id": employee_id,
            "note": note or f"تم تغيير الحالة من '{get_status_display_name(old_status)}' إلى '{get_status_display_name(new_status)}'",
        },
    )

    logger.info(
        "order_status_changed_successfully",
        extra={
            "order_id": order_id,
            "order_number": order.order_number,
            "old_status": old_status,
            "new_status": new_status,
            "employee_id": employee_id,
        },
    )

    return updated_order, True


# ==============================================
# 💰 UPDATE ORDER TOTALS (WRAPPER)
# ==============================================

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
    order = await orders_repo.get_by_id(id=order_id)

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