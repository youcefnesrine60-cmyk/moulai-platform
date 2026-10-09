# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HANDLERS / CALLBACKS / TYPE CALLBACKS
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for type callbacks.

Part of MoulAI Platform - Agent-as-a-Service.
"""

import re

from app.core.logger import logger

from app.helpers.ui_manager import UIManager

from app.repositories.state_repo import (
    get_state,
    set_state,
)

from app.states.owner_states import OwnerStates

from app.views.texts import PHONE_NUMBER

from app.views.ui import back_ui

# ==============================================
# 🍽️ TYPE CALLBACK
# ==============================================


async def type_callback(
    *,
    chat_id: int,
    message_id: int,
    callback_data: str,
    match: re.Match,
) -> None:

    # ==========================================
    # 📥 LOAD STATE
    # ==========================================

    state = await get_state(
        chat_id=chat_id,
    )

    # ==========================================
    # 🚫 STATE NOT FOUND
    # ==========================================

    if not state:

        logger.warning(
            "type_state_missing",
            extra={
                "chat_id": chat_id,
            },
        )

        return

    # ==========================================
    # 🍽️ SAVE TYPE
    # ==========================================

    selected_type = callback_data.removeprefix(
        "type_",
    )

    state["type"] = selected_type

    # ==========================================
    # 📜 UPDATE HISTORY
    # ==========================================

    state["history"].append(
        OwnerStates.TYPE,
    )

    # ==========================================
    # 🔄 UPDATE STEP
    # ==========================================

    state["step"] = OwnerStates.PHONE

    # ==========================================
    # 💾 SAVE STATE
    # ==========================================

    await set_state(
        chat_id=chat_id,
        state=state,
    )

    logger.info(
        "owner_type_selected",
        extra={
            "chat_id": chat_id,
            "type": selected_type,
            "next_step": OwnerStates.PHONE,
        },
    )

    # ==========================================
    # 📞 REQUEST PHONE NUMBER
    # ==========================================

    await UIManager.update(
        chat_id=chat_id,
        message_id=message_id,
        text=PHONE_NUMBER,
        reply_markup=await back_ui(),
    )
