# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / VIEWS / ORDER HISTORY UI
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for order history ui.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.logger import logger
from app.views.ui import button

# ==============================================
# 📜 ORDER HISTORY UI
# ==============================================


async def order_history_ui(
    *,
    orders: list[dict],
    page: int = 0,
    page_size: int = 5,
) -> dict:
    """
    بناء واجهة عرض تاريخ الطلبات

    Args:
        orders: قائمة الطلبات
        page: رقم الصفحة الحالية
        page_size: عدد العناصر في الصفحة

    Returns:
        dict: كائن InlineKeyboardMarkup جاهز للإرسال إلى Telegram
    """
    logger.info(
        "display_order_history_ui",
        extra={
            "total_orders": len(orders),
            "page": page,
        },
    )

    # ==========================================
    # 📊 حساب الصفحات
    # ==========================================

    total_orders = len(orders)
    total_pages = (total_orders + page_size - 1) // page_size

    start = page * page_size
    end = min(start + page_size, total_orders)

    page_orders = orders[start:end]

    # ==========================================
    # 📝 بناء الرسالة
    # ==========================================

    if not page_orders:
        text = "📜 لا توجد طلبات سابقة."
    else:
        text = "📜 **تاريخ الطلبات:**\n\n"

        for order in page_orders:
            order_number = order.get("order_number", "N/A")
            status = order.get("status", "unknown")
            total = order.get("total_amount", 0)
            created_at = order.get("created_at", "")

            status_emoji = {
                "received": "📥",
                "preparing": "👨‍🍳",
                "ready": "✅",
                "delivering": "🛵",
                "completed": "📦",
                "cancelled": "❌",
            }.get(status, "❓")

            text += (
                f"• **#{order_number}** {status_emoji} {status}\n"
                f"  💰 {total:.2f} دج | 📅 {created_at[:10]}\n\n"
            )

    # ==========================================
    # 🔘 الأزرار
    # ==========================================

    buttons = []

    # أزرار التنقل بين الصفحات
    nav_buttons = []

    if page > 0:
        nav_buttons.append(
            await button(
                text="⬅️ السابق",
                callback=f"history_page_{page - 1}",
            ),
        )

    if page < total_pages - 1:
        nav_buttons.append(
            await button(
                text="التالي ➡️",
                callback=f"history_page_{page + 1}",
            ),
        )

    if nav_buttons:
        buttons.append(nav_buttons)

    # 🔙 رجوع إلى القائمة الرئيسية
    buttons.append(
        [
            await button(
                text="🔙 رجوع",
                callback="back_main",
            ),
        ],
    )

    return {
        "inline_keyboard": buttons,
        "text": text,
    }
