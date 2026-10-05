# ==============================================
# MoulAI Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine
# ==============================================

# ==============================================
# 💬 RESPONSE GENERATOR
# توليد الردود الذكية
# ==============================================

from typing import (
    Any,
    Dict,
    List,
    Optional,
    Union,
)

from app.agent.config import LanguageCode
from app.agent.executor.actions import ActionResponse
from app.agent.prompts.templates import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    get_error_prompt,
    get_response_generation_prompt,
    get_success_prompt,
)
from app.agent.prompts.translations import (
    ERROR_RESPONSES,
    GOODBYE_RESPONSES,
    GREETING_RESPONSES,
    HELP_RESPONSES,
)
from app.core.ai_client import AIClient
from app.core.logger import logger

# ==============================================
# 🧩 TYPES
# ==============================================

ResponseContext = Dict[str, Any]
ResponseResult = Dict[str, Any]
MessageHistory = List[Dict[str, Any]]

# ==============================================
# 💬 RESPONSE GENERATOR
# ==============================================


class ResponseGenerator:
    """
    مولد الردود - مسؤول عن توليد ردود طبيعية وذكية.
    
    مسؤول عن:
        - توليد ردود بناءً على السياق والنية
        - تخصيص الردود حسب اللغة والمستخدم
        - استخدام الذكاء الاصطناعي لتوليد ردود متقدمة
        - التعامل مع الحالات الخاصة (تحية، وداع، مساعدة)
    
    Attributes:
        ai_client: عميل الذكاء الاصطناعي
        use_ai: تفعيل الذكاء الاصطناعي لتوليد الردود
    """

    def __init__(
        self,
        *,
        ai_client: Optional[AIClient] = None,
        use_ai: bool = True,
    ) -> None:
        """
        تهيئة مولد الردود.
        
        Args:
            ai_client: عميل الذكاء الاصطناعي (اختياري)
            use_ai: تفعيل الذكاء الاصطناعي لتوليد الردود
        """
        self.ai_client: AIClient = ai_client or AIClient()
        self.use_ai: bool = use_ai and self.ai_client.enabled

        logger.info(
            "response_generator_initialized",
            extra={
                "use_ai": self.use_ai,
                "ai_enabled": self.ai_client.enabled,
            },
        )

    # ==========================================
    # 🎯 GENERATE RESPONSE
    # ==========================================

    async def generate(
        self,
        *,
        intent: str,
        language: LanguageCode,
        action_result: Optional[ActionResponse] = None,
        context: Optional[ResponseContext] = None,
        user_message: Optional[str] = None,
        history: Optional[MessageHistory] = None,
        entities: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        توليد رد مناسب حسب السياق.
        
        Args:
            intent: النية المستخرجة
            language: رمز اللغة
            action_result: نتيجة تنفيذ الإجراء (اختياري)
            context: سياق المحادثة (اختياري)
            user_message: رسالة المستخدم الأصلية (اختياري)
            history: تاريخ المحادثة (اختياري)
            entities: الكيانات المستخرجة (اختياري)
            
        Returns:
            الرد النهائي
        """
        # اللغة الافتراضية
        if language not in SUPPORTED_LANGUAGES:
            language = DEFAULT_LANGUAGE

        logger.info(
            "response_generator_started",
            extra={
                "intent": intent,
                "language": language,
                "has_action_result": action_result is not None,
            },
        )

        # 1️⃣ الحالات الخاصة
        special_response = await self._get_special_response(
            intent=intent,
            language=language,
            action_result=action_result,
        )
        if special_response:
            return special_response

        # 2️⃣ استخدام الذكاء الاصطناعي لتوليد الرد
        if self.use_ai and action_result:
            ai_response = await self._generate_with_ai(
                intent=intent,
                language=language,
                action_result=action_result,
                context=context or {},
                user_message=user_message or "",
                history=history or [],
                entities=entities or {},
            )
            if ai_response:
                return ai_response

        # 3️⃣ استخدام القوالب الجاهزة
        template_response = self._generate_with_templates(
            intent=intent,
            language=language,
            action_result=action_result,
            entities=entities or {},
        )
        if template_response:
            return template_response

        # 4️⃣ رد افتراضي
        return self._get_default_response(language=language)

    # ==========================================
    # 🔍 SPECIAL RESPONSES
    # ==========================================

    async def _get_special_response(
        self,
        *,
        intent: str,
        language: LanguageCode,
        action_result: Optional[ActionResponse] = None,
    ) -> Optional[str]:
        """
        الحصول على ردود خاصة للحالات المحددة.
        
        Args:
            intent: النية
            language: رمز اللغة
            action_result: نتيجة الإجراء
            
        Returns:
            الرد الخاص أو None
        """
        # تحية
        if intent == "greeting":
            return GREETING_RESPONSES.get(
                language,
                GREETING_RESPONSES[DEFAULT_LANGUAGE],
            )

        # وداع
        if intent == "goodbye":
            return GOODBYE_RESPONSES.get(
                language,
                GOODBYE_RESPONSES[DEFAULT_LANGUAGE],
            )

        # مساعدة
        if intent == "help":
            return HELP_RESPONSES.get(
                language,
                HELP_RESPONSES[DEFAULT_LANGUAGE],
            )

        # خطأ
        if action_result and not action_result.success:
            error = action_result.error or "unknown"
            return get_error_prompt(
                error_type=error,
                language=language,
            )

        # إذا كان الإجراء ناجحاً ولديه رسالة
        if action_result and action_result.success and action_result.message:
            return action_result.message

        return None

    # ==========================================
    # 🤖 AI GENERATION
    # ==========================================

    async def _generate_with_ai(
        self,
        *,
        intent: str,
        language: LanguageCode,
        action_result: ActionResponse,
        context: Dict[str, Any],
        user_message: str,
        history: List[Dict[str, Any]],
        entities: Dict[str, Any],
    ) -> Optional[str]:
        """
        توليد رد باستخدام الذكاء الاصطناعي.
        
        Args:
            intent: النية
            language: رمز اللغة
            action_result: نتيجة الإجراء
            context: سياق المحادثة
            user_message: رسالة المستخدم
            history: تاريخ المحادثة
            entities: الكيانات المستخرجة
            
        Returns:
            الرد المولد أو None
        """
        try:
            # بناء الـ Prompt
            prompt = get_response_generation_prompt(language=language).format(
                intent=intent,
                context=self._format_context(context),
                entities=self._format_entities(entities),
                action_result=self._format_action_result(action_result),
                user_message=user_message,
            )

            # استدعاء الذكاء الاصطناعي
            response = await self.ai_client.chat(
                message=prompt,
                system_prompt="أنت مساعد ذكي ومفيد. تولد ردوداً طبيعية ومفيدة.",
                temperature=0.7,
                max_tokens=500,
            )

            if response:
                logger.debug(
                    "response_generator_ai_success",
                    extra={
                        "intent": intent,
                        "response_length": len(response),
                    },
                )
                return response

        except Exception as e:
            logger.warning(
                "response_generator_ai_failed",
                extra={
                    "intent": intent,
                    "error": str(e),
                },
            )

        return None

    # ==========================================
    # 📝 TEMPLATE GENERATION
    # ==========================================

    def _generate_with_templates(
        self,
        *,
        intent: str,
        language: LanguageCode,
        action_result: Optional[ActionResponse] = None,
        entities: Dict[str, Any],
    ) -> Optional[str]:
        """
        توليد رد باستخدام القوالب الجاهزة.
        
        Args:
            intent: النية
            language: رمز اللغة
            action_result: نتيجة الإجراء
            entities: الكيانات المستخرجة
            
        Returns:
            الرد المولد أو None
        """
        if not action_result:
            return None

        if not action_result.success:
            return get_error_prompt(
                error_type=action_result.error or "unknown",
                language=language,
            )

        # نجاح الإجراء
        success_type = self._get_success_type(intent)
        if success_type:
            data = {**entities, **(action_result.data or {})}
            return get_success_prompt(
                success_type=success_type,
                language=language,
                **data,
            )

        return action_result.message

    def _get_success_type(self, intent: str) -> Optional[str]:
        """
        تحديد نوع النجاح بناءً على النية.
        
        Args:
            intent: النية
            
        Returns:
            نوع النجاح أو None
        """
        mapping = {
            "order_food": "order_created",
            "cancel_order": "order_cancelled",
            "track_order": "order_tracked",
            "ask_price": "price_found",
            "ask_offer": "offers_found",
        }
        return mapping.get(intent)

    # ==========================================
    # 🛠️ HELPERS
    # ==========================================

    def _format_context(self, context: Dict[str, Any]) -> str:
        """
        تنسيق السياق للنص.
        
        Args:
            context: سياق المحادثة
            
        Returns:
            السياق المنسق
        """
        if not context:
            return "لا يوجد سياق"

        lines = []
        for key, value in context.items():
            if value:
                lines.append(f"- {key}: {value}")

        return "\n".join(lines) if lines else "لا يوجد سياق"

    def _format_entities(self, entities: Dict[str, Any]) -> str:
        """
        تنسيق الكيانات للنص.
        
        Args:
            entities: الكيانات المستخرجة
            
        Returns:
            الكيانات المنسقة
        """
        if not entities:
            return "لا توجد كيانات"

        lines = []
        for key, value in entities.items():
            if value is not None:
                lines.append(f"- {key}: {value}")

        return "\n".join(lines) if lines else "لا توجد كيانات"

    def _format_action_result(self, action_result: ActionResponse) -> str:
        """
        تنسيق نتيجة الإجراء للنص.
        
        Args:
            action_result: نتيجة الإجراء
            
        Returns:
            النتيجة المنسقة
        """
        if not action_result:
            return "لا توجد نتيجة"

        lines = [
            f"- نجاح: {action_result.success}",
            f"- رسالة: {action_result.message}",
        ]

        if action_result.data:
            lines.append(f"- بيانات: {action_result.data}")

        if action_result.error:
            lines.append(f"- خطأ: {action_result.error}")

        return "\n".join(lines)

    def _get_default_response(self, language: LanguageCode) -> str:
        """
        الحصول على رد افتراضي.
        
        Args:
            language: رمز اللغة
            
        Returns:
            الرد الافتراضي
        """
        default_responses = {
            "ar": "آسف، لم أتمكن من معالجة طلبك. يرجى المحاولة مرة أخرى.",
            "en": "Sorry, I couldn't process your request. Please try again.",
            "fr": "Désolé, je n'ai pas pu traiter votre demande. Veuillez réessayer.",
        }
        return default_responses.get(
            language,
            default_responses[DEFAULT_LANGUAGE],
        )


# ==============================================
# 🌍 GLOBAL INSTANCE
# ==============================================

response_generator = ResponseGenerator()


# ==============================================
# 🔍 UTILITY FUNCTIONS
# ==============================================

# ==============================================
# GENERATE RESPONSE
# ==============================================

async def generate_response(
    *,
    intent: str,
    language: LanguageCode,
    action_result: Optional[ActionResponse] = None,
    context: Optional[ResponseContext] = None,
    user_message: Optional[str] = None,
    history: Optional[MessageHistory] = None,
    entities: Optional[Dict[str, Any]] = None,
    generator: Optional[ResponseGenerator] = None,
) -> str:
    """
    توليد رد (دالة مساعدة).
    
    Args:
        intent: النية
        language: رمز اللغة
        action_result: نتيجة الإجراء
        context: سياق المحادثة
        user_message: رسالة المستخدم
        history: تاريخ المحادثة
        entities: الكيانات المستخرجة
        generator: مولد الردود (اختياري)
        
    Returns:
        الرد المولد
    """
    logger.debug(
        "generate_response_called",
        extra={
            "intent": intent,
            "language": language,
            "has_action_result": action_result is not None,
        },
    )

    if generator is None:
        generator = response_generator

    return await generator.generate(
        intent=intent,
        language=language,
        action_result=action_result,
        context=context,
        user_message=user_message,
        history=history,
        entities=entities,
    )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "ResponseGenerator",
    "response_generator",
    "generate_response",
    "ResponseContext",
    "ResponseResult",
]