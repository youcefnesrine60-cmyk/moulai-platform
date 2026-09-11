# ==============================================
# MoulAI Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine
# ==============================================

# ==============================================
# 💬 CONVERSATION REPOSITORY
# عمليات قاعدة البيانات للمحادثات
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
from app.models.agent import Conversation
from app.repositories.base import BaseRepository


# ==============================================
# 🧩 TYPES
# ==============================================

ConversationData = Dict[str, Any]
ConversationUpdateData = Dict[str, Any]
ConversationList = List[Conversation]


# ==============================================
# 💬 CONVERSATION REPOSITORY
# ==============================================

class ConversationRepository(BaseRepository[Conversation, ConversationData, ConversationUpdateData]):
    """
    مستودع المحادثات - يوفر عمليات خاصة بجدول المحادثات.
    
    مسؤول عن:
        - عمليات CRUD الأساسية للمحادثات
        - البحث عن المحادثات حسب المستخدم والوكيل
        - إدارة سياق المحادثة
    
    Attributes:
        model: نموذج Conversation
        session: جلسة قاعدة البيانات غير المتزامنة
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة مستودع المحادثات.
        
        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(Conversation, session)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET BY USER ID
    # ==============================================

    async def get_by_user_id(
        self,
        *,
        agent_id: int,
        user_id: str,
        only_active: bool = True,
    ) -> Optional[Conversation]:
        """
        الحصول على محادثة حسب معرف المستخدم.
        
        Args:
            agent_id: معرف الوكيل
            user_id: معرف المستخدم
            only_active: جلب المحادثة النشطة فقط
            
        Returns:
            Optional[Conversation]: كائن Conversation أو None
        """
        try:
            query = select(self.model).where(
                and_(
                    self.model.agent_id == agent_id,
                    self.model.user_id == user_id,
                ),
            )

            if only_active:
                query = query.where(self.model.is_active == True)

            query = query.order_by(
                self.model.id.desc(),
            ).limit(1)

            result = await self.session.execute(query)

            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(
                "conversation_repo_get_by_user_failed",
                extra={
                    "agent_id": agent_id,
                    "user_id": user_id,
                    "only_active": only_active,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET BY AGENT ID
    # ==============================================

    async def get_by_agent_id(
        self,
        *,
        agent_id: int,
        only_active: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> ConversationList:
        """
        الحصول على محادثات وكيل معين.
        
        Args:
            agent_id: معرف الوكيل
            only_active: جلب المحادثات النشطة فقط
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            ConversationList: قائمة المحادثات
        """
        try:
            query = select(self.model).where(
                self.model.agent_id == agent_id,
            )

            if only_active:
                query = query.where(self.model.is_active == True)

            query = query.order_by(
                self.model.updated_at.desc(),
            ).offset(skip).limit(limit)

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "conversation_repo_get_by_agent_failed",
                extra={
                    "agent_id": agent_id,
                    "only_active": only_active,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET WITH MESSAGES
    # ==============================================

    async def get_with_messages(
        self,
        *,
        conversation_id: int,
    ) -> Optional[Conversation]:
        """
        الحصول على محادثة مع رسائلها.
        
        Args:
            conversation_id: معرف المحادثة
            
        Returns:
            Optional[Conversation]: كائن Conversation مع الرسائل أو None
        """
        try:
            query = select(self.model).where(
                self.model.id == conversation_id,
            )

            result = await self.session.execute(query)

            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(
                "conversation_repo_get_with_messages_failed",
                extra={
                    "conversation_id": conversation_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET BY STATUS
    # ==============================================

    async def get_by_status(
        self,
        *,
        agent_id: Optional[int] = None,
        status: str,
        skip: int = 0,
        limit: int = 100,
    ) -> ConversationList:
        """
        الحصول على محادثات حسب الحالة.
        
        Args:
            agent_id: معرف الوكيل (اختياري)
            status: حالة المحادثة
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            ConversationList: قائمة المحادثات
        """
        try:
            conditions = [
                self.model.status == status,
            ]

            if agent_id is not None:
                conditions.append(
                    self.model.agent_id == agent_id,
                )

            query = select(self.model).where(
                *conditions,
            ).order_by(
                self.model.updated_at.desc(),
            ).offset(skip).limit(limit)

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "conversation_repo_get_by_status_failed",
                extra={
                    "agent_id": agent_id,
                    "status": status,
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
        agent_id: Optional[int] = None,
        only_active: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> ConversationList:
        """
        البحث عن المحادثات.
        
        Args:
            query: نص البحث (معرف المستخدم أو السياق)
            agent_id: معرف الوكيل (اختياري)
            only_active: جلب المحادثات النشطة فقط
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            ConversationList: قائمة المحادثات
        """
        try:
            conditions = [
                or_(
                    self.model.user_id.ilike(f"%{query}%"),
                    self.model.context.cast().cast(str).ilike(f"%{query}%"),
                ),
            ]

            if agent_id is not None:
                conditions.append(
                    self.model.agent_id == agent_id,
                )

            if only_active:
                conditions.append(
                    self.model.is_active == True,
                )

            stmt = (
                select(self.model)
                .where(*conditions)
                .order_by(
                    self.model.updated_at.desc(),
                )
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(stmt)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "conversation_repo_search_failed",
                extra={
                    "query": query,
                    "agent_id": agent_id,
                    "only_active": only_active,
                    "error": str(e),
                },
            )
            raise

    # ==========================================
    # 📊 STATISTICS
    # ==========================================

    # ==============================================
    # COUNT BY AGENT
    # ==============================================

    async def count_by_agent(
        self,
        *,
        agent_id: int,
        only_active: bool = True,
    ) -> int:
        """
        حساب عدد محادثات وكيل معين.
        
        Args:
            agent_id: معرف الوكيل
            only_active: حساب المحادثات النشطة فقط
            
        Returns:
            int: عدد المحادثات
        """
        filters = {"agent_id": agent_id}

        if only_active:
            filters["is_active"] = True

        return await self.count(filters=filters)

    # ==============================================
    # COUNT BY STATUS
    # ==============================================

    async def count_by_status(
        self,
        *,
        agent_id: Optional[int] = None,
        status: str,
        only_active: bool = True,
    ) -> int:
        """
        حساب عدد المحادثات حسب الحالة.
        
        Args:
            agent_id: معرف الوكيل (اختياري)
            status: حالة المحادثة
            only_active: حساب المحادثات النشطة فقط
            
        Returns:
            int: عدد المحادثات
        """
        try:
            conditions = [
                self.model.status == status,
            ]

            if agent_id is not None:
                conditions.append(
                    self.model.agent_id == agent_id,
                )

            if only_active:
                conditions.append(
                    self.model.is_active == True,
                )

            stmt = select(func.count()).select_from(self.model).where(
                *conditions,
            )

            result = await self.session.execute(stmt)

            return result.scalar() or 0

        except Exception as e:
            logger.exception(
                "conversation_repo_count_by_status_failed",
                extra={
                    "agent_id": agent_id,
                    "status": status,
                    "only_active": only_active,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET STATUS SUMMARY
    # ==============================================

    async def get_status_summary(
        self,
        *,
        agent_id: Optional[int] = None,
        only_active: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        الحصول على ملخص حالات المحادثات.
        
        Args:
            agent_id: معرف الوكيل (اختياري)
            only_active: حساب المحادثات النشطة فقط
            
        Returns:
            List[Dict[str, Any]]: ملخص حالات المحادثات
        """
        try:
            conditions = []

            if agent_id is not None:
                conditions.append(
                    self.model.agent_id == agent_id,
                )

            if only_active:
                conditions.append(
                    self.model.is_active == True,
                )

            stmt = (
                select(
                    self.model.status,
                    func.count(self.model.id).label("count"),
                )
                .where(*conditions)
                .group_by(self.model.status)
                .order_by(func.count(self.model.id).desc())
            )

            result = await self.session.execute(stmt)

            return [
                {"status": row[0], "count": row[1]}
                for row in result.all()
            ]

        except Exception as e:
            logger.exception(
                "conversation_repo_get_status_summary_failed",
                extra={
                    "agent_id": agent_id,
                    "only_active": only_active,
                    "error": str(e),
                },
            )
            raise

    # ==========================================
    # ✏️ MUTATIONS
    # ==========================================

    # ==============================================
    # UPDATE CONTEXT
    # ==============================================

    async def update_context(
        self,
        *,
        conversation_id: int,
        context: Dict[str, Any],
    ) -> Optional[Conversation]:
        """
        تحديث سياق المحادثة.
        
        Args:
            conversation_id: معرف المحادثة
            context: السياق الجديد
            
        Returns:
            Optional[Conversation]: كائن Conversation المحدث أو None
        """
        try:
            conversation = await self.get_by_id(id=conversation_id)

            if not conversation:
                logger.warning(
                    "conversation_repo_update_context_not_found",
                    extra={"conversation_id": conversation_id},
                )
                return None

            updated = await self.update(
                id=conversation_id,
                data={"context": context},
            )

            logger.info(
                "conversation_context_updated",
                extra={"conversation_id": conversation_id},
            )

            return updated

        except Exception as e:
            logger.exception(
                "conversation_repo_update_context_failed",
                extra={
                    "conversation_id": conversation_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # UPDATE STATUS
    # ==============================================

    async def update_status(
        self,
        *,
        conversation_id: int,
        status: str,
    ) -> Optional[Conversation]:
        """
        تحديث حالة المحادثة.
        
        Args:
            conversation_id: معرف المحادثة
            status: الحالة الجديدة
            
        Returns:
            Optional[Conversation]: كائن Conversation المحدث أو None
        """
        try:
            conversation = await self.get_by_id(id=conversation_id)

            if not conversation:
                logger.warning(
                    "conversation_repo_update_status_not_found",
                    extra={"conversation_id": conversation_id},
                )
                return None

            updated = await self.update(
                id=conversation_id,
                data={"status": status},
            )

            logger.info(
                "conversation_status_updated",
                extra={
                    "conversation_id": conversation_id,
                    "status": status,
                },
            )

            return updated

        except Exception as e:
            logger.exception(
                "conversation_repo_update_status_failed",
                extra={
                    "conversation_id": conversation_id,
                    "status": status,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # TOGGLE ACTIVE
    # ==============================================

    async def toggle_active(
        self,
        *,
        conversation_id: int,
    ) -> Optional[Conversation]:
        """
        تبديل حالة المحادثة (نشط/غير نشط).
        
        Args:
            conversation_id: معرف المحادثة
            
        Returns:
            Optional[Conversation]: كائن Conversation المحدث أو None
        """
        try:
            conversation = await self.get_by_id(id=conversation_id)

            if not conversation:
                logger.warning(
                    "conversation_repo_toggle_active_not_found",
                    extra={"conversation_id": conversation_id},
                )
                return None

            new_status = not conversation.is_active

            updated = await self.update(
                id=conversation_id,
                data={"is_active": new_status},
            )

            logger.info(
                "conversation_toggle_active_successful",
                extra={
                    "conversation_id": conversation_id,
                    "is_active": new_status,
                },
            )

            return updated

        except Exception as e:
            logger.exception(
                "conversation_repo_toggle_active_failed",
                extra={
                    "conversation_id": conversation_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # DELETE BY AGENT
    # ==============================================

    async def delete_by_agent(
        self,
        *,
        agent_id: int,
    ) -> int:
        """
        حذف جميع محادثات وكيل معين.
        
        Args:
            agent_id: معرف الوكيل
            
        Returns:
            int: عدد المحادثات المحذوفة
        """
        try:
            conversations = await self.get_by_agent_id(
                agent_id=agent_id,
                only_active=False,
                skip=0,
                limit=1000,
            )

            count = 0
            for conversation in conversations:
                await self.delete(id=conversation.id)
                count += 1

            logger.info(
                "conversation_delete_by_agent_successful",
                extra={
                    "agent_id": agent_id,
                    "deleted_count": count,
                },
            )

            return count

        except Exception as e:
            logger.exception(
                "conversation_repo_delete_by_agent_failed",
                extra={
                    "agent_id": agent_id,
                    "error": str(e),
                },
            )
            raise