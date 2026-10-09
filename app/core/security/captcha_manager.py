# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / CORE / SECURITY / CAPTCHA MANAGER
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for captcha manager.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.logger import logger
from app.core.redis_client import redis_client

# ==============================================
# 🧩 CAPTCHA MANAGER
# ==============================================


class CaptchaManager:

    PREFIX = "captcha"
    ANSWER_PREFIX = "captcha_answer"
    TTL = 300

    # ==========================================
    # ➕ REQUIRE CAPTCHA
    # ==========================================

    @classmethod
    async def require(
        cls,
        *,
        chat_id: int,
        answer: str,
    ) -> None:

        if redis_client is None:
            logger.warning("captcha_redis_unavailable")
            return

        redis_client.setex(
            f"{cls.PREFIX}:{chat_id}",
            cls.TTL,
            "1",
        )

        redis_client.setex(
            f"{cls.ANSWER_PREFIX}:{chat_id}",
            cls.TTL,
            str(answer),
        )

        logger.info(
            "captcha_required",
            extra={
                "chat_id": chat_id,
            },
        )

    # ==========================================
    # 🔍 CHECK CAPTCHA REQUIRED
    # ==========================================

    @classmethod
    async def is_required(
        cls,
        *,
        chat_id: int,
    ) -> bool:

        if redis_client is None:
            logger.warning("captcha_redis_unavailable")
            return False

        required = bool(
            redis_client.exists(
                f"{cls.PREFIX}:{chat_id}",
            )
        )

        logger.info(
            "captcha_requirement_checked",
            extra={
                "chat_id": chat_id,
                "required": required,
            },
        )

        return required

    # ==========================================
    # ✅ VERIFY CAPTCHA
    # ==========================================

    @classmethod
    async def verify(
        cls,
        *,
        chat_id: int,
        user_answer: str,
    ) -> bool:

        if redis_client is None:
            logger.warning("captcha_redis_unavailable")
            return False

        saved = redis_client.get(
            f"{cls.ANSWER_PREFIX}:{chat_id}",
        )

        if not saved:
            logger.warning(
                "captcha_answer_missing",
                extra={
                    "chat_id": chat_id,
                },
            )
            return False

        if isinstance(saved, bytes):
            saved = saved.decode()

        verified = str(saved) == str(user_answer)

        logger.info(
            "captcha_verified",
            extra={
                "chat_id": chat_id,
                "success": verified,
            },
        )

        return verified

    # ==========================================
    # 🧹 CLEAR CAPTCHA
    # ==========================================

    @classmethod
    async def clear(
        cls,
        *,
        chat_id: int,
    ) -> None:

        if redis_client is None:
            logger.warning("captcha_redis_unavailable")
            return

        redis_client.delete(
            f"{cls.PREFIX}:{chat_id}",
            f"{cls.ANSWER_PREFIX}:{chat_id}",
        )

        logger.info(
            "captcha_cleared",
            extra={
                "chat_id": chat_id,
            },
        )
