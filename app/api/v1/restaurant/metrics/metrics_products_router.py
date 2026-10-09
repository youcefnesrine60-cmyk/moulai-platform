# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📊 RESTAURANT METRICS ROUTER - PRODUCTS
# نقاط نهاية مقاييس المنتجات
# ==============================================

"""MoulAI operational module for metrics products router.

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
from app.repositories.products_repo import ProductRepository
from app.schemas.restaurant.restaurant_metric import ProductMetrics
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
# GET PRODUCT METRICS
# ==============================================


@router.get(
    "/{restaurant_id}/products",
    response_model=ProductMetrics,
    summary="مقاييس المنتجات",
    description="الحصول على مقاييس المنتجات لمطعم معين",
)
async def get_product_metrics(
    *,
    restaurant_id: int = Path(..., ge=1, description="معرف المطعم"),
    service: RestaurantMetricsService = Depends(get_metrics_service),
) -> ProductMetrics:
    """الحصول على مقاييس المنتجات لمطعم معين."""
    logger.info(
        "api_get_product_metrics",
        extra={"restaurant_id": restaurant_id},
    )

    try:
        # الحصول على المقاييس
        await service.get_metrics(restaurant_id=restaurant_id)

        # جلب المنتجات الفعلية لحساب الأسعار
        product_repo = ProductRepository(service.session)
        products = await product_repo.get_by_restaurant_id(
            restaurant_id=restaurant_id,
            only_available=False,
        )

        total_products = len(products)
        available_products = sum(1 for product in products if product.is_available)
        unavailable_products = total_products - available_products

        prices = [product.price for product in products] if products else [0]

        return ProductMetrics(
            restaurant_id=restaurant_id,
            total_products=total_products,
            available_products=available_products,
            unavailable_products=unavailable_products,
            most_expensive=max(prices) if prices else 0,
            least_expensive=min(prices) if prices else 0,
            avg_price=sum(prices) / len(prices) if prices else 0,
        )

    except NotFoundError as e:
        logger.warning(
            "api_restaurant_metrics_not_found_for_products",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_get_product_metrics_error",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب مقاييس المنتجات",
        )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "router",
]
