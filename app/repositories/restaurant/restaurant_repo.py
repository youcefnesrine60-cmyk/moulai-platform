# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🏪 RESTAURANT REPOSITORY
# عمليات قاعدة البيانات للمطاعم
# Repository ---> SQLAlchemy
# ==============================================

from typing import (
    List,
    Optional,
)

from sqlalchemy import (
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logger import logger
from app.models.restaurant import Restaurant
from app.repositories.base import BaseRepository


# ==============================================
# 🧩 TYPES
# ==============================================

RestaurantList = List[Restaurant]


# ==============================================
# 🏪 RESTAURANT REPOSITORY
# ==============================================

class RestaurantRepository(BaseRepository[Restaurant, dict, dict]):
    """
    مستودع المطاعم - يوفر عمليات خاصة بالمطاعم.
    
    مسؤول عن:
        - عمليات CRUD الأساسية للمطاعم
        - البحث والتصفية حسب المالك والولاية
        - البحث النصي
        - جلب المطاعم مع العلاقات
    
    Attributes:
        session: جلسة قاعدة البيانات غير المتزامنة
        model: نموذج Restaurant
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة مستودع المطاعم.
        
        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(Restaurant, session)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET BY OWNER ID
    # ==============================================

    async def get_by_owner_id(
        self,
        *,
        owner_id: int,
        skip: int = 0,
        limit: int = 100,
        include_inactive: bool = False,
    ) -> RestaurantList:
        """
        الحصول على مطاعم المالك.
        
        Args:
            owner_id: معرف المالك
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            include_inactive: تضمين المطاعم غير النشطة
            
        Returns:
            RestaurantList: قائمة المطاعم
        """
        try:
            query = select(self.model).where(
                self.model.owner_id == owner_id,
            )

            if not include_inactive:
                query = query.where(self.model.is_active == True)

            query = query.offset(skip).limit(limit)

            result = await self.session.execute(query)

            return list(result.scalars().all())

        except Exception as e:
            logger.exception(
                "restaurant_repo_get_by_owner_failed",
                extra={
                    "owner_id": owner_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET BY WILAYA
    # ==============================================

    async def get_by_wilaya(
        self,
        *,
        wilaya: str,
        skip: int = 0,
        limit: int = 100,
    ) -> RestaurantList:
        """
        الحصول على مطاعم حسب الولاية.
        
        Args:
            wilaya: اسم الولاية
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            RestaurantList: قائمة المطاعم
        """
        try:
            query = (
                select(self.model)
                .where(self.model.wilaya == wilaya)
                .where(self.model.is_active == True)
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(query)

            return list(result.scalars().all())

        except Exception as e:
            logger.exception(
                "restaurant_repo_get_by_wilaya_failed",
                extra={
                    "wilaya": wilaya,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET BY NAME AND OWNER
    # ==============================================

    async def get_by_name_and_owner(
        self,
        *,
        owner_id: int,
        name: str,
    ) -> Optional[Restaurant]:
        """
        الحصول على مطعم بواسطة الاسم والمالك.
        
        ✅ يستخدم للتحقق من عدم وجود اسم مكرر لنفس المالك
        
        Args:
            owner_id: معرف المالك
            name: اسم المطعم
            
        Returns:
            Optional[Restaurant]: كائن Restaurant أو None
        """
        try:
            query = (
                select(self.model)
                .where(self.model.owner_id == owner_id)
                .where(self.model.name == name)
                .limit(1)
            )

            result = await self.session.execute(query)

            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(
                "restaurant_repo_get_by_name_and_owner_failed",
                extra={
                    "owner_id": owner_id,
                    "name": name,
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
        skip: int = 0,
        limit: int = 100,
    ) -> RestaurantList:
        """
        البحث عن مطاعم.
        
        Args:
            query: نص البحث
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            RestaurantList: قائمة المطاعم
        """
        try:
            stmt = (
                select(self.model)
                .where(
                    or_(
                        self.model.name.ilike(f"%{query}%"),
                        self.model.type.ilike(f"%{query}%"),
                        self.model.wilaya.ilike(f"%{query}%"),
                    ),
                )
                .where(self.model.is_active == True)
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(stmt)

            return list(result.scalars().all())

        except Exception as e:
            logger.exception(
                "restaurant_repo_search_failed",
                extra={
                    "query": query,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET WITH RELATIONS
    # ==============================================

    async def get_with_relations(
        self,
        *,
        restaurant_id: int,
    ) -> Optional[Restaurant]:
        """
        الحصول على مطعم مع جميع علاقاته.
        
        Args:
            restaurant_id: معرف المطعم
            
        Returns:
            Optional[Restaurant]: المطعم مع العلاقات أو None
        """
        try:
            query = (
                select(self.model)
                .where(self.model.id == restaurant_id)
                .options(
                    selectinload(self.model.owner),
                    selectinload(self.model.branches),
                    selectinload(self.model.categories),
                    selectinload(self.model.products),
                    selectinload(self.model.subscriptions),
                    selectinload(self.model.metrics),
                    selectinload(self.model.agents),
                )
            )

            result = await self.session.execute(query)

            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(
                "restaurant_repo_get_with_relations_failed",
                extra={
                    "restaurant_id": restaurant_id,
                    "error": str(e),
                },
            )
            raise

    # ==========================================
    # ✏️ UPDATES
    # ==========================================

    # ==============================================
    # UPDATE STATUS
    # ==============================================

    async def update_status(
        self,
        *,
        restaurant_id: int,
        is_active: bool,
    ) -> Optional[Restaurant]:
        """
        تحديث حالة المطعم.
        
        Args:
            restaurant_id: معرف المطعم
            is_active: الحالة الجديدة
            
        Returns:
            Optional[Restaurant]: المطعم المُحدّث أو None
        """
        return await self.update(
            id=restaurant_id,
            data={"is_active": is_active},
        )

    # ==========================================
    # 📊 STATISTICS
    # ==========================================

    # ==============================================
    # COUNT BY OWNER
    # ==============================================

    async def count_by_owner(
        self,
        *,
        owner_id: int,
    ) -> int:
        """
        حساب عدد مطاعم المالك.
        
        Args:
            owner_id: معرف المالك
            
        Returns:
            int: عدد المطاعم
        """
        return await self.count(
            filters={"owner_id": owner_id, "is_active": True},
        )

    # ==============================================
    # COUNT BY WILAYA
    # ==============================================

    async def count_by_wilaya(
        self,
        *,
        wilaya: str,
    ) -> int:
        """
        حساب عدد المطاعم في الولاية.
        
        Args:
            wilaya: اسم الولاية
            
        Returns:
            int: عدد المطاعم
        """
        return await self.count(
            filters={"wilaya": wilaya, "is_active": True},
        )

    # ==============================================
    # COUNT BRANCHES
    # ==============================================

    async def count_branches(
        self,
        *,
        restaurant_id: int,
    ) -> int:
        """
        حساب عدد فروع المطعم.
        
        ✅ يستخدم للتحقق قبل الحذف
        
        Args:
            restaurant_id: معرف المطعم
            
        Returns:
            int: عدد الفروع
        """
        try:
            from app.models.restaurant_group import RestaurantBranch

            from sqlalchemy import func

            result = await self.session.execute(
                select(func.count())
                .select_from(RestaurantBranch)
                .where(RestaurantBranch.restaurant_id == restaurant_id),
            )

            return result.scalar_one() or 0

        except Exception as e:
            logger.exception(
                "restaurant_repo_count_branches_failed",
                extra={
                    "restaurant_id": restaurant_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # COUNT PRODUCTS
    # ==============================================

    async def count_products(
        self,
        *,
        restaurant_id: int,
    ) -> int:
        """
        حساب عدد منتجات المطعم.
        
        ✅ يستخدم للتحقق قبل الحذف
        
        Args:
            restaurant_id: معرف المطعم
            
        Returns:
            int: عدد المنتجات
        """
        try:
            from app.models.product import Product

            from sqlalchemy import func

            result = await self.session.execute(
                select(func.count())
                .select_from(Product)
                .where(Product.restaurant_id == restaurant_id),
            )

            return result.scalar_one() or 0

        except Exception as e:
            logger.exception(
                "restaurant_repo_count_products_failed",
                extra={
                    "restaurant_id": restaurant_id,
                    "error": str(e),
                },
            )
            raise


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# دوال متوافقة مع الاستيرادات القديمة
# ==============================================

# ==============================================
# GET RESTAURANT BY ID (COMPATIBILITY)
# ==============================================

async def get_restaurant_by_id(
    *,
    restaurant_id: int,
    session: AsyncSession,
) -> Optional[Restaurant]:
    """
    الحصول على مطعم بالمعرف (دالة متوافقة مع الإصدار القديم).
    
    Args:
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        Optional[Restaurant]: كائن Restaurant أو None
    """
    repo = RestaurantRepository(session=session)

    return await repo.get_by_id(
        id=restaurant_id,
    )


# ==============================================
# GET RESTAURANTS BY OWNER (COMPATIBILITY)
# ==============================================

async def get_restaurants_by_owner(
    *,
    owner_id: int,
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
) -> RestaurantList:
    """
    الحصول على مطاعم المالك (دالة متوافقة مع الإصدار القديم).
    
    Args:
        owner_id: معرف المالك
        session: جلسة قاعدة البيانات غير المتزامنة
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        
    Returns:
        RestaurantList: قائمة المطاعم
    """
    repo = RestaurantRepository(session=session)

    return await repo.get_by_owner_id(
        owner_id=owner_id,
        skip=skip,
        limit=limit,
    )


# ==============================================
# SEARCH RESTAURANTS (COMPATIBILITY)
# ==============================================

async def search_restaurants(
    *,
    query: str,
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
) -> RestaurantList:
    """
    البحث عن مطاعم (دالة متوافقة مع الإصدار القديم).
    
    Args:
        query: نص البحث
        session: جلسة قاعدة البيانات غير المتزامنة
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        
    Returns:
        RestaurantList: قائمة المطاعم
    """
    repo = RestaurantRepository(session=session)

    return await repo.search(
        query=query,
        skip=skip,
        limit=limit,
    )


# ==============================================
# GET RESTAURANT WITH DETAILS (COMPATIBILITY)
# ==============================================

async def get_restaurant_with_details(
    *,
    restaurant_id: int,
    session: AsyncSession,
) -> Optional[Restaurant]:
    """
    الحصول على مطعم مع جميع علاقاته (دالة متوافقة مع الإصدار القديم).
    
    Args:
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        Optional[Restaurant]: كائن Restaurant مع العلاقات أو None
    """
    repo = RestaurantRepository(session=session)

    return await repo.get_with_relations(
        restaurant_id=restaurant_id,
    )


# ==============================================
# GET ALL RESTAURANTS (COMPATIBILITY)
# ==============================================

async def get_all_restaurants(
    *,
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    only_active: bool = True,
) -> RestaurantList:
    """
    الحصول على جميع المطاعم (دالة متوافقة مع الإصدار القديم).
    
    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        only_active: جلب المطاعم النشطة فقط
        
    Returns:
        RestaurantList: قائمة المطاعم
    """
    repo = RestaurantRepository(session=session)

    filters = {}

    if only_active:
        filters["is_active"] = True

    return await repo.get_all(
        skip=skip,
        limit=limit,
        filters=filters,
        order_by="name",
    )


# ==============================================
# CREATE RESTAURANT (COMPATIBILITY)
# ==============================================

async def create_restaurant(
    *,
    session: AsyncSession,
    data: dict,
) -> Restaurant:
    """
    إنشاء مطعم جديد (دالة متوافقة مع الإصدار القديم).
    
    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        data: بيانات المطعم
        
    Returns:
        Restaurant: المطعم المُنشأ
    """
    repo = RestaurantRepository(session=session)

    return await repo.create(data=data)


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "RestaurantRepository",
    "RestaurantList",
    "get_restaurant_by_id",
    "get_restaurants_by_owner",
    "search_restaurants",
    "get_restaurant_with_details",
    "get_all_restaurants",
    "create_restaurant",
]