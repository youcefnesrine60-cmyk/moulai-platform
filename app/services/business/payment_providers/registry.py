# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Fail closed for disabled methods and providers without approved adapters."""

# ==============================================
# IMPORTS
# ==============================================

from app.core.config import settings
from app.core.exceptions import ValidationError

from .contracts import PaymentProvider
from .manual_transfer import ManualTransferProvider

# ==============================================
# RESOLVE ENABLED PAYMENT PROVIDER
# ==============================================


def get_payment_provider(*, method: str) -> PaymentProvider:
    """Resolve an approved adapter only when its payment method is enabled."""

    enabled = {
        "ccp": settings.MANUAL_CCP_ENABLED,
        "baridimob": settings.MANUAL_BARIDIMOB_ENABLED,
    }
    if not enabled.get(method, False):
        raise ValidationError(message="Payment method is unavailable")
    return ManualTransferProvider()
