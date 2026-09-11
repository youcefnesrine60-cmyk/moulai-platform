# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🔗 RESTAURANT BRANCHES API
# ==============================================

from fastapi import APIRouter

from app.api.v1.restaurant.branches.router import router as basic_router
from app.api.v1.restaurant.branches.router_list import router as list_router
from app.api.v1.restaurant.branches.router_delete import router as delete_router


# ==============================================
# 📋 MAIN ROUTER
# ==============================================

router = APIRouter()

router.include_router(basic_router)
router.include_router(list_router)
router.include_router(delete_router)


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "router",
]