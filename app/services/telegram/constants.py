# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / SERVICES / TELEGRAM / CONSTANTS
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for constants.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.config import settings

# ============================================
# 🌐 TELEGRAM API CONSTANTS
# ============================================

BASE_URL: str = f"https://api.telegram.org/bot{settings.BOT_TOKEN}"

PARSE_MODE: str = "HTML"

MAX_RETRIES: int = 3
