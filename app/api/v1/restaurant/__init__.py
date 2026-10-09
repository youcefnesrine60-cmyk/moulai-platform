# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🍽️ RESTAURANT API - PACKAGE INIT
# ==============================================

"""Package initializer and public module exports.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from fastapi import APIRouter

# ==============================================
# 📦 IMPORT SUB-ROUTERS
# ==============================================

# Restaurants
from app.api.v1.restaurant.restaurants import router as restaurants_router

# Metrics
from app.api.v1.restaurant.metrics import router as metrics_router

# Order Counter
from app.api.v1.restaurant.order_counter import router as order_counter_router

# Payment Settings
from app.api.v1.restaurant.payment_setting import router as payment_setting_router

# Groups
from app.api.v1.restaurant.groups import router as groups_router

# Branches
from app.api.v1.restaurant.branches import router as branches_router

# ==============================================
# 📋 MAIN ROUTER
# ==============================================

router = APIRouter()

router.include_router(restaurants_router)
router.include_router(metrics_router)
router.include_router(order_counter_router)
router.include_router(payment_setting_router)
router.include_router(groups_router)
router.include_router(branches_router)


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "router",
]
