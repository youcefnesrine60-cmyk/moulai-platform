# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🔗 RESTAURANT BRANCH EVENT HANDLERS
# معالجات أحداث فروع المطاعم
# ==============================================

"""MoulAI operational module for branch handlers.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.schemas.restaurant.restaurant_group import (
    RestaurantBranchResponse,
    RestaurantBranchBulkCreate,
)
from app.services.business.restaurant.groups.service import RestaurantGroupService

# ==============================================
# 🔗 RESTAURANT BRANCH EVENT HANDLERS
# ==============================================


class RestaurantBranchEventHandlers:
    """
    معالجات أحداث فروع المطاعم.

    تتعامل مع عمليات إضافة وإزالة فروع المطاعم من المجموعات.

    Attributes:
        session: جلسة قاعدة البيانات غير المتزامنة
        service: خدمة مجموعات المطاعم
    """

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة معالجات الأحداث.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        self.session = session
        self.service = RestaurantGroupService(session)

    # ==========================================
    # 📊 BRANCH OPERATIONS
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

        Args:
            data: بيانات الفروع

        Returns:
            List[RestaurantBranchResponse]: قائمة الفروع المنشأة

        Raises:
            NotFoundError: إذا لم يتم العثور على المجموعة
        """
        logger.info(
            "handler_add_branches_to_group",
            extra={
                "group_id": data.group_id,
                "restaurant_count": len(data.restaurant_ids),
            },
        )

        return await self.service.add_branches_to_group(data=data)

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
            "handler_remove_branch_from_group",
            extra={
                "group_id": group_id,
                "restaurant_id": restaurant_id,
            },
        )

        await self.service.remove_branch_from_group(
            group_id=group_id,
            restaurant_id=restaurant_id,
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
            "handler_remove_all_branches_from_group",
            extra={"group_id": group_id},
        )

        return await self.service.remove_all_branches_from_group(
            group_id=group_id,
        )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "RestaurantBranchEventHandlers",
]
