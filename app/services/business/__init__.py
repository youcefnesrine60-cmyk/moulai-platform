# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🏢 BUSINESS SERVICES - PACKAGE INIT
# ==============================================

"""
حزمة خدمات منطق الأعمال.

تحتوي على جميع خدمات الأعمال مقسمة حسب المجال:
- admin: خدمات إدارة المديرين
- restaurant: خدمات إدارة المطاعم
- agent: خدمات الوكيل الذكي
- order: خدمات الطلبات
- product: خدمات المنتجات
- user: خدمات المستخدمين
"""

# ==============================================
# 📦 IMPORT SERVICES
# ==============================================

# ---------- Admin Services ----------
from app.services.business.admin import (
    AdminService,
    AdminLogService,
    AdminSessionService,
)

# ---------- Restaurant Services ----------
from app.services.business.restaurant import (

    # Restaurants
    RestaurantService,
    RestaurantEventHandlers,
    MAX_RESTAURANTS_PER_OWNER,
    VALID_RESTAURANT_TYPES,
    validate_restaurant_type,
    validate_owner_limit,
    create_restaurant,
    get_restaurant,
    get_restaurants,
    get_all_restaurants,
    update_restaurant,
    delete_restaurant,
    toggle_restaurant_status,

    # Metrics
    RestaurantMetricsService,
    MetricsDict,
    MetricsEventHandlers,
    initialize_metrics,
    product_created,
    product_deleted,
    category_created,
    category_deleted,
    order_registered,
    get_metrics,
    get_metrics_summary,
    reset_metrics,

    # Order Counter
    RestaurantOrderCounterService,
    OrderCounterEventHandlers,
    initialize_order_counter,
    get_order_counter,
    update_order_counter,
    generate_next_order_number,
    get_order_counter_summary,
    reset_order_counter,
    increment_order_counter,
    build_order_number,
    get_current_order_number,

    # Payment Settings
    RestaurantPaymentSettingsService,
    ALL_PAYMENT_METHODS,
    DEFAULT_PAYMENT_METHODS,
    PaymentSettingsEventHandlers,
    create_payment_settings,
    get_payment_settings,
    update_payment_settings,
    update_payment_methods,
    get_allowed_payment_methods,
    delete_payment_settings,
    reset_payment_settings,
    enable_payment_method,
    disable_payment_method,

    # Groups
    RestaurantGroupService,
    RestaurantGroupEventHandlers,
    RestaurantBranchEventHandlers,
    create_group,
    get_group,
    get_groups_by_owner,
    update_group,
    delete_group,
    toggle_group_active,
    add_branches_to_group,
    remove_branch_from_group,

    # Branches
    RestaurantBranchService,
    create_branch,
    get_branch,
    get_branches_by_group,
    get_branches_by_restaurant,
    delete_branch,
)

# ---------- Agent Services ----------
from app.services.business.agent import (
    AgentService,
    ChannelService,
    ConversationService,
    MessageService,
)


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [

    # Admin Services
    "AdminService",
    "AdminLogService",
    "AdminSessionService",

    # Restaurant Services - Restaurants
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

    # Restaurant Services - Metrics
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

    # Restaurant Services - Order Counter
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

    # Restaurant Services - Payment Settings
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

    # Restaurant Services - Groups
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

    # Restaurant Services - Branches
    "RestaurantBranchService",
    "create_branch",
    "get_branch",
    "get_branches_by_group",
    "get_branches_by_restaurant",
    "delete_branch",

    # Agent Services
    "AgentService",
    "ChannelService",
    "ConversationService",
    "MessageService",
]