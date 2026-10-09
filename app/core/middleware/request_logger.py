# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / CORE / MIDDLEWARE / REQUEST LOGGER
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for request logger.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.logger import logger

# ==========================================
# 📜 REQUEST LOGGER
# ==========================================


class RequestLogger:

    # ==============================================
    # LOG
    # ==============================================

    @staticmethod
    async def log(*, chat_id: int, update_type: str) -> None:

        logger.info(
            "request_received",
            extra={"chat_id": chat_id, "event": update_type, "order_id": "-"},
        )
