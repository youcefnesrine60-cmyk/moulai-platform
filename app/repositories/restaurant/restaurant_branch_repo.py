# ==============================================
# MoulAI Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine
# ==============================================

# ==============================================
# 🔗 RESTAURANT BRANCH REPOSITORY
# مستودع فروع المطاعم
# يدير عمليات قاعدة البيانات لفروع المطاعم
# ==============================================

from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from sqlalchemy import (
    and_,
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logger import logger
from app.models.restaurant_group import RestaurantBranch
from app.repositories.base import BaseRepository


# ==============================================
# 🧩 TYPES
# ==============================================

BranchData = Dict[str, Any]
BranchUpdateData = Dict[str, Any]


# ==============================================
# 🔗 RESTAURANT BRANCH REPOSITORY
# ==============================================

class RestaurantBranchRepository(BaseRepository[RestaurantBranch, BranchData, BranchUpdateData]):
    """
    مستودع فروع المطاعم.
    
    يدير عمليات قاعدة البيانات لنموذج RestaurantBranch.
    
    Attributes:
        session: جلسة قاعدة البيانات غير المتزامنة
        model: نموذج RestaurantBranch
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة مستودع فروع المطاعم.
        
        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(session, RestaurantBranch)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET BRANCH BY ID WITH DETAILS
    # ==============================================

    async def get_by_id_with_details(
        self,
        *,
        branch_id: int,
    ) -> Optional[RestaurantBranch]:
        """
        الحصول على فرع مطعم بالمعرف مع تفاصيله.
        
        Args:
            branch_id: معرف الفرع
            
        Returns:
            Optional[RestaurantBranch]: الفرع مع تفاصيله أو None
        """
        logger.info(
            "repo_get_branch_by_id_with_details",
            extra={"branch_id": branch_id},
        )

        query = (
            select(RestaurantBranch)
            .where(RestaurantBranch.id == branch_id)
            .options(
                selectinload(RestaurantBranch.group),
                selectinload(RestaurantBranch.restaurant),
            )
        )

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    # ==============================================
    # GET BRANCHES BY GROUP
    # ==============================================

    async def get_by_group(
        self,
        *,
        group_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[RestaurantBranch]:
        """
        الحصول على فروع المطاعم لمجموعة معينة.
        
        Args:
            group_id: معرف المجموعة
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            List[RestaurantBranch]: قائمة فروع المطاعم
        """
        logger.info(
            "repo_get_branches_by_group",
            extra={
                "group_id": group_id,
                "skip": skip,
                "limit": limit,
            },
        )

        query = (
            select(RestaurantBranch)
            .where(RestaurantBranch.group_id == group_id)
            .options(selectinload(RestaurantBranch.restaurant))
            .offset(skip)
            .limit(limit)
            .order_by(RestaurantBranch.created_at.desc())
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    # ==============================================
    # GET BRANCHES BY RESTAURANT
    # ==============================================

    async def get_by_restaurant(
        self,
        *,
        restaurant_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[RestaurantBranch]:
        """
        الحصول على فروع المطاعم لمطعم معين.
        
        Args:
            restaurant_id: معرف المطعم
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            List[RestaurantBranch]: قائمة فروع المطاعم
        """
        logger.info(
            "repo_get_branches_by_restaurant",
            extra={
                "restaurant_id": restaurant_id,
                "skip": skip,
                "limit": limit,
            },
        )

        query = (
            select(RestaurantBranch)
            .where(RestaurantBranch.restaurant_id == restaurant_id)
            .options(selectinload(RestaurantBranch.group))
            .offset(skip)
            .limit(limit)
            .order_by(RestaurantBranch.created_at.desc())
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    # ==============================================
    # GET BRANCH BY GROUP AND RESTAURANT
    # ==============================================

    async def get_by_group_and_restaurant(
        self,
        *,
        group_id: int,
        restaurant_id: int,
    ) -> Optional[RestaurantBranch]:
        """
        الحصول على فرع مطعم بواسطة معرف المجموعة والمطعم.
        
        Args:
            group_id: معرف المجموعة
            restaurant_id: معرف المطعم
            
        Returns:
            Optional[RestaurantBranch]: الفرع أو None
        """
        logger.info(
            "repo_get_branch_by_group_and_restaurant",
            extra={
                "group_id": group_id,
                "restaurant_id": restaurant_id,
            },
        )

        query = select(RestaurantBranch).where(
            and_(
                RestaurantBranch.group_id == group_id,
                RestaurantBranch.restaurant_id == restaurant_id,
            ),
        )

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    # ==============================================
    # COUNT BRANCHES BY GROUP
    # ==============================================

    async def count_by_group(
        self,
        *,
        group_id: int,
    ) -> int:
        """
        حساب عدد فروع المطاعم لمجموعة معينة.
        
        Args:
            group_id: معرف المجموعة
            
        Returns:
            int: عدد الفروع
        """
        query = (
            select(func.count())
            .select_from(RestaurantBranch)
            .where(RestaurantBranch.group_id == group_id)
        )

        result = await self.session.execute(query)
        return result.scalar_one() or 0

    # ==============================================
    # COUNT BRANCHES BY RESTAURANT
    # ==============================================

    async def count_by_restaurant(
        self,
        *,
        restaurant_id: int,
    ) -> int:
        """
        حساب عدد فروع المطاعم لمطعم معين.
        
        Args:
            restaurant_id: معرف المطعم
            
        Returns:
            int: عدد الفروع
        """
        query = (
            select(func.count())
            .select_from(RestaurantBranch)
            .where(RestaurantBranch.restaurant_id == restaurant_id)
        )

        result = await self.session.execute(query)
        return result.scalar_one() or 0

    # ==========================================
    # ✏️ MUTATIONS
    # ==========================================

    # ==============================================
    # BULK CREATE BRANCHES
    # ==============================================

    async def bulk_create_branches(
        self,
        *,
        group_id: int,
        restaurant_ids: List[int],
    ) -> List[RestaurantBranch]:
        """
        إنشاء فروع مطاعم متعددة دفعة واحدة.
        
        Args:
            group_id: معرف المجموعة
            restaurant_ids: قائمة معرفات المطاعم
            
        Returns:
            List[RestaurantBranch]: قائمة الفروع المنشأة
        """
        logger.info(
            "repo_bulk_create_branches",
            extra={
                "group_id": group_id,
                "restaurant_count": len(restaurant_ids),
            },
        )

        branches = []

        for restaurant_id in restaurant_ids:
            existing = await self.get_by_group_and_restaurant(
                group_id=group_id,
                restaurant_id=restaurant_id,
            )

            if existing:
                continue

            branch = RestaurantBranch(
                group_id=group_id,
                restaurant_id=restaurant_id,
            )
            self.session.add(branch)
            branches.append(branch)

        await self.session.flush()

        for branch in branches:
            await self.session.refresh(branch)

        return branches

    # ==============================================
    # DELETE BRANCHES BY GROUP
    # ==============================================

    async def delete_by_group(
        self,
        *,
        group_id: int,
    ) -> int:
        """
        حذف جميع فروع المطاعم لمجموعة معينة.
        
        Args:
            group_id: معرف المجموعة
            
        Returns:
            int: عدد الفروع المحذوفة
        """
        logger.info(
            "repo_delete_branches_by_group",
            extra={"group_id": group_id},
        )

        branches = await self.get_by_group(
            group_id=group_id,
            limit=1000,
        )

        count = len(branches)

        for branch in branches:
            await self.session.delete(branch)

        await self.session.flush()

        return count

    # ==============================================
    # DELETE BRANCHES BY RESTAURANT
    # ==============================================

    async def delete_by_restaurant(
        self,
        *,
        restaurant_id: int,
    ) -> int:
        """
        حذف جميع فروع المطاعم لمطعم معين.
        
        Args:
            restaurant_id: معرف المطعم
            
        Returns:
            int: عدد الفروع المحذوفة
        """
        logger.info(
            "repo_delete_branches_by_restaurant",
            extra={"restaurant_id": restaurant_id},
        )

        branches = await self.get_by_restaurant(
            restaurant_id=restaurant_id,
            limit=1000,
        )

        count = len(branches)

        for branch in branches:
            await self.session.delete(branch)

        await self.session.flush()

        return count

    # ==============================================
    # DELETE BRANCH BY GROUP AND RESTAURANT
    # ==============================================

    async def delete_by_group_and_restaurant(
        self,
        *,
        group_id: int,
        restaurant_id: int,
    ) -> bool:
        """
        حذف فرع مطعم بواسطة معرف المجموعة والمطعم.
        
        Args:
            group_id: معرف المجموعة
            restaurant_id: معرف المطعم
            
        Returns:
            bool: True إذا تم الحذف بنجاح
        """
        logger.info(
            "repo_delete_branch_by_group_and_restaurant",
            extra={
                "group_id": group_id,
                "restaurant_id": restaurant_id,
            },
        )

        branch = await self.get_by_group_and_restaurant(
            group_id=group_id,
            restaurant_id=restaurant_id,
        )

        if not branch:
            return False

        await self.session.delete(branch)
        await self.session.flush()

        return True


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "RestaurantBranchRepository",
]