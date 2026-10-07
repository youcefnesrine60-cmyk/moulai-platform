# ==============================================
# 📦 ORDERS SERVICE - CANCEL
# إلغاء الطلب (cancel_order)
# ==============================================

from typing import Optional

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
from app.services.business.orders.update import change_order_status

# ==============================================
# 🧩 CONSTANTS
# ==============================================

# الحالات التي يمكن إلغاؤها
CANCELLABLE_STATUSES = {"pending", "confirmed", "preparing", "ready"}

# الحالات التي لا يمكن إلغاؤها
NON_CANCELLABLE_STATUSES = {"completed", "delivered", "cancelled"}


# ==============================================
# ❌ CANCEL ORDER
# ==============================================

async def cancel_order(
    *,
    order_id: int,
    employee_id: Optional[int] = None,
    reason: Optional[str] = None,
    session: AsyncSession,
) -> None:
    """
    إلغاء الطلب.
    
    Args:
        order_id: معرف الطلب
        employee_id: معرف الموظف (اختياري)
        reason: سبب الإلغاء (اختياري)
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Raises:
        NotFoundError: إذا لم يتم العثور على الطلب
        ValidationError: إذا كانت حالة الطلب لا تسمح بالإلغاء
    """
    logger.info(
        "cancel_order_started",
        extra={
            "order_id": order_id,
            "employee_id": employee_id,
            "reason": reason,
        },
    )

    had_transaction = session.in_transaction()
    transaction = session.begin_nested() if had_transaction else session.begin()
    async with transaction:
        order = (
            await session.execute(
                select(Order)
                .where(Order.id == order_id)
                .with_for_update(),
            )
        ).scalar_one_or_none()
        if not order:
            logger.error(
                "cancel_order_order_not_found",
                extra={"order_id": order_id},
            )
            raise NotFoundError(
                message=f"الطلب بـ ID '{order_id}' غير موجود",
            )

        current_status = order.status
        if current_status == "cancelled":
            raise ValidationError(
                message=f"الطلب #{order_id} ملغى بالفعل",
            )
        if current_status not in CANCELLABLE_STATUSES:
            raise ValidationError(
                message=f"لا يمكن إلغاء الطلب #{order_id} في حالة '{current_status}'",
                details={
                    "order_id": order_id,
                    "current_status": current_status,
                    "allowed_statuses": CANCELLABLE_STATUSES,
                },
            )

        if order.is_paid:
            logger.info(
                "cancel_order_paid_order",
                extra={
                    "order_id": order_id,
                    "payment_status": order.payment_status,
                },
            )

        note = reason or f"تم إلغاء الطلب بواسطة {'الموظف' if employee_id else 'النظام'}"
        await change_order_status(
            order_id=order_id,
            new_status="cancelled",
            employee_id=employee_id,
            note=note,
            session=session,
        )

    logger.info(
        "order_cancelled_successfully",
        extra={
            "order_id": order_id,
            "employee_id": employee_id,
            "previous_status": current_status,
        },
    )


# ==============================================
# ❌ CANCEL ORDER WITH REFUND
# ==============================================

