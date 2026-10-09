# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HANDLERS / CUSTOMER_HANDLER / PAYMENT STEP
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for payment step.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.logger import logger
from app.helpers.ui_manager import UIManager
from app.views.payment_ui import payment_confirmation_ui

# ==============================================
# 💳 HANDLE PAYMENT STEP
# ==============================================


async def handle_payment_step(
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
        "handle_payment_step",
        extra={
            "chat_id": chat_id,
            "text_length": len(text),
        },
    )

    # التحقق من وجود طريقة دفع مختارة
    payment_method = state.get("payment_method")

    if not payment_method:
        logger.warning(
            "payment_step_no_method_selected",
            extra={
                "chat_id": chat_id,
            },
        )

        await UIManager.update(
            chat_id=chat_id,
            text="❌ يرجى اختيار طريقة الدفع أولاً.",
            reply_markup=None,
        )
        return

    # حساب المجموع الكلي
    cart = state.get("cart", [])
    total = sum(float(item.get("price", 0)) for item in cart)

    # عرض واجهة تأكيد الدفع
    await UIManager.update(
        chat_id=chat_id,
        text=(
            f"💳 تأكيد الدفع\n\n"
            f"طريقة الدفع: {payment_method}\n"
            f"المبلغ: {total:.2f} دج\n\n"
            f"هل أنت متأكد من إتمام عملية الدفع؟"
        ),
        reply_markup=await payment_confirmation_ui(
            order_id=state.get("order_id", 0),
            payment_method=payment_method,
            amount=total,
        ),
    )
