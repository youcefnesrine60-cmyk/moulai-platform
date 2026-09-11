# ==============================================
# MoulAI Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine
# ==============================================

# ==============================================
# 🏢 RESTAURANT GROUPS ROUTER - STATISTICS
# نقاط نهاية إحصائيات مجموعات المطاعم
# ==============================================

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
from app.schemas.restaurant.restaurant_group import (
    RestaurantGroupListResponse,
    RestaurantGroupStatistics,
)
from app.services.business.restaurant.groups.service import RestaurantGroupService


# ==============================================
# 🏗️ ROUTER
# ==============================================

router = APIRouter(
    prefix="/restaurant-groups",
    tags=["🏢 Restaurant Groups"],
)


# ==============================================
# 🔧 DEPENDENCIES
# ==============================================

async def get_restaurant_group_service(
    session: AsyncSession = Depends(get_db),
) -> RestaurantGroupService:
    """الحصول على خدمة مجموعات المطاعم."""
    return RestaurantGroupService(session)


# ==============================================
# 📋 ENDPOINTS
# ==============================================

# ==============================================
# GET GROUP STATISTICS
# ==============================================

@router.get(
    "/statistics/{owner_id}",
    response_model=RestaurantGroupStatistics,
    summary="إحصائيات مجموعات المطاعم",
    description="الحصول على إحصائيات مجموعات المطاعم لمالك محدد",
)
async def get_restaurant_group_statistics(
    *,
    owner_id: int = Path(..., ge=1, description="معرف المالك"),
    service: RestaurantGroupService = Depends(get_restaurant_group_service),
) -> RestaurantGroupStatistics:
    """الحصول على إحصائيات مجموعات المطاعم لمالك معين."""
    logger.info(
        "api_get_restaurant_group_statistics",
        extra={"owner_id": owner_id},
    )

    try:
        return await service.get_statistics(owner_id=owner_id)

    except Exception as e:
        logger.exception(
            "api_get_restaurant_group_statistics_error",
            extra={"owner_id": owner_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب إحصائيات مجموعات المطاعم",
        )


# ==============================================
# GET GROUPS WITH RESTAURANTS
# ==============================================

@router.get(
    "/owner/{owner_id}/with-restaurants",
    response_model=RestaurantGroupListResponse,
    summary="قائمة مجموعات مطاعم مع المطاعم",
    description="الحصول على قائمة مجموعات المطاعم مع المطاعم التابعة لها",
)
async def get_restaurant_groups_with_restaurants(
    *,
    owner_id: int = Path(..., ge=1, description="معرف المالك"),
    skip: int = Query(0, ge=0, description="عدد السجلات للتخطي"),
    limit: int = Query(100, ge=1, le=200, description="الحد الأقصى للسجلات"),
    service: RestaurantGroupService = Depends(get_restaurant_group_service),
) -> RestaurantGroupListResponse:
    """الحصول على مجموعات المطاعم مع المطاعم التابعة لها."""
    logger.info(
        "api_get_restaurant_groups_with_restaurants",
        extra={
            "owner_id": owner_id,
            "skip": skip,
            "limit": limit,
        },
    )

    try:
        return await service.get_with_restaurants(
            owner_id=owner_id,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.exception(
            "api_get_restaurant_groups_with_restaurants_error",
            extra={"owner_id": owner_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب مجموعات المطاعم مع المطاعم",
        )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "router",
]