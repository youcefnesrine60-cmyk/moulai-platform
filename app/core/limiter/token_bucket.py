# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / CORE / LIMITER / TOKEN BUCKET
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for token bucket.

Part of MoulAI Platform - Agent-as-a-Service.
"""

import time

from app.core.logger import logger
from app.core.redis_client import memory_storage
from app.core.redis_client import redis_client

# ==============================================
# 🧩 TYPES
# ==============================================

BucketData = dict[str, float]


# ==============================================
# 🚦 TOKEN BUCKET
# ==============================================


class TokenBucket:

    # ==============================================
    # ALLOW
    # ==============================================

    @staticmethod
    async def allow(*, key: str, capacity: int = 5, refill_rate: float = 1.0) -> bool:

        now = int(time.time())

        redis_key = f"bucket:{key}"

        # ======================================
        # 🔴 REDIS MODE
        # ======================================

        if redis_client:

            try:

                bucket = redis_client.hgetall(redis_key)

                if not bucket:

                    tokens = float(capacity)
                    last_refill = float(now)

                    logger.info("token_bucket_initialized", extra={"key": key})

                else:

                    tokens = float(bucket.get("tokens", 0))

                    last_refill = float(bucket.get("last_refill", now))

                # ==============================
                # ♻️ REFILL TOKENS
                # ==============================

                elapsed = now - last_refill

                tokens = min(capacity, tokens + elapsed * refill_rate)

                # ==============================
                # 🚫 LIMIT EXCEEDED
                # ==============================

                if tokens < 1:

                    logger.warning("token_bucket_exceeded", extra={"key": key})

                    return False

                tokens -= 1

                redis_client.hset(
                    redis_key, mapping={"tokens": tokens, "last_refill": now}
                )

                redis_client.expire(redis_key, 3600)

                return True

            except Exception as e:

                logger.exception(
                    "token_bucket_redis_failed", extra={"key": key, "error": str(e)}
                )

        # ======================================
        # 🧠 MEMORY FALLBACK
        # ======================================

        bucket: BucketData | None = memory_storage.get(redis_key)

        if not bucket:

            tokens = float(capacity)
            last_refill = float(now)

            logger.info("token_bucket_memory_initialized", extra={"key": key})

        else:

            tokens = bucket["tokens"]
            last_refill = bucket["last_refill"]

        # ======================================
        # ♻️ REFILL TOKENS
        # ======================================

        elapsed = now - last_refill

        tokens = min(capacity, tokens + elapsed * refill_rate)

        # ======================================
        # 🚫 LIMIT EXCEEDED
        # ======================================

        if tokens < 1:

            logger.warning("token_bucket_memory_exceeded", extra={"key": key})

            return False

        tokens -= 1

        memory_storage[redis_key] = {"tokens": tokens, "last_refill": float(now)}

        return True
