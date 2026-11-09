# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# CASH COLLECTION INPUT SCHEMA
# Validate independently reported cash receipt facts before administrative settlement.
# ==============================================

"""Validated physical cash receipt facts; no owner declaration can settle them."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Declare the standard-library, framework and project dependencies used below.
# ==============================================

from decimal import Decimal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
)

# ==============================================
# CASH CONFIRMATION
# Validated physical collection facts submitted by an authenticated administrator.
# ==============================================


class CashConfirmation(BaseModel):
    """Validated physical collection facts submitted by an authenticated administrator."""

    # ==============================================
    # CONTRACT FIELDS
    # Describe the fields accepted or returned by this declared data contract.
    # ==============================================

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    received_amount: Decimal = Field(
        gt=0, allow_inf_nan=False, max_digits=24, decimal_places=8
    )
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    collected_at: AwareDatetime
    receipt_reference: str = Field(
        min_length=3, max_length=120, pattern=r"^[A-Za-z0-9 ./_-]+$"
    )
