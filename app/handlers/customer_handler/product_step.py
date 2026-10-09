# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HANDLERS / CUSTOMER_HANDLER / PRODUCT STEP
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for product step.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.logger import logger
from app.helpers.ui_manager import UIManager
from app.handlers.customer_handler.cart_step import add_to_cart

# ==============================================
# 🍔 HANDLE PRODUCT STEP
# ==============================================


async def handle_product_step(
    *,
    chat_id: int,
    text: str,
    state: dict,
) -> None:
    """
    معالجة رسائل المستخدم في مرحلة اختيار المنتجات

    Args:
        chat_id: معرف المستخدم
        text: النص المرسل
        state: حالة المستخدم الحالية
    """
    logger.info(
        "handle_product_step",
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
            "product_step_invalid_input",
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
            "product_step_product_not_found",
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
