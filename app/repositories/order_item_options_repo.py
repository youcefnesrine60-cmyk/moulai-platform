# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / REPOSITORIES / ORDER ITEM OPTIONS REPO
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for order item options repo.

Part of MoulAI Platform - Agent-as-a-Service.
"""

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
)

from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload

from app.core.logger import logger
from app.models.order_item import OrderItemOption
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

OrderItemOptionData = dict[str, Any]
OrderItemOptionUpdateData = dict[str, Any]
OrderItemOptionList = list[OrderItemOption]

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

    # ==============================================
    #   INIT
    # ==============================================

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
        self.commit_on_write = False
        self.query_options = [raiseload("*")]

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET BY ORDER ITEM ID
    # ==============================================

    async def get_by_name(self, *, order_item_id, option_group_name, option_name):
        return (
            await self.session.execute(
                self._select()
                .where(
                    self.model.order_item_id == order_item_id,
                    self.model.option_group_name == option_group_name,
                    self.model.option_name == option_name,
                )
                .limit(1)
            )
        ).scalar_one_or_none()

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
                self._select()
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
    ) -> OrderItemOption | None:
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
                self._select()
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
                select(func.coalesce(func.sum(self.model.additional_price), 0)).where(
                    self.model.order_item_id == order_item_id
                ),
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
