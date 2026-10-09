# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / CORE / SECURITY / FRAUD STORAGE
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for fraud storage.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.redis_client import redis_client
from app.core.logger import logger


class FraudStorage:

    PREFIX = "fraud"

    # ==========================================
    # ➕ ADD FRAUD SCORE
    # إضافة نقاط احتيال للمستخدم
    # ==========================================

    # ==============================================
    # ADD SCORE
    # ==============================================

    @classmethod
    async def add_score(cls: type, *, chat_id: int, score: int) -> None:

        # ======================================
        # 🚫 REDIS NOT AVAILABLE
        # ======================================

        if not redis_client:

            logger.warning(
                "fraud_storage_redis_unavailable", extra={"chat_id": chat_id}
            )

            return

        key = f"{cls.PREFIX}:{chat_id}"

        await redis_client.incrby(
            key,
            score,
        )

        await redis_client.expire(
            key,
            86400,
        )

        logger.info(
            "fraud_score_added",
            extra={
                "chat_id": chat_id,
                "score_added": score,
            },
        )

    # ==========================================
    # 📊 GET FRAUD SCORE
    # جلب نقاط الاحتيال الحالية
    # ==========================================

    # ==============================================
    # GET SCORE
    # ==============================================

    @classmethod
    async def get_score(cls: type, *, chat_id: int) -> int:

        # ======================================
        # 🚫 REDIS NOT AVAILABLE
        # ======================================

        if not redis_client:

            logger.warning(
                "fraud_storage_redis_unavailable", extra={"chat_id": chat_id}
            )

            return 0

        key = f"{cls.PREFIX}:{chat_id}"

        score = await redis_client.get(key)

        current_score = int(score) if score else 0

        return current_score

    # ==========================================
    # 🧹 RESET FRAUD SCORE
    # تصفير نقاط الاحتيال
    # ==========================================

    # ==============================================
    # RESET
    # ==============================================

    @classmethod
    async def reset(cls: type, *, chat_id: int) -> None:

        # ======================================
        # 🚫 REDIS NOT AVAILABLE
        # ======================================

        if not redis_client:

            logger.warning(
                "fraud_storage_redis_unavailable", extra={"chat_id": chat_id}
            )

            return

        await redis_client.delete(f"{cls.PREFIX}:{chat_id}")

        logger.info("fraud_score_reset", extra={"chat_id": chat_id})
