# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HANDLERS / WEBAPP HANDLER
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for webapp handler.

Part of MoulAI Platform - Agent-as-a-Service.
"""

import json

from app.core.logger import logger
from app.helpers.state_transition import transition_to
from app.helpers.ui_manager import UIManager
from app.repositories.state_repo import get_state
from app.states.owner_states import OwnerStates
from app.views.ui import types_ui

# ==============================================
# 🌍 HANDLE WEBAPP DATA
# ==============================================


async def handle_webapp_data(
    *,
    data: dict,
) -> None:

    message = data["message"]

    chat_id = message["chat"]["id"]

    state = await get_state(
        chat_id=chat_id,
    )

    # ==========================================
    # 🚫 STATE NOT FOUND
    # ==========================================

    if not state:

        logger.warning(
            "webapp_state_missing",
            extra={
                "chat_id": chat_id,
            },
        )

        return

    # ==========================================
    # 🚫 INVALID STEP
    # ==========================================

    if state["step"] != OwnerStates.LOCATION:

        logger.warning(
            "invalid_webapp_step",
            extra={
                "chat_id": chat_id,
                "step": state["step"],
            },
        )

        return

    # ==========================================
    # 📍 EXTRACT LOCATION
    # ==========================================

    webapp_data = json.loads(
        message["web_app_data"]["data"],
    )

    state["lat"] = webapp_data["lat"]
    state["lng"] = webapp_data["lng"]

    logger.info(
        "location_saved",
        extra={
            "chat_id": chat_id,
            "lat": state["lat"],
            "lng": state["lng"],
        },
    )

    # ==========================================
    # 🔄 TRANSITION TO TYPE
    # ==========================================

    success = await transition_to(
        chat_id=chat_id,
        state=state,
        next_state=OwnerStates.TYPE,
    )

    if not success:

        logger.error(
            "webapp_transition_failed",
            extra={
                "chat_id": chat_id,
            },
        )

        return

    # ==========================================
    # 🍽️ SHOW TYPES
    # ==========================================

    await UIManager.update(
        chat_id=chat_id,
        text="📍 تم حفظ موقع المحل بنجاح.",
        reply_markup=None,
    )

    await UIManager.update(
        chat_id=chat_id,
        text="🍽️ اختر نوع المحل:",
        reply_markup=await types_ui(),
    )

    logger.info(
        "webapp_location_processed",
        extra={
            "chat_id": chat_id,
            "next_step": OwnerStates.TYPE,
        },
    )
