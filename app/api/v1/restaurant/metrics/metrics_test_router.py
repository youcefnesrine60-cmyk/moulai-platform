# ==============================================
# MoulAI Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine
# ==============================================

# ==============================================
# 📊 RESTAURANT METRICS ROUTER - TEST
# نقاط نهاية الاختبار والمحاكاة
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
from app.services.business.restaurant.metrics.service import RestaurantMetricsService


# ==============================================
# 🏗️ ROUTER
# ==============================================

router = APIRouter(
    prefix="/restaurant-metrics",
    tags=["Restaurant Metrics - Test"],
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
# SIMULATE ORDER (FOR TESTING)
# ==============================================

@router.post(
    "/{restaurant_id}/simulate-order",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="محاكاة طلب (للاختبار)",
    description="محاكاة طلب جديد لتحديث المقاييس (للاختبار فقط)",
)
async def simulate_order(
    *,
    restaurant_id: int = Path(..., ge=1, description="معرف المطعم"),
    order_total: float = Query(
        100.00,
        gt=0,
        description="قيمة الطلب",
    ),
    service: RestaurantMetricsService = Depends(get_metrics_service),
) -> None:
    """محاكاة طلب جديد لتحديث المقاييس (للاختبار فقط)."""
    logger.info(
        "api_simulate_order",
        extra={
            "restaurant_id": restaurant_id,
            "order_total": order_total,
        },
    )

    try:
        await service.order_registered(
            restaurant_id=restaurant_id,
            order_total=order_total,
        )

    except NotFoundError as e:
        logger.warning(
            "api_restaurant_metrics_not_found_for_simulate",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_simulate_order_validation_error",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_simulate_order_error",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء محاكاة الطلب",
        )

    logger.info(
        "api_simulate_order_successful",
        extra={
            "restaurant_id": restaurant_id,
            "order_total": order_total,
        },
    )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "router",
]