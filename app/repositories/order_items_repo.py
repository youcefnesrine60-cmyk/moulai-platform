# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / REPOSITORIES / ORDER ITEMS REPO
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for order items repo.

Part of MoulAI Platform - Agent-as-a-Service.
"""

# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================
# ==============================================
# 📦 ORDER ITEMS REPOSITORY
# عمليات قاعدة البيانات لعناصر الطلبات باستخدام SQLAlchemy
# ==============================================
from typing import (
    Any,
)

from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload, selectinload

from app.core.logger import logger
from app.models.order_item import OrderItem
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

OrderItemData = dict[str, Any]
OrderItemUpdateData = dict[str, Any]
OrderItemList = list[OrderItem]

# ==============================================
# 📦 ORDER ITEMS REPOSITORY
# ==============================================


class OrderItemsRepository(
    BaseRepository[OrderItem, OrderItemData, OrderItemUpdateData]
):
    """
    مستودع عناصر الطلبات - يوفر عمليات خاصة بعناصر الطلبات.

    مسؤول عن:
        - عمليات CRUD الأساسية لعناصر الطلبات
        - حساب المجموع الفرعي للطلب
        - حذف عناصر الطلب

    Attributes:
        model: نموذج OrderItem
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
        تهيئة مستودع عناصر الطلبات.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(OrderItem, session)
        self.commit_on_write = False
        self.query_options = [
            raiseload("*"),
            selectinload(OrderItem.options).raiseload("*"),
        ]

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET BY ORDER ID
    # ==============================================

    async def get_with_options(self, *, order_item_id):
        return await self.get_by_id(id=order_item_id)

    # ==============================================
    # GET BY PRODUCT AND ORDER
    # ==============================================

    async def get_by_product_and_order(self, *, order_id, product_id):
        return (
            await self.session.execute(
                self._select()
                .where(
                    self.model.order_id == order_id, self.model.product_id == product_id
                )
                .limit(1)
            )
        ).scalar_one_or_none()

    # ==============================================
    # GET BY ORDER ID
    # ==============================================

    async def get_by_order_id(
        self,
        *,
        order_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> OrderItemList:
        """
        الحصول على عناصر طلب معين.

        Args:
            order_id: معرف الطلب
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة عناصر الطلب
        """
        try:
            query = (
                self._select()
                .where(self.model.order_id == order_id)
                .order_by(self.model.id.asc())
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "order_items_repo_get_by_order_failed",
                extra={
                    "order_id": order_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET BY PRODUCT ID
    # ==============================================

    async def get_by_product_id(
        self,
        *,
        product_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> OrderItemList:
        """
        الحصول على عناصر الطلبات لمنتج معين.

        Args:
            product_id: معرف المنتج
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة عناصر الطلبات
        """
        try:
            query = (
                self._select()
                .where(self.model.product_id == product_id)
                .order_by(self.model.created_at.desc())
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "order_items_repo_get_by_product_failed",
                extra={
                    "product_id": product_id,
                    "error": str(e),
                },
            )
            raise

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
            عدد العناصر
        """
        try:
            result = await self.session.execute(
                select(func.count())
                .select_from(self.model)
                .where(self.model.order_id == order_id),
            )

            return result.scalar_one()

        except Exception as e:
            logger.exception(
                "order_items_repo_count_by_order_failed",
                extra={
                    "order_id": order_id,
                    "error": str(e),
                },
            )
            raise

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
            المجموع الفرعي
        """
        try:
            result = await self.session.execute(
                select(func.coalesce(func.sum(self.model.total_price), 0)).where(
                    self.model.order_id == order_id
                ),
            )

            return float(result.scalar_one())

        except Exception as e:
            logger.exception(
                "order_items_repo_get_subtotal_failed",
                extra={
                    "order_id": order_id,
                    "error": str(e),
                },
            )
            raise

    # ==========================================
    # ✏️ UPDATES
    # ==========================================

    # ==============================================
    # UPDATE QUANTITY
    # ==============================================

    async def update_quantity(
        self,
        *,
        order_item_id: int,
        quantity: int,
        total_price: float,
    ) -> OrderItem | None:
        """
        تحديث كمية عنصر الطلب.

        Args:
            order_item_id: معرف عنصر الطلب
            quantity: الكمية الجديدة
            total_price: السعر الإجمالي الجديد

        Returns:
            كائن OrderItem المحدث أو None
        """
        logger.info(
            "order_items_repo_update_quantity",
            extra={
                "order_item_id": order_item_id,
                "quantity": quantity,
                "total_price": total_price,
            },
        )

        return await self.update(
            id=order_item_id,
            data={"quantity": quantity, "total_price": total_price},
        )

    # ==========================================
    # 🗑️ DELETE
    # ==========================================

    # ==============================================
    # DELETE BY ORDER
    # ==============================================

    async def delete_by_order(
        self,
        *,
        order_id: int,
    ) -> int:
        """
        حذف جميع عناصر طلب معين.

        Args:
            order_id: معرف الطلب

        Returns:
            عدد العناصر المحذوفة
        """
        try:
            # جلب جميع العناصر
            items = await self.get_by_order_id(order_id=order_id)
            count = len(items)

            # حذف كل عنصر
            for item in items:
                await self.delete(id=item.id)

            logger.info(
                "order_items_deleted_by_order",
                extra={
                    "order_id": order_id,
                    "count": count,
                },
            )

            return count

        except Exception as e:
            logger.exception(
                "order_items_repo_delete_by_order_failed",
                extra={
                    "order_id": order_id,
                    "error": str(e),
                },
            )
            raise
