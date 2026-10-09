# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / CORE / SECURITY / FRAUD DETECTOR
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for fraud detector.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.security.fraud_storage import FraudStorage
from app.core.security.fraud_score import FraudScore
from app.core.security.ban_manager import BanManager
from app.core.security.captcha_manager import CaptchaManager
from app.core.logger import logger


class FraudDetector:

    # ==============================================
    # FLAG
    # ==============================================

    @classmethod
    async def flag(cls: type, *, chat_id: int, severity: int) -> None:

        logger.info(
            "fraud_flag_received", extra={"chat_id": chat_id, "severity": severity}
        )

        await FraudStorage.add_score(chat_id=chat_id, score=severity)

        total = await FraudStorage.get_score(chat_id=chat_id)

        # ======================================
        # 🚫 CAPTCHA
        # ======================================

        if total >= FraudScore.MEDIUM:

            logger.info(
                "fraud_medium_detected",
                extra={"chat_id": chat_id, "total_score": total},
            )

            await CaptchaManager.require(chat_id=chat_id)

        # ======================================
        # 🚫 TEMP BAN
        # ======================================

        if total >= FraudScore.HIGH:

            logger.info(
                "fraud_high_detected", extra={"chat_id": chat_id, "total_score": total}
            )

            await BanManager.ban(chat_id=chat_id, ttl=3600)

        # ======================================
        # 🚫 PERMANENT-LIKE BAN
        # ======================================

        if total >= FraudScore.CRITICAL:

            logger.info(
                "fraud_critical_detected",
                extra={"chat_id": chat_id, "total_score": total},
            )

            await BanManager.ban(chat_id=chat_id, ttl=86400 * 30)
