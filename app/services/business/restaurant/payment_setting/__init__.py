# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🏦 RESTAURANT PAYMENT SETTINGS SERVICES - PACKAGE INIT
# ==============================================

"""Package initializer and public module exports.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.services.business.restaurant.payment_setting.service import (
    RestaurantPaymentSettingsService,
    ALL_PAYMENT_METHODS,
    DEFAULT_PAYMENT_METHODS,
)
from app.services.business.restaurant.payment_setting.handlers import (
    PaymentSettingsEventHandlers,
)
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

# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
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
]
