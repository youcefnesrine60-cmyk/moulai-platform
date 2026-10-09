# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🔢 RESTAURANT ORDER COUNTER ROUTER - INITIALIZE
# نقاط نهاية تهيئة عداد طلبات المطعم
# ==============================================

"""MoulAI operational module for router initialize.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Path,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
)
from app.core.logger import logger
from app.schemas.restaurant.restaurant_order_counter import (
    RestaurantOrderCounterResponse,
)
from app.services.business.restaurant.order_counter.service import (
    RestaurantOrderCounterService,
)
from app.services.business.restaurant.restaurants.service import RestaurantService

# ==============================================
# 🏗️ ROUTER
# ==============================================

router = APIRouter(
    prefix="/restaurant-order-counters",
    tags=["Restaurant Order Counters"],
)


# ==============================================
# 🔧 DEPENDENCIES
# ==============================================


async def get_order_counter_service(
    session: AsyncSession = Depends(get_db),
) -> RestaurantOrderCounterService:
    """الحصول على خدمة عداد طلبات المطعم."""
    return RestaurantOrderCounterService(session)


# ==============================================
# GET RESTAURANT SERVICE
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
# INITIALIZE ORDER COUNTER
# ==============================================


@router.post(
    "/{restaurant_id}/initialize",
    response_model=RestaurantOrderCounterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="تهيئة عداد طلبات المطعم",
    description="تهيئة عداد طلبات جديد لمطعم",
)
async def initialize_order_counter(
    *,
    restaurant_id: int = Path(..., ge=1, description="معرف المطعم"),
    service: RestaurantOrderCounterService = Depends(get_order_counter_service),
    restaurant_service: RestaurantService = Depends(get_restaurant_service),
) -> RestaurantOrderCounterResponse:
    """تهيئة عداد طلبات جديد لمطعم."""
    logger.info(
        "api_initialize_order_counter",
        extra={"restaurant_id": restaurant_id},
    )

    try:
        # ✅ التحقق من وجود المطعم (بما في ذلك غير النشط)
        await restaurant_service.get_restaurant(
            restaurant_id=restaurant_id,
            include_inactive=True,
        )

        # تهيئة العداد
        return await service.initialize_counter(restaurant_id=restaurant_id)

    except NotFoundError as e:
        logger.warning(
            "api_restaurant_not_found_for_counter",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ConflictError as e:
        logger.warning(
            "api_order_counter_already_exists",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_initialize_order_counter_error",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تهيئة عداد الطلبات",
        )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "router",
]
