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

from sqlalchemy import (
    Select,
    select,
)
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
from app.core.security import sanitize_input
from app.core.security.tenant_scope import bind_owner_scope
from app.guards.feature_guard import require_feature
from app.models.branch import Branch
from app.models.restaurant import Restaurant
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


def _base_restaurant_select() -> Select[tuple[int]]:
    """Select restaurant identifiers before applying authenticated owner scope."""
    return select(Restaurant.id)


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
        *,
        session: AsyncSession,
        owner_id: int,
    ) -> None:
        """
        تهيئة خدمة الفروع.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        self.session = session
        self.owner_id = owner_id
        bind_owner_scope(session=session, owner_id=owner_id)
        self.repo = BranchesRepository(session)
        self.pricing_repo = BranchPricingRepository(session)

    # ==============================================
    # AUTHENTICATED RESTAURANT OWNERSHIP
    # ==============================================

    async def _require_owned_restaurant(
        self, *, restaurant_id: int, for_update: bool = False
    ) -> None:
        """Reject inaccessible parents before feature checks or branch operations."""
        statement = _base_restaurant_select().where(
            Restaurant.id == restaurant_id,
            Restaurant.owner_id == self.owner_id,
        )
        if for_update:
            statement = statement.with_for_update()
        restaurant = await self.session.scalar(statement)
        if restaurant is None:
            raise NotFoundError(message="Restaurant not found")

    async def _get_locked_branch(self, *, branch_id: int) -> Branch:
        """Lock the owned parent first, then its branch, before counter changes."""
        restaurant_id = await self.session.scalar(
            select(Branch.restaurant_id).where(Branch.id == branch_id)
        )
        if restaurant_id is None:
            raise NotFoundError(message="Branch not found")
        await self._require_owned_restaurant(
            restaurant_id=restaurant_id, for_update=True
        )
        branch = await self.repo.get_for_update(branch_id=branch_id)
        if branch is None or branch.restaurant_id != restaurant_id:
            raise NotFoundError(message="Branch not found")
        return branch

    async def _require_branch_entitlement(self, *, restaurant_id: int) -> None:
        """Check subscription access without treating a branch ID as permission."""
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
            raise ForbiddenError(message=error_code, error_code=error_code) from error

    async def _require_branch_capacity(self, *, restaurant_id: int) -> None:
        """Enforce the active-branch cap while holding the restaurant row lock."""
        count = await self.count_by_restaurant(
            restaurant_id=restaurant_id, only_active=True
        )
        if count >= MAX_BRANCHES_PER_RESTAURANT:
            raise BranchLimitExceededError(
                restaurant_id=restaurant_id,
                max_branches=MAX_BRANCHES_PER_RESTAURANT,
                message=f"Active branch capacity ({MAX_BRANCHES_PER_RESTAURANT}) exceeded",
            )

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

        await self._require_owned_restaurant(restaurant_id=restaurant_id)
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

        await self._require_owned_restaurant(restaurant_id=restaurant_id)
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
        if restaurant_id is not None:
            await self._require_owned_restaurant(restaurant_id=restaurant_id)

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
            await self._require_owned_restaurant(
                restaurant_id=restaurant_id, for_update=True
            )
            if not skip_feature_check:
                await self._require_branch_entitlement(restaurant_id=restaurant_id)
            await self._require_branch_capacity(restaurant_id=restaurant_id)

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

        async with branch_transaction(self.session):
            branch = await self._get_locked_branch(branch_id=branch_id)
            if not branch.is_active:
                return branch
            restaurant_id = branch.restaurant_id
            updated = await self.repo.deactivate(branch_id=branch_id)
            if updated is None:
                raise NotFoundError(message="Branch not found")
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

        async with branch_transaction(self.session):
            branch = await self._get_locked_branch(branch_id=branch_id)
            if branch.is_active:
                return branch
            restaurant_id = branch.restaurant_id
            await self._require_branch_entitlement(restaurant_id=restaurant_id)
            await self._require_branch_capacity(restaurant_id=restaurant_id)
            updated = await self.repo.activate(branch_id=branch_id)
            if updated is None:
                raise NotFoundError(message="Branch not found")
            await increase_usage(
                session=self.session,
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

        async with branch_transaction(self.session):
            branch = await self._get_locked_branch(branch_id=branch_id)
            restaurant_id = branch.restaurant_id
            was_active = branch.is_active
            if permanent:
                await self.repo.delete(id=branch_id)
            elif was_active:
                await self.repo.deactivate(branch_id=branch_id)
            else:
                return
            if was_active:
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
