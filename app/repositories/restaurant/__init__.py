# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# PACKAGE INITIALIZER - APP / REPOSITORIES / RESTAURANT /   INIT
# Package initialization and public exports component.
# ==============================================

"""Package initializer and public module exports.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.repositories.restaurant.restaurant_repo import RestaurantRepository
from app.repositories.restaurant.restaurant_branch_repo import (
    RestaurantBranchRepository,
)
from app.repositories.restaurant.restaurant_metrics_repo import (
    RestaurantMetricsRepository,
)
from app.repositories.restaurant.restaurant_group_repo import RestaurantGroupRepository
from app.repositories.restaurant.restaurant_order_counters_repo import (
    RestaurantOrderCountersRepository,
)
from app.repositories.restaurant.restaurant_payment_settings_repo import (
    RestaurantPaymentSettingsRepository,
)

# from app.repositories.restaurant.restaurant_menu_repo import RestaurantMenuRepository

# ==============================================
# 📤 EXPORTS
# ==============================================

__all__ = [
    "RestaurantRepository",
    "RestaurantBranchRepository",
    "RestaurantMetricsRepository",
    "RestaurantGroupRepository",
    "RestaurantOrderCountersRepository",
    "RestaurantPaymentSettingsRepository",
    # "RestaurantMenuRepository"
]
