# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🔢 RESTAURANT ORDER COUNTER SERVICES - PACKAGE INIT
# ==============================================

from app.services.business.restaurant.order_counter.service import RestaurantOrderCounterService
from app.services.business.restaurant.order_counter.handlers import OrderCounterEventHandlers
from app.services.business.restaurant.order_counter.compat import (
    initialize_order_counter,
    get_order_counter,
    update_order_counter,
    generate_next_order_number,
    get_order_counter_summary,
    reset_order_counter,
    increment_order_counter,
    build_order_number,
    get_current_order_number,
)


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "RestaurantOrderCounterService",
    "OrderCounterEventHandlers",
    "initialize_order_counter",
    "get_order_counter",
    "update_order_counter",
    "generate_next_order_number",
    "get_order_counter_summary",
    "reset_order_counter",
    "increment_order_counter",
    "build_order_number",
    "get_current_order_number",
]