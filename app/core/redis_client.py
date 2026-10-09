# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / CORE / REDIS CLIENT
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for redis client.

Part of MoulAI Platform - Agent-as-a-Service.
"""

import os
import redis

from dotenv import load_dotenv
from app.core.logger import logger

# ==============================================
# 🌍 LOAD ENV
# ==============================================

load_dotenv()

# ==============================================
# 🌍 REDIS URL
# ==============================================

REDIS_URL = os.getenv("REDIS_URL")

# ==============================================
# 🧠 MEMORY STORAGE
# ==============================================

memory_storage = {}

# ==============================================
# 🔌 REDIS CONNECTION
# ==============================================

redis_client = None

if REDIS_URL:

    try:

        redis_client = redis.from_url(REDIS_URL, decode_responses=True)

        redis_client.ping()

        logger.info("Redis connected successfully.")

    except Exception as e:

        logger.warning(f"Redis unavailable: {e}")

        redis_client = None

else:

    logger.warning("REDIS_URL not found. Using memory storage.")
