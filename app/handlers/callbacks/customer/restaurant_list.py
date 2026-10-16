# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HANDLERS / CALLBACKS / CUSTOMER / RESTAURANT LIST
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for restaurant list.

Part of MoulAI Platform - Agent-as-a-Service.
"""

import re

from app.core.database import get_session
from app.core.logger import logger
from app.helpers.ui_manager import UIManager
from app.repositories.restaurant.restaurant_repo import RestaurantRepository
from app.repositories.state_repo import set_state
from app.services.business.user_service import UserService
from app.states.customer_states import CustomerStates
from app.views.ui import consent_text, consent_ui, restaurants_ui

# ==============================================
# 👤 CUSTOMER CALLBACK
# ==============================================


async def customer_callback(
    *, chat_id: int, message_id: int, callback_data: str, match: re.Match
) -> None:

    # ==========================================
    # 🚫 CONSENT REQUIRED
    # ==========================================

    async with await get_session() as session:
        has_consent = await UserService(session).has_consent(chat_id=chat_id)

    if not has_consent:

        logger.info("customer_consent_required", extra={"chat_id": chat_id})

        await UIManager.edit(
            chat_id=chat_id,
            text=consent_text(),
            reply_markup=await consent_ui(role="customer"),
            message_id=message_id,
        )
        return

    # ==========================================
    # 🧠 INIT CUSTOMER FLOW
    # ==========================================

    await set_state(
        chat_id=chat_id,
        state={"flow": "customer", "step": CustomerStates.RESTAURANT, "history": []},
    )

    logger.info("customer_flow_started", extra={"chat_id": chat_id})

    await show_restaurants(chat_id=chat_id, message_id=message_id)


# ==========================================
# 🍽️ SHOW RESTAURANTS
# عرض قائمة المطاعم للمستخدم
# ==========================================


# ==============================================
# SHOW RESTAURANTS
# ==============================================


async def show_restaurants(*, chat_id: int, message_id: int) -> None:

    async with await get_session() as session:
        restaurant_models = await RestaurantRepository(session).get_all(
            filters={"is_active": True}, order_by="name"
        )

    restaurants = [
        {"id": restaurant.id, "name": restaurant.name, "wilaya": restaurant.wilaya}
        for restaurant in restaurant_models
    ]

    if not restaurants:

        logger.warning("لا توجد مطاعم لعرضها للمستخدم", extra={"chat_id": chat_id})

        await UIManager.edit(
            chat_id=chat_id,
            text="❌ عذراً، قائمة المطاعم غير متوفرة حالياً",
            reply_markup=None,
            message_id=message_id,
        )
        return

    logger.info("عرض قائمة المطاعم للمستخدم", extra={"chat_id": chat_id})

    await UIManager.edit(
        chat_id=chat_id,
        text="🍽️ اختر مطعم:",
        reply_markup=await restaurants_ui(restaurants=restaurants),
        message_id=message_id,
    )
