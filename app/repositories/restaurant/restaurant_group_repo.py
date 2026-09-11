# ==============================================
# MoulAI Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine
# ==============================================

# ==============================================
# 🏢 RESTAURANT GROUP REPOSITORY
# مستودع مجموعات المطاعم
# يدير عمليات قاعدة البيانات لمجموعات المطاعم
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
from app.models.restaurant_group import (
    RestaurantGroup,
    RestaurantBranch,
)
from app.repositories.base import BaseRepository


# ==============================================
# 🧩 TYPES
# ==============================================

GroupData = Dict[str, Any]
GroupUpdateData = Dict[str, Any]


# ==============================================
# 🏢 RESTAURANT GROUP REPOSITORY
# ==============================================

class RestaurantGroupRepository(BaseRepository[RestaurantGroup, GroupData, GroupUpdateData]):
    """
    مستودع مجموعات المطاعم.
    
    يدير عمليات قاعدة البيانات لنموذج RestaurantGroup.
    
    Attributes:
        session: جلسة قاعدة البيانات غير المتزامنة
        model: نموذج RestaurantGroup
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة مستودع مجموعات المطاعم.
        
        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(session, RestaurantGroup)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET GROUP BY ID WITH DETAILS
    # ==============================================

    async def get_by_id_with_details(
        self,
        *,
        group_id: int,
    ) -> Optional[RestaurantGroup]:
        """
        الحصول على مجموعة مطاعم بالمعرف مع تفاصيلها.
        
        Args:
            group_id: معرف المجموعة
            
        Returns:
            Optional[RestaurantGroup]: المجموعة مع تفاصيلها أو None
        """
        logger.info(
            "repo_get_group_by_id_with_details",
            extra={"group_id": group_id},
        )

        query = (
            select(RestaurantGroup)
            .where(RestaurantGroup.id == group_id)
            .options(
                selectinload(RestaurantGroup.owner),
                selectinload(RestaurantGroup.restaurants),
                selectinload(RestaurantGroup.branch_links).selectinload(RestaurantBranch.restaurant),
            )
        )

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    # ==============================================
    # GET GROUPS BY OWNER
    # ==============================================

    async def get_by_owner(
        self,
        *,
        owner_id: int,
        skip: int = 0,
        limit: int = 100,
        include_inactive: bool = False,
    ) -> List[RestaurantGroup]:
        """
        الحصول على مجموعات المطاعم لمالك معين.
        
        Args:
            owner_id: معرف المالك
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            include_inactive: تضمين المجموعات غير النشطة
            
        Returns:
            List[RestaurantGroup]: قائمة مجموعات المطاعم
        """
        logger.info(
            "repo_get_groups_by_owner",
            extra={
                "owner_id": owner_id,
                "skip": skip,
                "limit": limit,
                "include_inactive": include_inactive,
            },
        )

        query = select(RestaurantGroup).where(
            RestaurantGroup.owner_id == owner_id,
        )

        if not include_inactive:
            query = query.where(RestaurantGroup.is_active == True)

        query = query.offset(skip).limit(limit).order_by(RestaurantGroup.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    # ==============================================
    # COUNT GROUPS BY OWNER
    # ==============================================

    async def count_by_owner(
        self,
        *,
        owner_id: int,
        include_inactive: bool = False,
    ) -> int:
        """
        حساب عدد مجموعات المطاعم لمالك معين.
        
        Args:
            owner_id: معرف المالك
            include_inactive: تضمين المجموعات غير النشطة
            
        Returns:
            int: عدد المجموعات
        """
        query = select(func.count()).select_from(RestaurantGroup).where(
            RestaurantGroup.owner_id == owner_id,
        )

        if not include_inactive:
            query = query.where(RestaurantGroup.is_active == True)

        result = await self.session.execute(query)
        return result.scalar_one() or 0

    # ==============================================
    # GET GROUP BY NAME
    # ==============================================

    async def get_by_name(
        self,
        *,
        owner_id: int,
        name: str,
        include_inactive: bool = False,
    ) -> Optional[RestaurantGroup]:
        """
        الحصول على مجموعة مطاعم بواسطة اسمها.
        
        Args:
            owner_id: معرف المالك
            name: اسم المجموعة
            include_inactive: تضمين المجموعات غير النشطة
            
        Returns:
            Optional[RestaurantGroup]: المجموعة أو None
        """
        logger.info(
            "repo_get_group_by_name",
            extra={
                "owner_id": owner_id,
                "name": name,
            },
        )

        query = select(RestaurantGroup).where(
            and_(
                RestaurantGroup.owner_id == owner_id,
                RestaurantGroup.name == name,
            ),
        )

        if not include_inactive:
            query = query.where(RestaurantGroup.is_active == True)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    # ==============================================
    # SEARCH GROUPS
    # ==============================================

    async def search(
        self,
        *,
        query: str,
        owner_id: Optional[int] = None,
        only_active: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> List[RestaurantGroup]:
        """
        البحث عن مجموعات المطاعم.
        
        Args:
            query: نص البحث
            owner_id: معرف المالك (اختياري)
            only_active: جلب المجموعات النشطة فقط
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            List[RestaurantGroup]: قائمة المجموعات المطابقة
        """
        logger.info(
            "repo_search_groups",
            extra={
                "query": query,
                "owner_id": owner_id,
                "only_active": only_active,
            },
        )

        conditions = [RestaurantGroup.name.ilike(f"%{query}%")]

        if owner_id is not None:
            conditions.append(RestaurantGroup.owner_id == owner_id)

        if only_active:
            conditions.append(RestaurantGroup.is_active == True)

        query_stmt = (
            select(RestaurantGroup)
            .where(and_(*conditions))
            .offset(skip)
            .limit(limit)
            .order_by(RestaurantGroup.name.asc())
        )

        result = await self.session.execute(query_stmt)
        return list(result.scalars().all())

    # ==============================================
    # GET GROUPS WITH RESTAURANTS
    # ==============================================

    async def get_with_restaurants(
        self,
        *,
        owner_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[RestaurantGroup]:
        """
        الحصول على مجموعات المطاعم مع المطاعم التابعة لها.
        
        Args:
            owner_id: معرف المالك
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            List[RestaurantGroup]: قائمة المجموعات مع المطاعم
        """
        logger.info(
            "repo_get_groups_with_restaurants",
            extra={
                "owner_id": owner_id,
                "skip": skip,
                "limit": limit,
            },
        )

        query = (
            select(RestaurantGroup)
            .where(
                and_(
                    RestaurantGroup.owner_id == owner_id,
                    RestaurantGroup.is_active == True,
                ),
            )
            .options(
                selectinload(RestaurantGroup.restaurants),
                selectinload(RestaurantGroup.branch_links).selectinload(RestaurantBranch.restaurant),
            )
            .offset(skip)
            .limit(limit)
            .order_by(RestaurantGroup.name.asc())
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    # ==============================================
    # GET GROUP STATISTICS
    # ==============================================

    async def get_statistics(
        self,
        *,
        owner_id: int,
    ) -> Dict[str, Any]:
        """
        الحصول على إحصائيات مجموعات المطاعم لمالك معين.
        
        Args:
            owner_id: معرف المالك
            
        Returns:
            Dict[str, Any]: إحصائيات المجموعات
        """
        logger.info(
            "repo_get_group_statistics",
            extra={"owner_id": owner_id},
        )

        total = await self.count_by_owner(
            owner_id=owner_id,
            include_inactive=False,
        )

        active = await self.count_by_owner(
            owner_id=owner_id,
            include_inactive=False,
        )

        return {
            "total_groups": total,
            "active_groups": active,
            "inactive_groups": total - active,
        }

    # ==========================================
    # ✏️ MUTATIONS
    # ==========================================

    # ==============================================
    # TOGGLE GROUP ACTIVE
    # ==============================================

    async def toggle_active(
        self,
        *,
        group_id: int,
    ) -> Optional[RestaurantGroup]:
        """
        تبديل حالة المجموعة (نشط/غير نشط).
        
        Args:
            group_id: معرف المجموعة
            
        Returns:
            Optional[RestaurantGroup]: المجموعة المحدثة أو None
        """
        logger.info(
            "repo_toggle_group_active",
            extra={"group_id": group_id},
        )

        group = await self.get_by_id(id=group_id)

        if not group:
            return None

        group.is_active = not group.is_active
        await self.session.flush()
        await self.session.refresh(group)

        return group

    # ==============================================
    # BULK TOGGLE GROUPS ACTIVE
    # ==============================================

    async def bulk_toggle_active(
        self,
        *,
        group_ids: List[int],
        is_active: bool,
    ) -> int:
        """
        تبديل حالة مجموعة من المجموعات.
        
        Args:
            group_ids: قائمة معرفات المجموعات
            is_active: الحالة الجديدة
            
        Returns:
            int: عدد المجموعات المحدثة
        """
        logger.info(
            "repo_bulk_toggle_groups_active",
            extra={
                "group_ids": group_ids,
                "is_active": is_active,
            },
        )

        if not group_ids:
            return 0

        query = (
            select(RestaurantGroup)
            .where(RestaurantGroup.id.in_(group_ids))
        )

        result = await self.session.execute(query)
        groups = list(result.scalars().all())

        for group in groups:
            group.is_active = is_active

        await self.session.flush()

        return len(groups)

    # ==============================================
    # DELETE GROUP WITH BRANCHES
    # ==============================================

    async def delete_with_branches(
        self,
        *,
        group_id: int,
    ) -> bool:
        """
        حذف مجموعة مع جميع فروعها المرتبطة.
        
        Args:
            group_id: معرف المجموعة
            
        Returns:
            bool: True إذا تم الحذف بنجاح
        """
        logger.info(
            "repo_delete_group_with_branches",
            extra={"group_id": group_id},
        )

        group = await self.get_by_id(id=group_id)

        if not group:
            return False

        await self.session.delete(group)
        await self.session.flush()

        return True


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "RestaurantGroupRepository",
]