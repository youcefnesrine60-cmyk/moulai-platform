# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / CORE / LOGGER
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for logger.

Part of MoulAI Platform - Agent-as-a-Service.
"""

import logging
import sys

from pythonjsonlogger import json

# ==========================================
# SAFE JSON FORMATTER
# ==========================================


class SafeJsonFormatter(json.JsonFormatter):

    # ==============================================
    # ADD FIELDS
    # ==============================================

    def add_fields(
        self,
        log_record,
        record,
        message_dict,
    ) -> None:

        super().add_fields(
            log_record,
            record,
            message_dict,
        )

        # ==================================
        # SAFE DEFAULTS
        # ==================================

        log_record.setdefault("chat_id", "-")
        log_record.setdefault("event", "-")
        log_record.setdefault("order_id", "-")


# ==========================================
# LOGGER
# ==========================================

logger = logging.getLogger("MoulAI™ Platform - Agent-as-a-Service")
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)

formatter = SafeJsonFormatter(
    "%(asctime)s %(levelname)s %(event)s %(chat_id)s %(order_id)s %(message)s"
)

handler.setFormatter(formatter)

logger.addHandler(handler)
logger.propagate = False
