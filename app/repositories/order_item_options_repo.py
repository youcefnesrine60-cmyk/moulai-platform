# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🎛 ORDER ITEM OPTIONS REPOSITORY
# عمليات قاعدة البيانات لخيارات عناصر الطلبات باستخدام SQLAlchemy
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
from app.models.order_item import OrderItemOption
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

OrderItemOptionData = Dict[str, Any]
OrderItemOptionUpdateData = Dict[str, Any]
OrderItemOptionList = List[OrderItemOption]

# ==============================================
# 🎛 ORDER ITEM OPTIONS REPOSITORY
# ==============================================


class OrderItemOptionsRepository(
    BaseRepository[
        OrderItemOption,
        OrderItemOptionData,
        OrderItemOptionUpdateData,
    ]
):
    """
    مستودع خيارات عناصر الطلبات - يوفر عمليات خاصة بخيارات عناصر الطلبات.
    
    مسؤول عن:
        - عمليات CRUD الأساسية لخيارات عناصر الطلبات
        - حساب السعر الإضافي الإجمالي
        - حذف خيارات عنصر الطلب
    
    Attributes:
        model: نموذج OrderItemOption
        session: جلسة قاعدة البيانات غير المتزامنة
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة مستودع خيارات عناصر الطلبات.
        
        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(OrderItemOption, session)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET BY ORDER ITEM ID
    # ==============================================

    async def get_by_order_item_id(
        self,
        *,
        order_item_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> OrderItemOptionList:
        """
        الحصول على خيارات عنصر طلب معين.
        
        Args:
            order_item_id: معرف عنصر الطلب
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            قائمة خيارات عنصر الطلب
        """
        try:
            query = (
                select(self.model)
                .where(self.model.order_item_id == order_item_id)
                .order_by(self.model.id.asc())
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "order_item_options_repo_get_by_order_item_failed",
                extra={
                    "order_item_id": order_item_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET BY OPTION NAME
    # ==============================================

    async def get_by_option_name(
        self,
        *,
        order_item_id: int,
        option_name: str,
    ) -> Optional[OrderItemOption]:
        """
        الحصول على خيار بواسطة اسمه.
        
        Args:
            order_item_id: معرف عنصر الطلب
            option_name: اسم الخيار
            
        Returns:
            كائن OrderItemOption أو None
        """
        try:
            result = await self.session.execute(
                select(self.model)
                .where(
                    self.model.order_item_id == order_item_id,
                    self.model.option_name == option_name,
                )
                .limit(1),
            )

            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(
                "order_item_options_repo_get_by_option_name_failed",
                extra={
                    "order_item_id": order_item_id,
                    "option_name": option_name,
                    "error": str(e),
                },
            )
            raise

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
            عدد الخيارات
        """
        try:
            result = await self.session.execute(
                select(func.count())
                .select_from(self.model)
                .where(self.model.order_item_id == order_item_id),
            )

            return result.scalar_one()

        except Exception as e:
            logger.exception(
                "order_item_options_repo_count_by_order_item_failed",
                extra={
                    "order_item_id": order_item_id,
                    "error": str(e),
                },
            )
            raise

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
            السعر الإضافي الإجمالي
        """
        try:
            result = await self.session.execute(
                select(func.coalesce(func.sum(self.model.additional_price), 0))
                .where(self.model.order_item_id == order_item_id),
            )

            return float(result.scalar_one())

        except Exception as e:
            logger.exception(
                "order_item_options_repo_get_total_additional_price_failed",
                extra={
                    "order_item_id": order_item_id,
                    "error": str(e),
                },
            )
            raise

    # ==========================================
    # 🗑️ DELETE
    # ==========================================

    # ==============================================
    # DELETE BY ORDER ITEM
    # ==============================================

    async def delete_by_order_item(
        self,
        *,
        order_item_id: int,
    ) -> int:
        """
        حذف جميع خيارات عنصر طلب معين.
        
        Args:
            order_item_id: معرف عنصر الطلب
            
        Returns:
            عدد الخيارات المحذوفة
        """
        try:
            # جلب جميع الخيارات
            options = await self.get_by_order_item_id(
                order_item_id=order_item_id,
            )

            count = len(options)

            # حذف كل خيار
            for option in options:
                await self.delete(id=option.id)

            logger.info(
                "order_item_options_deleted_by_order_item",
                extra={
                    "order_item_id": order_item_id,
                    "count": count,
                },
            )

            return count

        except Exception as e:
            logger.exception(
                "order_item_options_repo_delete_by_order_item_failed",
                extra={
                    "order_item_id": order_item_id,
                    "error": str(e),
                },
            )
            raise


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# دوال متوافقة مع الاستيرادات القديمة
# ==============================================

# ==============================================
# CREATE ORDER ITEM OPTION (COMPATIBILITY)
# ==============================================

async def create_order_item_option(
    *,
    order_item_id: int,
    option_group_name: str,
    option_name: str,
    additional_price: float = 0,
    session: AsyncSession,
) -> int:
    """
    إنشاء خيار جديد لعنصر طلب (دالة متوافقة مع الإصدار القديم).
    
    Args:
        order_item_id: معرف عنصر الطلب
        option_group_name: اسم مجموعة الخيارات
        option_name: اسم الخيار
        additional_price: السعر الإضافي
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        معرف الخيار
    """
    repo = OrderItemOptionsRepository(session=session)

    data: OrderItemOptionData = {
        "order_item_id": order_item_id,
        "option_group_name": option_group_name,
        "option_name": option_name,
        "additional_price": additional_price,
    }

    option = await repo.create(data=data)

    logger.info(
        "order_item_option_created",
        extra={
            "option_id": option.id,
            "order_item_id": order_item_id,
        },
    )

    return option.id


# ==============================================
# GET ORDER ITEM OPTION (COMPATIBILITY)
# ==============================================

async def get_order_item_option(
    *,
    option_id: int,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على خيار بالمعرف (دالة متوافقة مع الإصدار القديم).
    
    Args:
        option_id: معرف الخيار
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        قاموس بيانات الخيار أو None
    """
    repo = OrderItemOptionsRepository(session=session)

    option = await repo.get_by_id(id=option_id)

    if not option:
        return None

    return {
        "id": option.id,
        "order_item_id": option.order_item_id,
        "option_group_name": option.option_group_name,
        "option_name": option.option_name,
        "additional_price": option.additional_price,
        "created_at": option.created_at,
    }


