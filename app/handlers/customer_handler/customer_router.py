# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HANDLERS / CUSTOMER_HANDLER / CUSTOMER ROUTER
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for customer router.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.logger import logger
from app.states.customer_states import CustomerStates

# ==============================================
# 📥 استيراد معالجات الحالات
# ==============================================

from app.handlers.customer_handler.restaurant_step import handle_restaurant_step
from app.handlers.customer_handler.product_step import handle_product_step
from app.handlers.customer_handler.cart_step import handle_cart_step
from app.handlers.customer_handler.checkout_step import handle_checkout_step
from app.handlers.customer_handler.payment_step import handle_payment_step

# ==============================================
# 🗺️ MAP: الحالة ← المعالج
# ==============================================

STATE_HANDLERS = {
    CustomerStates.RESTAURANT: handle_restaurant_step,
    CustomerStates.PRODUCT: handle_product_step,
    CustomerStates.CART: handle_cart_step,
    CustomerStates.CHECKOUT: handle_checkout_step,
    CustomerStates.PAYMENT: handle_payment_step,
}

# ==============================================
# 🚀 HANDLE CUSTOMER STATE
# ==============================================


async def handle_customer_state(
    *,
    chat_id: int,
    text: str,
    state: dict,
) -> None:
    """
    توجيه رسالة الزبون إلى المعالج المناسب حسب الحالة

    Args:
        chat_id: معرف المستخدم
        text: النص المرسل
        state: حالة المستخدم الحالية
    """
    step = state.get("step")

    if not step:
        logger.warning(
            "customer_state_missing_step",
            extra={
                "chat_id": chat_id,
            },
        )
        return

    # الحصول على المعالج المناسب
    handler = STATE_HANDLERS.get(step)

    if not handler:
        logger.warning(
            "customer_state_handler_not_found",
            extra={
                "chat_id": chat_id,
                "step": step,
            },
        )
        return

    logger.info(
        "handling_customer_state",
        extra={
            "chat_id": chat_id,
            "step": step,
            "text_length": len(text),
        },
    )

    # استدعاء المعالج
    await handler(
        chat_id=chat_id,
        text=text,
        state=state,
    )
