# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HELPERS / NAVIGATION
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for navigation.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from typing import Any

from app.core.logger import logger

from app.repositories.state_repo import (
    get_state,
    set_state,
)

from app.states.owner_states import OwnerStates

# ==============================================
# 🧹 STEP CLEANUP MAP
# ==============================================

STEP_CLEANUP: dict[str, list[str]] = {
    OwnerStates.NAME: [
        "owner",
        "restaurant",
        "wilaya",
        "lat",
        "lng",
        "type",
        "phone",
    ],
    OwnerStates.RESTAURANT: [
        "restaurant",
        "wilaya",
        "lat",
        "lng",
        "type",
        "phone",
    ],
    OwnerStates.WILAYA: [
        "wilaya",
        "lat",
        "lng",
        "type",
        "phone",
    ],
    OwnerStates.LOCATION: [
        "lat",
        "lng",
        "type",
        "phone",
    ],
    OwnerStates.TYPE: [
        "type",
        "phone",
    ],
    OwnerStates.PHONE: [
        "phone",
    ],
}


# ==============================================
# 🔙 GO BACK
# ==============================================


async def go_back(
    *,
    chat_id: int,
) -> str | None:
    """
    العودة إلى الخطوة السابقة في تدفق المستخدم

    Args:
        chat_id: معرف المستخدم

    Returns:
        str | None: اسم الخطوة السابقة أو None
    """
    state: dict[str, Any] | None = await get_state(
        chat_id=chat_id,
    )

    # ==========================================
    # 🚫 INVALID STATE
    # ==========================================

    if not state or not isinstance(state, dict):
        logger.warning(
            "navigation_invalid_state",
            extra={
                "chat_id": chat_id,
            },
        )
        return None

    history = state.get("history", [])

    # ==========================================
    # 🚫 INVALID HISTORY
    # ==========================================

    if not isinstance(history, list):
        logger.warning(
            "navigation_invalid_history",
            extra={
                "chat_id": chat_id,
            },
        )
        return None

    # ==========================================
    # 🚫 EMPTY HISTORY
    # ==========================================

    if not history:
        logger.info(
            "navigation_history_empty",
            extra={
                "chat_id": chat_id,
            },
        )
        return None

    # ==========================================
    # 🔙 PREVIOUS STEP
    # ==========================================

    previous_step = history.pop()

    state["history"] = history

    # ==========================================
    # 🧹 CLEAN DATA
    # ==========================================

    for key in STEP_CLEANUP.get(previous_step, []):
        state.pop(key, None)

    # ==========================================
    # 💾 UPDATE STEP
    # ==========================================

    state["step"] = previous_step

    # ==========================================
    # 💾 SAVE STATE
    # ==========================================

    await set_state(
        chat_id=chat_id,
        state=state,
    )

    logger.info(
        "navigation_back_success",
        extra={
            "chat_id": chat_id,
            "step": previous_step,
            "history_size": len(history),
        },
    )

    return previous_step
