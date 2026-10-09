# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🔢 RESTAURANT ORDER COUNTER API
# ==============================================

"""Package initializer and public module exports.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from fastapi import APIRouter

from app.api.v1.restaurant.order_counter.router import router as basic_router
from app.api.v1.restaurant.order_counter.router_initialize import (
    router as initialize_router,
)
from app.api.v1.restaurant.order_counter.router_generate import (
    router as generate_router,
)
from app.api.v1.restaurant.order_counter.router_summary import router as summary_router
from app.api.v1.restaurant.order_counter.router_reset import router as reset_router

# ==============================================
# 📋 MAIN ROUTER
# ==============================================

router = APIRouter()

router.include_router(basic_router)
router.include_router(initialize_router)
router.include_router(generate_router)
router.include_router(summary_router)
router.include_router(reset_router)


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "router",
]
