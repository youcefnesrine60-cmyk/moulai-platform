# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# CLOSED BILLING COUNTRY REQUEST CONTRACTS
# The owner can declare and request review, never submit a validated country or an administrative identity.
# ==============================================

"""Explicit synthetic local proof is mandatory until a real-data retention policy is approved."""

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

# ==============================================
# OWNER DECLARATION
# Proof references are validated again against the selected organization in the service.
# ==============================================


class CountryDeclaration(BaseModel):
    """Declare the country of establishment and the unchanged legal entity to be reviewed."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    declared_country: str = Field(pattern=r"^[A-Z]{2}$")
    legal_entity_reference: str = Field(min_length=3, max_length=180)
    evidence_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    reason: str = Field(min_length=3, max_length=2000)
    expected_revision: int = Field(strict=True, ge=1)
    idempotency_key: str = Field(pattern=r"^[A-Za-z0-9_-]{8,80}$")


# ==============================================
# EXPLICIT ADMINISTRATIVE DECISION
# Initial validation and later changes share the exact dedicated permission and audit.
# ==============================================


class CountryReview(BaseModel):
    """Record a human decision without accepting a caller-chosen effective country or date."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    decision: Literal["approve", "reject", "needs_information"]
    expected_revision: int = Field(strict=True, ge=1)
    justification: str = Field(min_length=3, max_length=2000)
    evidence_checked: bool = Field(strict=True)
    same_legal_entity: bool = Field(strict=True)
