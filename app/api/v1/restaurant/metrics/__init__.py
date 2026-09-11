# ==============================================
# MoulAI Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine
# ==============================================

# ==============================================
# 📊 RESTAURANT METRICS API
# ==============================================

from fastapi import APIRouter

from app.api.v1.restaurant.metrics.metrics_router import router as metrics_basic_router
from app.api.v1.restaurant.metrics.metrics_summary_router import router as metrics_summary_router
from app.api.v1.restaurant.metrics.metrics_products_router import router as metrics_products_router
from app.api.v1.restaurant.metrics.metrics_trend_router import router as metrics_trend_router
from app.api.v1.restaurant.metrics.metrics_test_router import router as metrics_test_router


# ==============================================
# 📋 MAIN ROUTER
# ==============================================

router = APIRouter()

router.include_router(metrics_basic_router)
router.include_router(metrics_summary_router)
router.include_router(metrics_products_router)
router.include_router(metrics_trend_router)
router.include_router(metrics_test_router)


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "router",
]