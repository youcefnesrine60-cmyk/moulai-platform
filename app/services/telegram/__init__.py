# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# PACKAGE INITIALIZER - APP / SERVICES / TELEGRAM /   INIT
# Package initialization and public exports component.
# ==============================================

"""Package initializer and public module exports.

Part of MoulAI Platform - Agent-as-a-Service.
"""

# ============================================
# 🤖 TELEGRAM SERVICE EXPORTS
# ============================================

from app.services.telegram.telegram_client import (
    send_message,
    edit_message,
    delete_message,
)
from app.services.telegram.callbacks import answer_callback
from app.services.telegram.webhook import set_webhook
from app.services.telegram.actions import send_chat_action
from app.services.telegram.client import close_http_client

# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "send_message",
    "edit_message",
    "delete_message",
    "answer_callback",
    "set_webhook",
    "send_chat_action",
    "close_http_client",
]
