# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / SERVICES / TELEGRAM / WEBHOOK
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for webhook.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.logger import logger
from app.core.config import settings
from app.services.telegram.base import _post

# ============================================
# 🧩 TYPES
# ============================================

TelegramResponse = dict | None

# ============================================
# 🔗 SET WEBHOOK
# ============================================


async def set_webhook(
    *,
    url: str,
) -> TelegramResponse:

    # ========================================
    # 📝 LOG REQUEST
    # ========================================

    logger.info("setting_webhook", extra={"url": url})

    # ========================================
    # 🚀 CALL TELEGRAM API
    # ========================================

    secret = settings.TELEGRAM_WEBHOOK_SECRET_TOKEN
    if secret is None or not secret.get_secret_value():
        raise ValueError("telegram_webhook_not_configured")
    token = secret.get_secret_value()
    if not 1 <= len(token) <= 256 or any(
        not (ch.isascii() and (ch.isalnum() or ch in "_-")) for ch in token
    ):
        raise ValueError("invalid_telegram_webhook_token_format")
    return await _post(method="setWebhook", data={"url": url, "secret_token": token})
