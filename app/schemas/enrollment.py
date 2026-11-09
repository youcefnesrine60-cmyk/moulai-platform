# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# AUTHENTICATED LOCAL ENROLLMENT INPUTS
# Let the owner describe a company while keeping account binding, country validation and rights server-owned.
# ==============================================

"""Closed input contracts; no caller-selected owner, role, trial eligibility or validated country."""

# isort: split
# ==============================================
# BOUNDED USER INPUT
# Preserve separate document purposes and require the exact presented version on every response.
# ==============================================

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class EnrollmentInput(BaseModel):
    """Company and first establishment details belonging to the currently authenticated development account."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    company_name: str = Field(min_length=2, max_length=180)
    legal_entity_reference: str = Field(min_length=3, max_length=180)
    full_name: str = Field(min_length=2, max_length=180)
    phone: str = Field(min_length=3, max_length=20)
    email: str | None = Field(default=None, max_length=180)
    restaurant_name: str = Field(min_length=2, max_length=180)
    branch_name: str = Field(min_length=2, max_length=180)
    restaurant_type: Literal["restaurant", "cafe", "other"] = "restaurant"


class DocumentResponseInput(BaseModel):
    """A separate explicit action on one exact document; no global acceptance flag exists."""

    model_config = ConfigDict(extra="forbid")
    document_id: int = Field(strict=True, gt=0)
    version: str = Field(min_length=1, max_length=80)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    locale: Literal["fr", "en", "ar"]
    action: Literal["accepted", "acknowledged", "declined"]


# ==============================================
# INCOMPLETE TEXT-ONLY ENROLLMENT DRAFT
# Allow empty text while refusing credentials, files, consents and arbitrary commands.
# ==============================================


class EnrollmentDraftInput(BaseModel):
    """Closed partial form contract; saving never creates a company or accepts a document."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    company_name: str = Field(default="", max_length=180)
    legal_entity_reference: str = Field(default="", max_length=180)
    full_name: str = Field(default="", max_length=180)
    phone: str = Field(default="", max_length=20)
    email: str = Field(default="", max_length=180)
    restaurant_name: str = Field(default="", max_length=180)
    branch_name: str = Field(default="", max_length=180)
