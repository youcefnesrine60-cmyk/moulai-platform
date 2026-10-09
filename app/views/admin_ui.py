# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / VIEWS / ADMIN UI
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for admin ui.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.logger import logger
from app.views.ui import button

# ==============================================
# 🛡️ ADMIN DASHBOARD UI
# ==============================================


async def admin_dashboard_ui(
    *,
    pending_requests: int,
    total_restaurants: int,
    total_owners: int,
    total_orders: int,
    total_admins: int = 1,
) -> dict:
    """
    بناء واجهة لوحة تحكم المسؤول

    Args:
        pending_requests: عدد طلبات التسجيل المعلقة
        total_restaurants: عدد المطاعم الكلي
        total_owners: عدد المالكين الكلي
        total_orders: عدد الطلبات الكلي
        total_admins: عدد المسؤولين

    Returns:
        dict: كائن InlineKeyboardMarkup جاهز للإرسال إلى Telegram
    """
    logger.info(
        "display_admin_dashboard_ui",
        extra={
            "pending_requests": pending_requests,
            "total_restaurants": total_restaurants,
            "total_owners": total_owners,
            "total_orders": total_orders,
        },
    )

    # ==========================================
    # 📝 بناء الرسالة
    # ==========================================

    text = (
        "🛡️ **لوحة تحكم المسؤول**\n\n"
        f"📋 طلبات تسجيل معلقة: **{pending_requests}**\n"
        f"🏪 عدد المطاعم: **{total_restaurants}**\n"
        f"👤 عدد المالكين: **{total_owners}**\n"
        f"📦 عدد الطلبات: **{total_orders}**\n"
        f"👑 عدد المسؤولين: **{total_admins}**\n"
    )

    # ==========================================
    # 🔘 الأزرار
    # ==========================================

    buttons = []

    # 📋 طلبات التسجيل
    if pending_requests > 0:
        buttons.append(
            [
                await button(
                    text=f"📋 طلبات التسجيل ({pending_requests})",
                    callback="admin_requests",
                ),
            ],
        )
    else:
        buttons.append(
            [
                await button(
                    text="✅ لا توجد طلبات معلقة",
                    callback="noop",
                ),
            ],
        )

    # 🏪 إدارة المطاعم
    buttons.append(
        [
            await button(
                text="🏪 إدارة المطاعم",
                callback="admin_restaurants",
            ),
        ],
    )

    # 👤 إدارة المالكين
    buttons.append(
        [
            await button(
                text="👤 إدارة المالكين",
                callback="admin_owners",
            ),
        ],
    )

    # 📦 إدارة الطلبات
    buttons.append(
        [
            await button(
                text="📦 إدارة الطلبات",
                callback="admin_orders",
            ),
        ],
    )

    # 💳 إدارة الباقات
    buttons.append(
        [
            await button(
                text="💳 إدارة الباقات",
                callback="admin_plans",
            ),
        ],
    )

    # 👑 إدارة المسؤولين
    buttons.append(
        [
            await button(
                text="👑 إدارة المسؤولين",
                callback="admin_admins",
            ),
        ],
    )

    # 📊 الإحصائيات
    buttons.append(
        [
            await button(
                text="📊 الإحصائيات",
                callback="admin_stats",
            ),
        ],
    )

    # 🔙 رجوع
    buttons.append(
        [
            await button(
                text="🔙 رجوع إلى القائمة الرئيسية",
                callback="back_main",
            ),
        ],
    )

    return {
        "inline_keyboard": buttons,
        "text": text,
    }


# ==============================================
# 📋 ADMIN REQUESTS UI
# عرض طلبات التسجيل المعلقة
# ==============================================


# ==============================================
# ADMIN REQUESTS UI
# ==============================================


async def admin_requests_ui(
    *,
    requests: list[dict],
) -> dict:
    """
    بناء واجهة عرض طلبات التسجيل المعلقة

    Args:
        requests: قائمة طلبات التسجيل

    Returns:
        dict: كائن InlineKeyboardMarkup جاهز للإرسال إلى Telegram
    """
    logger.info(
        "display_admin_requests_ui",
        extra={
            "total_requests": len(requests),
        },
    )

    # ==========================================
    # 📝 بناء الرسالة
    # ==========================================

    if not requests:
        text = "📋 لا توجد طلبات تسجيل معلقة."
    else:
        text = "📋 **طلبات التسجيل المعلقة:**\n\n"

        for req in requests:
            request_id = req.get("id")
            full_name = req.get("full_name", "غير محدد")
            restaurant_name = req.get("restaurant_name", "غير محدد")
            wilaya = req.get("wilaya", "غير محدد")

            text += (
                f"**#{request_id}** - {full_name}\n"
                f"🏪 {restaurant_name} | 📍 {wilaya}\n\n"
            )

    # ==========================================
    # 🔘 الأزرار
    # ==========================================

    buttons = []

    for req in requests:
        request_id = req.get("id")

        buttons.append(
            [
                await button(
                    text=f"📋 طلب #{request_id}",
                    callback=f"admin_request_{request_id}",
                ),
            ],
        )

    buttons.append(
        [
            await button(
                text="🔙 رجوع إلى لوحة التحكم",
                callback="admin_dashboard",
            ),
        ],
    )

    return {
        "inline_keyboard": buttons,
        "text": text,
    }


# ==============================================
# 📋 ADMIN REQUEST DETAILS UI
# عرض تفاصيل طلب تسجيل معين
# ==============================================


# ==============================================
# ADMIN REQUEST DETAILS UI
# ==============================================


async def admin_request_details_ui(
    *,
    request: dict,
) -> dict:
    """
    بناء واجهة عرض تفاصيل طلب تسجيل

    Args:
        request: بيانات طلب التسجيل

    Returns:
        dict: كائن InlineKeyboardMarkup جاهز للإرسال إلى Telegram
    """
    logger.info(
        "display_admin_request_details_ui",
        extra={
            "request_id": request.get("id"),
        },
    )

    # ==========================================
    # 📝 بناء الرسالة
    # ==========================================

    request_id = request.get("id")
    full_name = request.get("full_name", "غير محدد")
    owner_phone = request.get("owner_phone", "غير محدد")
    email = request.get("email", "غير محدد")
    restaurant_name = request.get("restaurant_name", "غير محدد")
    restaurant_type = request.get("restaurant_type", "غير محدد")
    restaurant_phone = request.get("restaurant_phone", "غير محدد")
    wilaya = request.get("wilaya", "غير محدد")

    text = (
        f"📋 **طلب تسجيل #{request_id}**\n\n"
        f"👤 **المالك:**\n"
        f"📛 الاسم: {full_name}\n"
        f"📞 الهاتف: {owner_phone}\n"
        f"📧 البريد: {email}\n\n"
        f"🏪 **المطعم:**\n"
        f"📛 الاسم: {restaurant_name}\n"
        f"🍽️ النوع: {restaurant_type}\n"
        f"📞 الهاتف: {restaurant_phone}\n"
        f"📍 الولاية: {wilaya}\n"
    )

    # ==========================================
    # 🔘 الأزرار
    # ==========================================

    buttons = [
        [
            await button(
                text="✅ موافقة",
                callback=f"admin_approve_{request_id}",
            ),
            await button(
                text="❌ رفض",
                callback=f"admin_reject_{request_id}",
            ),
        ],
        [
            await button(
                text="🔙 رجوع إلى الطلبات",
                callback="admin_requests",
            ),
        ],
    ]

    return {
        "inline_keyboard": buttons,
        "text": text,
    }
