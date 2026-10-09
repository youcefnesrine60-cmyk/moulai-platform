# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HANDLERS / CALLBACKS / OWNER / OWNER DASHBOARD ROUTES
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for owner dashboard routes.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.logger import logger
from app.core.router_instance import router

from app.handlers.callbacks.owner.owner_dashboard_handlers import (
    owner_dashboard_callback,
    owner_orders_callback,
    owner_products_callback,
)

# ==============================================
# 🚀 REGISTER OWNER DASHBOARD ROUTES
# ==============================================


async def register_owner_dashboard_routes() -> None:
    """
    تسجيل مسارات لوحة تحكم صاحب المحل
    """
    logger.info(
        "registering_owner_dashboard_routes",
    )

    # 🏪 لوحة التحكم الرئيسية
    router.register(
        pattern=r"^owner_dashboard_(\d+)$",
        handler=owner_dashboard_callback,
    )

    # 📦 إدارة الطلبات
    router.register(
        pattern=r"^owner_orders_(\d+)$",
        handler=owner_orders_callback,
    )

    # 🍔 إدارة المنتجات
    router.register(
        pattern=r"^owner_products_(\d+)$",
        handler=owner_products_callback,
    )

    # 📂 إدارة الأقسام
    router.register(
        pattern=r"^owner_categories_(\d+)$",
        handler=owner_products_callback,  # مؤقتاً نستخدم نفس المعالج
    )

    # 💳 الاشتراك والباقات
    router.register(
        pattern=r"^owner_subscription_(\d+)$",
        handler=owner_products_callback,  # مؤقتاً نستخدم نفس المعالج
    )

    # 📊 الإحصائيات المتقدمة
    router.register(
        pattern=r"^owner_stats_(\d+)$",
        handler=owner_products_callback,  # مؤقتاً نستخدم نفس المعالج
    )

    logger.info(
        "owner_dashboard_routes_registered",
    )
