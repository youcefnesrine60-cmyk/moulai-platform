# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 💬 CONVERSATION SERVICE
# منطق الأعمال للمحادثات
# ==============================================

"""MoulAI operational module for conversation service.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from typing import (
    Any,
    Dict,
    Optional,
)

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    NotFoundError,
    ValidationError,
)
from app.core.logger import logger
from app.repositories.agent.conversation_repo import ConversationRepository
from app.repositories.agent.agent_repo import AgentRepository
from app.repositories.agent.channel_repo import ChannelRepository
from app.schemas.agent.conversation import (
    ConversationCreate,
    ConversationResponse,
    ConversationUpdate,
    ConversationListResponse,
)

# ==============================================
# 🧩 TYPES
# ==============================================

ConversationData = Dict[str, Any]
ConversationStats = Dict[str, Any]


# ==============================================
# 💬 CONVERSATION SERVICE
# ==============================================


class ConversationService:
    """
    خدمة المحادثات - تدير منطق الأعمال للمحادثات.

    مسؤول عن:
        - إنشاء وتحديث المحادثات
        - إدارة سياق المحادثة
        - البحث عن المحادثات حسب المستخدم
        - إدارة حالة المحادثة

    Attributes:
        session: جلسة قاعدة البيانات غير المتزامنة
        repo: مستودع المحادثات
        agent_repo: مستودع الوكيل
        channel_repo: مستودع القنوات
    """

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة خدمة المحادثات.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        self.session = session
        self.repo = ConversationRepository(session)
        self.agent_repo = AgentRepository(session)
        self.channel_repo = ChannelRepository(session)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET CONVERSATION BY ID
    # ==============================================

    async def get_by_id(
        self,
        *,
        conversation_id: int,
        include_inactive: bool = False,
    ) -> ConversationResponse:
        """
        الحصول على محادثة بالمعرف.

        Args:
            conversation_id: معرف المحادثة
            include_inactive: تضمين المحادثات غير النشطة

        Returns:
            ConversationResponse: بيانات المحادثة

        Raises:
            NotFoundError: إذا لم يتم العثور على المحادثة
        """
        logger.info(
            "conversation_service_get_by_id",
            extra={
                "conversation_id": conversation_id,
                "include_inactive": include_inactive,
            },
        )

        conversation = await self.repo.get_by_id(id=conversation_id)

        if not conversation:
            raise NotFoundError(
                message=f"المحادثة بـ ID '{conversation_id}' غير موجودة",
            )

        if not include_inactive and not conversation.is_active:
            raise NotFoundError(
                message=f"المحادثة بـ ID '{conversation_id}' غير نشطة",
            )

        return ConversationResponse.model_validate(conversation)

    # ==============================================
    # GET CONVERSATION WITH MESSAGES
    # ==============================================

    async def get_with_messages(
        self,
        *,
        conversation_id: int,
        include_inactive: bool = False,
    ) -> ConversationResponse:
        """
        الحصول على محادثة مع رسائلها.

        Args:
            conversation_id: معرف المحادثة
            include_inactive: تضمين المحادثات غير النشطة

        Returns:
            ConversationResponse: بيانات المحادثة مع الرسائل

        Raises:
            NotFoundError: إذا لم يتم العثور على المحادثة
        """
        logger.info(
            "conversation_service_get_with_messages",
            extra={
                "conversation_id": conversation_id,
                "include_inactive": include_inactive,
            },
        )

        conversation = await self.repo.get_with_messages(
            conversation_id=conversation_id,
        )

        if not conversation:
            raise NotFoundError(
                message=f"المحادثة بـ ID '{conversation_id}' غير موجودة",
            )

        if not include_inactive and not conversation.is_active:
            raise NotFoundError(
                message=f"المحادثة بـ ID '{conversation_id}' غير نشطة",
            )

        return ConversationResponse.model_validate(conversation)

    # ==============================================
    # GET CONVERSATION BY USER
    # ==============================================

    async def get_by_user(
        self,
        *,
        agent_id: int,
        user_id: str,
        only_active: bool = True,
    ) -> Optional[ConversationResponse]:
        """
        الحصول على محادثة حسب معرف المستخدم.

        Args:
            agent_id: معرف الوكيل
            user_id: معرف المستخدم
            only_active: جلب المحادثة النشطة فقط

        Returns:
            Optional[ConversationResponse]: بيانات المحادثة أو None
        """
        logger.info(
            "conversation_service_get_by_user",
            extra={
                "agent_id": agent_id,
                "user_id": user_id,
                "only_active": only_active,
            },
        )

        conversation = await self.repo.get_by_user_id(
            agent_id=agent_id,
            user_id=user_id,
            only_active=only_active,
        )

        if not conversation:
            return None

        return ConversationResponse.model_validate(conversation)

    # ==============================================
    # GET CONVERSATIONS BY AGENT
    # ==============================================

    async def get_by_agent(
        self,
        *,
        agent_id: int,
        only_active: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> ConversationListResponse:
        """
        الحصول على محادثات وكيل معين.

        Args:
            agent_id: معرف الوكيل
            only_active: جلب المحادثات النشطة فقط
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            ConversationListResponse: قائمة المحادثات مع الإحصائيات
        """
        logger.info(
            "conversation_service_get_by_agent",
            extra={
                "agent_id": agent_id,
                "only_active": only_active,
            },
        )

        # التحقق من وجود الوكيل
        agent = await self.agent_repo.get_by_id(id=agent_id)

        if not agent:
            raise NotFoundError(
                message=f"الوكيل بـ ID '{agent_id}' غير موجود",
            )

        conversations = await self.repo.get_by_agent_id(
            agent_id=agent_id,
            only_active=only_active,
            skip=skip,
            limit=limit,
        )

        total = await self.repo.count_by_agent(
            agent_id=agent_id,
            only_active=only_active,
        )

        return ConversationListResponse(
            items=[ConversationResponse.model_validate(c) for c in conversations],
            total=total,
            skip=skip,
            limit=limit,
        )

    # ==============================================
    # GET CONVERSATIONS BY STATUS
    # ==============================================

    async def get_by_status(
        self,
        *,
        agent_id: int,
        status: str,
        skip: int = 0,
        limit: int = 100,
    ) -> ConversationListResponse:
        """
        الحصول على محادثات حسب الحالة.

        Args:
            agent_id: معرف الوكيل
            status: حالة المحادثة (active, closed, suspended)
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            ConversationListResponse: قائمة المحادثات مع الإحصائيات
        """
        logger.info(
            "conversation_service_get_by_status",
            extra={
                "agent_id": agent_id,
                "status": status,
            },
        )

        conversations = await self.repo.get_by_status(
            agent_id=agent_id,
            status=status,
            skip=skip,
            limit=limit,
        )

        total = await self.repo.count_by_status(
            agent_id=agent_id,
            status=status,
            only_active=True,
        )

        return ConversationListResponse(
            items=[ConversationResponse.model_validate(c) for c in conversations],
            total=total,
            skip=skip,
            limit=limit,
        )

    # ==============================================
    # SEARCH CONVERSATIONS
    # ==============================================

    async def search(
        self,
        *,
        query: str,
        agent_id: Optional[int] = None,
        only_active: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> ConversationListResponse:
        """
        البحث عن المحادثات.

        Args:
            query: نص البحث
            agent_id: معرف الوكيل (اختياري)
            only_active: جلب المحادثات النشطة فقط
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            ConversationListResponse: قائمة المحادثات مع الإحصائيات
        """
        logger.info(
            "conversation_service_search",
            extra={
                "query": query,
                "agent_id": agent_id,
            },
        )

        conversations = await self.repo.search(
            query=query,
            agent_id=agent_id,
            only_active=only_active,
            skip=skip,
            limit=limit,
        )

        total = len(conversations)

        return ConversationListResponse(
            items=[ConversationResponse.model_validate(c) for c in conversations],
            total=total,
            skip=skip,
            limit=limit,
        )

    # ==========================================
    # ✏️ MUTATIONS
    # ==========================================

    # ==============================================
    # CREATE CONVERSATION
    # ==============================================

    async def create(
        self,
        *,
        conversation_data: ConversationCreate,
    ) -> ConversationResponse:
        """
        إنشاء محادثة جديدة.

        Args:
            conversation_data: بيانات المحادثة

        Returns:
            ConversationResponse: بيانات المحادثة المنشأة

        Raises:
            NotFoundError: إذا لم يتم العثور على الوكيل أو القناة
        """
        logger.info(
            "conversation_service_create",
            extra={
                "agent_id": conversation_data.agent_id,
                "user_id": conversation_data.user_id,
            },
        )

        # التحقق من وجود الوكيل
        agent = await self.agent_repo.get_by_id(
            id=conversation_data.agent_id,
        )

        if not agent:
            raise NotFoundError(
                message=f"الوكيل بـ ID '{conversation_data.agent_id}' غير موجود",
            )

        # التحقق من وجود القناة
        channel = await self.channel_repo.get_by_id(
            id=conversation_data.channel_id,
        )

        if not channel:
            raise NotFoundError(
                message=f"القناة بـ ID '{conversation_data.channel_id}' غير موجودة",
            )

        # التحقق من عدم وجود محادثة نشطة لنفس المستخدم والوكيل
        existing = await self.repo.get_by_user_id(
            agent_id=conversation_data.agent_id,
            user_id=conversation_data.user_id,
            only_active=True,
        )

        if existing:
            # إرجاع المحادثة الموجودة
            logger.info(
                "conversation_already_exists",
                extra={
                    "conversation_id": existing.id,
                    "user_id": conversation_data.user_id,
                },
            )
            return ConversationResponse.model_validate(existing)

        # إنشاء المحادثة
        data: ConversationData = {
            "agent_id": conversation_data.agent_id,
            "channel_id": conversation_data.channel_id,
            "user_id": conversation_data.user_id,
            "user_name": conversation_data.user_name,
            "is_active": True,
            "status": "active",
            "context": conversation_data.context or {},
        }

        conversation = await self.repo.create(data=data)
        await self.session.commit()

        logger.info(
            "conversation_created_successfully",
            extra={
                "conversation_id": conversation.id,
                "agent_id": conversation_data.agent_id,
                "user_id": conversation_data.user_id,
            },
        )

        return ConversationResponse.model_validate(conversation)

    # ==============================================
    # UPDATE CONVERSATION
    # ==============================================

    async def update(
        self,
        *,
        conversation_id: int,
        update_data: ConversationUpdate,
    ) -> ConversationResponse:
        """
        تحديث محادثة.

        Args:
            conversation_id: معرف المحادثة
            update_data: بيانات التحديث

        Returns:
            ConversationResponse: بيانات المحادثة المحدثة

        Raises:
            NotFoundError: إذا لم يتم العثور على المحادثة
        """
        logger.info(
            "conversation_service_update",
            extra={
                "conversation_id": conversation_id,
                "fields": list(update_data.model_dump(exclude_unset=True).keys()),
            },
        )

        # التحقق من وجود المحادثة
        conversation = await self.repo.get_by_id(id=conversation_id)

        if not conversation:
            raise NotFoundError(
                message=f"المحادثة بـ ID '{conversation_id}' غير موجودة",
            )

        # تحضير بيانات التحديث
        updates = update_data.model_dump(exclude_unset=True)

        # تحديث المحادثة
        updated = await self.repo.update(
            id=conversation_id,
            data=updates,
        )
        await self.session.commit()

        if not updated:
            raise NotFoundError(
                message=f"المحادثة بـ ID '{conversation_id}' غير موجودة",
            )

        logger.info(
            "conversation_updated_successfully",
            extra={
                "conversation_id": conversation_id,
                "updated_fields": list(updates.keys()),
            },
        )

        return ConversationResponse.model_validate(updated)

    # ==============================================
    # UPDATE CONTEXT
    # ==============================================

    async def update_context(
        self,
        *,
        conversation_id: int,
        context: Dict[str, Any],
    ) -> ConversationResponse:
        """
        تحديث سياق المحادثة.

        Args:
            conversation_id: معرف المحادثة
            context: السياق الجديد

        Returns:
            ConversationResponse: بيانات المحادثة المحدثة

        Raises:
            NotFoundError: إذا لم يتم العثور على المحادثة
        """
        logger.info(
            "conversation_service_update_context",
            extra={
                "conversation_id": conversation_id,
            },
        )

        # التحقق من وجود المحادثة
        conversation = await self.repo.get_by_id(id=conversation_id)

        if not conversation:
            raise NotFoundError(
                message=f"المحادثة بـ ID '{conversation_id}' غير موجودة",
            )

        # دمج السياق الجديد مع السياق الحالي
        current_context = conversation.context or {}
        current_context.update(context)

        updated = await self.repo.update_context(
            conversation_id=conversation_id,
            context=current_context,
        )
        await self.session.commit()

        if not updated:
            raise NotFoundError(
                message=f"المحادثة بـ ID '{conversation_id}' غير موجودة",
            )

        logger.info(
            "conversation_context_updated_successfully",
            extra={"conversation_id": conversation_id},
        )

        return ConversationResponse.model_validate(updated)

    # ==============================================
    # UPDATE STATUS
    # ==============================================

    async def update_status(
        self,
        *,
        conversation_id: int,
        status: str,
    ) -> ConversationResponse:
        """
        تحديث حالة المحادثة.

        Args:
            conversation_id: معرف المحادثة
            status: الحالة الجديدة (active, closed, suspended)

        Returns:
            ConversationResponse: بيانات المحادثة المحدثة

        Raises:
            NotFoundError: إذا لم يتم العثور على المحادثة
            ValidationError: إذا كانت الحالة غير صالحة
        """
        logger.info(
            "conversation_service_update_status",
            extra={
                "conversation_id": conversation_id,
                "status": status,
            },
        )

        # التحقق من صحة الحالة
        allowed_statuses = {"active", "closed", "suspended"}
        if status not in allowed_statuses:
            raise ValidationError(
                message=f"الحالة يجب أن تكون واحدة من: {', '.join(allowed_statuses)}",
            )

        updated = await self.repo.update_status(
            conversation_id=conversation_id,
            status=status,
        )
        await self.session.commit()

        if not updated:
            raise NotFoundError(
                message=f"المحادثة بـ ID '{conversation_id}' غير موجودة",
            )

        logger.info(
            "conversation_status_updated_successfully",
            extra={
                "conversation_id": conversation_id,
                "status": status,
            },
        )

        return ConversationResponse.model_validate(updated)

    # ==============================================
    # DEACTIVATE CONVERSATION
    # ==============================================

    async def deactivate(
        self,
        *,
        conversation_id: int,
    ) -> ConversationResponse:
        """
        إلغاء تنشيط المحادثة.

        Args:
            conversation_id: معرف المحادثة

        Returns:
            ConversationResponse: بيانات المحادثة المحدثة

        Raises:
            NotFoundError: إذا لم يتم العثور على المحادثة
        """
        logger.info(
            "conversation_service_deactivate",
            extra={"conversation_id": conversation_id},
        )

        updated = await self.repo.toggle_active(
            conversation_id=conversation_id,
        )
        await self.session.commit()

        if not updated:
            raise NotFoundError(
                message=f"المحادثة بـ ID '{conversation_id}' غير موجودة",
            )

        logger.info(
            "conversation_deactivated_successfully",
            extra={
                "conversation_id": conversation_id,
                "is_active": updated.is_active,
            },
        )

        return ConversationResponse.model_validate(updated)

    # ==============================================
    # DELETE CONVERSATION
    # ==============================================

    async def delete(
        self,
        *,
        conversation_id: int,
        permanent: bool = False,
    ) -> None:
        """
        حذف محادثة.

        Args:
            conversation_id: معرف المحادثة
            permanent: حذف نهائي

        Raises:
            NotFoundError: إذا لم يتم العثور على المحادثة
        """
        logger.info(
            "conversation_service_delete",
            extra={
                "conversation_id": conversation_id,
                "permanent": permanent,
            },
        )

        # التحقق من وجود المحادثة
        conversation = await self.repo.get_by_id(id=conversation_id)

        if not conversation:
            raise NotFoundError(
                message=f"المحادثة بـ ID '{conversation_id}' غير موجودة",
            )

        if permanent:
            await self.repo.delete(id=conversation_id)
        else:
            # حذف منطقي (تعيين is_active = False)
            await self.repo.toggle_active(conversation_id=conversation_id)

        await self.session.commit()

        logger.info(
            "conversation_deleted_successfully",
            extra={
                "conversation_id": conversation_id,
                "permanent": permanent,
            },
        )

    # ==========================================
    # 📊 STATISTICS
    # ==========================================

    # ==============================================
    # GET STATISTICS
    # ==============================================

    async def get_statistics(
        self,
        *,
        agent_id: int,
    ) -> ConversationStats:
        """
        الحصول على إحصائيات المحادثات لوكيل معين.

        Args:
            agent_id: معرف الوكيل

        Returns:
            ConversationStats: إحصائيات المحادثات

        Raises:
            NotFoundError: إذا لم يتم العثور على الوكيل
        """
        logger.info(
            "conversation_service_get_statistics",
            extra={"agent_id": agent_id},
        )

        # التحقق من وجود الوكيل
        agent = await self.agent_repo.get_by_id(id=agent_id)

        if not agent:
            raise NotFoundError(
                message=f"الوكيل بـ ID '{agent_id}' غير موجود",
            )

        total = await self.repo.count_by_agent(
            agent_id=agent_id,
            only_active=False,
        )

        active = await self.repo.count_by_agent(
            agent_id=agent_id,
            only_active=True,
        )

        inactive = total - active

        # الحصول على ملخص حالات المحادثات
        status_summary = await self.repo.get_status_summary(
            agent_id=agent_id,
            only_active=False,
        )

        return {
            "total_conversations": total,
            "active_conversations": active,
            "inactive_conversations": inactive,
            "status_summary": status_summary,
        }
