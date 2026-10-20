# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Closed tenant vocabulary; catalogue ceilings never provision permissions."""

from typing import (
    Literal,
    TypeAlias,
)
from urllib.parse import urlsplit

# ==============================================
# TYPES AND POLICY VALIDATION
# ==============================================

TenantRoleCode: TypeAlias = Literal["owner", "manager", "employee"]
RestaurantAccessMode: TypeAlias = Literal["company-wide", "explicit-grants"]
TenantPermissionCode: TypeAlias = str
TENANT_ROLES = frozenset({"owner", "manager", "employee"})
ACCESS_MODES = frozenset({"company-wide", "explicit-grants"})
TENANT_PERMISSIONS = frozenset(
    {
        "tenant.organization.read",
        "tenant.organization.update",
        "tenant.organization.suspend",
        "tenant.membership.self.read",
        "tenant.membership.self.leave",
        "tenant.restaurants.read",
        "tenant.restaurants.update",
        "tenant.branches.read",
        "tenant.branches.manage",
        "tenant.catalog.read",
        "tenant.catalog.manage",
        "tenant.orders.read",
        "tenant.orders.fulfill",
        "tenant.orders.manage",
        "tenant.agents.read",
        "tenant.agents.manage",
        "tenant.conversations.read",
        "tenant.conversations.respond",
        "tenant.reports.read",
        "tenant.groups.read",
        "tenant.groups.manage",
        "tenant.memberships.read",
        "tenant.memberships.manage",
        "tenant.ownership.manage",
        "tenant.billing.read",
        "tenant.billing.checkout",
        "tenant.receipts.submit",
    }
)
EMPLOYEE_PERMISSION_CEILING = frozenset(
    {
        "tenant.membership.self.read",
        "tenant.membership.self.leave",
        "tenant.restaurants.read",
        "tenant.branches.read",
        "tenant.catalog.read",
        "tenant.orders.read",
        "tenant.orders.fulfill",
    }
)
MANAGER_PERMISSION_CEILING = EMPLOYEE_PERMISSION_CEILING | frozenset(
    {
        "tenant.organization.read",
        "tenant.restaurants.update",
        "tenant.branches.manage",
        "tenant.catalog.manage",
        "tenant.orders.manage",
        "tenant.agents.read",
        "tenant.agents.manage",
        "tenant.conversations.read",
        "tenant.conversations.respond",
        "tenant.reports.read",
        "tenant.groups.read",
    }
)
# Fulfillment remains blocked for every role until transition review, even if
# a future database template contains this approved catalogue name.
BLOCKED_B1_PERMISSIONS = frozenset({"tenant.orders.fulfill"})


class TenantAccessDenied(PermissionError):
    """Deny without exposing identifiers, credentials or foreign resources."""


class TenantConflict(RuntimeError):
    """Report a stale revision or an incompatible unit of work."""


# ==============================================
# PERMISSION CEILING
# ==============================================


def permission_ceiling(*, role_code: str) -> frozenset[str]:
    """Validate a stored role; never use this ceiling as a permission fallback."""
    if role_code == "owner":
        return TENANT_PERMISSIONS
    if role_code == "manager":
        return MANAGER_PERMISSION_CEILING
    if role_code == "employee":
        return EMPLOYEE_PERMISSION_CEILING
    raise TenantAccessDenied("tenant_policy_invalid")


# ==============================================
# POSITIVE ID
# ==============================================


def positive_id(*, value: int) -> int:
    """Reject bools and nonpositive/noninteger local identifiers."""
    if type(value) is not int or value < 1:
        raise ValueError("positive_integer_required")
    return value


# ==============================================
# VALIDATE IDENTITY KEY
# ==============================================


def validate_identity_key(*, issuer: str, subject: str) -> None:
    """Validate exact bounded ASCII identity keys without normalizing them."""
    validate_issuer(issuer=issuer)
    validate_subject(subject=subject)


# ==============================================
# VALIDATE COMPONENT
# ==============================================


def _validate_component(*, value: str, limit: int) -> None:
    """Reject malformed opaque key components without substituting values."""
    if (
        not isinstance(value, str)
        or not value
        or len(value) > limit
        or value != value.strip()
        or not value.isascii()
        or any(ord(char) < 32 or ord(char) == 127 for char in value)
    ):
        raise ValueError("identity_key_invalid")


# ==============================================
# VALIDATE SUBJECT
# ==============================================


def validate_subject(*, subject: str) -> None:
    """Validate the exact issuer-local opaque subject component."""
    _validate_component(value=subject, limit=255)


# ==============================================
# VALIDATE ISSUER
# ==============================================


def validate_issuer(*, issuer: str) -> None:
    """Validate the exact business HTTPS issuer component."""
    _validate_component(value=issuer, limit=1024)
    try:
        parsed = urlsplit(issuer)
        valid = (
            parsed.scheme == "https"
            and parsed.hostname is not None
            and parsed.username is None
            and parsed.password is None
            and not parsed.query
            and not parsed.fragment
            and parsed.port != 0
        )
    except ValueError:
        valid = False
    if not valid:
        raise ValueError("trusted_https_issuer_required")
