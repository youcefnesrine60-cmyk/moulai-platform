# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HANDLERS / CALLBACKS / SHARED / ERRORS
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for errors.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.logger import logger

# ==============================================
# 📋 رسائل الخطأ الموحدة
# ==============================================

ERROR_MESSAGES = {
    # 🔍 أخطاء عامة
    "not_found": "❌ العنصر غير موجود.",
    "invalid_input": "❌ إدخال غير صحيح.",
    "unauthorized": "⛔ غير مصرح لك بالوصول.",
    "forbidden": "⛔ هذا الإجراء غير مسموح به.",
    "internal_error": "⚠️ حدث خطأ داخلي. يرجى المحاولة مرة أخرى.",
    # 🍔 أخطاء المطاعم
    "restaurant_not_found": "❌ المطعم غير موجود.",
    "restaurant_inactive": "⛔ المطعم غير نشط حالياً.",
    "restaurant_no_products": "⚠️ لا توجد منتجات في هذا المطعم.",
    "restaurant_no_categories": "⚠️ لا توجد أقسام في هذا المطعم.",
    # 📦 أخطاء الطلبات
    "order_not_found": "❌ الطلب غير موجود.",
    "order_cannot_modify": "⛔ لا يمكن تعديل هذا الطلب.",
    "order_cannot_cancel": "⛔ لا يمكن إلغاء هذا الطلب.",
    "order_already_completed": "✅ هذا الطلب مكتمل بالفعل.",
    "order_already_cancelled": "❌ هذا الطلب ملغى بالفعل.",
    # 🛒 أخطاء السلة
    "cart_empty": "🛒 السلة فارغة.",
    "cart_item_not_found": "❌ المنتج غير موجود في السلة.",
    "cart_invalid_quantity": "❌ كمية غير صالحة.",
    # 💳 أخطاء الدفع
    "payment_failed": "❌ فشل الدفع. يرجى المحاولة مرة أخرى.",
    "payment_not_found": "❌ عملية الدفع غير موجودة.",
    "payment_already_paid": "✅ تم الدفع مسبقاً.",
    "payment_method_not_allowed": "❌ طريقة الدفع غير مسموح بها.",
    # 👤 أخطاء المستخدم
    "user_not_found": "❌ المستخدم غير موجود.",
    "user_not_owner": "⛔ هذا المستخدم ليس مالكاً.",
    "user_not_admin": "⛔ هذا المستخدم ليس مسؤولاً.",
}


# ==============================================
# 📋 GET ERROR MESSAGE
# جلب رسالة خطأ
# ==============================================


# ==============================================
# GET ERROR MESSAGE
# ==============================================


async def get_error_message(
    *,
    error_code: str,
    default: str | None = None,
) -> str:
    """
    جلب رسالة خطأ موحدة

    Args:
        error_code: رمز الخطأ
        default: رسالة افتراضية في حال عدم وجود الرمز

    Returns:
        str: رسالة الخطأ
    """
    message = ERROR_MESSAGES.get(
        error_code,
        default or f"❌ خطأ: {error_code}",
    )

    logger.debug(
        "error_message_fetched",
        extra={
            "error_code": error_code,
            "resolved_error_message": message,
        },
    )

    return message


# ==============================================
# 📋 FORMAT ERROR RESPONSE
# تنسيق رد الخطأ
# ==============================================


# ==============================================
# FORMAT ERROR RESPONSE
# ==============================================


async def format_error_response(
    *,
    error_code: str,
    details: str | None = None,
) -> dict:
    """
    تنسيق رد خطأ موحد

    Args:
        error_code: رمز الخطأ
        details: تفاصيل إضافية (اختياري)

    Returns:
        dict: كائن الخطأ
    """
    message = await get_error_message(
        error_code=error_code,
    )

    if details:
        message += f"\n\n📝 {details}"

    return {
        "error": error_code,
        "message": message,
    }
