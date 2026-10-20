# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🏢 BRANCHES REPOSITORY
# عمليات قاعدة البيانات للفروع باستخدام SQLAlchemy
# ==============================================

"""MoulAI operational module for branches repo.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from sqlalchemy import (
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models.branch import Branch
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

BranchData = Dict[str, Any]
BranchUpdateData = Dict[str, Any]
BranchList = List[Branch]

# ==============================================
# 🏢 BRANCHES REPOSITORY
# ==============================================


class BranchesRepository(BaseRepository[Branch, BranchData, BranchUpdateData]):
    """
    مستودع الفروع - يوفر عمليات خاصة بالفروع.

    مسؤول عن:
        - عمليات CRUD الأساسية للفروع
        - البحث والتصفية حسب المطعم والولاية
        - إدارة حالة النشاط
        - إحصائيات الفروع

    Attributes:
        model: نموذج Branch
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
        تهيئة مستودع الفروع.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(Branch, session)

    # ==============================================
    # LOCK A BRANCH FOR ITS ATOMIC UNIT OF WORK
    # ==============================================

    async def get_for_update(self, *, branch_id: int) -> Optional[Branch]:
        """Lock an owner-visible branch until the surrounding transaction ends."""
        result = await self.session.execute(
            self._select().where(self.model.id == branch_id).with_for_update()
        )
        return result.scalar_one_or_none()

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET BY RESTAURANT AND NAME
    # ==============================================

    async def get_by_name(
        self,
        *,
        restaurant_id: int,
        name: str,
    ) -> Optional[Branch]:
        """Return one branch by its restaurant-scoped name, when it exists."""
        try:
            result = await self.session.execute(
                select(self.model)
                .where(
                    self.model.restaurant_id == restaurant_id,
                    self.model.name == name,
                )
                .limit(1),
            )
            return result.scalar_one_or_none()
        except Exception as error:
            logger.exception(
                "branches_repo_get_by_name_failed",
                extra={
                    "restaurant_id": restaurant_id,
                    "branch_name": name,
                    "error": str(error),
                },
            )
            raise

    # ==============================================
    # GET BY RESTAURANT ID
    # ==============================================

    async def get_by_restaurant_id(
        self,
        *,
        restaurant_id: int,
        skip: int = 0,
        limit: int = 100,
        only_active: bool = True,
    ) -> BranchList:
        """
        الحصول على فروع مطعم معين.

        Args:
            restaurant_id: معرف المطعم
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            only_active: جلب الفروع النشطة فقط

        Returns:
            قائمة الفروع
        """
        try:
            query = select(self.model).where(
                self.model.restaurant_id == restaurant_id,
            )

            if only_active:
                query = query.where(self.model.is_active == True)

            query = query.order_by(self.model.id.asc()).offset(skip).limit(limit)

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "branches_repo_get_by_restaurant_failed",
                extra={
                    "restaurant_id": restaurant_id,
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
        only_active: bool = True,
    ) -> BranchList:
        """
        الحصول على فروع حسب الولاية.

        Args:
            wilaya: اسم الولاية
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            only_active: جلب الفروع النشطة فقط

        Returns:
            قائمة الفروع
        """
        try:
            query = select(self.model).where(
                self.model.wilaya == wilaya,
            )

            if only_active:
                query = query.where(self.model.is_active == True)

            query = query.order_by(self.model.id.asc()).offset(skip).limit(limit)

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "branches_repo_get_by_wilaya_failed",
                extra={
                    "wilaya": wilaya,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET ACTIVE BY RESTAURANT
    # ==============================================

    async def get_active_by_restaurant(
        self,
        *,
        restaurant_id: int,
    ) -> BranchList:
        """
        الحصول على الفروع النشطة لمطعم معين.

        Args:
            restaurant_id: معرف المطعم

        Returns:
            قائمة الفروع النشطة
        """
        return await self.get_by_restaurant_id(
            restaurant_id=restaurant_id,
            only_active=True,
        )

    # ==============================================
    # SEARCH
    # ==============================================

    async def search(
        self,
        *,
        query: str,
        skip: int = 0,
        limit: int = 100,
        restaurant_id: Optional[int] = None,
    ) -> BranchList:
        """
        البحث عن فروع.

        Args:
            query: نص البحث
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            restaurant_id: معرف المطعم (اختياري)

        Returns:
            قائمة الفروع
        """
        try:
            conditions = [
                or_(
                    self.model.name.ilike(f"%{query}%"),
                    self.model.wilaya.ilike(f"%{query}%"),
                    self.model.phone.ilike(f"%{query}%"),
                ),
            ]

            if restaurant_id is not None:
                conditions.append(
                    self.model.restaurant_id == restaurant_id,
                )

            stmt = (
                select(self.model)
                .where(*conditions)
                .where(self.model.is_active == True)
                .order_by(self.model.name.asc())
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(stmt)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "branches_repo_search_failed",
                extra={
                    "query": query,
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
        branch_id: int,
        is_active: bool,
    ) -> Optional[Branch]:
        """
        تحديث حالة الفرع.

        Args:
            branch_id: معرف الفرع
            is_active: الحالة الجديدة

        Returns:
            كائن Branch المحدث أو None
        """
        logger.info(
            "branches_repo_update_status",
            extra={
                "branch_id": branch_id,
                "is_active": is_active,
            },
        )

        return await self.update(
            id=branch_id,
            data={"is_active": is_active},
        )

    # ==============================================
    # ACTIVATE
    # ==============================================

    async def activate(
        self,
        *,
        branch_id: int,
    ) -> Optional[Branch]:
        """
        تفعيل الفرع.

        Args:
            branch_id: معرف الفرع

        Returns:
            كائن Branch المحدث أو None
        """
        logger.info(
            "branches_repo_activate",
            extra={"branch_id": branch_id},
        )

        return await self.update_status(
            branch_id=branch_id,
            is_active=True,
        )

    # ==============================================
    # DEACTIVATE
    # ==============================================

    async def deactivate(
        self,
        *,
        branch_id: int,
    ) -> Optional[Branch]:
        """
        إلغاء تفعيل الفرع.

        Args:
            branch_id: معرف الفرع

        Returns:
            كائن Branch المحدث أو None
        """
        logger.info(
            "branches_repo_deactivate",
            extra={"branch_id": branch_id},
        )

        return await self.update_status(
            branch_id=branch_id,
            is_active=False,
        )

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
        حساب عدد فروع مطعم معين.

        Args:
            restaurant_id: معرف المطعم
            only_active: حساب الفروع النشطة فقط

        Returns:
            عدد الفروع
        """
        filters = {"restaurant_id": restaurant_id}

        if only_active:
            filters["is_active"] = True

        return await self.count(filters=filters)

    # ==============================================
    # COUNT BY WILAYA
    # ==============================================

    async def count_by_wilaya(
        self,
        *,
        wilaya: str,
        only_active: bool = True,
    ) -> int:
        """
        حساب عدد الفروع في ولاية معينة.

        Args:
            wilaya: اسم الولاية
            only_active: حساب الفروع النشطة فقط

        Returns:
            عدد الفروع
        """
        filters = {"wilaya": wilaya}

        if only_active:
            filters["is_active"] = True

        return await self.count(filters=filters)


# ==============================================
