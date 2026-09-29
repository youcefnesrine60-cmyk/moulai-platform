# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🔄 RESTAURANT GROUP COMPATIBILITY
# دوال متوافقة مع الاستيرادات القديمة
# ==============================================

from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.restaurant.restaurant_group import (
    RestaurantBranchBulkCreate,
    RestaurantGroupCreate,
    RestaurantGroupUpdate,
)
from app.services.business.restaurant.groups.branch_handlers import (
    RestaurantBranchEventHandlers,
)
from app.services.business.restaurant.groups.handlers import (
    RestaurantGroupEventHandlers,
)
from app.services.business.restaurant.groups.service import (
    RestaurantGroupService,
)

# ==============================================
# 📦 GROUP OPERATIONS (COMPATIBILITY)
# ==============================================

# ==============================================
# CREATE GROUP
# ==============================================

async def create_group(
    *,
    owner_id: int,
    name: str,
    session: AsyncSession,
) -> int:
    """
    إنشاء مجموعة مطاعم جديدة (دالة متوافقة مع الإصدار القديم).

    ⚠️ RestaurantGroup لا يحتوي على is_active — تم إزالتها.

    Args:
        owner_id: معرف المالك
        name: اسم المجموعة
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        int: معرف المجموعة المنشأة
    """
    handlers = RestaurantGroupEventHandlers(session=session)

    group_data = RestaurantGroupCreate(
        owner_id=owner_id,
        name=name,
    )

    group = await handlers.create_group(group_data=group_data)

    return group.id


# ==============================================
# GET GROUP
# ==============================================

async def get_group(
    *,
    group_id: int,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على مجموعة مطاعم بالمعرف (دالة متوافقة مع الإصدار القديم).

    Args:
        group_id: معرف المجموعة
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        Optional[Dict[str, Any]]: قاموس بيانات المجموعة أو None
    """
    service = RestaurantGroupService(session=session)

    try:
        group = await service.get_by_id(group_id=group_id)
        return group.model_dump()
    except Exception:
        return None


# ==============================================
# GET GROUPS BY OWNER
# ==============================================

async def get_groups_by_owner(
    *,
    owner_id: int,
    session: AsyncSession,
    only_active: bool = True,
) -> List[Dict[str, Any]]:
    """
    الحصول على مجموعات المطاعم لمالك معين (دالة متوافقة مع الإصدار القديم).

    ⚠️ only_active مهمل — RestaurantGroup لا يحتوي على is_active.

    Args:
        owner_id: معرف المالك
        session: جلسة قاعدة البيانات غير المتزامنة
        only_active: مهمل (للتوافق فقط)

    Returns:
        List[Dict[str, Any]]: قائمة المجموعات
    """
    service = RestaurantGroupService(session=session)

    result = await service.get_by_owner(
        owner_id=owner_id,
    )

    return [g.model_dump() for g in result.items]


# ==============================================
# UPDATE GROUP
# ==============================================

async def update_group(
    *,
    group_id: int,
    data: Dict[str, Any],
    session: AsyncSession,
) -> None:
    """
    تحديث مجموعة مطاعم (دالة متوافقة مع الإصدار القديم).

    Args:
        group_id: معرف المجموعة
        data: بيانات التحديث
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    handlers = RestaurantGroupEventHandlers(session=session)

    update_data = RestaurantGroupUpdate(**data)

    await handlers.update_group(
        group_id=group_id,
        update_data=update_data,
    )


# ==============================================
# DELETE GROUP
# ==============================================

async def delete_group(
    *,
    group_id: int,
    session: AsyncSession,
    permanent: bool = False,
) -> None:
    """
    حذف مجموعة مطاعم (دالة متوافقة مع الإصدار القديم).

    Args:
        group_id: معرف المجموعة
        session: جلسة قاعدة البيانات غير المتزامنة
        permanent: حذف نهائي
    """
    handlers = RestaurantGroupEventHandlers(session=session)

    await handlers.delete_group(
        group_id=group_id,
        permanent=permanent,
    )


# ==============================================
# TOGGLE GROUP ACTIVE
# ==============================================

async def toggle_group_active(
    *,
    group_id: int,
    session: AsyncSession,
) -> None:
    """
    تبديل حالة المجموعة (نشط/غير نشط) (دالة متوافقة مع الإصدار القديم).

    ⚠️ RestaurantGroup لا يحتوي على is_active — عملية no-op.

    Args:
        group_id: معرف المجموعة
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    handlers = RestaurantGroupEventHandlers(session=session)

    await handlers.toggle_group_active(group_id=group_id)


# ==============================================
# 📊 BRANCH OPERATIONS (COMPATIBILITY)
# ==============================================

# ==============================================
# ADD BRANCHES TO GROUP
# ==============================================

async def add_branches_to_group(
    *,
    group_id: int,
    restaurant_ids: List[int],
    session: AsyncSession,
) -> List[Dict[str, Any]]:
    """
    إضافة فروع مطاعم إلى مجموعة (دالة متوافقة مع الإصدار القديم).

    Args:
        group_id: معرف المجموعة
        restaurant_ids: قائمة معرفات المطاعم
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        List[Dict[str, Any]]: قائمة الفروع المُنشأة
    """
    handlers = RestaurantBranchEventHandlers(session=session)

    data = RestaurantBranchBulkCreate(
        group_id=group_id,
        restaurant_ids=restaurant_ids,
    )

    branches = await handlers.add_branches_to_group(data=data)

    return [b.model_dump() for b in branches]


# ==============================================
# REMOVE BRANCH FROM GROUP
# ==============================================

async def remove_branch_from_group(
    *,
    group_id: int,
    restaurant_id: int,
    session: AsyncSession,
) -> None:
    """
    إزالة فرع مطعم من مجموعة (دالة متوافقة مع الإصدار القديم).

    Args:
        group_id: معرف المجموعة
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    handlers = RestaurantBranchEventHandlers(session=session)

    await handlers.remove_branch_from_group(
        group_id=group_id,
        restaurant_id=restaurant_id,
    )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    # Group Operations
    "create_group",
    "get_group",
    "get_groups_by_owner",
    "update_group",
    "delete_group",
    "toggle_group_active",

    # Branch Operations
    "add_branches_to_group",
    "remove_branch_from_group",
]