# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Internal immutable tenant snapshots, never HTTP request schemas."""

from dataclasses import (
    InitVar,
    dataclass,
    field,
)

from app.core.security.tenant_types import (
    ACCESS_MODES,
    BLOCKED_B1_PERMISSIONS,
    TENANT_ROLES,
    RestaurantAccessMode,
    TenantAccessDenied,
    TenantPermissionCode,
    TenantRoleCode,
    permission_ceiling,
    positive_id,
)

_ISSUANCE_AUTHORITY = object()

# ==============================================
# VERIFIED DATABASE CONTEXT
# ==============================================


@dataclass(frozen=True, slots=True, kw_only=True)
class TenantContext:
    """Carry one database-verified membership; not a persistent capability.

    The issuance object is process-local, excluded from serialization and never
    accepted from HTTP. Trusted Python code is not a sandbox security boundary.
    Every operation still revalidates the snapshot in its owned transaction.
    """

    identity_id: int
    organization_id: int
    membership_id: int
    role_code: TenantRoleCode
    access_mode: RestaurantAccessMode
    permissions: frozenset[TenantPermissionCode]
    restaurant_ids: frozenset[int]
    identity_revision: int
    organization_revision: int
    membership_revision: int
    role_policy_revision: int
    _proof: InitVar[object]
    _seal: object = field(init=False, repr=False, compare=False)

    # ==============================================
    # VALIDATE VERIFIED TENANT CONTEXT
    # ==============================================

    def __post_init__(self, _proof: object) -> None:
        """Refuse unverified construction and mutable/invalid policy fields."""
        if _proof is not _ISSUANCE_AUTHORITY:
            raise TenantAccessDenied("tenant_context_not_verified")
        for value in (
            self.identity_id,
            self.organization_id,
            self.membership_id,
            self.identity_revision,
            self.organization_revision,
            self.membership_revision,
            self.role_policy_revision,
        ):
            positive_id(value=value)
        if (
            self.role_code not in TENANT_ROLES
            or self.access_mode not in ACCESS_MODES
            or type(self.permissions) is not frozenset
            or type(self.restaurant_ids) is not frozenset
            or not self.permissions.issubset(
                permission_ceiling(role_code=self.role_code)
            )
            or self.permissions.intersection(BLOCKED_B1_PERMISSIONS)
            or (self.role_code == "owner" and self.access_mode != "company-wide")
            or (self.access_mode == "company-wide" and self.restaurant_ids)
        ):
            raise TenantAccessDenied("tenant_context_policy_invalid")
        for restaurant_id in self.restaurant_ids:
            positive_id(value=restaurant_id)
        object.__setattr__(self, "_seal", _ISSUANCE_AUTHORITY)

    # ==============================================
    # ASSERT VERIFIED
    # ==============================================

    def assert_verified(self) -> None:
        """Reject a manually allocated/deserialized object lacking issuance."""
        if getattr(self, "_seal", None) is not _ISSUANCE_AUTHORITY:
            raise TenantAccessDenied("tenant_context_not_verified")

    # ==============================================
    # REQUIRE
    # ==============================================

    def require(self, *, permission: str) -> None:
        """Check explicit policy only; resource scope is checked separately."""
        self.assert_verified()
        if permission in BLOCKED_B1_PERMISSIONS or permission not in self.permissions:
            raise TenantAccessDenied("tenant_permission_denied")


# ==============================================
# ISSUE CONTEXT
# ==============================================


def _issue_context(
    *,
    identity_id: int,
    organization_id: int,
    membership_id: int,
    role_code: TenantRoleCode,
    access_mode: RestaurantAccessMode,
    permissions: frozenset[str],
    restaurant_ids: frozenset[int],
    identity_revision: int,
    organization_revision: int,
    membership_revision: int,
    role_policy_revision: int,
) -> TenantContext:
    """Issue only after the internal resolver verifies locked database rows."""
    return TenantContext(
        identity_id=identity_id,
        organization_id=organization_id,
        membership_id=membership_id,
        role_code=role_code,
        access_mode=access_mode,
        permissions=permissions,
        restaurant_ids=restaurant_ids,
        identity_revision=identity_revision,
        organization_revision=organization_revision,
        membership_revision=membership_revision,
        role_policy_revision=role_policy_revision,
        _proof=_ISSUANCE_AUTHORITY,
    )
