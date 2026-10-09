# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HANDLERS / CALLBACKS / CUSTOMER / CART ROUTES
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for cart routes.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.logger import logger
from app.core.router_instance import router

from app.handlers.callbacks.customer.cart import (
    show_cart_callback,
    cart_item_callback,
    cart_increment_callback,
    cart_decrement_callback,
    cart_remove_callback,
    cart_clear_callback,
    checkout_callback,
)

# ==============================================
# 🚀 REGISTER CART ROUTES
# ==============================================


async def register_cart_routes() -> None:
    """
    تسجيل جميع مسارات السلة في الـ Router
    """
    logger.info(
        "registering_cart_routes",
    )

    # 🛒 عرض السلة
    router.register(
        pattern=r"^show_cart$",
        handler=show_cart_callback,
    )

    # 📦 عرض تفاصيل منتج في السلة
    router.register(
        pattern=r"^cart_item_(\d+)$",
        handler=cart_item_callback,
    )

    # ➕ زيادة كمية منتج
    router.register(
        pattern=r"^cart_inc_(\d+)$",
        handler=cart_increment_callback,
    )

    # ➖ إنقاص كمية منتج
    router.register(
        pattern=r"^cart_dec_(\d+)$",
        handler=cart_decrement_callback,
    )

    # ❌ حذف منتج من السلة
    router.register(
        pattern=r"^cart_remove_(\d+)$",
        handler=cart_remove_callback,
    )

    # 🗑️ إفراغ السلة
    router.register(
        pattern=r"^cart_clear$",
        handler=cart_clear_callback,
    )

    # 💳 الانتقال إلى الدفع
    router.register(
        pattern=r"^checkout$",
        handler=checkout_callback,
    )

    logger.info(
        "cart_routes_registered",
    )
