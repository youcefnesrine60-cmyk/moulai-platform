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
    
    ⚠️ ملاحظة: RestaurantGroup لا يحتوي على حقل is_active
    ⚠️ ملاحظة: لا نستخدم "name" في extra لأنها محجوزة في LogRecord
    
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
        super().__init__(RestaurantGroup, session)

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
        include_inactive: bool = False,  # متجاهل — RestaurantGroup لا يحتوي على is_active
    ) -> List[RestaurantGroup]:
        """
        الحصول على مجموعات المطاعم لمالك معين.
        
        ✅ التصحيح: إزالة is_active (غير موجود في RestaurantGroup)
        
        Args:
            owner_id: معرف المالك
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            include_inactive: متجاهل (RestaurantGroup لا يحتوي على is_active)
            
        Returns:
            List[RestaurantGroup]: قائمة مجموعات المطاعم
        """
        logger.info(
            "repo_get_groups_by_owner",
            extra={
                "owner_id": owner_id,
                "skip": skip,
                "limit": limit,
            },
        )

        # ✅ إزالة is_active من الاستعلام
        query = (
            select(RestaurantGroup)
            .where(RestaurantGroup.owner_id == owner_id)
            .offset(skip)
            .limit(limit)
            .order_by(RestaurantGroup.created_at.desc())
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    # ==============================================
    # COUNT GROUPS BY OWNER
    # ==============================================

    async def count_by_owner(
        self,
        *,
        owner_id: int,
        include_inactive: bool = False,  # متجاهل
    ) -> int:
        """
        حساب عدد مجموعات المطاعم لمالك معين.
        
        ✅ التصحيح: إزالة is_active
        
        Args:
            owner_id: معرف المالك
            include_inactive: متجاهل
            
        Returns:
            int: عدد المجموعات
        """
        # ✅ إزالة is_active من الاستعلام
        query = (
            select(func.count())
            .select_from(RestaurantGroup)
            .where(RestaurantGroup.owner_id == owner_id)
        )

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
        include_inactive: bool = False,  # متجاهل
    ) -> Optional[RestaurantGroup]:
        """
        الحصول على مجموعة مطاعم بواسطة اسمها.
        
        ✅ التصحيح 1: إزالة is_active
        ✅ التصحيح 2: استخدام "group_name" بدلاً من "name" في extra
                      لأن "name" محجوزة في LogRecord
        
        Args:
            owner_id: معرف المالك
            name: اسم المجموعة
            include_inactive: متجاهل
            
        Returns:
            Optional[RestaurantGroup]: المجموعة أو None
        """
        logger.info(
            "repo_get_group_by_name",
            extra={
                "owner_id": owner_id,
                "group_name": name,  # ✅ استخدام group_name بدلاً من name
            },
        )

        # ✅ إزالة is_active من الاستعلام
        query = (
            select(RestaurantGroup)
            .where(
                and_(
                    RestaurantGroup.owner_id == owner_id,
                    RestaurantGroup.name == name,
                ),
            )
        )

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
        only_active: bool = True,  # متجاهل
        skip: int = 0,
        limit: int = 100,
    ) -> List[RestaurantGroup]:
        """
        البحث عن مجموعات المطاعم.
        
        ✅ التصحيح: إزالة is_active
        
        Args:
            query: نص البحث
            owner_id: معرف المالك (اختياري)
            only_active: متجاهل
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            List[RestaurantGroup]: قائمة المجموعات المطابقة
        """
        logger.info(
            "repo_search_groups",
            extra={
                "search_query": query,  # ✅ استخدام search_query بدلاً من query (query محجوزة أيضاً!)
                "owner_id": owner_id,
            },
        )

        # ✅ إزالة is_active من الشروط
        conditions = [RestaurantGroup.name.ilike(f"%{query}%")]

        if owner_id is not None:
            conditions.append(RestaurantGroup.owner_id == owner_id)

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
        
        ✅ التصحيح: إزالة is_active
        
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

        # ✅ إزالة is_active من الاستعلام
        query = (
            select(RestaurantGroup)
            .where(RestaurantGroup.owner_id == owner_id)
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
        
        ✅ التصحيح: إزالة is_active
        
        Args:
            owner_id: معرف المالك
            
        Returns:
            Dict[str, Any]: إحصائيات المجموعات
        """
        logger.info(
            "repo_get_group_statistics",
            extra={"owner_id": owner_id},
        )

        total = await self.count_by_owner(owner_id=owner_id)

        # ✅ RestaurantGroup لا يحتوي على is_active — الكل نشط
        return {
            "total_groups": total,
            "active_groups": total,
            "inactive_groups": 0,
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
        
        ⚠️ RestaurantGroup لا يحتوي على is_active
        هذه الدالة موجودة للتوافق فقط — تُعيد المجموعة كما هي.
        
        Args:
            group_id: معرف المجموعة
            
        Returns:
            Optional[RestaurantGroup]: المجموعة أو None
        """
        logger.info(
            "repo_toggle_group_active",
            extra={"group_id": group_id},
        )

        group = await self.get_by_id(id=group_id)

        if not group:
            return None

        # ⚠️ لا يوجد is_active — نُعيد المجموعة كما هي
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
        
        ⚠️ RestaurantGroup لا يحتوي على is_active
        هذه الدالة موجودة للتوافق فقط — تُعيد 0.
        
        Args:
            group_ids: قائمة معرفات المجموعات
            is_active: الحالة الجديدة (متجاهل)
            
        Returns:
            int: 0 (لأنه لا يوجد is_active)
        """
        logger.info(
            "repo_bulk_toggle_groups_active",
            extra={
                "group_ids": group_ids,
                "is_active": is_active,
            },
        )

        # ⚠️ لا يوجد is_active — نُعيد 0
        return 0

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
