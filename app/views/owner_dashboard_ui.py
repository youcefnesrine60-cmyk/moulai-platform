# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / VIEWS / OWNER DASHBOARD UI
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for owner dashboard ui.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.logger import logger
from app.views.ui import button

# ==============================================
# 🏪 OWNER DASHBOARD UI
# ==============================================


async def owner_dashboard_ui(
    *,
    restaurant_id: int,
    restaurant_name: str,
    orders_count: int,
    pending_orders: int,
    products_count: int,
    revenue: float,
) -> dict:
    """
    بناء واجهة لوحة تحكم صاحب المحل

    Args:
        restaurant_id: معرف المطعم
        restaurant_name: اسم المطعم
        orders_count: عدد الطلبات الكلي
        pending_orders: عدد الطلبات المعلقة
        products_count: عدد المنتجات
        revenue: الإيرادات الكلية

    Returns:
        dict: كائن InlineKeyboardMarkup جاهز للإرسال إلى Telegram
    """
    logger.info(
        "display_owner_dashboard_ui",
        extra={
            "restaurant_id": restaurant_id,
            "orders_count": orders_count,
        },
    )

    text = (
        f"🏪 **لوحة تحكم {restaurant_name}**\n\n"
        f"📊 **الإحصائيات:**\n"
        f"📦 عدد الطلبات: **{orders_count}**\n"
        f"⏳ طلبات معلقة: **{pending_orders}**\n"
        f"🍔 عدد المنتجات: **{products_count}**\n"
        f"💰 الإيرادات: **{revenue:.2f} دج**\n\n"
        f"📌 **إجراءات سريعة:**"
    )

    buttons = [
        [
            await button(
                text="📦 إدارة الطلبات",
                callback=f"owner_orders_{restaurant_id}",
            ),
        ],
        [
            await button(
                text="🍔 إدارة المنتجات",
                callback=f"owner_products_{restaurant_id}",
            ),
        ],
        [
            await button(
                text="📂 إدارة الأقسام",
                callback=f"owner_categories_{restaurant_id}",
            ),
        ],
        [
            await button(
                text="💳 الاشتراك والباقات",
                callback=f"owner_subscription_{restaurant_id}",
            ),
        ],
        [
            await button(
                text="📊 الإحصائيات المتقدمة",
                callback=f"owner_stats_{restaurant_id}",
            ),
        ],
        [
            await button(
                text="🔙 رجوع إلى القائمة الرئيسية",
                callback="back_main",
            ),
        ],
    ]

    return {
        "inline_keyboard": buttons,
        "text": text,
    }
