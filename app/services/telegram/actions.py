# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / SERVICES / TELEGRAM / ACTIONS
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for actions.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.logger import logger
from app.services.telegram.base import _post

# ============================================
# 🧩 TYPES
# ============================================

TelegramResponse = dict | None

# ============================================
# ⌨️ SEND TYPING ACTION
# ============================================


async def send_chat_action(*, chat_id: int, action: str = "typing") -> TelegramResponse:

    # ========================================
    # 📝 LOG REQUEST
    # ========================================

    logger.info("sending_chat_action", extra={"chat_id": chat_id, "action": action})

    # ========================================
    # 🚀 CALL TELEGRAM API
    # ========================================

    return await _post(
        method="sendChatAction", data={"chat_id": chat_id, "action": action}
    )
