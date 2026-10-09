# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🔍 ENTITY EXTRACTOR
# استخراج الكيانات المتقدم من النص
# ==============================================

"""MoulAI operational module for entity extractor.

Part of MoulAI Platform - Agent-as-a-Service.
"""

import re
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from app.agent.config import (
    LanguageCode,
)
from app.agent.language.detector import detect_language
from app.core.ai_client import AIClient
from app.core.logger import logger

# ==============================================
# 🧩 TYPES
# ==============================================

EntityDict = Dict[str, Any]
EntityList = List[Dict[str, Any]]
ExtractionResult = Dict[str, Any]

# ==============================================
# 🔍 ENTITY EXTRACTOR
# ==============================================


class EntityExtractor:
    """
    مستخرج الكيانات المتقدم - يستخرج المعلومات المهمة من النص.

    يدعم:
        - أسماء المنتجات
        - الكميات والأوزان
        - الأسعار
        - العناوين
        - التواريخ والأوقات
        - أرقام الطلبات
        - أسماء العملاء
        - أرقام الهواتف

    Attributes:
        ai_client: عميل الذكاء الاصطناعي
        confidence_threshold: عتبة الثقة
    """

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        *,
        ai_client: Optional[AIClient] = None,
        confidence_threshold: float = 0.5,
    ) -> None:
        """
        تهيئة مستخرج الكيانات.

        Args:
            ai_client: عميل الذكاء الاصطناعي (اختياري)
            confidence_threshold: عتبة الثقة (اختياري)
        """
        self.ai_client: AIClient = ai_client or AIClient()
        self.confidence_threshold: float = confidence_threshold

        logger.info(
            "entity_extractor_initialized",
            extra={
                "confidence_threshold": confidence_threshold,
                "ai_enabled": self.ai_client.enabled,
            },
        )

    # ==========================================
    # 🔍 EXTRACT ENTITIES
    # ==========================================

    async def extract(
        self,
        *,
        text: str,
        language: Optional[LanguageCode] = None,
    ) -> ExtractionResult:
        """
        استخراج الكيانات من النص.

        Args:
            text: النص المراد استخراج الكيانات منه
            language: رمز اللغة (اختياري - سيتم كشفها تلقائياً)

        Returns:
            ExtractionResult: {
                "entities": List[Dict],
                "language": str,
                "raw_text": str,
            }
        """
        if not text or not text.strip():
            logger.debug(
                "extract_entities_empty_text",
                extra={"text": text},
            )
            return {
                "entities": [],
                "language": "ar",
                "raw_text": text,
            }

        # 1️⃣ كشف اللغة إذا لم يتم تحديدها
        if language is None:
            detected_lang, _ = detect_language(text=text)
            language = detected_lang

        logger.info(
            "extract_entities_started",
            extra={
                "text_preview": text[:50],
                "language": language,
            },
        )

        entities: EntityList = []

        # 2️⃣ محاولة الاستخراج باستخدام الذكاء الاصطناعي
        if self.ai_client.enabled:
            try:
                ai_entities = await self._extract_with_ai(
                    text=text,
                    language=language,
                )
                if ai_entities:
                    entities.extend(ai_entities)
                    logger.info(
                        "extract_entities_ai_success",
                        extra={"count": len(ai_entities)},
                    )
            except Exception as e:
                logger.warning(
                    "extract_entities_ai_failed",
                    extra={"error": str(e)},
                )

        # 3️⃣ الاستخراج باستخدام الأنماط (Fallback)
        pattern_entities = self._extract_with_patterns(
            text=text,
            language=language,
        )
        entities.extend(pattern_entities)

        # 4️⃣ دمج الكيانات المكررة
        entities = self._merge_entities(entities)

        logger.info(
            "extract_entities_result",
            extra={
                "count": len(entities),
                "types": list(set(e.get("type") for e in entities)),
            },
        )

        return {
            "entities": entities,
            "language": language,
            "raw_text": text,
        }

    # ==========================================
    # 🤖 EXTRACT WITH AI
    # ==========================================

    async def _extract_with_ai(
        self,
        *,
        text: str,
        language: LanguageCode,
    ) -> EntityList:
        """
        استخراج الكيانات باستخدام الذكاء الاصطناعي.

        Args:
            text: النص المراد استخراج الكيانات منه
            language: رمز اللغة

        Returns:
            قائمة الكيانات المستخرجة
        """
        try:
            # بناء الـ Prompt
            system_prompt = """
            You are an entity extraction expert. Extract the following entities from the text:
            - product_name: اسم المنتج أو الطبق
            - quantity: الكمية (number)
            - unit: وحدة القياس (kg, g, piece, etc.)
            - price: السعر (number)
            - order_id: رقم الطلب
            - customer_name: اسم العميل
            - customer_phone: رقم الهاتف
            - delivery_address: عنوان التوصيل
            - date: التاريخ
            - time: الوقت
            
            Output the result as a JSON array of entities.
            Each entity should have: type, value, confidence (0-1)
            """

            user_prompt = f"""
            Text: {text}
            Language: {language}
            
            Extract all entities from the text above.
            """

            response = await self.ai_client.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                max_tokens=500,
            )

            # استخراج JSON من الرد
            json_str = self._extract_json(response)

            if not json_str:
                return []

            import json

            entities = json.loads(json_str)

            if isinstance(entities, dict):
                # إذا كانت النتيجة قاموساً، نحولها إلى قائمة
                if "entities" in entities:
                    entities = entities["entities"]
                else:
                    entities = [entities]

            if not isinstance(entities, list):
                return []

            # تصفية الكيانات ذات الثقة المنخفضة
            return [
                e
                for e in entities
                if e.get("confidence", 0) >= self.confidence_threshold
            ]

        except Exception as e:
            logger.warning(
                "extract_entities_ai_error",
                extra={"error": str(e)},
            )
            return []

    # ==========================================
    # 🔍 EXTRACT WITH PATTERNS
    # ==========================================

    def _extract_with_patterns(
        self,
        *,
        text: str,
        language: LanguageCode,
    ) -> EntityList:
        """
        استخراج الكيانات باستخدام الأنماط.

        Args:
            text: النص المراد استخراج الكيانات منه
            language: رمز اللغة

        Returns:
            قائمة الكيانات المستخرجة
        """
        entities: EntityList = []

        # 1️⃣ استخراج أرقام الطلبات
        order_patterns = [
            r"\b(RST\d+-\d{6})\b",
            r"#?(\d{4,8})",
            r"رقم\s*الطلب\s*[#:]?\s*(\d+)",
            r"order\s*[#:]?\s*(\d+)",
            r"commande\s*[#:]?\s*(\d+)",
        ]

        for pattern in order_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                entities.append(
                    {
                        "type": "order_id",
                        "value": match.group(1),
                        "confidence": 0.9,
                    }
                )
                break

        # 2️⃣ استخراج الكميات
        quantity_patterns = [
            r"(?:quantity|qty)\s*(?:to|of)?\s*(\d+)",
            r"(?:change|set|make|update)\b.*\bquantity\b.*?\bto\s*(\d+)",
            r"(?:quantité)\s*(?:à|a|de)?\s*(\d+)",
            r"(?:chang\w*|modifi\w*|mett\w*)\s+(?:la\s+)?quantité.*?(?:à|a)\s*(\d+)",
            r"(?:الكمية|عدد الحبات)\s*(?:إلى|الى)?\s*(\d+)",
            r"(?:كمية)\s*.+?(?:إلى|الى)\s*(\d+)",
            r"(?:اجعل|خلي|بدلها)\s*(?:الكمية\s*)?(?:إلى|الى)?\s*(\d+)",
            r"(\d+)\s*(?:كيلو|كغم|غرام|قطعة|حبة|وحدة|كوب|ملعقة)",
            r"(\d+)\s*(?:kg|g|piece|unit|cup|spoon)",
            r"(\d+)\s*(?:kg|g|pièce|unité|cuillère)",
            r"(\d+)\s*(?:بيتزا|برجر|شاورما|وجبة|pizza|burger|repas)",
        ]

        for pattern in quantity_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                entities.append(
                    {
                        "type": "quantity",
                        "value": int(match.group(1)),
                        "confidence": 0.8,
                    }
                )
                break

        # 3️⃣ استخراج الأسعار
        price_patterns = [
            r"(\d+(?:\.\d{1,2})?)\s*(?:دج|دينار|da|dzd)",
            r"(\d+(?:\.\d{1,2})?)\s*(?:da|dzd)",
            r"(\d+(?:\.\d{1,2})?)\s*(?:€|eur|dollar|usd)",
            r"سعر\s*[هو]?\s*(\d+(?:\.\d{1,2})?)",
            r"price\s*(?:is)?\s*(\d+(?:\.\d{1,2})?)",
            r"prix\s*(?:est)?\s*(\d+(?:\.\d{1,2})?)",
            r"بسعر\s*(\d+(?:\.\d{1,2})?)",
            r"ب\s*(\d+(?:\.\d{1,2})?)\s*(?:دج|دينار)",
        ]

        for pattern in price_patterns:
            match = re.search(pattern, text)
            if match:
                entities.append(
                    {
                        "type": "price",
                        "value": float(match.group(1)),
                        "confidence": 0.9,
                    }
                )
                break

        # 4️⃣ استخراج أسماء المنتجات
        product_patterns = [
            r"(?:اطلب|اريد|ابغى|بدي|order|commander)\s*(?!(?:#?RST\d+-\d{6}|#?\d{4,8}\b))(.+?)(?:\s*$|\.|،)",
            r"(بيتزا|برجر|شاورما|فطيرة|كوكا|عصير|مشروب)",
            r"(pizza|burger|shawarma|drink|juice|coffee|tea)",
        ]

        for pattern in product_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                entities.append(
                    {
                        "type": "product_name",
                        "value": match.group(1).strip(),
                        "confidence": 0.7,
                    }
                )
                break

        # 5️⃣ استخراج أرقام الهواتف
        phone_patterns = [
            r"(0[567]\d{8})",
            r"(\+213\s*[567]\d{8})",
            r"(\+213\s*\d{9})",
            r"(05[567]\d{7})",
        ]

        for pattern in phone_patterns:
            match = re.search(pattern, text)
            if match:
                entities.append(
                    {
                        "type": "customer_phone",
                        "value": match.group(1),
                        "confidence": 0.9,
                    }
                )
                break

        # 6️⃣ استخراج أسماء العملاء
        name_patterns = [
            r"اسمي\s*(.+?)(?:\s*$|\.|،)",
            r"اسم العميل\s*(.+?)(?:\s*$|\.|،)",
            r"my name is\s*(.+?)(?:\s*$|\.|,)",
            r"je m\'appelle\s*(.+?)(?:\s*$|\.|,)",
        ]

        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                # التأكد من أن الاسم ليس طويلاً جداً
                if len(name) < 50:
                    entities.append(
                        {
                            "type": "customer_name",
                            "value": name,
                            "confidence": 0.7,
                        }
                    )
                break

        # 7️⃣ استخراج العناوين
        address_patterns = [
            r"(?:عنوان|العنوان|address|adresse)\s*(.+?)(?:\s*$|\.|،)",
            r"(?:في\s*)(.+?)(?:\s*$|\.|،)(?=.*شارع|.*street|.*rue)",
            r"(شارع|street|rue)\s*(.+?)(?:\s*$|\.|،)",
        ]

        for pattern in address_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                address = match.group(1).strip()
                if len(address) > 3:
                    entities.append(
                        {
                            "type": "delivery_address",
                            "value": address,
                            "confidence": 0.7,
                        }
                    )
                break

        # 8️⃣ استخراج التاريخ
        date_patterns = [
            r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"(\d{1,2}\s*(?:يناير|فبراير|مارس|أبريل|مايو|يونيو|يوليو|أغسطس|سبتمبر|أكتوبر|نوفمبر|ديسمبر)\s*\d{2,4})",
            r"(\d{1,2}\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*\d{2,4})",
        ]

        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                entities.append(
                    {
                        "type": "date",
                        "value": match.group(1),
                        "confidence": 0.8,
                    }
                )
                break

        # 9️⃣ استخراج الوقت
        time_patterns = [
            r"(\d{1,2}:\d{2})",
            r"(\d{1,2}\s*(?:صباحاً|مساءً|ص|م|am|pm))",
        ]

        for pattern in time_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                entities.append(
                    {
                        "type": "time",
                        "value": match.group(1),
                        "confidence": 0.8,
                    }
                )
                break

        # 🔟 استخراج وحدة القياس
        unit_patterns = [
            r"(كيلو|كغم|غرام|قطعة|حبة|وحدة|كوب|ملعقة|لتر)",
            r"(kg|g|piece|unit|cup|spoon|liter|l)",
        ]

        for pattern in unit_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                entities.append(
                    {
                        "type": "unit",
                        "value": match.group(1),
                        "confidence": 0.8,
                    }
                )
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
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            return match.group(0)

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return match.group(0)

        return None

    # ==============================================
    #  MERGE ENTITIES
    # ==============================================

    def _merge_entities(
        self,
        entities: EntityList,
    ) -> EntityList:
        """
        دمج الكيانات المكررة.

        Args:
            entities: قائمة الكيانات

        Returns:
            قائمة الكيانات المدمجة
        """
        merged: Dict[str, Dict[str, Any]] = {}

        for entity in entities:
            entity_type = entity.get("type")
            entity_value = entity.get("value")

            if not entity_type or entity_value is None:
                continue

            key = f"{entity_type}:{entity_value}"

            if key not in merged:
                merged[key] = entity
            else:
                # الاحتفاظ بالثقة الأعلى
                if entity.get("confidence", 0) > merged[key].get("confidence", 0):
                    merged[key]["confidence"] = entity["confidence"]

        return list(merged.values())

    # ==========================================
    # 🔍 GET ENTITY TYPES
    # ==========================================

    def get_entity_types(self) -> List[str]:
        """
        الحصول على قائمة أنواع الكيانات المدعومة.

        Returns:
            قائمة أنواع الكيانات
        """
        return [
            "product_name",
            "quantity",
            "unit",
            "price",
            "order_id",
            "customer_name",
            "customer_phone",
            "delivery_address",
            "date",
            "time",
        ]


# ==============================================
# 🔍 UTILITY FUNCTIONS
# ==============================================

# ==============================================
# EXTRACT ENTITIES
# ==============================================


async def extract_entities(
    *,
    text: str,
    language: Optional[LanguageCode] = None,
    extractor: Optional[EntityExtractor] = None,
) -> ExtractionResult:
    """
    استخراج الكيانات من النص (دالة مساعدة).

    Args:
        text: النص المراد استخراج الكيانات منه
        language: رمز اللغة (اختياري)
        extractor: مستخرج الكيانات (اختياري)

    Returns:
        نتيجة الاستخراج
    """
    logger.debug(
        "extract_entities_called",
        extra={
            "text_length": len(text) if text else 0,
            "language": language,
        },
    )

    if extractor is None:
        extractor = EntityExtractor()

    return await extractor.extract(
        text=text,
        language=language,
    )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "EntityExtractor",
    "extract_entities",
    "ExtractionResult",
    "EntityDict",
    "EntityList",
]
