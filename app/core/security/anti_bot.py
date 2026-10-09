# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / CORE / SECURITY / ANTI BOT
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for anti bot.

Part of MoulAI Platform - Agent-as-a-Service.
"""

import time

from app.core.logger import logger
from app.core.limiter.sliding_window import SlidingWindowLimiter
from app.core.redis_client import redis_client

# =========================================
# 🤖 ANTI BOT
# =========================================


class AntiBot:

    PREFIX = "bot"

    FAST_LIMIT = 5

    FAST_WINDOW = 2

    MIN_HUMAN_DELAY = 0.35

    # =====================================
    # 🤖 CHECK USER BEHAVIOR
    # =====================================

    @classmethod
    async def check(cls, *, chat_id: int) -> bool:

        # ==================================
        # 🚫 BURST DETECTION
        # ==================================

        allowed = await SlidingWindowLimiter.is_allowed(
            key=f"{cls.PREFIX}:burst:{chat_id}",
            limit=cls.FAST_LIMIT,
            window=cls.FAST_WINDOW,
        )

        if not allowed:

            logger.warning("burst_detected", extra={"chat_id": chat_id})

            return False

        # ==================================
        # 🚫 REDIS UNAVAILABLE
        # ==================================

        if not redis_client:

            logger.warning("redis_client_not_initialized", extra={"chat_id": chat_id})

            return True

        try:

            # ==============================
            # 🚫 HUMAN SPEED DETECTION
            # ==============================

            key = f"{cls.PREFIX}:human:{chat_id}"

            now = time.time()

            last = redis_client.get(key)

            redis_client.setex(key, 10, str(now))

            if not last:

                logger.info("first_interaction_recorded", extra={"chat_id": chat_id})

                return True

            diff = now - float(last)

            if diff < cls.MIN_HUMAN_DELAY:

                logger.warning(
                    "bot_like_speed_detected", extra={"chat_id": chat_id, "delay": diff}
                )

                return False

            return True

        except Exception as e:

            logger.exception(
                "anti_bot_check_failed", extra={"chat_id": chat_id, "error": str(e)}
            )

            return True
