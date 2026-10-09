# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HANDLERS / CALLBACKS / CUSTOMER / CART
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for cart.

Part of MoulAI Platform - Agent-as-a-Service.
"""

import re

from app.core.logger import logger
from app.core.middleware.rate_limit import rate_limit

from app.helpers.ui_manager import UIManager

from app.repositories.state_repo import get_state, set_state

from app.views.cart_ui import cart_ui, cart_item_ui, cart_empty_ui
from app.views.payment_ui import payment_ui

from app.services.business.order_payments_service import (
    get_allowed_payment_methods_for_order,
)

# ==============================================
# 🛒 SHOW CART
# عرض السلة
# ==============================================


# ==============================================
# SHOW CART CALLBACK
# ==============================================


@rate_limit(
    limit=10,
    window=30,
    key_prefix="show_cart",
)
async def show_cart_callback(
    *,
    chat_id: int,
    message_id: int,
    callback_data: str,
    match: re.Match[str],
) -> None:
    """
    عرض سلة التسوق للزبون
    """
    logger.info(
        "show_cart_callback",
        extra={
            "chat_id": chat_id,
        },
    )

    # جلب حالة المستخدم
    state = await get_state(
        chat_id=chat_id,
    )

    if not state:
        logger.warning(
            "state_not_found_show_cart",
            extra={
                "chat_id": chat_id,
            },
        )
        return

    # جلب عناصر السلة من الحالة
    cart = state.get("cart", [])

    if not cart:
        logger.info(
            "cart_empty",
            extra={
                "chat_id": chat_id,
            },
        )

        await UIManager.update(
            chat_id=chat_id,
            message_id=message_id,
            text="🛒 السلة فارغة.",
            reply_markup=await cart_empty_ui(),
        )
        return

    # حساب المجموع الكلي
    total = sum(float(item.get("price", 0)) for item in cart)

    await UIManager.update(
        chat_id=chat_id,
        message_id=message_id,
        text=f"🛒 سلة التسوق\n\nالمجموع الكلي: {total:.2f} دج",
        reply_markup=await cart_ui(
            items=cart,
            total=total,
        ),
    )


# ==============================================
# 🛒 CART ITEM
# عرض تفاصيل منتج في السلة
# ==============================================


# ==============================================
# CART ITEM CALLBACK
# ==============================================


@rate_limit(
    limit=10,
    window=30,
    key_prefix="cart_item",
)
async def cart_item_callback(
    *,
    chat_id: int,
    message_id: int,
    callback_data: str,
    match: re.Match[str],
) -> None:
    """
    عرض تفاصيل منتج معين في السلة
    """
    # استخراج معرف المنتج من callback_data
    item_id = int(
        match.group(1),
    )

    logger.info(
        "cart_item_callback",
        extra={
            "chat_id": chat_id,
            "item_id": item_id,
        },
    )

    # جلب حالة المستخدم
    state = await get_state(
        chat_id=chat_id,
    )

    if not state:
        logger.warning(
            "state_not_found_cart_item",
            extra={
                "chat_id": chat_id,
            },
        )
        return

    # البحث عن المنتج في السلة
    cart = state.get("cart", [])
    item = None

    for i in cart:
        if i.get("id") == item_id:
            item = i
            break

    if not item:
        logger.warning(
            "item_not_found_in_cart",
            extra={
                "chat_id": chat_id,
                "item_id": item_id,
            },
        )

        await UIManager.update(
            chat_id=chat_id,
            message_id=message_id,
            text="❌ المنتج غير موجود في السلة.",
            reply_markup=await cart_empty_ui(),
        )
        return

    await UIManager.update(
        chat_id=chat_id,
        message_id=message_id,
        text=f"📦 {item.get('name', 'منتج')}",
        reply_markup=await cart_item_ui(
            item=item,
        ),
    )


# ==============================================
# ➕ CART INCREMENT
# زيادة كمية منتج في السلة
# ==============================================


# ==============================================
# CART INCREMENT CALLBACK
# ==============================================


@rate_limit(
    limit=10,
    window=30,
    key_prefix="cart_inc",
)
async def cart_increment_callback(
    *,
    chat_id: int,
    message_id: int,
    callback_data: str,
    match: re.Match[str],
) -> None:
    """
    زيادة كمية منتج في السلة
    """
    # استخراج معرف المنتج من callback_data
    item_id = int(
        match.group(1),
    )

    logger.info(
        "cart_increment_callback",
        extra={
            "chat_id": chat_id,
            "item_id": item_id,
        },
    )

    # جلب حالة المستخدم
    state = await get_state(
        chat_id=chat_id,
    )

    if not state:
        logger.warning(
            "state_not_found_cart_inc",
            extra={
                "chat_id": chat_id,
            },
        )
        return

    # تحديث الكمية في السلة
    cart = state.get("cart", [])

    for item in cart:
        if item.get("id") == item_id:
            quantity = item.get("quantity", 1)
            unit_price = item.get("unit_price", 0)
            item["quantity"] = quantity + 1
            item["price"] = (quantity + 1) * unit_price
            break

    # حفظ الحالة
    state["cart"] = cart
    await set_state(
        chat_id=chat_id,
        state=state,
    )

    # حساب المجموع الكلي
    total = sum(float(item.get("price", 0)) for item in cart)

    await UIManager.update(
        chat_id=chat_id,
        message_id=message_id,
        text=f"🛒 سلة التسوق\n\nالمجموع الكلي: {total:.2f} دج",
        reply_markup=await cart_ui(
            items=cart,
            total=total,
        ),
    )


# ==============================================
# ➖ CART DECREMENT
# إنقاص كمية منتج في السلة
# ==============================================


# ==============================================
# CART DECREMENT CALLBACK
# ==============================================


@rate_limit(
    limit=10,
    window=30,
    key_prefix="cart_dec",
)
async def cart_decrement_callback(
    *,
    chat_id: int,
    message_id: int,
    callback_data: str,
    match: re.Match[str],
) -> None:
    """
    إنقاص كمية منتج في السلة
    """
    # استخراج معرف المنتج من callback_data
    item_id = int(
        match.group(1),
    )

    logger.info(
        "cart_decrement_callback",
        extra={
            "chat_id": chat_id,
            "item_id": item_id,
        },
    )

    # جلب حالة المستخدم
    state = await get_state(
        chat_id=chat_id,
    )

    if not state:
        logger.warning(
            "state_not_found_cart_dec",
            extra={
                "chat_id": chat_id,
            },
        )
        return

    # تحديث الكمية في السلة
    cart = state.get("cart", [])

    for item in cart:
        if item.get("id") == item_id:
            quantity = item.get("quantity", 1)
            unit_price = item.get("unit_price", 0)

            if quantity <= 1:
                # حذف المنتج إذا كانت الكمية 1
                cart.remove(item)
                break

            item["quantity"] = quantity - 1
            item["price"] = (quantity - 1) * unit_price
            break

    # حفظ الحالة
    state["cart"] = cart
    await set_state(
        chat_id=chat_id,
        state=state,
    )

    # إذا أصبحت السلة فارغة
    if not cart:
        await UIManager.update(
            chat_id=chat_id,
            message_id=message_id,
            text="🛒 السلة فارغة.",
            reply_markup=await cart_empty_ui(),
        )
        return

    # حساب المجموع الكلي
    total = sum(float(item.get("price", 0)) for item in cart)

    await UIManager.update(
        chat_id=chat_id,
        message_id=message_id,
        text=f"🛒 سلة التسوق\n\nالمجموع الكلي: {total:.2f} دج",
        reply_markup=await cart_ui(
            items=cart,
            total=total,
        ),
    )


# ==============================================
# ❌ CART REMOVE
# حذف منتج من السلة
# ==============================================


# ==============================================
# CART REMOVE CALLBACK
# ==============================================


@rate_limit(
    limit=10,
    window=30,
    key_prefix="cart_remove",
)
async def cart_remove_callback(
    *,
    chat_id: int,
    message_id: int,
    callback_data: str,
    match: re.Match[str],
) -> None:
    """
    حذف منتج من السلة
    """
    # استخراج معرف المنتج من callback_data
    item_id = int(
        match.group(1),
    )

    logger.info(
        "cart_remove_callback",
        extra={
            "chat_id": chat_id,
            "item_id": item_id,
        },
    )

    # جلب حالة المستخدم
    state = await get_state(
        chat_id=chat_id,
    )

    if not state:
        logger.warning(
            "state_not_found_cart_remove",
            extra={
                "chat_id": chat_id,
            },
        )
        return

    # حذف المنتج من السلة
    cart = state.get("cart", [])

    for item in cart[:]:
        if item.get("id") == item_id:
            cart.remove(item)
            break

    # حفظ الحالة
    state["cart"] = cart
    await set_state(
        chat_id=chat_id,
        state=state,
    )

    # إذا أصبحت السلة فارغة
    if not cart:
        await UIManager.update(
            chat_id=chat_id,
            message_id=message_id,
            text="🛒 السلة فارغة.",
            reply_markup=await cart_empty_ui(),
        )
        return

    # حساب المجموع الكلي
    total = sum(float(item.get("price", 0)) for item in cart)

    await UIManager.update(
        chat_id=chat_id,
        message_id=message_id,
        text=f"🛒 سلة التسوق\n\nالمجموع الكلي: {total:.2f} دج",
        reply_markup=await cart_ui(
            items=cart,
            total=total,
        ),
    )


# ==============================================
# 🗑️ CART CLEAR
# إفراغ السلة
# ==============================================


# ==============================================
# CART CLEAR CALLBACK
# ==============================================


@rate_limit(
    limit=5,
    window=60,
    key_prefix="cart_clear",
)
async def cart_clear_callback(
    *,
    chat_id: int,
    message_id: int,
    callback_data: str,
    match: re.Match[str],
) -> None:
    """
    إفراغ السلة بالكامل
    """
    logger.info(
        "cart_clear_callback",
        extra={
            "chat_id": chat_id,
        },
    )

    # جلب حالة المستخدم
    state = await get_state(
        chat_id=chat_id,
    )

    if not state:
        logger.warning(
            "state_not_found_cart_clear",
            extra={
                "chat_id": chat_id,
            },
        )
        return

    # إفراغ السلة
    state["cart"] = []
    await set_state(
        chat_id=chat_id,
        state=state,
    )

    await UIManager.update(
        chat_id=chat_id,
        message_id=message_id,
        text="🗑️ تم إفراغ السلة بنجاح.",
        reply_markup=await cart_empty_ui(),
    )


# ==============================================
# 💳 CHECKOUT
# الانتقال إلى الدفع
# ==============================================


# ==============================================
# CHECKOUT CALLBACK
# ==============================================


@rate_limit(
    limit=5,
    window=60,
    key_prefix="checkout",
)
async def checkout_callback(
    *,
    chat_id: int,
    message_id: int,
    callback_data: str,
    match: re.Match[str],
) -> None:
    """
    الانتقال إلى واجهة الدفع
    """
    logger.info(
        "checkout_callback",
        extra={
            "chat_id": chat_id,
        },
    )

    # جلب حالة المستخدم
    state = await get_state(
        chat_id=chat_id,
    )

    if not state:
        logger.warning(
            "state_not_found_checkout",
            extra={
                "chat_id": chat_id,
            },
        )
        return

    # التحقق من وجود عناصر في السلة
    cart = state.get("cart", [])

    if not cart:
        await UIManager.update(
            chat_id=chat_id,
            message_id=message_id,
            text="🛒 السلة فارغة. أضف منتجات أولاً.",
            reply_markup=await cart_empty_ui(),
        )
        return

    # حساب المجموع الكلي
    total = sum(float(item.get("price", 0)) for item in cart)

    # الحصول على معرف المطعم من الحالة
    restaurant_id = state.get("restaurant_id")

    if not restaurant_id:
        logger.warning(
            "restaurant_id_not_found_checkout",
            extra={
                "chat_id": chat_id,
            },
        )
        await UIManager.update(
            chat_id=chat_id,
            message_id=message_id,
            text="❌ حدث خطأ. يرجى المحاولة مرة أخرى.",
            reply_markup=None,
        )
        return

    # جلب طرق الدفع المسموح بها للمطعم
    allowed_methods = await get_allowed_payment_methods_for_order(
        order_id=state.get("order_id", 0),
    )

    # إذا لم توجد طرق دفع مسموح بها، نستخدم الافتراضية
    if not allowed_methods:
        allowed_methods = {"cash", "card"}

    logger.info(
        "checkout_allowed_methods",
        extra={
            "chat_id": chat_id,
            "allowed_methods": list(allowed_methods),
        },
    )

    await UIManager.update(
        chat_id=chat_id,
        message_id=message_id,
        text=(
            f"💳 الدفع\n\n" f"المجموع الكلي: {total:.2f} دج\n\n" f"اختر طريقة الدفع:"
        ),
        reply_markup=await payment_ui(
            allowed_methods=allowed_methods,
            order_id=state.get("order_id", 0),
        ),
    )
