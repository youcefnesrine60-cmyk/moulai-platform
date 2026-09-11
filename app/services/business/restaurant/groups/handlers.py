# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🏢 RESTAURANT GROUP EVENT HANDLERS
# معالجات أحداث مجموعات المطاعم
# ==============================================

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.schemas.restaurant.restaurant_group import (
    RestaurantGroupCreate,
    RestaurantGroupResponse,
    RestaurantGroupUpdate,
)
from app.services.business.restaurant.groups.service import RestaurantGroupService


# ==============================================
# 🏢 RESTAURANT GROUP EVENT HANDLERS
# ==============================================

class RestaurantGroupEventHandlers:
    """
    معالجات أحداث مجموعات المطاعم.
    
    تتعامل مع عمليات إنشاء وتحديث وحذف مجموعات المطاعم.
    
    Attributes:
        session: جلسة قاعدة البيانات غير المتزامنة
        service: خدمة مجموعات المطاعم
    """

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
    # 📦 GROUP OPERATIONS
    # ==========================================

    # ==============================================
    # CREATE GROUP
    # ==============================================

    async def create_group(
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
            "handler_create_group",
            extra={
                "owner_id": group_data.owner_id,
                "group_name": group_data.name,
            },
        )

        return await self.service.create(group_data=group_data)

    # ==============================================
    # UPDATE GROUP
    # ==============================================

    async def update_group(
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
            "handler_update_group",
            extra={
                "group_id": group_id,
                "group_name": update_data.name,
                "fields": list(update_data.model_dump(exclude_unset=True).keys()),
            },
        )

        return await self.service.update(
            group_id=group_id,
            update_data=update_data,
        )

    # ==============================================
    # TOGGLE GROUP ACTIVE
    # ==============================================

    async def toggle_group_active(
        self,
        *,
        group_id: int,
    ) -> RestaurantGroupResponse:
        """
        تبديل حالة المجموعة (نشط/غير نشط).
        
        Args:
            group_id: معرف المجموعة
            
        Returns:
            RestaurantGroupResponse: بيانات المجموعة المحدثة
            
        Raises:
            NotFoundError: إذا لم يتم العثور على المجموعة
        """
        logger.info(
            "handler_toggle_group_active",
            extra={
                "group_id": group_id
            },
        )

        return await self.service.toggle_active(group_id=group_id)

    # ==============================================
    # DELETE GROUP
    # ==============================================

    async def delete_group(
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
            "handler_delete_group",
            extra={
                "group_id": group_id,
                "permanent": permanent,
            },
        )

        await self.service.delete(
            group_id=group_id,
            permanent=permanent,
        )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "RestaurantGroupEventHandlers",
]