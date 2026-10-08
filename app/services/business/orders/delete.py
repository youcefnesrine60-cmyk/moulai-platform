from app.repositories.orders_repo import lock_order
from app.services.business.orders.transaction import transactional_order
# ==============================================
# 📦 ORDERS SERVICE - DELETE
# حذف الطلب (remove_order)
# ==============================================

from sqlalchemy.ext.asyncio import AsyncSession

# ✅ استيراد الاستثناءات
from app.core.exceptions import (
    NotFoundError,
    ValidationError,
)

from app.core.logger import logger
from app.repositories.order_items_repo import OrderItemsRepository
from app.repositories.order_payments_repo import OrderPaymentsRepository
from app.repositories.orders_repo import OrdersRepository
from app.repositories.order_status_history_repo import OrderStatusHistoryRepository
from app.services.business.orders.constants import is_editable_status

# ==============================================
# ❌ DELETE ORDER
# ==============================================

@transactional_order
async def remove_order(
    *,
    order_id: int,
    permanent: bool = False,
    session: AsyncSession,
) -> None:
    """
    حذف طلب.
    
    Args:
        order_id: معرف الطلب
        permanent: حذف نهائي (بدلاً من الحذف المنطقي)
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Raises:
        NotFoundError: إذا لم يتم العثور على الطلب
        ValidationError: إذا كان الطلب مقفلاً أو مدفوعاً
    """
    logger.info(
        "remove_order_started",
        extra={
            "order_id": order_id,
            "permanent": permanent,
        },
    )

    # 1️⃣ التحقق من وجود الطلب
    orders_repo = OrdersRepository(session=session)
    order = await lock_order(order_id=order_id, session=session)

    if not order:
        logger.error(
            "remove_order_order_not_found",
            extra={"order_id": order_id},
        )
        raise NotFoundError(
            message=f"الطلب بـ ID '{order_id}' غير موجود",
        )

    # 2️⃣ التحقق من إمكانية حذف الطلب
    if order.is_paid:
        raise ValidationError(
            message=f"لا يمكن حذف الطلب #{order.order_number} لأنه مدفوع",
            details={
                "order_id": order_id,
                "order_number": order.order_number,
                "is_paid": order.is_paid,
            },
        )

    if not is_editable_status(order.status):
        raise ValidationError(
            message=f"لا يمكن حذف الطلب #{order.order_number} في حالة '{order.status}'",
            details={
                "order_id": order_id,
                "order_number": order.order_number,
                "status": order.status,
                "editable_statuses": ["pending", "confirmed"],
            },
        )

    # 3️⃣ حذف الطلب
    if permanent:
        # حذف نهائي - حذف جميع البيانات المرتبطة
        await _delete_order_permanently(
            order_id=order_id,
            session=session,
        )
    else:
        # حذف منطقي - تعيين is_active = False
        await _delete_order_logically(
            order_id=order_id,
            session=session,
        )

    logger.info(
        "order_removed_successfully",
        extra={
            "order_id": order_id,
            "order_number": order.order_number,
            "permanent": permanent,
        },
    )


# ==============================================
# ❌ DELETE ORDER PERMANENTLY (INTERNAL)
# ==============================================

async def _delete_order_permanently(
    *,
    order_id: int,
    session: AsyncSession,
) -> None:
    """
    حذف الطلب نهائياً مع جميع البيانات المرتبطة.
    
    Args:
        order_id: معرف الطلب
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    # ORM/database cascades own child deletion; the use case owns the transaction.
    await OrdersRepository(session=session).delete(id=order_id)


# ==============================================
# ❌ DELETE ORDER LOGICALLY (INTERNAL)
# ==============================================

async def _delete_order_logically(
    *,
    order_id: int,
    session: AsyncSession,
) -> None:
    """
    حذف الطلب منطقياً (تعيين is_active = False).
    
    Args:
        order_id: معرف الطلب
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    from app.services.business.orders.update import change_order_status
    await change_order_status(order_id=order_id, new_status="cancelled",
                              note="Order deleted", session=session)

    logger.info(
        "order_logically_deleted",
        extra={"order_id": order_id},
    )


# ==============================================
# ❌ DELETE ALL ORDERS FOR RESTAURANT
# ==============================================

