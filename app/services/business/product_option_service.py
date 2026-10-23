# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / SERVICES / BUSINESS / PRODUCT OPTION SERVICE
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for product option service.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from typing import (
    Any,
    TypeAlias,
)

from sqlalchemy.ext.asyncio import AsyncSession

# ✅ استيراد الاستثناءات
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.core.logger import logger

# ✅ استيراد دوال الأمان
from app.core.security import sanitize_input
from app.core.security.tenant_scope import bind_owner_scope
from app.models.product_option import ProductOption
from app.repositories.option_groups_repo import OptionGroupsRepository
from app.repositories.product_option_repo import ProductOptionRepository

# ✅ استيراد المخططات
from app.schemas.product_option import (
    ProductOptionAvailabilityUpdate,
    ProductOptionCreate,
    ProductOptionListResponse,
    ProductOptionResponse,
    ProductOptionSummary,
    ProductOptionUpdate,
)
from app.services.business.catalog_transaction import catalog_transaction

# ==============================================
# 🧩 CONSTANTS
# ==============================================

MAX_OPTIONS_PER_GROUP = 20
MAX_EXTRA_PRICE = 1000000.0  # 1,000,000 DZD


# ==============================================
# 🧩 TYPES
# ==============================================

ProductOptionData: TypeAlias = dict[str, Any]
ProductOptionUpdateData: TypeAlias = dict[str, Any]
ProductOptionList: TypeAlias = list[ProductOption]


# ==============================================
# 🎯 PRODUCT OPTION SERVICE
# ==============================================


