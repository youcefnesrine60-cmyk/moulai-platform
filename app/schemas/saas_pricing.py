# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# EXPLICIT SAAS CAMPAIGN EDITOR CONTRACTS
# Receive exact percentage text and dated intent without accepting caller authority.
# ==============================================

"""Version reviewed campaigns through existing persisted promotions and admin audit."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Validate timezone-aware dates and reject binary monetary approximations.
# ==============================================

from datetime import datetime
from decimal import Decimal
from typing import (
    Annotated,
    Literal,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

# ==============================================
# SINGLE EXISTING BASE PARAMETER
# Apply only an explicit immediate change; future scheduling is not silently approximated.
# ==============================================


class BasePriceCommand(BaseModel):
    """Change DZD B in its existing singleton, with a strict optimistic version check."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)
    country_code: str = Field(default="DZ", pattern=r"^[A-Z]{2}$")
    currency: str = Field(default="DZD", pattern=r"^[A-Z]{3}$")
    amount: str = Field(pattern=r"^(?:0|[1-9]\d{0,11})(?:\.\d{1,2})?$")
    expected_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    effective: Literal["on_commit"]
    reason: str = Field(min_length=1, max_length=500)


# ==============================================
# IMMUTABLE DRAFT VALUES
# A campaign changes only a percentage, not feature prices or retained invoices.
# ==============================================


class CampaignValues(BaseModel):
    """Require explicit targets, administrative priority and an unambiguous UTC interval."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=255)
    discount_percent: str = Field(pattern=r"^(?:0|[1-9]\d{0,2})(?:\.\d{1,8})?$")
    starts_at: datetime
    expires_at: datetime
    priority: int = Field(strict=True, ge=0, le=2147483647)
    restaurant_id: int | None = Field(default=None, strict=True, gt=0)
    owner_id: int | None = Field(default=None, strict=True, gt=0)
    plan_id: int | None = Field(default=None, strict=True, gt=0)

    # ==============================================
    # COMPLETE CAMPAIGN INTERVAL
    # Refuse naive dates, empty names and percentages outside the existing engine range.
    # ==============================================

    @model_validator(mode="after")
    def validate_values(self) -> CampaignValues:
        """Reject ambiguous intervals before any authorization-dependent SQL write."""
        if (
            not self.name.strip()
            or Decimal(self.discount_percent) > 100
            or self.starts_at.utcoffset() is None
            or self.expires_at.utcoffset() is None
            or self.starts_at >= self.expires_at
        ):
            raise ValueError("invalid_campaign_interval_or_percentage")
        return self


# ==============================================
# EXPLICIT CAMPAIGN INTENT
# Every mutation after creation must identify the exact prior persisted representation.
# ==============================================


class CampaignCommand(BaseModel):
    """Keep draft editing separate from publication and immediate deactivation."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    operation: Literal["create", "update", "publish", "deactivate"]
    identifier: int | None = Field(default=None, strict=True, gt=0)
    expected_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    values: CampaignValues | None = None
    reason: str = Field(min_length=1, max_length=500)

    # ==============================================
    # CLOSED OPERATION SHAPE
    # Reject missing version checks and irrelevant values rather than guessing the intent.
    # ==============================================

    @model_validator(mode="after")
    def validate_intent(self) -> CampaignCommand:
        """Require a complete new draft or a precisely versioned existing campaign."""
        if (
            not self.reason.strip()
            or (self.operation == "create") != (self.identifier is None)
            or (self.operation == "create") != (self.expected_sha256 is None)
            or (self.operation in {"create", "update"}) != (self.values is not None)
        ):
            raise ValueError("invalid_campaign_command_shape")
        return self


# ==============================================
# FUTURE REMINDER CALENDAR CONFIGURATION
# Keep offsets explicit, unique and bounded; a change never means a payment or confirmed renewal.
# ==============================================


class ReminderCommand(BaseModel):
    """Version the existing reminder policy without reprogramming already scheduled jobs implicitly."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    days: list[Annotated[int, Field(strict=True, ge=0, le=3660)]] = Field(
        min_length=1, max_length=32
    )
    expected_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reason: str = Field(min_length=1, max_length=500)

    # ==============================================
    # UNAMBIGUOUS DAY OFFSETS
    # Expiration itself remains represented and duplicate or unordered offsets cannot create extra jobs.
    # ==============================================

    @model_validator(mode="after")
    def validate_days(self) -> ReminderCommand:
        """Require descending unique nonnegative days including expiration and a real audit reason."""
        if (
            self.days != sorted(set(self.days), reverse=True)
            or 0 not in self.days
            or not self.reason.strip()
        ):
            raise ValueError("explicit_unique_reminder_days_required")
        return self
