# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HANDLERS / CALLBACKS / ORDER / ROUTER
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for router.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.logger import logger
from app.core.router_instance import router

from app.handlers.callbacks.customer.order import order_details_callback

# ==============================================
# 🚀 REGISTER ORDER ROUTES
# ==============================================


async def register_order_routes() -> None:
    """
    تسجيل جميع مسارات الطلبات في الـ Router
    """
    logger.info(
        "registering_order_routes",
    )

    # 📦 تفاصيل الطلب
    router.register(
        pattern=r"^order_details_(\d+)$",
        handler=order_details_callback,
    )

    logger.info(
        "order_routes_registered",
    )
