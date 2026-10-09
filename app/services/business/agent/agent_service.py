# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🤖 AGENT SERVICE
# منطق الأعمال للوكيل الذكي
# ==============================================

"""MoulAI operational module for agent service.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
)
from app.core.logger import logger
from app.repositories.agent.agent_repo import AgentRepository
from app.schemas.agent.agent import (
    AgentCreate,
    AgentResponse,
    AgentUpdate,
    AgentListResponse,
    AgentConfigUpdate,
)

# ==============================================
# 🧩 TYPES
# ==============================================

AgentData = Dict[str, Any]
AgentStats = Dict[str, Any]


# ==============================================
# 🤖 AGENT SERVICE
# ==============================================


class AgentService:
    """
    خدمة الوكيل الذكي - تدير منطق الأعمال للوكيل.

    مسؤول عن:
        - إنشاء وتحديث وحذف الوكلاء
        - إدارة إعدادات الوكيل
        - إدارة حالة الوكيل
        - التحقق من صلاحيات الوكيل

    Attributes:
        session: جلسة قاعدة البيانات غير المتزامنة
        repo: مستودع الوكيل
    """

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة خدمة الوكيل.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        self.session = session
        self.repo = AgentRepository(session)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET AGENT BY ID
    # ==============================================

    async def get_by_id(
        self,
        *,
        agent_id: int,
        include_inactive: bool = False,
    ) -> AgentResponse:
        """
        الحصول على وكيل بالمعرف.

        Args:
            agent_id: معرف الوكيل
            include_inactive: تضمين الوكلاء غير النشطين

        Returns:
            AgentResponse: بيانات الوكيل

        Raises:
            NotFoundError: إذا لم يتم العثور على الوكيل
        """
        logger.info(
            "agent_service_get_by_id",
            extra={
                "agent_id": agent_id,
                "include_inactive": include_inactive,
            },
        )

        agent = await self.repo.get_by_id(id=agent_id)

        if not agent:
            raise NotFoundError(
                message=f"الوكيل بـ ID '{agent_id}' غير موجود",
            )

        if not include_inactive and not agent.is_active:
            raise NotFoundError(
                message=f"الوكيل بـ ID '{agent_id}' غير نشط",
            )

        return AgentResponse.model_validate(agent)

    # ==============================================
    # GET AGENT WITH CHANNELS
    # ==============================================

    async def get_with_channels(
        self,
        *,
        agent_id: int,
        include_inactive: bool = False,
    ) -> AgentResponse:
        """
        الحصول على وكيل مع قنواته.

        Args:
            agent_id: معرف الوكيل
            include_inactive: تضمين الوكلاء غير النشطين

        Returns:
            AgentResponse: بيانات الوكيل مع القنوات

        Raises:
            NotFoundError: إذا لم يتم العثور على الوكيل
        """
        logger.info(
            "agent_service_get_with_channels",
            extra={
                "agent_id": agent_id,
                "include_inactive": include_inactive,
            },
        )

        agent = await self.repo.get_with_channels(agent_id=agent_id)

        if not agent:
            raise NotFoundError(
                message=f"الوكيل بـ ID '{agent_id}' غير موجود",
            )

        if not include_inactive and not agent.is_active:
            raise NotFoundError(
                message=f"الوكيل بـ ID '{agent_id}' غير نشط",
            )

        return AgentResponse.model_validate(agent)

    # ==============================================
    # GET AGENTS BY RESTAURANT
    # ==============================================

    async def get_by_restaurant(
        self,
        *,
        restaurant_id: int,
        only_active: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> AgentListResponse:
        """
        الحصول على وكلاء مطعم معين.

        Args:
            restaurant_id: معرف المطعم
            only_active: جلب الوكلاء النشطين فقط
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            AgentListResponse: قائمة الوكلاء مع الإحصائيات
        """
        logger.info(
            "agent_service_get_by_restaurant",
            extra={
                "restaurant_id": restaurant_id,
                "only_active": only_active,
            },
        )

        agents = await self.repo.get_by_restaurant_id(
            restaurant_id=restaurant_id,
            only_active=only_active,
            skip=skip,
            limit=limit,
        )

        total = await self.repo.count_by_restaurant(
            restaurant_id=restaurant_id,
            only_active=only_active,
        )

        return AgentListResponse(
            items=[AgentResponse.model_validate(agent) for agent in agents],
            total=total,
            skip=skip,
            limit=limit,
        )

    # ==============================================
    # GET AGENT BY NAME
    # ==============================================

    async def get_by_name(
        self,
        *,
        restaurant_id: int,
        name: str,
    ) -> Optional[AgentResponse]:
        """
        الحصول على وكيل بواسطة اسمه.

        Args:
            restaurant_id: معرف المطعم
            name: اسم الوكيل

        Returns:
            Optional[AgentResponse]: بيانات الوكيل أو None
        """
        logger.info(
            "agent_service_get_by_name",
            extra={
                "restaurant_id": restaurant_id,
                "agent_name": name,
            },
        )

        agent = await self.repo.get_by_name(
            restaurant_id=restaurant_id,
            name=name,
        )

        if not agent:
            return None

        return AgentResponse.model_validate(agent)

    # ==============================================
    # GET AGENTS BY STATUS
    # ==============================================

    async def get_by_status(
        self,
        *,
        restaurant_id: Optional[int] = None,
        is_active: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> AgentListResponse:
        """
        الحصول على وكلاء حسب الحالة.

        Args:
            restaurant_id: معرف المطعم (اختياري)
            is_active: حالة الوكيل
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            AgentListResponse: قائمة الوكلاء مع الإحصائيات
        """
        logger.info(
            "agent_service_get_by_status",
            extra={
                "restaurant_id": restaurant_id,
                "is_active": is_active,
            },
        )

        agents = await self.repo.get_by_status(
            restaurant_id=restaurant_id,
            is_active=is_active,
            skip=skip,
            limit=limit,
        )

        total = await self.repo.count_by_status(
            restaurant_id=restaurant_id,
            is_active=is_active,
        )

        return AgentListResponse(
            items=[AgentResponse.model_validate(agent) for agent in agents],
            total=total,
            skip=skip,
            limit=limit,
        )

    # ==============================================
    # SEARCH AGENTS
    # ==============================================

    async def search(
        self,
        *,
        query: str,
        restaurant_id: Optional[int] = None,
        only_active: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> AgentListResponse:
        """
        البحث عن الوكلاء.

        Args:
            query: نص البحث
            restaurant_id: معرف المطعم (اختياري)
            only_active: جلب الوكلاء النشطين فقط
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            AgentListResponse: قائمة الوكلاء مع الإحصائيات
        """
        logger.info(
            "agent_service_search",
            extra={
                "query": query,
                "restaurant_id": restaurant_id,
            },
        )

        agents = await self.repo.search(
            query=query,
            restaurant_id=restaurant_id,
            only_active=only_active,
            skip=skip,
            limit=limit,
        )

        total = len(agents)

        return AgentListResponse(
            items=[AgentResponse.model_validate(agent) for agent in agents],
            total=total,
            skip=skip,
            limit=limit,
        )

    # ==========================================
    # ✏️ MUTATIONS
    # ==========================================

    # ==============================================
    # CREATE AGENT
    # ==============================================

    async def create(
        self,
        *,
        agent_data: AgentCreate,
    ) -> AgentResponse:
        """
        إنشاء وكيل جديد.

        Args:
            agent_data: بيانات الوكيل

        Returns:
            AgentResponse: بيانات الوكيل المنشأ

        Raises:
            ConflictError: إذا كان الاسم موجوداً مسبقاً للمطعم
            ValidationError: إذا كانت البيانات غير صالحة
        """
        logger.info(
            "agent_service_create",
            extra={
                "restaurant_id": agent_data.restaurant_id,
                "agent_name": agent_data.name,
            },
        )

        # التحقق من عدم وجود اسم مكرر
        existing = await self.repo.get_by_name(
            restaurant_id=agent_data.restaurant_id,
            name=agent_data.name,
        )

        if existing:
            raise ConflictError(
                message=f"الوكيل باسم '{agent_data.name}' موجود مسبقاً لهذا المطعم",
            )

        # إنشاء الوكيل
        data: AgentData = {
            "restaurant_id": agent_data.restaurant_id,
            "name": agent_data.name,
            "description": agent_data.description,
            "language": agent_data.language or "ar",
            "tone": agent_data.tone or "professional",
            "is_active": (
                agent_data.is_active if agent_data.is_active is not None else True
            ),
            "config": agent_data.config or {},
            "ai_config": agent_data.ai_config or {},
        }

        agent = await self.repo.create(data=data)
        await self.session.commit()

        logger.info(
            "agent_created_successfully",
            extra={
                "agent_id": agent.id,
                "restaurant_id": agent_data.restaurant_id,
            },
        )

        return AgentResponse.model_validate(agent)

    # ==============================================
    # UPDATE AGENT
    # ==============================================

    async def update(
        self,
        *,
        agent_id: int,
        update_data: AgentUpdate,
    ) -> AgentResponse:
        """
        تحديث وكيل.

        Args:
            agent_id: معرف الوكيل
            update_data: بيانات التحديث

        Returns:
            AgentResponse: بيانات الوكيل المحدث

        Raises:
            NotFoundError: إذا لم يتم العثور على الوكيل
            ConflictError: إذا كان الاسم موجوداً مسبقاً
        """
        logger.info(
            "agent_service_update",
            extra={
                "agent_id": agent_id,
                "fields": list(update_data.model_dump(exclude_unset=True).keys()),
            },
        )

        # التحقق من وجود الوكيل
        agent = await self.repo.get_by_id(id=agent_id)

        if not agent:
            raise NotFoundError(
                message=f"الوكيل بـ ID '{agent_id}' غير موجود",
            )

        # تحضير بيانات التحديث
        updates = update_data.model_dump(exclude_unset=True)

        # التحقق من اسم مكرر
        if "name" in updates:
            existing = await self.repo.get_by_name(
                restaurant_id=agent.restaurant_id,
                name=updates["name"],
            )

            if existing and existing.id != agent_id:
                raise ConflictError(
                    message=f"الوكيل باسم '{updates['name']}' موجود مسبقاً لهذا المطعم",
                )

        # تحديث الوكيل
        updated = await self.repo.update(
            id=agent_id,
            data=updates,
        )
        await self.session.commit()

        if not updated:
            raise NotFoundError(
                message=f"الوكيل بـ ID '{agent_id}' غير موجود",
            )

        logger.info(
            "agent_updated_successfully",
            extra={
                "agent_id": agent_id,
                "updated_fields": list(updates.keys()),
            },
        )

        return AgentResponse.model_validate(updated)

    # ==============================================
    # UPDATE CONFIG
    # ==============================================

    async def update_config(
        self,
        *,
        agent_id: int,
        config_data: AgentConfigUpdate,
    ) -> AgentResponse:
        """
        تحديث إعدادات الوكيل.

        Args:
            agent_id: معرف الوكيل
            config_data: بيانات إعدادات الوكيل

        Returns:
            AgentResponse: بيانات الوكيل المحدث

        Raises:
            NotFoundError: إذا لم يتم العثور على الوكيل
        """
        logger.info(
            "agent_service_update_config",
            extra={"agent_id": agent_id},
        )

        # التحقق من وجود الوكيل
        agent = await self.repo.get_by_id(id=agent_id)

        if not agent:
            raise NotFoundError(
                message=f"الوكيل بـ ID '{agent_id}' غير موجود",
            )

        # تحديث الإعدادات
        updates = config_data.model_dump(exclude_unset=True)

        # تحديث config أو ai_config
        if "config" in updates:
            # دمج مع الإعدادات الحالية
            current_config = agent.config or {}
            current_config.update(updates["config"])
            updates["config"] = current_config

        if "ai_config" in updates:
            current_ai_config = agent.ai_config or {}
            current_ai_config.update(updates["ai_config"])
            updates["ai_config"] = current_ai_config

        updated = await self.repo.update(
            id=agent_id,
            data=updates,
        )
        await self.session.commit()

        if not updated:
            raise NotFoundError(
                message=f"الوكيل بـ ID '{agent_id}' غير موجود",
            )

        logger.info(
            "agent_config_updated_successfully",
            extra={"agent_id": agent_id},
        )

        return AgentResponse.model_validate(updated)

    # ==============================================
    # TOGGLE ACTIVE
    # ==============================================

    async def toggle_active(
        self,
        *,
        agent_id: int,
    ) -> AgentResponse:
        """
        تبديل حالة الوكيل (نشط/غير نشط).

        Args:
            agent_id: معرف الوكيل

        Returns:
            AgentResponse: بيانات الوكيل المحدث

        Raises:
            NotFoundError: إذا لم يتم العثور على الوكيل
        """
        logger.info(
            "agent_service_toggle_active",
            extra={"agent_id": agent_id},
        )

        agent = await self.repo.toggle_active(agent_id=agent_id)
        await self.session.commit()

        if not agent:
            raise NotFoundError(
                message=f"الوكيل بـ ID '{agent_id}' غير موجود",
            )

        logger.info(
            "agent_toggle_active_successful",
            extra={
                "agent_id": agent_id,
                "is_active": agent.is_active,
            },
        )

        return AgentResponse.model_validate(agent)

    # ==============================================
    # DELETE AGENT
    # ==============================================

    async def delete(
        self,
        *,
        agent_id: int,
        permanent: bool = False,
    ) -> None:
        """
        حذف وكيل.

        Args:
            agent_id: معرف الوكيل
            permanent: حذف نهائي

        Raises:
            NotFoundError: إذا لم يتم العثور على الوكيل
        """
        logger.info(
            "agent_service_delete",
            extra={
                "agent_id": agent_id,
                "permanent": permanent,
            },
        )

        # التحقق من وجود الوكيل
        agent = await self.repo.get_by_id(id=agent_id)

        if not agent:
            raise NotFoundError(
                message=f"الوكيل بـ ID '{agent_id}' غير موجود",
            )

        if permanent:
            await self.repo.delete(id=agent_id)
        else:
            # حذف منطقي (تعيين is_active = False)
            await self.repo.toggle_active(agent_id=agent_id)

        await self.session.commit()

        logger.info(
            "agent_deleted_successfully",
            extra={
                "agent_id": agent_id,
                "permanent": permanent,
            },
        )

    # ==============================================
    # BULK TOGGLE ACTIVE
    # ==============================================

    async def bulk_toggle_active(
        self,
        *,
        agent_ids: List[int],
        is_active: bool,
    ) -> int:
        """
        تبديل حالة مجموعة من الوكلاء.

        Args:
            agent_ids: قائمة معرفات الوكلاء
            is_active: الحالة الجديدة

        Returns:
            int: عدد الوكلاء المحدثين

        Raises:
            NotFoundError: إذا لم يتم العثور على بعض الوكلاء
        """
        logger.info(
            "agent_service_bulk_toggle_active",
            extra={
                "agent_ids": agent_ids,
                "is_active": is_active,
            },
        )

        count = await self.repo.bulk_toggle_active(
            agent_ids=agent_ids,
            is_active=is_active,
        )
        await self.session.commit()

        logger.info(
            "agent_bulk_toggle_active_successful",
            extra={
                "updated_count": count,
                "is_active": is_active,
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
        restaurant_id: int,
    ) -> AgentStats:
        """
        الحصول على إحصائيات الوكلاء لمطعم معين.

        Args:
            restaurant_id: معرف المطعم

        Returns:
            AgentStats: إحصائيات الوكلاء
        """
        logger.info(
            "agent_service_get_statistics",
            extra={"restaurant_id": restaurant_id},
        )

        total = await self.repo.count_by_restaurant(
            restaurant_id=restaurant_id,
            only_active=False,
        )

        active = await self.repo.count_by_restaurant(
            restaurant_id=restaurant_id,
            only_active=True,
        )

        inactive = total - active

        # الحصول على الوكلاء للتحليل
        agents = await self.repo.get_by_restaurant_id(
            restaurant_id=restaurant_id,
            only_active=False,
            limit=1000,
        )

        # توزيع اللغات
        language_distribution: Dict[str, int] = {}
        tone_distribution: Dict[str, int] = {}

        for agent in agents:
            language = agent.language or "ar"
            language_distribution[language] = language_distribution.get(language, 0) + 1

            tone = agent.tone or "professional"
            tone_distribution[tone] = tone_distribution.get(tone, 0) + 1

        return {
            "total_agents": total,
            "active_agents": active,
            "inactive_agents": inactive,
            "language_distribution": language_distribution,
            "tone_distribution": tone_distribution,
        }
