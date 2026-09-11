# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🏢 RESTAURANT GROUP SERVICE
# منطق الأعمال لمجموعات المطاعم
# ==============================================

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.logger import logger
from app.repositories.restaurant.restaurant_group_repo import RestaurantGroupRepository
from app.repositories.restaurant.restaurant_branch_repo import RestaurantBranchRepository
from app.schemas.restaurant.restaurant_group import (
    RestaurantGroupResponse,
    RestaurantGroupListResponse,
    RestaurantGroupStatistics,
)


# ==============================================
# 🏢 RESTAURANT GROUP SERVICE
# ==============================================

class RestaurantGroupService:
    """
    خدمة مجموعات المطاعم.
    
    تدير منطق الأعمال لمجموعات المطاعم.
    
    Attributes:
        session: جلسة قاعدة البيانات غير المتزامنة
        repo: مستودع مجموعات المطاعم
        branch_repo: مستودع فروع المطاعم
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة خدمة مجموعات المطاعم.
        
        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        self.session = session
        self.repo = RestaurantGroupRepository(session)
        self.branch_repo = RestaurantBranchRepository(session)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET GROUP BY ID
    # ==============================================

    async def get_by_id(
        self,
        *,
        group_id: int,
        include_inactive: bool = False,
    ) -> RestaurantGroupResponse:
        """
        الحصول على مجموعة مطاعم بالمعرف.
        
        Args:
            group_id: معرف المجموعة
            include_inactive: تضمين المجموعات غير النشطة
            
        Returns:
            RestaurantGroupResponse: بيانات المجموعة
            
        Raises:
            NotFoundError: إذا لم يتم العثور على المجموعة
        """
        logger.info(
            "service_get_group_by_id",
            extra={
                "group_id": group_id,
                "include_inactive": include_inactive,
            },
        )

        group = await self.repo.get_by_id(id=group_id)

        if not group:
            raise NotFoundError(
                message=f"المجموعة بـ ID '{group_id}' غير موجودة",
            )

        if not include_inactive and not group.is_active:
            raise NotFoundError(
                message=f"المجموعة بـ ID '{group_id}' غير نشطة",
            )

        return RestaurantGroupResponse.model_validate(group)

    # ==============================================
    # GET GROUP BY ID WITH DETAILS
    # ==============================================

    async def get_by_id_with_details(
        self,
        *,
        group_id: int,
    ) -> RestaurantGroupResponse:
        """
        الحصول على مجموعة مطاعم بالمعرف مع تفاصيلها.
        
        Args:
            group_id: معرف المجموعة
            
        Returns:
            RestaurantGroupResponse: بيانات المجموعة مع التفاصيل
            
        Raises:
            NotFoundError: إذا لم يتم العثور على المجموعة
        """
        logger.info(
            "service_get_group_by_id_with_details",
            extra={"group_id": group_id},
        )

        group = await self.repo.get_by_id_with_details(group_id=group_id)

        if not group:
            raise NotFoundError(
                message=f"المجموعة بـ ID '{group_id}' غير موجودة",
            )

        return RestaurantGroupResponse.model_validate(group)

    # ==============================================
    # GET GROUPS BY OWNER
    # ==============================================

    async def get_by_owner(
        self,
        *,
        owner_id: int,
        skip: int = 0,
        limit: int = 100,
        only_active: bool = True,
    ) -> RestaurantGroupListResponse:
        """
        الحصول على مجموعات المطاعم لمالك معين.
        
        Args:
            owner_id: معرف المالك
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            only_active: جلب المجموعات النشطة فقط
            
        Returns:
            RestaurantGroupListResponse: قائمة المجموعات مع الإحصائيات
        """
        logger.info(
            "service_get_groups_by_owner",
            extra={
                "owner_id": owner_id,
                "skip": skip,
                "limit": limit,
                "only_active": only_active,
            },
        )

        groups = await self.repo.get_by_owner(
            owner_id=owner_id,
            skip=skip,
            limit=limit,
            include_inactive=not only_active,
        )

        total = await self.repo.count_by_owner(
            owner_id=owner_id,
            include_inactive=not only_active,
        )

        return RestaurantGroupListResponse(
            items=[RestaurantGroupResponse.model_validate(g) for g in groups],
            total=total,
            skip=skip,
            limit=limit,
        )

    # ==============================================
    # GET GROUP BY NAME
    # ==============================================

    async def get_by_name(
        self,
        *,
        owner_id: int,
        name: str,
    ) -> Optional[RestaurantGroupResponse]:
        """
        الحصول على مجموعة مطاعم بواسطة اسمها.
        
        Args:
            owner_id: معرف المالك
            name: اسم المجموعة
            
        Returns:
            Optional[RestaurantGroupResponse]: بيانات المجموعة أو None
        """
        logger.info(
            "service_get_group_by_name",
            extra={
                "owner_id": owner_id,
                "name": name,
            },
        )

        group = await self.repo.get_by_name(
            owner_id=owner_id,
            name=name,
        )

        if not group:
            return None

        return RestaurantGroupResponse.model_validate(group)

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
    ) -> RestaurantGroupListResponse:
        """
        البحث عن مجموعات المطاعم.
        
        Args:
            query: نص البحث
            owner_id: معرف المالك (اختياري)
            only_active: جلب المجموعات النشطة فقط
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            RestaurantGroupListResponse: قائمة المجموعات مع الإحصائيات
        """
        logger.info(
            "service_search_groups",
            extra={
                "query": query,
                "owner_id": owner_id,
                "only_active": only_active,
            },
        )

        groups = await self.repo.search(
            query=query,
            owner_id=owner_id,
            only_active=only_active,
            skip=skip,
            limit=limit,
        )

        total = len(groups)

        return RestaurantGroupListResponse(
            items=[RestaurantGroupResponse.model_validate(g) for g in groups],
            total=total,
            skip=skip,
            limit=limit,
        )

    # ==============================================
    # GET GROUPS WITH RESTAURANTS
    # ==============================================

    async def get_with_restaurants(
        self,
        *,
        owner_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> RestaurantGroupListResponse:
        """
        الحصول على مجموعات المطاعم مع المطاعم التابعة لها.
        
        Args:
            owner_id: معرف المالك
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            RestaurantGroupListResponse: قائمة المجموعات مع المطاعم
        """
        logger.info(
            "service_get_groups_with_restaurants",
            extra={
                "owner_id": owner_id,
                "skip": skip,
                "limit": limit,
            },
        )

        groups = await self.repo.get_with_restaurants(
            owner_id=owner_id,
            skip=skip,
            limit=limit,
        )

        total = len(groups)

        return RestaurantGroupListResponse(
            items=[RestaurantGroupResponse.model_validate(g) for g in groups],
            total=total,
            skip=skip,
            limit=limit,
        )

    # ==============================================
    # GET STATISTICS
    # ==============================================

    async def get_statistics(
        self,
        *,
        owner_id: int,
    ) -> RestaurantGroupStatistics:
        """
        الحصول على إحصائيات مجموعات المطاعم لمالك معين.
        
        Args:
            owner_id: معرف المالك
            
        Returns:
            RestaurantGroupStatistics: إحصائيات المجموعات
        """
        logger.info(
            "service_get_group_statistics",
            extra={"owner_id": owner_id},
        )

        stats = await self.repo.get_statistics(owner_id=owner_id)

        return RestaurantGroupStatistics(
            total_groups=stats["total_groups"],
            active_groups=stats["active_groups"],
            inactive_groups=stats["inactive_groups"],
        )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "RestaurantGroupService",
]