# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HANDLERS / CALLBACKS / RESTAURANT / ROUTER
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for router.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.logger import logger
from app.core.router_instance import router

from app.handlers.callbacks.restaurant.details import restaurant_details_callback
from app.handlers.callbacks.restaurant.menu import restaurant_menu_callback

# ==============================================
# 🚀 REGISTER RESTAURANT ROUTES
# ==============================================


async def register_restaurant_routes() -> None:
    """
    تسجيل جميع مسارات المطعم في الـ Router
    """
    logger.info(
        "registering_restaurant_routes",
    )

    # 🍽️ تفاصيل المطعم
    router.register(
        pattern=r"^restaurant_details_(\d+)$",
        handler=restaurant_details_callback,
    )

    # 📋 قائمة المطعم
    router.register(
        pattern=r"^restaurant_menu_(\d+)$",
        handler=restaurant_menu_callback,
    )

    logger.info(
        "restaurant_routes_registered",
    )
