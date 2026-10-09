# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / CORE / SECURITY / CAPTCHA GENERATOR
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for captcha generator.

Part of MoulAI Platform - Agent-as-a-Service.
"""

import random

from app.core.logger import logger

# ==============================================
# 🧩 CAPTCHA GENERATOR
# مسؤول عن إنشاء اختبار CAPTCHA بسيط
# للتحقق من أن المستخدم ليس روبوتاً.
# ==============================================


class CaptchaGenerator:

    # ==========================================
    # ➕ GENERATE CAPTCHA
    # إنشاء سؤال CAPTCHA وإرجاع السؤال والإجابة
    # ==========================================

    # ==============================================
    # GENERATE
    # ==============================================

    @classmethod
    def generate(
        cls,
    ) -> dict[str, object]:

        # ======================================
        # 🎲 GENERATE RANDOM NUMBERS
        # ======================================

        a = random.randint(1, 9)
        b = random.randint(1, 9)

        # ======================================
        # ➕ CALCULATE ANSWER
        # ======================================

        answer = a + b

        # ======================================
        # 📝 BUILD QUESTION
        # ======================================

        question = "🤖 تحقق أمني\n\n" "ما نتيجة:\n\n" f"{a} + {b} = ؟"

        # ======================================
        # 📝 LOG GENERATED CAPTCHA
        # ======================================

        logger.info(
            "captcha_generated", extra={"question": question, "answer": str(answer)}
        )

        # ======================================
        # 📤 RETURN CAPTCHA
        # ======================================

        return {
            "question": question,
            "answer": str(answer),
        }
