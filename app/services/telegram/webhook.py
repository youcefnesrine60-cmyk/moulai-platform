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

    return await _post(method="setWebhook", data={"url": url})
