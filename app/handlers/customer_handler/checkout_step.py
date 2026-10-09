# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HANDLERS / CUSTOMER_HANDLER / CHECKOUT STEP
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for checkout step.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.logger import logger
from app.helpers.ui_manager import UIManager
from app.views.payment_ui import payment_ui

from app.services.business.order_payments_service import (
    get_allowed_payment_methods_for_order,
)

# ==============================================
# 💳 HANDLE CHECKOUT STEP
# ==============================================


async def handle_checkout_step(
    *,
    chat_id: int,
    text: str,
    state: dict,
) -> None:
    """
    معالجة رسائل المستخدم في مرحلة الدفع

    Args:
        chat_id: معرف المستخدم
        text: النص المرسل
        state: حالة المستخدم الحالية
    """
    logger.info(
        "handle_checkout_step",
        extra={
            "chat_id": chat_id,
            "text_length": len(text),
        },
    )

    # التحقق من وجود سلة غير فارغة
    cart = state.get("cart", [])

    if not cart:
        logger.warning(
            "checkout_empty_cart",
            extra={
                "chat_id": chat_id,
            },
        )

        await UIManager.update(
            chat_id=chat_id,
            text="🛒 السلة فارغة. أضف منتجات أولاً.",
            reply_markup=None,
        )
        return

    # حساب المجموع الكلي
    total = sum(float(item.get("price", 0)) for item in cart)

    # الحصول على معرف المطعم
    restaurant_id = state.get("restaurant_id")

    if not restaurant_id:
        logger.warning(
            "checkout_restaurant_id_missing",
            extra={
                "chat_id": chat_id,
            },
        )

        await UIManager.update(
            chat_id=chat_id,
            text="❌ حدث خطأ. يرجى المحاولة مرة أخرى.",
            reply_markup=None,
        )
        return

    # جلب طرق الدفع المسموح بها للمطعم
    # ملاحظة: نحتاج إلى order_id، لكن قد لا يكون موجوداً بعد
    # لذلك نستخدم 0 مؤقتاً، وسيتم تحديثه عند إنشاء الطلب
    allowed_methods = await get_allowed_payment_methods_for_order(
        order_id=state.get("order_id", 0),
    )

    # إذا لم توجد طرق دفع مسموح بها، نستخدم الافتراضية
    if not allowed_methods:
        allowed_methods = {"cash", "card"}

    logger.info(
        "checkout_allowed_methods",
        extra={
            "chat_id": chat_id,
            "allowed_methods": list(allowed_methods),
        },
    )

    await UIManager.update(
        chat_id=chat_id,
        text=(
            f"💳 الدفع\n\n" f"المجموع الكلي: {total:.2f} دج\n\n" f"اختر طريقة الدفع:"
        ),
        reply_markup=await payment_ui(
            allowed_methods=allowed_methods,
            order_id=state.get("order_id", 0),
        ),
    )
