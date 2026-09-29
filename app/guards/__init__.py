# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🛡️ GUARDS - PACKAGE INIT
# طبقة الحماية: اشتراكات + ميزات
# ==============================================

# ---------- Subscription Guard ----------
from app.guards.subscription_guard import (
    SubscriptionResult,
    get_active_subscription,
    get_subscription_plan_code,
    get_subscription_plan_id,
    get_valid_subscription,
    has_active_subscription,
    is_paid_subscription,
    is_trial_subscription,
    require_active_subscription,
)

# ---------- Feature Guard ----------
from app.guards.feature_guard import (
    check_feature_access,
    has_feature,
    require_feature,
)


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    # Subscription Guard
    "SubscriptionResult",
    "require_active_subscription",
    "has_active_subscription",
    "get_active_subscription",
    "get_valid_subscription",
    "is_trial_subscription",
    "is_paid_subscription",
    "get_subscription_plan_code",
    "get_subscription_plan_id",

    # Feature Guard
    "check_feature_access",
    "require_feature",
    "has_feature",
]