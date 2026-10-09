# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / SERVICES / BUSINESS / ORDERS / COMPLETE
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for complete.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.services.business.orders.constants import ALLOWED_TRANSITIONS
from app.services.business.orders.transaction import transactional_order

# ==============================================
# 📦 ORDERS SERVICE - COMPLETE
# إكمال الطلب (complete_order)
# ==============================================

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

# ✅ استيراد الاستثناءات
from app.core.exceptions import (
    NotFoundError,
    ValidationError,
)

from app.core.logger import logger
from app.repositories.orders_repo import OrdersRepository
from app.services.business.orders.update import change_order_status

# ==============================================
# 🧩 CONSTANTS
# ==============================================

# الحالات التي يمكن إكمالها
COMPLETABLE_STATUSES = {
    state for state, targets in ALLOWED_TRANSITIONS.items() if "completed" in targets
}

# الحالات التي لا يمكن إكمالها
NON_COMPLETABLE_STATUSES = {"pending", "cancelled", "completed"}


# ==============================================
# ✅ COMPLETE ORDER
# ==============================================


@transactional_order
async def complete_order(
    *,
    order_id: int,
    employee_id: Optional[int] = None,
    note: Optional[str] = None,
    session: AsyncSession,
) -> None:
    """
    إكمال الطلب (تعيين الحالة إلى completed).

    Args:
        order_id: معرف الطلب
        employee_id: معرف الموظف (اختياري)
        note: ملاحظة إضافية (اختياري)
        session: جلسة قاعدة البيانات غير المتزامنة

    Raises:
        NotFoundError: إذا لم يتم العثور على الطلب
        ValidationError: إذا كانت حالة الطلب لا تسمح بالإكمال
    """
    logger.info(
        "complete_order_started",
        extra={
            "order_id": order_id,
            "employee_id": employee_id,
            "note": note,
        },
    )

    # 1️⃣ التحقق من وجود الطلب
    orders_repo = OrdersRepository(session=session)
    order = await orders_repo.get_by_id(id=order_id)

    if not order:
        logger.error(
            "complete_order_order_not_found",
            extra={"order_id": order_id},
        )
        raise NotFoundError(
            message=f"الطلب بـ ID '{order_id}' غير موجود",
        )

    # 2️⃣ التحقق من إمكانية إكمال الطلب
    current_status = order.status

    if current_status in NON_COMPLETABLE_STATUSES:
        if current_status == "completed":
            raise ValidationError(
                message=f"الطلب #{order_id} مكتمل بالفعل",
            )
        elif current_status == "cancelled":
            raise ValidationError(
                message=f"لا يمكن إكمال الطلب #{order_id} لأنه ملغى",
            )
        else:
            raise ValidationError(
                message=f"لا يمكن إكمال الطلب #{order_id} لأنه في حالة '{current_status}'",
                details={
                    "order_id": order_id,
                    "current_status": current_status,
                    "allowed_statuses": COMPLETABLE_STATUSES,
                },
            )

    if current_status not in COMPLETABLE_STATUSES:
        raise ValidationError(
            message=f"لا يمكن إكمال الطلب #{order_id} في حالة '{current_status}'",
            details={
                "order_id": order_id,
                "current_status": current_status,
                "allowed_statuses": COMPLETABLE_STATUSES,
            },
        )

    # 3️⃣ التحقق من أن الطلب مدفوع (اختياري)
    # يمكن تفعيل هذا التحقق إذا كان النظام يتطلب الدفع قبل الإكمال
    # if not order.is_paid:
    #     raise ValidationError(
    #         message=f"الطلب #{order_id} غير مدفوع، يرجى إتمام الدفع أولاً",
    #         details={
    #             "order_id": order_id,
    #             "is_paid": order.is_paid,
    #         },
    #     )

    # 4️⃣ تغيير حالة الطلب إلى completed
    completion_note = (
        note or f"تم إكمال الطلب بواسطة {'الموظف' if employee_id else 'النظام'}"
    )

    await change_order_status(
        order_id=order_id,
        new_status="completed",
        employee_id=employee_id,
        note=completion_note,
        session=session,
    )

    logger.info(
        "order_completed_successfully",
        extra={
            "order_id": order_id,
            "employee_id": employee_id,
            "previous_status": current_status,
        },
    )


# ==============================================
# ✅ COMPLETE ORDER WITH DELIVERY CONFIRMATION
# ==============================================


