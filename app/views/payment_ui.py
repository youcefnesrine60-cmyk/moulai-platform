# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / VIEWS / PAYMENT UI
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for payment ui.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.logger import logger
from app.views.ui import button

# ==============================================
# 💳 PAYMENT UI
# عرض طرق الدفع المتاحة حسب إعدادات المطعم
# ==============================================


# ==============================================
# PAYMENT UI
# ==============================================


async def payment_ui(
    *,
    allowed_methods: set[str],
    order_id: int,
) -> dict:
    """
    بناء واجهة طرق الدفع المتاحة للزبون

    Args:
        allowed_methods: مجموعة طرق الدفع المسموح بها (من إعدادات المطعم)
        order_id: معرف الطلب

    Returns:
        dict: كائن InlineKeyboardMarkup جاهز للإرسال إلى Telegram
    """
    logger.info(
        "display_payment_ui",
        extra={
            "order_id": order_id,
            "allowed_methods": list(allowed_methods),
        },
    )

    buttons = []

    # ==========================================
    # 💵 طرق الدفع المسموح بها
    # ==========================================

    # 🏦 الدفع نقداً (الافتراضي)
    if "cash" in allowed_methods:
        buttons.append(
            [
                await button(
                    text="💰 دفع نقداً",
                    callback=f"payment_cash_{order_id}",
                ),
            ],
        )

    # 💳 الدفع ببطاقة POS (الافتراضي)
    if "card" in allowed_methods:
        buttons.append(
            [
                await button(
                    text="💳 دفع ببطاقة POS",
                    callback=f"payment_card_{order_id}",
                ),
            ],
        )

    # 📱 الدفع عبر CCP (إذا فعّله المطعم)
    if "ccp" in allowed_methods:
        buttons.append(
            [
                await button(
                    text="📱 دفع عبر CCP",
                    callback=f"payment_ccp_{order_id}",
                ),
            ],
        )

    # 📱 الدفع عبر بريدي موب (إذا فعّله المطعم)
    if "baridimob" in allowed_methods:
        buttons.append(
            [
                await button(
                    text="📱 دفع عبر بريدي موب",
                    callback=f"payment_baridimob_{order_id}",
                ),
            ],
        )

    # 🌐 الدفع عبر Stripe (إذا فعّله المطعم)
    if "stripe" in allowed_methods:
        buttons.append(
            [
                await button(
                    text="🌐 دفع عبر Stripe",
                    callback=f"payment_stripe_{order_id}",
                ),
            ],
        )

    # 🌐 الدفع عبر PayPal (إذا فعّله المطعم)
    if "paypal" in allowed_methods:
        buttons.append(
            [
                await button(
                    text="🌐 دفع عبر PayPal",
                    callback=f"payment_paypal_{order_id}",
                ),
            ],
        )

    # ==========================================
    # 🔙 رجوع
    # ==========================================

    buttons.append(
        [
            await button(
                text="🔙 رجوع",
                callback=f"back_to_cart_{order_id}",
            ),
        ],
    )

    return {
        "inline_keyboard": buttons,
    }


# ==============================================
# 💳 PAYMENT CONFIRMATION UI
# تأكيد عملية الدفع
# ==============================================


# ==============================================
# PAYMENT CONFIRMATION UI
# ==============================================


async def payment_confirmation_ui(
    *,
    order_id: int,
    payment_method: str,
    amount: float,
) -> dict:
    """
    بناء واجهة تأكيد الدفع

    Args:
        order_id: معرف الطلب
        payment_method: طريقة الدفع المختارة
        amount: المبلغ المطلوب

    Returns:
        dict: كائن InlineKeyboardMarkup جاهز للإرسال إلى Telegram
    """
    logger.info(
        "display_payment_confirmation_ui",
        extra={
            "order_id": order_id,
            "payment_method": payment_method,
            "amount": amount,
        },
    )

    return {
        "inline_keyboard": [
            [
                await button(
                    text=f"💳 تأكيد الدفع ({payment_method})",
                    callback=f"payment_confirm_{order_id}",
                ),
            ],
            [
                await button(
                    text="🔙 رجوع",
                    callback=f"back_to_payment_{order_id}",
                ),
            ],
        ],
    }


# ==============================================
# ✅ PAYMENT SUCCESS UI
# تم الدفع بنجاح
# ==============================================


# ==============================================
# PAYMENT SUCCESS UI
# ==============================================


async def payment_success_ui(
    *,
    order_id: int,
    payment_method: str,
    amount: float,
) -> dict:
    """
    بناء واجهة إتمام الدفع بنجاح

    Args:
        order_id: معرف الطلب
        payment_method: طريقة الدفع
        amount: المبلغ المدفوع

    Returns:
        dict: كائن InlineKeyboardMarkup جاهز للإرسال إلى Telegram
    """
    logger.info(
        "display_payment_success_ui",
        extra={
            "order_id": order_id,
            "payment_method": payment_method,
            "amount": amount,
        },
    )

    return {
        "inline_keyboard": [
            [
                await button(
                    text="✅ تم الدفع بنجاح",
                    callback="noop",
                ),
            ],
            [
                await button(
                    text="📦 تتبع الطلب",
                    callback=f"track_order_{order_id}",
                ),
            ],
            [
                await button(
                    text="🏠 القائمة الرئيسية",
                    callback="back_main",
                ),
            ],
        ],
    }


# ==============================================
# ❌ PAYMENT FAILED UI
# فشل الدفع
# ==============================================


# ==============================================
# PAYMENT FAILED UI
# ==============================================


async def payment_failed_ui(
    *,
    order_id: int,
    reason: str,
) -> dict:
    """
    بناء واجهة فشل الدفع

    Args:
        order_id: معرف الطلب
        reason: سبب الفشل

    Returns:
        dict: كائن InlineKeyboardMarkup جاهز للإرسال إلى Telegram
    """
    logger.warning(
        "display_payment_failed_ui",
        extra={
            "order_id": order_id,
            "reason": reason,
        },
    )

    return {
        "inline_keyboard": [
            [
                await button(
                    text="❌ فشل الدفع",
                    callback="noop",
                ),
            ],
            [
                await button(
                    text="🔄 إعادة المحاولة",
                    callback=f"retry_payment_{order_id}",
                ),
            ],
            [
                await button(
                    text="🔙 رجوع",
                    callback=f"back_to_cart_{order_id}",
                ),
            ],
        ],
    }
