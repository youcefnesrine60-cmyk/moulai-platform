# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📂 CATEGORIES REPOSITORY
# عمليات قاعدة البيانات للتصنيفات باستخدام SQLAlchemy
# ==============================================

"""MoulAI operational module for categories repo.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from sqlalchemy import (
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models.category import Category
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

CategoryData = Dict[str, Any]
CategoryUpdateData = Dict[str, Any]
CategoryList = List[Category]

# ==============================================
# 📂 CATEGORIES REPOSITORY
# ==============================================


class CategoriesRepository(BaseRepository[Category, CategoryData, CategoryUpdateData]):
    """
    مستودع التصنيفات - يوفر عمليات خاصة بالتصنيفات.

    مسؤول عن:
        - عمليات CRUD الأساسية للتصنيفات
        - البحث والتصفية حسب المطعم
        - تحديث الترتيب والاسم

    Attributes:
        model: نموذج Category
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
        تهيئة مستودع التصنيفات.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(Category, session)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET BY RESTAURANT ID
    # ==============================================

    async def get_by_restaurant_id(
        self,
        *,
        restaurant_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> CategoryList:
        """
        الحصول على تصنيفات مطعم معين.

        Args:
            restaurant_id: معرف المطعم
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة التصنيفات
        """
        try:
            query = (
                select(self.model)
                .where(self.model.restaurant_id == restaurant_id)
                .order_by(
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
                "categories_repo_get_by_restaurant_failed",
                extra={
                    "restaurant_id": restaurant_id,
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
        restaurant_id: int,
        name: str,
    ) -> Optional[Category]:
        """
        الحصول على تصنيف بواسطة اسمه.

        Args:
            restaurant_id: معرف المطعم
            name: اسم التصنيف

        Returns:
            كائن Category أو None
        """
        try:
            result = await self.session.execute(
                select(self.model)
                .where(
                    self.model.restaurant_id == restaurant_id,
                    self.model.name == name,
                )
                .limit(1),
            )

            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(
                "categories_repo_get_by_name_failed",
                extra={
                    "restaurant_id": restaurant_id,
                    "categories_name": name,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # SEARCH
    # ==============================================

    async def search(
        self,
        *,
        query: str,
        restaurant_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> CategoryList:
        """
        البحث عن تصنيفات.

        Args:
            query: نص البحث
            restaurant_id: معرف المطعم (اختياري)
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة التصنيفات
        """
        try:
            conditions = [
                self.model.name.ilike(f"%{query}%"),
            ]

            if restaurant_id is not None:
                conditions.append(
                    self.model.restaurant_id == restaurant_id,
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

            result = await self.session.execute(stmt)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "categories_repo_search_failed",
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
        category_id: int,
        sort_order: int,
    ) -> Optional[Category]:
        """
        تحديث ترتيب التصنيف.

        Args:
            category_id: معرف التصنيف
            sort_order: الترتيب الجديد

        Returns:
            كائن Category المحدث أو None
        """
        logger.info(
            "categories_repo_update_sort_order",
            extra={
                "category_id": category_id,
                "sort_order": sort_order,
            },
        )

        return await self.update(
            id=category_id,
            data={"sort_order": sort_order},
        )

    # ==============================================
    # UPDATE NAME
    # ==============================================

    async def update_name(
        self,
        *,
        category_id: int,
        name: str,
    ) -> Optional[Category]:
        """
        تحديث اسم التصنيف.

        Args:
            category_id: معرف التصنيف
            name: الاسم الجديد

        Returns:
            كائن Category المحدث أو None
        """
        logger.info(
            "categories_repo_update_name",
            extra={
                "category_id": category_id,
                "categories_name": name,
            },
        )

        return await self.update(
            id=category_id,
            data={"name": name},
        )

    # ==========================================
    # 📊 STATISTICS
    # ==========================================

    # ==============================================
    # COUNT BY RESTAURANT
    # ==============================================

    async def count_by_restaurant(
        self,
        *,
        restaurant_id: int,
    ) -> int:
        """
        حساب عدد تصنيفات مطعم معين.

        Args:
            restaurant_id: معرف المطعم

        Returns:
            عدد التصنيفات
        """
        return await self.count(filters={"restaurant_id": restaurant_id})


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# دوال متوافقة مع الاستيرادات القديمة
# ==============================================

# ==============================================
# CREATE CATEGORY (COMPATIBILITY)
# ==============================================


async def create_category(
    *,
    restaurant_id: int,
    name: str,
    sort_order: int = 0,
    session: AsyncSession,
) -> int:
    """
    إنشاء تصنيف جديد (دالة متوافقة مع الإصدار القديم).

    Args:
        restaurant_id: معرف المطعم
        name: اسم التصنيف
        sort_order: ترتيب العرض
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        معرف التصنيف
    """
    repo = CategoriesRepository(session=session)

    data: CategoryData = {
        "restaurant_id": restaurant_id,
        "name": name,
        "sort_order": sort_order,
    }

    category = await repo.create(data=data)

    logger.info(
        "category_created",
        extra={
            "category_id": category.id,
            "restaurant_id": restaurant_id,
        },
    )

    return category.id


# ==============================================
# GET CATEGORY BY ID (COMPATIBILITY)
# ==============================================


async def get_category_by_id(
    *,
    category_id: int,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على تصنيف بالمعرف (دالة متوافقة مع الإصدار القديم).

    Args:
        category_id: معرف التصنيف
        session: جلسة قاعدة البيانات غير المتزامنة

    Returns:
        قاموس بيانات التصنيف أو None
    """
    repo = CategoriesRepository(session=session)

    category = await repo.get_by_id(id=category_id)

    if not category:
        return None

    return {
        "id": category.id,
        "restaurant_id": category.restaurant_id,
        "name": category.name,
        "sort_order": category.sort_order,
        "created_at": category.created_at,
    }


# ==============================================
# GET RESTAURANT CATEGORIES (COMPATIBILITY)
# ==============================================


async def get_restaurant_categories(
    *,
    restaurant_id: int,
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    الحصول على تصنيفات مطعم معين (دالة متوافقة مع الإصدار القديم).

    Args:
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات

    Returns:
        قائمة التصنيفات
    """
    repo = CategoriesRepository(session=session)

    categories = await repo.get_by_restaurant_id(
        restaurant_id=restaurant_id,
        skip=skip,
        limit=limit,
    )

    result = []

    for category in categories:
        result.append(
            {
                "id": category.id,
                "restaurant_id": category.restaurant_id,
                "name": category.name,
                "sort_order": category.sort_order,
                "created_at": category.created_at,
            }
        )

    return result


# ==============================================
# DELETE CATEGORY (COMPATIBILITY)
# ==============================================


async def delete_category(
    *,
    category_id: int,
    session: AsyncSession,
) -> None:
    """
    حذف تصنيف (دالة متوافقة مع الإصدار القديم).

    Args:
        category_id: معرف التصنيف
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = CategoriesRepository(session=session)

    await repo.delete(id=category_id)

    logger.info(
        "category_deleted",
        extra={"category_id": category_id},
    )
