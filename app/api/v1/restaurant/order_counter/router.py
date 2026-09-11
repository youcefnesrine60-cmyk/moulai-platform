# ==============================================
# MoulAI Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine
# ==============================================

# ==============================================
# 🔢 RESTAURANT ORDER COUNTER ROUTER - BASIC
# نقاط نهاية عداد طلبات المطعم الأساسية
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
from app.core.exceptions import (
    NotFoundError,
    ValidationError,
)
from app.core.logger import logger
from app.schemas.restaurant.restaurant_order_counter import (
    RestaurantOrderCounterResponse,
    RestaurantOrderCounterUpdate,
    RestaurantOrderCounterListResponse,
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
# LIST ORDER COUNTERS
# ==============================================

@router.get(
    "/",
    response_model=RestaurantOrderCounterListResponse,
    summary="قائمة عدادات الطلبات",
    description="الحصول على قائمة عدادات طلبات المطاعم",
)
async def list_order_counters(
    *,
    skip: int = Query(0, ge=0, description="عدد السجلات للتخطي"),
    limit: int = Query(100, ge=1, le=200, description="الحد الأقصى للسجلات"),
    service: RestaurantOrderCounterService = Depends(get_order_counter_service),
) -> RestaurantOrderCounterListResponse:
    """الحصول على قائمة عدادات طلبات المطاعم."""
    logger.info(
        "api_list_order_counters",
        extra={"skip": skip, "limit": limit},
    )

    try:
        counters = await service.repo.get_all(
            skip=skip,
            limit=limit,
            order_by="restaurant_id",
        )
        total = await service.repo.count()

        return RestaurantOrderCounterListResponse(
            items=[RestaurantOrderCounterResponse.model_validate(c) for c in counters],
            total=total,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.exception(
            "api_list_order_counters_error",
            extra={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب قائمة عدادات الطلبات",
        )


# ==============================================
# GET ORDER COUNTER
# ==============================================

@router.get(
    "/{restaurant_id}",
    response_model=RestaurantOrderCounterResponse,
    summary="عداد طلبات المطعم",
    description="الحصول على عداد طلبات مطعم معين",
)
async def get_order_counter(
    *,
    restaurant_id: int = Path(..., ge=1, description="معرف المطعم"),
    service: RestaurantOrderCounterService = Depends(get_order_counter_service),
) -> RestaurantOrderCounterResponse:
    """الحصول على عداد طلبات مطعم معين."""
    logger.info(
        "api_get_order_counter",
        extra={"restaurant_id": restaurant_id},
    )

    try:
        return await service.get_counter(restaurant_id=restaurant_id)

    except NotFoundError as e:
        logger.warning(
            "api_order_counter_not_found",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_get_order_counter_error",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب عداد الطلبات",
        )


# ==============================================
# UPDATE ORDER COUNTER
# ==============================================

@router.patch(
    "/{restaurant_id}",
    response_model=RestaurantOrderCounterResponse,
    summary="تحديث عداد طلبات المطعم",
    description="تحديث عداد طلبات مطعم معين",
)
async def update_order_counter(
    *,
    restaurant_id: int = Path(..., ge=1, description="معرف المطعم"),
    data: RestaurantOrderCounterUpdate,
    service: RestaurantOrderCounterService = Depends(get_order_counter_service),
) -> RestaurantOrderCounterResponse:
    """تحديث عداد طلبات مطعم معين."""
    logger.info(
        "api_update_order_counter",
        extra={
            "restaurant_id": restaurant_id,
            "fields": list(data.model_dump(exclude_unset=True).keys()),
        },
    )

    try:
        return await service.update_counter(
            restaurant_id=restaurant_id,
            update_data=data,
        )

    except NotFoundError as e:
        logger.warning(
            "api_order_counter_not_found_for_update",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_update_order_counter_validation_error",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_update_order_counter_error",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث عداد الطلبات",
        )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "router",
]