@transactional_order
async def delete_restaurant_orders(
    *,
    restaurant_id: int,
    permanent: bool = False,
    session: AsyncSession,
) -> dict:
    """
    حذف جميع طلبات مطعم معين.
    
    Args:
        restaurant_id: معرف المطعم
        permanent: حذف نهائي
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        dict: نتائج الحذف (deleted_count, failed_count)
        
    Raises:
        ValidationError: إذا كان المطعم يحتوي على طلبات مدفوعة
    """
    logger.info(
        "delete_restaurant_orders_started",
        extra={
            "restaurant_id": restaurant_id,
            "permanent": permanent,
        },
    )

    orders_repo = OrdersRepository(session=session)

    # الحصول على جميع طلبات المطعم
    orders = await orders_repo.get_by_restaurant_id(
        restaurant_id=restaurant_id,
        limit=10000,
    )

    if not orders:
        logger.info(
            "no_orders_found_for_restaurant",
            extra={"restaurant_id": restaurant_id},
        )
        return {"deleted_count": 0, "failed_count": 0}

    # التحقق من وجود طلبات مدفوعة
    paid_orders = [o for o in orders if o.is_paid]

    if paid_orders:
        raise ValidationError(
            message=f"لا يمكن حذف طلبات المطعم #{restaurant_id} لأنه يحتوي على طلبات مدفوعة",
            details={
                "restaurant_id": restaurant_id,
                "paid_orders_count": len(paid_orders),
                "paid_order_ids": [o.id for o in paid_orders],
            },
        )

    # حذف الطلبات
    deleted_count = 0
    failed_count = 0

    for order in orders:
        try:
            await remove_order(
                order_id=order.id,
                permanent=permanent,
                session=session,
            )
            deleted_count += 1

        except Exception as e:
            logger.error(
                "delete_restaurant_order_failed",
                extra={
                    "order_id": order.id,
                    "error": str(e),
                },
            )
            failed_count += 1

    logger.info(
        "restaurant_orders_deleted",
        extra={
            "restaurant_id": restaurant_id,
            "deleted_count": deleted_count,
            "failed_count": failed_count,
        },
    )

    return {
        "deleted_count": deleted_count,
        "failed_count": failed_count,
    }


# ==============================================
# ❌ DELETE ORDERS BY STATUS
# ==============================================

@transactional_order
async def delete_orders_by_status(
    *,
    restaurant_id: int,
    status: str,
    permanent: bool = False,
    session: AsyncSession,
) -> dict:
    """
    حذف طلبات حسب الحالة.
    
    Args:
        restaurant_id: معرف المطعم
        status: حالة الطلب
        permanent: حذف نهائي
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        dict: نتائج الحذف (deleted_count, failed_count)
        
    Raises:
        ValidationError: إذا كانت الحالة غير صالحة
    """
    from app.services.business.orders.constants import VALID_STATUSES

    if status not in VALID_STATUSES:
        raise ValidationError(
            message=f"الحالة '{status}' غير صالحة",
            details={
                "status": status,
                "valid_statuses": list(VALID_STATUSES),
            },
        )

    logger.info(
        "delete_orders_by_status_started",
        extra={
            "restaurant_id": restaurant_id,
            "status": status,
            "permanent": permanent,
        },
    )

    orders_repo = OrdersRepository(session=session)

    # الحصول على الطلبات حسب الحالة
    orders = await orders_repo.get_by_status(
        restaurant_id=restaurant_id,
        status=status,
        limit=10000,
    )

    if not orders:
        logger.info(
            "no_orders_found_for_status",
            extra={
                "restaurant_id": restaurant_id,
                "status": status,
            },
        )
        return {"deleted_count": 0, "failed_count": 0}

    # حذف الطلبات
    deleted_count = 0
    failed_count = 0

    for order in orders:
        try:
            await remove_order(
                order_id=order.id,
                permanent=permanent,
                session=session,
            )
            deleted_count += 1

        except Exception as e:
            logger.error(
                "delete_order_by_status_failed",
                extra={
                    "order_id": order.id,
                    "error": str(e),
                },
            )
            failed_count += 1

    logger.info(
        "orders_by_status_deleted",
        extra={
            "restaurant_id": restaurant_id,
            "status": status,
            "deleted_count": deleted_count,
            "failed_count": failed_count,
        },
    )

    return {
        "deleted_count": deleted_count,
        "failed_count": failed_count,
    }


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# ==============================================

# دالة التوافق مع الإصدار القديم
async def remove_order_compat(
    *,
    order_id: int,
    session: AsyncSession,
) -> None:
    """
    دالة متوافقة مع الإصدار القديم (مغلفة).
    
    Args:
        order_id: معرف الطلب
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    await remove_order(
        order_id=order_id,
        permanent=False,
        session=session,
    )