async def cancel_order_with_refund(
    *,
    order_id: int,
    employee_id: Optional[int] = None,
    reason: Optional[str] = None,
    session: AsyncSession,
) -> None:
    """
    إلغاء الطلب مع استرداد المبلغ (للطلبات المدفوعة).
    
    Args:
        order_id: معرف الطلب
        employee_id: معرف الموظف (اختياري)
        reason: سبب الإلغاء (اختياري)
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Raises:
        NotFoundError: إذا لم يتم العثور على الطلب
        ValidationError: إذا كانت حالة الطلب لا تسمح بالإلغاء أو لم يتم الدفع
    """
    logger.info(
        "cancel_order_with_refund_started",
        extra={
            "order_id": order_id,
            "employee_id": employee_id,
            "reason": reason,
        },
    )

    # 1️⃣ التحقق من وجود الطلب
    orders_repo = OrdersRepository(session=session)
    order = await orders_repo.get_by_id(id=order_id)

    if not order:
        logger.error(
            "cancel_order_refund_order_not_found",
            extra={"order_id": order_id},
        )
        raise NotFoundError(
            message=f"الطلب بـ ID '{order_id}' غير موجود",
        )

    # 2️⃣ التحقق من أن الطلب مدفوع
    if not order.is_paid:
        raise ValidationError(
            message=f"الطلب #{order_id} غير مدفوع، لا حاجة لاسترداد المبلغ",
            details={
                "order_id": order_id,
                "is_paid": order.is_paid,
            },
        )

    # 3️⃣ إلغاء الطلب (مع تمرير reason)
    await cancel_order(
        order_id=order_id,
        employee_id=employee_id,
        reason=reason or "تم إلغاء الطلب مع استرداد المبلغ",
        session=session,
    )

    # 4️⃣ معالجة استرداد المبلغ (يمكن إضافة منطق خاص)
    # TODO: استدعاء خدمة الدفع لاسترداد المبلغ

    logger.info(
        "order_cancelled_with_refund_successfully",
        extra={
            "order_id": order_id,
            "employee_id": employee_id,
        },
    )


# ==============================================
# ❌ BULK CANCEL ORDERS
# ==============================================

async def bulk_cancel_orders(
    *,
    order_ids: list[int],
    employee_id: Optional[int] = None,
    reason: Optional[str] = None,
    session: AsyncSession,
) -> dict:
    """
    إلغاء مجموعة من الطلبات دفعة واحدة.
    
    Args:
        order_ids: قائمة معرفات الطلبات
        employee_id: معرف الموظف (اختياري)
        reason: سبب الإلغاء (اختياري)
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        dict: نتائج الإلغاء (cancelled, failed)
        
    Raises:
        ValueError: إذا كانت القائمة فارغة
    """
    if not order_ids:
        raise ValidationError(
            message="قائمة الطلبات فارغة",
        )

    logger.info(
        "bulk_cancel_orders_started",
        extra={
            "order_count": len(order_ids),
            "employee_id": employee_id,
        },
    )

    results = {
        "cancelled": [],
        "failed": [],
    }

    for order_id in order_ids:
        try:
            await cancel_order(
                order_id=order_id,
                employee_id=employee_id,
                reason=reason,
                session=session,
            )
            results["cancelled"].append(order_id)

        except (NotFoundError, ValidationError) as e:
            logger.warning(
                "bulk_cancel_order_failed",
                extra={
                    "order_id": order_id,
                    "error": str(e),
                },
            )
            results["failed"].append({
                "order_id": order_id,
                "error": str(e),
            })

        except Exception as e:
            logger.error(
                "bulk_cancel_order_unexpected_error",
                extra={
                    "order_id": order_id,
                    "error": str(e),
                },
            )
            results["failed"].append({
                "order_id": order_id,
                "error": f"خطأ غير متوقع: {str(e)}",
            })

    logger.info(
        "bulk_cancel_orders_completed",
        extra={
            "total": len(order_ids),
            "cancelled": len(results["cancelled"]),
            "failed": len(results["failed"]),
        },
    )

    return results


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# ==============================================

# دالة التوافق مع الإصدار القديم
async def cancel_order_compat(
    *,
    order_id: int,
    employee_id: Optional[int] = None,
    reason: Optional[str] = None,
    session: AsyncSession,
) -> None:
    """
    دالة متوافقة مع الإصدار القديم (مغلفة).
    
    Args:
        order_id: معرف الطلب
        employee_id: معرف الموظف (اختياري)
        reason: سبب الإلغاء (اختياري)
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    await cancel_order(
        order_id=order_id,
        employee_id=employee_id,
        reason=reason,
        session=session,
    )