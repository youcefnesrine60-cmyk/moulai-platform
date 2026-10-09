# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HANDLERS / CALLBACKS / CUSTOMER / ORDER
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for order.

Part of MoulAI Platform - Agent-as-a-Service.
"""

import re

from app.core.logger import logger
from app.core.middleware.rate_limit import rate_limit

from app.helpers.ui_manager import UIManager

from app.services.business.orders import get_restaurant_order

# ==============================================
# 📦 ORDER DETAILS
# عرض تفاصيل الطلب
# ==============================================


# ==============================================
# ORDER DETAILS CALLBACK
# ==============================================


@rate_limit(
    limit=10,
    window=30,
    key_prefix="order_details",
)
async def order_details_callback(
    *,
    chat_id: int,
    message_id: int,
    callback_data: str,
    match: re.Match[str],
) -> None:
    """
    عرض تفاصيل طلب معين
    """
    try:
        order_id = int(match.group(1))
    except (IndexError, ValueError):
        logger.warning(
            "order_details_invalid_order_id",
            extra={
                "chat_id": chat_id,
                "callback_data": callback_data,
            },
        )
        return

    logger.info(
        "order_details_callback",
        extra={
            "chat_id": chat_id,
            "order_id": order_id,
        },
    )

    # جلب بيانات الطلب
    order = await get_restaurant_order(
        order_id=order_id,
    )

    if not order:
        await UIManager.update(
            chat_id=chat_id,
            message_id=message_id,
            text="❌ الطلب غير موجود.",
            reply_markup=None,
        )
        return

    # بناء الرسالة
    text = (
        f"📦 **تفاصيل الطلب #{order.get('order_number', 'N/A')}**\n\n"
        f"📅 التاريخ: {order.get('created_at', 'غير معروف')}\n"
        f"📊 الحالة: {order.get('status', 'غير معروف')}\n"
        f"💰 المجموع: {order.get('total_amount', 0):.2f} دج\n"
    )

    await UIManager.update(
        chat_id=chat_id,
        message_id=message_id,
        text=text,
        reply_markup=None,
    )
