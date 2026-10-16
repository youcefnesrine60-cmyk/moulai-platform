# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / SERVICES / BUSINESS / BRANCH SERVICE
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for branch service.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import SessionTransactionOrigin

# ✅ استيراد الاستثناءات
from app.core.exceptions import (
    BranchLimitExceededError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from app.core.logger import logger

# ✅ استيراد دوال الأمان (للتحقق من الصلاحيات)
from app.core.security import (
    sanitize_input,
)
from app.guards.feature_guard import require_feature
from app.models.branch import Branch
from app.repositories.branch_pricing_repo import BranchPricingRepository
from app.repositories.branches_repo import BranchesRepository

# ✅ استيراد المخططات
from app.schemas.branch import (
    BranchCreate,
    BranchListResponse,
    BranchResponse,
    BranchStatusUpdate,
    BranchSummary,
    BranchUpdate,
)
from app.services.business.feature_usage_counter_engine import (
    decrease_usage,
    increase_usage,
)

# ==============================================
# 🧩 CONSTANTS
# ==============================================

BRANCH_FEATURE_ID = 3
MAX_BRANCHES_PER_RESTAURANT = 10


# ==============================================
# 🧩 TYPES
# ==============================================

BranchData = dict[str, Any]
BranchList = list[Branch]

# ==============================================
# 🔒 BRANCH TRANSACTION BOUNDARY
# يحافظ على ذرية إنشاء الفرع وعداد استخدام الميزة
# ==============================================


@asynccontextmanager
async def branch_transaction(session: AsyncSession) -> AsyncIterator[None]:
    """Create a branch unit of work that also owns its feature usage update."""
    info: dict[str, Any] = session.info
    active = session.in_transaction()
    current = session.get_transaction() if active else None
    owns_autobegin = bool(
        current
        and current.sync_transaction.origin is SessionTransactionOrigin.AUTOBEGIN
    )
    previous = info.get("defer_repository_commit")
    info["defer_repository_commit"] = True
    try:
        async with session.begin_nested() if active else session.begin():
            yield
        if owns_autobegin:
            await session.commit()
    except BaseException:
        if owns_autobegin:
            await session.rollback()
        raise
    finally:
        if previous is None:
            info.pop("defer_repository_commit", None)
        else:
            info["defer_repository_commit"] = previous


# ==============================================
# 🏢 BRANCH SERVICE
# ==============================================


class BranchService:
    """
    خدمة الفروع - تدير منطق الأعمال للفروع.

    مسؤولة عن:
        - إنشاء وإدارة الفروع
        - تحديث حالة النشاط
        - حساب تكلفة الفروع
        - إدارة عداد استخدام الميزات

    Attributes:
        session: جلسة قاعدة البيانات غير المتزامنة
        repo: مستودع الفروع
        pricing_repo: مستودع تسعير الفروع
    """

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة خدمة الفروع.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        self.session = session
        self.repo = BranchesRepository(session)
        self.pricing_repo = BranchPricingRepository(session)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET BY ID
    # ==============================================

    async def get_by_id(
        self,
        *,
        branch_id: int,
    ) -> BranchResponse:
        """
        الحصول على فرع بالمعرف.

        Args:
            branch_id: معرف الفرع

        Returns:
            BranchResponse: بيانات الفرع

        Raises:
            NotFoundError: إذا لم يتم العثور على الفرع
        """
        logger.info(
            "branch_service_get_by_id",
            extra={"branch_id": branch_id},
        )

        branch = await self.repo.get_by_id(
            id=branch_id,
        )

        if not branch:
            raise NotFoundError(
                message=f"الفرع بـ ID '{branch_id}' غير موجود",
            )

        return BranchResponse.model_validate(branch)

    # ==============================================
    # GET BY RESTAURANT
    # ==============================================

    async def get_by_restaurant(
        self,
        *,
        restaurant_id: int,
        skip: int = 0,
        limit: int = 100,
        only_active: bool = True,
    ) -> BranchListResponse:
        """
        الحصول على فروع مطعم معين.

        Args:
            restaurant_id: معرف المطعم
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            only_active: جلب الفروع النشطة فقط

        Returns:
            BranchListResponse: قائمة الفروع مع الإحصائيات
        """
        logger.info(
            "branch_service_get_by_restaurant",
            extra={
                "restaurant_id": restaurant_id,
                "skip": skip,
                "limit": limit,
                "only_active": only_active,
            },
        )

        branches = await self.repo.get_by_restaurant_id(
            restaurant_id=restaurant_id,
            skip=skip,
            limit=limit,
            only_active=only_active,
        )

        total = await self.repo.count_by_restaurant(
            restaurant_id=restaurant_id,
            only_active=only_active,
        )

        return BranchListResponse(
            items=[BranchResponse.model_validate(branch) for branch in branches],
            total=total,
            skip=skip,
            limit=limit,
        )

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
        حساب عدد فروع مطعم معين.

        Args:
            restaurant_id: معرف المطعم
            only_active: حساب الفروع النشطة فقط

        Returns:
            int: عدد الفروع
        """
        logger.info(
            "branch_service_count_by_restaurant",
            extra={
                "restaurant_id": restaurant_id,
                "only_active": only_active,
            },
        )

        return await self.repo.count_by_restaurant(
            restaurant_id=restaurant_id,
            only_active=only_active,
        )

    # ==============================================
    # SEARCH
    # ==============================================

    async def search(
        self,
        *,
        query: str,
        restaurant_id: int | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> BranchListResponse:
        """
        البحث عن فروع.

        Args:
            query: نص البحث
            restaurant_id: معرف المطعم (اختياري)
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            BranchListResponse: قائمة الفروع مع الإحصائيات
        """
        # تنظيف النص
        clean_query = sanitize_input(query)

        logger.info(
            "branch_service_search",
            extra={
                "query": clean_query,
                "restaurant_id": restaurant_id,
                "skip": skip,
                "limit": limit,
            },
        )

        branches = await self.repo.search(
            query=clean_query,
            restaurant_id=restaurant_id,
            skip=skip,
            limit=limit,
        )

        total = len(branches)

        return BranchListResponse(
            items=[BranchResponse.model_validate(branch) for branch in branches],
            total=total,
            skip=skip,
            limit=limit,
        )

    # ==========================================
    # 💰 PRICING
    # ==========================================

    # ==============================================
    # GET BRANCH COST
    # ==============================================

    async def get_branch_cost(
        self,
        *,
        restaurant_id: int,
    ) -> float:
        """
        حساب تكلفة الفروع لمطعم معين.

        Args:
            restaurant_id: معرف المطعم

        Returns:
            float: التكلفة الإجمالية للفروع
        """
        branches_count = await self.count_by_restaurant(
            restaurant_id=restaurant_id,
        )

        cost = await self.pricing_repo.calculate_cost(
            branches_count=branches_count,
        )

        logger.info(
            "branch_service_get_branch_cost",
            extra={
                "restaurant_id": restaurant_id,
                "branches_count": branches_count,
                "cost": cost,
            },
        )

        return cost

    # ==========================================
    # 📊 STATISTICS
    # ==========================================

    # ==============================================
    # GET BRANCH SUMMARY
    # ==============================================

    async def get_branch_summary(
        self,
        *,
        restaurant_id: int,
    ) -> BranchSummary:
        """
        الحصول على ملخص الفروع لمطعم معين.

        Args:
            restaurant_id: معرف المطعم

        Returns:
            BranchSummary: ملخص الفروع
        """
        logger.info(
            "branch_service_get_branch_summary",
            extra={"restaurant_id": restaurant_id},
        )

        total = await self.count_by_restaurant(
            restaurant_id=restaurant_id,
            only_active=False,
        )

        active = await self.count_by_restaurant(
            restaurant_id=restaurant_id,
            only_active=True,
        )

        inactive = total - active

        total_cost = await self.get_branch_cost(
            restaurant_id=restaurant_id,
        )

        # توزيع الفروع حسب الولاية
        branches = await self.repo.get_by_restaurant_id(
            restaurant_id=restaurant_id,
            only_active=False,
            limit=1000,
        )

        branches_per_wilaya: dict[str, int] = {}

        for branch in branches:
            wilaya = branch.wilaya or "غير محدد"
            branches_per_wilaya[wilaya] = branches_per_wilaya.get(wilaya, 0) + 1

        return BranchSummary(
            total_branches=total,
            active_branches=active,
            inactive_branches=inactive,
            total_cost=total_cost,
            branches_per_wilaya=branches_per_wilaya,
        )

    # ==========================================
    # ✏️ MUTATIONS
    # ==========================================

    # ==============================================
    # CREATE BRANCH
    # ==============================================

    async def create_branch(
        self,
        *,
        restaurant_id: int,
        branch_data: BranchCreate,
        skip_feature_check: bool = False,
    ) -> BranchResponse:
        """Create one branch and its feature-usage increment atomically.

        ``skip_feature_check`` is reserved for documented internal migration or
        super-admin workflows. Public API endpoints never expose that argument.
        """
        name = sanitize_input(branch_data.name)

        logger.info(
            "branch_service_create",
            extra={
                "restaurant_id": restaurant_id,
                "branch_name": name,
                "feature_check_skipped": skip_feature_check,
            },
        )

        async with branch_transaction(self.session):
            if not skip_feature_check:
                try:
                    await require_feature(
                        session=self.session,
                        restaurant_id=restaurant_id,
                        feature_id=BRANCH_FEATURE_ID,
                    )
                except ValueError as error:
                    error_code = str(error)
                    if error_code not in {
                        "no_active_subscription",
                        "feature_not_available",
                        "feature_limit_reached",
                    }:
                        raise
                    raise ForbiddenError(
                        message=error_code,
                        error_code=error_code,
                    ) from error

            current_count = await self.count_by_restaurant(
                restaurant_id=restaurant_id,
                only_active=True,
            )
            if current_count >= MAX_BRANCHES_PER_RESTAURANT:
                raise BranchLimitExceededError(
                    restaurant_id=restaurant_id,
                    max_branches=MAX_BRANCHES_PER_RESTAURANT,
                    message=(
                        "تجاوزت الحد الأقصى للفروع " f"({MAX_BRANCHES_PER_RESTAURANT})"
                    ),
                )

            existing = await self.repo.get_by_name(
                restaurant_id=restaurant_id,
                name=name,
            )
            if existing:
                raise ConflictError(
                    message=(f"يوجد فرع باسم '{name}' بالفعل لهذا المطعم"),
                )

            data: BranchData = {
                "restaurant_id": restaurant_id,
                "name": name,
                "phone": branch_data.phone,
                "wilaya": branch_data.wilaya,
                "lat": branch_data.lat,
                "lng": branch_data.lng,
                "is_active": True,
            }
            branch = await self.repo.create(data=data)
            await increase_usage(
                session=self.session,
                restaurant_id=restaurant_id,
                feature_id=BRANCH_FEATURE_ID,
            )

        logger.info(
            "branch_created_successfully",
            extra={
                "branch_id": branch.id,
                "restaurant_id": restaurant_id,
            },
        )
        return BranchResponse.model_validate(branch)

    # ==============================================
    # UPDATE BRANCH
    # ==============================================

    async def update_branch(
        self,
        *,
        branch_id: int,
        update_data: BranchUpdate,
    ) -> BranchResponse:
        """
        تحديث فرع.

        Args:
            branch_id: معرف الفرع
            update_data: بيانات التحديث

        Returns:
            BranchResponse: بيانات الفرع المحدث

        Raises:
            NotFoundError: إذا لم يتم العثور على الفرع
            ConflictError: إذا كان الاسم موجوداً مسبقاً
            ValidationError: إذا كانت البيانات غير صحيحة
        """
        logger.info(
            "branch_service_update",
            extra={
                "branch_id": branch_id,
                "update_data": update_data.model_dump(exclude_unset=True),
            },
        )

        # التحقق من وجود الفرع
        branch = await self.repo.get_by_id(id=branch_id)

        if not branch:
            raise NotFoundError(
                message=f"الفرع بـ ID '{branch_id}' غير موجود",
            )

        # تحضير بيانات التحديث
        updates = update_data.model_dump(exclude_unset=True)

        # تنظيف الاسم إذا تم تغييره
        if "name" in updates:
            updates["name"] = sanitize_input(updates["name"])

            # التحقق من عدم وجود اسم مكرر
            existing = await self.repo.get_by_name(
                restaurant_id=branch.restaurant_id,
                name=updates["name"],
            )

            if existing and existing.id != branch_id:
                raise ConflictError(
                    message=f"يوجد فرع باسم '{updates['name']}' بالفعل لهذا المطعم",
                )

        # تحديث الفرع
        updated = await self.repo.update(
            id=branch_id,
            data=updates,
        )

        if not updated:
            raise NotFoundError(
                message=f"الفرع بـ ID '{branch_id}' غير موجود",
            )

        logger.info(
            "branch_updated_successfully",
            extra={
                "branch_id": branch_id,
                "updated_fields": list(updates.keys()),
            },
        )

        return BranchResponse.model_validate(updated)

    # ==============================================
    # UPDATE BRANCH STATUS
    # ==============================================

    async def update_branch_status(
        self,
        *,
        branch_id: int,
        status_data: BranchStatusUpdate,
    ) -> BranchResponse:
        """
        تحديث حالة الفرع (نشط/غير نشط).

        Args:
            branch_id: معرف الفرع
            status_data: بيانات الحالة

        Returns:
            BranchResponse: بيانات الفرع المحدث

        Raises:
            NotFoundError: إذا لم يتم العثور على الفرع
        """
        logger.info(
            "branch_service_update_status",
            extra={
                "branch_id": branch_id,
                "is_active": status_data.is_active,
            },
        )

        branch = await self.repo.get_by_id(id=branch_id)

        if not branch:
            raise NotFoundError(
                message=f"الفرع بـ ID '{branch_id}' غير موجود",
            )

        if status_data.is_active:
            # تفعيل الفرع
            updated = await self.activate_branch(branch_id=branch_id)
        else:
            # إلغاء تفعيل الفرع
            updated = await self.deactivate_branch(branch_id=branch_id)

        return BranchResponse.model_validate(updated)

    # ==============================================
    # DEACTIVATE BRANCH
    # ==============================================

    async def deactivate_branch(
        self,
        *,
        branch_id: int,
    ) -> Branch:
        """
        إلغاء تفعيل فرع.

        Args:
            branch_id: معرف الفرع

        Returns:
            Branch: كائن الفرع المحدث

        Raises:
            NotFoundError: إذا لم يتم العثور على الفرع
        """
        logger.info(
            "branch_service_deactivate",
            extra={"branch_id": branch_id},
        )

        branch = await self.repo.get_by_id(id=branch_id)

        if not branch:
            raise NotFoundError(
                message=f"الفرع بـ ID '{branch_id}' غير موجود",
            )

        restaurant_id = branch.restaurant_id

        # إلغاء تفعيل الفرع
        updated = await self.repo.deactivate(branch_id=branch_id)

        if not updated:
            raise NotFoundError(
                message=f"الفرع بـ ID '{branch_id}' غير موجود",
            )

        # تقليل عداد استخدام الميزة
        await decrease_usage(
            session=self.session,
            restaurant_id=restaurant_id,
            feature_id=BRANCH_FEATURE_ID,
        )

        logger.info(
            "branch_deactivated_successfully",
            extra={
                "branch_id": branch_id,
                "restaurant_id": restaurant_id,
            },
        )

        return updated

    # ==============================================
    # ACTIVATE BRANCH
    # ==============================================

    async def activate_branch(
        self,
        *,
        branch_id: int,
    ) -> Branch:
        """
        تفعيل فرع.

        Args:
            branch_id: معرف الفرع

        Returns:
            Branch: كائن الفرع المحدث

        Raises:
            NotFoundError: إذا لم يتم العثور على الفرع
        """
        logger.info(
            "branch_service_activate",
            extra={"branch_id": branch_id},
        )

        branch = await self.repo.get_by_id(id=branch_id)

        if not branch:
            raise NotFoundError(
                message=f"الفرع بـ ID '{branch_id}' غير موجود",
            )

        restaurant_id = branch.restaurant_id

        # تفعيل الفرع
        updated = await self.repo.activate(branch_id=branch_id)

        if not updated:
            raise NotFoundError(
                message=f"الفرع بـ ID '{branch_id}' غير موجود",
            )

        # زيادة عداد استخدام الميزة
        await increase_usage(
            restaurant_id=restaurant_id,
            feature_id=BRANCH_FEATURE_ID,
        )

        logger.info(
            "branch_activated_successfully",
            extra={
                "branch_id": branch_id,
                "restaurant_id": restaurant_id,
            },
        )

        return updated

    # ==============================================
    # DELETE BRANCH
    # ==============================================

    async def delete_branch(
        self,
        *,
        branch_id: int,
        permanent: bool = False,
    ) -> None:
        """
        حذف فرع.

        Args:
            branch_id: معرف الفرع
            permanent: حذف فعلي (بدلاً من الحذف المنطقي)

        Raises:
            NotFoundError: إذا لم يتم العثور على الفرع
        """
        logger.info(
            "branch_service_delete",
            extra={
                "branch_id": branch_id,
                "permanent": permanent,
            },
        )

        branch = await self.repo.get_by_id(id=branch_id)

        if not branch:
            raise NotFoundError(
                message=f"الفرع بـ ID '{branch_id}' غير موجود",
            )

        restaurant_id = branch.restaurant_id

        if permanent:
            # حذف فعلي
            await self.repo.delete(id=branch_id)
        else:
            # حذف منطقي (تعيين is_active = False)
            await self.repo.deactivate(branch_id=branch_id)

        # تقليل عداد استخدام الميزة
        await decrease_usage(
            session=self.session,
            restaurant_id=restaurant_id,
            feature_id=BRANCH_FEATURE_ID,
        )

        logger.info(
            "branch_deleted_successfully",
            extra={
                "branch_id": branch_id,
                "restaurant_id": restaurant_id,
                "permanent": permanent,
            },
        )
