# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / VIEWS / SUBSCRIPTION UI
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for subscription ui.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.logger import logger
from app.views.ui import button

# ==============================================
# 💳 SUBSCRIPTION UI
# عرض جميع الباقات المتاحة
# ==============================================


# ==============================================
# SUBSCRIPTION UI
# ==============================================


async def subscription_ui(
    *,
    plans: list[dict],
    current_plan_id: int | None = None,
) -> dict:
    """
    بناء واجهة عرض الباقات والأسعار

    Args:
        plans: قائمة الباقات المتاحة
        current_plan_id: معرف الباقة الحالية (إن وجدت)

    Returns:
        dict: كائن InlineKeyboardMarkup جاهز للإرسال إلى Telegram
    """
    logger.info(
        "display_subscription_ui",
        extra={
            "total_plans": len(plans),
            "current_plan_id": current_plan_id,
        },
    )

    # ==========================================
    # 📝 بناء الرسالة
    # ==========================================

    text = "💳 **باقات الاشتراك**\n\n" "اختر الباقة المناسبة لمطعمك:\n\n"

    # ==========================================
    # 🔘 الأزرار
    # ==========================================

    buttons = []

    for plan in plans:
        plan_id = plan.get("id")
        plan_name = plan.get("name", "باقة")
        base_price = plan.get("base_price", 0)
        discount = plan.get("plan_discount_percent", 0)
        description = plan.get("description", "")

        # تحديد ما إذا كانت الباقة هي الحالية
        is_current = plan_id == current_plan_id

        # علامة الباقة الحالية
        current_mark = " ✅ (حالية)" if is_current else ""

        # عرض السعر مع الخصم
        if discount > 0:
            price_text = f"{base_price} دج (خصم {discount}%)"
        else:
            price_text = f"{base_price} دج"

        text += (
            f"**{plan_name}**{current_mark}\n"
            f"💰 {price_text}\n"
            f"📝 {description}\n\n"
        )

        # زر اختيار الباقة (إذا لم تكن حالية)
        if not is_current:
            buttons.append(
                [
                    await button(
                        text=f"اختيار {plan_name}",
                        callback=f"select_plan_{plan_id}",
                    ),
                ],
            )

    # ==========================================
    # 💰 زر حساب السعر
    # ==========================================

    buttons.append(
        [
            await button(
                text="💰 حساب السعر النهائي",
                callback="calculate_price",
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
# 💳 SUBSCRIPTION PLAN DETAILS UI
# عرض تفاصيل باقة معينة
# ==============================================


# ==============================================
# SUBSCRIPTION PLAN DETAILS UI
# ==============================================


async def subscription_plan_details_ui(
    *,
    plan: dict,
    features: list[dict],
) -> dict:
    """
    بناء واجهة عرض تفاصيل باقة معينة

    Args:
        plan: بيانات الباقة
        features: قائمة الميزات المتضمنة

    Returns:
        dict: كائن InlineKeyboardMarkup جاهز للإرسال إلى Telegram
    """
    logger.info(
        "display_subscription_plan_details_ui",
        extra={
            "plan_id": plan.get("id"),
        },
    )

    plan_name = plan.get("name", "باقة")
    base_price = plan.get("base_price", 0)
    discount = plan.get("plan_discount_percent", 0)
    description = plan.get("description", "")

    # بناء قائمة الميزات
    features_text = (
        "\n".join(f"✅ {f.get('feature_name', 'ميزة')}" for f in features)
        if features
        else "⚠️ لا توجد ميزات محددة."
    )

    text = (
        f"💳 **{plan_name}**\n\n"
        f"📝 {description}\n\n"
        f"💰 السعر الأساسي: {base_price} دج\n"
    )

    if discount > 0:
        text += f"🎁 خصم الباقة: {discount}%\n"

    text += f"\n📋 **الميزات المتضمنة:**\n\n{features_text}"

    buttons = [
        [
            await button(
                text="💳 اختيار هذه الباقة",
                callback=f"select_plan_{plan.get('id')}",
            ),
        ],
        [
            await button(
                text="🔙 رجوع إلى الباقات",
                callback="show_plans",
            ),
        ],
    ]

    return {
        "inline_keyboard": buttons,
        "text": text,
    }
