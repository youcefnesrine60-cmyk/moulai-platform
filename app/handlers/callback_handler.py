# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HANDLERS / CALLBACK HANDLER
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for callback handler.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.logger import logger
from app.core.router_instance import router
from app.services.telegram import answer_callback

# ==============================================
# 📌 HANDLE CALLBACK
# ==============================================


async def handle_callback(
    *,
    data: dict,
) -> None:

    # ==========================================
    # 📦 EXTRACT CALLBACK QUERY
    # ==========================================

    query = data["callback_query"]

    chat_id = query["message"]["chat"]["id"]
    message_id = query["message"]["message_id"]
    callback_id = query["id"]
    callback_data = query["data"]

    logger.info(
        "callback_received",
        extra={
            "chat_id": chat_id,
            "callback_data": callback_data,
        },
    )

    # ==========================================
    # ☑️ ANSWER CALLBACK
    # ==========================================

    await answer_callback(
        callback_id=callback_id,
    )

    # ==========================================
    # 🚀 DISPATCH CALLBACK
    # ==========================================

    # ✅ استدعاء dispatch مع المعاملات المسماه
    await router.dispatch(
        callback_data=callback_data,
        chat_id=chat_id,
        message_id=message_id,
    )

    logger.info(
        "callback_dispatched",
        extra={
            "chat_id": chat_id,
            "callback_data": callback_data,
        },
    )
