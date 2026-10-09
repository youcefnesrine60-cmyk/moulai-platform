# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📝 PROMPTS MODULE
# وحدة قوالب الـ Prompts
# ==============================================

"""Package initializer and public module exports.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.agent.prompts.templates import (
    # Languages
    SUPPORTED_LANGUAGES,
    DEFAULT_LANGUAGE,
    # System
    SYSTEM_PROMPTS,
    get_system_prompt,
    # Classification
    INTENT_CLASSIFICATION_PROMPTS,
    get_intent_classification_prompt,
    # Response
    RESPONSE_GENERATION_PROMPTS,
    get_response_generation_prompt,
    # Entity Extraction
    ENTITY_EXTRACTION_PROMPTS,
    get_entity_extraction_prompt,
    # Confirmation
    CONFIRMATION_PROMPTS,
    get_confirmation_prompt,
    # Error
    ERROR_PROMPTS,
    get_error_prompt,
    # Success
    SUCCESS_PROMPTS,
    get_success_prompt,
)

from app.agent.prompts.translations import (
    SYSTEM_PROMPTS as SYSTEM_PROMPTS_TRANSLATIONS,
    INTENT_CLASSIFICATION_PROMPTS as INTENT_CLASSIFICATION_PROMPTS_TRANSLATIONS,
    RESPONSE_GENERATION_PROMPTS as RESPONSE_GENERATION_PROMPTS_TRANSLATIONS,
    GREETING_RESPONSES,
    GOODBYE_RESPONSES,
    HELP_RESPONSES,
    ERROR_RESPONSES,
)

# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    # Languages
    "SUPPORTED_LANGUAGES",
    "DEFAULT_LANGUAGE",
    # System
    "SYSTEM_PROMPTS",
    "get_system_prompt",
    # Classification
    "INTENT_CLASSIFICATION_PROMPTS",
    "get_intent_classification_prompt",
    # Response
    "RESPONSE_GENERATION_PROMPTS",
    "get_response_generation_prompt",
    # Entity Extraction
    "ENTITY_EXTRACTION_PROMPTS",
    "get_entity_extraction_prompt",
    # Confirmation
    "CONFIRMATION_PROMPTS",
    "get_confirmation_prompt",
    # Error
    "ERROR_PROMPTS",
    "get_error_prompt",
    # Success
    "SUCCESS_PROMPTS",
    "get_success_prompt",
    # Translations
    "SYSTEM_PROMPTS_TRANSLATIONS",
    "INTENT_CLASSIFICATION_PROMPTS_TRANSLATIONS",
    "RESPONSE_GENERATION_PROMPTS_TRANSLATIONS",
    "GREETING_RESPONSES",
    "GOODBYE_RESPONSES",
    "HELP_RESPONSES",
    "ERROR_RESPONSES",
]