@transactional_order
async def complete_order_with_delivery_confirmation(
    *,
    order_id: int,
    employee_id: Optional[int] = None,
    delivery_note: Optional[str] = None,
    session: AsyncSession,
) -> None:
    """
    إكمال الطلب مع تأكيد التسليم (للطلبات التي تم توصيلها).

    Args:
        order_id: معرف الطلب
        employee_id: معرف الموظف (اختياري)
        delivery_note: ملاحظة التسليم (اختياري)
        session: جلسة قاعدة البيانات غير المتزامنة

    Raises:
        NotFoundError: إذا لم يتم العثور على الطلب
        ValidationError: إذا كانت حالة الطلب لا تسمح بالإكمال
    """
    logger.info(
        "complete_order_with_delivery_started",
        extra={
            "order_id": order_id,
            "employee_id": employee_id,
            "delivery_note": delivery_note,
        },
    )

    # 1️⃣ التحقق من وجود الطلب
    orders_repo = OrdersRepository(session=session)
    order = await orders_repo.get_by_id(id=order_id)

    if not order:
        logger.error(
            "complete_order_delivery_order_not_found",
            extra={"order_id": order_id},
        )
        raise NotFoundError(
            message=f"الطلب بـ ID '{order_id}' غير موجود",
        )

    # 2️⃣ التحقق من أن الطلب في حالة "delivering"
    if order.status != "delivering":
        raise ValidationError(
            message=f"الطلب #{order_id} ليس في حالة توصيل (الحالة الحالية: {order.status})",
            details={
                "order_id": order_id,
                "current_status": order.status,
                "required_status": "delivering",
            },
        )

    # 3️⃣ إكمال الطلب مع ملاحظة التسليم
    note = delivery_note or "تم تسليم الطلب وتأكيد الاستلام"

    await change_order_status(
        order_id=order_id,
        new_status="delivered",
        employee_id=employee_id,
        note=note,
        session=session,
    )
    await complete_order(
        order_id=order_id,
        employee_id=employee_id,
        note=note,
        session=session,
    )

    logger.info(
        "order_completed_with_delivery_confirmation",
        extra={
            "order_id": order_id,
            "employee_id": employee_id,
        },
    )


# ==============================================
# ✅ BULK COMPLETE ORDERS
# ==============================================


@transactional_order
async def bulk_complete_orders(
    *,
    order_ids: list[int],
    employee_id: Optional[int] = None,
    note: Optional[str] = None,
    session: AsyncSession,
) -> dict:
    """
    إكمال مجموعة من الطلبات دفعة واحدة.

    Args:
        order_ids: قائمة معرفات الطلبات
        employee_id: معرف الموظف (اختياري)
        note: ملاحظة إضافية (اختياري)
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        dict: نتائج الإكمال (completed, failed)

    Raises:
        ValidationError: إذا كانت القائمة فارغة
    """
    if not order_ids:
        raise ValidationError(
            message="قائمة الطلبات فارغة",
        )

    logger.info(
        "bulk_complete_orders_started",
        extra={
            "order_count": len(order_ids),
            "employee_id": employee_id,
        },
    )

    results = {
        "completed": [],
        "failed": [],
    }

    for order_id in order_ids:
        try:
            await complete_order(
                order_id=order_id,
                employee_id=employee_id,
                note=note,
                session=session,
            )
            results["completed"].append(order_id)

        except (NotFoundError, ValidationError) as e:
            logger.warning(
                "bulk_complete_order_failed",
                extra={
                    "order_id": order_id,
                    "error": str(e),
                },
            )
            results["failed"].append(
                {
                    "order_id": order_id,
                    "error": str(e),
                }
            )

        except Exception as e:
            logger.error(
                "bulk_complete_order_unexpected_error",
                extra={
                    "order_id": order_id,
                    "error": str(e),
                },
            )
            results["failed"].append(
                {
                    "order_id": order_id,
                    "error": f"خطأ غير متوقع: {str(e)}",
                }
            )

    logger.info(
        "bulk_complete_orders_completed",
        extra={
            "total": len(order_ids),
            "completed": len(results["completed"]),
            "failed": len(results["failed"]),
        },
    )

    return results


# ==============================================
# ✅ CHECK IF ORDER CAN BE COMPLETED
# ==============================================


async def can_complete_order(
    *,
    order_id: int,
    session: AsyncSession,
) -> bool:
    """
    التحقق مما إذا كان يمكن إكمال الطلب.

    Args:
        order_id: معرف الطلب
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        bool: True إذا كان يمكن الإكمال، False إذا لم يكن
    """
    try:
        orders_repo = OrdersRepository(session=session)
        order = await orders_repo.get_by_id(id=order_id)

        if not order:
            return False

        return order.status in COMPLETABLE_STATUSES

    except Exception as e:
        logger.error(
            "can_complete_order_error",
            extra={
                "order_id": order_id,
                "error": str(e),
            },
        )
        return False


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# ==============================================


# دالة التوافق مع الإصدار القديم
# ==============================================
# COMPLETE ORDER COMPAT
# ==============================================


async def complete_order_compat(
    *,
    order_id: int,
    employee_id: Optional[int] = None,
    note: Optional[str] = None,
    session: AsyncSession,
) -> None:
    """
    دالة متوافقة مع الإصدار القديم (مغلفة).

    Args:
        order_id: معرف الطلب
        employee_id: معرف الموظف (اختياري)
        note: ملاحظة إضافية (اختياري)
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    await complete_order(
        order_id=order_id,
        employee_id=employee_id,
        note=note,
        session=session,
    )
