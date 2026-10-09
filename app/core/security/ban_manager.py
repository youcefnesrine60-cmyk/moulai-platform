# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / CORE / SECURITY / BAN MANAGER
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for ban manager.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.logger import logger
from app.core.redis_client import redis_client

# ==============================================
# 🚫 BAN MANAGER
# ==============================================


class BanManager:

    PREFIX = "banned"

    # ==========================================
    # 🔨 BAN USER
    # ==========================================

    @classmethod
    async def ban(
        cls,
        *,
        chat_id: int,
        ttl: int = 3600,
    ) -> None:

        if redis_client is None:
            logger.warning(
                "redis_client_not_initialized",
            )
            return

        await redis_client.setex(
            f"{cls.PREFIX}:{chat_id}",
            ttl,
            "1",
        )

        logger.warning(
            "user_banned",
            extra={
                "chat_id": chat_id,
                "ttl": ttl,
            },
        )

    # ==========================================
    # ✅ UNBAN USER
    # ==========================================

    @classmethod
    async def unban(
        cls,
        *,
        chat_id: int,
    ) -> None:

        if redis_client is None:
            logger.warning(
                "redis_client_not_initialized",
            )
            return

        await redis_client.delete(
            f"{cls.PREFIX}:{chat_id}",
        )

        logger.info(
            "user_unbanned",
            extra={
                "chat_id": chat_id,
            },
        )

    # ==========================================
    # 🚫 CHECK BAN
    # ==========================================

    @classmethod
    async def is_banned(
        cls,
        *,
        chat_id: int,
    ) -> bool:

        if redis_client is None:
            logger.warning(
                "redis_client_not_initialized",
            )
            return False

        banned = bool(
            await redis_client.exists(
                f"{cls.PREFIX}:{chat_id}",
            )
        )

        if banned:

            logger.warning(
                "banned_user_attempt",
                extra={
                    "chat_id": chat_id,
                },
            )

        return banned
