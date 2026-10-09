# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HANDLERS / CALLBACKS / ORDER CALLBACKS
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for order callbacks.

Part of MoulAI Platform - Agent-as-a-Service.
"""

import re

from app.core.logger import logger
from app.core.middleware.rate_limit import rate_limit

from app.helpers.ui_manager import UIManager
from app.services.business.orders import get_restaurant_order

# ==============================================
# ORDER CALLBACK
# ==============================================


@rate_limit(limit=5, window=20, key_prefix="orders")
async def order_callback(
    *, chat_id: int, message_id: int, callback_data: str, match: re.Match[str]
) -> None:
    """
    معالجة أي كولباك متعلق بالطلب (Fallback)

    يتم استدعاء هذه الدالة عندما لا يجد الـ Router
    مساراً مخصصاً للكولباك.
    """
    # ==========================================
    # 🔍 EXTRACT ORDER ID
    # استخراج معرف الطلب من Regex
    # ==========================================

    try:
        order_id = int(match.group(1))

    # ==========================================
    # 🚫 INVALID CALLBACK
    # في حال كانت البيانات غير صحيحة أو لا تحتوي
    # على مجموعة Regex مطابقة.
    # ==========================================

    except (ValueError, IndexError):
        logger.warning(
            "invalid_order_callback",
            extra={"chat_id": chat_id, "callback_data": callback_data},
        )
        return

    # ==========================================
    # ✅ ORDER SELECTED
    # تم اختيار الطلب بنجاح
    # ==========================================

    logger.info("order_selected", extra={"chat_id": chat_id, "order_id": order_id})

    # ==========================================
    # 📋 جلب بيانات الطلب
    # ==========================================

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

    # ==========================================
    # 📝 عرض تفاصيل الطلب
    # ==========================================

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
