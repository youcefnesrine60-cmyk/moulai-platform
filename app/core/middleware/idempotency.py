# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / CORE / MIDDLEWARE / IDEMPOTENCY
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for idempotency.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.logger import logger
from app.core.redis_client import redis_client

# =====================================
# 🔒 IDEMPOTENCY
# =====================================


class Idempotency:

    PREFIX = "idempotency"

    # ==============================================
    # PROTECT
    # ==============================================

    @staticmethod
    async def protect(*, key: str, ttl: int = 30) -> bool:

        # ==================================
        # 🚫 REDIS UNAVAILABLE
        # ==================================

        if not redis_client:

            logger.warning("redis_client_not_initialized", extra={"key": key})

            return True

        # ==================================
        # 🔑 BUILD KEY
        # ==================================

        redis_key = f"{Idempotency.PREFIX}:{key}"

        # ==================================
        # 🔒 ATOMIC PROTECTION
        # ==================================

        created = redis_client.set(redis_key, "1", ex=ttl, nx=True)

        if not created:

            logger.warning("idempotency_violation", extra={"key": key})

            return False

        # ==================================
        # ✅ PROTECTED
        # ==================================

        logger.info("idempotency_created", extra={"key": key, "ttl": ttl})

        return True
