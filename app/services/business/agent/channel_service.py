# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📡 CHANNEL SERVICE
# منطق الأعمال للقنوات
# ==============================================

from typing import (
    Any,
    Dict,
    Optional,
)

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
)
from app.core.logger import logger
from app.repositories.agent.channel_repo import ChannelRepository
from app.repositories.agent.agent_repo import AgentRepository
from app.schemas.agent.channel import (
    ChannelCreate,
    ChannelResponse,
    ChannelUpdate,
    ChannelListResponse,
)


# ==============================================
# 🧩 TYPES
# ==============================================

ChannelData = Dict[str, Any]
ChannelStats = Dict[str, Any]


# ==============================================
# 📡 CHANNEL SERVICE
# ==============================================

class ChannelService:
    """
    خدمة القنوات - تدير منطق الأعمال للقنوات.
    
    مسؤول عن:
        - إنشاء وتحديث وحذف القنوات
        - إدارة حالة القناة
        - التحقق من صلاحيات القناة
        - إدارة إعدادات القناة
    
    Attributes:
        session: جلسة قاعدة البيانات غير المتزامنة
        repo: مستودع القنوات
        agent_repo: مستودع الوكيل
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة خدمة القنوات.
        
        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        self.session = session
        self.repo = ChannelRepository(session)
        self.agent_repo = AgentRepository(session)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET CHANNEL BY ID
    # ==============================================

    async def get_by_id(
        self,
        *,
        channel_id: int,
        include_inactive: bool = False,
    ) -> ChannelResponse:
        """
        الحصول على قناة بالمعرف.
        
        Args:
            channel_id: معرف القناة
            include_inactive: تضمين القنوات غير النشطة
            
        Returns:
            ChannelResponse: بيانات القناة
            
        Raises:
            NotFoundError: إذا لم يتم العثور على القناة
        """
        logger.info(
            "channel_service_get_by_id",
            extra={
                "channel_id": channel_id,
                "include_inactive": include_inactive,
            },
        )

        channel = await self.repo.get_by_id(id=channel_id)

        if not channel:
            raise NotFoundError(
                message=f"القناة بـ ID '{channel_id}' غير موجودة",
            )

        if not include_inactive and not channel.is_active:
            raise NotFoundError(
                message=f"القناة بـ ID '{channel_id}' غير نشطة",
            )

        return ChannelResponse.model_validate(channel)

    # ==============================================
    # GET CHANNELS BY AGENT
    # ==============================================

    async def get_by_agent(
        self,
        *,
        agent_id: int,
        only_active: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> ChannelListResponse:
        """
        الحصول على قنوات وكيل معين.
        
        Args:
            agent_id: معرف الوكيل
            only_active: جلب القنوات النشطة فقط
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            ChannelListResponse: قائمة القنوات مع الإحصائيات
        """
        logger.info(
            "channel_service_get_by_agent",
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

        channels = await self.repo.get_by_agent_id(
            agent_id=agent_id,
            only_active=only_active,
            skip=skip,
            limit=limit,
        )

        total = await self.repo.count_by_agent(
            agent_id=agent_id,
            only_active=only_active,
        )

        return ChannelListResponse(
            items=[ChannelResponse.model_validate(channel) for channel in channels],
            total=total,
            skip=skip,
            limit=limit,
        )

    # ==============================================
    # GET CHANNEL BY TYPE
    # ==============================================

    async def get_by_type(
        self,
        *,
        agent_id: int,
        channel_type: str,
        only_active: bool = True,
    ) -> Optional[ChannelResponse]:
        """
        الحصول على قناة حسب النوع.
        
        Args:
            agent_id: معرف الوكيل
            channel_type: نوع القناة
            only_active: جلب القناة النشطة فقط
            
        Returns:
            Optional[ChannelResponse]: بيانات القناة أو None
        """
        logger.info(
            "channel_service_get_by_type",
            extra={
                "agent_id": agent_id,
                "channel_type": channel_type,
                "only_active": only_active,
            },
        )

        channel = await self.repo.get_by_agent_and_type(
            agent_id=agent_id,
            channel_type=channel_type,
            only_active=only_active,
        )

        if not channel:
            return None

        return ChannelResponse.model_validate(channel)

    # ==============================================
    # GET CHANNEL BY CONFIG KEY
    # ==============================================

    async def get_by_config_key(
        self,
        *,
        config_key: str,
        agent_id: Optional[int] = None,
    ) -> Optional[ChannelResponse]:
        """
        الحصول على قناة حسب مفتاح التهيئة.
        
        Args:
            config_key: مفتاح التهيئة
            agent_id: معرف الوكيل (اختياري)
            
        Returns:
            Optional[ChannelResponse]: بيانات القناة أو None
        """
        logger.info(
            "channel_service_get_by_config_key",
            extra={
                "config_key": config_key,
                "agent_id": agent_id,
            },
        )

        channel = await self.repo.get_by_config_key(
            config_key=config_key,
            agent_id=agent_id,
        )

        if not channel:
            return None

        return ChannelResponse.model_validate(channel)

    # ==============================================
    # SEARCH CHANNELS
    # ==============================================

    async def search(
        self,
        *,
        query: str,
        agent_id: Optional[int] = None,
        only_active: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> ChannelListResponse:
        """
        البحث عن القنوات.
        
        Args:
            query: نص البحث
            agent_id: معرف الوكيل (اختياري)
            only_active: جلب القنوات النشطة فقط
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            ChannelListResponse: قائمة القنوات مع الإحصائيات
        """
        logger.info(
            "channel_service_search",
            extra={
                "query": query,
                "agent_id": agent_id,
            },
        )

        channels = await self.repo.search(
            query=query,
            agent_id=agent_id,
            only_active=only_active,
            skip=skip,
            limit=limit,
        )

        total = len(channels)

        return ChannelListResponse(
            items=[ChannelResponse.model_validate(channel) for channel in channels],
            total=total,
            skip=skip,
            limit=limit,
        )

    # ==========================================
    # ✏️ MUTATIONS
    # ==========================================

    # ==============================================
    # CREATE CHANNEL
    # ==============================================

    async def create(
        self,
        *,
        channel_data: ChannelCreate,
    ) -> ChannelResponse:
        """
        إنشاء قناة جديدة.
        
        Args:
            channel_data: بيانات القناة
            
        Returns:
            ChannelResponse: بيانات القناة المنشأة
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الوكيل
            ConflictError: إذا كانت القناة موجودة مسبقاً
        """
        logger.info(
            "channel_service_create",
            extra={
                "agent_id": channel_data.agent_id,
                "type": channel_data.type,
                "name": channel_data.name,
            },
        )

        # التحقق من وجود الوكيل
        agent = await self.agent_repo.get_by_id(id=channel_data.agent_id)

        if not agent:
            raise NotFoundError(
                message=f"الوكيل بـ ID '{channel_data.agent_id}' غير موجود",
            )

        # التحقق من عدم وجود قناة بنفس النوع
        existing = await self.repo.get_by_type(
            agent_id=channel_data.agent_id,
            channel_type=channel_data.type,
        )

        if existing:
            raise ConflictError(
                message=f"قناة من نوع '{channel_data.type}' موجودة بالفعل لهذا الوكيل",
            )

        # إنشاء القناة
        data: ChannelData = {
            "agent_id": channel_data.agent_id,
            "type": channel_data.type,
            "name": channel_data.name,
            "is_active": channel_data.is_active if channel_data.is_active is not None else True,
            "config": channel_data.config or {},
        }

        channel = await self.repo.create(data=data)
        await self.session.commit()

        logger.info(
            "channel_created_successfully",
            extra={
                "channel_id": channel.id,
                "agent_id": channel_data.agent_id,
            },
        )

        return ChannelResponse.model_validate(channel)

    # ==============================================
    # UPDATE CHANNEL
    # ==============================================

    async def update(
        self,
        *,
        channel_id: int,
        update_data: ChannelUpdate,
    ) -> ChannelResponse:
        """
        تحديث قناة.
        
        Args:
            channel_id: معرف القناة
            update_data: بيانات التحديث
            
        Returns:
            ChannelResponse: بيانات القناة المحدثة
            
        Raises:
            NotFoundError: إذا لم يتم العثور على القناة
        """
        logger.info(
            "channel_service_update",
            extra={
                "channel_id": channel_id,
                "fields": list(update_data.model_dump(exclude_unset=True).keys()),
            },
        )

        # التحقق من وجود القناة
        channel = await self.repo.get_by_id(id=channel_id)

        if not channel:
            raise NotFoundError(
                message=f"القناة بـ ID '{channel_id}' غير موجودة",
            )

        # تحضير بيانات التحديث
        updates = update_data.model_dump(exclude_unset=True)

        # إذا كان هناك تحديث للـ config، دمج مع الإعدادات الحالية
        if "config" in updates:
            current_config = channel.config or {}
            current_config.update(updates["config"])
            updates["config"] = current_config

        # تحديث القناة
        updated = await self.repo.update(
            id=channel_id,
            data=updates,
        )
        await self.session.commit()

        if not updated:
            raise NotFoundError(
                message=f"القناة بـ ID '{channel_id}' غير موجودة",
            )

        logger.info(
            "channel_updated_successfully",
            extra={
                "channel_id": channel_id,
                "updated_fields": list(updates.keys()),
            },
        )

        return ChannelResponse.model_validate(updated)

    # ==============================================
    # UPDATE CONFIG
    # ==============================================

    async def update_config(
        self,
        *,
        channel_id: int,
        config: Dict[str, Any],
    ) -> ChannelResponse:
        """
        تحديث إعدادات القناة.
        
        Args:
            channel_id: معرف القناة
            config: إعدادات القناة الجديدة
            
        Returns:
            ChannelResponse: بيانات القناة المحدثة
            
        Raises:
            NotFoundError: إذا لم يتم العثور على القناة
        """
        logger.info(
            "channel_service_update_config",
            extra={"channel_id": channel_id},
        )

        # التحقق من وجود القناة
        channel = await self.repo.get_by_id(id=channel_id)

        if not channel:
            raise NotFoundError(
                message=f"القناة بـ ID '{channel_id}' غير موجودة",
            )

        # دمج الإعدادات
        current_config = channel.config or {}
        current_config.update(config)

        updated = await self.repo.update(
            id=channel_id,
            data={"config": current_config},
        )
        await self.session.commit()

        if not updated:
            raise NotFoundError(
                message=f"القناة بـ ID '{channel_id}' غير موجودة",
            )

        logger.info(
            "channel_config_updated_successfully",
            extra={"channel_id": channel_id},
        )

        return ChannelResponse.model_validate(updated)

    # ==============================================
    # TOGGLE ACTIVE
    # ==============================================

    async def toggle_active(
        self,
        *,
        channel_id: int,
    ) -> ChannelResponse:
        """
        تبديل حالة القناة (نشط/غير نشط).
        
        Args:
            channel_id: معرف القناة
            
        Returns:
            ChannelResponse: بيانات القناة المحدثة
            
        Raises:
            NotFoundError: إذا لم يتم العثور على القناة
        """
        logger.info(
            "channel_service_toggle_active",
            extra={"channel_id": channel_id},
        )

        channel = await self.repo.toggle_active(channel_id=channel_id)
        await self.session.commit()

        if not channel:
            raise NotFoundError(
                message=f"القناة بـ ID '{channel_id}' غير موجودة",
            )

        logger.info(
            "channel_toggle_active_successful",
            extra={
                "channel_id": channel_id,
                "is_active": channel.is_active,
            },
        )

        return ChannelResponse.model_validate(channel)

    # ==============================================
    # DELETE CHANNEL
    # ==============================================

    async def delete(
        self,
        *,
        channel_id: int,
        permanent: bool = False,
    ) -> None:
        """
        حذف قناة.
        
        Args:
            channel_id: معرف القناة
            permanent: حذف نهائي
            
        Raises:
            NotFoundError: إذا لم يتم العثور على القناة
        """
        logger.info(
            "channel_service_delete",
            extra={
                "channel_id": channel_id,
                "permanent": permanent,
            },
        )

        # التحقق من وجود القناة
        channel = await self.repo.get_by_id(id=channel_id)

        if not channel:
            raise NotFoundError(
                message=f"القناة بـ ID '{channel_id}' غير موجودة",
            )

        if permanent:
            await self.repo.delete(id=channel_id)
        else:
            # حذف منطقي (تعيين is_active = False)
            await self.repo.toggle_active(channel_id=channel_id)

        await self.session.commit()

        logger.info(
            "channel_deleted_successfully",
            extra={
                "channel_id": channel_id,
                "permanent": permanent,
            },
        )

    # ==============================================
    # DELETE CHANNELS BY AGENT
    # ==============================================

    async def delete_by_agent(
        self,
        *,
        agent_id: int,
        permanent: bool = False,
    ) -> int:
        """
        حذف جميع قنوات وكيل معين.
        
        Args:
            agent_id: معرف الوكيل
            permanent: حذف نهائي
            
        Returns:
            int: عدد القنوات المحذوفة
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الوكيل
        """
        logger.info(
            "channel_service_delete_by_agent",
            extra={
                "agent_id": agent_id,
                "permanent": permanent,
            },
        )

        # التحقق من وجود الوكيل
        agent = await self.agent_repo.get_by_id(id=agent_id)

        if not agent:
            raise NotFoundError(
                message=f"الوكيل بـ ID '{agent_id}' غير موجود",
            )

        if permanent:
            count = await self.repo.delete_by_agent(agent_id=agent_id)
        else:
            count = await self.repo.bulk_toggle_active_by_agent(
                agent_id=agent_id,
                is_active=False,
            )

        await self.session.commit()

        logger.info(
            "channel_delete_by_agent_successful",
            extra={
                "agent_id": agent_id,
                "deleted_count": count,
                "permanent": permanent,
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
        agent_id: int,
    ) -> ChannelStats:
        """
        الحصول على إحصائيات القنوات لوكيل معين.
        
        Args:
            agent_id: معرف الوكيل
            
        Returns:
            ChannelStats: إحصائيات القنوات
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الوكيل
        """
        logger.info(
            "channel_service_get_statistics",
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

        # الحصول على ملخص أنواع القنوات
        types_summary = await self.repo.get_channel_types_summary(
            agent_id=agent_id,
            only_active=False,
        )

        return {
            "total_channels": total,
            "active_channels": active,
            "inactive_channels": inactive,
            "types_summary": types_summary,
        }