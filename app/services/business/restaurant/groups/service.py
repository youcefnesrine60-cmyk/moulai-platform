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

"""MoulAI operational module for service.

Part of MoulAI Platform - Agent-as-a-Service.
"""

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
from app.repositories.restaurant.restaurant_branch_repo import (
    RestaurantBranchRepository,
)
from app.repositories.restaurant.restaurant_group_repo import RestaurantGroupRepository
from app.repositories.restaurant.restaurant_repo import RestaurantRepository
from app.schemas.restaurant.restaurant_group import (
    RestaurantBranchBulkCreate,
    RestaurantBranchResponse,
    RestaurantGroupCreate,
    RestaurantGroupListResponse,
    RestaurantGroupResponse,
    RestaurantGroupStatistics,
    RestaurantGroupUpdate,
)

# ==============================================
# 🏢 RESTAURANT GROUP SERVICE
# ==============================================


class RestaurantGroupService:
    """
    خدمة مجموعات المطاعم.

    تدير منطق الأعمال لمجموعات المطاعم.

    ⚠️ ملاحظة: RestaurantGroup لا يحتوي على حقل is_active.
    جميع المجموعات تُعتبر نشطة.

    Attributes:
        session: جلسة قاعدة البيانات غير المتزامنة
        repo: مستودع مجموعات المطاعم
        branch_repo: مستودع فروع المطاعم
        restaurant_repo: مستودع المطاعم
    """

    # ==============================================
    #   INIT
    # ==============================================

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
        self.restaurant_repo = RestaurantRepository(session)

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

        ⚠️ ملاحظة: RestaurantGroup لا يحتوي على is_active.

        Args:
            group_id: معرف المجموعة
            include_inactive: متجاهل (للتوافق مع الواجهة)

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

        ⚠️ ملاحظة: RestaurantGroup لا يحتوي على is_active.

        Args:
            owner_id: معرف المالك
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            only_active: متجاهل (للتوافق مع الواجهة)

        Returns:
            RestaurantGroupListResponse: قائمة المجموعات
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
        )

        total = await self.repo.count_by_owner(owner_id=owner_id)

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
                "group_name": name,
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
            only_active: متجاهل (للتوافق مع الواجهة)
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            RestaurantGroupListResponse: قائمة المجموعات
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

        ⚠️ ملاحظة: RestaurantGroup لا يحتوي على is_active.
        جميع المجموعات نشطة.

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
            active_groups=stats["total_groups"],
            inactive_groups=0,
        )

    # ==========================================
    # ✏️ MUTATIONS
    # ==========================================

    # ==============================================
    # CREATE GROUP
    # ==============================================

    async def create(
        self,
        *,
        group_data: RestaurantGroupCreate,
    ) -> RestaurantGroupResponse:
        """
        إنشاء مجموعة مطاعم جديدة.

        Args:
            group_data: بيانات المجموعة

        Returns:
            RestaurantGroupResponse: بيانات المجموعة المنشأة

        Raises:
            ConflictError: إذا كان الاسم موجوداً مسبقاً
        """
        logger.info(
            "service_create_group",
            extra={
                "owner_id": group_data.owner_id,
                "group_name": group_data.name,
            },
        )

        # التحقق من عدم وجود اسم مكرر
        existing = await self.repo.get_by_name(
            owner_id=group_data.owner_id,
            name=group_data.name,
        )

        if existing:
            raise ConflictError(
                message=f"مجموعة باسم '{group_data.name}' موجودة مسبقاً",
            )

        # إنشاء المجموعة
        data = group_data.model_dump(exclude_unset=True)
        group = await self.repo.create(data=data)

        return RestaurantGroupResponse.model_validate(group)

    # ==============================================
    # UPDATE GROUP
    # ==============================================

    async def update(
        self,
        *,
        group_id: int,
        update_data: RestaurantGroupUpdate,
    ) -> RestaurantGroupResponse:
        """
        تحديث مجموعة مطاعم.

        Args:
            group_id: معرف المجموعة
            update_data: بيانات التحديث

        Returns:
            RestaurantGroupResponse: بيانات المجموعة المحدثة

        Raises:
            NotFoundError: إذا لم يتم العثور على المجموعة
            ConflictError: إذا كان الاسم موجوداً مسبقاً
        """
        logger.info(
            "service_update_group",
            extra={
                "group_id": group_id,
                "fields": list(update_data.model_dump(exclude_unset=True).keys()),
            },
        )

        # التحقق من وجود المجموعة
        existing = await self.repo.get_by_id(id=group_id)

        if not existing:
            raise NotFoundError(
                message=f"المجموعة بـ ID '{group_id}' غير موجودة",
            )

        updates = update_data.model_dump(exclude_unset=True)

        # التحقق من عدم وجود اسم مكرر
        if "name" in updates:
            duplicate = await self.repo.get_by_name(
                owner_id=existing.owner_id,
                name=updates["name"],
            )

            if duplicate and duplicate.id != group_id:
                raise ConflictError(
                    message=f"مجموعة باسم '{updates['name']}' موجودة مسبقاً",
                )

        # تحديث المجموعة
        group = await self.repo.update(
            id=group_id,
            data=updates,
        )

        if not group:
            raise NotFoundError(
                message=f"المجموعة بـ ID '{group_id}' غير موجودة",
            )

        return RestaurantGroupResponse.model_validate(group)

    # ==============================================
    # TOGGLE GROUP ACTIVE
    # ==============================================

    async def toggle_active(
        self,
        *,
        group_id: int,
    ) -> RestaurantGroupResponse:
        """
        تبديل حالة المجموعة (نشط/غير نشط).

        ⚠️ ملاحظة: RestaurantGroup لا يحتوي على is_active.
        هذه الدالة موجودة للتوافق فقط — تُعيد المجموعة كما هي.

        Args:
            group_id: معرف المجموعة

        Returns:
            RestaurantGroupResponse: بيانات المجموعة

        Raises:
            NotFoundError: إذا لم يتم العثور على المجموعة
        """
        logger.info(
            "service_toggle_group_active",
            extra={"group_id": group_id},
        )

        group = await self.repo.get_by_id(id=group_id)

        if not group:
            raise NotFoundError(
                message=f"المجموعة بـ ID '{group_id}' غير موجودة",
            )

        return RestaurantGroupResponse.model_validate(group)

    # ==============================================
    # DELETE GROUP
    # ==============================================

    async def delete(
        self,
        *,
        group_id: int,
        permanent: bool = False,
    ) -> None:
        """
        حذف مجموعة مطاعم.

        Args:
            group_id: معرف المجموعة
            permanent: حذف نهائي

        Raises:
            NotFoundError: إذا لم يتم العثور على المجموعة
        """
        logger.info(
            "service_delete_group",
            extra={
                "group_id": group_id,
                "permanent": permanent,
            },
        )

        group = await self.repo.get_by_id(id=group_id)

        if not group:
            raise NotFoundError(
                message=f"المجموعة بـ ID '{group_id}' غير موجودة",
            )

        # حذف المجموعة
        await self.repo.delete(id=group_id)

    # ==========================================
    # 🔗 BRANCH OPERATIONS
    # ==========================================

    # ==============================================
    # ADD BRANCHES TO GROUP
    # ==============================================

    async def add_branches_to_group(
        self,
        *,
        data: RestaurantBranchBulkCreate,
    ) -> List[RestaurantBranchResponse]:
        """
        إضافة فروع مطاعم إلى مجموعة.

        ✅ التحقق من وجود المجموعة
        ✅ التحقق من وجود جميع المطاعم
        ✅ تجاهل المطاعم الموجودة مسبقاً

        Args:
            data: بيانات الفروع (group_id + restaurant_ids)

        Returns:
            List[RestaurantBranchResponse]: قائمة الفروع المنشأة

        Raises:
            NotFoundError: إذا لم يتم العثور على المجموعة أو أحد المطاعم
        """
        logger.info(
            "service_add_branches_to_group",
            extra={
                "group_id": data.group_id,
                "restaurant_count": len(data.restaurant_ids),
            },
        )

        # ✅ التحقق من وجود المجموعة
        group = await self.repo.get_by_id(id=data.group_id)

        if not group:
            raise NotFoundError(
                message=f"المجموعة بـ ID '{data.group_id}' غير موجودة",
            )

        # ✅ التحقق من وجود جميع المطاعم
        for restaurant_id in data.restaurant_ids:
            restaurant = await self.restaurant_repo.get_by_id(
                id=restaurant_id,
            )

            if not restaurant:
                raise NotFoundError(
                    message=f"المطعم بـ ID '{restaurant_id}' غير موجود",
                )

        # ✅ إنشاء الفروع (bulk)
        branches = await self.branch_repo.bulk_create_branches(
            group_id=data.group_id,
            restaurant_ids=data.restaurant_ids,
        )

        logger.info(
            "branches_added_to_group_successfully",
            extra={
                "group_id": data.group_id,
                "created_count": len(branches),
            },
        )

        return [RestaurantBranchResponse.model_validate(b) for b in branches]

    # ==============================================
    # REMOVE BRANCH FROM GROUP
    # ==============================================

    async def remove_branch_from_group(
        self,
        *,
        group_id: int,
        restaurant_id: int,
    ) -> None:
        """
        إزالة فرع مطعم من مجموعة.

        Args:
            group_id: معرف المجموعة
            restaurant_id: معرف المطعم

        Raises:
            NotFoundError: إذا لم يتم العثور على الفرع
        """
        logger.info(
            "service_remove_branch_from_group",
            extra={
                "group_id": group_id,
                "restaurant_id": restaurant_id,
            },
        )

        # ✅ التحقق من وجود الفرع
        branch = await self.branch_repo.get_by_group_and_restaurant(
            group_id=group_id,
            restaurant_id=restaurant_id,
        )

        if not branch:
            raise NotFoundError(
                message=f"الفرع بين المجموعة '{group_id}' والمطعم '{restaurant_id}' غير موجود",
            )

        # ✅ حذف الفرع
        deleted = await self.branch_repo.delete_by_group_and_restaurant(
            group_id=group_id,
            restaurant_id=restaurant_id,
        )

        if not deleted:
            raise NotFoundError(
                message=f"الفرع بين المجموعة '{group_id}' والمطعم '{restaurant_id}' غير موجود",
            )

        logger.info(
            "branch_removed_from_group_successfully",
            extra={
                "group_id": group_id,
                "restaurant_id": restaurant_id,
            },
        )

    # ==============================================
    # REMOVE ALL BRANCHES FROM GROUP
    # ==============================================

    async def remove_all_branches_from_group(
        self,
        *,
        group_id: int,
    ) -> int:
        """
        إزالة جميع فروع المطاعم من مجموعة.

        Args:
            group_id: معرف المجموعة

        Returns:
            int: عدد الفروع المحذوفة

        Raises:
            NotFoundError: إذا لم يتم العثور على المجموعة
        """
        logger.info(
            "service_remove_all_branches_from_group",
            extra={"group_id": group_id},
        )

        # ✅ التحقق من وجود المجموعة
        group = await self.repo.get_by_id(id=group_id)

        if not group:
            raise NotFoundError(
                message=f"المجموعة بـ ID '{group_id}' غير موجودة",
            )

        # ✅ حذف جميع الفروع
        count = await self.branch_repo.delete_by_group(
            group_id=group_id,
        )

        logger.info(
            "all_branches_removed_from_group_successfully",
            extra={
                "group_id": group_id,
                "removed_count": count,
            },
        )

        return count


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "RestaurantGroupService",
]
