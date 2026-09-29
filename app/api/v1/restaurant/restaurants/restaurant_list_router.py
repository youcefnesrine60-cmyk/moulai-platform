# ==============================================
# MoulAI Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine
# ==============================================

# ==============================================
# 🍽️ RESTAURANT ROUTER - LIST
# نقاط نهاية القوائم المختلفة
# ==============================================

from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Path,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logger import logger
from app.schemas.restaurant import (
    RestaurantResponse,
    RestaurantListResponse,
)
from app.services.business.restaurant.restaurants.service import RestaurantService


# ==============================================
# 🏗️ ROUTER
# ==============================================

router = APIRouter(
    prefix="/restaurants",
    tags=["Restaurants"],
)


# ==============================================
# 🔧 DEPENDENCIES
# ==============================================

async def get_restaurant_service(
    session: AsyncSession = Depends(get_db),
) -> RestaurantService:
    """الحصول على خدمة المطاعم."""
    return RestaurantService(session)


# ==============================================
# 📋 ENDPOINTS
# ==============================================

# ==============================================
# LIST RESTAURANTS
# ==============================================

@router.get(
    "/",
    response_model=RestaurantListResponse,
    summary="قائمة المطاعم",
    description="الحصول على قائمة المطاعم مع إمكانية التصفية والبحث",
)
async def list_restaurants(
    *,
    owner_id: Optional[int] = Query(None, description="معرف المالك", ge=1),
    wilaya: Optional[str] = Query(None, max_length=100, description="الولاية"),
    search: Optional[str] = Query(None, min_length=1, max_length=255, description="نص البحث"),
    only_active: bool = Query(True, description="جلب المطاعم النشطة فقط"),
    skip: int = Query(0, ge=0, description="عدد السجلات للتخطي"),
    limit: int = Query(100, ge=1, le=200, description="الحد الأقصى للسجلات"),
    service: RestaurantService = Depends(get_restaurant_service),
) -> RestaurantListResponse:
    """الحصول على قائمة المطاعم."""
    logger.info(
        "api_list_restaurants",
        extra={
            "owner_id": owner_id,
            "wilaya": wilaya,
            "search": search,
            "only_active": only_active,
            "skip": skip,
            "limit": limit,
        },
    )

    try:
        # تحديد طريقة الجلب بناءً على معايير التصفية
        if owner_id is not None:
            restaurants = await service.get_owner_restaurants(
                owner_id=owner_id,
                skip=skip,
                limit=limit,
                include_inactive=not only_active,
            )
            total = await service.count_owner_restaurants(owner_id=owner_id)

        elif wilaya is not None:
            restaurants = await service.get_restaurants_by_wilaya(
                wilaya=wilaya,
                skip=skip,
                limit=limit,
            )
            total = await service.count_restaurants_by_wilaya(wilaya=wilaya)

        elif search is not None:
            restaurants = await service.search_restaurants(
                query=search,
                skip=skip,
                limit=limit,
            )
            total = await service.count_search_restaurants(
                query=search,
                include_inactive=not only_active,
            )

        else:
            restaurants = await service.get_all_restaurants(
                skip=skip,
                limit=limit,
                only_active=only_active,
            )
            total = await service.count_all_restaurants(
                only_active=only_active,
            )

        return RestaurantListResponse(
            items=restaurants,
            total=total,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.exception(
            "api_list_restaurants_error",
            extra={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب قائمة المطاعم",
        )


# ==============================================
# GET OWNER RESTAURANTS
# ==============================================

@router.get(
    "/owner/{owner_id}/list",
    response_model=RestaurantListResponse,
    summary="مطاعم المالك",
    description="الحصول على مطاعم مالك معين",
)
async def get_owner_restaurants(
    *,
    owner_id: int = Path(..., ge=1, description="معرف المالك"),
    only_active: bool = Query(True, description="جلب المطاعم النشطة فقط"),
    skip: int = Query(0, ge=0, description="عدد السجلات للتخطي"),
    limit: int = Query(100, ge=1, le=200, description="الحد الأقصى للسجلات"),
    service: RestaurantService = Depends(get_restaurant_service),
) -> RestaurantListResponse:
    """الحصول على مطاعم مالك معين."""
    logger.info(
        "api_get_owner_restaurants",
        extra={
            "owner_id": owner_id,
            "only_active": only_active,
            "skip": skip,
            "limit": limit,
        },
    )

    try:
        restaurants = await service.get_owner_restaurants(
            owner_id=owner_id,
            skip=skip,
            limit=limit,
            include_inactive=not only_active,
        )

        total = await service.count_owner_restaurants(owner_id=owner_id)

        return RestaurantListResponse(
            items=restaurants,
            total=total,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.exception(
            "api_get_owner_restaurants_error",
            extra={"owner_id": owner_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب مطاعم المالك",
        )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "router",
]