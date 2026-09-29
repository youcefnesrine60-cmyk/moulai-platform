# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📦 ORDER ITEMS SERVICE
# Business Logic Layer
# منطق الأعمال لعناصر الطلبات
#
# إنشاء عنصر طلب
# قراءة عنصر الطلب
# قراءة عناصر الطلب
# حساب عدد العناصر
# حساب المجموع الفرعي
# تغيير الكمية
# حذف عنصر
# حذف جميع العناصر
# ==============================================

from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from sqlalchemy.ext.asyncio import AsyncSession

# ✅ استيراد الاستثناءات
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)

# ✅ استيراد دوال الأمان
from app.core.security import (
    sanitize_input,
)

from app.core.logger import logger
from app.models.order_item import OrderItem
from app.repositories.order_items_repo import OrderItemsRepository

# ✅ استيراد المخططات
from app.schemas.order_item import (
    OrderItemCreate,
    OrderItemResponse,
    OrderItemWithOptionsResponse,
    OrderItemSummary,
)


# ==============================================
# 🧩 CONSTANTS
# ==============================================

MAX_ITEMS_PER_ORDER = 50
MAX_QUANTITY_PER_ITEM = 100
MIN_QUANTITY_PER_ITEM = 1


# ==============================================
# 🧩 TYPES
# ==============================================

OrderItemData = Dict[str, Any]
OrderItemList = List[OrderItem]


# ==============================================
# 📦 ORDER ITEMS SERVICE
# ==============================================


