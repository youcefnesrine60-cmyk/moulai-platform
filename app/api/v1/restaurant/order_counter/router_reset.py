# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🔢 RESTAURANT ORDER COUNTER ROUTER - RESET & INCREMENT
# نقاط نهاية إعادة التعيين والزيادة
# ==============================================

"""MoulAI operational module for router reset.

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
from app.core.exceptions import NotFoundError
from app.core.logger import logger
from app.schemas.restaurant.restaurant_order_counter import (
    RestaurantOrderCounterResponse,
)
from app.services.business.restaurant.order_counter.service import (
    RestaurantOrderCounterService,
)

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
# 📋 ENDPOINTS
# ==============================================

# ==============================================
# RESET ORDER COUNTER
# ==============================================


@router.post(
    "/{restaurant_id}/reset",
    response_model=RestaurantOrderCounterResponse,
    summary="إعادة تعيين عداد طلبات المطعم",
    description="إعادة تعيين عداد طلبات المطعم إلى الصفر",
)
async def reset_order_counter(
    *,
    restaurant_id: int = Path(..., ge=1, description="معرف المطعم"),
    service: RestaurantOrderCounterService = Depends(get_order_counter_service),
) -> RestaurantOrderCounterResponse:
    """إعادة تعيين عداد طلبات المطعم إلى الصفر."""
    logger.info(
        "api_reset_order_counter",
        extra={"restaurant_id": restaurant_id},
    )

    try:
        return await service.reset_counter(restaurant_id=restaurant_id)

    except NotFoundError as e:
        logger.warning(
            "api_order_counter_not_found_for_reset",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_reset_order_counter_error",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إعادة تعيين عداد الطلبات",
        )


# ==============================================
# INCREMENT ORDER COUNTER
# ==============================================


@router.post(
    "/{restaurant_id}/increment",
    response_model=RestaurantOrderCounterResponse,
    summary="زيادة عداد طلبات المطعم",
    description="زيادة عداد طلبات المطعم بمقدار 1",
)
async def increment_order_counter(
    *,
    restaurant_id: int = Path(..., ge=1, description="معرف المطعم"),
    service: RestaurantOrderCounterService = Depends(get_order_counter_service),
) -> RestaurantOrderCounterResponse:
    """زيادة عداد طلبات المطعم بمقدار 1."""
    logger.info(
        "api_increment_order_counter",
        extra={"restaurant_id": restaurant_id},
    )

    try:
        return await service.increment_counter(restaurant_id=restaurant_id)

    except NotFoundError as e:
        logger.warning(
            "api_order_counter_not_found_for_increment",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_increment_order_counter_error",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء زيادة عداد الطلبات",
        )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "router",
]
