# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# PACKAGE INITIALIZER - APP / REPOSITORIES /   INIT
# Package initialization and public exports component.
# ==============================================

"""Package initializer and public module exports.

Part of MoulAI Platform - Agent-as-a-Service.
"""

# 🤖 Agent
from app.repositories.agent import (
    AgentRepository,
    ChannelRepository,
    ConversationRepository,
    MessageRepository,
)

# 🏪 RESTAURANT
from app.repositories.restaurant import (
    RestaurantRepository,
    RestaurantBranchRepository,
    RestaurantMetricsRepository,
    RestaurantGroupRepository,
    RestaurantOrderCountersRepository,
    RestaurantPaymentSettingsRepository,
)

# 👑 ADMIN REPOSITORY

from app.repositories.admin import (
    AdminRepository,
    AdminLogRepository,
    AdminSessionsRepository,
)

# ==============================================
# 📤 EXPORTS
# ==============================================

__all__ = [
    # Agent
    "AgentRepository",
    "ChannelRepository",
    "ConversationRepository",
    "MessageRepository",
    # Restaurant
    "RestaurantRepository",
    "RestaurantBranchRepository",
    "RestaurantMetricsRepository",
    "RestaurantGroupRepository",
    "RestaurantOrderCountersRepository",
    "RestaurantPaymentSettingsRepository",
    # "RestaurantMenuRepository"
    # Admin
    "AdminRepository",
    "AdminLogRepository",
    "AdminSessionsRepository",
]
