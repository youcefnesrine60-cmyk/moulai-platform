# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / SERVICES / TELEGRAM / TELEGRAM CLIENT
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for telegram client.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.logger import logger

from app.services.telegram.base import _post
from app.services.telegram.constants import PARSE_MODE

# ============================================
# 🧩 TYPES
# ============================================

TelegramResponse = dict[str, object] | None
ReplyMarkup = dict[str, object] | None
TelegramPayload = dict[str, object]

# ============================================
# 💬 SEND MESSAGE
# ============================================


async def send_message(
    *,
    chat_id: int,
    text: str,
    reply_markup: ReplyMarkup = None,
) -> TelegramResponse:

    data: TelegramPayload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": PARSE_MODE,
        "disable_web_page_preview": True,
    }

    # ========================================
    # 🎛️ REPLY MARKUP
    # ========================================

    if reply_markup is not None:
        data["reply_markup"] = reply_markup

    logger.info(
        "message_sent",
        extra={
            "chat_id": chat_id,
        },
    )

    return await _post(
        method="sendMessage",
        data=data,
    )


# ============================================
# ✏️ EDIT MESSAGE
# ============================================


async def edit_message(
    *,
    chat_id: int,
    message_id: int,
    text: str,
    reply_markup: ReplyMarkup = None,
) -> TelegramResponse:

    data: TelegramPayload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": PARSE_MODE,
        "disable_web_page_preview": True,
    }

    # ========================================
    # 🎛️ REPLY MARKUP
    # ========================================

    if reply_markup is not None:
        data["reply_markup"] = reply_markup

    logger.info(
        "message_edited",
        extra={
            "chat_id": chat_id,
            "message_id": message_id,
        },
    )

    return await _post(
        method="editMessageText",
        data=data,
    )


# ============================================
# 🗑️ DELETE MESSAGE
# ============================================


async def delete_message(
    *,
    chat_id: int,
    message_id: int,
) -> TelegramResponse:

    logger.info(
        "message_deleted",
        extra={
            "chat_id": chat_id,
            "message_id": message_id,
        },
    )

    return await _post(
        method="deleteMessage",
        data={
            "chat_id": chat_id,
            "message_id": message_id,
        },
    )
