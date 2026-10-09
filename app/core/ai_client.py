# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🤖 AI CLIENT
# مسؤول عن التواصل مع نماذج الذكاء الاصطناعي
# يدعم OpenAI و DeepSeek
# ==============================================

"""MoulAI operational module for ai client.

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

from openai import OpenAI

from app.core.config import settings
from app.core.logger import logger

# ==============================================
# 🧩 TYPES
# ==============================================

AIMessage = Dict[str, str]
AIMessages = List[AIMessage]
AIResponse = Dict[str, Any]

# ==============================================
# 🤖 AI CLIENT
# ==============================================


class AIClient:
    """
    عميل موحد للذكاء الاصطناعي

    يدعم:
        - OpenAI (GPT-4, GPT-4o-mini, etc.)
        - DeepSeek (deepseek-chat, deepseek-reasoner)

    Attributes:
        client: عميل OpenAI
        model: اسم النموذج المستخدم
        enabled: هل العميل مفعّل؟
        api_key: مفتاح API
        base_url: رابط API
    """

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        """
        تهيئة العميل مع الإعدادات من .env

        Args:
            api_key: مفتاح API (اختياري)
            base_url: رابط API (اختياري)
            model: اسم النموذج (اختياري)
        """
        self.api_key: str = api_key or settings.OPENAI_API_KEY or ""
        self.base_url: str = (
            base_url or settings.OPENAI_BASE_URL or "https://api.openai.com/v1"
        )
        self.model: str = model or settings.AI_MODEL or "gpt-3.5-turbo"

        # تحديد ما إذا كان العميل مفعلاً
        self.enabled: bool = bool(self.api_key and len(self.api_key) > 0)

        # إنشاء العميل فقط إذا كان مفعلاً
        if self.enabled:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
        else:
            self.client = None

        logger.info(
            "ai_client_initialized",
            extra={
                "model": self.model,
                "base_url": self.base_url,
                "enabled": self.enabled,
            },
        )

    # ==========================================
    # 🗣️ CHAT
    # ==========================================

    async def chat(
        self,
        *,
        message: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> str:
        """
        إرسال رسالة والحصول على رد من الذكاء الاصطناعي

        Args:
            message: رسالة المستخدم
            system_prompt: تعليمات النظام (اختياري)
            temperature: درجة الحرارة (0.0 - 1.0)
            max_tokens: الحد الأقصى للرموز

        Returns:
            رد الذكاء الاصطناعي
        """
        # التحقق من التفعيل
        if not self.enabled or self.client is None:
            logger.warning(
                "ai_client_not_enabled",
                extra={"configuration_error": "API key not configured"},
            )
            return "عذراً، خدمة الذكاء الاصطناعي غير مفعلة. يرجى الاتصال بالدعم."

        try:
            messages: AIMessages = []

            # إضافة تعليمات النظام
            if system_prompt:
                messages.append(
                    {
                        "role": "system",
                        "content": system_prompt,
                    }
                )
            else:
                messages.append(
                    {
                        "role": "system",
                        "content": "أنت مساعد ذكي للمطاعم، تتحدث العربية والفرنسية والإنجليزية.",
                    }
                )

            # إضافة رسالة المستخدم
            messages.append(
                {
                    "role": "user",
                    "content": message,
                }
            )

            # إرسال الطلب
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # استخراج الرد
            reply = response.choices[0].message.content

            logger.debug(
                "ai_chat_success",
                extra={
                    "message_length": len(message),
                    "reply_length": len(reply) if reply else 0,
                },
            )

            return reply or ""

        except Exception as e:
            logger.exception(
                "ai_chat_failed",
                extra={
                    "error": str(e),
                    "request_message_excerpt": message[:100],
                },
            )
            return "عذراً، حدث خطأ في معالجة طلبك. يرجى المحاولة مرة أخرى."

    # ==========================================
    # 💬 CHAT COMPLETION (للتوافق مع intent_classifier)
    # ==========================================

    async def chat_completion(
        self,
        *,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 500,
        stream: bool = False,
    ) -> str:
        """
        إجراء مكالمة Chat Completion (متوافقة مع intent_classifier).

        Args:
            messages: قائمة الرسائل
            temperature: درجة الحرارة
            max_tokens: الحد الأقصى للرموز
            stream: تدفق النتيجة

        Returns:
            رد النموذج
        """
        # استخراج آخر رسالة للمستخدم
        user_message = ""
        system_prompt = None

        for msg in messages:
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
            elif msg.get("role") == "system":
                system_prompt = msg.get("content", "")

        return await self.chat(
            message=user_message,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    # ==========================================
    # 📊 ANALYZE ORDER
    # ==========================================

    async def analyze_order(
        self,
        *,
        order_text: str,
    ) -> AIResponse:
        """
        تحليل طلب العميل واستخراج المنتجات

        Args:
            order_text: نص الطلب

        Returns:
            قاموس يحتوي على المنتجات والملاحظات
        """
        system_prompt = """
        أنت مساعد مطعم ذكي. مهمتك تحليل طلبات العملاء واستخراج:
        1. المنتجات المطلوبة
        2. الكميات
        3. الملاحظات (مثل: بدون زيتون، إضافة جبن)
        4. الاقتراحات (Upselling)

        أخرج النتيجة بصيغة JSON.
        """

        response = await self.chat(
            message=order_text,
            system_prompt=system_prompt,
        )

        # محاولة تحويل الرد إلى JSON
        try:
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except (json.JSONDecodeError, AttributeError):
            pass

        # إذا فشل التحويل، أرجع النص كامل
        return {
            "raw_response": response,
            "products": [],
            "notes": order_text,
        }


# ==============================================
# 🌍 GLOBAL INSTANCE
# ==============================================

ai_client = AIClient()


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "AIClient",
    "ai_client",
    "AIMessage",
    "AIMessages",
    "AIResponse",
]
