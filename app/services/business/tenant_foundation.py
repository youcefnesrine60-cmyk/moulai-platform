# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Opt-in B1 identity, membership and authorization foundation; no API wiring."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import (
    datetime,
    timezone,
)
from typing import cast
from uuid import uuid4

from sqlalchemy import (
    ColumnElement,
    and_,
    false,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.oidc import OIDCPrincipal
from app.core.security.tenant_context import (
    TenantContext,
    _issue_context,
)
from app.core.security.tenant_types import (
    BLOCKED_B1_PERMISSIONS,
    RestaurantAccessMode,
    TenantAccessDenied,
    TenantConflict,
    TenantRoleCode,
    permission_ceiling,
    positive_id,
    validate_identity_key,
)
from app.models.tenant.schema import (
    TenantAuditEvent,
    restaurant_reference,
)
from app.repositories.tenant_repo import (
    IdentityRepository,
    TenantRepository,
)

logger = logging.getLogger(__name__)
_UNIT_KEY = "moulai.tenant.foundation.unit"
_BOUND_KEY = "moulai.tenant.foundation.bound"

# ==============================================
# OWNED ATOMIC UNIT OF WORK
# ==============================================


# ==============================================
# TENANT UNIT OF WORK
# ==============================================


@asynccontextmanager
async def tenant_unit_of_work(*, session: AsyncSession) -> AsyncIterator[None]:
    """Own one transaction, refusing pending or already-autobegun work."""
    if session.in_transaction() or session.new or session.dirty or session.deleted:
        raise TenantConflict("tenant_clean_transaction_required")
    async with session.begin():
        session.info[_UNIT_KEY] = object()
        try:
            yield
        finally:
            session.info.pop(_UNIT_KEY, None)


# ==============================================
# REQUIRE UNIT
# ==============================================


def _require_unit(*, session: AsyncSession) -> None:
    """Refuse SQL outside the owned boundary or with unauthorized pending IO."""
    if not session.in_transaction() or _UNIT_KEY not in session.info:
        raise TenantConflict("tenant_owned_transaction_required")
    if session.new or session.dirty or session.deleted:
        raise TenantConflict("tenant_clean_session_required")


class IdentityService:
    """Resolve only a caller-verified OIDC principal; never enroll on login."""

    # ==============================================
    # INITIALIZE INSTANCE
    # ==============================================

    def __init__(self, *, session: AsyncSession) -> None:
        """Store the request session and prepare collaborators without SQL IO."""
        self.session = session
        self.repo = IdentityRepository(session=session)

    # ==============================================
    # RESOLVE ID
    # ==============================================

    async def resolve_id(self, *, principal: OIDCPrincipal) -> int:
        """Require an existing active exact association; no profile mutations."""
        _require_unit(session=self.session)
        if not isinstance(principal, OIDCPrincipal):
            raise TenantAccessDenied("verified_principal_required")
        validate_identity_key(issuer=principal.issuer, subject=principal.subject)
        identity = await self.repo.find(
            issuer=principal.issuer, subject=principal.subject
        )
        if identity is None or identity.status != "active":
            raise TenantAccessDenied("tenant_identity_unavailable")
        return identity.id


class TenantContextResolver:
    """Resolve locked database authority, not Keycloak/global RBAC roles."""

    # ==============================================
    # INITIALIZE INSTANCE
    # ==============================================

    def __init__(self, *, session: AsyncSession) -> None:
        """Store the request session and prepare collaborators without SQL IO."""
        self.session = session
        self.identities = IdentityRepository(session=session)
        self.repo = TenantRepository(session=session)

    # ==============================================
    # RESOLVE
    # ==============================================

    async def resolve(
        self, *, principal: OIDCPrincipal, organization_id: int
    ) -> TenantContext:
        """Create a read/business snapshot without installing any route guard."""
        return await self._resolve(
            principal=principal, organization_id=organization_id, governance=False
        )

    # ==============================================
    # RESOLVE
    # ==============================================

    async def _resolve(
        self, *, principal: OIDCPrincipal, organization_id: int, governance: bool
    ) -> TenantContext:
        """Discover targets, lock consistently, reload and deny changed authority."""
        _require_unit(session=self.session)
        positive_id(value=organization_id)
        identity_id = await IdentityService(session=self.session).resolve_id(
            principal=principal
        )
        member = await self.repo.membership(
            organization_id=organization_id, identity_id=identity_id
        )
        if member is None:
            raise TenantAccessDenied("tenant_membership_unavailable")
        member_id, role_code, member_revision = (
            member.id,
            member.role_code,
            member.revision,
        )
        binding = (identity_id, organization_id, member_id, governance)
        existing_binding = self.session.info.get(_BOUND_KEY)
        if existing_binding is not None and existing_binding != binding:
            raise TenantConflict("tenant_session_cannot_rebind_or_upgrade")
        role = await self.repo.lock_role(role_code=role_code)
        identity = await self.identities.lock(identity_id=identity_id)
        organization = await self.repo.lock_organization(
            organization_id=organization_id, governance=governance
        )
        member = await self.repo.lock_membership(
            organization_id=organization_id, membership_id=member_id
        )
        if (
            role is None
            or identity is None
            or identity.status != "active"
            or organization is None
            or organization.status != "active"
            or organization.tenant_enforced_at is None
            or member is None
            or member.status != "active"
            or member.accepted_at is None
            or member.activated_at is None
            or member.identity_id != identity_id
            or member.role_code != role_code
            or member.revision != member_revision
            or not await self.repo.has_active_owner(organization_id=organization_id)
        ):
            raise TenantAccessDenied("tenant_authority_unavailable")
        permissions = await self.repo.permissions(role_code=role_code)
        if not permissions.issubset(permission_ceiling(role_code=role_code)):
            raise TenantAccessDenied("tenant_policy_invalid")
        grants = await self.repo.grants(
            organization_id=organization_id, membership_id=member_id
        )
        if member.access_mode == "company-wide" and grants:
            raise TenantAccessDenied("tenant_grants_invalid")
        context = _issue_context(
            identity_id=identity_id,
            organization_id=organization_id,
            membership_id=member_id,
            role_code=cast(TenantRoleCode, role_code),
            access_mode=cast(RestaurantAccessMode, member.access_mode),
            permissions=permissions - BLOCKED_B1_PERMISSIONS,
            restaurant_ids=grants,
            identity_revision=identity.revision,
            organization_revision=organization.revision,
            membership_revision=member.revision,
            role_policy_revision=role.policy_revision,
        )
        self.session.info[_BOUND_KEY] = binding
        return context


class TenantAuthorizationService:
    """Revalidate snapshots and scope resources; contains no business mutations."""

    # ==============================================
    # INITIALIZE INSTANCE
    # ==============================================

    def __init__(self, *, session: AsyncSession) -> None:
        """Store the request session and prepare collaborators without SQL IO."""
        self.session = session
        self.repo = TenantRepository(session=session)

    # ==============================================
    # REQUIRE CURRENT
    # ==============================================

    async def require_current(self, *, context: TenantContext, permission: str) -> None:
        """Refuse fabricated, stale, revoked or policy-incompatible authority."""
        _require_unit(session=self.session)
        context.require(permission=permission)
        binding = self.session.info.get(_BOUND_KEY)
        if binding is None or binding[:3] != (
            context.identity_id,
            context.organization_id,
            context.membership_id,
        ):
            raise TenantAccessDenied("tenant_session_not_resolved")
        role = await self.repo.lock_role(role_code=context.role_code)
        identity = await IdentityRepository(session=self.session).lock(
            identity_id=context.identity_id
        )
        org = await self.repo.lock_organization(
            organization_id=context.organization_id, governance=binding[3]
        )
        member = await self.repo.lock_membership(
            organization_id=context.organization_id, membership_id=context.membership_id
        )
        if (
            role is None
            or role.policy_revision != context.role_policy_revision
            or identity is None
            or identity.status != "active"
            or identity.revision != context.identity_revision
            or org is None
            or org.status != "active"
            or org.tenant_enforced_at is None
            or org.revision != context.organization_revision
            or member is None
            or member.status != "active"
            or member.accepted_at is None
            or member.activated_at is None
            or member.identity_id != context.identity_id
            or member.role_code != context.role_code
            or member.access_mode != context.access_mode
            or member.revision != context.membership_revision
            or not await self.repo.has_active_owner(
                organization_id=context.organization_id
            )
            or await self.repo.permissions(role_code=context.role_code)
            - BLOCKED_B1_PERMISSIONS
            != context.permissions
            or await self.repo.grants(
                organization_id=context.organization_id,
                membership_id=context.membership_id,
            )
            != context.restaurant_ids
        ):
            raise TenantAccessDenied("tenant_context_stale_or_revoked")

    # ==============================================
    # REQUIRE RESTAURANT
    # ==============================================

    async def require_restaurant(
        self, *, context: TenantContext, restaurant_id: int, permission: str
    ) -> None:
        """Require company equality even for the same legacy business owner."""
        positive_id(value=restaurant_id)
        await self.require_current(context=context, permission=permission)
        company = await self.repo.restaurant_company(restaurant_id=restaurant_id)
        if company != context.organization_id or (
            context.access_mode == "explicit-grants"
            and restaurant_id not in context.restaurant_ids
        ):
            raise TenantAccessDenied("tenant_resource_unavailable")


# ==============================================
# RESTAURANT SCOPE
# ==============================================


def restaurant_scope(*, context: TenantContext) -> ColumnElement[bool]:
    """Build an explicit predicate, never interpreting an empty grant set as all.

    This predicate alone is not authorization: callers must first use the
    current-state service in their owned transaction.
    """
    context.assert_verified()
    company = restaurant_reference.c.organization_id == context.organization_id
    if context.access_mode == "company-wide":
        return company
    if not context.restaurant_ids:
        return false()
    return and_(company, restaurant_reference.c.id.in_(context.restaurant_ids))


@dataclass(frozen=True, slots=True)
class MembershipMutation:
    """Return local mutation evidence without ORM instances or credentials."""

    membership_id: int
    revision: int
    status: str


class MembershipService:
    """Provide bounded non-owner revocation; no promotion/linking/bootstrap API."""

    # ==============================================
    # INITIALIZE INSTANCE
    # ==============================================

    def __init__(self, *, session: AsyncSession) -> None:
        """Store the request session and prepare collaborators without SQL IO."""
        self.session = session
        self.repo = TenantRepository(session=session)

    # ==============================================
    # REVOKE NON OWNER
    # ==============================================

    async def revoke_non_owner(
        self,
        *,
        principal: OIDCPrincipal,
        organization_id: int,
        membership_id: int,
        expected_revision: int
    ) -> MembershipMutation:
        """Atomically revoke a non-owner, clear grants and append audit evidence.

        Owner changes intentionally have no implementation entry point in B1:
        they require the separately reviewed last-owner/acceptance machinery.
        A savepoint protects the caller even if it catches a mutation failure.
        """
        _require_unit(session=self.session)
        positive_id(value=membership_id)
        positive_id(value=expected_revision)
        async with self.session.begin_nested():
            actor = await TenantContextResolver(session=self.session)._resolve(
                principal=principal, organization_id=organization_id, governance=True
            )
            actor.require(permission="tenant.memberships.manage")
            if actor.role_code != "owner":
                raise TenantAccessDenied("tenant_owner_required")
            member = await self.repo.lock_membership(
                organization_id=organization_id,
                membership_id=membership_id,
                exclusive=True,
            )
            if member is None or member.role_code == "owner":
                raise TenantAccessDenied("tenant_non_owner_target_required")
            if member.revision != expected_revision or member.status == "revoked":
                raise TenantConflict("tenant_membership_revision_conflict")
            target_identity, generation = (
                member.identity_id,
                member.enrollment_generation,
            )
            previous_grants = await self.repo.grants(
                organization_id=organization_id, membership_id=membership_id
            )
            previous_policy = {
                "role": member.role_code,
                "mode": member.access_mode,
                "status": member.status,
                "restaurant_ids": sorted(previous_grants),
            }
            if not await self.repo.revoke_non_owner(
                membership=member,
                expected_revision=expected_revision,
                now=datetime.now(timezone.utc),
            ):
                raise TenantConflict("tenant_membership_revision_conflict")
            await self.repo.append_audit(
                event=TenantAuditEvent(
                    organization_id=organization_id,
                    actor_kind="tenant",
                    actor_identity_id=actor.identity_id,
                    actor_membership_id=actor.membership_id,
                    target_identity_id=target_identity,
                    target_membership_id=membership_id,
                    action="membership.revoked",
                    previous_revision=expected_revision,
                    resulting_revision=expected_revision + 1,
                    enrollment_generation=generation,
                    reason_code="owner_revocation",
                    correlation_id=uuid4().hex,
                    policy_before=previous_policy,
                    policy_after={
                        **previous_policy,
                        "status": "revoked",
                        "restaurant_ids": [],
                    },
                )
            )
        logger.info(
            "Tenant membership revocation staged",
            extra={"organization_id": organization_id, "membership_id": membership_id},
        )
        return MembershipMutation(
            membership_id=membership_id,
            revision=expected_revision + 1,
            status="revoked",
        )
