# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# CANONICAL SUBSCRIPTION CONTRACT
# Define supported plan layers, feature inclusions and approved billing-cycle semantics.
# ==============================================

"""Approved commercial inclusions shared by pricing, grants and mutations."""

from __future__ import annotations

# ==============================================
# CONFIGURATION AND CONSTANTS
# Group the existing configuration values without changing their defaults.
# ==============================================

BASIC = frozenset(
    {"qr_menu", "categories", "products", "hosting", "dashboard", "basic_support"}
)
PROFESSIONAL = frozenset({"orders", "reviews", "best_customer"})
ENTERPRISE = frozenset({"analytics", "delivery", "whatsapp", "multi_branch"})
INCLUDED = {
    "basic": BASIC,
    "professional": BASIC | PROFESSIONAL,
    "enterprise": BASIC | PROFESSIONAL | ENTERPRISE,
    "trial": BASIC | {"orders", "delivery"},
}
PAYABLE_MONTHS = {"monthly": 1, "quarterly": 3, "semiannual": 6, "yearly": 10}
SERVICE_MONTHS = {"monthly": 1, "quarterly": 3, "semiannual": 6, "yearly": 12}


# ==============================================
# PLAN CODE
# Keep the existing 'pro' identifier as an alias, not a fourth product.
# ==============================================


def plan_code(*, code: str) -> str:
    """Keep the existing 'pro' identifier as an alias, not a fourth product."""
    code = "professional" if code == "pro" else code
    if code not in INCLUDED:
        raise ValueError("unsupported_subscription_plan")
    return code
