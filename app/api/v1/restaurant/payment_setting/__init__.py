# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🏦 RESTAURANT PAYMENT SETTINGS API
# ==============================================

"""Package initializer and public module exports.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from fastapi import APIRouter

from app.api.v1.restaurant.payment_setting.router import router as basic_router
from app.api.v1.restaurant.payment_setting.router_methods import (
    router as methods_router,
)
from app.api.v1.restaurant.payment_setting.router_summary import (
    router as summary_router,
)
from app.api.v1.restaurant.payment_setting.router_single_method import (
    router as single_method_router,
)

# ==============================================
# 📋 MAIN ROUTER
# ==============================================

router = APIRouter()

router.include_router(basic_router)
router.include_router(methods_router)
router.include_router(summary_router)
router.include_router(single_method_router)


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "router",
]
