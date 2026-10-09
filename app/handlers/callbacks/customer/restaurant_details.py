# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HANDLERS / CALLBACKS / CUSTOMER / RESTAURANT DETAILS
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for restaurant details.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.logger import logger

from app.helpers.ui_manager import UIManager

from app.repositories.restaurant.restaurant_repo import get_restaurant_by_id

from app.views.ui import (
    back_ui,
    restaurant_actions_ui,
)

# ==============================================
# 🍔 HANDLE RESTAURANT SELECTION
# ==============================================


async def handle_restaurant_selection(
    *,
    chat_id: int,
    message_id: int,
    callback_data: str,
) -> None:

    # ==========================================
    # 🔍 EXTRACT RESTAURANT ID
    # ==========================================

    try:

        restaurant_id = int(callback_data.removeprefix("rest_"))

    except ValueError:

        logger.warning(
            "invalid_restaurant_callback",
            extra={
                "chat_id": chat_id,
                "callback_data": callback_data,
            },
        )

        return

    # ==========================================
    # 🔍 LOAD RESTAURANT
    # ==========================================

    restaurant = await get_restaurant_by_id(
        restaurant_id=restaurant_id,
    )

    if not restaurant:

        logger.warning(
            "restaurant_not_found",
            extra={
                "chat_id": chat_id,
                "restaurant_id": restaurant_id,
            },
        )

        await UIManager.update(
            chat_id=chat_id,
            message_id=message_id,
            text="❌ المطعم غير موجود.",
            reply_markup=back_ui(),
        )

        return

    # ==========================================
    # ✅ SHOW RESTAURANT
    # ==========================================

    logger.info(
        "restaurant_selected",
        extra={
            "chat_id": chat_id,
            "restaurant_id": restaurant_id,
        },
    )

    await UIManager.update(
        chat_id=chat_id,
        message_id=message_id,
        text=f"🍔 {restaurant['name']}",
        reply_markup=restaurant_actions_ui(
            restaurant_id,
        ),
    )
