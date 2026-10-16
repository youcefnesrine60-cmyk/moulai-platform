# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Offline CCP/BaridiMob instructions; an upload never proves settlement."""

# ==============================================
# IMPORTS
# ==============================================

from decimal import Decimal

from app.core.exceptions import ValidationError

from .contracts import PaymentInstruction

# ==============================================
# MANUAL TRANSFER PROVIDER
# ==============================================


class ManualTransferProvider:
    """Prepare local transfer terms without simulating a banking integration."""

    code: str = "manual_transfer"
    supported_methods: frozenset[str] = frozenset({"ccp", "baridimob"})

    # ==========================================
    # PREPARE PAYMENT INSTRUCTIONS
    # ==========================================

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
            or amount.as_tuple().exponent < -2
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
