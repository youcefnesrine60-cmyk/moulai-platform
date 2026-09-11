# ==============================================
# MoulAI Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine
# ==============================================

# ==============================================
# 📊 RESTAURANT METRICS ROUTER - SUMMARY
# نقاط نهاية الملخص والإحصائيات
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
from app.schemas.restaurant.restaurant_metric import (
    RestaurantMetricSummary,
)
from app.services.business.restaurant.metrics.service import RestaurantMetricsService


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


# ==============================================
# 📋 ENDPOINTS
# ==============================================

# ==============================================
# GET RESTAURANT METRICS SUMMARY
# ==============================================

@router.get(
    "/{restaurant_id}/summary",
    response_model=RestaurantMetricSummary,
    summary="ملخص مقاييس المطعم",
    description="الحصول على ملخص مقاييس مطعم معين",
)
async def get_restaurant_metrics_summary(
    *,
    restaurant_id: int = Path(..., ge=1, description="معرف المطعم"),
    service: RestaurantMetricsService = Depends(get_metrics_service),
) -> RestaurantMetricSummary:
    """الحصول على ملخص مقاييس مطعم معين."""
    logger.info(
        "api_get_restaurant_metrics_summary",
        extra={"restaurant_id": restaurant_id},
    )

    try:
        return await service.get_metrics_summary(restaurant_id=restaurant_id)

    except NotFoundError as e:
        logger.warning(
            "api_restaurant_metrics_not_found_for_summary",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_get_restaurant_metrics_summary_error",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب ملخص مقاييس المطعم",
        )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "router",
]