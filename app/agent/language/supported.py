# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🌍 SUPPORTED LANGUAGES
# اللغات المدعومة في الوكيل
# ==============================================

"""MoulAI operational module for supported.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from typing import (
    Dict,
    List,
    Set,
)
from enum import Enum

from app.core.logger import logger

# ==============================================
# 🧩 TYPES
# ==============================================

LanguageCode = str
LanguageName = str
LanguageMap = Dict[LanguageCode, LanguageName]

# ==============================================
# 🌍 LANGUAGE ENUM
# ==============================================


class Language(Enum):
    """
    اللغات المدعومة في الوكيل الذكي.

    يدعم ثلاث لغات: العربية والإنجليزية والفرنسية.
    """

    ARABIC = "ar"
    ENGLISH = "en"
    FRENCH = "fr"

    # ==============================================
    # LIST CODES
    # ==============================================

    @classmethod
    def list_codes(cls) -> List[LanguageCode]:
        """
        الحصول على قائمة رموز اللغات المدعومة.

        Returns:
            قائمة رموز اللغات
        """
        return [lang.value for lang in cls]

    # ==============================================
    # LIST NAMES
    # ==============================================

    @classmethod
    def list_names(cls) -> LanguageMap:
        """
        الحصول على قائمة أسماء اللغات المدعومة.

        Returns:
            قاموس (رمز اللغة, اسم اللغة)
        """
        return {
            "ar": "العربية",
            "en": "English",
            "fr": "Français",
        }

    # ==============================================
    # IS SUPPORTED
    # ==============================================

    @classmethod
    def is_supported(cls, lang_code: str) -> bool:
        """
        التحقق من أن اللغة مدعومة.

        Args:
            lang_code: رمز اللغة

        Returns:
            True إذا كانت مدعومة
        """
        return lang_code in cls.list_codes()

    # ==============================================
    # GET NAME
    # ==============================================

    @classmethod
    def get_name(cls, lang_code: str) -> str:
        """
        الحصول على اسم اللغة من رمزها.

        Args:
            lang_code: رمز اللغة

        Returns:
            اسم اللغة
        """
        names = cls.list_names()
        return names.get(lang_code, lang_code)

    # ==============================================
    # GET DEFAULT
    # ==============================================

    @classmethod
    def get_default(cls) -> str:
        """
        الحصول على اللغة الافتراضية.

        Returns:
            رمز اللغة الافتراضية
        """
        return "ar"


# ==============================================
# 📋 LANGUAGE MAPPINGS
# ==============================================

# أسماء اللغات بالإنجليزية
LANG_NAMES_EN: LanguageMap = {
    "ar": "Arabic",
    "en": "English",
    "fr": "French",
}

# أسماء اللغات بالعربية
LANG_NAMES_AR: LanguageMap = {
    "ar": "العربية",
    "en": "الإنجليزية",
    "fr": "الفرنسية",
}

# أسماء اللغات بالفرنسية
LANG_NAMES_FR: LanguageMap = {
    "ar": "Arabe",
    "en": "Anglais",
    "fr": "Français",
}

# أسماء اللغات بجميع اللغات
LANG_NAMES_ALL: Dict[str, LanguageMap] = {
    "ar": LANG_NAMES_AR,
    "en": LANG_NAMES_EN,
    "fr": LANG_NAMES_FR,
}

# اللغة الافتراضية
DEFAULT_LANGUAGE: LanguageCode = "ar"

# جميع اللغات المدعومة
SUPPORTED_LANGUAGES: Set[LanguageCode] = {"ar", "en", "fr"}

# أسماء اللغات المعروضة
LANGUAGE_DISPLAY_NAMES: LanguageMap = {
    "ar": "🇸🇦 العربية",
    "en": "🇬🇧 English",
    "fr": "🇫🇷 Français",
}


# ==============================================
# 🛠️ UTILITY FUNCTIONS
# ==============================================

# ==============================================
# GET LANGUAGE NAME
# ==============================================


def get_language_name(
    lang_code: str,
    display_lang: str = "ar",
) -> str:
    """
    الحصول على اسم اللغة باللغة المطلوبة.

    Args:
        lang_code: رمز اللغة
        display_lang: لغة العرض (ar, en, fr)

    Returns:
        اسم اللغة
    """
    logger.debug(
        "get_language_name_called",
        extra={
            "lang_code": lang_code,
            "display_lang": display_lang,
        },
    )

    if display_lang in LANG_NAMES_ALL:
        return LANG_NAMES_ALL[display_lang].get(lang_code, lang_code)

    return LANG_NAMES_EN.get(lang_code, lang_code)


# ==============================================
# GET LANGUAGE DISPLAY NAME
# ==============================================


def get_language_display_name(
    lang_code: str,
) -> str:
    """
    الحصول على اسم اللغة المعروض مع العلم.

    Args:
        lang_code: رمز اللغة

    Returns:
        اسم اللغة المعروض
    """
    logger.debug(
        "get_language_display_name_called",
        extra={"lang_code": lang_code},
    )

    return LANGUAGE_DISPLAY_NAMES.get(lang_code, lang_code)


# ==============================================
# IS SUPPORTED LANGUAGE
# ==============================================


def is_supported_language(
    lang_code: str,
) -> bool:
    """
    التحقق من أن اللغة مدعومة.

    Args:
        lang_code: رمز اللغة

    Returns:
        True إذا كانت مدعومة، False وإلا
    """
    return lang_code in SUPPORTED_LANGUAGES


# ==============================================
# GET SUPPORTED LANGUAGES
# ==============================================


def get_supported_languages(
    as_list: bool = False,
) -> Set[LanguageCode] | List[LanguageCode]:
    """
    الحصول على قائمة اللغات المدعومة.

    Args:
        as_list: إرجاع القائمة كـ list بدلاً من set

    Returns:
        قائمة أو مجموعة اللغات المدعومة
    """
    logger.debug(
        "get_supported_languages_called",
        extra={"as_list": as_list},
    )

    if as_list:
        return list(SUPPORTED_LANGUAGES)

    return SUPPORTED_LANGUAGES


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "Language",
    "LANG_NAMES_EN",
    "LANG_NAMES_AR",
    "LANG_NAMES_FR",
    "LANG_NAMES_ALL",
    "DEFAULT_LANGUAGE",
    "SUPPORTED_LANGUAGES",
    "LANGUAGE_DISPLAY_NAMES",
    "get_language_name",
    "get_language_display_name",
    "is_supported_language",
    "get_supported_languages",
]
