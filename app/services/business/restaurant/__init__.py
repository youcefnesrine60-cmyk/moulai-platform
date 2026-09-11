# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🍽️ RESTAURANT SERVICES - PACKAGE INIT
# ==============================================

# ==============================================
# 📦 IMPORT SERVICES
# ==============================================

# ---------- Restaurants ----------
from app.services.business.restaurant.restaurants.service import RestaurantService
from app.services.business.restaurant.restaurants.handlers import RestaurantEventHandlers
from app.services.business.restaurant.restaurants.validators import (
    MAX_RESTAURANTS_PER_OWNER,
    VALID_RESTAURANT_TYPES,
    validate_restaurant_type,
    validate_owner_limit,
)
from app.services.business.restaurant.restaurants.compat import (
    create_restaurant,
    get_restaurant,
    get_restaurants,
    get_all_restaurants,
    update_restaurant,
    delete_restaurant,
    toggle_restaurant_status,
)

# ---------- Metrics ----------
from app.services.business.restaurant.metrics.service import (
    RestaurantMetricsService,
    MetricsDict,
)
from app.services.business.restaurant.metrics.handlers import MetricsEventHandlers
from app.services.business.restaurant.metrics.compat import (
    initialize_metrics,
    product_created,
    product_deleted,
    category_created,
    category_deleted,
    order_registered,
    get_metrics,
    get_metrics_summary,
    reset_metrics,
)

# ---------- Order Counter ----------
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

# ---------- Payment Settings ----------
from app.services.business.restaurant.payment_setting.service import (
    RestaurantPaymentSettingsService,
    ALL_PAYMENT_METHODS,
    DEFAULT_PAYMENT_METHODS,
)
from app.services.business.restaurant.payment_setting.handlers import PaymentSettingsEventHandlers
from app.services.business.restaurant.payment_setting.compat import (
    create_payment_settings,
    get_payment_settings,
    update_payment_settings,
    update_payment_methods,
    get_allowed_payment_methods,
    delete_payment_settings,
    reset_payment_settings,
    enable_payment_method,
    disable_payment_method,
)

# ---------- Groups ----------
from app.services.business.restaurant.groups.service import RestaurantGroupService
from app.services.business.restaurant.groups.handlers import RestaurantGroupEventHandlers
from app.services.business.restaurant.groups.branch_handlers import RestaurantBranchEventHandlers
from app.services.business.restaurant.groups.compat import (
    create_group,
    get_group,
    get_groups_by_owner,
    update_group,
    delete_group,
    toggle_group_active,
    add_branches_to_group,
    remove_branch_from_group,
)

# ---------- Branches ----------
from app.services.business.restaurant.branches.service import RestaurantBranchService
from app.services.business.restaurant.branches.compat import (
    create_branch,
    get_branch,
    get_branches_by_group,
    get_branches_by_restaurant,
    delete_branch,
)


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
    "create_restaurant",
    "get_restaurant",
    "get_restaurants",
    "get_all_restaurants",
    "update_restaurant",
    "delete_restaurant",
    "toggle_restaurant_status",

    # ---------- Metrics ----------
    "RestaurantMetricsService",
    "MetricsDict",
    "MetricsEventHandlers",
    "initialize_metrics",
    "product_created",
    "product_deleted",
    "category_created",
    "category_deleted",
    "order_registered",
    "get_metrics",
    "get_metrics_summary",
    "reset_metrics",

    # ---------- Order Counter ----------
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

    # ---------- Payment Settings ----------
    "RestaurantPaymentSettingsService",
    "ALL_PAYMENT_METHODS",
    "DEFAULT_PAYMENT_METHODS",
    "PaymentSettingsEventHandlers",
    "create_payment_settings",
    "get_payment_settings",
    "update_payment_settings",
    "update_payment_methods",
    "get_allowed_payment_methods",
    "delete_payment_settings",
    "reset_payment_settings",
    "enable_payment_method",
    "disable_payment_method",

    # ---------- Groups ----------
    "RestaurantGroupService",
    "RestaurantGroupEventHandlers",
    "RestaurantBranchEventHandlers",
    "create_group",
    "get_group",
    "get_groups_by_owner",
    "update_group",
    "delete_group",
    "toggle_group_active",
    "add_branches_to_group",
    "remove_branch_from_group",

    # ---------- Branches ----------
    "RestaurantBranchService",
    "create_branch",
    "get_branch",
    "get_branches_by_group",
    "get_branches_by_restaurant",
    "delete_branch",
]