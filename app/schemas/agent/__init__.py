# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🤖 AGENT SCHEMAS - PACKAGE INIT
# ==============================================

"""Package initializer and public module exports.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.schemas.agent.agent import (
    AgentBase,
    AgentCreate,
    AgentUpdate,
    AgentConfigUpdate,
    AgentResponse,
    AgentListResponse,
    AgentStatistics,
    AgentData,
    AgentUpdateData,
    AgentListData,
)

from app.schemas.agent.channel import (
    ChannelBase,
    ChannelCreate,
    ChannelUpdate,
    ChannelResponse,
    ChannelListResponse,
    ChannelData,
    ChannelUpdateData,
    ChannelListData,
)

from app.schemas.agent.conversation import (
    ConversationBase,
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ConversationListResponse,
    ConversationStatistics,
    ConversationData,
    ConversationUpdateData,
    ConversationListData,
)

from app.schemas.agent.message import (
    MessageBase,
    MessageCreate,
    MessageUpdate,
    MessageResponse,
    MessageListResponse,
    MessageData,
    MessageUpdateData,
    MessageListData,
)

# ==============================================
# 📤 EXPORTS
# ==============================================

__all__ = [
    # Agent
    "AgentBase",
    "AgentCreate",
    "AgentUpdate",
    "AgentConfigUpdate",
    "AgentResponse",
    "AgentListResponse",
    "AgentStatistics",
    "AgentData",
    "AgentUpdateData",
    "AgentListData",
    # Channel
    "ChannelBase",
    "ChannelCreate",
    "ChannelUpdate",
    "ChannelResponse",
    "ChannelListResponse",
    "ChannelData",
    "ChannelUpdateData",
    "ChannelListData",
    # Conversation
    "ConversationBase",
    "ConversationCreate",
    "ConversationUpdate",
    "ConversationResponse",
    "ConversationListResponse",
    "ConversationStatistics",
    "ConversationData",
    "ConversationUpdateData",
    "ConversationListData",
    # Message
    "MessageBase",
    "MessageCreate",
    "MessageUpdate",
    "MessageResponse",
    "MessageListResponse",
    "MessageData",
    "MessageUpdateData",
    "MessageListData",
]
