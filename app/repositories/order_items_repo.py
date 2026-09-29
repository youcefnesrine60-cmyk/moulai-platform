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
    Dict,
    List,
    Optional,
)

from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models.order_item import OrderItem
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

OrderItemData = Dict[str, Any]
OrderItemUpdateData = Dict[str, Any]
OrderItemList = List[OrderItem]

# ==============================================
# 📦 ORDER ITEMS REPOSITORY
# ==============================================


class OrderItemsRepository(BaseRepository[OrderItem, OrderItemData, OrderItemUpdateData]):
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

    # ==========================================
    # 📖 QUERIES
    # ==========================================

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
                select(self.model)
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
                select(self.model)
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
                select(func.coalesce(func.sum(self.model.total_price), 0))
                .where(self.model.order_id == order_id),
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
    ) -> Optional[OrderItem]:
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


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# دوال متوافقة مع الاستيرادات القديمة
# ==============================================

# ==============================================
# CREATE ORDER ITEM (COMPATIBILITY)
# ==============================================

async def create_order_item(
    *,
    order_id: int,
    product_id: int,
    product_name: str,
    unit_price: float,
    quantity: int,
    total_price: float,
    session: AsyncSession,
) -> int:
    """
    إنشاء عنصر طلب جديد (دالة متوافقة مع الإصدار القديم).
    
    Args:
        order_id: معرف الطلب
        product_id: معرف المنتج
        product_name: اسم المنتج
        unit_price: سعر الوحدة
        quantity: الكمية
        total_price: السعر الإجمالي
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        معرف عنصر الطلب
    """
    repo = OrderItemsRepository(session=session)

    data: OrderItemData = {
        "order_id": order_id,
        "product_id": product_id,
        "product_name": product_name,
        "unit_price": unit_price,
        "quantity": quantity,
        "total_price": total_price,
    }

    item = await repo.create(data=data)

    logger.info(
        "order_item_created",
        extra={
            "order_item_id": item.id,
            "order_id": order_id,
        },
    )

    return item.id


# ==============================================
# GET ORDER ITEM (COMPATIBILITY)
# ==============================================

