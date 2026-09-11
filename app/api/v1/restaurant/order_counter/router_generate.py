# ==============================================
# MoulAI Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine
# ==============================================

# ==============================================
# 🔢 RESTAURANT ORDER COUNTER ROUTER - GENERATE
# نقاط نهاية توليد رقم الطلب التالي
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
from app.schemas.restaurant.restaurant_order_counter import (
    NextOrderNumberResponse,
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
# GENERATE NEXT ORDER NUMBER
# ==============================================

@router.post(
    "/{restaurant_id}/next",
    response_model=NextOrderNumberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="توليد رقم الطلب التالي",
    description="توليد رقم الطلب التالي لمطعم معين",
)
async def generate_next_order_number(
    *,
    restaurant_id: int = Path(..., ge=1, description="معرف المطعم"),
    service: RestaurantOrderCounterService = Depends(get_order_counter_service),
) -> NextOrderNumberResponse:
    """توليد رقم الطلب التالي لمطعم معين."""
    logger.info(
        "api_generate_next_order_number",
        extra={"restaurant_id": restaurant_id},
    )

    try:
        return await service.generate_next_order_number(
            restaurant_id=restaurant_id,
        )

    except NotFoundError as e:
        logger.warning(
            "api_order_counter_not_found_for_generate",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_generate_next_order_number_error",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء توليد رقم الطلب التالي",
        )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "router",
]