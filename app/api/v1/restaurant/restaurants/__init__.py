# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine
# ==============================================

# ==============================================
# 🍽️ RESTAURANT API
# ==============================================

from fastapi import APIRouter

from app.api.v1.restaurant.restaurants.restaurant_router import router as basic_router
from app.api.v1.restaurant.restaurants.restaurant_status_router import router as status_router
from app.api.v1.restaurant.restaurants.restaurant_stats_router import router as stats_router
from app.api.v1.restaurant.restaurants.restaurant_list_router import router as list_router


# ==============================================
# 📋 MAIN ROUTER
# ==============================================

router = APIRouter()

router.include_router(basic_router)
router.include_router(status_router)
router.include_router(stats_router)
router.include_router(list_router)


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "router",
]