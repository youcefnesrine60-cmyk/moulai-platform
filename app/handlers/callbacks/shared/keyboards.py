# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HANDLERS / CALLBACKS / SHARED / KEYBOARDS
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for keyboards.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.logger import logger
from app.views.ui import button

# ==============================================
# ⌨️ CONFIRM KEYBOARD
# أزرار التأكيد
# ==============================================


# ==============================================
# CONFIRM KEYBOARD
# ==============================================


async def confirm_keyboard(
    *,
    confirm_callback: str,
    cancel_callback: str = "back_main",
) -> dict:
    """
    بناء أزرار تأكيد/إلغاء

    Args:
        confirm_callback: الكولباك عند الضغط على تأكيد
        cancel_callback: الكولباك عند الضغط على إلغاء

    Returns:
        dict: كائن InlineKeyboardMarkup
    """
    logger.debug(
        "confirm_keyboard_built",
        extra={
            "confirm_callback": confirm_callback,
            "cancel_callback": cancel_callback,
        },
    )

    return {
        "inline_keyboard": [
            [
                await button(
                    text="✅ تأكيد",
                    callback=confirm_callback,
                ),
                await button(
                    text="❌ إلغاء",
                    callback=cancel_callback,
                ),
            ],
        ],
    }


# ==============================================
# ⌨️ NAVIGATION KEYBOARD
# أزرار التنقل
# ==============================================


# ==============================================
# NAVIGATION KEYBOARD
# ==============================================


async def navigation_keyboard(
    *,
    back_callback: str = "back_main",
    home_callback: str = "back_main",
) -> dict:
    """
    بناء أزرار تنقل (رجوع، رئيسية)

    Args:
        back_callback: الكولباك عند الضغط على رجوع
        home_callback: الكولباك عند الضغط على رئيسية

    Returns:
        dict: كائن InlineKeyboardMarkup
    """
    return {
        "inline_keyboard": [
            [
                await button(
                    text="🔙 رجوع",
                    callback=back_callback,
                ),
                await button(
                    text="🏠 رئيسية",
                    callback=home_callback,
                ),
            ],
        ],
    }


# ==============================================
# ⌨️ PAGINATION KEYBOARD
# أزرار التنقل بين الصفحات
# ==============================================


# ==============================================
# PAGINATION KEYBOARD
# ==============================================


async def pagination_keyboard(
    *,
    page: int,
    total_pages: int,
    base_callback: str,
) -> dict:
    """
    بناء أزرار التنقل بين الصفحات

    Args:
        page: رقم الصفحة الحالية (تبدأ من 0)
        total_pages: إجمالي عدد الصفحات
        base_callback: أساس الكولباك (سيُضاف إليه رقم الصفحة)

    Returns:
        dict: كائن InlineKeyboardMarkup
    """
    buttons = []
    nav_buttons = []

    if page > 0:
        nav_buttons.append(
            await button(
                text="⬅️ السابق",
                callback=f"{base_callback}_{page - 1}",
            ),
        )

    if page < total_pages - 1:
        nav_buttons.append(
            await button(
                text="التالي ➡️",
                callback=f"{base_callback}_{page + 1}",
            ),
        )

    if nav_buttons:
        buttons.append(nav_buttons)

    # زر الرجوع
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
    }


# ==============================================
# ⌨️ ACTION KEYBOARD
# أزرار إجراءات
# ==============================================


# ==============================================
# ACTION KEYBOARD
# ==============================================


async def action_keyboard(
    *,
    actions: list[tuple[str, str]],
) -> dict:
    """
    بناء أزرار إجراءات مخصصة

    Args:
        actions: قائمة من (النص, الكولباك)

    Returns:
        dict: كائن InlineKeyboardMarkup
    """
    buttons = []

    for text, callback in actions:
        buttons.append(
            [
                await button(
                    text=text,
                    callback=callback,
                ),
            ],
        )

    # زر الرجوع
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
    }
