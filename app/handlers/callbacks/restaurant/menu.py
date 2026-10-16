# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HANDLERS / CALLBACKS / RESTAURANT / MENU
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for menu.

Part of MoulAI Platform - Agent-as-a-Service.
"""

import re

from app.core.logger import logger
from app.core.middleware.rate_limit import rate_limit

from app.helpers.ui_manager import UIManager

from app.repositories.products_repo import ProductRepository
from app.core.database import get_session
from app.repositories.categories_repo import CategoriesRepository

from app.views.ui import button

# ==============================================
# 🍽️ SHOW RESTAURANT MENU
# عرض قائمة المطعم
# ==============================================


# ==============================================
# RESTAURANT MENU CALLBACK
# ==============================================


@rate_limit(
    limit=10,
    window=30,
    key_prefix="restaurant_menu",
)
async def restaurant_menu_callback(
    *,
    chat_id: int,
    message_id: int,
    callback_data: str,
    match: re.Match[str],
) -> None:
    """
    عرض قائمة المطعم للزبون
    """
    try:
        restaurant_id = int(match.group(1))
    except (IndexError, ValueError):
        logger.warning(
            "restaurant_menu_invalid_restaurant_id",
            extra={
                "chat_id": chat_id,
                "callback_data": callback_data,
            },
        )
        return

    logger.info(
        "restaurant_menu_callback",
        extra={
            "chat_id": chat_id,
            "restaurant_id": restaurant_id,
        },
    )

    # جلب الأقسام
    async with await get_session() as session:
        category_models = await CategoriesRepository(session).get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )
        product_models = await ProductRepository(session).get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )

    categories = [
        {"id": category.id, "name": category.name} for category in category_models
    ]
    products = [
        {
            "category_id": product.category_id,
            "name": product.name,
            "price": product.price,
        }
        for product in product_models
    ]

    # جلب المنتجات

    # بناء الرسالة
    text = "🍽️ **قائمة المطعم**\n\n"

    if categories:
        for category in categories:
            text += f"📂 **{category.get('name', 'غير محدد')}**\n"
            category_products = [
                p for p in products if p.get("category_id") == category.get("id")
            ]
            for product in category_products[:5]:
                text += f"  • {product.get('name')} - {product.get('price')} دج\n"
            text += "\n"
    else:
        text += "⚠️ لا توجد أقسام بعد.\n"

    buttons = [
        [
            await button(
                text="🔙 رجوع إلى المطعم",
                callback=f"restaurant_details_{restaurant_id}",
            ),
        ],
    ]

    await UIManager.edit(
        chat_id=chat_id,
        message_id=message_id,
        text=text,
        reply_markup={
            "inline_keyboard": buttons,
        },
    )
