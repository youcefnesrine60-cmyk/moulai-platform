# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🍽️ RESTAURANT SERVICES - PACKAGE INIT
# ==============================================

"""Package initializer and public module exports.

Part of MoulAI Platform - Agent-as-a-Service.
"""

# ==============================================
# 📦 IMPORT SERVICES
# ==============================================

# ---------- Restaurants ----------
from app.services.business.restaurant.restaurants.service import RestaurantService
from app.services.business.restaurant.restaurants.handlers import (
    RestaurantEventHandlers,
)
from app.services.business.restaurant.restaurants.validators import (
    MAX_RESTAURANTS_PER_OWNER,
    VALID_RESTAURANT_TYPES,
    validate_restaurant_type,
    validate_owner_limit,
)

# ---------- Metrics ----------
from app.services.business.restaurant.metrics.service import (
    RestaurantMetricsService,
    MetricsDict,
)
from app.services.business.restaurant.metrics.handlers import MetricsEventHandlers

# ---------- Order Counter ----------
from app.services.business.restaurant.order_counter.service import (
    RestaurantOrderCounterService,
)
from app.services.business.restaurant.order_counter.handlers import (
    OrderCounterEventHandlers,
)

# ---------- Payment Settings ----------
from app.services.business.restaurant.payment_setting.service import (
    RestaurantPaymentSettingsService,
    ALL_PAYMENT_METHODS,
    DEFAULT_PAYMENT_METHODS,
)
from app.services.business.restaurant.payment_setting.handlers import (
    PaymentSettingsEventHandlers,
)

# ---------- Groups ----------
from app.services.business.restaurant.groups.service import RestaurantGroupService
from app.services.business.restaurant.groups.handlers import (
    RestaurantGroupEventHandlers,
)
from app.services.business.restaurant.groups.branch_handlers import (
    RestaurantBranchEventHandlers,
)

# ---------- Branches ----------
from app.services.business.restaurant.branches.service import RestaurantBranchService

# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    # ---------- Restaurants ----------
    "RestaurantService",
    "RestaurantEventHandlers",
    "MAX_RESTAURANTS_PER_OWNER",
    "VALID_RESTAURANT_TYPES",
    "validate_restaurant_type",
    "validate_owner_limit",
    # ---------- Metrics ----------
    "RestaurantMetricsService",
    "MetricsDict",
    "MetricsEventHandlers",
    # ---------- Order Counter ----------
    "RestaurantOrderCounterService",
    "OrderCounterEventHandlers",
    # ---------- Payment Settings ----------
    "RestaurantPaymentSettingsService",
    "ALL_PAYMENT_METHODS",
    "DEFAULT_PAYMENT_METHODS",
    "PaymentSettingsEventHandlers",
    # ---------- Groups ----------
    "RestaurantGroupService",
    "RestaurantGroupEventHandlers",
    "RestaurantBranchEventHandlers",
    # ---------- Branches ----------
    "RestaurantBranchService",
]
