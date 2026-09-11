# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📞 PHONE VALIDATION
# ==============================================

import re

from app.core.logger import logger

# ==============================================
# 🧩 CONSTANTS
# ==============================================

PHONE_CLEAN_PATTERN = re.compile(
    r"[\s\-\.\(\)]",
)

ALGERIAN_PHONE_PATTERN = re.compile(
    r"0[5-7]\d{8}",
)

INTERNATIONAL_PHONE_PATTERN = re.compile(
    r"\+?[1-9]\d{7,14}",
)

# ==============================================
# 📞 NORMALIZE PHONE
# ==============================================

async def normalize_phone(
    *,
    text: str,
) -> str:

    # ==========================================
    # 🧹 CLEAN INPUT
    # ==========================================

    phone = PHONE_CLEAN_PATTERN.sub(
        "",
        text.strip(),
    )

    # ==========================================
    # 🇩🇿 NORMALIZE ALGERIAN PREFIX
    # ==========================================

    if phone.startswith("+213"):
        return f"0{phone[4:]}"

    if phone.startswith("213"):
        return f"0{phone[3:]}"

    return phone

# ==============================================
# 📞 VALIDATE PHONE
# ==============================================

async def validate_phone(
    *,
    text: str | None,
    chat_id: int | None = None,
) -> bool:

    # ==========================================
    # 🚫 INVALID INPUT
    # ==========================================

    if text is None:
        logger.warning(
            "phone_none_input",
            extra={
                "chat_id": chat_id,
            },
        )
        return False

    if not isinstance(
        text,
        str,
    ):
        logger.warning(
            "phone_invalid_type",
            extra={
                "chat_id": chat_id,
                "input_type": type(text).__name__,
            },
        )
        return False

    # ==========================================
    # 📞 NORMALIZE PHONE
    # ==========================================

    try:
        phone = await normalize_phone(
            text=text,
        )

    except Exception:
        logger.exception(
            "phone_normalization_failed",
            extra={
                "chat_id": chat_id,
            },
        )
        return False

    # ==========================================
    # ✅ VALIDATE FORMAT
    # ==========================================

    is_valid = (
        ALGERIAN_PHONE_PATTERN.fullmatch(phone)
        is not None
        or INTERNATIONAL_PHONE_PATTERN.fullmatch(phone)
        is not None
    )

    if not is_valid:
        logger.warning(
            "phone_invalid_format",
            extra={
                "chat_id": chat_id,
            },
        )
        return False

    return True