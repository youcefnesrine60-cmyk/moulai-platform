# ==============================================
# MoulAI Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine
# ==============================================

# ==============================================
# 🍽️ RESTAURANT SCHEMAS - PACKAGE INIT
# ==============================================

# 🍽️ RESTAURANT
from app.schemas.restaurant.restaurant import (

    RestaurantBase,
    RestaurantCreate,
    RestaurantUpdate,
    RestaurantResponse,
    RestaurantListResponse,
    RestaurantStats,
    RestaurantData,
    RestaurantUpdateData,
    RestaurantListData,
)

# 🏢 RESTAURANT GROUP
from app.schemas.restaurant.restaurant_group import (

    # Types
    RestaurantGroupData,
    RestaurantGroupUpdateData,
    RestaurantGroupListData,
    RestaurantBranchData,
    RestaurantBranchUpdateData,
    RestaurantBranchListData,
            
    # Restaurant Group
    RestaurantGroupBase,
    RestaurantGroupCreate,
    RestaurantGroupUpdate,
    RestaurantGroupResponse,
    RestaurantGroupListResponse,
    RestaurantGroupStatistics,
            
    # Restaurant Branch
    RestaurantBranchBase,
    RestaurantBranchCreate,
    RestaurantBranchUpdate,
    RestaurantBranchResponse,
    RestaurantBranchListResponse,
    RestaurantBranchBulkCreate,    
)

# 📊 RESTAURANT METRIC
from app.schemas.restaurant.restaurant_metric import (
    
    # Restaurant Metric
    RestaurantMetricBase,
    RestaurantMetricCreate,
    RestaurantMetricUpdate,
    RestaurantMetricResponse,
    RestaurantMetricListResponse,
    RestaurantMetricSummary,
    
    # Metrics Trend
    MetricsTrendPoint,
    MetricsTrend,
    
    # Product Metrics
    ProductMetrics,
    
    # Types
    RestaurantMetricData,
    RestaurantMetricUpdateData,
    RestaurantMetricListData,
)

# 🔢 RESTAURANT ORDER COUNTER
from app.schemas.restaurant.restaurant_order_counter import (

    # Restaurant Order Counter
    RestaurantOrderCounterBase,
    RestaurantOrderCounterCreate,
    RestaurantOrderCounterUpdate,
    RestaurantOrderCounterResponse,
    RestaurantOrderCounterListResponse,
    
    # Next Order Number Response
    NextOrderNumberResponse,
    
    # Order Counter Summary
    OrderCounterSummary,
    
    # Order Number Format
    OrderNumberFormat,
    
    # Types
    OrderCounterData,
    OrderCounterUpdateData,
    OrderCounterListData,
)
# 🏦 RESTAURANT PAYMENT SETTING
from app.schemas.restaurant.restaurant_payment_setting import (

    # Restaurant Payment Setting
    RestaurantPaymentSettingBase,
    RestaurantPaymentSettingCreate,
    RestaurantPaymentSettingUpdate,
    RestaurantPaymentSettingResponse,
    RestaurantPaymentSettingListResponse,
    
    # Payment Methods List
    PaymentMethodsList,
    
    #Payment Settings Summary
    PaymentSettingsSummary,
    
    # Types
    PaymentSettingData,
    PaymentSettingUpdateData,
    PaymentSettingListData,
)

# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [

    # Restaurant
    "RestaurantBase",
    "RestaurantCreate",
    "RestaurantUpdate",
    "RestaurantResponse",
    "RestaurantListResponse",
    "RestaurantStats",
    "RestaurantData",
    "RestaurantUpdateData",
    "RestaurantListData",

    #----------------------
    # Types
    "RestaurantGroupData",
    "RestaurantGroupUpdateData",
    "RestaurantGroupListData",
    "RestaurantBranchData",
    "RestaurantBranchUpdateData",
    "RestaurantBranchListData",

    # Restaurant Group
    "RestaurantGroupBase",
    "RestaurantGroupCreate",
    "RestaurantGroupUpdate",
    "RestaurantGroupResponse",
    "RestaurantGroupListResponse",
    "RestaurantGroupStatistics",

    # Restaurant Branch
    "RestaurantBranchBase",
    "RestaurantBranchCreate",
    "RestaurantBranchUpdate",
    "RestaurantBranchResponse",
    "RestaurantBranchListResponse",
    "RestaurantBranchBulkCreate",

    #----------------------
    # Restaurant Metric
    "RestaurantMetricBase",
    "RestaurantMetricCreate",
    "RestaurantMetricUpdate",
    "RestaurantMetricResponse",
    "RestaurantMetricListResponse",
    "RestaurantMetricSummary",
    
    # Metrics Trend
    "MetricsTrendPoint",
    "MetricsTrend",
    
    # Product Metrics
    "ProductMetrics",
    
    # Types
    "RestaurantMetricData",
    "RestaurantMetricUpdateData",
    "RestaurantMetricListData",

    #----------------------
    # Restaurant Order Counter
    "RestaurantOrderCounterBase",
    "RestaurantOrderCounterCreate",
    "RestaurantOrderCounterUpdate",
    "RestaurantOrderCounterResponse",
    "RestaurantOrderCounterListResponse",
    
    # Next Order Number Response
    "NextOrderNumberResponse",
    
    # Order Counter Summary
    "OrderCounterSummary",
    
    # Order Number Format
    "OrderNumberFormat",
    
    # Types
    "OrderCounterData",
    "OrderCounterUpdateData",
    "OrderCounterListData",

    #----------------------
    # Restaurant Payment Setting
    "RestaurantPaymentSettingBase",
    "RestaurantPaymentSettingCreate",
    "RestaurantPaymentSettingUpdate",
    "RestaurantPaymentSettingResponse",
    "RestaurantPaymentSettingListResponse",
    
    # Payment Methods List
    "PaymentMethodsList",
    
    #Payment Settings Summary
    "PaymentSettingsSummary",
    
    # Types
    "PaymentSettingData",
    "PaymentSettingUpdateData",
    "PaymentSettingListData",
]