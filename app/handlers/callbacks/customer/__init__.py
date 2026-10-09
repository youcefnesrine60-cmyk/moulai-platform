# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# PACKAGE INITIALIZER - APP / HANDLERS / CALLBACKS / CUSTOMER /   INIT
# Package initialization and public exports component.
# ==============================================

"""Package initializer and public module exports.

Part of MoulAI Platform - Agent-as-a-Service.
"""

# مسارات الزبون العامة
from app.handlers.callbacks.customer.router import register_customer_routes

# مسارات السلة
from app.handlers.callbacks.customer.cart_routes import register_cart_routes

# معالجات السلة
from app.handlers.callbacks.customer.cart import (
    show_cart_callback,
    cart_item_callback,
    cart_increment_callback,
    cart_decrement_callback,
    cart_remove_callback,
    cart_clear_callback,
    checkout_callback,
)

# معالجات الطلبات
from app.handlers.callbacks.customer.order import order_details_callback

# معالجات الدفع
from app.handlers.callbacks.customer.payment import (
    payment_method_callback,
    payment_confirm_callback,
    retry_payment_callback,
    back_to_payment_callback,
)

__all__ = [
    # مسارات
    "register_customer_routes",
    "register_cart_routes",
    # معالجات السلة
    "show_cart_callback",
    "cart_item_callback",
    "cart_increment_callback",
    "cart_decrement_callback",
    "cart_remove_callback",
    "cart_clear_callback",
    "checkout_callback",
    # معالجات الطلبات
    "order_details_callback",
    # معالجات الدفع
    "payment_method_callback",
    "payment_confirm_callback",
    "retry_payment_callback",
    "back_to_payment_callback",
]
