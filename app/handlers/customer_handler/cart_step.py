# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HANDLERS / CUSTOMER_HANDLER / CART STEP
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for cart step.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.logger import logger

from app.helpers.ui_manager import UIManager
from app.repositories.state_repo import get_state, set_state

from app.views.cart_ui import cart_ui, cart_empty_ui

# ==============================================
# ➕ ADD TO CART
# إضافة منتج إلى السلة
# ==============================================


# ==============================================
# ADD TO CART
# ==============================================


async def add_to_cart(
    *,
    chat_id: int,
    product_id: int,
    product_name: str,
    unit_price: float,
    quantity: int = 1,
) -> None:
    """
    إضافة منتج إلى سلة التسوق

    Args:
        chat_id: معرف المستخدم
        product_id: معرف المنتج
        product_name: اسم المنتج
        unit_price: سعر الوحدة
        quantity: الكمية (افتراضي 1)
    """
    logger.info(
        "add_to_cart",
        extra={
            "chat_id": chat_id,
            "product_id": product_id,
            "product_name": product_name,
            "quantity": quantity,
        },
    )

    # جلب حالة المستخدم
    state = await get_state(
        chat_id=chat_id,
    )

    if not state:
        logger.warning(
            "state_not_found_add_to_cart",
            extra={
                "chat_id": chat_id,
            },
        )
        return

    # جلب السلة من الحالة
    cart = state.get("cart", [])

    # البحث عن المنتج في السلة
    found = False

    for item in cart:
        if item.get("id") == product_id:
            # تحديث الكمية والسعر
            item["quantity"] = item.get("quantity", 0) + quantity
            item["price"] = item["quantity"] * unit_price
            found = True
            break

    # إذا لم يكن المنتج موجوداً، نضيفه
    if not found:
        cart.append(
            {
                "id": product_id,
                "name": product_name,
                "unit_price": unit_price,
                "quantity": quantity,
                "price": quantity * unit_price,
            },
        )

    # حفظ الحالة
    state["cart"] = cart
    await set_state(
        chat_id=chat_id,
        state=state,
    )

    # حساب المجموع الكلي
    total = sum(float(item.get("price", 0)) for item in cart)

    logger.info(
        "product_added_to_cart",
        extra={
            "chat_id": chat_id,
            "product_id": product_id,
            "total_items": len(cart),
            "total_price": total,
        },
    )


# ==============================================
# 🛒 SHOW CART
# عرض السلة للمستخدم
# ==============================================


# ==============================================
# SHOW CART
# ==============================================


async def show_cart(
    *,
    chat_id: int,
) -> None:
    """
    عرض سلة التسوق للمستخدم
    """
    logger.info(
        "show_cart",
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
            "state_not_found_show_cart_step",
            extra={
                "chat_id": chat_id,
            },
        )
        return

    # جلب السلة
    cart = state.get("cart", [])

    if not cart:
        await UIManager.update(
            chat_id=chat_id,
            text="🛒 السلة فارغة.",
            reply_markup=await cart_empty_ui(),
        )
        return

    # حساب المجموع الكلي
    total = sum(float(item.get("price", 0)) for item in cart)

    await UIManager.update(
        chat_id=chat_id,
        text=f"🛒 سلة التسوق\n\nالمجموع الكلي: {total:.2f} دج",
        reply_markup=await cart_ui(
            items=cart,
            total=total,
        ),
    )


# ==============================================
# 🛒 HANDLE CART STEP
# معالجة رسائل المستخدم أثناء السلة
# ==============================================


# ==============================================
# HANDLE CART STEP
# ==============================================


async def handle_cart_step(
    *,
    chat_id: int,
    text: str,
    state: dict,
) -> None:
    """
    معالجة رسائل المستخدم في مرحلة السلة

    Args:
        chat_id: معرف المستخدم
        text: النص المرسل
        state: حالة المستخدم الحالية
    """
    logger.info(
        "handle_cart_step",
        extra={
            "chat_id": chat_id,
            "text_length": len(text),
        },
    )

    # محاولة تحويل النص إلى رقم (معرف المنتج)
    try:
        product_id = int(text.strip())
    except ValueError:
        logger.warning(
            "cart_step_invalid_input",
            extra={
                "chat_id": chat_id,
                "text": text,
            },
        )

        await UIManager.update(
            chat_id=chat_id,
            text="❌ الرجاء إدخال رقم المنتج الصحيح.",
            reply_markup=None,
        )
        return

    # البحث عن المنتج في حالة المستخدم
    products = state.get("products", [])
    product = None

    for p in products:
        if p.get("id") == product_id:
            product = p
            break

    if not product:
        logger.warning(
            "cart_step_product_not_found",
            extra={
                "chat_id": chat_id,
                "product_id": product_id,
            },
        )

        await UIManager.update(
            chat_id=chat_id,
            text="❌ المنتج غير موجود.",
            reply_markup=None,
        )
        return

    # إضافة المنتج إلى السلة (بكمية 1 افتراضياً)
    await add_to_cart(
        chat_id=chat_id,
        product_id=product_id,
        product_name=product.get("name", "منتج"),
        unit_price=float(product.get("price", 0)),
        quantity=1,
    )

    logger.info(
        "product_added_to_cart_from_step",
        extra={
            "chat_id": chat_id,
            "product_id": product_id,
            "product_name": product.get("name"),
        },
    )

    # عرض رسالة نجاح
    await UIManager.update(
        chat_id=chat_id,
        text=(
            f"✅ تم إضافة {product.get('name', 'المنتج')} إلى السلة.\n\n"
            f"💰 السعر: {product.get('price', 0)} دج\n\n"
            f"يمكنك اختيار منتج آخر أو الذهاب إلى السلة."
        ),
        reply_markup=None,
    )
