# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🔢 RESTAURANT ORDER COUNTER SERVICES - PACKAGE INIT
# ==============================================

"""Package initializer and public module exports.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.services.business.restaurant.order_counter.service import (
    RestaurantOrderCounterService,
)
from app.services.business.restaurant.order_counter.handlers import (
    OrderCounterEventHandlers,
)

# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "RestaurantOrderCounterService",
    "OrderCounterEventHandlers",
]