class ProductOptionService:
    """
    خدمة خيارات المنتج - تدير منطق الأعمال لخيارات المنتج.

    مسؤولة عن:
        - إنشاء خيارات المنتج
        - قراءة خيارات المنتج
        - تحديث خيارات المنتج
        - حذف خيارات المنتج

    Attributes:
        session: جلسة قاعدة البيانات غير المتزامنة
        repo: مستودع خيارات المنتج
        group_repo: مستودع مجموعات الخيارات
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
        تهيئة خدمة خيارات المنتج.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        bind_owner_scope(session=session, owner_id=owner_id)
        self.owner_id = owner_id
        self.session = session
        self.repo = ProductOptionRepository(session)
        self.group_repo = OptionGroupsRepository(session)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET BY ID
    # ==============================================

    async def get_by_id(
        self,
        *,
        option_id: int,
    ) -> ProductOptionResponse:
        """
        الحصول على خيار منتج بالمعرف.

        Args:
            option_id: معرف الخيار

        Returns:
            ProductOptionResponse: بيانات الخيار

        Raises:
            NotFoundError: إذا لم يتم العثور على الخيار
        """
        logger.info(
            "product_option_service_get_by_id",
            extra={"option_id": option_id},
        )

        option = await self.repo.get_by_id(
            id=option_id,
        )

        if not option:
            raise NotFoundError(
                message=f"خيار المنتج بـ ID '{option_id}' غير موجود",
            )

        return ProductOptionResponse.model_validate(option)

    # ==============================================
    # GET BY GROUP
    # ==============================================

    async def get_by_group(
        self,
        *,
        group_id: int,
        skip: int = 0,
        limit: int = 100,
        only_available: bool = True,
    ) -> ProductOptionListResponse:
        """
        الحصول على خيارات مجموعة معينة.

        Args:
            group_id: معرف مجموعة الخيارات
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            only_available: جلب الخيارات المتاحة فقط

        Returns:
            ProductOptionListResponse: قائمة خيارات المنتج مع الإحصائيات
        """
        logger.info(
            "product_option_service_get_by_group",
            extra={
                "group_id": group_id,
                "skip": skip,
                "limit": limit,
                "only_available": only_available,
            },
        )

        options = await self.repo.get_by_group_id(
            group_id=group_id,
            skip=skip,
            limit=limit,
            only_available=only_available,
        )

        total = await self.repo.count_by_group(
            group_id=group_id,
            only_available=only_available,
        )

        return ProductOptionListResponse(
            items=[ProductOptionResponse.model_validate(option) for option in options],
            total=total,
            skip=skip,
            limit=limit,
        )

    # ==============================================
    # GET AVAILABLE BY GROUP
    # ==============================================

    async def get_available_by_group(
        self,
        *,
        group_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> ProductOptionListResponse:
        """
        الحصول على الخيارات المتاحة لمجموعة معينة.

        Args:
            group_id: معرف مجموعة الخيارات
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            ProductOptionListResponse: قائمة الخيارات المتاحة
        """
        logger.info(
            "product_option_service_get_available_by_group",
            extra={
                "group_id": group_id,
                "skip": skip,
                "limit": limit,
            },
        )

        options = await self.repo.get_available_by_group(
            group_id=group_id,
            skip=skip,
            limit=limit,
        )

        total = await self.repo.count_available_by_group(
            group_id=group_id,
        )

        return ProductOptionListResponse(
            items=[ProductOptionResponse.model_validate(option) for option in options],
            total=total,
            skip=skip,
            limit=limit,
        )

    # ==============================================
    # SEARCH
    # ==============================================

    async def search(
        self,
        *,
        query: str,
        group_id: int | None = None,
        skip: int = 0,
        limit: int = 100,
        only_available: bool = True,
    ) -> ProductOptionListResponse:
        """
        البحث عن خيارات المنتج.

        Args:
            query: نص البحث
            group_id: معرف مجموعة الخيارات (اختياري)
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            only_available: جلب الخيارات المتاحة فقط

        Returns:
            ProductOptionListResponse: قائمة خيارات المنتج
        """
        # تنظيف النص
        clean_query = sanitize_input(query)

        logger.info(
            "product_option_service_search",
            extra={
                "query": clean_query,
                "group_id": group_id,
                "skip": skip,
                "limit": limit,
                "only_available": only_available,
            },
        )

        options = await self.repo.search(
            query=clean_query,
            group_id=group_id,
            skip=skip,
            limit=limit,
            only_available=only_available,
        )

        total = len(options)

        return ProductOptionListResponse(
            items=[ProductOptionResponse.model_validate(option) for option in options],
            total=total,
            skip=skip,
            limit=limit,
        )

    # ==========================================
    # 📊 STATISTICS
    # ==========================================

    # ==============================================
    # COUNT BY GROUP
    # ==============================================

    async def count_by_group(
        self,
        *,
        group_id: int,
        only_available: bool = True,
    ) -> int:
        """
        حساب عدد خيارات مجموعة معينة.

        Args:
            group_id: معرف مجموعة الخيارات
            only_available: حساب الخيارات المتاحة فقط

        Returns:
            int: عدد الخيارات
        """
        return await self.repo.count_by_group(
            group_id=group_id,
            only_available=only_available,
        )

    # ==============================================
    # COUNT AVAILABLE BY GROUP
    # ==============================================

    async def count_available_by_group(
        self,
        *,
        group_id: int,
    ) -> int:
        """
        حساب عدد الخيارات المتاحة لمجموعة معينة.

        Args:
            group_id: معرف مجموعة الخيارات

        Returns:
            int: عدد الخيارات المتاحة
        """
        return await self.repo.count_available_by_group(
            group_id=group_id,
        )

    # ==============================================
    # GET OPTION SUMMARY
    # ==============================================

    async def get_option_summary(
        self,
        *,
        group_id: int,
    ) -> ProductOptionSummary:
        """
        الحصول على ملخص خيارات المجموعة.

        Args:
            group_id: معرف مجموعة الخيارات

        Returns:
            ProductOptionSummary: ملخص الخيارات
        """
        logger.info(
            "product_option_service_get_option_summary",
            extra={"group_id": group_id},
        )

        statistics = await self.repo.get_statistics(group_id=group_id)
        return ProductOptionSummary(
            group_id=group_id,
            total_options=statistics.total_options,
            available_options=statistics.available_options,
            unavailable_options=(
                statistics.total_options - statistics.available_options
            ),
            total_extra_price=statistics.total_extra_price,
            avg_extra_price=statistics.avg_extra_price,
            min_extra_price=statistics.min_extra_price,
            max_extra_price=statistics.max_extra_price,
        )

    # ==========================================
    # ✏️ MUTATIONS
    # ==========================================

    # ==============================================
    # CREATE AN ATOMIC OPTION BATCH
    # ==============================================

    async def create_options_bulk(
        self, *, group_id: int, options: list[ProductOptionCreate]
    ) -> list[ProductOptionResponse]:
        """Reuse single-option rules while committing the complete batch once."""
        if not options:
            raise ValidationError(message="The option batch cannot be empty")
        async with catalog_transaction(session=self.session):
            created = [
                await self.create_option(group_id=group_id, option_data=option)
                for option in options
            ]
        return created

    # ==============================================
    # CREATE OPTION
    # ==============================================

    async def create_option(
        self,
        *,
        group_id: int,
        option_data: ProductOptionCreate,
    ) -> ProductOptionResponse:
        """
        إنشاء خيار منتج جديد.

        Args:
            group_id: معرف مجموعة الخيارات المستقل عن بيانات الخيار
            option_data: بيانات الخيار

        Returns:
            ProductOptionResponse: بيانات الخيار المنشأ

        Raises:
            NotFoundError: إذا لم يتم العثور على المجموعة
            ConflictError: إذا كان الاسم مكرراً
            ValidationError: إذا كانت البيانات غير صالحة
        """
        # تنظيف الاسم
        name = sanitize_input(option_data.name)

        logger.info(
            "product_option_service_create",
            extra={
                "group_id": group_id,
                "product_option_name": name,
                "extra_price": option_data.extra_price,
            },
        )

        # التحقق من وجود المجموعة
        group = await self.group_repo.get_by_id(
            id=group_id,
        )

        if not group:
            raise NotFoundError(
                message=f"مجموعة الخيارات بـ ID '{group_id}' غير موجودة",
            )

        # التحقق من الحد الأقصى للخيارات
        current_count = await self.count_by_group(
            group_id=group_id,
            only_available=False,
        )

        if current_count >= MAX_OPTIONS_PER_GROUP:
            raise ValidationError(
                message=f"تجاوزت الحد الأقصى للخيارات ({MAX_OPTIONS_PER_GROUP})",
                details={
                    "group_id": group_id,
                    "current_count": current_count,
                    "max_allowed": MAX_OPTIONS_PER_GROUP,
                },
            )

        # التحقق من صحة السعر الإضافي
        if option_data.extra_price < 0:
            raise ValidationError(
                message="السعر الإضافي لا يمكن أن يكون سالباً",
            )

        if option_data.extra_price > MAX_EXTRA_PRICE:
            raise ValidationError(
                message=f"السعر الإضافي يتجاوز الحد الأقصى المسموح به ({MAX_EXTRA_PRICE})",
            )

        # التحقق من عدم وجود خيار بنفس الاسم
        existing = await self.repo.get_by_name(
            group_id=group_id,
            name=name,
        )

        if existing:
            raise ConflictError(
                message=f"الخيار '{name}' موجود بالفعل في هذه المجموعة",
            )

        # إنشاء الخيار
        data: ProductOptionData = {
            "group_id": group_id,
            "name": name,
            "extra_price": option_data.extra_price,
            "is_available": (
                option_data.is_available
                if option_data.is_available is not None
                else True
            ),
            "sort_order": option_data.sort_order or 0,
        }

        option = await self.repo.create(data=data)

        logger.info(
            "product_option_created_successfully",
            extra={
                "option_id": option.id,
                "group_id": group_id,
            },
        )

        return ProductOptionResponse.model_validate(option)

    # ==============================================
    # UPDATE OPTION
    # ==============================================

    async def update_option(
        self,
        *,
        option_id: int,
        update_data: ProductOptionUpdate,
    ) -> ProductOptionResponse:
        """
        تحديث خيار منتج.

        Args:
            option_id: معرف الخيار
            update_data: بيانات التحديث

        Returns:
            ProductOptionResponse: بيانات الخيار المحدث

        Raises:
            NotFoundError: إذا لم يتم العثور على الخيار
            ConflictError: إذا كان الاسم مكرراً
            ValidationError: إذا كانت البيانات غير صالحة
        """
        logger.info(
            "product_option_service_update",
            extra={
                "option_id": option_id,
                "fields": list(update_data.model_dump(exclude_unset=True).keys()),
            },
        )

        # التحقق من وجود الخيار
        existing = await self.repo.get_by_id(
            id=option_id,
        )

        if not existing:
            raise NotFoundError(
                message=f"خيار المنتج بـ ID '{option_id}' غير موجود",
            )

        # تحضير بيانات التحديث
        updates = update_data.model_dump(exclude_unset=True)

        # تنظيف الاسم إذا تم تغييره
        if "name" in updates:
            updates["name"] = sanitize_input(updates["name"])

            # التحقق من عدم وجود اسم مكرر
            duplicate = await self.repo.get_by_name(
                group_id=existing.group_id,
                name=updates["name"],
            )

            if duplicate and duplicate.id != option_id:
                raise ConflictError(
                    message=f"الخيار '{updates['name']}' موجود بالفعل في هذه المجموعة",
                )

        # التحقق من صحة السعر الإضافي
        if "extra_price" in updates:
            if updates["extra_price"] < 0:
                raise ValidationError(
                    message="السعر الإضافي لا يمكن أن يكون سالباً",
                )

            if updates["extra_price"] > MAX_EXTRA_PRICE:
                raise ValidationError(
                    message=f"السعر الإضافي يتجاوز الحد الأقصى المسموح به ({MAX_EXTRA_PRICE})",
                )

        # تحديث الخيار
        updated = await self.repo.update(
            id=option_id,
            data=updates,
        )

        if not updated:
            raise NotFoundError(
                message=f"خيار المنتج بـ ID '{option_id}' غير موجود",
            )

        logger.info(
            "product_option_updated_successfully",
            extra={
                "option_id": option_id,
                "updated_fields": list(updates.keys()),
            },
        )

        return ProductOptionResponse.model_validate(updated)

    # ==============================================
    # UPDATE AVAILABILITY
    # ==============================================

    async def update_availability(
        self,
        *,
        option_id: int,
        availability_data: ProductOptionAvailabilityUpdate,
    ) -> ProductOptionResponse:
        """
        تحديث حالة توفر الخيار.

        Args:
            option_id: معرف الخيار
            availability_data: بيانات حالة التوفر

        Returns:
            ProductOptionResponse: بيانات الخيار المحدث

        Raises:
            NotFoundError: إذا لم يتم العثور على الخيار
        """
        logger.info(
            "product_option_service_update_availability",
            extra={
                "option_id": option_id,
                "is_available": availability_data.is_available,
            },
        )

        option = await self.repo.update_availability(
            option_id=option_id,
            is_available=availability_data.is_available,
        )

        if not option:
            raise NotFoundError(
                message=f"خيار المنتج بـ ID '{option_id}' غير موجود",
            )

        logger.info(
            "product_option_availability_updated_successfully",
            extra={
                "option_id": option_id,
                "is_available": availability_data.is_available,
            },
        )

        return ProductOptionResponse.model_validate(option)

    # ==============================================
    # UPDATE PRICE
    # ==============================================

    async def update_price(
        self,
        *,
        option_id: int,
        extra_price: float,
    ) -> ProductOptionResponse:
        """
        تحديث السعر الإضافي للخيار.

        Args:
            option_id: معرف الخيار
            extra_price: السعر الإضافي الجديد

        Returns:
            ProductOptionResponse: بيانات الخيار المحدث

        Raises:
            NotFoundError: إذا لم يتم العثور على الخيار
            ValidationError: إذا كان السعر غير صالح
        """
        logger.info(
            "product_option_service_update_price",
            extra={
                "option_id": option_id,
                "extra_price": extra_price,
            },
        )

        if extra_price < 0:
            raise ValidationError(
                message="السعر الإضافي لا يمكن أن يكون سالباً",
            )

        if extra_price > MAX_EXTRA_PRICE:
            raise ValidationError(
                message=f"السعر الإضافي يتجاوز الحد الأقصى المسموح به ({MAX_EXTRA_PRICE})",
            )

        option = await self.repo.update_price(
            option_id=option_id,
            extra_price=extra_price,
        )

        if not option:
            raise NotFoundError(
                message=f"خيار المنتج بـ ID '{option_id}' غير موجود",
            )

        logger.info(
            "product_option_price_updated_successfully",
            extra={
                "option_id": option_id,
                "extra_price": extra_price,
            },
        )

        return ProductOptionResponse.model_validate(option)

    # ==============================================
    # UPDATE SORT ORDER
    # ==============================================

    async def update_sort_order(
        self,
        *,
        option_id: int,
        sort_order: int,
    ) -> ProductOptionResponse:
        """
        تحديث ترتيب الخيار.

        Args:
            option_id: معرف الخيار
            sort_order: الترتيب الجديد

        Returns:
            ProductOptionResponse: بيانات الخيار المحدث

        Raises:
            NotFoundError: إذا لم يتم العثور على الخيار
        """
        logger.info(
            "product_option_service_update_sort_order",
            extra={
                "option_id": option_id,
                "sort_order": sort_order,
            },
        )

        option = await self.repo.update_sort_order(
            option_id=option_id,
            sort_order=sort_order,
        )

        if not option:
            raise NotFoundError(
                message=f"خيار المنتج بـ ID '{option_id}' غير موجود",
            )

        logger.info(
            "product_option_sort_order_updated_successfully",
            extra={
                "option_id": option_id,
                "sort_order": sort_order,
            },
        )

        return ProductOptionResponse.model_validate(option)

    # ==============================================
    # ACTIVATE OPTION
    # ==============================================

    async def activate_option(
        self,
        *,
        option_id: int,
    ) -> ProductOptionResponse:
        """
        تفعيل الخيار.

        Args:
            option_id: معرف الخيار

        Returns:
            ProductOptionResponse: بيانات الخيار المحدث

        Raises:
            NotFoundError: إذا لم يتم العثور على الخيار
        """
        logger.info(
            "product_option_service_activate",
            extra={"option_id": option_id},
        )

        option = await self.repo.activate(
            option_id=option_id,
        )

        if not option:
            raise NotFoundError(
                message=f"خيار المنتج بـ ID '{option_id}' غير موجود",
            )

        logger.info(
            "product_option_activated_successfully",
            extra={"option_id": option_id},
        )

        return ProductOptionResponse.model_validate(option)

    # ==============================================
    # DEACTIVATE OPTION
    # ==============================================

    async def deactivate_option(
        self,
        *,
        option_id: int,
    ) -> ProductOptionResponse:
        """
        إلغاء تفعيل الخيار.

        Args:
            option_id: معرف الخيار

        Returns:
            ProductOptionResponse: بيانات الخيار المحدث

        Raises:
            NotFoundError: إذا لم يتم العثور على الخيار
        """
        logger.info(
            "product_option_service_deactivate",
            extra={"option_id": option_id},
        )

        option = await self.repo.deactivate(
            option_id=option_id,
        )

        if not option:
            raise NotFoundError(
                message=f"خيار المنتج بـ ID '{option_id}' غير موجود",
            )

        logger.info(
            "product_option_deactivated_successfully",
            extra={"option_id": option_id},
        )

        return ProductOptionResponse.model_validate(option)

    # ==============================================
    # DELETE OPTION
    # ==============================================

    async def delete_option(
        self,
        *,
        option_id: int,
    ) -> None:
        """
        حذف خيار منتج.

        Args:
            option_id: معرف الخيار

        Raises:
            NotFoundError: إذا لم يتم العثور على الخيار
        """
        logger.info(
            "product_option_service_delete",
            extra={"option_id": option_id},
        )

        # التحقق من وجود الخيار
        existing = await self.repo.get_by_id(
            id=option_id,
        )

        if not existing:
            raise NotFoundError(
                message=f"خيار المنتج بـ ID '{option_id}' غير موجود",
            )

        # حذف الخيار
        await self.repo.delete(id=option_id)

        logger.info(
            "product_option_deleted_successfully",
            extra={"option_id": option_id},
        )

    # ==============================================
    # DELETE BY GROUP
    # ==============================================

    async def delete_by_group(
        self,
        *,
        group_id: int,
    ) -> int:
        """
        حذف جميع خيارات مجموعة معينة.

        Args:
            group_id: معرف مجموعة الخيارات

        Returns:
            int: عدد الخيارات المحذوفة

        Raises:
            NotFoundError: إذا لم يتم العثور على المجموعة
        """
        logger.info(
            "product_option_service_delete_by_group",
            extra={"group_id": group_id},
        )

        # التحقق من وجود المجموعة
        group = await self.group_repo.get_by_id(
            id=group_id,
        )

        if not group:
            raise NotFoundError(
                message=f"مجموعة الخيارات بـ ID '{group_id}' غير موجودة",
            )

        # حذف الخيارات
        async with catalog_transaction(session=self.session):
            count = await self.repo.delete_by_group(group_id=group_id)

        logger.info(
            "product_options_deleted_by_group_successfully",
            extra={
                "group_id": group_id,
                "count": count,
            },
        )

        return count

    # ==============================================
    # REORDER OPTIONS
    # ==============================================

    async def reorder_options(
        self,
        *,
        group_id: int,
        option_order: list[int],
    ) -> None:
        """
        إعادة ترتيب خيارات المجموعة.

        Args:
            group_id: معرف مجموعة الخيارات
            option_order: قائمة معرفات الخيارات بالترتيب الجديد

        Raises:
            NotFoundError: إذا كان أحد الخيارات غير موجود
            ValidationError: إذا كانت القائمة فارغة أو تحتوي على معرفات مكررة
        """
        logger.info(
            "product_option_service_reorder",
            extra={
                "group_id": group_id,
                "option_count": len(option_order),
            },
        )

        if not option_order:
            raise ValidationError(
                message="قائمة ترتيب الخيارات لا يمكن أن تكون فارغة",
            )

        # التحقق من عدم وجود معرفات مكررة
        if len(option_order) != len(set(option_order)):
            raise ValidationError(
                message="قائمة ترتيب الخيارات تحتوي على معرفات مكررة",
            )

        # التحقق من وجود المجموعة
        group = await self.group_repo.get_by_id(
            id=group_id,
        )

        if not group:
            raise NotFoundError(
                message=f"مجموعة الخيارات بـ ID '{group_id}' غير موجودة",
            )

        # Validate every option before writing the first ordering change.
        for option_id in option_order:
            option = await self.repo.get_by_id(id=option_id)

            if not option:
                raise NotFoundError(
                    message=f"خيار المنتج بـ ID '{option_id}' غير موجود",
                )

            if option.group_id != group_id:
                raise ValidationError(
                    message=f"الخيار '{option_id}' لا ينتمي لهذه المجموعة",
                )

        async with catalog_transaction(session=self.session):
            for index, option_id in enumerate(option_order):
                await self.repo.update_sort_order(
                    option_id=option_id,
                    sort_order=index,
                )

        logger.info(
            "product_options_reordered_successfully",
            extra={
                "group_id": group_id,
                "option_count": len(option_order),
            },
        )


# ==============================================
