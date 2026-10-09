# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🎯 INTENT CLASSIFIER
# تصنيف نوايا المستخدم متعدد اللغات
# ==============================================

"""MoulAI operational module for intent classifier.

Part of MoulAI Platform - Agent-as-a-Service.
"""

import json
import re
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from app.agent.config import (
    LanguageCode,
    default_config,
)
from app.agent.language.detector import detect_language
from app.agent.prompts.translations import (
    INTENT_CLASSIFICATION_PROMPTS,
)
from app.core.ai_client import AIClient
from app.core.logger import logger

# ==============================================
# 🧩 TYPES
# ==============================================

IntentResult = Dict[str, Any]
EntityDict = Dict[str, Any]
IntentList = List[str]

# ==============================================
# 🎯 INTENT CLASSIFIER
# ==============================================


class IntentClassifier:
    """
    مصنف نوايا المستخدم - يدعم اللغات المتعددة مع نظام الأولويات.

    مسؤول عن:
        - تصنيف نية المستخدم من النص
        - استخراج الكيانات الأساسية
        - دعم اللغة العربية (بلهجاتها) والإنجليزية والفرنسية

    Attributes:
        ai_client: عميل الذكاء الاصطناعي
        confidence_threshold: عتبة الثقة
        supported_intents: قائمة النوايا المدعومة
        priority_order: ترتيب أولويات النوايا
    """

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        *,
        ai_client: Optional[AIClient] = None,
        confidence_threshold: Optional[float] = None,
    ) -> None:
        """
        تهيئة مصنف النوايا.

        Args:
            ai_client: عميل الذكاء الاصطناعي (اختياري)
            confidence_threshold: عتبة الثقة (اختياري)
        """
        self.ai_client: AIClient = ai_client or AIClient()
        self.confidence_threshold: float = (
            confidence_threshold or default_config.confidence_threshold
        )

        # قائمة النوايا المدعومة
        self.supported_intents: IntentList = [
            "order_food",
            "view_menu",
            "view_restaurants",
            "modify_order",
            "cancel_order",
            "track_order",
            "ask_price",
            "ask_offer",
            "complaint",
            "help",
            "greeting",
            "goodbye",
            "unknown",
        ]

        # ترتيب الأولويات (الأعلى أولاً)
        self.priority_order: List[str] = [
            "greeting",  # 1️⃣ أعلى أولوية
            "goodbye",  # 2️⃣
            "order_food",  # 3️⃣
            "cancel_order",  # 4️⃣
            "modify_order",  # 5️⃣
            "track_order",  # 6️⃣
            "ask_price",  # 7️⃣
            "ask_offer",  # 8️⃣
            "complaint",  # 9️⃣
            "help",  # 🔟
            "view_menu",  # 1️⃣1️⃣
            "view_restaurants",  # 1️⃣2️⃣
            "unknown",  # 1️⃣3️⃣ أقل أولوية
        ]

        # أنماط الكلمات المفتاحية لكل نية (لكل لغة)
        self.intent_patterns: Dict[LanguageCode, Dict[str, List[str]]] = {
            "ar": {
                "order_food": [
                    "طلب",
                    "اطلب",
                    "اريد",
                    "ابغى",
                    "بدي",
                    "نريد",
                    "طلبات",
                    "وجبة",
                    "اكل",
                    "طعام",
                    "بيتزا",
                    "برجر",
                    "شاورما",
                ],
                "view_menu": [
                    "قائمة",
                    "منيو",
                    "menu",
                    "الاكل",
                    "الطعام",
                    "الوجبات",
                    "عرض",
                ],
                "view_restaurants": ["مطعم", "مطاعم", "محلات", "اكل", "طعام"],
                "modify_order": ["تعديل", "تغيير", "تعديل الطلب"],
                "cancel_order": ["الغاء", "إلغاء", "الغ", "الغي", "الغاء الطلب"],
                "track_order": ["تتبع", "طلبى", "طلبي", "رقم الطلب", "وصول"],
                "ask_price": ["سعر", "بكم", "كم", "ثمن", "كلفة"],
                "ask_offer": ["عرض", "عروض", "خصم", "تخفيض", "صفقة"],
                "complaint": ["شكوى", "مشكلة", "شكوي", "خطأ", "غلط"],
                # الاحتفاظ بـ "كيف" لأن الأولوية ستحل المشكلة
                "help": [
                    "مساعدة",
                    "مساعده",
                    "مساعدتي",
                    "ساعد",
                    "طريقة",
                    "شرح",
                    "طريقه",
                    "ساعدني",
                    "دليل",
                    "ارشاد",
                    "كيف",
                ],
                "greeting": [
                    "مرحبا",
                    "السلام",
                    "اهلا",
                    "هلا",
                    "صباح",
                    "مساء",
                    "حالك",
                    "حال",
                    "اخبار",
                    "اخبارك",
                    "عليكم",
                ],
                "goodbye": ["مع السلامة", "وداعا", "باي", "سلام", "الى اللقاء"],
            },
            "en": {
                "order_food": [
                    "order",
                    "buy",
                    "purchase",
                    "get",
                    "want",
                    "need",
                    "food",
                    "meal",
                    "pizza",
                    "burger",
                ],
                "view_menu": [
                    "menu",
                    "list",
                    "items",
                    "food",
                    "dishes",
                    "meals",
                    "show",
                ],
                "view_restaurants": ["restaurant", "restaurants", "places", "eat"],
                "modify_order": ["modify", "change", "edit", "update", "order"],
                "cancel_order": ["cancel", "cancel order", "stop"],
                "track_order": ["track", "follow", "order status", "where is"],
                "ask_price": ["price", "cost", "how much", "charge", "fee"],
                "ask_offer": ["offer", "offers", "discount", "deal", "promotion"],
                "complaint": ["complaint", "problem", "issue", "wrong", "error"],
                "help": ["help", "assist", "support", "guide", "how to"],
                "greeting": [
                    "hello",
                    "hi",
                    "hey",
                    "good morning",
                    "good evening",
                    "how are you",
                ],
                "goodbye": ["goodbye", "bye", "see you", "later", "farewell"],
            },
            "fr": {
                "order_food": [
                    "commander",
                    "acheter",
                    "obtenir",
                    "vouloir",
                    "besoin",
                    "nourriture",
                    "repas",
                    "pizza",
                    "burger",
                ],
                "view_menu": [
                    "menu",
                    "liste",
                    "plats",
                    "nourriture",
                    "repas",
                    "afficher",
                ],
                "view_restaurants": ["restaurant", "restaurants", "endroits", "manger"],
                "modify_order": [
                    "modifier",
                    "changer",
                    "éditer",
                    "mettre à jour",
                    "commande",
                ],
                "cancel_order": ["annuler", "annuler la commande", "arrêter"],
                "track_order": ["suivre", "suivi", "état de commande", "où est"],
                "ask_price": ["prix", "coût", "combien", "tarif", "frais"],
                "ask_offer": ["offre", "offres", "remise", "réduction", "promotion"],
                "complaint": ["réclamation", "problème", "erreur", "plainte"],
                # الاحتفاظ بـ "comment" لأن الأولوية ستحل المشكلة
                "help": [
                    "aide",
                    "assistance",
                    "support",
                    "guide",
                    "tutoriel",
                    "comment",
                ],
                "greeting": [
                    "bonjour",
                    "salut",
                    "bonsoir",
                    "hé",
                    "ça va",
                    "allez-vous",
                ],
                "goodbye": ["au revoir", "salut", "à bientôt", "ciao", "adieu"],
            },
        }

        logger.info(
            "intent_classifier_initialized",
            extra={
                "supported_intents": len(self.supported_intents),
                "supported_languages": list(self.intent_patterns.keys()),
                "confidence_threshold": self.confidence_threshold,
                "priority_order": self.priority_order,
            },
        )

    # ==========================================
    # 🎯 CLASSIFY INTENT
    # ==========================================

    async def classify(
        self,
        *,
        text: str,
        language: Optional[LanguageCode] = None,
    ) -> IntentResult:
        """
        تصنيف نية المستخدم من النص.

        Args:
            text: النص المراد تصنيفه
            language: رمز اللغة (اختياري - سيتم كشفها تلقائياً)

        Returns:
            IntentResult: {
                "intent": str,
                "confidence": float,
                "entities": Dict,
                "language": str,
                "raw_response": str (اختياري)
            }
        """
        if not text or not text.strip():
            logger.debug(
                "classify_intent_empty_text",
                extra={"text": text},
            )
            return {
                "intent": "unknown",
                "confidence": 0.0,
                "entities": {},
                "language": "ar",
            }

        # 1️⃣ كشف اللغة إذا لم يتم تحديدها
        if language is None:
            detected_lang, _ = detect_language(text=text)
            language = detected_lang

        logger.info(
            "classify_intent_started",
            extra={
                "text_preview": text[:50],
                "language": language,
            },
        )

        # 2️⃣ محاولة التصنيف باستخدام الذكاء الاصطناعي
        if self.ai_client.enabled:
            try:
                result = await self._classify_with_ai(
                    text=text,
                    language=language,
                )
                if (
                    result
                    and result.get("confidence", 0.0) >= self.confidence_threshold
                ):
                    logger.info(
                        "classify_intent_ai_success",
                        extra={
                            "intent": result.get("intent"),
                            "confidence": result.get("confidence"),
                        },
                    )
                    result["language"] = language
                    return result
            except Exception as e:
                logger.warning(
                    "classify_intent_ai_failed",
                    extra={"error": str(e)},
                )

        # 3️⃣ التصنيف باستخدام الأنماط (Fallback) مع نظام الأولويات
        result = self._classify_with_patterns(
            text=text,
            language=language,
        )

        # تحسين الثقة (جعلها أعلى قليلاً)
        if result["intent"] != "unknown" and result["confidence"] < 0.5:
            result["confidence"] = 0.5

        logger.info(
            "classify_intent_result",
            extra={
                "intent": result.get("intent"),
                "confidence": result.get("confidence"),
                "language": language,
            },
        )

        return result

    # ==========================================
    # 🤖 CLASSIFY WITH AI
    # ==========================================

    async def _classify_with_ai(
        self,
        *,
        text: str,
        language: LanguageCode,
    ) -> Optional[IntentResult]:
        """
        تصنيف النية باستخدام الذكاء الاصطناعي.

        Args:
            text: النص المراد تصنيفه
            language: رمز اللغة

        Returns:
            نتيجة التصنيف أو None
        """
        try:
            # الحصول على القالب المناسب للغة
            prompt_template = INTENT_CLASSIFICATION_PROMPTS.get(
                language,
                INTENT_CLASSIFICATION_PROMPTS["en"],
            )

            prompt = prompt_template.format(message=text)

            # استدعاء الذكاء الاصطناعي
            response = await self.ai_client.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an intent classifier. Output only valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=200,
            )

            # استخراج JSON من الرد
            json_str = self._extract_json(response)

            if not json_str:
                return None

            result = json.loads(json_str)

            # التحقق من صحة النتيجة
            if "intent" not in result:
                return None

            # التأكد من أن النية مدعومة
            if result["intent"] not in self.supported_intents:
                result["intent"] = "unknown"

            # التأكد من وجود الكيانات
            if "entities" not in result:
                result["entities"] = {}

            # التأكد من وجود الثقة
            if "confidence" not in result:
                result["confidence"] = 0.7

            return result

        except json.JSONDecodeError as e:
            logger.warning(
                "classify_intent_ai_json_error",
                extra={"error": str(e)},
            )
            return None

        except Exception as e:
            logger.warning(
                "classify_intent_ai_error",
                extra={"error": str(e)},
            )
            return None

    # ==========================================
    # 🔍 CLASSIFY WITH PATTERNS (مع الأولويات)
    # ==========================================

    def _classify_with_patterns(
        self,
        *,
        text: str,
        language: LanguageCode,
    ) -> IntentResult:
        """
        تصنيف النية باستخدام الأنماط مع نظام الأولويات (Fallback).

        Args:
            text: النص المراد تصنيفه
            language: رمز اللغة

        Returns:
            نتيجة التصنيف
        """
        text_lower = text.lower()
        patterns = self.intent_patterns.get(language, self.intent_patterns["en"])

        # حساب درجة كل نية
        scores: Dict[str, int] = {}

        for intent, keywords in patterns.items():
            score = 0
            for keyword in keywords:
                if keyword in text_lower:
                    score += 1
            if score > 0:
                scores[intent] = score

        # إذا لم يتم العثور على أي نية
        if not scores:
            return {
                "intent": "unknown",
                "confidence": 0.0,
                "entities": {},
            }

        # اختيار النية بناءً على الأولوية
        best_intent = None
        best_score = 0.0

        for intent in self.priority_order:
            if intent in scores and scores[intent] > 0:
                # إضافة مكافأة للنية ذات الأولوية العالية
                priority_bonus = (
                    len(self.priority_order) - self.priority_order.index(intent)
                ) * 0.1
                adjusted_score = scores[intent] + priority_bonus

                if best_intent is None or adjusted_score > best_score:
                    best_intent = intent
                    best_score = adjusted_score

        # إذا لم يتم العثور على نية في قائمة الأولويات
        if best_intent is None:
            best_intent = max(scores, key=scores.get)
            best_score = float(scores[best_intent])

        # حساب الثقة
        total_keywords = len(patterns.get(best_intent, []))
        confidence = min(best_score / max(1, total_keywords / 2), 0.8)

        # استخراج الكيانات
        entities = self._extract_entities(
            text=text,
            language=language,
        )

        logger.debug(
            "classify_intent_patterns_result",
            extra={
                "intent": best_intent,
                "confidence": confidence,
                "score": scores.get(best_intent, 0),
                "priority_index": (
                    self.priority_order.index(best_intent)
                    if best_intent in self.priority_order
                    else -1
                ),
            },
        )

        return {
            "intent": best_intent,
            "confidence": confidence,
            "entities": entities,
        }

    # ==========================================
    # 🔍 EXTRACT ENTITIES
    # ==========================================

    def _extract_entities(
        self,
        *,
        text: str,
        language: LanguageCode,
    ) -> EntityDict:
        """
        استخراج الكيانات من النص.

        Args:
            text: النص المراد استخراج الكيانات منه
            language: رمز اللغة

        Returns:
            الكيانات المستخرجة
        """
        entities: EntityDict = {
            "restaurant_name": None,
            "product_name": None,
            "order_id": None,
            "quantity": None,
            "price": None,
        }

        text_lower = text.lower()

        # 1️⃣ استخراج رقم الطلب
        order_patterns = [
            r"#?(\d{4,8})",
            r"رقم\s*الطلب\s*[#:]?\s*(\d+)",
            r"order\s*[#:]?\s*(\d+)",
            r"commande\s*[#:]?\s*(\d+)",
        ]

        for pattern in order_patterns:
            match = re.search(pattern, text_lower)
            if match:
                entities["order_id"] = match.group(1)
                break

        # 2️⃣ استخراج الكمية (محسّن)
        quantity_patterns = [
            r"(\d+)\s*(?:كيلو|كغم|غرام|قطعة|حبة|وحدة)",
            r"(\d+)\s*(?:kg|g|piece|unit)",
            r"(\d+)\s*(?:kg|g|pièce|unité)",
            r"(?:أريد|اطلب|اريد|ابغى|بدي|order|commander)\s*(\d+)",
            r"(\d+)\s*(?:بيتزا|برجر|شاورما|وجبة|pizza|burger|repas)",
            r"(\d+)\s*$",
        ]

        for pattern in quantity_patterns:
            match = re.search(pattern, text_lower)
            if match:
                entities["quantity"] = int(match.group(1))
                break

        # 3️⃣ استخراج السعر
        price_patterns = [
            r"(\d+(?:\.\d{1,2})?)\s*(?:دج|دينار|da|dzd)",
            r"(\d+(?:\.\d{1,2})?)\s*(?:da|dzd)",
            r"(\d+(?:\.\d{1,2})?)\s*(?:€|eur|dollar|usd)",
            r"سعر\s*[هو]?\s*(\d+(?:\.\d{1,2})?)",
            r"price\s*(?:is)?\s*(\d+(?:\.\d{1,2})?)",
            r"prix\s*(?:est)?\s*(\d+(?:\.\d{1,2})?)",
            r"بسعر\s*(\d+(?:\.\d{1,2})?)",
        ]

        for pattern in price_patterns:
            match = re.search(pattern, text_lower)
            if match:
                entities["price"] = float(match.group(1))
                break

        # 4️⃣ استخراج اسم المنتج
        product_patterns = [
            r"(?:اطلب|اريد|ابغى|بدي|order|commander)\s*(.+?)(?:\s*$|\.|،)",
            r"(بيتزا|برجر|شاورما|فطيرة|كوكا|عصير|مشروب)",
            r"(pizza|burger|shawarma|drink|juice)",
        ]

        for pattern in product_patterns:
            match = re.search(pattern, text_lower)
            if match:
                entities["product_name"] = match.group(1).strip()
                break

        return entities

    # ==========================================
    # 🛠️ UTILITY FUNCTIONS
    # ==========================================

    def _extract_json(
        self,
        text: str,
    ) -> Optional[str]:
        """
        استخراج JSON من النص.

        Args:
            text: النص المراد استخراج JSON منه

        Returns:
            نص JSON أو None
        """
        # البحث عن JSON بين قوسين
        match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
        if match:
            return match.group(0)

        # البحث عن JSON في النص
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            return text[start:end]

        return None

    # ==========================================
    # 🔍 GET INTENT DETAILS
    # ==========================================

    def get_intent_details(
        self,
        *,
        intent: str,
        language: LanguageCode = "ar",
    ) -> Dict[str, Any]:
        """
        الحصول على تفاصيل النية.

        Args:
            intent: اسم النية
            language: رمز اللغة

        Returns:
            تفاصيل النية
        """
        details = {
            "name": intent,
            "description": "",
            "keywords": [],
            "examples": [],
            "priority": (
                self.priority_order.index(intent)
                if intent in self.priority_order
                else -1
            ),
        }

        # ترجمات الأسماء
        names = {
            "ar": {
                "order_food": "طلب طعام",
                "view_menu": "عرض القائمة",
                "view_restaurants": "عرض المطاعم",
                "modify_order": "تعديل طلب",
                "cancel_order": "إلغاء طلب",
                "track_order": "تتبع طلب",
                "ask_price": "الاستفسار عن السعر",
                "ask_offer": "الاستفسار عن العروض",
                "complaint": "شكوى",
                "help": "مساعدة",
                "greeting": "تحية",
                "goodbye": "وداع",
                "unknown": "غير معروف",
            },
            "en": {
                "order_food": "Order Food",
                "view_menu": "View Menu",
                "view_restaurants": "View Restaurants",
                "modify_order": "Modify Order",
                "cancel_order": "Cancel Order",
                "track_order": "Track Order",
                "ask_price": "Ask Price",
                "ask_offer": "Ask Offer",
                "complaint": "Complaint",
                "help": "Help",
                "greeting": "Greeting",
                "goodbye": "Goodbye",
                "unknown": "Unknown",
            },
            "fr": {
                "order_food": "Commander",
                "view_menu": "Voir le Menu",
                "view_restaurants": "Voir les Restaurants",
                "modify_order": "Modifier la Commande",
                "cancel_order": "Annuler la Commande",
                "track_order": "Suivre la Commande",
                "ask_price": "Demander le Prix",
                "ask_offer": "Demander les Offres",
                "complaint": "Réclamation",
                "help": "Aide",
                "greeting": "Salutation",
                "goodbye": "Au Revoir",
                "unknown": "Inconnu",
            },
        }

        details["display_name"] = names.get(language, names["ar"]).get(intent, intent)

        # الكلمات المفتاحية
        patterns = self.intent_patterns.get(language, self.intent_patterns["ar"])
        details["keywords"] = patterns.get(intent, [])

        # أمثلة (حسب اللغة)
        examples = {
            "ar": {
                "order_food": ["أريد طلب بيتزا", "اطلب وجبة", "اريد شاورما"],
                "view_menu": ["عرض القائمة", "المنيو", "شو عندكم"],
                "view_restaurants": ["المطاعم المتاحة", "فين المطاعم", "عرض المطاعم"],
                "modify_order": ["تعديل طلبي", "تغيير الطلب", "بدل الطلب"],
                "cancel_order": ["الغاء الطلب", "الغي طلبي", "الغ الطلب"],
                "track_order": ["تتبع طلبي", "وين طلبي", "رقم الطلب"],
                "ask_price": ["سعر البيتزا", "بكم شاورما", "كم سعر"],
                "ask_offer": ["عروض اليوم", "خصومات", "تخفيضات"],
                "complaint": ["شكوى على الطلب", "مشكلة في الطلب", "الطلب غلط"],
                "help": ["مساعدة", "كيف اطلب", "طريقة الطلب", "ساعدني"],
                "greeting": ["مرحبا", "السلام عليكم", "اهلا", "كيف الحال"],
                "goodbye": ["مع السلامة", "وداعا", "باي"],
            },
            "en": {
                "order_food": ["I want to order pizza", "I need a meal", "Order food"],
                "view_menu": ["Show menu", "What do you have", "Menu please"],
                "view_restaurants": [
                    "Available restaurants",
                    "Where to eat",
                    "Restaurants",
                ],
                "modify_order": ["Modify my order", "Change order", "Edit order"],
                "cancel_order": ["Cancel my order", "Stop order", "Cancel"],
                "track_order": ["Track my order", "Where is my order", "Order status"],
                "ask_price": ["Price of pizza", "How much", "Cost"],
                "ask_offer": ["Today's offers", "Deals", "Discounts"],
                "complaint": [
                    "Complaint about order",
                    "Problem with order",
                    "Wrong order",
                ],
                "help": ["Help", "How to order", "Guide"],
                "greeting": ["Hello", "Hi", "Good morning", "How are you"],
                "goodbye": ["Goodbye", "Bye", "See you"],
            },
            "fr": {
                "order_food": [
                    "Je veux commander une pizza",
                    "J'ai besoin d'un repas",
                    "Commander",
                ],
                "view_menu": ["Afficher le menu", "Qu'est-ce que vous avez", "Menu"],
                "view_restaurants": [
                    "Restaurants disponibles",
                    "Où manger",
                    "Restaurants",
                ],
                "modify_order": [
                    "Modifier ma commande",
                    "Changer la commande",
                    "Éditer",
                ],
                "cancel_order": ["Annuler ma commande", "Arrêter", "Annuler"],
                "track_order": ["Suivre ma commande", "Où est ma commande", "État"],
                "ask_price": ["Prix de la pizza", "Combien", "Coût"],
                "ask_offer": ["Offres du jour", "Promotions", "Réductions"],
                "complaint": ["Réclamation sur la commande", "Problème", "Erreur"],
                "help": ["Aide", "Comment commander", "Guide"],
                "greeting": ["Bonjour", "Salut", "Bonsoir", "Comment allez-vous"],
                "goodbye": ["Au revoir", "Salut", "À bientôt"],
            },
        }

        details["examples"] = examples.get(language, examples["ar"]).get(intent, [])

        return details


# ==============================================
# 🔍 UTILITY FUNCTIONS
# ==============================================

# ==============================================
# CLASSIFY INTENT
# ==============================================


async def classify_intent(
    *,
    text: str,
    language: Optional[LanguageCode] = None,
    classifier: Optional[IntentClassifier] = None,
) -> IntentResult:
    """
    تصنيف نية المستخدم (دالة مساعدة).

    Args:
        text: النص المراد تصنيفه
        language: رمز اللغة (اختياري)
        classifier: مصنف النوايا (اختياري)

    Returns:
        نتيجة التصنيف
    """
    logger.debug(
        "classify_intent_called",
        extra={
            "text_length": len(text) if text else 0,
            "language": language,
        },
    )

    if classifier is None:
        classifier = IntentClassifier()

    return await classifier.classify(
        text=text,
        language=language,
    )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "IntentClassifier",
    "classify_intent",
    "IntentResult",
    "EntityDict",
]