# ==============================================
# GET ORDER ITEM OPTIONS (COMPATIBILITY)
# ==============================================

async def get_order_item_options(
    *,
    order_item_id: int,
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    الحصول على خيارات عنصر طلب معين (دالة متوافقة مع الإصدار القديم).
    
    Args:
        order_item_id: معرف عنصر الطلب
        session: جلسة قاعدة البيانات غير المتزامنة
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        
    Returns:
        قائمة الخيارات
    """
    repo = OrderItemOptionsRepository(session=session)

    options = await repo.get_by_order_item_id(
        order_item_id=order_item_id,
        skip=skip,
        limit=limit,
    )

    result = []

    for option in options:
        result.append({
            "id": option.id,
            "order_item_id": option.order_item_id,
            "option_group_name": option.option_group_name,
            "option_name": option.option_name,
            "additional_price": option.additional_price,
            "created_at": option.created_at,
        })

    return result


# ==============================================
# GET ORDER ITEM OPTIONS TOTAL (COMPATIBILITY)
# ==============================================

async def get_order_item_options_total(
    *,
    order_item_id: int,
    session: AsyncSession,
) -> float:
    """
    حساب السعر الإضافي الإجمالي لخيارات عنصر طلب معين (دالة متوافقة مع الإصدار القديم).
    
    Args:
        order_item_id: معرف عنصر الطلب
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        السعر الإضافي الإجمالي
    """
    repo = OrderItemOptionsRepository(session=session)

    return await repo.get_total_additional_price(
        order_item_id=order_item_id,
    )


# ==============================================
# COUNT ORDER ITEM OPTIONS (COMPATIBILITY)
# ==============================================

async def count_order_item_options(
    *,
    order_item_id: int,
    session: AsyncSession,
) -> int:
    """
    حساب عدد خيارات عنصر طلب معين (دالة متوافقة مع الإصدار القديم).
    
    Args:
        order_item_id: معرف عنصر الطلب
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        عدد الخيارات
    """
    repo = OrderItemOptionsRepository(session=session)

    return await repo.count_by_order_item(
        order_item_id=order_item_id,
    )


# ==============================================
# DELETE ORDER ITEM OPTION (COMPATIBILITY)
# ==============================================

async def delete_order_item_option(
    *,
    option_id: int,
    session: AsyncSession,
) -> None:
    """
    حذف خيار (دالة متوافقة مع الإصدار القديم).
    
    Args:
        option_id: معرف الخيار
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = OrderItemOptionsRepository(session=session)

    await repo.delete(id=option_id)

    logger.info(
        "order_item_option_deleted",
        extra={"option_id": option_id},
    )


# ==============================================
# DELETE ORDER ITEM OPTIONS (COMPATIBILITY)
# ==============================================

async def delete_order_item_options(
    *,
    order_item_id: int,
    session: AsyncSession,
) -> None:
    """
    حذف جميع خيارات عنصر طلب معين (دالة متوافقة مع الإصدار القديم).
    
    Args:
        order_item_id: معرف عنصر الطلب
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = OrderItemOptionsRepository(session=session)

    await repo.delete_by_order_item(
        order_item_id=order_item_id,
    )

    logger.info(
        "order_item_options_deleted",
        extra={"order_item_id": order_item_id},
    )


# ==============================================
# 🔄 TRANSACTION FUNCTIONS (للتوافق مع الكود القديم)
# ==============================================

# ==============================================
# CREATE ORDER ITEM OPTION TX
# ==============================================

async def create_order_item_option_tx(
    *,
    conn: AsyncSession,
    order_item_id: int,
    option_group_name: str,
    option_name: str,
    additional_price: float = 0,
) -> int:
    """
    إنشاء خيار جديد لعنصر طلب (معاملة) - دالة متوافقة مع الإصدار القديم.
    
    Args:
        conn: جلسة قاعدة البيانات (AsyncSession)
        order_item_id: معرف عنصر الطلب
        option_group_name: اسم مجموعة الخيارات
        option_name: اسم الخيار
        additional_price: السعر الإضافي
        
    Returns:
        معرف الخيار
    """
    repo = OrderItemOptionsRepository(conn)

    data: OrderItemOptionData = {
        "order_item_id": order_item_id,
        "option_group_name": option_group_name,
        "option_name": option_name,
        "additional_price": additional_price,
    }

    option = await repo.create(data=data)

    logger.info(
        "order_item_option_created_tx",
        extra={
            "option_id": option.id,
            "order_item_id": order_item_id,
        },
    )

    return option.id


# ==============================================
# DELETE ORDER ITEM OPTION TX
# ==============================================

async def delete_order_item_option_tx(
    *,
    conn: AsyncSession,
    option_id: int,
) -> None:
    """
    حذف خيار (معاملة) - دالة متوافقة مع الإصدار القديم.
    
    Args:
        conn: جلسة قاعدة البيانات (AsyncSession)
        option_id: معرف الخيار
    """
    repo = OrderItemOptionsRepository(conn)

    await repo.delete(id=option_id)

    logger.info(
        "order_item_option_deleted_tx",
        extra={"option_id": option_id},
    )