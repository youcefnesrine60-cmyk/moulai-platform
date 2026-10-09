# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / CORE / MIDDLEWARE / TRACING
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for tracing.

Part of MoulAI Platform - Agent-as-a-Service.
"""

import uuid

from app.core.logger import logger

# ==============================================
# 🆔 TRACE
# ==============================================


class Trace:

    # ==============================================
    # GENERATE
    # ==============================================

    @staticmethod
    def generate() -> str:

        trace_id = str(uuid.uuid4())

        logger.info(
            "trace_generated",
            extra={
                "trace_id": trace_id,
            },
        )

        return trace_id
