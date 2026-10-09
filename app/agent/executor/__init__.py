# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# ⚡ EXECUTOR MODULE
# وحدة تنفيذ الإجراءات
# ==============================================

"""Package initializer and public module exports.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.agent.executor.actions import (
    BaseAction,
    ActionResponse,
    ActionResult,
    ActionRegistry,
    action_registry,
    get_action,
    get_action_by_intent,
    # Actions
    OrderFoodAction,
    ViewMenuAction,
    ViewRestaurantsAction,
    ModifyOrderAction,
    CancelOrderAction,
    TrackOrderAction,
    AskPriceAction,
    AskOfferAction,
    ComplaintAction,
    HelpAction,
    GreetingAction,
    GoodbyeAction,
)

from app.agent.executor.action_executor import (
    ActionExecutor,
    action_executor,
    execute_action,
    ExecutionResult,
    ActionContext,
)

# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    # Base
    "BaseAction",
    "ActionResponse",
    "ActionResult",
    # Registry
    "ActionRegistry",
    "action_registry",
    "get_action",
    "get_action_by_intent",
    # Actions
    "OrderFoodAction",
    "ViewMenuAction",
    "ViewRestaurantsAction",
    "ModifyOrderAction",
    "CancelOrderAction",
    "TrackOrderAction",
    "AskPriceAction",
    "AskOfferAction",
    "ComplaintAction",
    "HelpAction",
    "GreetingAction",
    "GoodbyeAction",
    # Executor
    "ActionExecutor",
    "action_executor",
    "execute_action",
    "ExecutionResult",
    "ActionContext",
]
