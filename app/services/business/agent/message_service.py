# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 💬 MESSAGE SERVICE
# منطق الأعمال للرسائل
# ==============================================

from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    NotFoundError,
    ValidationError,
)
from app.core.logger import logger
from app.repositories.agent.message_repo import MessageRepository
from app.repositories.agent.conversation_repo import ConversationRepository
from app.schemas.agent.message import (
    MessageCreate,
    MessageResponse,
    MessageUpdate,
    MessageListResponse,
)


# ==============================================
# 🧩 TYPES
# ==============================================

MessageData = Dict[str, Any]
MessageStats = Dict[str, Any]


# ==============================================
# 💬 MESSAGE SERVICE
# ==============================================

class MessageService:
    """
    خدمة الرسائل - تدير منطق الأعمال للرسائل.
    
    مسؤول عن:
        - إنشاء وتحديث الرسائل
        - البحث عن الرسائل حسب المحادثة والدور
        - تحليل الرسائل (النوايا، الكيانات، الثقة)
        - إدارة الرسائل (حذف، تنظيف)
    
    Attributes:
        session: جلسة قاعدة البيانات غير المتزامنة
        repo: مستودع الرسائل
        conversation_repo: مستودع المحادثات
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة خدمة الرسائل.
        
        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        self.session = session
        self.repo = MessageRepository(session)
        self.conversation_repo = ConversationRepository(session)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET MESSAGE BY ID
    # ==============================================

    async def get_by_id(
        self,
        *,
        message_id: int,
    ) -> MessageResponse:
        """
        الحصول على رسالة بالمعرف.
        
        Args:
            message_id: معرف الرسالة
            
        Returns:
            MessageResponse: بيانات الرسالة
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الرسالة
        """
        logger.info(
            "message_service_get_by_id",
            extra={"message_id": message_id},
        )

        message = await self.repo.get_by_id(id=message_id)

        if not message:
            raise NotFoundError(
                message=f"الرسالة بـ ID '{message_id}' غير موجودة",
            )

        return MessageResponse.model_validate(message)

    # ==============================================
    # GET MESSAGES BY CONVERSATION
    # ==============================================

    async def get_by_conversation(
        self,
        *,
        conversation_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> MessageListResponse:
        """
        الحصول على رسائل محادثة معينة.
        
        Args:
            conversation_id: معرف المحادثة
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            MessageListResponse: قائمة الرسائل مع الإحصائيات
        """
        logger.info(
            "message_service_get_by_conversation",
            extra={
                "conversation_id": conversation_id,
                "skip": skip,
                "limit": limit,
            },
        )

        # التحقق من وجود المحادثة
        conversation = await self.conversation_repo.get_by_id(
            id=conversation_id,
        )

        if not conversation:
            raise NotFoundError(
                message=f"المحادثة بـ ID '{conversation_id}' غير موجودة",
            )

        messages = await self.repo.get_by_conversation_id(
            conversation_id=conversation_id,
            skip=skip,
            limit=limit,
        )

        total = await self.repo.count_by_conversation(
            conversation_id=conversation_id,
        )

        return MessageListResponse(
            items=[MessageResponse.model_validate(msg) for msg in messages],
            total=total,
            skip=skip,
            limit=limit,
        )

    # ==============================================
    # GET MESSAGES BY ROLE
    # ==============================================

    async def get_by_role(
        self,
        *,
        conversation_id: int,
        role: str,
        skip: int = 0,
        limit: int = 100,
    ) -> MessageListResponse:
        """
        الحصول على رسائل حسب الدور.
        
        Args:
            conversation_id: معرف المحادثة
            role: دور المرسل
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            MessageListResponse: قائمة الرسائل مع الإحصائيات
        """
        logger.info(
            "message_service_get_by_role",
            extra={
                "conversation_id": conversation_id,
                "role": role,
            },
        )

        messages = await self.repo.get_by_role(
            conversation_id=conversation_id,
            role=role,
            skip=skip,
            limit=limit,
        )

        total = await self.repo.count_by_conversation(
            conversation_id=conversation_id,
            role=role,
        )

        return MessageListResponse(
            items=[MessageResponse.model_validate(msg) for msg in messages],
            total=total,
            skip=skip,
            limit=limit,
        )

    # ==============================================
    # GET MESSAGES BY CONTENT TYPE
    # ==============================================

    async def get_by_content_type(
        self,
        *,
        conversation_id: int,
        content_type: str,
        skip: int = 0,
        limit: int = 100,
    ) -> MessageListResponse:
        """
        الحصول على رسائل حسب نوع المحتوى.
        
        Args:
            conversation_id: معرف المحادثة
            content_type: نوع المحتوى (text, image, audio, video, file)
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            MessageListResponse: قائمة الرسائل مع الإحصائيات
        """
        logger.info(
            "message_service_get_by_content_type",
            extra={
                "conversation_id": conversation_id,
                "content_type": content_type,
            },
        )

        messages = await self.repo.get_by_content_type(
            conversation_id=conversation_id,
            content_type=content_type,
            skip=skip,
            limit=limit,
        )

        total = await self.repo.count_by_content_type(
            conversation_id=conversation_id,
            content_type=content_type,
        )

        return MessageListResponse(
            items=[MessageResponse.model_validate(msg) for msg in messages],
            total=total,
            skip=skip,
            limit=limit,
        )

    # ==============================================
    # GET LAST MESSAGE
    # ==============================================

    async def get_last_message(
        self,
        *,
        conversation_id: int,
    ) -> Optional[MessageResponse]:
        """
        الحصول على آخر رسالة في المحادثة.
        
        Args:
            conversation_id: معرف المحادثة
            
        Returns:
            Optional[MessageResponse]: آخر رسالة أو None
        """
        logger.info(
            "message_service_get_last_message",
            extra={"conversation_id": conversation_id},
        )

        message = await self.repo.get_last_message(
            conversation_id=conversation_id,
        )

        if not message:
            return None

        return MessageResponse.model_validate(message)

    # ==============================================
    # GET FIRST MESSAGE
    # ==============================================

    async def get_first_message(
        self,
        *,
        conversation_id: int,
    ) -> Optional[MessageResponse]:
        """
        الحصول على أول رسالة في المحادثة.
        
        Args:
            conversation_id: معرف المحادثة
            
        Returns:
            Optional[MessageResponse]: أول رسالة أو None
        """
        logger.info(
            "message_service_get_first_message",
            extra={"conversation_id": conversation_id},
        )

        message = await self.repo.get_first_message(
            conversation_id=conversation_id,
        )

        if not message:
            return None

        return MessageResponse.model_validate(message)

    # ==============================================
    # SEARCH MESSAGES
    # ==============================================

    async def search(
        self,
        *,
        query: str,
        conversation_id: Optional[int] = None,
        role: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> MessageListResponse:
        """
        البحث عن الرسائل.
        
        Args:
            query: نص البحث
            conversation_id: معرف المحادثة (اختياري)
            role: دور المرسل (اختياري)
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            MessageListResponse: قائمة الرسائل مع الإحصائيات
        """
        logger.info(
            "message_service_search",
            extra={
                "query": query,
                "conversation_id": conversation_id,
                "role": role,
            },
        )

        messages = await self.repo.search(
            query=query,
            conversation_id=conversation_id,
            role=role,
            skip=skip,
            limit=limit,
        )

        total = len(messages)

        return MessageListResponse(
            items=[MessageResponse.model_validate(msg) for msg in messages],
            total=total,
            skip=skip,
            limit=limit,
        )

    # ==========================================
    # ✏️ MUTATIONS
    # ==========================================

    # ==============================================
    # CREATE MESSAGE
    # ==============================================

    async def create(
        self,
        *,
        message_data: MessageCreate,
    ) -> MessageResponse:
        """
        إنشاء رسالة جديدة.
        
        Args:
            message_data: بيانات الرسالة
            
        Returns:
            MessageResponse: بيانات الرسالة المنشأة
            
        Raises:
            NotFoundError: إذا لم يتم العثور على المحادثة
        """
        logger.info(
            "message_service_create",
            extra={
                "conversation_id": message_data.conversation_id,
                "role": message_data.role,
            },
        )

        # التحقق من وجود المحادثة
        conversation = await self.conversation_repo.get_by_id(
            id=message_data.conversation_id,
        )

        if not conversation:
            raise NotFoundError(
                message=f"المحادثة بـ ID '{message_data.conversation_id}' غير موجودة",
            )

        # التحقق من أن المحادثة نشطة
        if not conversation.is_active:
            raise ValidationError(
                message="لا يمكن إضافة رسائل إلى محادثة غير نشطة",
            )

        # إنشاء الرسالة
        data: MessageData = {
            "conversation_id": message_data.conversation_id,
            "role": message_data.role,
            "content": message_data.content,
            "content_type": message_data.content_type or "text",
            "intent": message_data.intent,
            "confidence": message_data.confidence,
            "entities": message_data.entities or {},
            "meta_data": message_data.meta_data or {},
        }

        message = await self.repo.create(data=data)
        await self.session.commit()

        # تحديث وقت تحديث المحادثة
        await self.conversation_repo.update(
            id=message_data.conversation_id,
            data={"updated_at": message.created_at},
        )
        await self.session.commit()

        logger.info(
            "message_created_successfully",
            extra={
                "message_id": message.id,
                "conversation_id": message_data.conversation_id,
                "role": message_data.role,
            },
        )

        return MessageResponse.model_validate(message)

    # ==============================================
    # CREATE USER MESSAGE
    # ==============================================

    async def create_user_message(
        self,
        *,
        conversation_id: int,
        content: str,
        content_type: str = "text",
        intent: Optional[str] = None,
        confidence: Optional[float] = None,
        entities: Optional[Dict[str, Any]] = None,
    ) -> MessageResponse:
        """
        إنشاء رسالة مستخدم.
        
        Args:
            conversation_id: معرف المحادثة
            content: محتوى الرسالة
            content_type: نوع المحتوى (اختياري)
            intent: النية (اختياري)
            confidence: الثقة (اختياري)
            entities: الكيانات (اختياري)
            
        Returns:
            MessageResponse: بيانات الرسالة المنشأة
        """
        message_data = MessageCreate(
            conversation_id=conversation_id,
            role="user",
            content=content,
            content_type=content_type,
            intent=intent,
            confidence=confidence,
            entities=entities or {},
        )

        return await self.create(message_data=message_data)

    # ==============================================
    # CREATE ASSISTANT MESSAGE
    # ==============================================

    async def create_assistant_message(
        self,
        *,
        conversation_id: int,
        content: str,
        content_type: str = "text",
        intent: Optional[str] = None,
        confidence: Optional[float] = None,
        entities: Optional[Dict[str, Any]] = None,
    ) -> MessageResponse:
        """
        إنشاء رسالة مساعد.
        
        Args:
            conversation_id: معرف المحادثة
            content: محتوى الرسالة
            content_type: نوع المحتوى (اختياري)
            intent: النية (اختياري)
            confidence: الثقة (اختياري)
            entities: الكيانات (اختياري)
            
        Returns:
            MessageResponse: بيانات الرسالة المنشأة
        """
        message_data = MessageCreate(
            conversation_id=conversation_id,
            role="assistant",
            content=content,
            content_type=content_type,
            intent=intent,
            confidence=confidence,
            entities=entities or {},
        )

        return await self.create(message_data=message_data)

    # ==============================================
    # CREATE SYSTEM MESSAGE
    # ==============================================

    async def create_system_message(
        self,
        *,
        conversation_id: int,
        content: str,
        intent: Optional[str] = None,
        confidence: Optional[float] = None,
        entities: Optional[Dict[str, Any]] = None,
    ) -> MessageResponse:
        """
        إنشاء رسالة نظام.
        
        Args:
            conversation_id: معرف المحادثة
            content: محتوى الرسالة
            intent: النية (اختياري)
            confidence: الثقة (اختياري)
            entities: الكيانات (اختياري)
            
        Returns:
            MessageResponse: بيانات الرسالة المنشأة
        """
        message_data = MessageCreate(
            conversation_id=conversation_id,
            role="system",
            content=content,
            content_type="text",
            intent=intent,
            confidence=confidence,
            entities=entities or {},
        )

        return await self.create(message_data=message_data)

    # ==============================================
    # BULK CREATE MESSAGES
    # ==============================================

    async def bulk_create_messages(
        self,
        *,
        conversation_id: int,
        messages: List[Dict[str, Any]],
    ) -> List[MessageResponse]:
        """
        إنشاء مجموعة من الرسائل دفعة واحدة.
        
        Args:
            conversation_id: معرف المحادثة
            messages: قائمة بيانات الرسائل
            
        Returns:
            List[MessageResponse]: قائمة الرسائل المنشأة
            
        Raises:
            NotFoundError: إذا لم يتم العثور على المحادثة
        """
        logger.info(
            "message_service_bulk_create",
            extra={
                "conversation_id": conversation_id,
                "count": len(messages),
            },
        )

        # التحقق من وجود المحادثة
        conversation = await self.conversation_repo.get_by_id(
            id=conversation_id,
        )

        if not conversation:
            raise NotFoundError(
                message=f"المحادثة بـ ID '{conversation_id}' غير موجودة",
            )

        # إضافة conversation_id إلى كل رسالة
        for msg in messages:
            msg["conversation_id"] = conversation_id
            if "content_type" not in msg:
                msg["content_type"] = "text"
            if "entities" not in msg:
                msg["entities"] = {}
            if "meta_data" not in msg:
                msg["meta_data"] = {}

        created_messages = await self.repo.bulk_create_messages(
            messages_data=messages,
        )
        await self.session.commit()

        # تحديث وقت تحديث المحادثة
        if created_messages:
            await self.conversation_repo.update(
                id=conversation_id,
                data={"updated_at": created_messages[-1].created_at},
            )
            await self.session.commit()

        logger.info(
            "message_bulk_create_successful",
            extra={
                "conversation_id": conversation_id,
                "count": len(created_messages),
            },
        )

        return [MessageResponse.model_validate(msg) for msg in created_messages]

    # ==============================================
    # UPDATE MESSAGE
    # ==============================================

    async def update(
        self,
        *,
        message_id: int,
        update_data: MessageUpdate,
    ) -> MessageResponse:
        """
        تحديث رسالة.
        
        Args:
            message_id: معرف الرسالة
            update_data: بيانات التحديث
            
        Returns:
            MessageResponse: بيانات الرسالة المحدثة
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الرسالة
        """
        logger.info(
            "message_service_update",
            extra={
                "message_id": message_id,
                "fields": list(update_data.model_dump(exclude_unset=True).keys()),
            },
        )

        # التحقق من وجود الرسالة
        message = await self.repo.get_by_id(id=message_id)

        if not message:
            raise NotFoundError(
                message=f"الرسالة بـ ID '{message_id}' غير موجودة",
            )

        # تحضير بيانات التحديث
        updates = update_data.model_dump(exclude_unset=True)

        # تحديث الرسالة
        updated = await self.repo.update(
            id=message_id,
            data=updates,
        )
        await self.session.commit()

        if not updated:
            raise NotFoundError(
                message=f"الرسالة بـ ID '{message_id}' غير موجودة",
            )

        logger.info(
            "message_updated_successfully",
            extra={
                "message_id": message_id,
                "updated_fields": list(updates.keys()),
            },
        )

        return MessageResponse.model_validate(updated)

    # ==============================================
    # DELETE MESSAGE
    # ==============================================

    async def delete(
        self,
        *,
        message_id: int,
    ) -> None:
        """
        حذف رسالة.
        
        Args:
            message_id: معرف الرسالة
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الرسالة
        """
        logger.info(
            "message_service_delete",
            extra={"message_id": message_id},
        )

        # التحقق من وجود الرسالة
        message = await self.repo.get_by_id(id=message_id)

        if not message:
            raise NotFoundError(
                message=f"الرسالة بـ ID '{message_id}' غير موجودة",
            )

        await self.repo.delete(id=message_id)
        await self.session.commit()

        logger.info(
            "message_deleted_successfully",
            extra={"message_id": message_id},
        )

    # ==============================================
    # DELETE MESSAGES BY CONVERSATION
    # ==============================================

    async def delete_by_conversation(
        self,
        *,
        conversation_id: int,
    ) -> int:
        """
        حذف جميع رسائل محادثة معينة.
        
        Args:
            conversation_id: معرف المحادثة
            
        Returns:
            int: عدد الرسائل المحذوفة
            
        Raises:
            NotFoundError: إذا لم يتم العثور على المحادثة
        """
        logger.info(
            "message_service_delete_by_conversation",
            extra={"conversation_id": conversation_id},
        )

        # التحقق من وجود المحادثة
        conversation = await self.conversation_repo.get_by_id(
            id=conversation_id,
        )

        if not conversation:
            raise NotFoundError(
                message=f"المحادثة بـ ID '{conversation_id}' غير موجودة",
            )

        count = await self.repo.delete_by_conversation(
            conversation_id=conversation_id,
        )
        await self.session.commit()

        logger.info(
            "message_delete_by_conversation_successful",
            extra={
                "conversation_id": conversation_id,
                "deleted_count": count,
            },
        )

        return count

    # ==============================================
    # DELETE OLD MESSAGES
    # ==============================================

    async def delete_old_messages(
        self,
        *,
        conversation_id: int,
        keep_count: int = 50,
    ) -> int:
        """
        حذف الرسائل القديمة مع الاحتفاظ بعدد محدد من أحدث الرسائل.
        
        Args:
            conversation_id: معرف المحادثة
            keep_count: عدد الرسائل التي سيتم الاحتفاظ بها
            
        Returns:
            int: عدد الرسائل المحذوفة
            
        Raises:
            NotFoundError: إذا لم يتم العثور على المحادثة
        """
        logger.info(
            "message_service_delete_old_messages",
            extra={
                "conversation_id": conversation_id,
                "keep_count": keep_count,
            },
        )

        # التحقق من وجود المحادثة
        conversation = await self.conversation_repo.get_by_id(
            id=conversation_id,
        )

        if not conversation:
            raise NotFoundError(
                message=f"المحادثة بـ ID '{conversation_id}' غير موجودة",
            )

        count = await self.repo.delete_old_messages(
            conversation_id=conversation_id,
            keep_count=keep_count,
        )
        await self.session.commit()

        logger.info(
            "message_delete_old_messages_successful",
            extra={
                "conversation_id": conversation_id,
                "deleted_count": count,
                "kept_count": keep_count,
            },
        )

        return count

    # ==========================================
    # 📊 STATISTICS
    # ==========================================

    # ==============================================
    # GET STATISTICS
    # ==============================================

    async def get_statistics(
        self,
        *,
        conversation_id: int,
    ) -> MessageStats:
        """
        الحصول على إحصائيات الرسائل لمحادثة معينة.
        
        Args:
            conversation_id: معرف المحادثة
            
        Returns:
            MessageStats: إحصائيات الرسائل
            
        Raises:
            NotFoundError: إذا لم يتم العثور على المحادثة
        """
        logger.info(
            "message_service_get_statistics",
            extra={"conversation_id": conversation_id},
        )

        # التحقق من وجود المحادثة
        conversation = await self.conversation_repo.get_by_id(
            id=conversation_id,
        )

        if not conversation:
            raise NotFoundError(
                message=f"المحادثة بـ ID '{conversation_id}' غير موجودة",
            )

        total = await self.repo.count_by_conversation(
            conversation_id=conversation_id,
        )

        user_count = await self.repo.count_by_conversation(
            conversation_id=conversation_id,
            role="user",
        )

        assistant_count = await self.repo.count_by_conversation(
            conversation_id=conversation_id,
            role="assistant",
        )

        system_count = await self.repo.count_by_conversation(
            conversation_id=conversation_id,
            role="system",
        )

        # الحصول على ملخص أدوار الرسائل
        role_summary = await self.repo.get_role_summary(
            conversation_id=conversation_id,
        )

        return {
            "total_messages": total,
            "user_messages": user_count,
            "assistant_messages": assistant_count,
            "system_messages": system_count,
            "role_summary": role_summary,
        }