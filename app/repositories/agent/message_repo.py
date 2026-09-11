# ==============================================
# MoulAI Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine
# ==============================================

# ==============================================
# 💬 MESSAGE REPOSITORY
# عمليات قاعدة البيانات للرسائل
# ==============================================

from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from sqlalchemy import (
    and_,
    or_,
    select,
    func,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models.agent import Message
from app.repositories.base import BaseRepository


# ==============================================
# 🧩 TYPES
# ==============================================

MessageData = Dict[str, Any]
MessageUpdateData = Dict[str, Any]
MessageList = List[Message]


# ==============================================
# 💬 MESSAGE REPOSITORY
# ==============================================

class MessageRepository(BaseRepository[Message, MessageData, MessageUpdateData]):
    """
    مستودع الرسائل - يوفر عمليات خاصة بجدول الرسائل.
    
    مسؤول عن:
        - عمليات CRUD الأساسية للرسائل
        - البحث عن الرسائل حسب المحادثة والدور
        - إدارة محتوى الرسائل والملحقات
    
    Attributes:
        model: نموذج Message
        session: جلسة قاعدة البيانات غير المتزامنة
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة مستودع الرسائل.
        
        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(Message, session)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET BY CONVERSATION ID
    # ==============================================

    async def get_by_conversation_id(
        self,
        *,
        conversation_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> MessageList:
        """
        الحصول على رسائل محادثة معينة.
        
        Args:
            conversation_id: معرف المحادثة
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            MessageList: قائمة الرسائل
        """
        try:
            query = select(self.model).where(
                self.model.conversation_id == conversation_id,
            )

            query = query.order_by(
                self.model.created_at.asc(),
            ).offset(skip).limit(limit)

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "message_repo_get_by_conversation_failed",
                extra={
                    "conversation_id": conversation_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET BY ROLE
    # ==============================================

    async def get_by_role(
        self,
        *,
        conversation_id: int,
        role: str,
        skip: int = 0,
        limit: int = 100,
    ) -> MessageList:
        """
        الحصول على رسائل حسب الدور.
        
        Args:
            conversation_id: معرف المحادثة
            role: دور المرسل (user, assistant, system)
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            MessageList: قائمة الرسائل
        """
        try:
            query = select(self.model).where(
                and_(
                    self.model.conversation_id == conversation_id,
                    self.model.role == role,
                ),
            )

            query = query.order_by(
                self.model.created_at.asc(),
            ).offset(skip).limit(limit)

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "message_repo_get_by_role_failed",
                extra={
                    "conversation_id": conversation_id,
                    "role": role,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET BY CONTENT TYPE
    # ==============================================

    async def get_by_content_type(
        self,
        *,
        conversation_id: int,
        content_type: str,
        skip: int = 0,
        limit: int = 100,
    ) -> MessageList:
        """
        الحصول على رسائل حسب نوع المحتوى.
        
        Args:
            conversation_id: معرف المحادثة
            content_type: نوع المحتوى (text, image, audio, video, file)
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            MessageList: قائمة الرسائل
        """
        try:
            query = select(self.model).where(
                and_(
                    self.model.conversation_id == conversation_id,
                    self.model.content_type == content_type,
                ),
            )

            query = query.order_by(
                self.model.created_at.asc(),
            ).offset(skip).limit(limit)

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "message_repo_get_by_content_type_failed",
                extra={
                    "conversation_id": conversation_id,
                    "content_type": content_type,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET LAST MESSAGE
    # ==============================================

    async def get_last_message(
        self,
        *,
        conversation_id: int,
    ) -> Optional[Message]:
        """
        الحصول على آخر رسالة في المحادثة.
        
        Args:
            conversation_id: معرف المحادثة
            
        Returns:
            Optional[Message]: آخر رسالة أو None
        """
        try:
            query = select(self.model).where(
                self.model.conversation_id == conversation_id,
            ).order_by(
                self.model.created_at.desc(),
            ).limit(1)

            result = await self.session.execute(query)

            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(
                "message_repo_get_last_message_failed",
                extra={
                    "conversation_id": conversation_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET FIRST MESSAGE
    # ==============================================

    async def get_first_message(
        self,
        *,
        conversation_id: int,
    ) -> Optional[Message]:
        """
        الحصول على أول رسالة في المحادثة.
        
        Args:
            conversation_id: معرف المحادثة
            
        Returns:
            Optional[Message]: أول رسالة أو None
        """
        try:
            query = select(self.model).where(
                self.model.conversation_id == conversation_id,
            ).order_by(
                self.model.created_at.asc(),
            ).limit(1)

            result = await self.session.execute(query)

            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(
                "message_repo_get_first_message_failed",
                extra={
                    "conversation_id": conversation_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # SEARCH
    # ==============================================

    async def search(
        self,
        *,
        query: str,
        conversation_id: Optional[int] = None,
        role: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> MessageList:
        """
        البحث عن الرسائل.
        
        Args:
            query: نص البحث
            conversation_id: معرف المحادثة (اختياري)
            role: دور المرسل (اختياري)
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            MessageList: قائمة الرسائل
        """
        try:
            conditions = [
                self.model.content.ilike(f"%{query}%"),
            ]

            if conversation_id is not None:
                conditions.append(
                    self.model.conversation_id == conversation_id,
                )

            if role is not None:
                conditions.append(
                    self.model.role == role,
                )

            stmt = (
                select(self.model)
                .where(*conditions)
                .order_by(
                    self.model.created_at.desc(),
                )
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(stmt)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "message_repo_search_failed",
                extra={
                    "query": query,
                    "conversation_id": conversation_id,
                    "role": role,
                    "error": str(e),
                },
            )
            raise

    # ==========================================
    # 📊 STATISTICS
    # ==========================================

    # ==============================================
    # COUNT BY CONVERSATION
    # ==============================================

    async def count_by_conversation(
        self,
        *,
        conversation_id: int,
        role: Optional[str] = None,
    ) -> int:
        """
        حساب عدد رسائل محادثة معينة.
        
        Args:
            conversation_id: معرف المحادثة
            role: دور المرسل (اختياري)
            
        Returns:
            int: عدد الرسائل
        """
        filters = {"conversation_id": conversation_id}

        if role is not None:
            filters["role"] = role

        return await self.count(filters=filters)

    # ==============================================
    # COUNT BY CONTENT TYPE
    # ==============================================

    async def count_by_content_type(
        self,
        *,
        conversation_id: int,
        content_type: str,
    ) -> int:
        """
        حساب عدد رسائل محادثة معينة حسب نوع المحتوى.
        
        Args:
            conversation_id: معرف المحادثة
            content_type: نوع المحتوى
            
        Returns:
            int: عدد الرسائل
        """
        try:
            conditions = [
                self.model.conversation_id == conversation_id,
                self.model.content_type == content_type,
            ]

            stmt = select(func.count()).select_from(self.model).where(
                *conditions,
            )

            result = await self.session.execute(stmt)

            return result.scalar() or 0

        except Exception as e:
            logger.exception(
                "message_repo_count_by_content_type_failed",
                extra={
                    "conversation_id": conversation_id,
                    "content_type": content_type,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET ROLE SUMMARY
    # ==============================================

    async def get_role_summary(
        self,
        *,
        conversation_id: int,
    ) -> List[Dict[str, Any]]:
        """
        الحصول على ملخص أدوار الرسائل في محادثة.
        
        Args:
            conversation_id: معرف المحادثة
            
        Returns:
            List[Dict[str, Any]]: ملخص أدوار الرسائل
        """
        try:
            stmt = (
                select(
                    self.model.role,
                    func.count(self.model.id).label("count"),
                )
                .where(
                    self.model.conversation_id == conversation_id,
                )
                .group_by(self.model.role)
                .order_by(func.count(self.model.id).desc())
            )

            result = await self.session.execute(stmt)

            return [
                {"role": row[0], "count": row[1]}
                for row in result.all()
            ]

        except Exception as e:
            logger.exception(
                "message_repo_get_role_summary_failed",
                extra={
                    "conversation_id": conversation_id,
                    "error": str(e),
                },
            )
            raise

    # ==========================================
    # ✏️ MUTATIONS
    # ==========================================

    # ==============================================
    # BULK CREATE MESSAGES
    # ==============================================

    async def bulk_create_messages(
        self,
        *,
        messages_data: List[Dict[str, Any]],
    ) -> MessageList:
        """
        إنشاء مجموعة من الرسائل دفعة واحدة.
        
        Args:
            messages_data: قائمة بيانات الرسائل
            
        Returns:
            MessageList: قائمة الرسائل المنشأة
        """
        try:
            created_messages = []

            for data in messages_data:
                message = await self.create(data=data)
                created_messages.append(message)

            logger.info(
                "message_bulk_create_successful",
                extra={
                    "conversation_id": messages_data[0].get("conversation_id") if messages_data else None,
                    "count": len(created_messages),
                },
            )

            return created_messages

        except Exception as e:
            logger.exception(
                "message_repo_bulk_create_failed",
                extra={
                    "count": len(messages_data),
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # DELETE BY CONVERSATION
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
        """
        try:
            messages = await self.get_by_conversation_id(
                conversation_id=conversation_id,
                skip=0,
                limit=1000,
            )

            count = 0
            for message in messages:
                await self.delete(id=message.id)
                count += 1

            logger.info(
                "message_delete_by_conversation_successful",
                extra={
                    "conversation_id": conversation_id,
                    "deleted_count": count,
                },
            )

            return count

        except Exception as e:
            logger.exception(
                "message_repo_delete_by_conversation_failed",
                extra={
                    "conversation_id": conversation_id,
                    "error": str(e),
                },
            )
            raise

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
        """
        try:
            # الحصول على جميع رسائل المحادثة مرتبة من الأقدم إلى الأحدث
            all_messages = await self.get_by_conversation_id(
                conversation_id=conversation_id,
                skip=0,
                limit=1000,
            )

            # إذا كان عدد الرسائل أقل من الحد الأدنى، لا نحذف شيئاً
            if len(all_messages) <= keep_count:
                return 0

            # الحصول على الرسائل القديمة التي سيتم حذفها
            old_messages = all_messages[:-keep_count]

            count = 0
            for message in old_messages:
                await self.delete(id=message.id)
                count += 1

            logger.info(
                "message_delete_old_messages_successful",
                extra={
                    "conversation_id": conversation_id,
                    "deleted_count": count,
                    "kept_count": keep_count,
                },
            )

            return count

        except Exception as e:
            logger.exception(
                "message_repo_delete_old_messages_failed",
                extra={
                    "conversation_id": conversation_id,
                    "keep_count": keep_count,
                    "error": str(e),
                },
            )
            raise