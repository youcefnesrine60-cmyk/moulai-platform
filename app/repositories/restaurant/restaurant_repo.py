# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🏪 RESTAURANT REPOSITORY
# عمليات قاعدة البيانات للمطاعم
# Repository ---> SQLAlchemy
# ==============================================

"""MoulAI operational module for restaurant repo.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from sqlalchemy import (
    func,
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logger import logger
from app.models.restaurant import Restaurant
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

RestaurantList = list[Restaurant]


# ==============================================
# 🏪 RESTAURANT REPOSITORY
# ==============================================


class RestaurantRepository(BaseRepository[Restaurant, dict, dict]):
    """
    مستودع المطاعم - يوفر عمليات خاصة بالمطاعم.

    مسؤول عن:
        - عمليات CRUD الأساسية للمطاعم
        - البحث والتصفية حسب المالك والولاية
        - البحث النصي
        - جلب المطاعم مع العلاقات

    Attributes:
        session: جلسة قاعدة البيانات غير المتزامنة
        model: نموذج Restaurant
    """

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة مستودع المطاعم.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(Restaurant, session)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET BY OWNER ID
    # ==============================================

    async def get_by_owner_id(
        self,
        *,
        owner_id: int,
        skip: int = 0,
        limit: int = 100,
        include_inactive: bool = False,
    ) -> RestaurantList:
        """
        الحصول على مطاعم المالك.

        Args:
            owner_id: معرف المالك
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            include_inactive: تضمين المطاعم غير النشطة

        Returns:
            RestaurantList: قائمة المطاعم
        """
        try:
            query = select(self.model).where(
                self.model.owner_id == owner_id,
            )

            if not include_inactive:
                query = query.where(self.model.is_active == True)

            query = query.offset(skip).limit(limit)

            result = await self.session.execute(query)

            return list(result.scalars().all())

        except Exception as e:
            logger.exception(
                "restaurant_repo_get_by_owner_failed",
                extra={
                    "owner_id": owner_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET BY WILAYA
    # ==============================================

    async def get_by_wilaya(
        self,
        *,
        wilaya: str,
        skip: int = 0,
        limit: int = 100,
    ) -> RestaurantList:
        """
        الحصول على مطاعم حسب الولاية.

        Args:
            wilaya: اسم الولاية
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            RestaurantList: قائمة المطاعم
        """
        try:
            query = (
                select(self.model)
                .where(self.model.wilaya == wilaya)
                .where(self.model.is_active == True)
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(query)

            return list(result.scalars().all())

        except Exception as e:
            logger.exception(
                "restaurant_repo_get_by_wilaya_failed",
                extra={
                    "wilaya": wilaya,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET BY NAME AND OWNER
    # ==============================================

    async def get_by_name_and_owner(
        self,
        *,
        owner_id: int,
        name: str,
    ) -> Restaurant | None:
        """
        الحصول على مطعم بواسطة الاسم والمالك.

        ✅ يستخدم للتحقق من عدم وجود اسم مكرر لنفس المالك

        Args:
            owner_id: معرف المالك
            name: اسم المطعم

        Returns:
            Optional[Restaurant]: كائن Restaurant أو None
        """
        try:
            query = (
                select(self.model)
                .where(self.model.owner_id == owner_id)
                .where(self.model.name == name)
                .limit(1)
            )

            result = await self.session.execute(query)

            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(
                "restaurant_repo_get_by_name_and_owner_failed",
                extra={
                    "owner_id": owner_id,
                    "restaurant_name": name,
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
        skip: int = 0,
        limit: int = 100,
    ) -> RestaurantList:
        """
        البحث عن مطاعم.

        Args:
            query: نص البحث
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            RestaurantList: قائمة المطاعم
        """
        try:
            stmt = (
                select(self.model)
                .where(
                    or_(
                        self.model.name.ilike(f"%{query}%"),
                        self.model.type.ilike(f"%{query}%"),
                        self.model.wilaya.ilike(f"%{query}%"),
                    ),
                )
                .where(self.model.is_active == True)
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(stmt)

            return list(result.scalars().all())

        except Exception as e:
            logger.exception(
                "restaurant_repo_search_failed",
                extra={
                    "query": query,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # COUNT SEARCH
    # ==============================================

    async def count_search(
        self,
        *,
        query: str,
        include_inactive: bool = False,
    ) -> int:
        """احسب العدد الإجمالي لنتائج البحث قبل الترقيم."""
        try:
            stmt = (
                select(func.count())
                .select_from(self.model)
                .where(
                    or_(
                        self.model.name.ilike(f"%{query}%"),
                        self.model.type.ilike(f"%{query}%"),
                        self.model.wilaya.ilike(f"%{query}%"),
                    )
                )
            )

            if not include_inactive:
                stmt = stmt.where(self.model.is_active == True)

            result = await self.session.execute(stmt)
            return result.scalar_one() or 0

        except Exception as e:
            logger.exception(
                "restaurant_repo_search_count_failed",
                extra={
                    "query": query,
                    "include_inactive": include_inactive,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET WITH RELATIONS
    # ==============================================

    async def get_with_relations(
        self,
        *,
        restaurant_id: int,
    ) -> Restaurant | None:
        """
        الحصول على مطعم مع جميع علاقاته.

        Args:
            restaurant_id: معرف المطعم

        Returns:
            Optional[Restaurant]: المطعم مع العلاقات أو None
        """
        try:
            query = (
                select(self.model)
                .where(self.model.id == restaurant_id)
                .options(
                    selectinload(self.model.owner),
                    selectinload(self.model.branches),
                    selectinload(self.model.categories),
                    selectinload(self.model.products),
                    selectinload(self.model.subscriptions),
                    selectinload(self.model.metrics),
                    selectinload(self.model.agents),
                )
            )

            result = await self.session.execute(query)

            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(
                "restaurant_repo_get_with_relations_failed",
                extra={
                    "restaurant_id": restaurant_id,
                    "error": str(e),
                },
            )
            raise

    # ==========================================
    # ✏️ UPDATES
    # ==========================================

    # ==============================================
    # UPDATE STATUS
    # ==============================================

    async def update_status(
        self,
        *,
        restaurant_id: int,
        is_active: bool,
    ) -> Restaurant | None:
        """
        تحديث حالة المطعم.

        Args:
            restaurant_id: معرف المطعم
            is_active: الحالة الجديدة

        Returns:
            Optional[Restaurant]: المطعم المُحدّث أو None
        """
        return await self.update(
            id=restaurant_id,
            data={"is_active": is_active},
        )

    # ==========================================
    # 📊 STATISTICS
    # ==========================================

    # ==============================================
    # COUNT BY OWNER
    # ==============================================

    async def count_by_owner(
        self,
        *,
        owner_id: int,
    ) -> int:
        """
        حساب عدد مطاعم المالك.

        Args:
            owner_id: معرف المالك

        Returns:
            int: عدد المطاعم
        """
        return await self.count(
            filters={"owner_id": owner_id, "is_active": True},
        )

    # ==============================================
    # COUNT BY WILAYA
    # ==============================================

    async def count_by_wilaya(
        self,
        *,
        wilaya: str,
    ) -> int:
        """
        حساب عدد المطاعم في الولاية.

        Args:
            wilaya: اسم الولاية

        Returns:
            int: عدد المطاعم
        """
        return await self.count(
            filters={"wilaya": wilaya, "is_active": True},
        )

    # ==============================================
    # COUNT BRANCHES
    # ==============================================

    async def count_branches(
        self,
        *,
        restaurant_id: int,
    ) -> int:
        """
        حساب عدد فروع المطعم.

        ✅ يستخدم للتحقق قبل الحذف

        Args:
            restaurant_id: معرف المطعم

        Returns:
            int: عدد الفروع
        """
        try:
            from sqlalchemy import func

            from app.models.restaurant_group import RestaurantBranch

            result = await self.session.execute(
                select(func.count())
                .select_from(RestaurantBranch)
                .where(RestaurantBranch.restaurant_id == restaurant_id),
            )

            return result.scalar_one() or 0

        except Exception as e:
            logger.exception(
                "restaurant_repo_count_branches_failed",
                extra={
                    "restaurant_id": restaurant_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # COUNT PRODUCTS
    # ==============================================

    async def count_products(
        self,
        *,
        restaurant_id: int,
    ) -> int:
        """
        حساب عدد منتجات المطعم.

        ✅ يستخدم للتحقق قبل الحذف

        Args:
            restaurant_id: معرف المطعم

        Returns:
            int: عدد المنتجات
        """
        try:
            from sqlalchemy import func

            from app.models.product import Product

            result = await self.session.execute(
                select(func.count())
                .select_from(Product)
                .where(Product.restaurant_id == restaurant_id),
            )

            return result.scalar_one() or 0

        except Exception as e:
            logger.exception(
                "restaurant_repo_count_products_failed",
                extra={
                    "restaurant_id": restaurant_id,
                    "error": str(e),
                },
            )
            raise


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "RestaurantList",
    "RestaurantRepository",
]
