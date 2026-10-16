# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HANDLERS / CALLBACKS / RESTAURANT / DETAILS
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for details.

Part of MoulAI Platform - Agent-as-a-Service.
"""

import re

from app.core.database import get_session
from app.core.logger import logger
from app.core.middleware.rate_limit import rate_limit
from app.helpers.ui_manager import UIManager
from app.repositories.branches_repo import BranchesRepository
from app.repositories.products_repo import ProductRepository
from app.repositories.restaurant.restaurant_repo import RestaurantRepository
from app.views.ui import button

# ==============================================
# 🍽️ RESTAURANT DETAILS
# عرض تفاصيل المطعم
# ==============================================


# ==============================================
# RESTAURANT DETAILS CALLBACK
# ==============================================


@rate_limit(
    limit=10,
    window=30,
    key_prefix="restaurant_details",
)
async def restaurant_details_callback(
    *,
    chat_id: int,
    message_id: int,
    callback_data: str,
    match: re.Match[str],
) -> None:
    """
    عرض تفاصيل المطعم للزبون
    """
    try:
        restaurant_id = int(match.group(1))
    except (IndexError, ValueError):
        logger.warning(
            "restaurant_details_invalid_restaurant_id",
            extra={
                "chat_id": chat_id,
                "callback_data": callback_data,
            },
        )
        return

    logger.info(
        "restaurant_details_callback",
        extra={
            "chat_id": chat_id,
            "restaurant_id": restaurant_id,
        },
    )

    # جلب بيانات المطعم
    async with await get_session() as session:
        restaurant_model = await RestaurantRepository(session).get_by_id(
            id=restaurant_id
        )
        branch_models = await BranchesRepository(session).get_by_restaurant_id(
            restaurant_id=restaurant_id,
        )
        products_count = await ProductRepository(session).count_by_restaurant(
            restaurant_id=restaurant_id,
        )

    restaurant = (
        {
            "name": restaurant_model.name,
            "phone": restaurant_model.phone,
            "wilaya": restaurant_model.wilaya,
        }
        if restaurant_model is not None
        else None
    )

    if not restaurant:
        await UIManager.edit(
            chat_id=chat_id,
            message_id=message_id,
            text="❌ المطعم غير موجود.",
            reply_markup=None,
        )
        return

    # جلب الفروع
    branches = [
        {
            "name": branch.name,
            "wilaya": branch.wilaya,
        }
        for branch in branch_models
    ]

    # جلب عدد المنتجات

    # بناء الرسالة
    branches_text = (
        "\n".join(
            f"• {b.get('name', 'فرع')} - {b.get('wilaya', 'غير محدد')}"
            for b in branches[:3]
        )
        if branches
        else "⚠️ لا توجد فروع."
    )

    text = (
        f"🍽️ **{restaurant.get('name', 'مطعم')}**\n\n"
        f"📞 الهاتف: {restaurant.get('phone', 'غير محدد')}\n"
        f"📍 الولاية: {restaurant.get('wilaya', 'غير محدد')}\n"
        f"🍔 عدد المنتجات: {products_count}\n"
        f"🏢 الفروع:\n{branches_text}\n"
    )

    # أزرار
    buttons = [
        [
            await button(
                text="📋 عرض القائمة",
                callback=f"restaurant_menu_{restaurant_id}",
            ),
        ],
        [
            await button(
                text="📍 عرض الموقع",
                callback=f"restaurant_location_{restaurant_id}",
            ),
        ],
        [
            await button(
                text="🔙 رجوع إلى المطاعم",
                callback="show_restaurants",
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
