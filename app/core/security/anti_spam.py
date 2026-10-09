# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / CORE / SECURITY / ANTI SPAM
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for anti spam.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.limiter.sliding_window import SlidingWindowLimiter
from app.core.logger import logger

# ===================================
# 🚫 ANTI SPAM
# ===================================


class AntiSpam:

    PREFIX = "spam"

    LIMIT = 15

    WINDOW = 10

    # ===================================
    # 🚫 CHECK SPAM
    # ===================================

    @classmethod
    async def check(cls: type, *, chat_id: int) -> bool:

        logger.info("checking_for_spam", extra={"chat_id": chat_id})

        allowed = await SlidingWindowLimiter.is_allowed(
            key=f"{cls.PREFIX}:{chat_id}", limit=cls.LIMIT, window=cls.WINDOW
        )

        if not allowed:

            logger.warning("spam_detected", extra={"chat_id": chat_id})

        return allowed
