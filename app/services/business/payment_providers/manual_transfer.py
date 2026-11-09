# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MANUAL TRANSFER INSTRUCTION PROVIDER
# Prepare CCP or BaridiMob instructions without confirming receipt or activating
# service.
# ==============================================

"""Offline CCP/BaridiMob instructions; an upload never proves settlement."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Declare the standard-library, framework and project dependencies used below.
# ==============================================

from decimal import Decimal

from app.core.exceptions import ValidationError

from .contracts import PaymentInstruction

# ==============================================
# MANUAL TRANSFER PROVIDER
# Prepare local transfer terms without simulating a banking integration.
# ==============================================


class ManualTransferProvider:
    """Prepare local transfer terms without simulating a banking integration."""

    # ==============================================
    # CONTRACT FIELDS
    # Describe the fields accepted or returned by this declared data contract.
    # ==============================================

    code: str = "manual_transfer"
    supported_methods: frozenset[str] = frozenset({"ccp", "baridimob"})

    # ==============================================
    # PREPARE PAYMENT INSTRUCTIONS
    # Validate positive DZD amounts with no fractional centime values.
    # ==============================================

    def prepare_payment(
        self, *, method: str, amount: Decimal, currency: str
    ) -> PaymentInstruction:
        """Validate positive DZD amounts with no fractional centime values.

        Settlement requires a receipt and a separate administrative check
        that the funds reached the platform's account.
        """

        if (
            method not in self.supported_methods
            or currency != "DZD"
            or not amount.is_finite()
            or amount <= 0
            or amount != amount.quantize(Decimal("0.01"))
        ):
            raise ValidationError(message="Unsupported manual transfer")
        return PaymentInstruction(
            provider=self.code,
            method=method,
            amount=amount,
            currency=currency,
            requires_receipt=True,
            requires_admin_review=True,
        )
