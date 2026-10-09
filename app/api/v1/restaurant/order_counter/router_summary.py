# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🔢 RESTAURANT ORDER COUNTER ROUTER - SUMMARY
# نقاط نهاية الملخص والتنسيق
# ==============================================

"""MoulAI operational module for router summary.

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
    OrderCounterSummary,
    OrderNumberFormat,
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
# GET ORDER COUNTER SUMMARY
# ==============================================


@router.get(
    "/{restaurant_id}/summary",
    response_model=OrderCounterSummary,
    summary="ملخص عداد طلبات المطعم",
    description="الحصول على ملخص عداد طلبات مطعم معين",
)
async def get_order_counter_summary(
    *,
    restaurant_id: int = Path(..., ge=1, description="معرف المطعم"),
    service: RestaurantOrderCounterService = Depends(get_order_counter_service),
) -> OrderCounterSummary:
    """الحصول على ملخص عداد طلبات مطعم معين."""
    logger.info(
        "api_get_order_counter_summary",
        extra={"restaurant_id": restaurant_id},
    )

    try:
        return await service.get_counter_summary(restaurant_id=restaurant_id)

    except Exception as e:
        logger.exception(
            "api_get_order_counter_summary_error",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب ملخص عداد الطلبات",
        )


# ==============================================
# GET ORDER NUMBER FORMAT
# ==============================================


@router.get(
    "/{restaurant_id}/format",
    response_model=OrderNumberFormat,
    summary="تنسيق رقم الطلب",
    description="الحصول على تنسيق رقم الطلب لمطعم معين",
)
async def get_order_number_format(
    *,
    restaurant_id: int = Path(..., ge=1, description="معرف المطعم"),
    service: RestaurantOrderCounterService = Depends(get_order_counter_service),
) -> OrderNumberFormat:
    """الحصول على تنسيق رقم الطلب لمطعم معين."""
    logger.info(
        "api_get_order_number_format",
        extra={"restaurant_id": restaurant_id},
    )

    try:
        # الحصول على العداد
        counter = await service.get_counter(restaurant_id=restaurant_id)

        # بناء تنسيق رقم الطلب
        sequence = counter.last_number + 1
        example = service.build_order_number(
            restaurant_id=restaurant_id,
            sequence=sequence,
        )

        return OrderNumberFormat(
            restaurant_id=restaurant_id,
            prefix=f"RST{restaurant_id}-",
            sequence=sequence,
            format="RST{restaurant_id}-{sequence:06d}",
            example=example,
        )

    except NotFoundError as e:
        logger.warning(
            "api_order_counter_not_found_for_format",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_get_order_number_format_error",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب تنسيق رقم الطلب",
        )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "router",
]
