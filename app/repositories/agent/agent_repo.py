# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🤖 AGENT REPOSITORY
# عمليات قاعدة البيانات للوكيل الذكي باستخدام SQLAlchemy
# ==============================================

"""MoulAI operational module for agent repo.

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
from app.models.agent import Agent
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

AgentData = Dict[str, Any]
AgentUpdateData = Dict[str, Any]
AgentList = List[Agent]


# ==============================================
# 🤖 AGENT REPOSITORY
# ==============================================


class AgentRepository(BaseRepository[Agent, AgentData, AgentUpdateData]):
    """
    مستودع الوكيل - يوفر عمليات خاصة بجدول الوكيل.

    مسؤول عن:
        - عمليات CRUD الأساسية للوكيل
        - البحث عن الوكلاء حسب المطعم
        - إدارة حالة الوكيل (نشط/غير نشط)

    Attributes:
        model: نموذج Agent
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
        تهيئة مستودع الوكيل.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(Agent, session)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET BY RESTAURANT ID
    # ==============================================

    async def get_by_restaurant_id(
        self,
        *,
        restaurant_id: int,
        only_active: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> AgentList:
        """
        الحصول على وكلاء مطعم معين.

        Args:
            restaurant_id: معرف المطعم
            only_active: جلب الوكلاء النشطين فقط
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            AgentList: قائمة الوكلاء
        """
        try:
            query = select(self.model).where(
                self.model.restaurant_id == restaurant_id,
            )

            if only_active:
                query = query.where(self.model.is_active == True)

            query = (
                query.order_by(
                    self.model.id.desc(),
                )
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "agent_repo_get_by_restaurant_failed",
                extra={
                    "restaurant_id": restaurant_id,
                    "only_active": only_active,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET BY NAME
    # ==============================================

    async def get_by_name(
        self,
        *,
        restaurant_id: int,
        name: str,
    ) -> Optional[Agent]:
        """
        الحصول على وكيل بواسطة اسمه.

        Args:
            restaurant_id: معرف المطعم
            name: اسم الوكيل

        Returns:
            Optional[Agent]: كائن Agent أو None
        """
        try:
            query = (
                select(self.model)
                .where(
                    and_(
                        self.model.restaurant_id == restaurant_id,
                        self.model.name == name,
                    ),
                )
                .limit(1)
            )

            result = await self.session.execute(query)

            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(
                "agent_repo_get_by_name_failed",
                extra={
                    "restaurant_id": restaurant_id,
                    "agent_name": name,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET WITH CHANNELS
    # ==============================================

    async def get_with_channels(
        self,
        *,
        agent_id: int,
    ) -> Optional[Agent]:
        """
        الحصول على وكيل مع قنواته.

        Args:
            agent_id: معرف الوكيل

        Returns:
            Optional[Agent]: كائن Agent مع القنوات أو None
        """
        try:
            query = select(self.model).where(
                self.model.id == agent_id,
            )

            result = await self.session.execute(query)

            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(
                "agent_repo_get_with_channels_failed",
                extra={
                    "agent_id": agent_id,
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
        restaurant_id: Optional[int] = None,
        is_active: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> AgentList:
        """
        الحصول على وكلاء حسب الحالة.

        Args:
            restaurant_id: معرف المطعم (اختياري)
            is_active: حالة الوكيل
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            AgentList: قائمة الوكلاء
        """
        try:
            conditions = [
                self.model.is_active == is_active,
            ]

            if restaurant_id is not None:
                conditions.append(
                    self.model.restaurant_id == restaurant_id,
                )

            query = (
                select(self.model)
                .where(
                    *conditions,
                )
                .order_by(
                    self.model.id.desc(),
                )
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "agent_repo_get_by_status_failed",
                extra={
                    "restaurant_id": restaurant_id,
                    "is_active": is_active,
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
        restaurant_id: Optional[int] = None,
        only_active: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> AgentList:
        """
        البحث عن الوكلاء.

        Args:
            query: نص البحث (الاسم أو الوصف)
            restaurant_id: معرف المطعم (اختياري)
            only_active: جلب الوكلاء النشطين فقط
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            AgentList: قائمة الوكلاء
        """
        try:
            conditions = [
                or_(
                    self.model.name.ilike(f"%{query}%"),
                    self.model.description.ilike(f"%{query}%"),
                ),
            ]

            if restaurant_id is not None:
                conditions.append(
                    self.model.restaurant_id == restaurant_id,
                )

            if only_active:
                conditions.append(
                    self.model.is_active == True,
                )

            stmt = (
                select(self.model)
                .where(*conditions)
                .order_by(
                    self.model.name.asc(),
                    self.model.id.desc(),
                )
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(stmt)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "agent_repo_search_failed",
                extra={
                    "query": query,
                    "restaurant_id": restaurant_id,
                    "only_active": only_active,
                    "error": str(e),
                },
            )
            raise

    # ==========================================
    # 📊 STATISTICS
    # ==========================================

    # ==============================================
    # COUNT BY RESTAURANT
    # ==============================================

    async def count_by_restaurant(
        self,
        *,
        restaurant_id: int,
        only_active: bool = True,
    ) -> int:
        """
        حساب عدد الوكلاء لمطعم معين.

        Args:
            restaurant_id: معرف المطعم
            only_active: حساب الوكلاء النشطين فقط

        Returns:
            int: عدد الوكلاء
        """
        filters = {"restaurant_id": restaurant_id}

        if only_active:
            filters["is_active"] = True

        return await self.count(filters=filters)

    # ==============================================
    # COUNT BY STATUS
    # ==============================================

    async def count_by_status(
        self,
        *,
        restaurant_id: Optional[int] = None,
        is_active: bool = True,
    ) -> int:
        """
        حساب عدد الوكلاء حسب الحالة.

        Args:
            restaurant_id: معرف المطعم (اختياري)
            is_active: حالة الوكيل

        Returns:
            int: عدد الوكلاء
        """
        try:
            conditions = [
                self.model.is_active == is_active,
            ]

            if restaurant_id is not None:
                conditions.append(
                    self.model.restaurant_id == restaurant_id,
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
                "agent_repo_count_by_status_failed",
                extra={
                    "restaurant_id": restaurant_id,
                    "is_active": is_active,
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
        agent_id: int,
    ) -> Optional[Agent]:
        """
        تبديل حالة الوكيل (نشط/غير نشط).

        Args:
            agent_id: معرف الوكيل

        Returns:
            Optional[Agent]: كائن Agent المحدث أو None
        """
        try:
            agent = await self.get_by_id(id=agent_id)

            if not agent:
                logger.warning(
                    "agent_repo_toggle_active_not_found",
                    extra={"agent_id": agent_id},
                )
                return None

            new_status = not agent.is_active

            updated = await self.update(
                id=agent_id,
                data={"is_active": new_status},
            )

            logger.info(
                "agent_toggle_active_successful",
                extra={
                    "agent_id": agent_id,
                    "is_active": new_status,
                },
            )

            return updated

        except Exception as e:
            logger.exception(
                "agent_repo_toggle_active_failed",
                extra={
                    "agent_id": agent_id,
                    "error": str(e),
                },
            )
            raise

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
        """
        try:
            from sqlalchemy import update

            stmt = (
                update(self.model)
                .where(self.model.id.in_(agent_ids))
                .values(is_active=is_active)
                .returning(self.model.id)
            )

            result = await self.session.execute(stmt)
            updated_ids = result.scalars().all()

            logger.info(
                "agent_bulk_toggle_active_successful",
                extra={
                    "updated_count": len(updated_ids),
                    "is_active": is_active,
                },
            )

            return len(updated_ids)

        except Exception as e:
            logger.exception(
                "agent_repo_bulk_toggle_active_failed",
                extra={
                    "agent_ids": agent_ids,
                    "is_active": is_active,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # DELETE BY RESTAURANT
    # ==============================================

    async def delete_by_restaurant(
        self,
        *,
        restaurant_id: int,
    ) -> int:
        """
        حذف جميع وكلاء مطعم معين.

        Args:
            restaurant_id: معرف المطعم

        Returns:
            int: عدد الوكلاء المحذوفين
        """
        try:
            agents = await self.get_by_restaurant_id(
                restaurant_id=restaurant_id,
                only_active=False,
                skip=0,
                limit=1000,
            )

            count = 0
            for agent in agents:
                await self.delete(id=agent.id)
                count += 1

            logger.info(
                "agent_delete_by_restaurant_successful",
                extra={
                    "restaurant_id": restaurant_id,
                    "deleted_count": count,
                },
            )

            return count

        except Exception as e:
            logger.exception(
                "agent_repo_delete_by_restaurant_failed",
                extra={
                    "restaurant_id": restaurant_id,
                    "error": str(e),
                },
            )
            raise
