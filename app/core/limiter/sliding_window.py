# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / CORE / LIMITER / SLIDING WINDOW
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for sliding window.

Part of MoulAI Platform - Agent-as-a-Service.
"""

import time

from app.core.logger import logger
from app.core.redis_client import redis_client

# ==========================================
# 🚫 LUA SLIDING WINDOW LIMITER
# ==========================================

LUA_SCRIPT = """

local key = KEYS[1]

local now = tonumber(ARGV[1])

local window = tonumber(ARGV[2])

local limit = tonumber(ARGV[3])

-- remove old requests
redis.call(
    "ZREMRANGEBYSCORE",
    key,
    0,
    now - window
)

-- count current requests
local count = redis.call(
    "ZCARD",
    key
)

-- block
if count >= limit then
    return 0
end

-- add request
redis.call(
    "ZADD",
    key,
    now,
    tostring(now)
)

-- expire
redis.call(
    "EXPIRE",
    key,
    window
)

return 1
"""


# ==========================================
# 🚫 SLIDING WINDOW LIMITER
# ==========================================


class SlidingWindowLimiter:

    # ==============================================
    # IS ALLOWED
    # ==============================================

    @staticmethod
    async def is_allowed(*, key: str, limit: int, window: int) -> bool:

        # ==================================
        # 🚫 REDIS UNAVAILABLE
        # ==================================

        if not redis_client:

            logger.warning("redis_client_not_initialized", extra={"key": key})

            return True

        try:

            now = int(time.time())

            redis_key = f"limit:{key}"

            allowed = redis_client.eval(LUA_SCRIPT, 1, redis_key, now, window, limit)

            # ==============================
            # 🚫 RATE LIMITED
            # ==============================

            if allowed != 1:

                logger.warning(
                    "rate_limit_exceeded",
                    extra={"key": key, "limit": limit, "window": window},
                )

                return False

            return True

        except Exception as e:

            logger.exception(
                "sliding_window_limiter_failed", extra={"key": key, "error": str(e)}
            )

            return True
