# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / CORE / DISPATCHER
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for dispatcher.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.logger import logger

from app.handlers.callback_handler import handle_callback
from app.handlers.message_handler import handle_message
from app.handlers.webapp_handler import handle_webapp_data

# ==============================================
# 🧩 TYPES
# ==============================================

Update = dict[str, object]

# ==============================================
# 🚀 DISPATCH UPDATE
# ==============================================


async def dispatch_update(
    *,
    data: Update,
) -> None:

    try:

        # ======================================
        # 📌 CALLBACK QUERY
        # ======================================

        if "callback_query" in data:

            await handle_callback(
                data=data,
            )

            return

        # ======================================
        # 💬 MESSAGE
        # ======================================

        if "message" not in data:
            return

        message = data["message"]

        # ======================================
        # 🌍 WEBAPP DATA
        # ======================================

        if isinstance(message, dict) and "web_app_data" in message:

            await handle_webapp_data(
                data=data,
            )

            return

        # ======================================
        # 💬 NORMAL MESSAGE
        # ======================================

        await handle_message(
            data=data,
        )

    except Exception as e:

        logger.exception(
            "update_dispatch_failed",
            extra={
                "error": str(e),
            },
        )
