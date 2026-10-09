# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / VIEWS / CART UI
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for cart ui.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.views.ui import button
from app.core.logger import logger

# ==============================================
# 🛒 CART UI
# عرض سلة التسوق مع جميع عناصرها
# ==============================================


# ==============================================
# CART UI
# ==============================================


async def cart_ui(
    *,
    items: list[dict],
    total: float,
) -> dict:
    """
    بناء واجهة سلة التسوق الرئيسية

    Args:
        items: قائمة عناصر السلة، كل عنصر يحتوي على:
               - id: معرف المنتج
               - name: اسم المنتج
               - quantity: الكمية
               - price: السعر الإجمالي للعنصر
        total: المجموع الكلي للسلة

    Returns:
        dict: كائن InlineKeyboardMarkup جاهز للإرسال إلى Telegram
    """
    logger.info(
        "display_cart_ui",
        extra={
            "item_count": len(items),
            "total": total,
        },
    )

    # ==========================================
    # 🚫 السلة فارغة
    # ==========================================

    if not items:

        logger.warning(
            "cart_is_empty",
        )

        return await cart_empty_ui()

    # ==========================================
    # 🛒 بناء أزرار المنتجات
    # ==========================================

    buttons = []

    for item in items:

        item_id = item.get(
            "id",
            0,
        )

        name = item.get(
            "name",
            "منتج",
        )

        quantity = item.get(
            "quantity",
            1,
        )

        price = item.get(
            "price",
            0,
        )

        logger.debug(
            "cart_item_processed",
            extra={
                "item_id": item_id,
                "quantity": quantity,
                "price": price,
            },
        )

        buttons.append(
            [
                await button(
                    text=f"🍽️ {name} x{quantity} = {price} دج",
                    callback=f"cart_item_{item_id}",
                ),
            ],
        )

    # ==========================================
    # 🧹 أزرار التحكم
    # ==========================================

    buttons.append(
        [
            await button(
                text="🗑️ إفراغ السلة",
                callback="cart_clear",
            ),
        ],
    )

    buttons.append(
        [
            await button(
                text="💳 الدفع",
                callback="checkout",
            ),
        ],
    )

    buttons.append(
        [
            await button(
                text="🔙 رجوع",
                callback="back_main",
            ),
        ],
    )

    # ==========================================
    # 📦 إرجاع الكائن النهائي
    # ==========================================

    return {
        "inline_keyboard": buttons,
    }


# ==============================================
# 🛒 CART ITEM UI
# عرض تفاصيل منتج معين في السلة
# ==============================================


# ==============================================
# CART ITEM UI
# ==============================================


async def cart_item_ui(
    *,
    item: dict,
) -> dict:
    """
    بناء واجهة عرض تفاصيل منتج معين في السلة

    Args:
        item: بيانات المنتج (id, name, quantity, price, unit_price)

    Returns:
        dict: كائن InlineKeyboardMarkup جاهز للإرسال إلى Telegram
    """
    logger.info(
        "display_cart_item_ui",
        extra={
            "item_id": item.get("id"),
        },
    )

    item_id = item.get(
        "id",
        0,
    )

    name = item.get(
        "name",
        "منتج",
    )

    quantity = item.get(
        "quantity",
        1,
    )

    total_price = item.get(
        "price",
        0,
    )

    return {
        "inline_keyboard": [
            [
                await button(
                    text=f"📦 {name}",
                    callback=f"noop",
                ),
            ],
            [
                await button(
                    text=f"🔢 الكمية: {quantity}",
                    callback=f"noop",
                ),
            ],
            [
                await button(
                    text=f"💰 السعر: {total_price} دج",
                    callback=f"noop",
                ),
            ],
            [
                await button(
                    text="➕ زيادة الكمية",
                    callback=f"cart_inc_{item_id}",
                ),
                await button(
                    text="➖ إنقاص الكمية",
                    callback=f"cart_dec_{item_id}",
                ),
            ],
            [
                await button(
                    text="❌ حذف المنتج",
                    callback=f"cart_remove_{item_id}",
                ),
            ],
            [
                await button(
                    text="🔙 رجوع إلى السلة",
                    callback="show_cart",
                ),
            ],
        ],
    }


# ==============================================
# 🚫 CART EMPTY UI
# عرض رسالة السلة فارغة
# ==============================================


# ==============================================
# CART EMPTY UI
# ==============================================


async def cart_empty_ui() -> dict:
    """
    بناء واجهة تعرض رسالة "السلة فارغة" مع زر رجوع

    Returns:
        dict: كائن InlineKeyboardMarkup جاهز للإرسال إلى Telegram
    """
    logger.info(
        "display_cart_empty_ui",
    )

    return {
        "inline_keyboard": [
            [
                await button(
                    text="🛒 السلة فارغة",
                    callback="noop",
                ),
            ],
            [
                await button(
                    text="🔙 رجوع",
                    callback="back_main",
                ),
            ],
        ],
    }


# ==============================================
# ⚠️ CART CONFIRMATION UI
# عرض تأكيد قبل إفراغ السلة
# ==============================================


# ==============================================
# CART CONFIRMATION UI
# ==============================================


async def cart_confirmation_ui() -> dict:
    """
    بناء واجهة تأكيد إفراغ السلة

    Returns:
        dict: كائن InlineKeyboardMarkup جاهز للإرسال إلى Telegram
    """
    logger.info(
        "display_cart_confirmation_ui",
    )

    return {
        "inline_keyboard": [
            [
                await button(
                    text="⚠️ هل أنت متأكد من إفراغ السلة؟",
                    callback="noop",
                ),
            ],
            [
                await button(
                    text="✅ نعم، إفراغ السلة",
                    callback="cart_clear_confirm",
                ),
                await button(
                    text="❌ إلغاء",
                    callback="show_cart",
                ),
            ],
        ],
    }
