# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Small provider contract independent of HTTP, tenants, and subscriptions."""

# ==============================================
# IMPORTS
# ==============================================

from abc import abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

# ==============================================
# PAYMENT INSTRUCTION
# ==============================================


@dataclass(frozen=True)
class PaymentInstruction:
    """Describe the evidence and settlement checks a payment requires."""

    provider: str
    method: str
    amount: Decimal
    currency: str
    requires_receipt: bool
    requires_admin_review: bool


# ==============================================
# PAYMENT PROVIDER CONTRACT
# ==============================================


class PaymentProvider(Protocol):
    """Define the implemented operations every approved adapter must expose.

    Structural typing keeps provider implementations independent from
    subscription services, transport APIs, and tenant authorization.
    """

    code: str
    supported_methods: frozenset[str]

    # ==========================================
    # PREPARE PAYMENT INSTRUCTIONS
    # ==========================================

    @abstractmethod
    def prepare_payment(
        self, *, method: str, amount: Decimal, currency: str
    ) -> PaymentInstruction:
        """Validate supported terms and return the adapter's instructions."""
