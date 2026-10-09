# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🧠 MEMORY MANAGER
# إدارة الذاكرة والسياق للمحادثات
# ==============================================

"""MoulAI operational module for memory manager.

Part of MoulAI Platform - Agent-as-a-Service.
"""

import json
import hashlib
from datetime import datetime
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from app.agent.config import default_config
from app.core.logger import logger

# ==============================================
# 🧩 TYPES
# ==============================================

Message = Dict[str, Any]
SessionData = Dict[str, Any]
ContextData = Dict[str, Any]
MemoryEntry = Dict[str, Any]
ConversationHistory = List[Message]

# ==============================================
# 🧠 MEMORY MANAGER
# ==============================================


class MemoryManager:
    """
    مدير الذاكرة - يدير سياق المحادثة والذاكرة.

    مسؤول عن:
        - تخزين واسترجاع سياق المحادثة
        - إدارة الجلسات
        - الحفاظ على تاريخ المحادثة
        - استخراج المعلومات المهمة من السياق

    Attributes:
        redis_client: عميل Redis (اختياري)
        max_history: الحد الأقصى لرسائل السياق
        session_timeout: مهلة الجلسة (ثواني)
    """

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        *,
        redis_client: Optional[Any] = None,
        max_history: Optional[int] = None,
        session_timeout: Optional[int] = None,
    ) -> None:
        """
        تهيئة مدير الذاكرة.

        Args:
            redis_client: عميل Redis (اختياري)
            max_history: الحد الأقصى لرسائل السياق
            session_timeout: مهلة الجلسة (ثواني)
        """
        self.redis_client: Optional[Any] = redis_client or redis_client
        self.max_history: int = max_history or default_config.max_history
        self.session_timeout: int = session_timeout or default_config.session_timeout

        # تخزين محلي للجلسات (في حالة عدم وجود Redis)
        self._local_memory: Dict[str, SessionData] = {}

        logger.info(
            "memory_manager_initialized",
            extra={
                "max_history": self.max_history,
                "session_timeout": self.session_timeout,
                "redis_enabled": self.redis_client is not None,
            },
        )

    # ==========================================
    # 📝 SESSION MANAGEMENT
    # ==========================================

    async def create_session(
        self,
        *,
        session_id: str,
        user_id: int,
        initial_context: Optional[ContextData] = None,
    ) -> SessionData:
        """
        إنشاء جلسة جديدة.

        Args:
            session_id: معرف الجلسة
            user_id: معرف المستخدم
            initial_context: السياق الأولي (اختياري)

        Returns:
            بيانات الجلسة
        """
        session: SessionData = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "context": initial_context or {},
            "history": [],
            "entities": {},
            "last_intent": None,
            "last_action": None,
        }

        # تخزين الجلسة
        await self._save_session(session)

        logger.info(
            "memory_session_created",
            extra={
                "session_id": session_id,
                "user_id": user_id,
            },
        )

        return session

    # ==============================================
    # GET SESSION
    # ==============================================

    async def get_session(
        self,
        *,
        session_id: str,
    ) -> Optional[SessionData]:
        """
        الحصول على جلسة.

        Args:
            session_id: معرف الجلسة

        Returns:
            بيانات الجلسة أو None
        """
        session = await self._load_session(session_id)

        if not session:
            logger.debug(
                "memory_session_not_found",
                extra={"session_id": session_id},
            )
            return None

        # تحديث وقت آخر نشاط
        session["updated_at"] = datetime.now().isoformat()
        await self._save_session(session)

        return session

    # ==============================================
    # UPDATE SESSION
    # ==============================================

    async def update_session(
        self,
        *,
        session_id: str,
        updates: Dict[str, Any],
    ) -> Optional[SessionData]:
        """
        تحديث جلسة.

        Args:
            session_id: معرف الجلسة
            updates: بيانات التحديث

        Returns:
            بيانات الجلسة المحدثة أو None
        """
        session = await self._load_session(session_id)

        if not session:
            logger.warning(
                "memory_session_update_failed",
                extra={"session_id": session_id},
            )
            return None

        # تطبيق التحديثات
        for key, value in updates.items():
            if key in session:
                session[key] = value

        session["updated_at"] = datetime.now().isoformat()

        # حفظ الجلسة المحدثة
        await self._save_session(session)

        logger.debug(
            "memory_session_updated",
            extra={
                "session_id": session_id,
                "updates": list(updates.keys()),
            },
        )

        return session

    # ==============================================
    # DELETE SESSION
    # ==============================================

    async def delete_session(
        self,
        *,
        session_id: str,
    ) -> bool:
        """
        حذف جلسة.

        Args:
            session_id: معرف الجلسة

        Returns:
            True إذا تم الحذف، False إذا لم يتم
        """
        if self.redis_client:
            key = self._get_session_key(session_id)
            deleted = await self.redis_client.delete(key) > 0
        else:
            deleted = session_id in self._local_memory
            if deleted:
                del self._local_memory[session_id]

        if deleted:
            logger.info(
                "memory_session_deleted",
                extra={"session_id": session_id},
            )
        else:
            logger.warning(
                "memory_session_delete_failed",
                extra={"session_id": session_id},
            )

        return deleted

    # ==========================================
    # 💬 MESSAGE MANAGEMENT
    # ==========================================

    async def add_message(
        self,
        *,
        session_id: str,
        message: str,
        role: str = "user",
        metadata: Optional[Dict[str, Any]] = None,
        intent: Optional[str] = None,
        entities: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        إضافة رسالة إلى تاريخ المحادثة.

        Args:
            session_id: معرف الجلسة
            message: نص الرسالة
            role: دور المرسل (user, assistant, system)
            metadata: بيانات إضافية (اختياري)
            intent: النية المستخرجة (اختياري)
            entities: الكيانات المستخرجة (اختياري)

        Returns:
            True إذا تمت الإضافة، False إذا لم يتم
        """
        session = await self._load_session(session_id)

        if not session:
            logger.warning(
                "memory_add_message_failed",
                extra={
                    "session_id": session_id,
                    "role": role,
                },
            )
            return False

        # إنشاء سجل الرسالة
        entry: Message = {
            "role": role,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        }

        if intent:
            entry["intent"] = intent

        if entities:
            entry["entities"] = entities

        # إضافة الرسالة إلى التاريخ
        session["history"].append(entry)

        # الحفاظ على الحد الأقصى للسياق
        if len(session["history"]) > self.max_history:
            session["history"] = session["history"][-self.max_history :]

        # تحديث وقت آخر نشاط
        session["updated_at"] = datetime.now().isoformat()

        # حفظ الجلسة
        await self._save_session(session)

        logger.debug(
            "memory_message_added",
            extra={
                "session_id": session_id,
                "role": role,
                "history_length": len(session["history"]),
            },
        )

        return True

    # ==============================================
    # GET HISTORY
    # ==============================================

    async def get_history(
        self,
        *,
        session_id: str,
        limit: Optional[int] = None,
    ) -> ConversationHistory:
        """
        الحصول على تاريخ المحادثة.

        Args:
            session_id: معرف الجلسة
            limit: الحد الأقصى للرسائل (اختياري)

        Returns:
            قائمة الرسائل
        """
        session = await self._load_session(session_id)

        if not session:
            logger.debug(
                "memory_get_history_failed",
                extra={"session_id": session_id},
            )
            return []

        history = session.get("history", [])

        if limit:
            return history[-limit:]

        return history

    # ==============================================
    # GET LAST MESSAGE
    # ==============================================

    async def get_last_message(
        self,
        *,
        session_id: str,
    ) -> Optional[Message]:
        """
        الحصول على آخر رسالة في المحادثة.

        Args:
            session_id: معرف الجلسة

        Returns:
            آخر رسالة أو None
        """
        history = await self.get_history(session_id=session_id)

        if not history:
            return None

        return history[-1]

    # ==============================================
    # GET LAST USER MESSAGE
    # ==============================================

    async def get_last_user_message(
        self,
        *,
        session_id: str,
    ) -> Optional[Message]:
        """
        الحصول على آخر رسالة من المستخدم.

        Args:
            session_id: معرف الجلسة

        Returns:
            آخر رسالة من المستخدم أو None
        """
        history = await self.get_history(session_id=session_id)

        for message in reversed(history):
            if message.get("role") == "user":
                return message

        return None

    # ==============================================
    # CLEAR HISTORY
    # ==============================================

    async def clear_history(
        self,
        *,
        session_id: str,
    ) -> bool:
        """
        مسح تاريخ المحادثة.

        Args:
            session_id: معرف الجلسة

        Returns:
            True إذا تم المسح، False إذا لم يتم
        """
        session = await self._load_session(session_id)

        if not session:
            return False

        session["history"] = []
        session["updated_at"] = datetime.now().isoformat()

        await self._save_session(session)

        logger.info(
            "memory_history_cleared",
            extra={"session_id": session_id},
        )

        return True

    # ==========================================
    # 🗂️ CONTEXT MANAGEMENT
    # ==========================================

    async def update_context(
        self,
        *,
        session_id: str,
        updates: Dict[str, Any],
    ) -> bool:
        """
        تحديث سياق المحادثة.

        Args:
            session_id: معرف الجلسة
            updates: تحديثات السياق

        Returns:
            True إذا تم التحديث، False إذا لم يتم
        """
        session = await self._load_session(session_id)

        if not session:
            return False

        context = session.get("context", {})

        for key, value in updates.items():
            context[key] = value

        session["context"] = context
        session["updated_at"] = datetime.now().isoformat()

        await self._save_session(session)

        logger.debug(
            "memory_context_updated",
            extra={
                "session_id": session_id,
                "updates": list(updates.keys()),
            },
        )

        return True

    # ==============================================
    # GET CONTEXT
    # ==============================================

    async def get_context(
        self,
        *,
        session_id: str,
    ) -> ContextData:
        """
        الحصول على سياق المحادثة.

        Args:
            session_id: معرف الجلسة

        Returns:
            سياق المحادثة
        """
        session = await self._load_session(session_id)

        if not session:
            return {}

        return session.get("context", {})

    # ==============================================
    # GET CONTEXT VALUE
    # ==============================================

    async def get_context_value(
        self,
        *,
        session_id: str,
        key: str,
        default: Any = None,
    ) -> Any:
        """
        الحصول على قيمة محددة من السياق.

        Args:
            session_id: معرف الجلسة
            key: مفتاح القيمة
            default: القيمة الافتراضية

        Returns:
            قيمة المفتاح أو القيمة الافتراضية
        """
        context = await self.get_context(session_id=session_id)
        return context.get(key, default)

    # ==========================================
    # 🔍 ENTITY MANAGEMENT
    # ==========================================

    async def update_entities(
        self,
        *,
        session_id: str,
        entities: Dict[str, Any],
    ) -> bool:
        """
        تحديث الكيانات المستخرجة.

        Args:
            session_id: معرف الجلسة
            entities: الكيانات الجديدة

        Returns:
            True إذا تم التحديث، False إذا لم يتم
        """
        session = await self._load_session(session_id)

        if not session:
            return False

        # دمج الكيانات الجديدة مع القديمة
        current_entities = session.get("entities", {})
        current_entities.update(entities)

        session["entities"] = current_entities
        session["updated_at"] = datetime.now().isoformat()

        await self._save_session(session)

        logger.debug(
            "memory_entities_updated",
            extra={
                "session_id": session_id,
                "entities": list(entities.keys()),
            },
        )

        return True

    # ==============================================
    # GET ENTITIES
    # ==============================================

    async def get_entities(
        self,
        *,
        session_id: str,
    ) -> Dict[str, Any]:
        """
        الحصول على جميع الكيانات المستخرجة.

        Args:
            session_id: معرف الجلسة

        Returns:
            الكيانات المستخرجة
        """
        session = await self._load_session(session_id)

        if not session:
            return {}

        return session.get("entities", {})

    # ==============================================
    # GET ENTITY
    # ==============================================

    async def get_entity(
        self,
        *,
        session_id: str,
        key: str,
        default: Any = None,
    ) -> Any:
        """
        الحصول على كيان محدد.

        Args:
            session_id: معرف الجلسة
            key: مفتاح الكيان
            default: القيمة الافتراضية

        Returns:
            قيمة الكيان أو القيمة الافتراضية
        """
        entities = await self.get_entities(session_id=session_id)
        return entities.get(key, default)

    # ==========================================
    # 📊 SESSION SUMMARY
    # ==========================================

    async def get_session_summary(
        self,
        *,
        session_id: str,
    ) -> Dict[str, Any]:
        """
        الحصول على ملخص الجلسة.

        Args:
            session_id: معرف الجلسة

        Returns:
            ملخص الجلسة
        """
        session = await self._load_session(session_id)

        if not session:
            return {
                "session_id": session_id,
                "exists": False,
            }

        history = session.get("history", [])
        context = session.get("context", {})
        entities = session.get("entities", {})

        # حساب عدد الرسائل حسب الدور
        message_counts = {
            "user": 0,
            "assistant": 0,
            "system": 0,
        }

        for msg in history:
            role = msg.get("role", "unknown")
            if role in message_counts:
                message_counts[role] += 1

        return {
            "session_id": session_id,
            "exists": True,
            "user_id": session.get("user_id"),
            "created_at": session.get("created_at"),
            "updated_at": session.get("updated_at"),
            "message_count": len(history),
            "message_counts": message_counts,
            "context_keys": list(context.keys()),
            "entity_keys": list(entities.keys()),
            "last_intent": session.get("last_intent"),
            "last_action": session.get("last_action"),
        }

    # ==========================================
    # 🛠️ PRIVATE HELPERS
    # ==========================================

    def _get_session_key(self, session_id: str) -> str:
        """
        الحصول على مفتاح الجلسة في Redis.

        Args:
            session_id: معرف الجلسة

        Returns:
            مفتاح الجلسة
        """
        return f"session:{session_id}"

    # ==============================================
    #  SAVE SESSION
    # ==============================================

    async def _save_session(
        self,
        session: SessionData,
    ) -> None:
        """
        حفظ الجلسة.

        Args:
            session: بيانات الجلسة
        """
        session_id = session.get("session_id")

        if not session_id:
            logger.error("memory_save_session_no_id")
            return

        if self.redis_client:
            key = self._get_session_key(session_id)
            value = json.dumps(session, ensure_ascii=False, default=str)
            await self.redis_client.setex(
                key,
                self.session_timeout,
                value,
            )
        else:
            self._local_memory[session_id] = session

    # ==============================================
    #  LOAD SESSION
    # ==============================================

    async def _load_session(
        self,
        session_id: str,
    ) -> Optional[SessionData]:
        """
        تحميل الجلسة.

        Args:
            session_id: معرف الجلسة

        Returns:
            بيانات الجلسة أو None
        """
        if self.redis_client:
            key = self._get_session_key(session_id)
            value = await self.redis_client.get(key)

            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    logger.error(
                        "memory_load_session_json_error",
                        extra={"session_id": session_id},
                    )
                    return None
            return None
        else:
            return self._local_memory.get(session_id)

    # ==============================================
    #  GENERATE SESSION ID
    # ==============================================

    def _generate_session_id(
        self,
        user_id: int,
    ) -> str:
        """
        توليد معرف جلسة فريد.

        Args:
            user_id: معرف المستخدم

        Returns:
            معرف الجلسة
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        hash_input = f"{user_id}:{timestamp}"
        hash_value = hashlib.md5(hash_input.encode()).hexdigest()[:8]
        return f"session_{user_id}_{timestamp}_{hash_value}"


# ==============================================
# 🌍 GLOBAL INSTANCE
# ==============================================

# إنشاء مدير ذاكرة عالمي
memory_manager = MemoryManager()


# ==============================================
# 🔍 UTILITY FUNCTIONS
# ==============================================

# ==============================================
# GET SESSION
# ==============================================


async def get_session(
    *,
    session_id: str,
    manager: Optional[MemoryManager] = None,
) -> Optional[SessionData]:
    """
    الحصول على جلسة (دالة مساعدة).

    Args:
        session_id: معرف الجلسة
        manager: مدير الذاكرة (اختياري)

    Returns:
        بيانات الجلسة أو None
    """
    logger.debug(
        "get_session_called",
        extra={"session_id": session_id},
    )

    if manager is None:
        manager = memory_manager

    return await manager.get_session(session_id=session_id)


# ==============================================
# ADD MESSAGE
# ==============================================


async def add_message(
    *,
    session_id: str,
    message: str,
    role: str = "user",
    manager: Optional[MemoryManager] = None,
    **kwargs,
) -> bool:
    """
    إضافة رسالة إلى المحادثة (دالة مساعدة).

    Args:
        session_id: معرف الجلسة
        message: نص الرسالة
        role: دور المرسل
        manager: مدير الذاكرة (اختياري)
        **kwargs: معاملات إضافية

    Returns:
        True إذا تمت الإضافة
    """
    logger.debug(
        "add_message_called",
        extra={
            "session_id": session_id,
            "role": role,
            "message_length": len(message) if message else 0,
        },
    )

    if manager is None:
        manager = memory_manager

    return await manager.add_message(
        session_id=session_id,
        message=message,
        role=role,
        **kwargs,
    )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "MemoryManager",
    "memory_manager",
    "get_session",
    "add_message",
    "SessionData",
    "ContextData",
    "ConversationHistory",
]
