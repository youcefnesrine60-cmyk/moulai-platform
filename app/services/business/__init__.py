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
    # Metrics
    RestaurantMetricsService,
    MetricsDict,
    MetricsEventHandlers,
    # Order Counter
    RestaurantOrderCounterService,
    OrderCounterEventHandlers,
    # Payment Settings
    RestaurantPaymentSettingsService,
    ALL_PAYMENT_METHODS,
    DEFAULT_PAYMENT_METHODS,
    PaymentSettingsEventHandlers,
    # Groups
    RestaurantGroupService,
    RestaurantGroupEventHandlers,
    RestaurantBranchEventHandlers,
    # Branches
    RestaurantBranchService,
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
    # Restaurant Services - Metrics
    "RestaurantMetricsService",
    "MetricsDict",
    "MetricsEventHandlers",
    # Restaurant Services - Order Counter
    "RestaurantOrderCounterService",
    "OrderCounterEventHandlers",
    # Restaurant Services - Payment Settings
    "RestaurantPaymentSettingsService",
    "ALL_PAYMENT_METHODS",
    "DEFAULT_PAYMENT_METHODS",
    "PaymentSettingsEventHandlers",
    # Restaurant Services - Groups
    "RestaurantGroupService",
    "RestaurantGroupEventHandlers",
    "RestaurantBranchEventHandlers",
    # Restaurant Services - Branches
    "RestaurantBranchService",
    # Agent Services
    "AgentService",
    "ChannelService",
    "ConversationService",
    "MessageService",
]
