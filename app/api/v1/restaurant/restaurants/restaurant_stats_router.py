# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🍽️ RESTAURANT ROUTER - STATS
# نقاط نهاية الإحصائيات
# ==============================================

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Path,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.core.logger import logger
from app.schemas.restaurant import RestaurantStats
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
    """
    الحصول على خدمة المطاعم.
    
    Args:
        session: جلسة قاعدة البيانات
        
    Returns:
        RestaurantService: خدمة المطاعم
    """
    return RestaurantService(session)


# ==============================================
# 📋 ENDPOINTS
# ==============================================

# ==============================================
# GET RESTAURANT STATS
# ==============================================

@router.get(
    "/{restaurant_id}/stats",
    response_model=RestaurantStats,
    summary="إحصائيات المطعم",
    description="الحصول على إحصائيات المطعم",
)
async def get_restaurant_stats(
    *,
    restaurant_id: int = Path(..., ge=1, description="معرف المطعم"),
    service: RestaurantService = Depends(get_restaurant_service),
) -> RestaurantStats:
    """
    الحصول على إحصائيات المطعم.
    
    Args:
        restaurant_id: معرف المطعم
        service: خدمة المطاعم
        
    Returns:
        RestaurantStats: إحصائيات المطعم
        
    Raises:
        HTTPException: إذا لم يتم العثور على المطعم
    """
    logger.info(
        "api_get_restaurant_stats",
        extra={"restaurant_id": restaurant_id},
    )

    try:
        return await service.get_restaurant_statistics(
            restaurant_id=restaurant_id,
        )

    except NotFoundError as e:
        logger.warning(
            "api_restaurant_not_found_for_stats",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_get_restaurant_stats_error",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب إحصائيات المطعم",
        )


# ==============================================
# GET OWNER RESTAURANTS STATS
# ==============================================

@router.get(
    "/stats/{owner_id}",
    response_model=RestaurantStats,
    summary="إحصائيات مطاعم المالك",
    description="الحصول على إحصائيات مطاعم مالك معين",
)
async def get_owner_restaurants_stats(
    *,
    owner_id: int = Path(..., ge=1, description="معرف المالك"),
    service: RestaurantService = Depends(get_restaurant_service),
) -> RestaurantStats:
    """
    الحصول على إحصائيات مطاعم مالك معين.
    
    Args:
        owner_id: معرف المالك
        service: خدمة المطاعم
        
    Returns:
        RestaurantStats: إحصائيات مطاعم المالك
        
    Raises:
        HTTPException: إذا لم يتم العثور على المالك
    """
    logger.info(
        "api_get_owner_restaurants_stats",
        extra={"owner_id": owner_id},
    )

    try:
        return await service.get_restaurant_statistics(owner_id=owner_id)

    except NotFoundError as e:
        # ✅ معالجة NotFoundError بشكل صحيح
        logger.warning(
            "api_owner_not_found_for_stats",
            extra={"owner_id": owner_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_get_owner_restaurants_stats_error",
            extra={"owner_id": owner_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب إحصائيات مطاعم المالك",
        )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "router",
]