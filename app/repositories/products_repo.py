# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🍔 PRODUCTS REPOSITORY
# عمليات قاعدة البيانات للمنتجات
# Repository ---> SQLAlchemy
# ==============================================

from typing import (
    List,
    Optional,
)

from sqlalchemy import (
    and_,
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logger import logger
from app.models.product import Product
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

ProductList = List[Product]

# ==============================================
# 🍔 PRODUCT REPOSITORY
# ==============================================


class ProductRepository(BaseRepository[Product, dict, dict]):
    """
    مستودع المنتجات - يوفر عمليات خاصة بالمنتجات.
    
    مسؤول عن:
        - عمليات CRUD الأساسية للمنتجات
        - البحث والتصفية حسب المطعم والتصنيف
        - جلب المنتجات مع العلاقات
        - تحديث التوفر والسعر والترتيب
    
    Attributes:
        model: نموذج Product
        session: جلسة قاعدة البيانات غير المتزامنة
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة مستودع المنتجات.
        
        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(Product, session)

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
        only_available: bool = True,
        category_id: Optional[int] = None,
    ) -> ProductList:
        """
        الحصول على منتجات مطعم معين.
        
        Args:
            restaurant_id: معرف المطعم
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            only_available: جلب المنتجات المتاحة فقط
            category_id: فلتر حسب التصنيف
            
        Returns:
            قائمة المنتجات
        """
        try:
            query = select(self.model).where(
                self.model.restaurant_id == restaurant_id,
            )

            if only_available:
                query = query.where(self.model.is_available == True)

            if category_id is not None:
                query = query.where(self.model.category_id == category_id)

            query = query.order_by(
                self.model.sort_order.asc(),
                self.model.id.asc(),
            ).offset(skip).limit(limit)

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "product_repo_get_by_restaurant_failed",
                extra={
                    "restaurant_id": restaurant_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET BY CATEGORY ID
    # ==============================================

    async def get_by_category_id(
        self,
        *,
        category_id: int,
        skip: int = 0,
        limit: int = 100,
        only_available: bool = True,
    ) -> ProductList:
        """
        الحصول على منتجات تصنيف معين.
        
        Args:
            category_id: معرف التصنيف
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            only_available: جلب المنتجات المتاحة فقط
            
        Returns:
            قائمة المنتجات
        """
        try:
            query = select(self.model).where(
                self.model.category_id == category_id,
            )

            if only_available:
                query = query.where(self.model.is_available == True)

            query = query.order_by(
                self.model.sort_order.asc(),
                self.model.id.asc(),
            ).offset(skip).limit(limit)

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "product_repo_get_by_category_failed",
                extra={
                    "category_id": category_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET WITH DETAILS
    # ==============================================

    async def get_with_details(
        self,
        *,
        product_id: int,
    ) -> Optional[Product]:
        """
        الحصول على منتج مع جميع علاقاته.
        
        Args:
            product_id: معرف المنتج
            
        Returns:
            المنتج مع العلاقات أو None
        """
        try:
            query = (
                select(self.model)
                .where(self.model.id == product_id)
                .options(
                    selectinload(self.model.restaurant),
                    selectinload(self.model.category),
                    selectinload(self.model.option_groups),
                )
            )

            result = await self.session.execute(query)

            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(
                "product_repo_get_with_details_failed",
                extra={
                    "product_id": product_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET AVAILABLE BY RESTAURANT
    # ==============================================

    async def get_available_by_restaurant(
        self,
        *,
        restaurant_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> ProductList:
        """
        الحصول على المنتجات المتاحة فقط لمطعم معين.
        
        Args:
            restaurant_id: معرف المطعم
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            قائمة المنتجات المتاحة
        """
        return await self.get_by_restaurant_id(
            restaurant_id=restaurant_id,
            skip=skip,
            limit=limit,
            only_available=True,
        )

    # ==============================================
    # GET BY IDS
    # ==============================================

    async def get_by_ids(
        self,
        *,
        product_ids: List[int],
        only_available: bool = True,
    ) -> ProductList:
        """
        الحصول على منتجات حسب قائمة المعرفات.
        
        Args:
            product_ids: قائمة معرفات المنتجات
            only_available: جلب المنتجات المتاحة فقط
            
        Returns:
            قائمة المنتجات
        """
        try:
            query = select(self.model).where(
                self.model.id.in_(product_ids),
            )

            if only_available:
                query = query.where(self.model.is_available == True)

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "product_repo_get_by_ids_failed",
                extra={
                    "product_ids": product_ids,
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
    ) -> ProductList:
        """
        البحث عن منتجات.
        
        Args:
            query: نص البحث
            restaurant_id: معرف المطعم (اختياري)
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            قائمة المنتجات
        """
        try:
            stmt = select(self.model).where(
                or_(
                    self.model.name.ilike(f"%{query}%"),
                    self.model.description.ilike(f"%{query}%"),
                ),
                self.model.is_available == True,
            )
            if restaurant_id is not None:
                stmt = stmt.where(self.model.restaurant_id == restaurant_id)
            stmt = stmt.offset(skip).limit(limit)

            result = await self.session.execute(stmt)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "product_repo_search_failed",
                extra={
                    "query": query,
                    "restaurant_id": restaurant_id,
                    "error": str(e),
                },
            )
            raise

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
        only_available: bool = True,
    ) -> int:
        """
        حساب عدد منتجات مطعم معين.
        
        Args:
            restaurant_id: معرف المطعم
            only_available: حساب المنتجات المتاحة فقط
            
        Returns:
            عدد المنتجات
        """
        filters = {"restaurant_id": restaurant_id}

        if only_available:
            filters["is_available"] = True

        return await self.count(filters=filters)

    # ==============================================
    # COUNT BY CATEGORY
    # ==============================================

    async def count_by_category(
        self,
        *,
        category_id: int,
        only_available: bool = True,
    ) -> int:
        """
        حساب عدد منتجات تصنيف معين.
        
        Args:
            category_id: معرف التصنيف
            only_available: حساب المنتجات المتاحة فقط
            
        Returns:
            عدد المنتجات
        """
        filters = {"category_id": category_id}

        if only_available:
            filters["is_available"] = True

        return await self.count(filters=filters)

    # ==========================================
    # ✏️ UPDATES
    # ==========================================

    # ==============================================
    # UPDATE AVAILABILITY
    # ==============================================

    async def update_availability(
        self,
        *,
        product_id: int,
        is_available: bool,
    ) -> Optional[Product]:
        """
        تحديث حالة توفر المنتج.
        
        Args:
            product_id: معرف المنتج
            is_available: حالة التوفر الجديدة
            
        Returns:
            المنتج المُحدّث أو None
        """
        return await self.update(
            product_id=product_id,
            data={"is_available": is_available},
        )

    # ==============================================
    # UPDATE PRICE
    # ==============================================

    async def update_price(
        self,
        *,
        product_id: int,
        price: float,
    ) -> Optional[Product]:
        """
        تحديث سعر المنتج.
        
        Args:
            product_id: معرف المنتج
            price: السعر الجديد
            
        Returns:
            المنتج المُحدّث أو None
        """
        return await self.update(
            product_id=product_id,
            data={"price": price},
        )

    # ==============================================
    # UPDATE SORT ORDER
    # ==============================================

    async def update_sort_order(
        self,
        *,
        product_id: int,
        sort_order: int,
    ) -> Optional[Product]:
        """
        تحديث ترتيب المنتج.
        
        Args:
            product_id: معرف المنتج
            sort_order: الترتيب الجديد
            
        Returns:
            المنتج المُحدّث أو None
        """
        return await self.update(
            product_id=product_id,
            data={"sort_order": sort_order},
        )


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# دوال متوافقة مع الاستيرادات القديمة
# ==============================================

# ==============================================
# GET PRODUCT BY ID (COMPATIBILITY)
# ==============================================

async def get_product_by_id(
    *,
    product_id: int,
    session: AsyncSession,
) -> Optional[Product]:
    """
    الحصول على منتج بالمعرف (دالة متوافقة مع الإصدار القديم).
    
    Args:
        product_id: معرف المنتج
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        المنتج أو None
    """
    repo = ProductRepository(session=session)

    return await repo.get_by_id(
        product_id=product_id,
    )


# ==============================================
# GET RESTAURANT PRODUCTS (COMPATIBILITY)
# ==============================================

async def get_restaurant_products(
    *,
    restaurant_id: int,
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    only_available: bool = True,
) -> ProductList:
    """
    الحصول على منتجات مطعم معين (دالة متوافقة مع الإصدار القديم).
    
    Args:
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        only_available: جلب المنتجات المتاحة فقط
        
    Returns:
        قائمة المنتجات
    """
    repo = ProductRepository(session=session)

    return await repo.get_by_restaurant_id(
        restaurant_id=restaurant_id,
        skip=skip,
        limit=limit,
        only_available=only_available,
    )


# ==============================================
# COUNT RESTAURANT PRODUCTS (COMPATIBILITY)
# ==============================================

async def count_restaurant_products(
    *,
    restaurant_id: int,
    session: AsyncSession,
    only_available: bool = True,
) -> int:
    """
    حساب عدد منتجات مطعم معين (دالة متوافقة مع الإصدار القديم).
    
    Args:
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة
        only_available: حساب المنتجات المتاحة فقط
        
    Returns:
        عدد المنتجات
    """
    repo = ProductRepository(session=session)

    return await repo.count_by_restaurant(
        restaurant_id=restaurant_id,
        only_available=only_available,
    )