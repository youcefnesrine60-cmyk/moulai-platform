# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🎯 PRODUCT OPTION REPOSITORY
# عمليات قاعدة البيانات لخيارات المنتج باستخدام SQLAlchemy
# ==============================================

"""MoulAI operational module for product option repo.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from typing import (
    Any,
)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models.product_option import ProductOption
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

ProductOptionData = dict[str, Any]
ProductOptionUpdateData = dict[str, Any]
ProductOptionList = list[ProductOption]

# ==============================================
# 🎯 PRODUCT OPTION REPOSITORY
# ==============================================


class ProductOptionRepository(
    BaseRepository[
        ProductOption,
        ProductOptionData,
        ProductOptionUpdateData,
    ]
):
    """
    مستودع خيارات المنتج - يوفر عمليات خاصة بخيارات المنتج.

    مسؤول عن:
        - عمليات CRUD الأساسية لخيارات المنتج
        - البحث والتصفية حسب مجموعة الخيارات
        - تحديث التوفر والسعر والترتيب

    Attributes:
        model: نموذج ProductOption
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
        تهيئة مستودع خيارات المنتج.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(ProductOption, session)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET BY GROUP ID
    # ==============================================

    async def get_by_group_id(
        self,
        *,
        group_id: int,
        skip: int = 0,
        limit: int = 100,
        only_available: bool = True,
    ) -> ProductOptionList:
        """
        الحصول على خيارات مجموعة معينة.

        Args:
            group_id: معرف مجموعة الخيارات
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            only_available: جلب الخيارات المتاحة فقط

        Returns:
            قائمة خيارات المنتج
        """
        try:
            query = select(self.model).where(
                self.model.group_id == group_id,
            )

            if only_available:
                query = query.where(self.model.is_available == True)

            query = (
                query.order_by(
                    self.model.sort_order.asc(),
                    self.model.id.asc(),
                )
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "product_option_repo_get_by_group_failed",
                extra={
                    "group_id": group_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET BY NAME
    # ==============================================

    async def get_by_name(
        self,
        *,
        group_id: int,
        name: str,
    ) -> ProductOption | None:
        """
        الحصول على خيار بواسطة اسمه.

        Args:
            group_id: معرف مجموعة الخيارات
            name: اسم الخيار

        Returns:
            كائن ProductOption أو None
        """
        try:
            result = await self.session.execute(
                select(self.model)
                .where(
                    self.model.group_id == group_id,
                    self.model.name == name,
                )
                .limit(1),
            )

            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(
                "product_option_repo_get_by_name_failed",
                extra={
                    "group_id": group_id,
                    "product_option_name": name,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET AVAILABLE BY GROUP
    # ==============================================

    async def get_available_by_group(
        self,
        *,
        group_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> ProductOptionList:
        """
        الحصول على الخيارات المتاحة لمجموعة معينة.

        Args:
            group_id: معرف مجموعة الخيارات
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة الخيارات المتاحة
        """
        return await self.get_by_group_id(
            group_id=group_id,
            skip=skip,
            limit=limit,
            only_available=True,
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
    ) -> ProductOptionList:
        """
        البحث عن خيارات المنتج.

        Args:
            query: نص البحث
            group_id: معرف مجموعة الخيارات (اختياري)
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            only_available: جلب الخيارات المتاحة فقط

        Returns:
            قائمة خيارات المنتج
        """
        try:
            conditions = [
                self.model.name.ilike(f"%{query}%"),
            ]

            if group_id is not None:
                conditions.append(
                    self.model.group_id == group_id,
                )

            stmt = (
                select(self.model)
                .where(*conditions)
                .order_by(
                    self.model.sort_order.asc(),
                    self.model.name.asc(),
                )
                .offset(skip)
                .limit(limit)
            )

            if only_available:
                stmt = stmt.where(self.model.is_available == True)

            result = await self.session.execute(stmt)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "product_option_repo_search_failed",
                extra={
                    "query": query,
                    "error": str(e),
                },
            )
            raise

    # ==========================================
    # ✏️ UPDATES
    # ==========================================

    # ==============================================
    # UPDATE SORT ORDER
    # ==============================================

    async def update_sort_order(
        self,
        *,
        option_id: int,
        sort_order: int,
    ) -> ProductOption | None:
        """
        تحديث ترتيب الخيار.

        Args:
            option_id: معرف الخيار
            sort_order: الترتيب الجديد

        Returns:
            كائن ProductOption المحدث أو None
        """
        logger.info(
            "product_option_repo_update_sort_order",
            extra={
                "option_id": option_id,
                "sort_order": sort_order,
            },
        )

        return await self.update(
            id=option_id,
            data={"sort_order": sort_order},
        )

    # ==============================================
    # UPDATE AVAILABILITY
    # ==============================================

    async def update_availability(
        self,
        *,
        option_id: int,
        is_available: bool,
    ) -> ProductOption | None:
        """
        تحديث حالة توفر الخيار.

        Args:
            option_id: معرف الخيار
            is_available: حالة التوفر الجديدة

        Returns:
            كائن ProductOption المحدث أو None
        """
        logger.info(
            "product_option_repo_update_availability",
            extra={
                "option_id": option_id,
                "is_available": is_available,
            },
        )

        return await self.update(
            id=option_id,
            data={"is_available": is_available},
        )

    # ==============================================
    # UPDATE PRICE
    # ==============================================

    async def update_price(
        self,
        *,
        option_id: int,
        extra_price: float,
    ) -> ProductOption | None:
        """
        تحديث السعر الإضافي للخيار.

        Args:
            option_id: معرف الخيار
            extra_price: السعر الإضافي الجديد

        Returns:
            كائن ProductOption المحدث أو None
        """
        logger.info(
            "product_option_repo_update_price",
            extra={
                "option_id": option_id,
                "extra_price": extra_price,
            },
        )

        return await self.update(
            id=option_id,
            data={"extra_price": extra_price},
        )

    # ==============================================
    # UPDATE NAME
    # ==============================================

    async def update_name(
        self,
        *,
        option_id: int,
        name: str,
    ) -> ProductOption | None:
        """
        تحديث اسم الخيار.

        Args:
            option_id: معرف الخيار
            name: الاسم الجديد

        Returns:
            كائن ProductOption المحدث أو None
        """
        logger.info(
            "product_option_repo_update_name",
            extra={
                "option_id": option_id,
                "product_option_name": name,
            },
        )

        return await self.update(
            id=option_id,
            data={"name": name},
        )

    # ==============================================
    # ACTIVATE
    # ==============================================

    async def activate(
        self,
        *,
        option_id: int,
    ) -> ProductOption | None:
        """
        تفعيل الخيار.

        Args:
            option_id: معرف الخيار

        Returns:
            كائن ProductOption المحدث أو None
        """
        logger.info(
            "product_option_repo_activate",
            extra={"option_id": option_id},
        )

        return await self.update_availability(
            option_id=option_id,
            is_available=True,
        )

    # ==============================================
    # DEACTIVATE
    # ==============================================

    async def deactivate(
        self,
        *,
        option_id: int,
    ) -> ProductOption | None:
        """
        إلغاء تفعيل الخيار.

        Args:
            option_id: معرف الخيار

        Returns:
            كائن ProductOption المحدث أو None
        """
        logger.info(
            "product_option_repo_deactivate",
            extra={"option_id": option_id},
        )

        return await self.update_availability(
            option_id=option_id,
            is_available=False,
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
            عدد الخيارات
        """
        filters = {"group_id": group_id}

        if only_available:
            filters["is_available"] = True

        return await self.count(filters=filters)

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
            عدد الخيارات المتاحة
        """
        return await self.count_by_group(
            group_id=group_id,
            only_available=True,
        )

    # ==========================================
    # 🗑️ DELETE
    # ==========================================

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
            عدد الخيارات المحذوفة
        """
        try:
            options = await self.get_by_group_id(
                group_id=group_id,
                only_available=False,
            )

            count = len(options)

            for option in options:
                await self.delete(id=option.id)

            logger.info(
                "product_options_deleted_by_group",
                extra={
                    "group_id": group_id,
                    "count": count,
                },
            )

            return count

        except Exception as e:
            logger.exception(
                "product_option_repo_delete_by_group_failed",
                extra={
                    "group_id": group_id,
                    "error": str(e),
                },
            )
            raise
