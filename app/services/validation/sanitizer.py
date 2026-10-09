# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🧼 SANITIZER SERVICE
# ==============================================

"""MoulAI operational module for sanitizer.

Part of MoulAI Platform - Agent-as-a-Service.
"""

import re

from app.core.logger import logger

from app.services.validation.text_rules import (
    MAX_DESCRIPTION_LENGTH,
    MAX_NAME_LENGTH,
    MAX_WILAYA_LENGTH,
)

# ==============================================
# 🧩 TYPES
# ==============================================

OptionalText = str | None

# ==============================================
# 🧩 REGEX PATTERNS
# ==============================================

RESTAURANT_PATTERN = re.compile(r"[^a-zA-Z0-9\u0600-\u06FF\s\-&']")

OWNER_PATTERN = re.compile(r"[^a-zA-Z\u0600-\u06FF\s\-']")

WILAYA_PATTERN = re.compile(r"[^a-zA-Z\u0600-\u06FF\s\-]")

DESCRIPTION_PATTERN = re.compile(r"[^a-zA-Z0-9\u0600-\u06FF\s\-\.,!?&':]")

MULTIPLE_SPACES_PATTERN = re.compile(r"\s+")

# ==============================================
# 🧼 BASE SANITIZER
# ==============================================


def _sanitize(
    *,
    text: OptionalText,
    pattern: re.Pattern[str],
    max_length: int,
    field: str,
    chat_id: int | None = None,
) -> OptionalText:

    # ==========================================
    # 🚫 NONE INPUT
    # ==========================================

    if text is None:

        logger.warning(
            "sanitize_none_input",
            extra={
                "chat_id": chat_id,
                "field": field,
            },
        )

        return None

    # ==========================================
    # 🚫 INVALID TYPE
    # ==========================================

    if not isinstance(text, str):

        logger.warning(
            "sanitize_invalid_type",
            extra={
                "chat_id": chat_id,
                "field": field,
                "input_type": type(text).__name__,
            },
        )

        return None

    # ==========================================
    # 🧹 REMOVE OUTER SPACES
    # ==========================================

    text = text.strip()

    # ==========================================
    # 🚫 EMPTY AFTER STRIP
    # ==========================================

    if not text:

        logger.warning(
            "sanitize_empty_after_strip",
            extra={
                "chat_id": chat_id,
                "field": field,
            },
        )

        return None

    # ==========================================
    # 🧼 REMOVE INVALID CHARACTERS
    # ==========================================

    text = pattern.sub(
        "",
        text,
    )

    # ==========================================
    # 🧼 NORMALIZE SPACES
    # ==========================================

    text = MULTIPLE_SPACES_PATTERN.sub(
        " ",
        text,
    )

    # ==========================================
    # 📏 LIMIT LENGTH
    # ==========================================

    text = text[:max_length].strip()

    # ==========================================
    # 🚫 TOO SHORT
    # ==========================================

    if len(text) < 2:

        logger.warning(
            "sanitize_too_short",
            extra={
                "chat_id": chat_id,
                "field": field,
            },
        )

        return None

    return text


# ==============================================
# 🍽️ RESTAURANT SANITIZER
# ==============================================


def sanitize_restaurant(
    *,
    text: OptionalText,
    chat_id: int | None = None,
) -> OptionalText:

    return _sanitize(
        text=text,
        pattern=RESTAURANT_PATTERN,
        max_length=MAX_NAME_LENGTH,
        field="restaurant",
        chat_id=chat_id,
    )


# ==============================================
# 👤 OWNER SANITIZER
# ==============================================


def sanitize_owner(
    *,
    text: OptionalText,
    chat_id: int | None = None,
) -> OptionalText:

    return _sanitize(
        text=text,
        pattern=OWNER_PATTERN,
        max_length=MAX_NAME_LENGTH,
        field="owner",
        chat_id=chat_id,
    )


# ==============================================
# 🗺️ WILAYA SANITIZER
# ==============================================


def sanitize_wilaya(
    *,
    text: OptionalText,
    chat_id: int | None = None,
) -> OptionalText:

    return _sanitize(
        text=text,
        pattern=WILAYA_PATTERN,
        max_length=MAX_WILAYA_LENGTH,
        field="wilaya",
        chat_id=chat_id,
    )


# ==============================================
# 📝 DESCRIPTION SANITIZER
# ==============================================


def sanitize_description(
    *,
    text: OptionalText,
    chat_id: int | None = None,
) -> OptionalText:

    return _sanitize(
        text=text,
        pattern=DESCRIPTION_PATTERN,
        max_length=MAX_DESCRIPTION_LENGTH,
        field="description",
        chat_id=chat_id,
    )
