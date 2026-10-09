# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HANDLERS / CAPTCHA HANDLER
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for captcha handler.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from typing import Any

from app.core.logger import logger

from app.core.security.captcha_generator import CaptchaGenerator
from app.core.security.captcha_manager import CaptchaManager

from app.helpers.ui_manager import UIManager

# ==============================================
# 🧩 TYPES
# ==============================================

CaptchaData = dict[str, Any]

# ==============================================
# 🚀 SEND CAPTCHA CHALLENGE
# ==============================================


async def send_captcha(
    *,
    chat_id: int,
) -> None:

    # ==========================================
    # 🚀 START CAPTCHA CHALLENGE
    # ==========================================

    logger.info(
        "captcha_challenge_started",
        extra={
            "chat_id": chat_id,
        },
    )

    # ==========================================
    # 🤖 GENERATE CAPTCHA
    # ==========================================

    captcha: CaptchaData = CaptchaGenerator.generate()

    # ==========================================
    # 💾 STORE EXPECTED ANSWER
    # ==========================================

    await CaptchaManager.require(
        chat_id=chat_id,
        answer=captcha["answer"],
    )

    logger.info(
        "captcha_answer_stored",
        extra={
            "chat_id": chat_id,
        },
    )

    # ==========================================
    # 📤 SEND CAPTCHA TO USER
    # ==========================================

    await UIManager.update(
        chat_id=chat_id,
        text=captcha["question"],
        reply_markup=captcha.get("keyboard"),
    )


# ==============================================
# ✅ HANDLE CAPTCHA RESPONSE
# ==============================================


async def handle_captcha(
    *,
    chat_id: int,
    text: str,
) -> bool:

    # ==========================================
    # 🚫 INVALID INPUT
    # ==========================================

    if not text.isdigit():

        logger.warning(
            "captcha_invalid_input",
            extra={
                "chat_id": chat_id,
            },
        )

        await UIManager.update(
            chat_id=chat_id,
            text="⚠️ الرجاء إدخال الرقم الصحيح فقط.",
            reply_markup=None,
        )

        return False

    # ==========================================
    # 🔍 VERIFY ANSWER
    # ==========================================

    valid = await CaptchaManager.verify(
        chat_id=chat_id,
        user_answer=text,
    )

    # ==========================================
    # 🚫 WRONG ANSWER
    # ==========================================

    if not valid:

        logger.warning(
            "captcha_verification_failed",
            extra={
                "chat_id": chat_id,
            },
        )

        await UIManager.update(
            chat_id=chat_id,
            text="❌ إجابة خاطئة.\nحاول مرة أخرى.",
            reply_markup=None,
        )

        return False

    # ==========================================
    # 🧹 CLEAR CAPTCHA
    # ==========================================

    await CaptchaManager.clear(
        chat_id=chat_id,
    )

    # ==========================================
    # ✅ VERIFICATION SUCCESS
    # ==========================================

    logger.info(
        "captcha_verification_success",
        extra={
            "chat_id": chat_id,
        },
    )

    await UIManager.update(
        chat_id=chat_id,
        text="✅ تم التحقق بنجاح.",
        reply_markup=None,
    )

    return True
