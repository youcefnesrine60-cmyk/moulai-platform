# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📊 RESTAURANT METRICS ROUTER - TREND
# نقاط نهاية اتجاهات المقاييس
# ==============================================

"""MoulAI operational module for metrics trend router.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from datetime import datetime
import calendar

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
from app.core.exceptions import NotFoundError
from app.core.logger import logger
from app.schemas.restaurant.restaurant_metric import MetricsTrend
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
# GET METRICS TREND
# ==============================================


@router.get(
    "/{restaurant_id}/trend",
    response_model=MetricsTrend,
    summary="اتجاه المقاييس",
    description="الحصول على اتجاه مقاييس مطعم معين",
)
async def get_metrics_trend(
    *,
    restaurant_id: int = Path(..., ge=1, description="معرف المطعم"),
    period: str = Query(
        "monthly",
        description="الفترة: daily, weekly, monthly",
        pattern="^(daily|weekly|monthly)$",
    ),
    service: RestaurantMetricsService = Depends(get_metrics_service),
) -> MetricsTrend:
    """الحصول على اتجاه مقاييس مطعم معين."""
    logger.info(
        "api_get_metrics_trend",
        extra={
            "restaurant_id": restaurant_id,
            "period": period,
        },
    )

    try:
        # الحصول على المقاييس
        metrics = await service.get_metrics(restaurant_id=restaurant_id)

        # بناء نقاط الاتجاه
        trend_points = []
        total_orders = metrics.monthly_orders or 0
        total_revenue = metrics.average_order_value * total_orders

        now = datetime.now()
        _, days_in_month = calendar.monthrange(now.year, now.month)
        days_to_show = min(days_in_month, 30)

        for day in range(1, days_to_show + 1):
            day_orders = max(1, int(total_orders / 30))
            day_revenue = day_orders * (metrics.average_order_value or 100)

            trend_points.append(
                {
                    "period": f"{now.year}-{now.month:02d}-{day:02d}",
                    "orders_count": day_orders,
                    "revenue": day_revenue,
                    "avg_order_value": metrics.average_order_value or 100,
                }
            )

        return MetricsTrend(
            restaurant_id=restaurant_id,
            trend=trend_points,
            total_orders=total_orders,
            total_revenue=total_revenue,
            overall_avg=metrics.average_order_value or 0,
        )

    except NotFoundError as e:
        logger.warning(
            "api_restaurant_metrics_not_found_for_trend",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_get_metrics_trend_error",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب اتجاه المقاييس",
        )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "router",
]
