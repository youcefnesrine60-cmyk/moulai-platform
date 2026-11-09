# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# PAYMENT PROVIDER REGISTRY
# Resolve the explicitly supported instruction provider and reject unsupported methods.
# ==============================================

"""Fail closed for disabled methods and providers without approved adapters."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Declare the standard-library, framework and project dependencies used below.
# ==============================================

from app.core.config import settings
from app.core.exceptions import ValidationError

from .contracts import PaymentProvider
from .manual_cash import ManualCashProvider
from .manual_transfer import ManualTransferProvider

# ==============================================
# RESOLVE ENABLED PAYMENT PROVIDER
# Resolve an approved adapter only when its payment method is enabled.
# ==============================================


def get_payment_provider(*, method: str) -> PaymentProvider:
    """Resolve an approved adapter only when its payment method is enabled."""

    if method == "cash":
        return ManualCashProvider()
    enabled = {
        "ccp": settings.MANUAL_CCP_ENABLED,
        "baridimob": settings.MANUAL_BARIDIMOB_ENABLED,
    }
    if not enabled.get(method, False):
        raise ValidationError(message="Payment method is unavailable")
    return ManualTransferProvider()
