# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / CORE / SECURITY / ABUSE DETECTOR
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for abuse detector.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.redis_client import redis_client
from app.core.logger import logger

# ==========================================
# 🚫 ABUSE DETECTOR
# ==========================================


class AbuseDetector:

    PREFIX = "abuse"

    LIMIT = 30

    WINDOW = 3600

    # ======================================
    # 🚫 FLAG USER
    # ======================================

    @classmethod
    async def flag(*, cls: type, chat_id: int, score: int = 1) -> int:

        if not redis_client:

            logger.warning(
                "Redis client is not initialized", extra={"chat_id": chat_id}
            )

            return 0

        key = f"{cls.PREFIX}:{chat_id}"

        count = redis_client.incrby(key, score)

        redis_client.expire(key, cls.WINDOW)

        logger.warning(
            "abuse_flagged", extra={"chat_id": chat_id, "score": score, "count": count}
        )

        return count

    # ======================================
    # 🚫 CHECK ABUSE
    # ======================================

    @classmethod
    async def is_abusive(*, cls: type, chat_id: int) -> bool:

        if not redis_client:

            logger.warning(
                "Redis client is not initialized", extra={"chat_id": chat_id}
            )

            return False

        key = f"{cls.PREFIX}:{chat_id}"

        count = redis_client.get(key)

        if not count:

            logger.info("No abuse detected", extra={"chat_id": chat_id})

            return False

        abusive = int(count) >= cls.LIMIT

        if abusive:

            logger.warning(
                "abusive_user_detected", extra={"chat_id": chat_id, "count": int(count)}
            )

        return abusive
