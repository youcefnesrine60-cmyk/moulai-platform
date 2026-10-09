# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / VIEWS / ORDER STATUS UI
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for order status ui.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.logger import logger
from app.views.ui import button

# ==============================================
# 📊 STATUS STEPS
# ==============================================

STATUS_STEPS = {
    "received": "📥 تم استلام الطلب",
    "preparing": "👨‍🍳 جاري التحضير",
    "ready": "✅ جاهز للتسليم",
    "delivering": "🛵 خرج مع المندوب",
    "completed": "📦 تم التسليم",
    "cancelled": "❌ تم الإلغاء",
}

STATUS_ORDER = [
    "received",
    "preparing",
    "ready",
    "delivering",
    "completed",
]

# ==============================================
# 📊 BUILD STATUS BAR
# ==============================================


def build_status_bar(
    *,
    current_status: str,
) -> str:
    """
    بناء شريط حالة متقدم

    Args:
        current_status: الحالة الحالية للطلب

    Returns:
        str: شريط الحالة كنص
    """
    # العثور على مؤشر الحالة الحالية
    try:
        current_index = STATUS_ORDER.index(current_status)
    except ValueError:
        current_index = -1

    bar = ""

    for i, status in enumerate(STATUS_ORDER):
        emoji = "✅" if i <= current_index else "⬜"
        label = STATUS_STEPS.get(status, status)

        if i == current_index:
            bar += f"➡️ **{emoji} {label}**\n"
        else:
            bar += f"   {emoji} {label}\n"

    return bar


# ==============================================
# 📦 ORDER STATUS UI
# ==============================================


async def order_status_ui(
    *,
    order_id: int,
    status: str,
    order_number: str,
    created_at: str,
    updated_at: str,
) -> dict:
    """
    بناء واجهة عرض حالة الطلب

    Args:
        order_id: معرف الطلب
        status: الحالة الحالية
        order_number: رقم الطلب
        created_at: تاريخ الإنشاء
        updated_at: آخر تحديث

    Returns:
        dict: كائن InlineKeyboardMarkup جاهز للإرسال إلى Telegram
    """
    logger.info(
        "display_order_status_ui",
        extra={
            "order_id": order_id,
            "status": status,
        },
    )

    # بناء شريط الحالة
    status_bar = build_status_bar(
        current_status=status,
    )

    # ==========================================
    # 📝 بناء الرسالة
    # ==========================================

    text = (
        f"📦 **الطلب #{order_number}**\n\n"
        f"📅 تاريخ الطلب: {created_at}\n"
        f"🔄 آخر تحديث: {updated_at}\n\n"
        f"📊 **حالة الطلب:**\n\n"
        f"{status_bar}\n"
    )

    # إضافة ملاحظة إذا كان الطلب مكتملاً
    if status == "completed":
        text += "\n✅ تم تسليم طلبك بنجاح. شكراً لاستخدامك خدمتنا!"
    elif status == "cancelled":
        text += "\n❌ تم إلغاء الطلب. يمكنك التواصل مع المطعم للمزيد من المعلومات."

    # ==========================================
    # 🔘 الأزرار
    # ==========================================

    buttons = []

    # 📞 الاتصال بالمطعم (إذا كان الطلب قيد التنفيذ)
    if status not in ["completed", "cancelled"]:
        buttons.append(
            [
                await button(
                    text="📞 التواصل مع المطعم",
                    callback=f"contact_restaurant_{order_id}",
                ),
            ],
        )

    # 🔄 تحديث الحالة (زر تحديث)
    buttons.append(
        [
            await button(
                text="🔄 تحديث الحالة",
                callback=f"refresh_status_{order_id}",
            ),
        ],
    )

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


# ==============================================
# 📦 ORDER STATUS SIMPLE UI
# عرض بسيط للحالة (للإشعارات)
# ==============================================


# ==============================================
# ORDER STATUS SIMPLE UI
# ==============================================


async def order_status_simple_ui(
    *,
    order_number: str,
    status: str,
) -> str:
    """
    بناء رسالة حالة بسيطة (للإشعارات)

    Args:
        order_number: رقم الطلب
        status: الحالة الحالية

    Returns:
        str: نص الحالة
    """
    status_text = STATUS_STEPS.get(
        status,
        status,
    )

    return f"📦 **الطلب #{order_number}**\n" f"📊 الحالة: {status_text}"
