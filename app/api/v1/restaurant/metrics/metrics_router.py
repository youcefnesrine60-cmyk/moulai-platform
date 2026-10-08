# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📊 RESTAURANT METRICS ROUTER - BASIC
# نقاط نهاية المقاييس الأساسية
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
from app.core.exceptions import (
    NotFoundError,
    ValidationError,
)
from app.core.logger import logger
from app.schemas.restaurant.restaurant_metric import (
    RestaurantMetricResponse,
    RestaurantMetricUpdate,
)
from app.services.business.restaurant.metrics.service import RestaurantMetricsService
from app.services.business.restaurant.restaurants.service import RestaurantService


# ==============================================
# 🏗️ ROUTER
# ==============================================

router = APIRouter(
    prefix="/restaurant-metrics",
    tags=["Restaurant Metrics"],
)


# ==============================================
# 🔧 DEPENDENCIES
# ==============================================

async def get_metrics_service(
    session: AsyncSession = Depends(get_db),
) -> RestaurantMetricsService:
    """الحصول على خدمة مقاييس المطعم."""
    return RestaurantMetricsService(session)


async def get_restaurant_service(
    session: AsyncSession = Depends(get_db),
) -> RestaurantService:
    """الحصول على خدمة المطاعم."""
    return RestaurantService(session)


# ==============================================
# 📋 ENDPOINTS
# ==============================================

# ==============================================
# GET RESTAURANT METRICS
# ==============================================

@router.get(
    "/{restaurant_id}",
    response_model=RestaurantMetricResponse,
    summary="مقاييس المطعم",
    description="الحصول على مقاييس مطعم معين",
)
async def get_restaurant_metrics(
    *,
    restaurant_id: int = Path(..., ge=1, description="معرف المطعم"),
    service: RestaurantMetricsService = Depends(get_metrics_service),
) -> RestaurantMetricResponse:
    """الحصول على مقاييس مطعم معين."""
    logger.info(
        "api_get_restaurant_metrics",
        extra={"restaurant_id": restaurant_id},
    )

    try:
        return await service.get_metrics(restaurant_id=restaurant_id)

    except NotFoundError as e:
        logger.warning(
            "api_restaurant_metrics_not_found",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_get_restaurant_metrics_error",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب مقاييس المطعم",
        )


# ==============================================
# UPDATE RESTAURANT METRICS
# ==============================================

@router.patch(
    "/{restaurant_id}",
    response_model=RestaurantMetricResponse,
    summary="تحديث مقاييس المطعم",
    description="تحديث مقاييس مطعم معين",
)
async def update_restaurant_metrics(
    *,
    restaurant_id: int = Path(..., ge=1, description="معرف المطعم"),
    data: RestaurantMetricUpdate,
    service: RestaurantMetricsService = Depends(get_metrics_service),
) -> RestaurantMetricResponse:
    """تحديث مقاييس مطعم معين."""
    logger.info(
        "api_update_restaurant_metrics",
        extra={
            "restaurant_id": restaurant_id,
            "fields": list(data.model_dump(exclude_unset=True).keys()),
        },
    )

    try:
        return await service.update_metrics(
            restaurant_id=restaurant_id,
            update_data=data,
        )

    except NotFoundError as e:
        logger.warning(
            "api_restaurant_metrics_not_found_for_update",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_update_restaurant_metrics_validation_error",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_update_restaurant_metrics_error",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث مقاييس المطعم",
        )


# ==============================================
# INITIALIZE RESTAURANT METRICS
# ==============================================

@router.post(
    "/{restaurant_id}/initialize",
    response_model=RestaurantMetricResponse,
    status_code=status.HTTP_201_CREATED,
    summary="تهيئة مقاييس المطعم",
    description="تهيئة مقاييس جديدة لمطعم",
)
async def initialize_restaurant_metrics(
    *,
    restaurant_id: int = Path(..., ge=1, description="معرف المطعم"),
    service: RestaurantMetricsService = Depends(get_metrics_service),
    restaurant_service: RestaurantService = Depends(get_restaurant_service),
) -> RestaurantMetricResponse:
    """تهيئة مقاييس جديدة لمطعم."""
    logger.info(
        "api_initialize_restaurant_metrics",
        extra={"restaurant_id": restaurant_id},
    )

    try:
        # ✅ التحقق من وجود المطعم (بما في ذلك غير النشط)
        await restaurant_service.get_restaurant(
            restaurant_id=restaurant_id,
            include_inactive=True,
        )

        # تهيئة المقاييس
        return await service.initialize_metrics(restaurant_id=restaurant_id)

    except NotFoundError as e:
        logger.warning(
            "api_restaurant_not_found_for_metrics",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_restaurant_metrics_already_exist",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_initialize_restaurant_metrics_error",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تهيئة مقاييس المطعم",
        )


# ==============================================
# RESET RESTAURANT METRICS
# ==============================================

@router.post(
    "/{restaurant_id}/reset",
    response_model=RestaurantMetricResponse,
    summary="إعادة تعيين مقاييس المطعم",
    description="إعادة تعيين مقاييس المطعم إلى الصفر",
)
async def reset_restaurant_metrics(
    *,
    restaurant_id: int = Path(..., ge=1, description="معرف المطعم"),
    service: RestaurantMetricsService = Depends(get_metrics_service),
) -> RestaurantMetricResponse:
    """إعادة تعيين مقاييس المطعم إلى الصفر."""
    logger.info(
        "api_reset_restaurant_metrics",
        extra={"restaurant_id": restaurant_id},
    )

    try:
        return await service.reset_metrics(restaurant_id=restaurant_id)

    except NotFoundError as e:
        logger.warning(
            "api_restaurant_metrics_not_found_for_reset",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_reset_restaurant_metrics_error",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إعادة تعيين مقاييس المطعم",
        )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "router",
]