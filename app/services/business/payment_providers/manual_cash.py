# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MANUAL CASH INSTRUCTION PROVIDER
# Prepare a pending cash request without treating instructions as collected funds.
# ==============================================

"""Prepare a cash collection request, never proof of received money."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Declare the standard-library, framework and project dependencies used below.
# ==============================================

from decimal import Decimal

from app.core.exceptions import ValidationError
from app.services.business.payment_providers.contracts import PaymentInstruction

# ==============================================
# MANUAL CASH PROVIDER
# Prepare a cash request without treating it as proof of collection.
# ==============================================


class ManualCashProvider:
    """Prepare a cash request without treating it as proof of collection."""

    # ==============================================
    # CONTRACT FIELDS
    # Describe the fields accepted or returned by this declared data contract.
    # ==============================================

    code = "manual_cash"
    supported_methods = frozenset({"cash"})

    # ==============================================
    # PREPARE PAYMENT
    # Return pending cash instructions; only authorized settlement can activate service.
    # ==============================================

    def prepare_payment(
        self, *, method: str, amount: Decimal, currency: str
    ) -> PaymentInstruction:
        """Return pending cash instructions; only authorized settlement can activate service."""

        if method != "cash" or not amount.is_finite() or amount <= 0:
            raise ValidationError(message="Invalid cash collection request")
        return PaymentInstruction(
            provider=self.code,
            method=method,
            amount=amount,
            currency=currency,
            requires_receipt=True,
            requires_admin_review=True,
        )
