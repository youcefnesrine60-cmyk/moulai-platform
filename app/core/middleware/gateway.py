# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / CORE / MIDDLEWARE / GATEWAY
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for gateway.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.logger import logger


class GatewayMiddleware:

    # ==============================================
    # PROCESS
    # ==============================================

    @staticmethod
    async def process(*, chat_id: int) -> bool:

        # ======================================
        # TEMPORARY:
        # Redis limiter disabled
        # ======================================

        logger.info(
            "gateway_processed",
            extra={
                "chat_id": chat_id,
            },
        )

        return True
