# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HANDLERS / CALLBACKS / CUSTOMER / ROUTER
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for router.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.logger import logger
from app.core.router_instance import router

# استيراد معالجات الزبون
from app.handlers.callbacks.customer.restaurant_list import customer_callback
from app.handlers.callbacks.customer.restaurant_details import (
    handle_restaurant_selection,
)

# استيراد معالجات الدفع
from app.handlers.callbacks.customer.payment import (
    payment_method_callback,
    payment_confirm_callback,
    retry_payment_callback,
    back_to_payment_callback,
)

# استيراد معالجات الطلبات
from app.handlers.callbacks.customer.order import order_details_callback

# ==============================================
# 🚀 REGISTER CUSTOMER ROUTES
# ==============================================


async def register_customer_routes() -> None:

    # ==========================================
    # 👤 CUSTOMER ENTRY
    # ==========================================

    router.register(
        pattern=r"^customer$",
        handler=customer_callback,
    )

    # ==========================================
    # 🍔 RESTAURANT DETAILS
    # ==========================================

    router.register(
        pattern=r"^rest_(.+)$",
        handler=handle_restaurant_selection,
    )

    # ==========================================
    # 📦 ORDER DETAILS
    # ==========================================

    router.register(
        pattern=r"^order_details_(\d+)$",
        handler=order_details_callback,
    )

    # ==========================================
    # 💳 PAYMENT METHODS
    # ==========================================

    # اختيار طريقة الدفع
    router.register(
        pattern=r"^payment_(cash|card|ccp|baridimob|stripe|paypal)_(\d+)$",
        handler=payment_method_callback,
    )

    # تأكيد الدفع
    router.register(
        pattern=r"^payment_confirm_(\d+)$",
        handler=payment_confirm_callback,
    )

    # إعادة محاولة الدفع
    router.register(
        pattern=r"^retry_payment_(\d+)$",
        handler=retry_payment_callback,
    )

    # الرجوع إلى الدفع
    router.register(
        pattern=r"^back_to_payment_(\d+)$",
        handler=back_to_payment_callback,
    )

    logger.info(
        "customer_callback_routes_registered",
    )
