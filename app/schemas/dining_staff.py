# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# EXPLICIT STAFF MANAGEMENT CONTRACTS
# Separate professional descriptions, personal acceptance and owner-granted authority.
# ==============================================

"""No password, account creation, role promotion or implicit capability template."""

from __future__ import annotations

# isort: split
# ==============================================
# CLOSED INPUT TYPES
# Preserve exact issuer/subject keys; callers cannot add hidden authorization fields.
# ==============================================

from typing import (
    Annotated,
    Literal,
    TypeAlias,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

# ==============================================
# COMMON STRICT BASE
# Identity keys are not trimmed or normalized by a professional display contract.
# ==============================================


class StaffInput(BaseModel):
    """Refuse undeclared fields and keep owner choices explicit."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    # ==============================================
    # NONEMPTY PROFESSIONAL LABELS
    # Clean descriptive whitespace without normalizing issuer or subject identifiers.
    # ==============================================

    @field_validator("employee_code", "display_name", "reason", check_fields=False)
    @classmethod
    def validate_description_text(cls, value: str) -> str:
        """Reject blank professional text before any database write."""
        if not value.strip():
            raise ValueError("dining_staff_description_invalid")
        return value.strip()


# ==============================================
# INVITE AN EXISTING VERIFIED ACCOUNT
# The invitation creates only a pending professional relationship until accepted.
# ==============================================


class StaffInviteInput(StaffInput):
    """Address an already registered OIDC identity without creating credentials."""

    operation: Literal["invite"]
    issuer: str = Field(min_length=1, max_length=500)
    subject: str = Field(min_length=1, max_length=255)
    employee_code: str = Field(min_length=1, max_length=50)
    display_name: str = Field(min_length=1, max_length=160)


# ==============================================
# PROFESSIONAL DISPLAY PROFILE
# Changing a name or employee code cannot grant a permission or activate a member.
# ==============================================


class StaffProfileInput(StaffInput):
    """Update only the current branch's descriptive employee fields."""

    operation: Literal["profile"]
    membership_id: int = Field(strict=True, gt=0)
    employee_code: str = Field(min_length=1, max_length=50)
    display_name: str = Field(min_length=1, max_length=160)


# ==============================================
# DESCRIPTIVE FUNCTION AND TASKS
# Every language has an explicit label and no list of implicit grants exists here.
# ==============================================


class StaffFunctionInput(StaffInput):
    """Describe responsibilities without changing effective authority."""

    operation: Literal["function"]
    code: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,49}$")
    labels: dict[Literal["fr", "en", "ar"], str]
    tasks: tuple[str, ...] = Field(max_length=50)
    active: bool

    # ==============================================
    # COMPLETE LOCALIZED DESCRIPTION
    # Empty or oversized descriptions are rejected before any persistence.
    # ==============================================

    @model_validator(mode="after")
    def validate_description(self) -> StaffFunctionInput:
        """Require all three labels and bounded nonempty task descriptions."""
        if (
            set(self.labels) != {"fr", "en", "ar"}
            or any(
                not value.strip() or len(value) > 160 for value in self.labels.values()
            )
            or any(not value.strip() or len(value) > 500 for value in self.tasks)
        ):
            raise ValueError("dining_staff_description_invalid")
        return self


# ==============================================
# BRANCH FUNCTION ASSIGNMENT
# Multiple functions are allowed; the existing grant form remains independent.
# ==============================================


class StaffAssignmentInput(StaffInput):
    """Assign only a descriptive responsibility in the route's exact branch."""

    operation: Literal["assignment"]
    membership_id: int = Field(strict=True, gt=0)
    function_id: int = Field(strict=True, gt=0)
    active: bool


# ==============================================
# REVISION-CHECKED PROFESSIONAL LIFECYCLE
# Owner changes exclude owner identities and never silently restore old grants.
# ==============================================


class StaffStatusInput(StaffInput):
    """Activate accepted employment, suspend it or revoke it with an audit reason."""

    operation: Literal["status"]
    membership_id: int = Field(strict=True, gt=0)
    expected_revision: int = Field(strict=True, gt=0)
    status: Literal["active", "suspended", "revoked"]
    reason: str = Field(min_length=1, max_length=500)


StaffCommand: TypeAlias = Annotated[
    StaffInviteInput
    | StaffProfileInput
    | StaffFunctionInput
    | StaffAssignmentInput
    | StaffStatusInput,
    Field(discriminator="operation"),
]
