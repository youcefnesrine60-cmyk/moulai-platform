# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🧠 NLU MODULE
# وحدة فهم اللغة الطبيعية
# ==============================================

"""Package initializer and public module exports.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.agent.nlu.intent_classifier import (
    IntentClassifier,
    classify_intent,
    IntentResult,
    EntityDict as IntentEntityDict,
)

from app.agent.nlu.entity_extractor import (
    EntityExtractor,
    extract_entities,
    ExtractionResult,
    EntityDict,
    EntityList,
)

# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    # Intent Classifier
    "IntentClassifier",
    "classify_intent",
    "IntentResult",
    "IntentEntityDict",
    # Entity Extractor
    "EntityExtractor",
    "extract_entities",
    "ExtractionResult",
    "EntityDict",
    "EntityList",
]
