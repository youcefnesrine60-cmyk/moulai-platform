# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / SERVICES / BUSINESS / ORDER ITEM OPTIONS SERVICE
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for order item options service.

Part of MoulAI Platform - Agent-as-a-Service.
"""

# ==============================================
# 🎛 ORDER ITEM OPTIONS SERVICE
# Business Logic Layer
# منطق الأعمال لخيارات عناصر الطلبات
#
# إضافة خيار
# قراءة الخيار
# قراءة خيارات عنصر الطلب
# حساب السعر الإضافي الإجمالي
# حساب عدد الخيارات
# حذف خيار
# حذف جميع الخيارات
# ==============================================
from typing import (
    Any,
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
from app.core.security import (
    sanitize_input,
)
from app.models.order_item import OrderItemOption
from app.repositories.order_item_options_repo import OrderItemOptionsRepository

# ✅ استيراد المخططات
from app.schemas.order_item import (
    OrderItemOptionCreate,
    OrderItemOptionResponse,
    OrderItemOptionSummary,
)
from app.services.business.orders.transaction import transactional_order

# ==============================================
# 🧩 CONSTANTS
# ==============================================

MAX_OPTIONS_PER_ORDER_ITEM = 20
MAX_ADDITIONAL_PRICE = 1000000.0  # 1,000,000 DZD


# ==============================================
# 🧩 TYPES
# ==============================================

OrderItemOptionData = dict[str, Any]
OrderItemOptionList = list[OrderItemOption]


# ==============================================
# 🎛 ORDER ITEM OPTIONS SERVICE
# ==============================================


class OrderItemOptionsService:
    """
    خدمة خيارات عناصر الطلبات - تدير منطق الأعمال لخيارات عناصر الطلبات.

    مسؤولة عن:
        - إضافة خيارات إلى عناصر الطلب
        - تحديث سعر الخيارات
        - حذف خيارات من عناصر الطلب
        - حساب السعر الإضافي الإجمالي

    Attributes:
        session: جلسة قاعدة البيانات غير المتزامنة
        repo: مستودع خيارات عناصر الطلبات
    """

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة خدمة خيارات عناصر الطلبات.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        self.session = session
        self.repo = OrderItemOptionsRepository(session)

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
    ) -> OrderItemOptionResponse:
        """
        الحصول على خيار بالمعرف.

        Args:
            option_id: معرف الخيار

        Returns:
            OrderItemOptionResponse: بيانات الخيار

        Raises:
            NotFoundError: إذا لم يتم العثور على الخيار
        """
        logger.info(
            "order_item_options_service_get_by_id",
            extra={"option_id": option_id},
        )

        option = await self.repo.get_by_id(
            id=option_id,
        )

        if not option:
            raise NotFoundError(
                message=f"الخيار بـ ID '{option_id}' غير موجود",
            )

        return OrderItemOptionResponse.model_validate(option)

    # ==============================================
    # GET BY ORDER ITEM
    # ==============================================

    async def get_by_order_item(
        self,
        *,
        order_item_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[OrderItemOptionResponse]:
        """
        الحصول على خيارات عنصر طلب معين.

        Args:
            order_item_id: معرف عنصر الطلب
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            List[OrderItemOptionResponse]: قائمة خيارات عنصر الطلب
        """
        logger.info(
            "order_item_options_service_get_by_order_item",
            extra={
                "order_item_id": order_item_id,
                "skip": skip,
                "limit": limit,
            },
        )

        options = await self.repo.get_by_order_item_id(
            order_item_id=order_item_id,
            skip=skip,
            limit=limit,
        )

        return [OrderItemOptionResponse.model_validate(option) for option in options]

    # ==============================================
    # COUNT BY ORDER ITEM
    # ==============================================

    async def count_by_order_item(
        self,
        *,
        order_item_id: int,
    ) -> int:
        """
        حساب عدد خيارات عنصر طلب معين.

        Args:
            order_item_id: معرف عنصر الطلب

        Returns:
            int: عدد الخيارات
        """
        logger.info(
            "order_item_options_service_count_by_order_item",
            extra={"order_item_id": order_item_id},
        )

        return await self.repo.count_by_order_item(
            order_item_id=order_item_id,
        )

    # ==============================================
    # GET TOTAL ADDITIONAL PRICE
    # ==============================================

    async def get_total_additional_price(
        self,
        *,
        order_item_id: int,
    ) -> float:
        """
        حساب السعر الإضافي الإجمالي لخيارات عنصر طلب معين.

        Args:
            order_item_id: معرف عنصر الطلب

        Returns:
            float: السعر الإضافي الإجمالي
        """
        logger.info(
            "order_item_options_service_get_total_additional_price",
            extra={"order_item_id": order_item_id},
        )

        return await self.repo.get_total_additional_price(
            order_item_id=order_item_id,
        )

    # ==============================================
    # GET OPTION SUMMARY
    # ==============================================

    async def get_option_summary(
        self,
        *,
        order_item_id: int,
    ) -> OrderItemOptionSummary:
        """
        الحصول على ملخص خيارات عنصر الطلب.

        Args:
            order_item_id: معرف عنصر الطلب

        Returns:
            OrderItemOptionSummary: ملخص الخيارات
        """
        logger.info(
            "order_item_options_service_get_option_summary",
            extra={"order_item_id": order_item_id},
        )

        total = await self.count_by_order_item(
            order_item_id=order_item_id,
        )

        total_price = await self.get_total_additional_price(
            order_item_id=order_item_id,
        )

        # الحصول على الخيارات
        options = await self.repo.get_by_order_item_id(
            order_item_id=order_item_id,
            limit=1000,
        )

        # تجميع الخيارات حسب مجموعة الخيارات
        groups: dict[str, list[str]] = {}

        for option in options:
            if option.option_group_name not in groups:
                groups[option.option_group_name] = []
            groups[option.option_group_name].append(option.option_name)

        return OrderItemOptionSummary(
            total_options=total,
            total_additional_price=total_price,
            groups=groups,
        )

    # ==========================================
    # ✏️ MUTATIONS
    # ==========================================

    # ==============================================
    # ADD OPTION
    # ==============================================

    @transactional_order
    async def add_option(
        self,
        *,
        option_data: OrderItemOptionCreate,
    ) -> OrderItemOptionResponse:
        """
        إضافة خيار جديد إلى عنصر الطلب.

        Args:
            option_data: بيانات الخيار

        Returns:
            OrderItemOptionResponse: بيانات الخيار المنشأ

        Raises:
            NotFoundError: إذا لم يتم العثور على عنصر الطلب
            ConflictError: إذا كان الخيار مكرراً
            ValidationError: إذا كانت البيانات غير صالحة
        """
        # تنظيف البيانات
        option_group_name = sanitize_input(option_data.option_group_name)
        option_name = sanitize_input(option_data.option_name)

        logger.info(
            "order_item_options_service_add_option",
            extra={
                "order_item_id": option_data.order_item_id,
                "option_group_name": option_group_name,
                "option_name": option_name,
                "additional_price": option_data.additional_price,
            },
        )

        # التحقق من صحة البيانات
        if not option_group_name:
            raise ValidationError(
                message="اسم مجموعة الخيارات مطلوب",
            )

        if not option_name:
            raise ValidationError(
                message="اسم الخيار مطلوب",
            )

        if option_data.additional_price < 0:
            raise ValidationError(
                message="السعر الإضافي لا يمكن أن يكون سالباً",
            )

        if option_data.additional_price > MAX_ADDITIONAL_PRICE:
            raise ValidationError(
                message=f"السعر الإضافي يتجاوز الحد الأقصى المسموح به ({MAX_ADDITIONAL_PRICE})",
            )

        # التحقق من الحد الأقصى للخيارات
        current_count = await self.count_by_order_item(
            order_item_id=option_data.order_item_id,
        )

        if current_count >= MAX_OPTIONS_PER_ORDER_ITEM:
            raise ValidationError(
                message=f"تجاوزت الحد الأقصى للخيارات ({MAX_OPTIONS_PER_ORDER_ITEM})",
                details={
                    "order_item_id": option_data.order_item_id,
                    "current_count": current_count,
                    "max_allowed": MAX_OPTIONS_PER_ORDER_ITEM,
                },
            )

        # التحقق من عدم وجود خيار مكرر
        existing = await self.repo.get_by_name(
            order_item_id=option_data.order_item_id,
            option_group_name=option_group_name,
            option_name=option_name,
        )

        if existing:
            raise ConflictError(
                message=f"الخيار '{option_name}' موجود بالفعل في مجموعة '{option_group_name}'",
            )

        # إنشاء الخيار
        data: OrderItemOptionData = {
            "order_item_id": option_data.order_item_id,
            "option_group_name": option_group_name,
            "option_name": option_name,
            "additional_price": option_data.additional_price,
        }

        option = await self.repo.create(data=data)

        logger.info(
            "order_item_option_added_successfully",
            extra={
                "option_id": option.id,
                "order_item_id": option_data.order_item_id,
            },
        )

        return OrderItemOptionResponse.model_validate(option)

    # ==============================================
    # REMOVE OPTION
    # ==============================================

    @transactional_order
    async def remove_option(
        self,
        *,
        option_id: int,
    ) -> None:
        """
        حذف خيار من عنصر الطلب.

        Args:
            option_id: معرف الخيار

        Raises:
            NotFoundError: إذا لم يتم العثور على الخيار
        """
        logger.info(
            "order_item_options_service_remove_option",
            extra={"option_id": option_id},
        )

        option = await self.repo.get_by_id(id=option_id)

        if not option:
            raise NotFoundError(
                message=f"الخيار بـ ID '{option_id}' غير موجود",
            )

        await self.repo.delete(id=option_id)

        logger.info(
            "order_item_option_removed_successfully",
            extra={"option_id": option_id},
        )

    # ==============================================
    # REMOVE ALL OPTIONS
    # ==============================================

    @transactional_order
    async def remove_all_options(
        self,
        *,
        order_item_id: int,
    ) -> int:
        """
        حذف جميع خيارات عنصر الطلب.

        Args:
            order_item_id: معرف عنصر الطلب

        Returns:
            int: عدد الخيارات المحذوفة

        Raises:
            NotFoundError: إذا لم يتم العثور على عنصر الطلب
        """
        logger.info(
            "order_item_options_service_remove_all_options",
            extra={"order_item_id": order_item_id},
        )

        # التحقق من وجود خيارات
        count = await self.count_by_order_item(
            order_item_id=order_item_id,
        )

        if count == 0:
            logger.info(
                "no_options_to_remove",
                extra={"order_item_id": order_item_id},
            )
            return 0

        # حذف جميع الخيارات
        deleted_count = await self.repo.delete_by_order_item(
            order_item_id=order_item_id,
        )

        logger.info(
            "all_order_item_options_removed_successfully",
            extra={
                "order_item_id": order_item_id,
                "count": deleted_count,
            },
        )

        return deleted_count

    # ==============================================
    # UPDATE OPTION PRICE
    # ==============================================

    @transactional_order
    async def update_option_price(
        self,
        *,
        option_id: int,
        additional_price: float,
    ) -> OrderItemOptionResponse:
        """
        تحديث السعر الإضافي للخيار.

        Args:
            option_id: معرف الخيار
            additional_price: السعر الإضافي الجديد

        Returns:
            OrderItemOptionResponse: بيانات الخيار المحدث

        Raises:
            NotFoundError: إذا لم يتم العثور على الخيار
            ValidationError: إذا كان السعر غير صالح
        """
        logger.info(
            "order_item_options_service_update_option_price",
            extra={
                "option_id": option_id,
                "additional_price": additional_price,
            },
        )

        if additional_price < 0:
            raise ValidationError(
                message="السعر الإضافي لا يمكن أن يكون سالباً",
            )

        if additional_price > MAX_ADDITIONAL_PRICE:
            raise ValidationError(
                message=f"السعر الإضافي يتجاوز الحد الأقصى المسموح به ({MAX_ADDITIONAL_PRICE})",
            )

        option = await self.repo.get_by_id(id=option_id)

        if not option:
            raise NotFoundError(
                message=f"الخيار بـ ID '{option_id}' غير موجود",
            )

        updated = await self.repo.update(
            id=option_id,
            data={"additional_price": additional_price},
        )

        if not updated:
            raise NotFoundError(
                message=f"الخيار بـ ID '{option_id}' غير موجود",
            )

        logger.info(
            "order_item_option_price_updated_successfully",
            extra={
                "option_id": option_id,
                "additional_price": additional_price,
            },
        )

        return OrderItemOptionResponse.model_validate(updated)

    # ==============================================
    # UPDATE OPTION NAME
    # ==============================================

    @transactional_order
    async def update_option_name(
        self,
        *,
        option_id: int,
        option_name: str,
    ) -> OrderItemOptionResponse:
        """
        تحديث اسم الخيار.

        Args:
            option_id: معرف الخيار
            option_name: اسم الخيار الجديد

        Returns:
            OrderItemOptionResponse: بيانات الخيار المحدث

        Raises:
            NotFoundError: إذا لم يتم العثور على الخيار
            ConflictError: إذا كان الاسم مكرراً
            ValidationError: إذا كان الاسم غير صالح
        """
        # تنظيف الاسم
        clean_name = sanitize_input(option_name)

        logger.info(
            "order_item_options_service_update_option_name",
            extra={
                "option_id": option_id,
                "option_name": clean_name,
            },
        )

        if not clean_name:
            raise ValidationError(
                message="اسم الخيار مطلوب",
            )

        option = await self.repo.get_by_id(id=option_id)

        if not option:
            raise NotFoundError(
                message=f"الخيار بـ ID '{option_id}' غير موجود",
            )

        # التحقق من عدم وجود اسم مكرر
        existing = await self.repo.get_by_name(
            order_item_id=option.order_item_id,
            option_group_name=option.option_group_name,
            option_name=clean_name,
        )

        if existing and existing.id != option_id:
            raise ConflictError(
                message=f"الخيار '{clean_name}' موجود بالفعل في هذه المجموعة",
            )

        updated = await self.repo.update(
            id=option_id,
            data={"option_name": clean_name},
        )

        if not updated:
            raise NotFoundError(
                message=f"الخيار بـ ID '{option_id}' غير موجود",
            )

        logger.info(
            "order_item_option_name_updated_successfully",
            extra={
                "option_id": option_id,
                "option_name": clean_name,
            },
        )

        return OrderItemOptionResponse.model_validate(updated)


# ==============================================
