# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / VIEWS / PROFILE UI
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for profile ui.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.logger import logger
from app.views.ui import button

# ==============================================
# 👤 PROFILE UI
# ==============================================


async def profile_ui(
    *,
    user_data: dict,
    role: str = "customer",
) -> dict:
    """
    بناء واجهة عرض الملف الشخصي

    Args:
        user_data: بيانات المستخدم
        role: دور المستخدم (customer, owner, admin)

    Returns:
        dict: كائن InlineKeyboardMarkup جاهز للإرسال إلى Telegram
    """
    logger.info(
        "display_profile_ui",
        extra={
            "chat_id": user_data.get("chat_id"),
            "role": role,
        },
    )

    # ==========================================
    # 📝 بناء الرسالة
    # ==========================================

    full_name = user_data.get("full_name", "غير محدد")
    phone = user_data.get("phone", "غير محدد")
    email = user_data.get("email", "غير محدد")

    text = (
        f"👤 **الملف الشخصي**\n\n"
        f"📛 الاسم: {full_name}\n"
        f"📞 الهاتف: {phone}\n"
        f"📧 البريد الإلكتروني: {email}\n"
        f"🔑 الدور: {role}\n"
    )

    # إضافة معلومات إضافية للمالك
    if role == "owner":
        restaurant_name = user_data.get("restaurant_name", "غير محدد")
        wilaya = user_data.get("wilaya", "غير محدد")
        subscription_status = user_data.get("subscription_status", "غير نشط")

        text += (
            f"\n🏪 **معلومات المطعم:**\n"
            f"🏪 اسم المطعم: {restaurant_name}\n"
            f"📍 الولاية: {wilaya}\n"
            f"💳 حالة الاشتراك: {subscription_status}\n"
        )

    # ==========================================
    # 🔘 الأزرار
    # ==========================================

    buttons = []

    # ✏️ تعديل البيانات
    buttons.append(
        [
            await button(
                text="✏️ تعديل البيانات",
                callback="edit_profile",
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
# ✏️ PROFILE EDIT UI
# ==============================================


async def profile_edit_ui(
    *,
    field: str,
    current_value: str,
) -> dict:
    """
    بناء واجهة تعديل حقل معين في الملف الشخصي

    Args:
        field: اسم الحقل المراد تعديله
        current_value: القيمة الحالية

    Returns:
        dict: كائن InlineKeyboardMarkup جاهز للإرسال إلى Telegram
    """
    logger.info(
        "display_profile_edit_ui",
        extra={
            "field": field,
        },
    )

    field_names = {
        "full_name": "الاسم الكامل",
        "phone": "رقم الهاتف",
        "email": "البريد الإلكتروني",
    }

    field_name = field_names.get(
        field,
        field,
    )

    text = (
        f"✏️ **تعديل {field_name}**\n\n"
        f"📝 القيمة الحالية: {current_value}\n\n"
        f"📤 أرسل القيمة الجديدة في رسالة نصية."
    )

    buttons = [
        [
            await button(
                text="🔙 رجوع",
                callback="back_to_profile",
            ),
        ],
    ]

    return {
        "inline_keyboard": buttons,
        "text": text,
    }
