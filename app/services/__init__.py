# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🧠 SERVICES - PACKAGE INIT
# ==============================================

"""
حزمة الخدمات - تحتوي على جميع خدمات التطبيق.

التقسيم:
- business: خدمات منطق الأعمال
- infrastructure: خدمات البنية التحتية
- integration: خدمات التكامل مع الأنظمة الخارجية

"""

# ==============================================
# 📦 IMPORT SERVICES
# ==============================================

# Business Services
from app.services.business import (

    # Admin Services
    AdminService,
    AdminLogService,
    AdminSessionService,

    # Restaurant Services
    RestaurantService,
    RestaurantEventHandlers,
    RestaurantMetricsService,
    MetricsEventHandlers,
    RestaurantOrderCounterService,
    OrderCounterEventHandlers,
    RestaurantPaymentSettingsService,
    PaymentSettingsEventHandlers,
    RestaurantGroupService,
    RestaurantGroupEventHandlers,
    RestaurantBranchEventHandlers,
    RestaurantBranchService,

    # Agent Services
    AgentService,
    ChannelService,
    ConversationService,
    MessageService,

    # Validators
    MAX_RESTAURANTS_PER_OWNER,
    VALID_RESTAURANT_TYPES,
    validate_restaurant_type,
    validate_owner_limit,

    # Constants
    ALL_PAYMENT_METHODS,
    DEFAULT_PAYMENT_METHODS,

    # Types
    MetricsDict,
)

# telegram Services
from app.services.telegram import (

    #Telegram Client
    send_message,
    edit_message,
    delete_message,

    # Callbacks
    answer_callback,

    # Webhook
    set_webhook,

    # Actions
    send_chat_action,

    # client
    close_http_client
)

# validation Services
from app.services.validation import (

    # Sanitizers
    sanitize_restaurant,
    sanitize_owner,
    sanitize_wilaya,
    sanitize_description,
    
    # Phone Validators
    validate_phone,
    normalize_phone

)


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [

    #------------------------
    # Business Services
    #------------------------

    # Admin Services
    "AdminService",
    "AdminLogService",
    "AdminSessionService",

    # Restaurant Services
    "RestaurantService",
    "RestaurantEventHandlers",
    "RestaurantMetricsService",
    "MetricsEventHandlers",
    "RestaurantOrderCounterService",
    "OrderCounterEventHandlers",
    "RestaurantPaymentSettingsService",
    "PaymentSettingsEventHandlers",
    "RestaurantGroupService",
    "RestaurantGroupEventHandlers",
    "RestaurantBranchEventHandlers",
    "RestaurantBranchService",

    # Agent Services
    "AgentService",
    "ChannelService",
    "ConversationService",
    "MessageService",

    # Validators
    "MAX_RESTAURANTS_PER_OWNER",
    "VALID_RESTAURANT_TYPES",
    "validate_restaurant_type",
    "validate_owner_limit",

    # Constants
    "ALL_PAYMENT_METHODS",
    "DEFAULT_PAYMENT_METHODS",

    # Types
    "MetricsDict",

    #------------------------
    # telegram Services
    #------------------------

    #Telegram Client
    "send_message",
    "edit_message",
    "delete_message",
    
    # Callbacks
    "answer_callback",
    
    # Webhook
    "set_webhook",
    
    # Actions
    "send_chat_action",
    
    # client
    "close_http_client"

    #------------------------
    # validation Services
    #------------------------

    # Sanitizers
    "sanitize_restaurant",
    "sanitize_owner",
    "sanitize_wilaya",
    "sanitize_description",
    
    # Phone Validators
    "validate_phone",
    "normalize_phone"

]