# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🏪 RESTAURANT SERVICE
# منطق الأعمال للمطاعم
# يدير عمليات استعراض المطاعم (QUERIES فقط)
# ==============================================

"""MoulAI operational module for service.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.logger import logger
from app.models.owner import Owner
from app.repositories.restaurant.restaurant_repo import RestaurantRepository
from app.schemas.restaurant import (
    RestaurantResponse,
    RestaurantStats,
)

# ==============================================
# 🧩 TYPES
# ==============================================

RestaurantData = Dict[str, Any]
RestaurantUpdateData = Dict[str, Any]
RestaurantList = List[RestaurantResponse]


# ==============================================
# 🏪 RESTAURANT SERVICE
# ==============================================


class RestaurantService:
    """
    خدمة المطاعم - تدير منطق الأعمال للمطاعم (QUERIES).

    مسؤولة عن:
        - استعراض المطاعم
        - البحث والتصفية
        - الإحصائيات
        - جلب المطاعم مع العلاقات

    ⚠️ ملاحظة: عمليات MUTATIONS (create, update, delete) في handlers.py

    Attributes:
        session: جلسة قاعدة البيانات غير المتزامنة
        repo: مستودع المطاعم
    """

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة خدمة المطاعم.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        self.session = session
        self.repo = RestaurantRepository(session)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET RESTAURANT BY ID
    # ==============================================

    async def get_restaurant(
        self,
        *,
        restaurant_id: int,
        include_inactive: bool = False,
    ) -> RestaurantResponse:
        """
        الحصول على مطعم بالمعرف.

        Args:
            restaurant_id: معرف المطعم
            include_inactive: تضمين المطاعم غير النشطة

        Returns:
            RestaurantResponse: بيانات المطعم

        Raises:
            NotFoundError: إذا لم يتم العثور على المطعم
        """
        logger.info(
            "restaurant_service_get_by_id",
            extra={
                "restaurant_id": restaurant_id,
                "include_inactive": include_inactive,
            },
        )

        restaurant = await self.repo.get_by_id(
            id=restaurant_id,
        )

        if not restaurant:
            raise NotFoundError(
                message=f"المطعم بـ ID '{restaurant_id}' غير موجود",
            )

        if not include_inactive and not restaurant.is_active:
            raise NotFoundError(
                message=f"المطعم بـ ID '{restaurant_id}' غير موجود",
            )

        return RestaurantResponse.model_validate(restaurant)

    # ==============================================
    # GET RESTAURANT WITH DETAILS
    # ==============================================

    async def get_restaurant_with_details(
        self,
        *,
        restaurant_id: int,
    ) -> RestaurantResponse:
        """
        الحصول على مطعم مع جميع علاقاته.

        Args:
            restaurant_id: معرف المطعم

        Returns:
            RestaurantResponse: بيانات المطعم مع العلاقات

        Raises:
            NotFoundError: إذا لم يتم العثور على المطعم
        """
        logger.info(
            "restaurant_service_get_with_details",
            extra={"restaurant_id": restaurant_id},
        )

        restaurant = await self.repo.get_with_relations(
            restaurant_id=restaurant_id,
        )

        if not restaurant:
            raise NotFoundError(
                message=f"المطعم بـ ID '{restaurant_id}' غير موجود",
            )

        return RestaurantResponse.model_validate(restaurant)

    # ==============================================
    # GET OWNER RESTAURANTS
    # ==============================================

    async def get_owner_restaurants(
        self,
        *,
        owner_id: int,
        skip: int = 0,
        limit: int = 100,
        include_inactive: bool = False,
    ) -> List[RestaurantResponse]:
        """
        الحصول على مطاعم المالك.

        Args:
            owner_id: معرف المالك
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            include_inactive: تضمين المطاعم غير النشطة

        Returns:
            List[RestaurantResponse]: قائمة المطاعم
        """
        logger.info(
            "restaurant_service_get_by_owner",
            extra={
                "owner_id": owner_id,
                "skip": skip,
                "limit": limit,
                "include_inactive": include_inactive,
            },
        )

        restaurants = await self.repo.get_by_owner_id(
            owner_id=owner_id,
            skip=skip,
            limit=limit,
            include_inactive=include_inactive,
        )

        return [RestaurantResponse.model_validate(r) for r in restaurants]

    # ==============================================
    # GET RESTAURANTS BY WILAYA
    # ==============================================

    async def get_restaurants_by_wilaya(
        self,
        *,
        wilaya: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[RestaurantResponse]:
        """
        الحصول على مطاعم حسب الولاية.

        Args:
            wilaya: الولاية
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            List[RestaurantResponse]: قائمة المطاعم
        """
        logger.info(
            "restaurant_service_get_by_wilaya",
            extra={
                "wilaya": wilaya,
                "skip": skip,
                "limit": limit,
            },
        )

        restaurants = await self.repo.get_by_wilaya(
            wilaya=wilaya,
            skip=skip,
            limit=limit,
        )

        return [RestaurantResponse.model_validate(r) for r in restaurants]

    # ==============================================
    # SEARCH RESTAURANTS
    # ==============================================

    async def search_restaurants(
        self,
        *,
        query: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[RestaurantResponse]:
        """
        البحث عن مطاعم.

        Args:
            query: نص البحث
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            List[RestaurantResponse]: قائمة المطاعم المطابقة للبحث
        """
        logger.info(
            "restaurant_service_search",
            extra={
                "query": query,
                "skip": skip,
                "limit": limit,
            },
        )

        restaurants = await self.repo.search(
            query=query,
            skip=skip,
            limit=limit,
        )

        return [RestaurantResponse.model_validate(r) for r in restaurants]

    # ==============================================
    # COUNT SEARCH RESTAURANTS
    # ==============================================

    async def count_search_restaurants(
        self,
        *,
        query: str,
        include_inactive: bool = False,
    ) -> int:
        """عدد المطاعم المطابقة للنص قبل الترقيم."""
        return await self.repo.count_search(
            query=query,
            include_inactive=include_inactive,
        )

    # ==============================================
    # GET ALL RESTAURANTS
    # ==============================================

    async def get_all_restaurants(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        only_active: bool = True,
    ) -> List[RestaurantResponse]:
        """
        الحصول على جميع المطاعم.

        Args:
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            only_active: جلب المطاعم النشطة فقط

        Returns:
            List[RestaurantResponse]: قائمة المطاعم
        """
        logger.info(
            "restaurant_service_get_all",
            extra={
                "skip": skip,
                "limit": limit,
                "only_active": only_active,
            },
        )

        filters = {}
        if only_active:
            filters["is_active"] = True

        restaurants = await self.repo.get_all(
            skip=skip,
            limit=limit,
            filters=filters,
            order_by="name",
        )

        return [RestaurantResponse.model_validate(r) for r in restaurants]

    # ==========================================
    # 📊 STATISTICS
    # ==========================================

    # ==============================================
    # COUNT OWNER RESTAURANTS
    # ==============================================

    async def count_owner_restaurants(
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
        return await self.repo.count_by_owner(owner_id=owner_id)

    # ==============================================
    # COUNT ALL RESTAURANTS
    # ==============================================

    async def count_all_restaurants(
        self,
        *,
        only_active: bool = True,
    ) -> int:
        """عدد كل المطاعم بعد تطبيق الفلاتر قبل الترقيم."""
        filters = {}
        if only_active:
            filters["is_active"] = True
        return await self.repo.count(filters=filters)

    # ==============================================
    # COUNT RESTAURANTS BY WILAYA
    # ==============================================

    async def count_restaurants_by_wilaya(
        self,
        *,
        wilaya: str,
    ) -> int:
        """
        حساب عدد المطاعم في الولاية.

        Args:
            wilaya: الولاية

        Returns:
            int: عدد المطاعم
        """
        return await self.repo.count_by_wilaya(wilaya=wilaya)

    # ==============================================
    # CHECK OWNER EXISTS
    # ==============================================

    async def _check_owner_exists(
        self,
        *,
        owner_id: int,
    ) -> None:
        """
        التحقق من وجود المالك.

        ✅ يستخدم BASE SELECT للتحقق من وجود المالك

        Args:
            owner_id: معرف المالك

        Raises:
            NotFoundError: إذا لم يتم العثور على المالك
        """
        result = await self.session.execute(
            select(Owner.id).where(Owner.id == owner_id).limit(1),
        )

        owner_exists = result.scalar_one_or_none()

        if owner_exists is None:
            raise NotFoundError(
                message=f"المالك بـ ID '{owner_id}' غير موجود",
            )

    # ==============================================
    # GET RESTAURANT STATISTICS
    # ==============================================

    async def get_restaurant_statistics(
        self,
        *,
        owner_id: Optional[int] = None,
        restaurant_id: Optional[int] = None,
    ) -> RestaurantStats:
        """
        الحصول على إحصائيات المطاعم.

        ✅ يدعم الفلترة بـ owner_id أو restaurant_id
        ✅ يتحقق من وجود المالك عند استخدام owner_id

        Args:
            owner_id: معرف المالك (اختياري)
            restaurant_id: معرف المطعم (اختياري)

        Returns:
            RestaurantStats: إحصائيات المطاعم

        Raises:
            NotFoundError: إذا لم يتم العثور على المالك أو المطعم
        """
        logger.info(
            "restaurant_service_get_statistics",
            extra={
                "owner_id": owner_id,
                "restaurant_id": restaurant_id,
            },
        )

        # ✅ التحقق من وجود المالك عند استخدام owner_id
        if owner_id is not None:
            await self._check_owner_exists(owner_id=owner_id)

        filters: Dict[str, Any] = {}

        if owner_id is not None:
            filters["owner_id"] = owner_id

        if restaurant_id is not None:
            filters["id"] = restaurant_id

        all_restaurants = await self.repo.get_all(
            filters=filters,
            limit=10000,
        )

        # ✅ التحقق من وجود المطعم عند استخدام restaurant_id
        if restaurant_id is not None and not all_restaurants:
            raise NotFoundError(
                message=f"المطعم بـ ID '{restaurant_id}' غير موجود",
            )

        total = len(all_restaurants)
        active = len([r for r in all_restaurants if r.is_active])
        inactive = total - active

        # توزيع المطاعم حسب النوع
        type_distribution: Dict[str, int] = {}

        for restaurant in all_restaurants:
            rest_type = restaurant.type or "unknown"
            type_distribution[rest_type] = type_distribution.get(rest_type, 0) + 1

        # توزيع المطاعم حسب الولاية
        wilaya_distribution: Dict[str, int] = {}

        for restaurant in all_restaurants:
            wilaya = restaurant.wilaya or "unknown"
            wilaya_distribution[wilaya] = wilaya_distribution.get(wilaya, 0) + 1

        return RestaurantStats(
            total_restaurants=total,
            active_restaurants=active,
            inactive_restaurants=inactive,
            type_distribution=type_distribution,
            wilaya_distribution=wilaya_distribution,
        )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "RestaurantService",
    "RestaurantData",
    "RestaurantUpdateData",
    "RestaurantList",
]
