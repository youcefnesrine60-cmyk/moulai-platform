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

import re

from app.core.database import get_session
from app.core.logger import logger

from app.helpers.ui_manager import UIManager

from app.repositories.restaurant.restaurant_repo import RestaurantRepository

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
    match: re.Match[str],
) -> None:

    # ==========================================
    # 🔍 EXTRACT RESTAURANT ID
    # ==========================================

    try:
        restaurant_id = int(match.group(1))

    except (IndexError, ValueError):
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

    async with await get_session() as session:
        restaurant_model = await RestaurantRepository(session).get_by_id(
            id=restaurant_id,
        )

    restaurant = (
        {"name": restaurant_model.name} if restaurant_model is not None else None
    )

    if not restaurant:
        logger.warning(
            "restaurant_not_found",
            extra={
                "chat_id": chat_id,
                "restaurant_id": restaurant_id,
            },
        )

        await UIManager.edit(
            chat_id=chat_id,
            message_id=message_id,
            text="❌ المطعم غير موجود.",
            reply_markup=await back_ui(),
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

    await UIManager.edit(
        chat_id=chat_id,
        message_id=message_id,
        text=f"🍔 {restaurant['name']}",
        reply_markup=await restaurant_actions_ui(
            restaurant_id=restaurant_id,
        ),
    )
