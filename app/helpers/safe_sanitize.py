# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HELPERS / SAFE SANITIZE
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for safe sanitize.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from collections.abc import Callable

from app.core.logger import logger

from app.services.validation import (
    sanitize_description,
    sanitize_owner,
    sanitize_restaurant,
    sanitize_wilaya,
)

# ==============================================
# 🧩 TYPES
# ==============================================

Sanitizer = Callable[..., str | None]

# ==============================================
# 🧼 SANITIZER MAP
# ==============================================

SANITIZERS: dict[str, Sanitizer] = {
    "restaurant": sanitize_restaurant,
    "owner": sanitize_owner,
    "wilaya": sanitize_wilaya,
    "description": sanitize_description,
}

# ==============================================
# 🧼 SAFE SANITIZE
# ==============================================


def safe_sanitize(
    *,
    chat_id: int,
    text: str,
    field: str,
) -> str | None:

    sanitizer = SANITIZERS.get(field)

    # ==========================================
    # 🚫 UNKNOWN FIELD
    # ==========================================

    if sanitizer is None:

        logger.warning(
            "safe_sanitize_unknown_field",
            extra={
                "chat_id": chat_id,
                "field": field,
            },
        )

        return None

    # ==========================================
    # 🧼 SANITIZE
    # ==========================================

    try:

        return sanitizer(
            text=text,
            chat_id=chat_id,
        )

    # ==========================================
    # 🚫 UNEXPECTED ERROR
    # ==========================================

    except Exception:

        logger.exception(
            "safe_sanitize_failed",
            extra={
                "chat_id": chat_id,
                "field": field,
            },
        )

        return None
