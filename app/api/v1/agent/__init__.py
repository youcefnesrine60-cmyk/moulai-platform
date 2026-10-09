# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🤖 AGENT API - PACKAGE INIT
# ==============================================

"""Package initializer and public module exports.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.api.v1.agent.agent import router as agent_router
from app.api.v1.agent.channel import router as channel_router
from app.api.v1.agent.conversation import router as conversation_router
from app.api.v1.agent.message import router as message_router

# ==============================================
# 📤 EXPORTS
# ==============================================

__all__ = [
    "agent_router",
    "channel_router",
    "conversation_router",
    "message_router",
]
