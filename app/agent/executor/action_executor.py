# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# ⚡ ACTION EXECUTOR
# منفذ الإجراءات - يدير تنفيذ الإجراءات بناءً على النوايا
# ==============================================

"""MoulAI operational module for action executor.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from typing import (
    Any,
    Dict,
    Optional,
)

from app.agent.executor.actions import (
    ActionRegistry,
    BaseAction,
    action_registry,
)
from app.agent.nlu.intent_classifier import IntentResult
from app.core.logger import logger

# ==============================================
# 🧩 TYPES
# ==============================================

ExecutionResult = Dict[str, Any]
ConfirmationResponse = bool
ActionContext = Dict[str, Any]
EntityMap = Dict[str, Any]

# ==============================================
# ⚡ ACTION EXECUTOR
# ==============================================


class ActionExecutor:
    """
    منفذ الإجراءات - مسؤول عن تنفيذ الإجراءات بناءً على النوايا.

    مسؤول عن:
        - اختيار الإجراء المناسب للنية
        - إدارة عملية التأكيد (عند الحاجة)
        - تنفيذ الإجراءات
        - تجميع النتائج
        - معالجة الأخطاء

    Attributes:
        registry: سجل الإجراءات
        confirmation_handler: معالج التأكيد (اختياري)
    """

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        *,
        registry: Optional[ActionRegistry] = None,
        confirmation_handler: Optional[callable] = None,
    ) -> None:
        """
        تهيئة منفذ الإجراءات.

        Args:
            registry: سجل الإجراءات (اختياري)
            confirmation_handler: معالج التأكيد (اختياري)
        """
        self.registry: ActionRegistry = registry or action_registry
        self.confirmation_handler = confirmation_handler

        logger.info(
            "action_executor_initialized",
            extra={
                "action_count": len(self.registry.get_all()),
                "confirmation_handler": confirmation_handler is not None,
            },
        )

    # ==========================================
    # 🎯 EXECUTE ACTION
    # ==========================================

    async def execute(
        self,
        *,
        intent_result: IntentResult,
        context: Optional[ActionContext] = None,
    ) -> ExecutionResult:
        """
        تنفيذ الإجراء المناسب للنية.

        Args:
            intent_result: نتيجة تصنيف النية
            context: سياق التنفيذ (اختياري)

        Returns:
            ExecutionResult: {
                "success": bool,
                "action": str,
                "message": str,
                "data": Dict,
                "requires_confirmation": bool,
                "confirmed": bool (إذا كان يحتاج تأكيد),
                "error": str (في حالة الفشل),
            }
        """
        intent: str = intent_result.get("intent", "unknown")
        entities: EntityMap = intent_result.get("entities", {})
        confidence: float = intent_result.get("confidence", 0.0)
        language: str = intent_result.get("language", "ar")

        logger.info(
            "executor_executing",
            extra={
                "intent": intent,
                "confidence": confidence,
                "language": language,
            },
        )

        # 1️⃣ التحقق من صحة النية
        if intent == "unknown" or intent not in self.registry.get_names():
            logger.warning(
                "executor_unknown_intent",
                extra={"intent": intent},
            )
            return self._create_error_result(
                action="unknown",
                message="آسف، لم أفهم طلبك. يمكنك كتابة 'مساعدة' لمعرفة الخدمات المتاحة.",
                error="unknown_intent",
            )

        # 2️⃣ الحصول على الإجراء المناسب
        action = self.registry.get_by_intent(intent)
        if not action:
            logger.warning(
                "executor_no_action_for_intent",
                extra={"intent": intent},
            )
            return self._create_error_result(
                action=intent,
                message="آسف، لا يمكنني تنفيذ هذا الطلب حالياً.",
                error="action_not_found",
            )

        # 3️⃣ بناء معاملات الإجراء
        params = self._build_action_params(
            entities=entities,
            context=context,
            language=language,
        )

        # 4️⃣ التحقق من الحاجة للتأكيد
        if action.requires_confirmation:
            if self.confirmation_handler is None:
                prepare = getattr(action, "prepare", None)
                if prepare:
                    try:
                        preview = await prepare(params=params, context=context)
                    except Exception as e:
                        logger.exception(
                            "executor_action_preparation_failed",
                            extra={"action": action.name, "error": str(e)},
                        )
                        return self._create_error_result(
                            action=action.name,
                            message="تعذر إعداد العملية لمراجعتها.",
                            error="action_failed",
                        )
                    if not preview.success:
                        return {
                            "success": False,
                            "action": action.name,
                            "message": preview.message,
                            "data": preview.data or {},
                            "requires_confirmation": True,
                            "confirmed": False,
                            "error": preview.error,
                        }
                    params.update(preview.data or {})
                    confirmation_message = preview.message
                    language_prompt = {
                        "ar": "\n\nهل تؤكد الطلب؟ (نعم/لا)",
                        "fr": "\n\nConfirmer cette commande ? (Oui/Non)",
                        "en": "\n\nConfirm this order? (Yes/No)",
                    }
                    confirmation_message += language_prompt.get(
                        language, language_prompt["en"]
                    )
                else:
                    confirmation_message = self._build_confirmation_message(
                        action=action,
                        params=params,
                    )
                return {
                    "success": True,
                    "action": action.name,
                    "message": confirmation_message,
                    "data": {
                        "pending_confirmation": True,
                        "params": {
                            key: value
                            for key, value in params.items()
                            if key
                            not in {
                                "history",
                                "context",
                                "request_context",
                                "session_id",
                            }
                        },
                        "context": {
                            "user_id": context.get("user_id") if context else None,
                            "channel": context.get("channel") if context else None,
                            "language": language,
                            "request_context": (
                                context.get("request_context", {}) if context else {}
                            ),
                        },
                    },
                    "requires_confirmation": True,
                    "confirmed": False,
                    "error": None,
                }

            # طلب تأكيد من المستخدم
            confirmed = await self._request_confirmation(
                action=action,
                params=params,
                context=context,
            )

            if not confirmed:
                logger.info(
                    "executor_action_cancelled",
                    extra={
                        "action": action.name,
                        "intent": intent,
                    },
                )
                return {
                    "success": False,
                    "action": action.name,
                    "message": "تم إلغاء العملية.",
                    "data": {},
                    "requires_confirmation": True,
                    "confirmed": False,
                    "error": None,
                }

        # 5️⃣ تنفيذ الإجراء
        try:
            logger.info(
                "executor_executing_action",
                extra={
                    "action": action.name,
                    "params": params,
                },
            )

            result = await action.execute(
                params=params,
                context=context,
            )

            # 6️⃣ معالجة النتيجة
            return {
                "success": result.success,
                "action": action.name,
                "message": result.message,
                "data": result.data or {},
                "requires_confirmation": action.requires_confirmation,
                "confirmed": True if action.requires_confirmation else None,
                "error": result.error,
            }

        except Exception as e:
            logger.exception(
                "executor_action_failed",
                extra={
                    "action": action.name,
                    "intent": intent,
                    "error": str(e),
                },
            )
            return self._create_error_result(
                action=action.name,
                message="حدث خطأ أثناء تنفيذ الطلب. يرجى المحاولة مرة أخرى.",
                error="action_failed",
            )

    # ==========================================
    # 🛠️ PRIVATE HELPERS
    # ==========================================

    def _build_action_params(
        self,
        *,
        entities: EntityMap,
        context: Optional[ActionContext] = None,
        language: str = "ar",
    ) -> Dict[str, Any]:
        """
        بناء معاملات الإجراء من الكيانات والسياق.

        Args:
            entities: الكيانات المستخرجة
            context: سياق التنفيذ (اختياري)
            language: رمز اللغة

        Returns:
            معاملات الإجراء
        """
        params: Dict[str, Any] = {
            "language": language,
        }

        # إضافة الكيانات إلى المعاملات
        for key, value in entities.items():
            if value is not None:
                params[key] = value

        # إضافة السياق إلى المعاملات
        if context:
            for key, value in context.items():
                if key not in params and value is not None:
                    params[key] = value

        return params

    # ==============================================
    #  REQUEST CONFIRMATION
    # ==============================================

    async def _request_confirmation(
        self,
        *,
        action: BaseAction,
        params: Dict[str, Any],
        context: Optional[ActionContext] = None,
    ) -> ConfirmationResponse:
        """
        طلب تأكيد من المستخدم.

        Args:
            action: الإجراء المطلوب تأكيده
            params: معاملات الإجراء
            context: سياق التنفيذ

        Returns:
            True إذا تم التأكيد، False إذا تم الإلغاء
        """
        # بناء رسالة التأكيد
        confirmation_message = self._build_confirmation_message(
            action=action,
            params=params,
        )

        # تغيير المفتاح من 'message' إلى 'confirmation_message' لتجنب التعارض
        logger.info(
            "executor_requesting_confirmation",
            extra={
                "action": action.name,
                "confirmation_message": confirmation_message,
            },
        )

        # استخدام معالج التأكيد إذا كان متاحاً
        if self.confirmation_handler:
            try:
                return await self.confirmation_handler(
                    action=action,
                    params=params,
                    message=confirmation_message,
                    context=context,
                )
            except Exception as e:
                logger.error(
                    "executor_confirmation_handler_failed",
                    extra={
                        "action": action.name,
                        "error": str(e),
                    },
                )
                # في حالة فشل المعالج، نرفض التنفيذ
                return False

        # لا يجوز تنفيذ إجراء يتطلب تأكيداً دون موافقة صريحة.
        logger.warning(
            "executor_no_confirmation_handler",
            extra={"action": action.name},
        )
        return False

    # ==============================================
    #  BUILD CONFIRMATION MESSAGE
    # ==============================================

    def _build_confirmation_message(
        self,
        *,
        action: BaseAction,
        params: Dict[str, Any],
    ) -> str:
        """
        بناء رسالة التأكيد.

        Args:
            action: الإجراء المطلوب تأكيده
            params: معاملات الإجراء

        Returns:
            رسالة التأكيد
        """
        language = params.get("language", "ar")
        action_name = self._get_action_display_name(action.name, language)

        # بناء رسالة حسب اللغة
        if language == "ar":
            message = f"📋 **تأكيد {action_name}**\n\n"
            message += self._format_params_arabic(params)
            message += "\n\nهل تريد تأكيد العملية؟ (نعم/لا)"
        elif language == "fr":
            message = f"📋 **Confirmation de {action_name}**\n\n"
            message += self._format_params_french(params)
            message += "\n\nVoulez-vous confirmer ? (Oui/Non)"
        else:  # English default
            message = f"📋 **Confirm {action_name}**\n\n"
            message += self._format_params_english(params)
            message += "\n\nDo you want to confirm? (Yes/No)"

        return message

    # ==============================================
    #  FORMAT PARAMS ARABIC
    # ==============================================

    def _format_params_arabic(self, params: Dict[str, Any]) -> str:
        """
        تنسيق المعاملات بالعربية.

        Args:
            params: معاملات الإجراء

        Returns:
            النص المنسق
        """
        lines = []

        # خريطة الترجمة العربية
        labels = {
            "product_name": "المنتج",
            "quantity": "الكمية",
            "price": "السعر",
            "order_id": "رقم الطلب",
            "customer_name": "اسم العميل",
            "customer_phone": "رقم الهاتف",
            "delivery_address": "عنوان التوصيل",
            "date": "التاريخ",
            "time": "الوقت",
        }

        for key, value in params.items():
            if key in labels and value is not None:
                lines.append(f"**{labels[key]}:** {value}")

        return "\n".join(lines) if lines else "**لا توجد معلومات إضافية**"

    # ==============================================
    #  FORMAT PARAMS ENGLISH
    # ==============================================

    def _format_params_english(self, params: Dict[str, Any]) -> str:
        """
        تنسيق المعاملات بالإنجليزية.

        Args:
            params: معاملات الإجراء

        Returns:
            النص المنسق
        """
        lines = []

        labels = {
            "product_name": "Product",
            "quantity": "Quantity",
            "price": "Price",
            "order_id": "Order ID",
            "customer_name": "Customer Name",
            "customer_phone": "Phone Number",
            "delivery_address": "Delivery Address",
            "date": "Date",
            "time": "Time",
        }

        for key, value in params.items():
            if key in labels and value is not None:
                lines.append(f"**{labels[key]}:** {value}")

        return "\n".join(lines) if lines else "**No additional information**"

    # ==============================================
    #  FORMAT PARAMS FRENCH
    # ==============================================

    def _format_params_french(self, params: Dict[str, Any]) -> str:
        """
        تنسيق المعاملات بالفرنسية.

        Args:
            params: معاملات الإجراء

        Returns:
            النص المنسق
        """
        lines = []

        labels = {
            "product_name": "Produit",
            "quantity": "Quantité",
            "price": "Prix",
            "order_id": "Numéro de commande",
            "customer_name": "Nom du client",
            "customer_phone": "Téléphone",
            "delivery_address": "Adresse de livraison",
            "date": "Date",
            "time": "Heure",
        }

        for key, value in params.items():
            if key in labels and value is not None:
                lines.append(f"**{labels[key]}:** {value}")

        return "\n".join(lines) if lines else "**Aucune information supplémentaire**"

    # ==============================================
    #  GET ACTION DISPLAY NAME
    # ==============================================

    def _get_action_display_name(
        self,
        action_name: str,
        language: str,
    ) -> str:
        """
        الحصول على اسم الإجراء المعروض.

        Args:
            action_name: اسم الإجراء
            language: رمز اللغة

        Returns:
            اسم الإجراء المعروض
        """
        names = {
            "order_food": {
                "ar": "الطلب",
                "en": "Order",
                "fr": "Commande",
            },
            "modify_order": {
                "ar": "تعديل الطلب",
                "en": "Modify Order",
                "fr": "Modifier la commande",
            },
            "cancel_order": {
                "ar": "إلغاء الطلب",
                "en": "Cancel Order",
                "fr": "Annuler la commande",
            },
            "complaint": {
                "ar": "الشكوى",
                "en": "Complaint",
                "fr": "Réclamation",
            },
        }

        return names.get(action_name, {}).get(language, action_name)

    # ==============================================
    #  CREATE ERROR RESULT
    # ==============================================

    def _create_error_result(
        self,
        *,
        action: str,
        message: str,
        error: str,
    ) -> ExecutionResult:
        """
        إنشاء نتيجة خطأ.

        Args:
            action: اسم الإجراء
            message: رسالة الخطأ للمستخدم
            error: رسالة الخطأ التقنية

        Returns:
            نتيجة الخطأ
        """
        return {
            "success": False,
            "action": action,
            "message": message,
            "data": {},
            "requires_confirmation": False,
            "confirmed": None,
            "error": error,
        }


# ==============================================
# 🌍 GLOBAL INSTANCE
# ==============================================

# إنشاء منفذ إجراءات عالمي
action_executor = ActionExecutor()


# ==============================================
# 🔍 UTILITY FUNCTIONS
# ==============================================

# ==============================================
# EXECUTE ACTION
# ==============================================


async def execute_action(
    *,
    intent_result: IntentResult,
    context: Optional[ActionContext] = None,
    executor: Optional[ActionExecutor] = None,
) -> ExecutionResult:
    """
    تنفيذ إجراء بناءً على النية (دالة مساعدة).

    Args:
        intent_result: نتيجة تصنيف النية
        context: سياق التنفيذ (اختياري)
        executor: منفذ الإجراءات (اختياري)

    Returns:
        نتيجة التنفيذ
    """
    logger.debug(
        "execute_action_called",
        extra={
            "intent": intent_result.get("intent"),
            "confidence": intent_result.get("confidence"),
        },
    )

    if executor is None:
        executor = action_executor

    return await executor.execute(
        intent_result=intent_result,
        context=context,
    )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "ActionExecutor",
    "action_executor",
    "execute_action",
    "ExecutionResult",
    "ActionContext",
]
