# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📡 CHANNEL REPOSITORY
# عمليات قاعدة البيانات للقنوات
# ==============================================

"""MoulAI operational module for channel repo.

Part of MoulAI Platform - Agent-as-a-Service.
"""

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
from app.models.agent import Channel
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

ChannelData = Dict[str, Any]
ChannelUpdateData = Dict[str, Any]
ChannelList = List[Channel]


# ==============================================
# 📡 CHANNEL REPOSITORY
# ==============================================


class ChannelRepository(BaseRepository[Channel, ChannelData, ChannelUpdateData]):
    """
    مستودع القنوات - يوفر عمليات خاصة بجدول القنوات.

    مسؤول عن:
        - عمليات CRUD الأساسية للقنوات
        - البحث عن القنوات حسب الوكيل والنوع
        - إدارة حالة القناة (نشط/غير نشط)

    Attributes:
        model: نموذج Channel
        session: جلسة قاعدة البيانات غير المتزامنة
    """

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة مستودع القنوات.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(Channel, session)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

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
    ) -> ChannelList:
        """
        الحصول على قنوات وكيل معين.

        Args:
            agent_id: معرف الوكيل
            only_active: جلب القنوات النشطة فقط
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            ChannelList: قائمة القنوات
        """
        try:
            query = select(self.model).where(
                self.model.agent_id == agent_id,
            )

            if only_active:
                query = query.where(self.model.is_active == True)

            query = (
                query.order_by(
                    self.model.type.asc(),
                    self.model.id.desc(),
                )
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "channel_repo_get_by_agent_failed",
                extra={
                    "agent_id": agent_id,
                    "only_active": only_active,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET BY TYPE
    # ==============================================

    async def get_by_type(
        self,
        *,
        agent_id: int,
        channel_type: str,
    ) -> Optional[Channel]:
        """
        الحصول على قناة حسب النوع.

        Args:
            agent_id: معرف الوكيل
            channel_type: نوع القناة

        Returns:
            Optional[Channel]: كائن Channel أو None
        """
        try:
            query = (
                select(self.model)
                .where(
                    and_(
                        self.model.agent_id == agent_id,
                        self.model.type == channel_type,
                    ),
                )
                .limit(1)
            )

            result = await self.session.execute(query)

            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(
                "channel_repo_get_by_type_failed",
                extra={
                    "agent_id": agent_id,
                    "channel_type": channel_type,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET BY AGENT AND TYPE
    # ==============================================

    async def get_by_agent_and_type(
        self,
        *,
        agent_id: int,
        channel_type: str,
        only_active: bool = True,
    ) -> Optional[Channel]:
        """
        الحصول على قناة حسب الوكيل والنوع.

        Args:
            agent_id: معرف الوكيل
            channel_type: نوع القناة
            only_active: جلب القناة النشطة فقط

        Returns:
            Optional[Channel]: كائن Channel أو None
        """
        try:
            conditions = [
                self.model.agent_id == agent_id,
                self.model.type == channel_type,
            ]

            if only_active:
                conditions.append(
                    self.model.is_active == True,
                )

            query = (
                select(self.model)
                .where(
                    *conditions,
                )
                .limit(1)
            )

            result = await self.session.execute(query)

            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(
                "channel_repo_get_by_agent_and_type_failed",
                extra={
                    "agent_id": agent_id,
                    "channel_type": channel_type,
                    "only_active": only_active,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET BY CONFIG KEY
    # ==============================================

    async def get_by_config_key(
        self,
        *,
        config_key: str,
        agent_id: Optional[int] = None,
    ) -> Optional[Channel]:
        """
        الحصول على قناة حسب مفتاح التهيئة.

        Args:
            config_key: مفتاح التهيئة
            agent_id: معرف الوكيل (اختياري)

        Returns:
            Optional[Channel]: كائن Channel أو None
        """
        try:
            conditions = [
                self.model.config.has_key(config_key),
            ]

            if agent_id is not None:
                conditions.append(
                    self.model.agent_id == agent_id,
                )

            query = (
                select(self.model)
                .where(
                    *conditions,
                )
                .limit(1)
            )

            result = await self.session.execute(query)

            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(
                "channel_repo_get_by_config_key_failed",
                extra={
                    "config_key": config_key,
                    "agent_id": agent_id,
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
    ) -> ChannelList:
        """
        البحث عن القنوات.

        Args:
            query: نص البحث (النوع أو الوصف)
            agent_id: معرف الوكيل (اختياري)
            only_active: جلب القنوات النشطة فقط
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            ChannelList: قائمة القنوات
        """
        try:
            conditions = [
                or_(
                    self.model.type.ilike(f"%{query}%"),
                    self.model.description.ilike(f"%{query}%"),
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
                    self.model.type.asc(),
                    self.model.id.desc(),
                )
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(stmt)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "channel_repo_search_failed",
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
        حساب عدد قنوات وكيل معين.

        Args:
            agent_id: معرف الوكيل
            only_active: حساب القنوات النشطة فقط

        Returns:
            int: عدد القنوات
        """
        filters = {"agent_id": agent_id}

        if only_active:
            filters["is_active"] = True

        return await self.count(filters=filters)

    # ==============================================
    # COUNT BY TYPE
    # ==============================================

    async def count_by_type(
        self,
        *,
        agent_id: int,
        channel_type: str,
        only_active: bool = True,
    ) -> int:
        """
        حساب عدد قنوات وكيل معين حسب النوع.

        Args:
            agent_id: معرف الوكيل
            channel_type: نوع القناة
            only_active: حساب القنوات النشطة فقط

        Returns:
            int: عدد القنوات
        """
        try:
            conditions = [
                self.model.agent_id == agent_id,
                self.model.type == channel_type,
            ]

            if only_active:
                conditions.append(
                    self.model.is_active == True,
                )

            stmt = (
                select(func.count())
                .select_from(self.model)
                .where(
                    *conditions,
                )
            )

            result = await self.session.execute(stmt)

            return result.scalar() or 0

        except Exception as e:
            logger.exception(
                "channel_repo_count_by_type_failed",
                extra={
                    "agent_id": agent_id,
                    "channel_type": channel_type,
                    "only_active": only_active,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET CHANNEL TYPES SUMMARY
    # ==============================================

    async def get_channel_types_summary(
        self,
        *,
        agent_id: int,
        only_active: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        الحصول على ملخص أنواع القنوات لوكيل معين.

        Args:
            agent_id: معرف الوكيل
            only_active: حساب القنوات النشطة فقط

        Returns:
            List[Dict[str, Any]]: ملخص أنواع القنوات
        """
        try:
            conditions = [
                self.model.agent_id == agent_id,
            ]

            if only_active:
                conditions.append(
                    self.model.is_active == True,
                )

            stmt = (
                select(
                    self.model.type,
                    func.count(self.model.id).label("count"),
                )
                .where(*conditions)
                .group_by(self.model.type)
                .order_by(func.count(self.model.id).desc())
            )

            result = await self.session.execute(stmt)

            return [{"type": row[0], "count": row[1]} for row in result.all()]

        except Exception as e:
            logger.exception(
                "channel_repo_get_types_summary_failed",
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
    # TOGGLE ACTIVE
    # ==============================================

    async def toggle_active(
        self,
        *,
        channel_id: int,
    ) -> Optional[Channel]:
        """
        تبديل حالة القناة (نشط/غير نشط).

        Args:
            channel_id: معرف القناة

        Returns:
            Optional[Channel]: كائن Channel المحدث أو None
        """
        try:
            channel = await self.get_by_id(id=channel_id)

            if not channel:
                logger.warning(
                    "channel_repo_toggle_active_not_found",
                    extra={"channel_id": channel_id},
                )
                return None

            new_status = not channel.is_active

            updated = await self.update(
                id=channel_id,
                data={"is_active": new_status},
            )

            logger.info(
                "channel_toggle_active_successful",
                extra={
                    "channel_id": channel_id,
                    "is_active": new_status,
                },
            )

            return updated

        except Exception as e:
            logger.exception(
                "channel_repo_toggle_active_failed",
                extra={
                    "channel_id": channel_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # BULK TOGGLE ACTIVE BY AGENT
    # ==============================================

    async def bulk_toggle_active_by_agent(
        self,
        *,
        agent_id: int,
        is_active: bool,
    ) -> int:
        """
        تبديل حالة جميع قنوات وكيل معين.

        Args:
            agent_id: معرف الوكيل
            is_active: الحالة الجديدة

        Returns:
            int: عدد القنوات المحدثة
        """
        try:
            from sqlalchemy import update

            stmt = (
                update(self.model)
                .where(self.model.agent_id == agent_id)
                .values(is_active=is_active)
                .returning(self.model.id)
            )

            result = await self.session.execute(stmt)
            updated_ids = result.scalars().all()

            logger.info(
                "channel_bulk_toggle_by_agent_successful",
                extra={
                    "agent_id": agent_id,
                    "updated_count": len(updated_ids),
                    "is_active": is_active,
                },
            )

            return len(updated_ids)

        except Exception as e:
            logger.exception(
                "channel_repo_bulk_toggle_by_agent_failed",
                extra={
                    "agent_id": agent_id,
                    "is_active": is_active,
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
        حذف جميع قنوات وكيل معين.

        Args:
            agent_id: معرف الوكيل

        Returns:
            int: عدد القنوات المحذوفة
        """
        try:
            channels = await self.get_by_agent_id(
                agent_id=agent_id,
                only_active=False,
                skip=0,
                limit=1000,
            )

            count = 0
            for channel in channels:
                await self.delete(id=channel.id)
                count += 1

            logger.info(
                "channel_delete_by_agent_successful",
                extra={
                    "agent_id": agent_id,
                    "deleted_count": count,
                },
            )

            return count

        except Exception as e:
            logger.exception(
                "channel_repo_delete_by_agent_failed",
                extra={
                    "agent_id": agent_id,
                    "error": str(e),
                },
            )
            raise
