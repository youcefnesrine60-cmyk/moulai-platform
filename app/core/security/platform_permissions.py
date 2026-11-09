# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# EXPLICIT PLATFORM PERMISSION REFERENCE
# Catalogue names never grant administrator or tenant authority by themselves.
# ==============================================

"""Country validation, pricing mutation and payment review require distinct stored grants."""

SUBSCRIPTION_PRICING_MANAGE = "subscriptions.pricing.manage"
TENANT_BILLING_COUNTRY_MANAGE = "tenant.billing_country.manage"
PLATFORM_PERMISSION_REFERENCE = frozenset(
    {
        "admins.manage",
        "restaurants.manage",
        "payments.review",
        SUBSCRIPTION_PRICING_MANAGE,
        TENANT_BILLING_COUNTRY_MANAGE,
    }
)