async def get_order_item(
    *,
    order_item_id: int,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على عنصر طلب بالمعرف (دالة متوافقة مع الإصدار القديم).
    
    Args:
        order_item_id: معرف عنصر الطلب
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        قاموس بيانات عنصر الطلب أو None
    """
    repo = OrderItemsRepository(session=session)

    item = await repo.get_by_id(id=order_item_id)

    if not item:
        return None

    return {
        "id": item.id,
        "order_id": item.order_id,
        "product_id": item.product_id,
        "product_name": item.product_name,
        "unit_price": item.unit_price,
        "quantity": item.quantity,
        "total_price": item.total_price,
        "created_at": item.created_at,
    }


# ==============================================
# GET ORDER ITEMS (COMPATIBILITY)
# ==============================================

async def get_order_items(
    *,
    order_id: int,
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    الحصول على عناصر طلب معين (دالة متوافقة مع الإصدار القديم).
    
    Args:
        order_id: معرف الطلب
        session: جلسة قاعدة البيانات غير المتزامنة
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        
    Returns:
        قائمة عناصر الطلب
    """
    repo = OrderItemsRepository(session=session)

    items = await repo.get_by_order_id(
        order_id=order_id,
        skip=skip,
        limit=limit,
    )

    result = []

    for item in items:
        result.append({
            "id": item.id,
            "order_id": item.order_id,
            "product_id": item.product_id,
            "product_name": item.product_name,
            "unit_price": item.unit_price,
            "quantity": item.quantity,
            "total_price": item.total_price,
            "created_at": item.created_at,
        })

    return result


# ==============================================
# COUNT ORDER ITEMS (COMPATIBILITY)
# ==============================================

async def count_order_items(
    *,
    order_id: int,
    session: AsyncSession,
) -> int:
    """
    حساب عدد عناصر طلب معين (دالة متوافقة مع الإصدار القديم).
    
    Args:
        order_id: معرف الطلب
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        عدد العناصر
    """
    repo = OrderItemsRepository(session=session)

    return await repo.count_by_order(order_id=order_id)


# ==============================================
# GET ORDER ITEMS SUBTOTAL (COMPATIBILITY)
# ==============================================

async def get_order_items_subtotal(
    *,
    order_id: int,
    session: AsyncSession,
) -> float:
    """
    حساب المجموع الفرعي لعناصر طلب معين (دالة متوافقة مع الإصدار القديم).
    
    Args:
        order_id: معرف الطلب
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        المجموع الفرعي
    """
    repo = OrderItemsRepository(session=session)

    return await repo.get_subtotal(order_id=order_id)


# ==============================================
# UPDATE ORDER ITEM QUANTITY (COMPATIBILITY)
# ==============================================

async def update_order_item_quantity(
    *,
    order_item_id: int,
    quantity: int,
    total_price: float,
    session: AsyncSession,
) -> None:
    """
    تحديث كمية عنصر الطلب (دالة متوافقة مع الإصدار القديم).
    
    Args:
        order_item_id: معرف عنصر الطلب
        quantity: الكمية الجديدة
        total_price: السعر الإجمالي الجديد
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = OrderItemsRepository(session=session)

    await repo.update_quantity(
        order_item_id=order_item_id,
        quantity=quantity,
        total_price=total_price,
    )

    logger.info(
        "order_item_quantity_updated",
        extra={"order_item_id": order_item_id},
    )


# ==============================================
# DELETE ORDER ITEM (COMPATIBILITY)
# ==============================================

async def delete_order_item(
    *,
    order_item_id: int,
    session: AsyncSession,
) -> None:
    """
    حذف عنصر طلب (دالة متوافقة مع الإصدار القديم).
    
    Args:
        order_item_id: معرف عنصر الطلب
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = OrderItemsRepository(session=session)

    await repo.delete(id=order_item_id)

    logger.info(
        "order_item_deleted",
        extra={"order_item_id": order_item_id},
    )


# ==============================================
# DELETE ORDER ITEMS (COMPATIBILITY)
# ==============================================

async def delete_order_items(
    *,
    order_id: int,
    session: AsyncSession,
) -> None:
    """
    حذف جميع عناصر طلب معين (دالة متوافقة مع الإصدار القديم).
    
    Args:
        order_id: معرف الطلب
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = OrderItemsRepository(session=session)

    await repo.delete_by_order(order_id=order_id)

    logger.info(
        "order_items_deleted",
        extra={"order_id": order_id},
    )


# ==============================================
# 🔄 TRANSACTION FUNCTIONS (للتوافق مع الكود القديم)
# ==============================================

# ==============================================
# CREATE ORDER ITEM TX
# ==============================================

async def create_order_item_tx(
    *,
    conn: AsyncSession,
    order_id: int,
    product_id: int,
    product_name: str,
    unit_price: float,
    quantity: int,
    total_price: float,
) -> int:
    """
    إنشاء عنصر طلب جديد (معاملة) - دالة متوافقة مع الإصدار القديم.
    
    Args:
        conn: جلسة قاعدة البيانات (AsyncSession)
        order_id: معرف الطلب
        product_id: معرف المنتج
        product_name: اسم المنتج
        unit_price: سعر الوحدة
        quantity: الكمية
        total_price: السعر الإجمالي
        
    Returns:
        معرف عنصر الطلب
    """
    repo = OrderItemsRepository(conn)

    data: OrderItemData = {
        "order_id": order_id,
        "product_id": product_id,
        "product_name": product_name,
        "unit_price": unit_price,
        "quantity": quantity,
        "total_price": total_price,
    }

    item = await repo.create(data=data)

    logger.info(
        "order_item_created_tx",
        extra={
            "order_item_id": item.id,
            "order_id": order_id,
        },
    )

    return item.id


# ==============================================
# DELETE ORDER ITEM TX
# ==============================================

async def delete_order_item_tx(
    *,
    conn: AsyncSession,
    order_item_id: int,
) -> None:
    """
    حذف عنصر طلب (معاملة) - دالة متوافقة مع الإصدار القديم.
    
    Args:
        conn: جلسة قاعدة البيانات (AsyncSession)
        order_item_id: معرف عنصر الطلب
    """
    repo = OrderItemsRepository(conn)

    await repo.delete(id=order_item_id)

    logger.info(
        "order_item_deleted_tx",
        extra={"order_item_id": order_item_id},
    )