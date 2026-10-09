# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🤖 AGENT CONFIG
# إعدادات الوكيل الذكي
# ==============================================

"""MoulAI operational module for config.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from typing import (
    Dict,
    List,
    Optional,
)

from pydantic import (
    ConfigDict,
    Field,
)
from pydantic_settings import BaseSettings

from app.core.logger import logger

# ==============================================
# 🧩 TYPES
# ==============================================

LanguageCode = str
LanguageName = str
ConfidenceScore = float
LanguageMap = Dict[LanguageCode, LanguageName]
PatternMap = Dict[LanguageCode, List[str]]
PhraseMap = Dict[LanguageCode, List[str]]

# ==============================================
# 🤖 AGENT CONFIG
# ==============================================


class AgentConfig(BaseSettings):
    """
    إعدادات الوكيل الذكي.

    تدير إعدادات النماذج اللغوية واللغات والقنوات.

    Attributes:
        llm_provider: مزود النموذج اللغوي (openai, gemini, local)
        openai_api_key: مفتاح OpenAI API
        openai_model: نموذج OpenAI
        gemini_api_key: مفتاح Gemini API
        gemini_model: نموذج Gemini
        max_history: الحد الأقصى لرسائل السياق
        confidence_threshold: عتبة الثقة للتصنيف
        session_timeout: مهلة الجلسة (ثواني)
        supported_languages: اللغات المدعومة
        default_language: اللغة الافتراضية
        telegram_token: رمز بوت Telegram
    """

    # إعدادات LLM
    llm_provider: str = Field(
        default="openai",
        description="مزود النموذج اللغوي (openai, gemini, local)",
    )
    openai_api_key: Optional[str] = Field(
        default=None,
        description="مفتاح OpenAI API",
    )
    openai_model: str = Field(
        default="gpt-3.5-turbo",
        description="نموذج OpenAI",
    )

    gemini_api_key: Optional[str] = Field(
        default=None,
        description="مفتاح Gemini API",
    )
    gemini_model: str = Field(
        default="gemini-pro",
        description="نموذج Gemini",
    )

    # إعدادات المحرك
    max_history: int = Field(
        default=10,
        ge=1,
        description="الحد الأقصى لرسائل السياق",
    )
    confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="عتبة الثقة للتصنيف",
    )
    session_timeout: int = Field(
        default=3600,
        ge=60,
        description="مهلة الجلسة (ثواني)",
    )

    # إعدادات اللغة
    supported_languages: List[str] = Field(
        default=["ar", "en", "fr"],
        description="اللغات المدعومة",
    )
    default_language: str = Field(
        default="ar",
        description="اللغة الافتراضية",
    )

    # إعدادات القنوات
    telegram_token: Optional[str] = Field(
        default=None,
        description="رمز بوت Telegram",
    )

    # استخدام ConfigDict بدلاً من class-based config
    model_config = ConfigDict(
        env_prefix="AGENT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


# ==============================================
# 🌍 LANGUAGE CONFIG
# ==============================================


class LanguageConfig:
    """
    إعدادات اللغات المدعومة.

    تحتوي على قواميس للغات المدعومة وأنماط الكشف والعبارات الشائعة.

    Attributes:
        LANGUAGE_NAMES: أسماء اللغات
        LANGUAGE_CODES: رموز اللغات
        DETECTION_PATTERNS: أنماط كشف اللغة
        GREETINGS: عبارات التحية
        GOODBYES: عبارات الوداع
        HELP: عبارات المساعدة
        ORDER: عبارات الطلب
        MENU: عبارات القائمة
        PRICE: عبارات الأسعار
        OFFER: عبارات العروض
    """

    # أسماء اللغات
    LANGUAGE_NAMES: LanguageMap = {
        "ar": "العربية",
        "en": "English",
        "fr": "Français",
    }

    # رموز اللغات
    LANGUAGE_CODES: Dict[str, LanguageCode] = {
        "ar": "ar",
        "en": "en",
        "fr": "fr",
    }

    # أنماط كشف اللغة
    DETECTION_PATTERNS: PatternMap = {
        "ar": [
            "مرحبا",
            "السلام",
            "اهلا",
            "شكرا",
            "من فضلك",
            "لو سمحت",
            "ممكن",
            "كيف",
            "ايش",
            "شنو",
            "وش",
            "ليش",
            "علاش",
            "ابي",
            "ابغى",
            "بدي",
            "نبي",
            "نبغى",
            "ندي",
        ],
        "en": [
            "hello",
            "hi",
            "thanks",
            "please",
            "can",
            "could",
            "how",
            "what",
            "why",
            "when",
            "where",
            "who",
            "which",
            "want",
            "need",
            "get",
            "order",
            "buy",
        ],
        "fr": [
            "bonjour",
            "salut",
            "merci",
            "s'il vous plaît",
            "peux",
            "peut",
            "comment",
            "quoi",
            "pourquoi",
            "quand",
            "où",
            "qui",
            "lequel",
            "veux",
            "besoin",
            "obtenir",
            "commander",
            "acheter",
        ],
    }

    # عبارات التحية حسب اللغة
    GREETINGS: PhraseMap = {
        "ar": ["مرحبا", "السلام عليكم", "اهلا", "هلا", "صباح الخير", "مساء الخير"],
        "en": ["hello", "hi", "hey", "good morning", "good evening", "greetings"],
        "fr": ["bonjour", "salut", "coucou", "bonsoir", "hé"],
    }

    # عبارات الوداع حسب اللغة
    GOODBYES: PhraseMap = {
        "ar": ["مع السلامة", "وداعا", "باي", "سلام", "الى اللقاء"],
        "en": ["goodbye", "bye", "see you", "later", "farewell"],
        "fr": ["au revoir", "salut", "à bientôt", "ciao", "adieu"],
    }

    # عبارات المساعدة حسب اللغة
    HELP: PhraseMap = {
        "ar": ["مساعدة", "مساعده", "help", "كيف", "طريقة", "شرح", "مساعدة"],
        "en": ["help", "assist", "support", "guide", "how to"],
        "fr": ["aide", "assistance", "support", "guide", "comment"],
    }

    # عبارات الطلب حسب اللغة
    ORDER: PhraseMap = {
        "ar": ["طلب", "اطلب", "اريد", "ابغى", "بدي", "نريد", "طلبات"],
        "en": ["order", "buy", "purchase", "get", "want", "need"],
        "fr": ["commander", "acheter", "obtenir", "vouloir", "besoin"],
    }

    # عبارات القائمة حسب اللغة
    MENU: PhraseMap = {
        "ar": ["قائمة", "منيو", "menu", "الاكل", "الطعام", "الوجبات"],
        "en": ["menu", "list", "items", "food", "dishes", "meals"],
        "fr": ["menu", "liste", "plats", "nourriture", "repas"],
    }

    # عبارات الأسعار حسب اللغة
    PRICE: PhraseMap = {
        "ar": ["سعر", "بكم", "كم", "ثمن", "كلفة"],
        "en": ["price", "cost", "how much", "charge", "fee"],
        "fr": ["prix", "coût", "combien", "tarif", "frais"],
    }

    # عبارات العروض حسب اللغة
    OFFER: PhraseMap = {
        "ar": ["عرض", "عروض", "خصم", "تخفيض", "صفقة"],
        "en": ["offer", "offers", "discount", "deal", "promotion"],
        "fr": ["offre", "offres", "remise", "réduction", "promotion"],
    }


# ==============================================
# 🔧 DEFAULT CONFIG
# ==============================================

# إنشاء إعدادات افتراضية
default_config: AgentConfig = AgentConfig()

# إنشاء إعدادات اللغة
language_config: LanguageConfig = LanguageConfig()


# ==============================================
# 🔍 HELPER FUNCTIONS
# ==============================================

# ==============================================
# GET LANGUAGE NAME
# ==============================================


def get_language_name(
    *,
    lang_code: LanguageCode,
) -> LanguageName:
    """
    الحصول على اسم اللغة من رمزها.

    Args:
        lang_code: رمز اللغة (ar, en, fr)

    Returns:
        اسم اللغة
    """
    logger.debug(
        "get_language_name_called",
        extra={"lang_code": lang_code},
    )

    return language_config.LANGUAGE_NAMES.get(lang_code, lang_code)


# ==============================================
# IS LANGUAGE SUPPORTED
# ==============================================


def is_language_supported(
    *,
    lang_code: LanguageCode,
) -> bool:
    """
    التحقق من أن اللغة مدعومة.

    Args:
        lang_code: رمز اللغة

    Returns:
        True إذا كانت مدعومة
    """
    logger.debug(
        "is_language_supported_called",
        extra={"lang_code": lang_code},
    )

    return lang_code in language_config.LANGUAGE_NAMES


# ==============================================
# GET SUPPORTED LANGUAGES
# ==============================================


def get_supported_languages() -> List[LanguageCode]:
    """
    الحصول على قائمة اللغات المدعومة.

    Returns:
        قائمة رموز اللغات المدعومة
    """
    supported = list(language_config.LANGUAGE_NAMES.keys())

    logger.info(
        "get_supported_languages",
        extra={"languages": supported},
    )

    return supported


# ==============================================
# GET DEFAULT LANGUAGE
# ==============================================


def get_default_language() -> LanguageCode:
    """
    الحصول على اللغة الافتراضية.

    Returns:
        اللغة الافتراضية
    """
    logger.debug(
        "get_default_language_called",
        extra={"default_language": default_config.default_language},
    )

    return default_config.default_language


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    # Classes
    "AgentConfig",
    "LanguageConfig",
    # Instances
    "default_config",
    "language_config",
    # Helper Functions
    "get_language_name",
    "is_language_supported",
    "get_supported_languages",
    "get_default_language",
    # Types
    "LanguageCode",
    "LanguageName",
    "ConfidenceScore",
    "LanguageMap",
    "PatternMap",
    "PhraseMap",
]
