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

from app.core.logger import logger

from app.repositories.restaurant.restaurant_repo import get_all_restaurants
from app.repositories.user_repo import has_consent
from app.repositories.state_repo import set_state
from app.helpers.ui_manager import UIManager

from app.views.ui import consent_text, consent_ui

from app.states.customer_states import CustomerStates
from app.views.ui import restaurants_ui

# ==============================================
# 👤 CUSTOMER CALLBACK
# ==============================================


async def customer_callback(
    *, chat_id: int, message_id: int, callback_data: str, match: re.Match
) -> None:

    # ==========================================
    # 🚫 CONSENT REQUIRED
    # ==========================================

    if not await has_consent(chat_id=chat_id):

        logger.info("customer_consent_required", extra={"chat_id": chat_id})

        await UIManager.update(
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

    restaurants = await get_all_restaurants()

    if not restaurants:

        logger.warning("لا توجد مطاعم لعرضها للمستخدم", extra={"chat_id": chat_id})

        await UIManager.update(
            chat_id=chat_id,
            text="❌ عذراً، قائمة المطاعم غير متوفرة حالياً",
            reply_markup=None,
            message_id=message_id,
        )
        return

    logger.info("عرض قائمة المطاعم للمستخدم", extra={"chat_id": chat_id})

    await UIManager.update(
        chat_id=chat_id,
        text="🍽️ اختر مطعم:",
        reply_markup=await restaurants_ui(restaurants=restaurants),
        message_id=message_id,
    )
