# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HANDLERS / CUSTOMER_HANDLER / ORDER STATUS STEP
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for order status step.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.logger import logger

from app.helpers.ui_manager import UIManager

from app.services.business.orders import (
    get_restaurant_order,
)

from app.views.order_status_ui import order_status_ui

# ==============================================
# 📦 SHOW ORDER STATUS
# عرض حالة الطلب
# ==============================================


# ==============================================
# SHOW ORDER STATUS
# ==============================================


async def show_order_status(
    *,
    chat_id: int,
    order_id: int,
) -> None:
    """
    عرض حالة طلب معين

    Args:
        chat_id: معرف المستخدم
        order_id: معرف الطلب
    """
    logger.info(
        "show_order_status",
        extra={
            "chat_id": chat_id,
            "order_id": order_id,
        },
    )

    # ==========================================
    # 1️⃣ جلب بيانات الطلب
    # ==========================================

    order = await get_restaurant_order(
        order_id=order_id,
    )

    if not order:
        logger.warning(
            "order_not_found",
            extra={
                "chat_id": chat_id,
                "order_id": order_id,
            },
        )

        await UIManager.update(
            chat_id=chat_id,
            text="❌ الطلب غير موجود.",
            reply_markup=None,
        )
        return

    # ==========================================
    # 2️⃣ عرض واجهة الحالة
    # ==========================================

    status_ui = await order_status_ui(
        order_id=order_id,
        status=order.get("status", "received"),
        order_number=order.get("order_number", "N/A"),
        created_at=str(order.get("created_at", "")),
        updated_at=str(order.get("updated_at", "")),
    )

    await UIManager.update(
        chat_id=chat_id,
        text=status_ui.get("text", "📦 حالة الطلب"),
        reply_markup=status_ui.get("inline_keyboard"),
    )
