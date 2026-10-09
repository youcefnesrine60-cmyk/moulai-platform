# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / CORE / SECURITY / FRAUD RULES
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for fraud rules.

Part of MoulAI Platform - Agent-as-a-Service.
"""


class FraudRules:

    # ==========================================
    # 🚫 TOO MANY ORDERS
    # ==========================================

    MAX_ORDERS_PER_HOUR = 20

    # ==========================================
    # 🚫 TOO MANY COUPONS
    # ==========================================

    MAX_COUPONS_PER_DAY = 10

    # ==========================================
    # 🚫 PAYMENT FAILURES
    # ==========================================

    MAX_PAYMENT_FAILURES = 5

    # ==========================================
    # 🚫 DELIVERY ABUSE
    # ==========================================

    MAX_FAKE_DELIVERIES = 3
