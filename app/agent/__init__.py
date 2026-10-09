# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🤖 AGENT MODULE
# وحدة الوكيل الذكي
# ==============================================

"""Package initializer and public module exports.

Part of MoulAI Platform - Agent-as-a-Service.
"""

# ==============================================
# 📦 CONFIG
# ==============================================

from app.agent.config import (
    AgentConfig,
    LanguageConfig,
    default_config,
    language_config,
    LanguageCode,
    LanguageName,
    ConfidenceScore,
    get_language_name as config_get_language_name,
    is_language_supported,
    get_supported_languages,
    get_default_language,
)

# ==============================================
# 🌍 LANGUAGE
# ==============================================

from app.agent.language.detector import (
    LanguageDetector,
    detect_language,
    get_language_name as detector_get_language_name,
    LanguageDetectionResult,
)

# ==============================================
# 🧠 NLU
# ==============================================

from app.agent.nlu import (
    # Intent Classifier
    IntentClassifier,
    classify_intent,
    IntentResult,
    IntentEntityDict,
    # Entity Extractor
    EntityExtractor,
    extract_entities,
    ExtractionResult,
    EntityDict,
    EntityList,
)

# ==============================================
# ⚡ EXECUTOR
# ==============================================

from app.agent.executor import (
    # Base
    BaseAction,
    ActionResponse,
    ActionResult,
    # Registry
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
    # Executor
    ActionExecutor,
    action_executor,
    execute_action,
    ExecutionResult,
    ActionContext,
)

# ==============================================
# 🧠 MEMORY
# ==============================================

from app.agent.memory import (
    MemoryManager,
    memory_manager,
    get_session,
    add_message,
    SessionData,
    ContextData,
    ConversationHistory,
)

# ==============================================
# 🤖 ENGINE
# ==============================================

from app.agent.engine import (
    AgentEngine,
    agent_engine,
    process_message,
    ProcessResult,
    AgentResponse,
)

# ==============================================
# 💬 RESPONSE GENERATOR
# ==============================================

from app.agent.response_generator import (
    ResponseGenerator,
    response_generator,
    generate_response,
    ResponseContext,
    ResponseResult,
)

# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    # Config
    "AgentConfig",
    "LanguageConfig",
    "default_config",
    "language_config",
    "LanguageCode",
    "LanguageName",
    "ConfidenceScore",
    "config_get_language_name",
    "is_language_supported",
    "get_supported_languages",
    "get_default_language",
    # Language
    "LanguageDetector",
    "detect_language",
    "detector_get_language_name",
    "LanguageDetectionResult",
    # NLU - Intent Classifier
    "IntentClassifier",
    "classify_intent",
    "IntentResult",
    "IntentEntityDict",
    # NLU - Entity Extractor
    "EntityExtractor",
    "extract_entities",
    "ExtractionResult",
    "EntityDict",
    "EntityList",
    # Executor - Base
    "BaseAction",
    "ActionResponse",
    "ActionResult",
    # Executor - Registry
    "ActionRegistry",
    "action_registry",
    "get_action",
    "get_action_by_intent",
    # Executor - Actions
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
    # Executor - Executor
    "ActionExecutor",
    "action_executor",
    "execute_action",
    "ExecutionResult",
    "ActionContext",
    # Memory
    "MemoryManager",
    "memory_manager",
    "get_session",
    "add_message",
    "SessionData",
    "ContextData",
    "ConversationHistory",
    # Engine
    "AgentEngine",
    "agent_engine",
    "process_message",
    "ProcessResult",
    "AgentResponse",
    # Response Generator
    "ResponseGenerator",
    "response_generator",
    "generate_response",
    "ResponseContext",
    "ResponseResult",
]