class OrderItemsService:
    """
    خدمة عناصر الطلبات - تدير منطق الأعمال لعناصر الطلبات.
    
    مسؤولة عن:
        - إضافة عناصر إلى الطلب
        - تحديث كمية العناصر
        - حذف عناصر من الطلب
        - حساب المجموع الفرعي
    
    Attributes:
        session: جلسة قاعدة البيانات غير المتزامنة
        repo: مستودع عناصر الطلبات
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة خدمة عناصر الطلبات.
        
        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        self.session = session
        self.repo = OrderItemsRepository(session)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET BY ID
    # ==============================================

    async def get_by_id(
        self,
        *,
        order_item_id: int,
    ) -> OrderItemResponse:
        """
        الحصول على عنصر طلب بالمعرف.
        
        Args:
            order_item_id: معرف عنصر الطلب
            
        Returns:
            OrderItemResponse: بيانات عنصر الطلب
            
        Raises:
            NotFoundError: إذا لم يتم العثور على العنصر
        """
        logger.info(
            "order_items_service_get_by_id",
            extra={"order_item_id": order_item_id},
        )

        item = await self.repo.get_by_id(
            id=order_item_id,
        )

        if not item:
            raise NotFoundError(
                message=f"عنصر الطلب بـ ID '{order_item_id}' غير موجود",
            )

        return OrderItemResponse.model_validate(item)

    # ==============================================
    # GET BY ORDER
    # ==============================================

    async def get_by_order(
        self,
        *,
        order_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[OrderItemResponse]:
        """
        الحصول على عناصر طلب معين.
        
        Args:
            order_id: معرف الطلب
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            List[OrderItemResponse]: قائمة عناصر الطلب
        """
        logger.info(
            "order_items_service_get_by_order",
            extra={
                "order_id": order_id,
                "skip": skip,
                "limit": limit,
            },
        )

        items = await self.repo.get_by_order_id(
            order_id=order_id,
            skip=skip,
            limit=limit,
        )

        return [OrderItemResponse.model_validate(item) for item in items]

    # ==============================================
    # GET WITH OPTIONS
    # ==============================================

    async def get_with_options(
        self,
        *,
        order_item_id: int,
    ) -> OrderItemWithOptionsResponse:
        """
        الحصول على عنصر طلب مع خياراته.
        
        Args:
            order_item_id: معرف عنصر الطلب
            
        Returns:
            OrderItemWithOptionsResponse: عنصر الطلب مع الخيارات
            
        Raises:
            NotFoundError: إذا لم يتم العثور على العنصر
        """
        logger.info(
            "order_items_service_get_with_options",
            extra={"order_item_id": order_item_id},
        )

        item = await self.repo.get_with_options(
            order_item_id=order_item_id,
        )

        if not item:
            raise NotFoundError(
                message=f"عنصر الطلب بـ ID '{order_item_id}' غير موجود",
            )

        return OrderItemWithOptionsResponse.model_validate(item)

    # ==============================================
    # COUNT BY ORDER
    # ==============================================

    async def count_by_order(
        self,
        *,
        order_id: int,
    ) -> int:
        """
        حساب عدد عناصر طلب معين.
        
        Args:
            order_id: معرف الطلب
            
        Returns:
            int: عدد العناصر
        """
        logger.info(
            "order_items_service_count_by_order",
            extra={"order_id": order_id},
        )

        return await self.repo.count_by_order(
            order_id=order_id,
        )

    # ==============================================
    # GET SUBTOTAL
    # ==============================================

    async def get_subtotal(
        self,
        *,
        order_id: int,
    ) -> float:
        """
        حساب المجموع الفرعي لعناصر طلب معين.
        
        Args:
            order_id: معرف الطلب
            
        Returns:
            float: المجموع الفرعي
        """
        logger.info(
            "order_items_service_get_subtotal",
            extra={"order_id": order_id},
        )

        return await self.repo.get_subtotal(
            order_id=order_id,
        )

    # ==============================================
    # GET ITEM SUMMARY
    # ==============================================

    async def get_item_summary(
        self,
        *,
        order_id: int,
    ) -> OrderItemSummary:
        """
        الحصول على ملخص عناصر الطلب.
        
        Args:
            order_id: معرف الطلب
            
        Returns:
            OrderItemSummary: ملخص عناصر الطلب
        """
        logger.info(
            "order_items_service_get_item_summary",
            extra={"order_id": order_id},
        )

        total_items = await self.count_by_order(
            order_id=order_id,
        )

        subtotal = await self.get_subtotal(
            order_id=order_id,
        )

        # الحصول على العناصر
        items = await self.repo.get_by_order_id(
            order_id=order_id,
            limit=1000,
        )

        # تجميع العناصر حسب المنتج
        product_counts: Dict[str, int] = {}

        for item in items:
            if item.product_name not in product_counts:
                product_counts[item.product_name] = 0
            product_counts[item.product_name] += item.quantity

        return OrderItemSummary(
            total_items=total_items,
            subtotal=subtotal,
            product_counts=product_counts,
        )

    # ==========================================
    # ✏️ MUTATIONS
    # ==========================================

    # ==============================================
    # ADD ITEM
    # ==============================================

    async def add_item(
        self,
        *,
        item_data: OrderItemCreate,
    ) -> OrderItemResponse:
        """
        إضافة عنصر جديد إلى الطلب.
        
        Args:
            item_data: بيانات عنصر الطلب
            
        Returns:
            OrderItemResponse: بيانات عنصر الطلب المنشأ
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الطلب أو المنتج
            ConflictError: إذا كان المنتج مكرراً في الطلب
            ValidationError: إذا كانت البيانات غير صالحة
        """
        logger.info(
            "order_items_service_add_item",
            extra={
                "order_id": item_data.order_id,
                "product_id": item_data.product_id,
                "quantity": item_data.quantity,
            },
        )

        # التحقق من صحة البيانات
        if item_data.quantity < MIN_QUANTITY_PER_ITEM:
            raise ValidationError(
                message=f"الكمية يجب أن تكون على الأقل {MIN_QUANTITY_PER_ITEM}",
            )

        if item_data.quantity > MAX_QUANTITY_PER_ITEM:
            raise ValidationError(
                message=f"الكمية تتجاوز الحد الأقصى المسموح به ({MAX_QUANTITY_PER_ITEM})",
            )

        if item_data.unit_price < 0:
            raise ValidationError(
                message="سعر الوحدة لا يمكن أن يكون سالباً",
            )

        # التحقق من عدد العناصر في الطلب
        current_count = await self.count_by_order(
            order_id=item_data.order_id,
        )

        if current_count >= MAX_ITEMS_PER_ORDER:
            raise ValidationError(
                message=f"تجاوزت الحد الأقصى لعناصر الطلب ({MAX_ITEMS_PER_ORDER})",
                details={
                    "order_id": item_data.order_id,
                    "current_count": current_count,
                    "max_allowed": MAX_ITEMS_PER_ORDER,
                },
            )

        # التحقق من عدم وجود منتج مكرر في الطلب
        existing = await self.repo.get_by_product_and_order(
            order_id=item_data.order_id,
            product_id=item_data.product_id,
        )

        if existing:
            raise ConflictError(
                message=f"المنتج '{item_data.product_name}' موجود بالفعل في الطلب",
                details={
                    "order_id": item_data.order_id,
                    "product_id": item_data.product_id,
                    "existing_item_id": existing.id,
                },
            )

        # حساب السعر الإجمالي
        total_price = item_data.unit_price * item_data.quantity

        # إنشاء عنصر الطلب
        data: OrderItemData = {
            "order_id": item_data.order_id,
            "product_id": item_data.product_id,
            "product_name": sanitize_input(item_data.product_name),
            "unit_price": item_data.unit_price,
            "quantity": item_data.quantity,
            "total_price": total_price,
        }

        item = await self.repo.create(data=data)

        logger.info(
            "order_item_added_successfully",
            extra={
                "order_item_id": item.id,
                "order_id": item_data.order_id,
            },
        )

        return OrderItemResponse.model_validate(item)

    # ==============================================
    # UPDATE QUANTITY
    # ==============================================

    async def update_quantity(
        self,
        *,
        order_item_id: int,
        quantity: int,
    ) -> OrderItemResponse:
        """
        تحديث كمية عنصر الطلب.
        
        Args:
            order_item_id: معرف عنصر الطلب
            quantity: الكمية الجديدة
            
        Returns:
            OrderItemResponse: بيانات عنصر الطلب المحدث
            
        Raises:
            NotFoundError: إذا لم يتم العثور على العنصر
            ValidationError: إذا كانت الكمية غير صالحة
        """
        logger.info(
            "order_items_service_update_quantity",
            extra={
                "order_item_id": order_item_id,
                "quantity": quantity,
            },
        )

        # التحقق من صحة الكمية
        if quantity < MIN_QUANTITY_PER_ITEM:
            raise ValidationError(
                message=f"الكمية يجب أن تكون على الأقل {MIN_QUANTITY_PER_ITEM}",
            )

        if quantity > MAX_QUANTITY_PER_ITEM:
            raise ValidationError(
                message=f"الكمية تتجاوز الحد الأقصى المسموح به ({MAX_QUANTITY_PER_ITEM})",
            )

        # الحصول على العنصر الحالي
        item = await self.repo.get_by_id(id=order_item_id)

        if not item:
            raise NotFoundError(
                message=f"عنصر الطلب بـ ID '{order_item_id}' غير موجود",
            )

        # حساب السعر الإجمالي الجديد
        unit_price = item.unit_price
        total_price = unit_price * quantity

        # تحديث الكمية
        updated = await self.repo.update_quantity(
            order_item_id=order_item_id,
            quantity=quantity,
            total_price=total_price,
        )

        if not updated:
            raise NotFoundError(
                message=f"عنصر الطلب بـ ID '{order_item_id}' غير موجود",
            )

        logger.info(
            "order_item_quantity_updated_successfully",
            extra={
                "order_item_id": order_item_id,
                "quantity": quantity,
                "total_price": total_price,
            },
        )

        return OrderItemResponse.model_validate(updated)

    # ==============================================
    # UPDATE UNIT PRICE
    # ==============================================

    async def update_unit_price(
        self,
        *,
        order_item_id: int,
        unit_price: float,
    ) -> OrderItemResponse:
        """
        تحديث سعر الوحدة لعنصر الطلب.
        
        Args:
            order_item_id: معرف عنصر الطلب
            unit_price: سعر الوحدة الجديد
            
        Returns:
            OrderItemResponse: بيانات عنصر الطلب المحدث
            
        Raises:
            NotFoundError: إذا لم يتم العثور على العنصر
            ValidationError: إذا كان السعر غير صالح
        """
        logger.info(
            "order_items_service_update_unit_price",
            extra={
                "order_item_id": order_item_id,
                "unit_price": unit_price,
            },
        )

        if unit_price < 0:
            raise ValidationError(
                message="سعر الوحدة لا يمكن أن يكون سالباً",
            )

        item = await self.repo.get_by_id(id=order_item_id)

        if not item:
            raise NotFoundError(
                message=f"عنصر الطلب بـ ID '{order_item_id}' غير موجود",
            )

        # حساب السعر الإجمالي الجديد
        total_price = unit_price * item.quantity

        updated = await self.repo.update(
            id=order_item_id,
            data={
                "unit_price": unit_price,
                "total_price": total_price,
            },
        )

        if not updated:
            raise NotFoundError(
                message=f"عنصر الطلب بـ ID '{order_item_id}' غير موجود",
            )

        logger.info(
            "order_item_unit_price_updated_successfully",
            extra={
                "order_item_id": order_item_id,
                "unit_price": unit_price,
                "total_price": total_price,
            },
        )

        return OrderItemResponse.model_validate(updated)

    # ==============================================
    # REMOVE ITEM
    # ==============================================

    async def remove_item(
        self,
        *,
        order_item_id: int,
    ) -> None:
        """
        حذف عنصر من الطلب.
        
        Args:
            order_item_id: معرف عنصر الطلب
            
        Raises:
            NotFoundError: إذا لم يتم العثور على العنصر
        """
        logger.info(
            "order_items_service_remove_item",
            extra={"order_item_id": order_item_id},
        )

        item = await self.repo.get_by_id(id=order_item_id)

        if not item:
            raise NotFoundError(
                message=f"عنصر الطلب بـ ID '{order_item_id}' غير موجود",
            )

        await self.repo.delete(id=order_item_id)

        logger.info(
            "order_item_removed_successfully",
            extra={"order_item_id": order_item_id},
        )

    # ==============================================
    # REMOVE ALL ITEMS
    # ==============================================

    async def remove_all_items(
        self,
        *,
        order_id: int,
    ) -> int:
        """
        حذف جميع عناصر الطلب.
        
        Args:
            order_id: معرف الطلب
            
        Returns:
            int: عدد العناصر المحذوفة
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الطلب
        """
        logger.info(
            "order_items_service_remove_all_items",
            extra={"order_id": order_id},
        )

        # التحقق من وجود عناصر
        count = await self.count_by_order(
            order_id=order_id,
        )

        if count == 0:
            logger.info(
                "no_items_to_remove",
                extra={"order_id": order_id},
            )
            return 0

        # حذف جميع العناصر
        deleted_count = await self.repo.delete_by_order(
            order_id=order_id,
        )

        logger.info(
            "all_order_items_removed_successfully",
            extra={
                "order_id": order_id,
                "count": deleted_count,
            },
        )

        return deleted_count
