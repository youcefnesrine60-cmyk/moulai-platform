# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HELPERS / STATE TRANSITION
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for state transition.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from typing import Any

from app.core.logger import logger

from app.helpers.state_machine import can_transition
from app.repositories.state_repo import set_state

# ==============================================
# 🧩 TYPES
# ==============================================

StateData = dict[str, Any]

# ==============================================
# 🔄 TRANSITION TO NEXT STATE
# ==============================================


async def transition_to(
    *,
    chat_id: int,
    state: StateData,
    next_state: str,
) -> bool:

    # ==========================================
    # 📥 CURRENT STATE
    # ==========================================

    current = state["step"]

    # ==========================================
    # 🚫 INVALID TRANSITION
    # ==========================================

    if not await can_transition(
        current_state=current,
        next_state=next_state,
    ):
        logger.warning(
            "invalid_state_transition",
            extra={
                "chat_id": chat_id,
                "from": current,
                "to": next_state,
            },
        )
        return False

    # ==========================================
    # 📚 SAVE HISTORY
    # ==========================================

    state.setdefault(
        "history",
        [],
    ).append(current)

    # ==========================================
    # 🔄 UPDATE STEP
    # ==========================================

    state["step"] = next_state

    # ==========================================
    # 💾 SAVE STATE
    # ==========================================

    await set_state(
        chat_id=chat_id,
        state=state,
    )

    # ==========================================
    # ✅ SUCCESS
    # ==========================================

    logger.info(
        "state_transition_completed",
        extra={
            "chat_id": chat_id,
            "from": current,
            "to": next_state,
        },
    )

    return True
