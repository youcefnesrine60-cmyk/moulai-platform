# ==============================================
# MoulAI Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine
# ==============================================

# ==============================================
# 🏢 RESTAURANT GROUPS API
# ==============================================

from fastapi import APIRouter

from app.api.v1.restaurant.groups.router import router as basic_router
from app.api.v1.restaurant.groups.router_status import router as status_router
from app.api.v1.restaurant.groups.router_statistics import router as statistics_router
from app.api.v1.restaurant.groups.router_branches import router as branches_router


# ==============================================
# 📋 MAIN ROUTER
# ==============================================

router = APIRouter()

router.include_router(basic_router)
router.include_router(status_router)
router.include_router(statistics_router)
router.include_router(branches_router)


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "router",
]