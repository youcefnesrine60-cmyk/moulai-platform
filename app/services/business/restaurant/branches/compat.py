# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🔗 RESTAURANT BRANCH COMPATIBILITY
# دوال متوافقة مع الاستيرادات القديمة
# ==============================================

from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.schemas.restaurant.restaurant_group import RestaurantBranchCreate
from app.services.business.restaurant.branches.service import RestaurantBranchService


# ==============================================
# 📦 COMPATIBILITY FUNCTIONS
# ==============================================

# ==============================================
# CREATE BRANCH
# ==============================================

async def create_branch(
    *,
    group_id: int,
    restaurant_id: int,
    session: AsyncSession,
) -> int:
    """
    إنشاء فرع مطعم جديد (دالة متوافقة مع الإصدار القديم).
    """
    service = RestaurantBranchService(session=session)

    branch_data = RestaurantBranchCreate(
        group_id=group_id,
        restaurant_id=restaurant_id,
    )

    branch = await service.create(branch_data=branch_data)

    return branch.id


# ==============================================
# GET BRANCH
# ==============================================

async def get_branch(
    *,
    branch_id: int,
    session: AsyncSession,
) -> Optional[dict]:
    """
    الحصول على فرع مطعم بالمعرف (دالة متوافقة مع الإصدار القديم).
    """
    service = RestaurantBranchService(session=session)

    try:
        branch = await service.get_by_id(branch_id=branch_id)
        return branch.model_dump()
    except Exception:
        return None


# ==============================================
# GET BRANCHES BY GROUP
# ==============================================

async def get_branches_by_group(
    *,
    group_id: int,
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
) -> List[dict]:
    """
    الحصول على فروع المطاعم لمجموعة معينة (دالة متوافقة مع الإصدار القديم).
    """
    service = RestaurantBranchService(session=session)

    result = await service.get_by_group(
        group_id=group_id,
        skip=skip,
        limit=limit,
    )

    return [b.model_dump() for b in result.items]


# ==============================================
# GET BRANCHES BY RESTAURANT
# ==============================================

async def get_branches_by_restaurant(
    *,
    restaurant_id: int,
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
) -> List[dict]:
    """
    الحصول على فروع المطاعم لمطعم معين (دالة متوافقة مع الإصدار القديم).
    """
    service = RestaurantBranchService(session=session)

    result = await service.get_by_restaurant(
        restaurant_id=restaurant_id,
        skip=skip,
        limit=limit,
    )

    return [b.model_dump() for b in result.items]


# ==============================================
# DELETE BRANCH
# ==============================================

async def delete_branch(
    *,
    branch_id: int,
    session: AsyncSession,
) -> None:
    """
    حذف فرع مطعم (دالة متوافقة مع الإصدار القديم).
    """
    service = RestaurantBranchService(session=session)

    await service.delete(branch_id=branch_id)

    logger.info(
        "branch_deleted",
        extra={"branch_id": branch_id},
    )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "create_branch",
    "get_branch",
    "get_branches_by_group",
    "get_branches_by_restaurant",
    "delete_branch",
]