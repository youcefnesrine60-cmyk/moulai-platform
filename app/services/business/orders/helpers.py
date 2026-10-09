# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / SERVICES / BUSINESS / ORDERS / HELPERS
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for helpers.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from typing import Any, Dict, Optional, Union

from app.models.order import Order
from app.services.business.orders.constants import (
    is_locked_status,
    can_transition,
    get_status_display_name,
)

# ==============================================
# 🧩 TYPES
# ==============================================

OrderDict = Dict[str, Any]
OrderStatusType = str


# ==============================================
# 🔒 CHECK ORDER EDITABLE
# ==============================================


def check_order_editable(
    order: Union[Order, OrderDict],
) -> None:
    """
    تتحقق من إمكانية تعديل الطلب.

    Args:
        order: كائن الطلب من SQLAlchemy أو قاموس بيانات

    Raises:
        ValueError: إذا كان الطلب في حالة تمنع التعديل
    """
    # استخراج الحالة من الكائن أو القاموس
    if isinstance(order, Order):
        status = order.status
        order_number = getattr(order, "order_number", "غير معروف")
    else:
        status = str(order.get("status", ""))
        order_number = order.get("order_number", "غير معروف")

    if is_locked_status(status):
        raise ValueError(
            f"لا يمكن تعديل الطلب #{order_number} لأنه في حالة '{get_status_display_name(status)}'",
        )


# ==============================================
# 🔒 CHECK ORDER EDITABLE (DICT VERSION)
# ==============================================


def check_order_editable_from_dict(
    order: OrderDict,
) -> None:
    """
    تتحقق من إمكانية تعديل الطلب (نسخة متوافقة مع الإصدار القديم).

    Args:
        order: بيانات الطلب من قاعدة البيانات (قاموس)

    Raises:
        ValueError: إذا كان الطلب في حالة تمنع التعديل
    """
    status = str(order.get("status", ""))
    order_number = order.get("order_number", "غير معروف")

    if is_locked_status(status):
        raise ValueError(
            f"لا يمكن تعديل الطلب #{order_number} لأنه في حالة '{get_status_display_name(status)}'",
        )


# ==============================================
# 🔒 CHECK ORDER EDITABLE BY STATUS
# ==============================================


def check_order_editable_by_status(
    status: str,
    order_number: Optional[str] = None,
) -> None:
    """
    تتحقق من إمكانية تعديل الطلب بناءً على حالته.

    Args:
        status: حالة الطلب
        order_number: رقم الطلب (اختياري، للعرض في رسالة الخطأ)

    Raises:
        ValueError: إذا كانت الحالة تمنع التعديل
    """
    order_display = f" #{order_number}" if order_number else ""

    if is_locked_status(status):
        raise ValueError(
            f"لا يمكن تعديل الطلب{order_display} لأنه في حالة '{get_status_display_name(status)}'",
        )


# ==============================================
# ✅ IS ORDER EDITABLE
# ==============================================


def is_order_editable(
    order: Union[Order, OrderDict, str],
) -> bool:
    """
    تتحقق مما إذا كان الطلب قابلاً للتعديل.

    Args:
        order: كائن الطلب، قاموس بيانات، أو حالة (string)

    Returns:
        bool: True إذا كان قابلاً للتعديل، False إذا كان مقفلاً
    """
    if isinstance(order, str):
        # حالة فقط
        return not is_locked_status(order)
    elif isinstance(order, Order):
        # كائن Order
        return not is_locked_status(order.status)
    elif isinstance(order, dict):
        # قاموس
        status = str(order.get("status", ""))
        return not is_locked_status(status)
    return False


# ==============================================
# ✅ VALIDATE ORDER TRANSITION
# ==============================================


def validate_order_transition(
    current_status: str,
    new_status: str,
    order_number: Optional[str] = None,
) -> None:
    """
    التحقق من صحة انتقال حالة الطلب.

    Args:
        current_status: الحالة الحالية
        new_status: الحالة الجديدة
        order_number: رقم الطلب (اختياري، للعرض في رسالة الخطأ)

    Raises:
        ValueError: إذا كان الانتقال غير مسموح به
    """
    order_display = f" #{order_number}" if order_number else ""

    if not can_transition(current_status, new_status):
        raise ValueError(
            f"لا يمكن تغيير حالة الطلب{order_display} من '{get_status_display_name(current_status)}' "
            f"إلى '{get_status_display_name(new_status)}'",
        )


# ==============================================
# 🔧 GET ORDER_DISPLAY_NAME
# ==============================================


def get_order_display_name(
    order: Union[Order, OrderDict],
) -> str:
    """
    الحصول على اسم عرض للطلب.

    Args:
        order: كائن الطلب أو قاموس

    Returns:
        str: اسم العرض (رقم الطلب أو المعرف)
    """
    if isinstance(order, Order):
        return f"#{getattr(order, 'order_number', order.id)}"
    else:
        return f"#{order.get('order_number', order.get('id', 'غير معروف'))}"


# ==============================================
# 📋 SUMMARY HELPER
# ==============================================


def build_order_summary(
    order: Union[Order, OrderDict],
) -> Dict[str, Any]:
    """
    بناء ملخص للطلب.

    Args:
        order: كائن الطلب أو قاموس

    Returns:
        dict: ملخص الطلب
    """
    if isinstance(order, Order):
        return {
            "id": order.id,
            "order_number": getattr(order, "order_number", "N/A"),
            "status": order.status,
            "status_display": get_status_display_name(order.status),
            "total_amount": getattr(order, "total_amount", 0),
            "customer_name": getattr(order, "customer_name", "غير معروف"),
            "is_paid": getattr(order, "is_paid", False),
            "is_editable": is_order_editable(order),
        }
    else:
        status = str(order.get("status", "unknown"))
        return {
            "id": order.get("id", "N/A"),
            "order_number": order.get("order_number", "N/A"),
            "status": status,
            "status_display": get_status_display_name(status),
            "total_amount": order.get("total_amount", 0),
            "customer_name": order.get("customer_name", "غير معروف"),
            "is_paid": order.get("is_paid", False),
            "is_editable": is_order_editable(order),
        }


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# ==============================================


# دوال التوافق مع الإصدار القديم
# ==============================================
# CHECK ORDER EDITABLE COMPAT
# ==============================================


def check_order_editable_compat(
    order: Union[Order, OrderDict],
) -> None:
    """
    دالة متوافقة مع الإصدار القديم (مغلفة).

    Args:
        order: كائن الطلب أو قاموس

    Raises:
        ValueError: إذا كان الطلب في حالة تمنع التعديل
    """
    check_order_editable(order)


# ==============================================
# IS ORDER EDITABLE COMPAT
# ==============================================


def is_order_editable_compat(
    status: str,
) -> bool:
    """
    دالة متوافقة مع الإصدار القديم (مغلفة).

    Args:
        status: حالة الطلب

    Returns:
        bool: True إذا كان قابلاً للتعديل
    """
    return is_order_editable(status)
