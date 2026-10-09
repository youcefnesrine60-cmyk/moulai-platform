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

    # ==========================================
    # 📖 QUERIES
    # ==========================================

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
# 🔄 COMPATIBILITY FUNCTIONS
# دوال متوافقة مع الاستيرادات القديمة
# ==============================================

# ==============================================
# CREATE BRANCH (COMPATIBILITY)
# ==============================================


async def create_branch(
    *,
    restaurant_id: int,
    name: str,
    phone: Optional[str] = None,
    wilaya: Optional[str] = None,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    session: AsyncSession,
) -> int:
    """
    إنشاء فرع جديد (دالة متوافقة مع الإصدار القديم).

    Args:
        restaurant_id: معرف المطعم
        name: اسم الفرع
        phone: رقم الهاتف
        wilaya: الولاية
        lat: خط العرض
        lng: خط الطول
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        معرف الفرع
    """
    repo = BranchesRepository(session=session)

    data: BranchData = {
        "restaurant_id": restaurant_id,
        "name": name,
        "phone": phone,
        "wilaya": wilaya,
        "lat": lat,
        "lng": lng,
        "is_active": True,
    }

    branch = await repo.create(data=data)

    logger.info(
        "branch_created",
        extra={
            "branch_id": branch.id,
            "restaurant_id": restaurant_id,
        },
    )

    return branch.id


# ==============================================
# GET BRANCH (COMPATIBILITY)
# ==============================================


async def get_branch(
    *,
    branch_id: int,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على فرع بالمعرف (دالة متوافقة مع الإصدار القديم).

    Args:
        branch_id: معرف الفرع
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        قاموس بيانات الفرع أو None
    """
    repo = BranchesRepository(session=session)

    branch = await repo.get_by_id(id=branch_id)

    if not branch:
        return None

    return {
        "id": branch.id,
        "restaurant_id": branch.restaurant_id,
        "name": branch.name,
        "phone": branch.phone,
        "wilaya": branch.wilaya,
        "lat": branch.lat,
        "lng": branch.lng,
        "is_active": branch.is_active,
        "created_at": branch.created_at,
    }


# ==============================================
# GET RESTAURANT BRANCHES (COMPATIBILITY)
# ==============================================


async def get_restaurant_branches(
    *,
    restaurant_id: int,
    session: AsyncSession,
    only_active: bool = True,
) -> List[Dict[str, Any]]:
    """
    الحصول على فروع مطعم معين (دالة متوافقة مع الإصدار القديم).

    Args:
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة
        only_active: جلب الفروع النشطة فقط

    Returns:
        قائمة الفروع
    """
    repo = BranchesRepository(session=session)

    branches = await repo.get_by_restaurant_id(
        restaurant_id=restaurant_id,
        only_active=only_active,
    )

    result = []

    for branch in branches:
        result.append(
            {
                "id": branch.id,
                "restaurant_id": branch.restaurant_id,
                "name": branch.name,
                "phone": branch.phone,
                "wilaya": branch.wilaya,
                "lat": branch.lat,
                "lng": branch.lng,
                "is_active": branch.is_active,
                "created_at": branch.created_at,
            }
        )

    return result


# ==============================================
# COUNT RESTAURANT BRANCHES (COMPATIBILITY)
# ==============================================


async def count_restaurant_branches(
    *,
    restaurant_id: int,
    session: AsyncSession,
    only_active: bool = True,
) -> int:
    """
    حساب عدد فروع مطعم معين (دالة متوافقة مع الإصدار القديم).

    Args:
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة
        only_active: حساب الفروع النشطة فقط

    Returns:
        عدد الفروع
    """
    repo = BranchesRepository(session=session)

    return await repo.count_by_restaurant(
        restaurant_id=restaurant_id,
        only_active=only_active,
    )


# ==============================================
# DELETE BRANCH (COMPATIBILITY)
# ==============================================


async def delete_branch(
    *,
    branch_id: int,
    session: AsyncSession,
) -> None:
    """
    حذف فرع (دالة متوافقة مع الإصدار القديم).

    Args:
        branch_id: معرف الفرع
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = BranchesRepository(session=session)

    await repo.delete(id=branch_id)

    logger.info(
        "branch_deleted",
        extra={"branch_id": branch_id},
    )


# ==============================================
# UPDATE BRANCH (COMPATIBILITY)
# ==============================================


async def update_branch(
    *,
    branch_id: int,
    name: str,
    phone: Optional[str] = None,
    wilaya: Optional[str] = None,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    session: AsyncSession,
) -> None:
    """
    تحديث فرع (دالة متوافقة مع الإصدار القديم).

    Args:
        branch_id: معرف الفرع
        name: اسم الفرع
        phone: رقم الهاتف
        wilaya: الولاية
        lat: خط العرض
        lng: خط الطول
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = BranchesRepository(session=session)

    data: BranchUpdateData = {
        "name": name,
        "phone": phone,
        "wilaya": wilaya,
        "lat": lat,
        "lng": lng,
    }

    await repo.update(
        id=branch_id,
        data=data,
    )

    logger.info(
        "branch_updated",
        extra={"branch_id": branch_id},
    )


# ==============================================
# DEACTIVATE BRANCH (COMPATIBILITY)
# ==============================================


async def deactivate_branch(
    *,
    branch_id: int,
    session: AsyncSession,
) -> None:
    """
    إلغاء تفعيل فرع (دالة متوافقة مع الإصدار القديم).

    Args:
        branch_id: معرف الفرع
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = BranchesRepository(session=session)

    await repo.deactivate(branch_id=branch_id)

    logger.info(
        "branch_deactivated",
        extra={"branch_id": branch_id},
    )


# ==============================================
# ACTIVATE BRANCH (COMPATIBILITY)
# ==============================================


async def activate_branch(
    *,
    branch_id: int,
    session: AsyncSession,
) -> None:
    """
    تفعيل فرع (دالة متوافقة مع الإصدار القديم).

    Args:
        branch_id: معرف الفرع
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = BranchesRepository(session=session)

    await repo.activate(branch_id=branch_id)

    logger.info(
        "branch_activated",
        extra={"branch_id": branch_id},
    )
