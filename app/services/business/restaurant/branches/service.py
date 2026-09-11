# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🔗 RESTAURANT BRANCH SERVICE
# منطق الأعمال لفروع المطاعم
# ==============================================

from typing import (
    List,
    Optional,
)

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
)
from app.core.logger import logger
from app.repositories.restaurant.restaurant_branch_repo import RestaurantBranchRepository
from app.repositories.restaurant.restaurant_group_repo import RestaurantGroupRepository
from app.schemas.restaurant.restaurant_group import (
    RestaurantBranchCreate,
    RestaurantBranchResponse,
    RestaurantBranchListResponse,
)


# ==============================================
# 🔗 RESTAURANT BRANCH SERVICE
# ==============================================

class RestaurantBranchService:
    """
    خدمة فروع المطاعم.
    
    تدير منطق الأعمال لفروع المطاعم.
    
    Attributes:
        session: جلسة قاعدة البيانات غير المتزامنة
        repo: مستودع فروع المطاعم
        group_repo: مستودع مجموعات المطاعم
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة خدمة فروع المطاعم.
        
        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        self.session = session
        self.repo = RestaurantBranchRepository(session)
        self.group_repo = RestaurantGroupRepository(session)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET BRANCH BY ID
    # ==============================================

    async def get_by_id(
        self,
        *,
        branch_id: int,
    ) -> RestaurantBranchResponse:
        """
        الحصول على فرع مطعم بالمعرف.
        
        Args:
            branch_id: معرف الفرع
            
        Returns:
            RestaurantBranchResponse: بيانات الفرع
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الفرع
        """
        logger.info(
            "service_get_branch_by_id",
            extra={"branch_id": branch_id},
        )

        branch = await self.repo.get_by_id(id=branch_id)

        if not branch:
            raise NotFoundError(
                message=f"الفرع بـ ID '{branch_id}' غير موجود",
            )

        return RestaurantBranchResponse.model_validate(branch)

    # ==============================================
    # GET BRANCH BY ID WITH DETAILS
    # ==============================================

    async def get_by_id_with_details(
        self,
        *,
        branch_id: int,
    ) -> RestaurantBranchResponse:
        """
        الحصول على فرع مطعم بالمعرف مع تفاصيله.
        
        Args:
            branch_id: معرف الفرع
            
        Returns:
            RestaurantBranchResponse: بيانات الفرع مع التفاصيل
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الفرع
        """
        logger.info(
            "service_get_branch_by_id_with_details",
            extra={"branch_id": branch_id},
        )

        branch = await self.repo.get_by_id_with_details(branch_id=branch_id)

        if not branch:
            raise NotFoundError(
                message=f"الفرع بـ ID '{branch_id}' غير موجود",
            )

        return RestaurantBranchResponse.model_validate(branch)

    # ==============================================
    # GET BRANCHES BY GROUP
    # ==============================================

    async def get_by_group(
        self,
        *,
        group_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> RestaurantBranchListResponse:
        """
        الحصول على فروع المطاعم لمجموعة معينة.
        
        Args:
            group_id: معرف المجموعة
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            RestaurantBranchListResponse: قائمة الفروع مع الإحصائيات
        """
        logger.info(
            "service_get_branches_by_group",
            extra={
                "group_id": group_id,
                "skip": skip,
                "limit": limit,
            },
        )

        branches = await self.repo.get_by_group(
            group_id=group_id,
            skip=skip,
            limit=limit,
        )

        total = await self.repo.count_by_group(group_id=group_id)

        return RestaurantBranchListResponse(
            items=[RestaurantBranchResponse.model_validate(b) for b in branches],
            total=total,
            skip=skip,
            limit=limit,
        )

    # ==============================================
    # GET BRANCHES BY RESTAURANT
    # ==============================================

    async def get_by_restaurant(
        self,
        *,
        restaurant_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> RestaurantBranchListResponse:
        """
        الحصول على فروع المطاعم لمطعم معين.
        
        Args:
            restaurant_id: معرف المطعم
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            RestaurantBranchListResponse: قائمة الفروع مع الإحصائيات
        """
        logger.info(
            "service_get_branches_by_restaurant",
            extra={
                "restaurant_id": restaurant_id,
                "skip": skip,
                "limit": limit,
            },
        )

        branches = await self.repo.get_by_restaurant(
            restaurant_id=restaurant_id,
            skip=skip,
            limit=limit,
        )

        total = await self.repo.count_by_restaurant(restaurant_id=restaurant_id)

        return RestaurantBranchListResponse(
            items=[RestaurantBranchResponse.model_validate(b) for b in branches],
            total=total,
            skip=skip,
            limit=limit,
        )

    # ==========================================
    # ✏️ MUTATIONS
    # ==========================================

    # ==============================================
    # CREATE BRANCH
    # ==============================================

    async def create(
        self,
        *,
        branch_data: RestaurantBranchCreate,
    ) -> RestaurantBranchResponse:
        """
        إنشاء فرع مطعم جديد.
        
        Args:
            branch_data: بيانات الفرع
            
        Returns:
            RestaurantBranchResponse: بيانات الفرع المنشأ
            
        Raises:
            NotFoundError: إذا لم يتم العثور على المجموعة
            ConflictError: إذا كان الفرع موجوداً مسبقاً
        """
        logger.info(
            "service_create_branch",
            extra={
                "group_id": branch_data.group_id,
                "restaurant_id": branch_data.restaurant_id,
            },
        )

        # التحقق من وجود المجموعة
        group = await self.group_repo.get_by_id(id=branch_data.group_id)

        if not group:
            raise NotFoundError(
                message=f"المجموعة بـ ID '{branch_data.group_id}' غير موجودة",
            )

        # التحقق من عدم وجود فرع مكرر
        existing = await self.repo.get_by_group_and_restaurant(
            group_id=branch_data.group_id,
            restaurant_id=branch_data.restaurant_id,
        )

        if existing:
            raise ConflictError(
                message=f"الفرع بين المجموعة '{branch_data.group_id}' والمطعم '{branch_data.restaurant_id}' موجود مسبقاً",
            )

        # إنشاء الفرع
        data = {
            "group_id": branch_data.group_id,
            "restaurant_id": branch_data.restaurant_id,
        }

        branch = await self.repo.create(data=data)
        await self.session.commit()

        logger.info(
            "branch_created_successfully",
            extra={
                "branch_id": branch.id,
                "group_id": branch_data.group_id,
                "restaurant_id": branch_data.restaurant_id,
            },
        )

        return RestaurantBranchResponse.model_validate(branch)

    # ==============================================
    # DELETE BRANCH
    # ==============================================

    async def delete(
        self,
        *,
        branch_id: int,
    ) -> None:
        """
        حذف فرع مطعم.
        
        Args:
            branch_id: معرف الفرع
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الفرع
        """
        logger.info(
            "service_delete_branch",
            extra={"branch_id": branch_id},
        )

        branch = await self.repo.get_by_id(id=branch_id)

        if not branch:
            raise NotFoundError(
                message=f"الفرع بـ ID '{branch_id}' غير موجود",
            )

        await self.repo.delete(id=branch_id)
        await self.session.commit()

        logger.info(
            "branch_deleted_successfully",
            extra={"branch_id": branch_id},
        )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "RestaurantBranchService",
]