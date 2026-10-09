# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🧠 MEMORY MODULE
# وحدة إدارة الذاكرة
# ==============================================

"""Package initializer and public module exports.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.agent.memory.memory_manager import (
    MemoryManager,
    memory_manager,
    get_session,
    add_message,
    SessionData,
    ContextData,
    ConversationHistory,
)

# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "MemoryManager",
    "memory_manager",
    "get_session",
    "add_message",
    "SessionData",
    "ContextData",
    "ConversationHistory",
]
