# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🌍 LANGUAGE DETECTOR
# كشف اللغة من النص
# ==============================================

"""MoulAI operational module for detector.

Part of MoulAI Platform - Agent-as-a-Service.
"""

import re
from typing import (
    Dict,
    List,
    Tuple,
)

from app.agent.config import (
    ConfidenceScore,
    LanguageCode,
    LanguageName,
    language_config,
)
from app.core.logger import logger

# ==============================================
# 🧩 TYPES
# ==============================================

LanguageDetectionResult = Tuple[LanguageCode, ConfidenceScore]

# ==============================================
# 🌍 LANGUAGE DETECTOR
# ==============================================


class LanguageDetector:
    """
    كاشف اللغة - يكتشف لغة النص المدخل.

    يدعم: العربية (بلهجاتها)، الإنجليزية، الفرنسية

    Attributes:
        patterns: أنماط كشف اللغة
        confidence_threshold: عتبة الثقة
        french_common_words: كلمات فرنسية شائعة
        english_common_words: كلمات إنجليزية شائعة
    """

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        *,
        confidence_threshold: float = 0.3,
    ) -> None:
        """
        تهيئة كاشف اللغة.

        Args:
            confidence_threshold: عتبة الثقة للكشف
        """
        self.patterns: Dict[LanguageCode, List[str]] = (
            language_config.DETECTION_PATTERNS
        )
        self.confidence_threshold: float = confidence_threshold

        # كلمات فرنسية شائعة للكشف
        self.french_common_words: List[str] = [
            "bonjour",
            "bonsoir",
            "merci",
            "s'il vous plaît",
            "s'il vous plait",
            "comment",
            "ça va",
            "très bien",
            "au revoir",
            "à bientôt",
            "je",
            "tu",
            "il",
            "elle",
            "nous",
            "vous",
            "ils",
            "elles",
            "le",
            "la",
            "les",
            "un",
            "une",
            "des",
            "est",
            "sont",
            "être",
            "avoir",
            "faire",
            "vouloir",
            "pouvoir",
            "devoir",
            "savoir",
            "oui",
            "non",
            "peut-être",
        ]

        # كلمات إنجليزية شائعة للكشف
        self.english_common_words: List[str] = [
            "hello",
            "hi",
            "hey",
            "good morning",
            "good evening",
            "good night",
            "thanks",
            "thank you",
            "please",
            "sorry",
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
            "purchase",
            "yes",
            "no",
            "maybe",
            "ok",
            "okay",
            "the",
            "a",
            "an",
            "this",
            "that",
            "these",
            "those",
        ]

        logger.info(
            "language_detector_initialized",
            extra={
                "supported_languages": list(self.patterns.keys()),
                "confidence_threshold": confidence_threshold,
            },
        )

    # ==========================================
    # 🔍 DETECT LANGUAGE
    # ==========================================

    def detect(
        self,
        *,
        text: str,
    ) -> LanguageDetectionResult:
        """
        كشف لغة النص.

        Args:
            text: النص المراد كشف لغته

        Returns:
            (رمز اللغة, نسبة الثقة)
        """
        if not text or not text.strip():
            logger.debug(
                "detect_language_empty_text",
                extra={"text": text},
            )
            return language_config.LANGUAGE_CODES["ar"], 0.0

        text_lower: str = text.lower().strip()
        words: List[str] = re.findall(r"\w+", text_lower)

        if not words:
            logger.debug(
                "detect_language_no_words",
                extra={"text": text},
            )
            return language_config.LANGUAGE_CODES["ar"], 0.0

        # حساب عدد الكلمات لكل لغة باستخدام الأنماط
        scores: Dict[LanguageCode, int] = {lang: 0 for lang in self.patterns.keys()}

        # حساب عدد الكلمات لكل لغة باستخدام الأنماط المحددة
        for word in words:
            for lang, patterns in self.patterns.items():
                for pattern in patterns:
                    if pattern in word or word in pattern:
                        scores[lang] += 1

        # إضافة نقاط إضافية للكلمات الشائعة في كل لغة
        for word in words:
            # كلمات فرنسية شائعة
            if word in self.french_common_words:
                scores["fr"] += 2

            # كلمات إنجليزية شائعة
            if word in self.english_common_words:
                scores["en"] += 2

            # كلمات عربية (تحقق من وجود أحرف عربية)
            if re.search(r"[\u0600-\u06FF]", word):
                scores["ar"] += 2

        # حساب نسبة الثقة
        total: int = sum(scores.values())

        if total == 0:
            logger.debug(
                "detect_language_fallback_to_characters",
                extra={"text": text},
            )
            return self._detect_by_characters(text=text)

        # اختيار اللغة ذات أعلى درجة
        best_lang: LanguageCode = max(scores, key=scores.get)
        confidence: ConfidenceScore = scores[best_lang] / total if total > 0 else 0.0

        # إذا كانت الثقة منخفضة، استخدم اللغة الافتراضية
        if confidence < self.confidence_threshold:
            logger.debug(
                "detect_language_low_confidence",
                extra={
                    "best_lang": best_lang,
                    "confidence": confidence,
                    "threshold": self.confidence_threshold,
                },
            )
            return self._detect_by_characters(text=text)

        logger.debug(
            "detect_language_result",
            extra={
                "language": best_lang,
                "confidence": confidence,
                "text_preview": text[:50],
            },
        )

        return best_lang, min(confidence, 1.0)

    # ==========================================
    # 🛠️ PRIVATE HELPERS
    # ==========================================

    def _detect_by_characters(
        self,
        *,
        text: str,
    ) -> LanguageDetectionResult:
        """
        كشف اللغة عن طريق تحليل الأحرف.

        Args:
            text: النص المراد كشف لغته

        Returns:
            (رمز اللغة, نسبة الثقة)
        """
        # نطاقات الأحرف العربية
        arabic_range: re.Pattern = re.compile(
            r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]",
        )

        # نطاقات الأحرف الفرنسية (أحرف لاتينية مع علامات)
        french_range: re.Pattern = re.compile(
            r"[àâäéèêëïîôöùûüÿç]",
            re.IGNORECASE,
        )

        # حساب عدد الأحرف العربية
        arabic_count: int = len(arabic_range.findall(text))

        # حساب عدد الأحرف الفرنسية
        french_count: int = len(french_range.findall(text))

        # عدد الأحرف اللاتينية العامة
        latin_count: int = len(re.findall(r"[a-zA-Z]", text)) - french_count

        total: int = arabic_count + latin_count + french_count

        if total == 0:
            return language_config.LANGUAGE_CODES["ar"], 0.0

        # إذا كان هناك أحرف عربية
        if arabic_count > 0 and arabic_count / total > 0.3:
            return language_config.LANGUAGE_CODES["ar"], min(arabic_count / total, 1.0)

        # إذا كان هناك أحرف فرنسية
        if french_count > 0 and french_count / total > 0.2:
            return language_config.LANGUAGE_CODES["fr"], min(french_count / total, 1.0)

        # إذا كان هناك أحرف لاتينية
        if latin_count > 0:
            # محاولة التمييز بين الإنجليزية والفرنسية
            # التحقق من كلمات فرنسية شائعة
            text_lower: str = text.lower()

            # قائمة كلمات فرنسية
            french_words: List[str] = [
                "je",
                "tu",
                "il",
                "elle",
                "nous",
                "vous",
                "ils",
                "elles",
                "le",
                "la",
                "les",
                "un",
                "une",
                "des",
                "est",
                "sont",
                "être",
                "avoir",
                "faire",
                "bonjour",
                "bonsoir",
                "merci",
                "au revoir",
            ]

            french_score: int = sum(
                1
                for word in french_words
                if word in text_lower or text_lower.startswith(word)
            )

            # قائمة كلمات إنجليزية
            english_words: List[str] = [
                "hello",
                "hi",
                "good",
                "morning",
                "evening",
                "thanks",
                "please",
                "sorry",
                "how",
                "what",
                "the",
                "this",
                "that",
                "these",
                "those",
            ]

            english_score: int = sum(
                1
                for word in english_words
                if word in text_lower or text_lower.startswith(word)
            )

            # إذا كانت الكلمات الفرنسية أكثر، نختار الفرنسية
            if french_score > english_score and french_score > 0:
                return language_config.LANGUAGE_CODES["fr"], min(0.7, french_score / 10)

            # إذا كانت الكلمات الإنجليزية أكثر، نختار الإنجليزية
            if english_score > french_score and english_score > 0:
                return language_config.LANGUAGE_CODES["en"], min(
                    0.7, english_score / 10
                )

            # إذا كان العدد متساوياً، نتحقق من وجود كلمات فرنسية مميزة
            if "bon" in text_lower or "soir" in text_lower or "jour" in text_lower:
                return language_config.LANGUAGE_CODES["fr"], 0.6

            return language_config.LANGUAGE_CODES["en"], min(0.8, latin_count / total)

        return language_config.LANGUAGE_CODES["ar"], 0.0


# ==============================================
# 🔍 UTILITY FUNCTIONS
# ==============================================

# ==============================================
# DETECT LANGUAGE
# ==============================================


def detect_language(
    *,
    text: str,
) -> LanguageDetectionResult:
    """
    كشف لغة النص (دالة مساعدة).

    Args:
        text: النص المراد كشف لغته

    Returns:
        (رمز اللغة, نسبة الثقة)
    """
    logger.debug(
        "detect_language_called",
        extra={"text_length": len(text) if text else 0},
    )

    detector: LanguageDetector = LanguageDetector()

    return detector.detect(text=text)


# ==============================================
# GET LANGUAGE NAME
# ==============================================


def get_language_name(
    *,
    lang_code: LanguageCode,
) -> LanguageName:
    """
    الحصول على اسم اللغة من رمزها (دالة مساعدة).

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
# 📋 EXPORTS
# ==============================================

__all__ = [
    "LanguageDetector",
    "detect_language",
    "get_language_name",
    "LanguageDetectionResult",
]
