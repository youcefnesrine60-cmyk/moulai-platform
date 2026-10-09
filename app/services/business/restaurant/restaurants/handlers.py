# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🏪 RESTAURANT EVENT HANDLERS
# معالجات أحداث المطاعم
# ==============================================

"""MoulAI operational module for handlers.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.core.logger import logger
from app.core.security import sanitize_input
from app.schemas.restaurant import (
    RestaurantCreate,
    RestaurantResponse,
    RestaurantUpdate,
)
from app.services.business.restaurant.restaurants.service import RestaurantService
from app.services.business.restaurant.restaurants.validators import (
    validate_owner_limit,
    validate_restaurant_type,
)

# ==============================================
# 🏪 RESTAURANT EVENT HANDLERS
# ==============================================


class RestaurantEventHandlers:
    """
    معالجات أحداث المطاعم.

    تتعامل مع عمليات إنشاء وتحديث وحذف المطاعم.

    Attributes:
        session: جلسة قاعدة البيانات غير المتزامنة
        service: خدمة المطاعم
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
        self.service = RestaurantService(session)

    # ==========================================
    # 📦 RESTAURANT OPERATIONS
    # ==========================================

    # ==============================================
    # CREATE RESTAURANT
    # ==============================================

    async def create_restaurant(
        self,
        *,
        restaurant_data: RestaurantCreate,
    ) -> RestaurantResponse:
        """
        إنشاء مطعم جديد.

        Args:
            restaurant_data: بيانات المطعم

        Returns:
            RestaurantResponse: بيانات المطعم المنشأ

        Raises:
            ConflictError: إذا كان الاسم موجوداً مسبقاً لنفس المالك
            ValidationError: إذا كانت البيانات غير صالحة
        """
        # تنظيف البيانات
        name = sanitize_input(restaurant_data.name)
        wilaya = (
            sanitize_input(restaurant_data.wilaya) if restaurant_data.wilaya else None
        )

        logger.info(
            "restaurant_handler_create",
            extra={
                "owner_id": restaurant_data.owner_id,
                "restaurant_name": name,
                "type": restaurant_data.type,
            },
        )

        # التحقق من صحة نوع المطعم
        validate_restaurant_type(restaurant_data.type)

        # التحقق من الحد الأقصى للمطاعم لكل مالك
        current_count = await self.service.count_owner_restaurants(
            owner_id=restaurant_data.owner_id,
        )
        validate_owner_limit(current_count)

        # التحقق من عدم وجود مطعم بنفس الاسم لنفس المالك
        existing = await self.service.repo.get_by_name_and_owner(
            owner_id=restaurant_data.owner_id,
            name=name,
        )

        if existing:
            raise ConflictError(
                message=f"يوجد مطعم باسم '{name}' موجود مسبقاً لهذا المالك",
            )

        # إنشاء المطعم
        data = {
            "owner_id": restaurant_data.owner_id,
            "name": name,
            "type": restaurant_data.type,
            "phone": restaurant_data.phone,
            "wilaya": wilaya,
            "lat": restaurant_data.lat,
            "lng": restaurant_data.lng,
            "group_id": restaurant_data.group_id,
            "is_active": (
                restaurant_data.is_active
                if restaurant_data.is_active is not None
                else True
            ),
        }

        restaurant = await self.service.repo.create(data=data)

        logger.info(
            "restaurant_created_successfully",
            extra={
                "restaurant_id": restaurant.id,
                "restaurant_name": restaurant.name,
            },
        )

        return RestaurantResponse.model_validate(restaurant)

    # ==============================================
    # UPDATE RESTAURANT
    # ==============================================

    async def update_restaurant(
        self,
        *,
        restaurant_id: int,
        update_data: RestaurantUpdate,
    ) -> RestaurantResponse:
        """
        تحديث مطعم.

        Args:
            restaurant_id: معرف المطعم
            update_data: بيانات التحديث

        Returns:
            RestaurantResponse: بيانات المطعم المحدث

        Raises:
            NotFoundError: إذا لم يتم العثور على المطعم
            ConflictError: إذا كان الاسم موجوداً مسبقاً
            ValidationError: إذا كانت البيانات غير صالحة
        """
        logger.info(
            "restaurant_handler_update",
            extra={
                "restaurant_id": restaurant_id,
                "fields": list(update_data.model_dump(exclude_unset=True).keys()),
            },
        )

        # ✅ التحقق من وجود المطعم - استخدام id بدلاً من restaurant_id
        existing = await self.service.repo.get_by_id(
            id=restaurant_id,
        )

        if not existing:
            raise NotFoundError(
                message=f"المطعم بـ ID '{restaurant_id}' غير موجود",
            )

        # تحضير بيانات التحديث
        updates = update_data.model_dump(exclude_unset=True)

        # تنظيف البيانات والتحقق منها
        if "name" in updates:
            updates["name"] = sanitize_input(updates["name"])

            # التحقق من عدم وجود اسم مكرر لنفس المالك
            duplicate = await self.service.repo.get_by_name_and_owner(
                owner_id=existing.owner_id,
                name=updates["name"],
            )

            if duplicate and duplicate.id != restaurant_id:
                raise ConflictError(
                    message=f"يوجد مطعم باسم '{updates['name']}' موجود مسبقاً لهذا المالك",
                )

        if "wilaya" in updates:
            updates["wilaya"] = (
                sanitize_input(updates["wilaya"]) if updates["wilaya"] else None
            )

        if "type" in updates:
            validate_restaurant_type(updates["type"])

        # ✅ تحديث المطعم - استخدام id بدلاً من restaurant_id
        restaurant = await self.service.repo.update(
            id=restaurant_id,
            data=updates,
        )

        if not restaurant:
            raise NotFoundError(
                message=f"المطعم بـ ID '{restaurant_id}' غير موجود",
            )

        logger.info(
            "restaurant_updated_successfully",
            extra={
                "restaurant_id": restaurant_id,
                "updated_fields": list(updates.keys()),
            },
        )

        return RestaurantResponse.model_validate(restaurant)

    # ==============================================
    # TOGGLE RESTAURANT STATUS
    # ==============================================

    async def toggle_restaurant_status(
        self,
        *,
        restaurant_id: int,
        is_active: bool,
    ) -> RestaurantResponse:
        """
        تفعيل/تعطيل مطعم.

        Args:
            restaurant_id: معرف المطعم
            is_active: الحالة الجديدة

        Returns:
            RestaurantResponse: بيانات المطعم المحدث

        Raises:
            NotFoundError: إذا لم يتم العثور على المطعم
        """
        logger.info(
            "restaurant_handler_toggle_status",
            extra={
                "restaurant_id": restaurant_id,
                "is_active": is_active,
            },
        )

        # ✅ استخدام id بدلاً من restaurant_id
        restaurant = await self.service.repo.update_status(
            restaurant_id=restaurant_id,
            is_active=is_active,
        )

        if not restaurant:
            raise NotFoundError(
                message=f"المطعم بـ ID '{restaurant_id}' غير موجود",
            )

        logger.info(
            "restaurant_status_toggled_successfully",
            extra={
                "restaurant_id": restaurant_id,
                "is_active": is_active,
            },
        )

        return RestaurantResponse.model_validate(restaurant)

    # ==============================================
    # DELETE RESTAURANT
    # ==============================================

    async def delete_restaurant(
        self,
        *,
        restaurant_id: int,
    ) -> None:
        """
        حذف مطعم.

        Args:
            restaurant_id: معرف المطعم

        Raises:
            NotFoundError: إذا لم يتم العثور على المطعم
            ValidationError: إذا كان المطعم يحتوي على فروع أو منتجات
        """
        logger.info(
            "restaurant_handler_delete",
            extra={"restaurant_id": restaurant_id},
        )

        # ✅ التحقق من وجود المطعم - استخدام id بدلاً من restaurant_id
        restaurant = await self.service.repo.get_by_id(
            id=restaurant_id,
        )

        if not restaurant:
            raise NotFoundError(
                message=f"المطعم بـ ID '{restaurant_id}' غير موجود",
            )

        # التحقق من وجود فروع تابعة
        branches_count = await self.service.repo.count_branches(
            restaurant_id=restaurant_id,
        )

        if branches_count > 0:
            raise ValidationError(
                message="لا يمكن حذف المطعم لأنه يحتوي على فروع",
                details={
                    "restaurant_id": restaurant_id,
                    "branches_count": branches_count,
                },
            )

        # التحقق من وجود منتجات
        products_count = await self.service.repo.count_products(
            restaurant_id=restaurant_id,
        )

        if products_count > 0:
            raise ValidationError(
                message="لا يمكن حذف المطعم لأنه يحتوي على منتجات",
                details={
                    "restaurant_id": restaurant_id,
                    "products_count": products_count,
                },
            )

        # ✅ حذف المطعم - استخدام id بدلاً من restaurant_id
        deleted = await self.service.repo.delete(
            id=restaurant_id,
        )

        if not deleted:
            raise NotFoundError(
                message=f"المطعم بـ ID '{restaurant_id}' غير موجود",
            )

        logger.info(
            "restaurant_deleted_successfully",
            extra={"restaurant_id": restaurant_id},
        )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "RestaurantEventHandlers",
]
