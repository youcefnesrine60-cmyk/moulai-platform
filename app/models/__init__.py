# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# SQLALCHEMY MODEL REGISTRY
# Expose mapped models and register their relationships in the shared ORM metadata.
# ==============================================

"""Expose mapped models and register their relationships in the shared ORM metadata."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Declare the standard-library, framework and project dependencies used below.
# ==============================================

from .admin import Admin
from .admin_log import AdminLog
from .admin_session import AdminSession
from .agent import (
    Agent,
    Channel,
    Conversation,
    Message,
)
from .base import (
    Base,
    BaseModel,
    BaseModelWithoutId,
)
from .branch import Branch
from .cash_collection import (
    CashCollection,
    CashCollectionAttempt,
)
from .category import Category
from .complaint import Complaint
from .feature_pricing import (
    BranchPricing,
    FeaturePricing,
    FeatureUsageCounter,
    FeatureUsageLimit,
)
from .loyalty_discount import (
    LoyaltyDiscount,
    MultiRestaurantDiscount,
    Promotion,
)
from .manual_payment import (
    ManualPaymentAudit,
    ManualPaymentReceipt,
)
from .option_group import OptionGroup
from .order import Order
from .order_item import (
    OrderItem,
    OrderItemOption,
    OrderPayment,
    OrderStatusHistory,
)
from .owner import Owner
from .payment import Payment
from .product import Product
from .product_option import ProductOption
from .rbac import (
    Permission,
    Role,
)
from .registration_request import RegistrationRequest
from .restaurant import Restaurant
from .restaurant_group import (
    RestaurantBranch,
    RestaurantGroup,
)
from .restaurant_metric import RestaurantMetric
from .restaurant_order_counter import RestaurantOrderCounter
from .restaurant_payment_setting import RestaurantPaymentSetting
from .subscription import (
    Feature,
    PlanFeature,
    Subscription,
    SubscriptionFeature,
    SubscriptionFeatureRequest,
    SubscriptionPlan,
)
from .subscription_pricing import (
    SubscriptionPricingConfig,
    SubscriptionPricingSnapshot,
    SubscriptionReminder,
)
from .user import User

# ==============================================
# 📤 EXPORTS
# Declare the public names intentionally exposed to importing modules.
# ==============================================

__all__ = [
    "Admin",
    "AdminLog",
    "AdminSession",
    # Agent
    "Agent",
    # Base
    "Base",
    "BaseModel",
    "BaseModelWithoutId",
    "Branch",
    "BranchPricing",
    "CashCollection",
    "CashCollectionAttempt",
    "Category",
    "Channel",
    "Complaint",
    "Conversation",
    "Feature",
    # Feature Pricing & Usage
    "FeaturePricing",
    "FeatureUsageCounter",
    "FeatureUsageLimit",
    # Discounts & Promotions
    "LoyaltyDiscount",
    "ManualPaymentAudit",
    "ManualPaymentReceipt",
    "Message",
    "MultiRestaurantDiscount",
    "OptionGroup",
    # Orders
    "Order",
    "OrderItem",
    "OrderItemOption",
    "OrderPayment",
    "OrderStatusHistory",
    # Core
    "Owner",
    # Payments
    "Payment",
    "Permission",
    "PlanFeature",
    "Product",
    "ProductOption",
    "Promotion",
    # Registration
    "RegistrationRequest",
    "Restaurant",
    "RestaurantBranch",
    # Groups
    "RestaurantGroup",
    # Metrics
    "RestaurantMetric",
    # Order Counter
    "RestaurantOrderCounter",
    "RestaurantPaymentSetting",
    "Role",
    "Subscription",
    "SubscriptionFeature",
    "SubscriptionFeatureRequest",
    # Subscription
    "SubscriptionPlan",
    "SubscriptionPricingConfig",
    "SubscriptionPricingSnapshot",
    "SubscriptionReminder",
    # Users
    "User",
]
