# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📦 MODELS INIT ( MODELS - نماذج SQLAlchemy.)
# تهيئة مجلد النماذج
# ==============================================

"""Package initializer and public module exports.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from .admin import Admin
from .admin_log import AdminLog
from .admin_session import AdminSession
from .agent import Agent, Channel, Conversation, Message
from .base import Base, BaseModel, BaseModelWithoutId
from .branch import Branch
from .category import Category
from .complaint import Complaint
from .feature_pricing import (
    BranchPricing,
    FeaturePricing,
    FeatureUsageCounter,
    FeatureUsageLimit,
)
from .loyalty_discount import LoyaltyDiscount, MultiRestaurantDiscount, Promotion
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
from .rbac import Permission, Role
from .registration_request import RegistrationRequest
from .restaurant import Restaurant
from .restaurant_group import RestaurantBranch, RestaurantGroup
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
from .user import User
from .manual_payment import ManualPaymentAudit, ManualPaymentReceipt

# ==============================================
# 📤 EXPORTS
# ==============================================

__all__ = [
    # Base
    "Base",
    "BaseModel",
    "BaseModelWithoutId",
    # Core
    "Owner",
    "Restaurant",
    "Branch",
    "Category",
    "Product",
    "OptionGroup",
    "ProductOption",
    # Orders
    "Order",
    "OrderItem",
    "OrderItemOption",
    "OrderPayment",
    "OrderStatusHistory",
    # Agent
    "Agent",
    "Channel",
    "Conversation",
    "Message",
    # Users
    "User",
    "Admin",
    "Permission",
    "Role",
    "AdminLog",
    "AdminSession",
    # Subscription
    "SubscriptionPlan",
    "Feature",
    "PlanFeature",
    "Subscription",
    "SubscriptionFeature",
    "SubscriptionFeatureRequest",
    # Feature Pricing & Usage
    "FeaturePricing",
    "FeatureUsageLimit",
    "FeatureUsageCounter",
    "BranchPricing",
    # Discounts & Promotions
    "LoyaltyDiscount",
    "MultiRestaurantDiscount",
    "Promotion",
    # Registration
    "RegistrationRequest",
    # Groups
    "RestaurantGroup",
    "RestaurantBranch",
    # Metrics
    "RestaurantMetric",
    # Order Counter
    "RestaurantOrderCounter",
    # Payments
    "Payment",
    "ManualPaymentAudit",
    "ManualPaymentReceipt",
    "RestaurantPaymentSetting",
    "Complaint",
]
