# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HANDLERS / OWNER_HANDLER / PHONE STEP
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for phone step.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from typing import Any

from app.core.logger import logger

from app.helpers.state_transition import transition_to
from app.helpers.ui_manager import UIManager

from app.services.validation import (
    normalize_phone,
    validate_phone,
)

from app.states.owner_states import OwnerStates

from app.views.ui import (
    back_ui,
    confirm_ui,
)

# ==============================================
# 🧩 TYPES
# ==============================================

StateData = dict[str, Any]

# ==============================================
# 📞 HANDLE PHONE STEP
# ==============================================


async def handle_phone_step(
    *,
    chat_id: int,
    text: str,
    state: StateData,
) -> None:

    # ==========================================
    # ☎️ NORMALIZE PHONE
    # ==========================================

    normalized_phone = await normalize_phone(
        text=text,
    )

    # ==========================================
    # 🚫 INVALID PHONE
    # ==========================================

    if not await validate_phone(
        text=normalized_phone,
        chat_id=chat_id,
    ):
        logger.warning(
            "invalid_phone",
            extra={
                "chat_id": chat_id,
            },
        )

        await UIManager.update(
            chat_id=chat_id,
            text=("❌ رقم الهاتف غير صحيح.\n\n" "📞 مثال صحيح:\n" "0551234567"),
            reply_markup=await back_ui(),
        )

        return

    # ==========================================
    # 💾 SAVE STATE
    # ==========================================

    state["phone"] = normalized_phone

    # ==========================================
    # 🔄 TRANSITION
    # ==========================================

    if not await transition_to(
        chat_id=chat_id,
        state=state,
        next_state=OwnerStates.CONFIRM,
    ):
        logger.error(
            "phone_transition_failed",
            extra={
                "chat_id": chat_id,
            },
        )
        return

    # ==========================================
    # ⚠️ SHOW CONFIRMATION
    # ==========================================

    await UIManager.update(
        chat_id=chat_id,
        text="⚠️ هل تؤكد عملية التسجيل؟",
        reply_markup=await confirm_ui(),
    )
