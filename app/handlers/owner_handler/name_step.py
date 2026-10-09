# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HANDLERS / OWNER_HANDLER / NAME STEP
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for name step.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from typing import Any

from app.core.logger import logger

from app.helpers.ui_helpers import send_restaurant_name
from app.helpers.safe_sanitize import safe_sanitize
from app.helpers.state_helper import get_user_state, update_state_field
from app.helpers.state_transition import transition_to
from app.helpers.ui_manager import UIManager

from app.states.owner_states import OwnerStates

from app.views.ui import back_ui

# ==============================================
# 🧩 TYPES
# ==============================================

StateData = dict[str, Any]


# ==============================================
# 👤 HANDLE OWNER NAME STEP
# ==============================================


async def handle_name_step(
    *,
    chat_id: int,
    text: str,
    state: StateData,
    message_id: int,
) -> None:
    """
    معالجة إدخال اسم المالك

    Args:
        chat_id: معرف المستخدم
        text: النص المدخل
        state: حالة المستخدم الحالية
        message_id: معرف رسالة المستخدم (تبقى ظاهرة)
    """
    logger.info(
        "handle_name_step",
        extra={
            "chat_id": chat_id,
            "text_length": len(text),
        },
    )

    # ==========================================
    # 💾 تخزين معرف رسالة المستخدم (لحذفها عند الرجوع)
    # ==========================================

    await update_state_field(
        chat_id=chat_id,
        key="user_message_id_name",
        value=message_id,
    )

    logger.debug(
        "user_message_id_name_stored",
        extra={
            "chat_id": chat_id,
            "message_id": message_id,
        },
    )

    # ==========================================
    # 🧼 SANITIZE INPUT
    # ==========================================

    clean = safe_sanitize(
        chat_id=chat_id,
        text=text,
        field="owner",
    )

    # ==========================================
    # 🚫 INVALID INPUT
    # ==========================================

    if clean is None:
        logger.warning(
            "invalid_owner_name",
            extra={
                "chat_id": chat_id,
            },
        )

        bot_message_id = state.get("bot_message_id")

        if bot_message_id:
            await UIManager.edit(
                chat_id=chat_id,
                message_id=bot_message_id,
                text="❌ الاسم غير صالح. يرجى إدخال اسم صحيح.",
                reply_markup=await back_ui(),
            )
        else:
            await UIManager.send_new_message(
                chat_id=chat_id,
                text="❌ الاسم غير صالح. يرجى إدخال اسم صحيح.",
                reply_markup=await back_ui(),
            )
        return

    # ==========================================
    # 💾 SAVE STATE
    # ==========================================

    await update_state_field(
        chat_id=chat_id,
        key="owner",
        value=clean,
    )

    logger.info(
        "owner_name_saved",
        extra={
            "chat_id": chat_id,
            "owner_name": clean,
        },
    )

    # ==========================================
    # 🔄 TRANSITION TO RESTAURANT STEP
    # ==========================================

    # ✅ جلب الحالة المحدثة من Redis
    state = await get_user_state(chat_id=chat_id)

    if not await transition_to(
        chat_id=chat_id,
        state=state,
        next_state=OwnerStates.RESTAURANT,
    ):
        logger.error(
            "owner_transition_to_restaurant_failed",
            extra={
                "chat_id": chat_id,
            },
        )
        return

    # ==========================================
    # 🍽️ SEND RESTAURANT NAME SCREEN
    # ==========================================

    bot_message_id = state.get("bot_message_id")

    if not bot_message_id:
        logger.warning(
            "bot_message_id_not_found_using_user_message_id",
            extra={
                "chat_id": chat_id,
                "message_id": message_id,
            },
        )
        bot_message_id = message_id

    restaurant_message_id = await send_restaurant_name(
        chat_id=chat_id,
        message_id=bot_message_id,
    )

    if restaurant_message_id:
        await update_state_field(
            chat_id=chat_id,
            key="restaurant_message_id",
            value=restaurant_message_id,
        )

        logger.info(
            "restaurant_message_id_saved",
            extra={
                "chat_id": chat_id,
                "restaurant_message_id": restaurant_message_id,
            },
        )
