# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / CORE / MIDDLEWARE / SECURITY
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for security.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.logger import logger


class SecurityMiddleware:

    BLOCKED_USERS = set()

    # ==============================================
    # CHECK
    # ==============================================

    @staticmethod
    async def check(*, chat_id: int) -> bool:

        logger.info("security_check", extra={"chat_id": chat_id})

        return chat_id not in SecurityMiddleware.BLOCKED_USERS
