# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / SERVICES / BUSINESS / ORDER ITEMS SERVICE
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for order items service.

Part of MoulAI Platform - Agent-as-a-Service.
"""

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
)

from sqlalchemy.ext.asyncio import AsyncSession

# ✅ استيراد الاستثناءات
from app.core.exceptions import (
    NotFoundError,
    ValidationError,
)

# ✅ استيراد دوال الأمان
from app.core.logger import logger
from app.models.order_item import OrderItem
from app.repositories.order_items_repo import OrderItemsRepository
from app.repositories.orders_repo import lock_order

# ✅ استيراد المخططات
from app.schemas.order_item import (
    OrderItemCreate,
    OrderItemListResponse,
    OrderItemResponse,
    OrderItemSummary,
    OrderItemWithOptionsResponse,
)
from app.services.business.orders.helpers import check_order_editable
from app.services.business.orders.items import (
    _recalculate_order_total,
    add_item_to_order,
    remove_item_from_order,
)
from app.services.business.orders.pricing import item_total
from app.services.business.orders.transaction import transactional_order

# ==============================================
# 🧩 CONSTANTS
# ==============================================

MAX_ITEMS_PER_ORDER = 50


# ==============================================
# 🧩 TYPES
# ==============================================

OrderItemData = dict[str, Any]
OrderItemList = list[OrderItem]


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

    # ==============================================
    #   INIT
    # ==============================================

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
    ) -> list[OrderItemResponse]:
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
        product_counts: dict[str, int] = {}

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

    @transactional_order
    async def add_items(self, *, items):
        if not items or len({item.order_id for item in items}) != 1:
            raise ValidationError(message="Items must belong to one order")
        created = [await self.add_item(item_data=item) for item in items]
        return OrderItemListResponse(
            items=created, total=len(created), skip=0, limit=len(created)
        )

    # ==============================================
    # ADD ITEM
    # ==============================================

    @transactional_order
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
        values = item_data.model_dump()
        item = await add_item_to_order(**values, session=self.session)
        return OrderItemResponse.model_validate(item)

    # ==============================================
    # CHANGE ITEM AMOUNTS
    # ==============================================

    async def _change_item_amounts(
        self,
        *,
        order_item_id: int,
        quantity: int | None = None,
        unit_price: float | None = None,
    ) -> OrderItem:
        """Update editable item amounts while preserving order-total consistency.

        The public callers own the transaction. This helper locks the parent order,
        updates the item, and recalculates the aggregate total in that same session.
        """
        item = await self.repo.get_by_id(id=order_item_id)
        if item is None:
            raise NotFoundError(message="Order item not found")

        order = await lock_order(order_id=item.order_id, session=self.session)
        if order is None:
            raise NotFoundError(message="Order not found")

        check_order_editable(order)
        new_quantity = item.quantity if quantity is None else quantity
        new_unit_price = item.unit_price if unit_price is None else unit_price
        updated = await self.repo.update(
            id=item.id,
            data={
                "quantity": new_quantity,
                "unit_price": new_unit_price,
                "total_price": item_total(new_unit_price, new_quantity),
            },
        )
        await _recalculate_order_total(order_id=order.id, session=self.session)
        return updated

    # ==============================================
    # UPDATE QUANTITY
    # ==============================================

    @transactional_order
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
        item = await self._change_item_amounts(
            order_item_id=order_item_id,
            quantity=quantity,
        )
        return OrderItemResponse.model_validate(item)

    # ==============================================
    # UPDATE UNIT PRICE
    # ==============================================

    @transactional_order
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
        item = await self._change_item_amounts(
            order_item_id=order_item_id,
            unit_price=unit_price,
        )
        return OrderItemResponse.model_validate(item)

    # ==============================================
    # REMOVE ITEM
    # ==============================================

    @transactional_order
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
        item = await self.repo.get_by_id(id=order_item_id)
        if item is None:
            raise NotFoundError(message="Order item not found")
        await remove_item_from_order(
            order_id=item.order_id, order_item_id=order_item_id, session=self.session
        )

    # ==============================================
    # REMOVE ALL ITEMS
    # ==============================================

    @transactional_order
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
        order = await lock_order(order_id=order_id, session=self.session)
        if order is None:
            raise NotFoundError(message="Order not found")
        check_order_editable(order)

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

        await _recalculate_order_total(order_id=order_id, session=self.session)
        return deleted_count
