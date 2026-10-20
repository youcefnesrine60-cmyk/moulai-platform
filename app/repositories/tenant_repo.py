# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Flush-only foundation repositories; authorization stays in tenant services."""

from datetime import datetime

from sqlalchemy import (
    ColumnElement,
    Select,
    delete,
    func,
    select,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.restaurant import Restaurant
from app.models.tenant.schema import (
    Identity,
    MembershipRestaurantGrant,
    Organization,
    OrganizationMembership,
    TenantAuditEvent,
    TenantRole,
    TenantRolePermission,
    restaurant_reference,
)
from app.schemas.tenant_access import RestaurantRecord

# ==============================================
# BASE SELECTS
# ==============================================


# ==============================================
# BASE IDENTITY SELECT
# ==============================================


def _base_identity_select() -> Select[tuple[Identity]]:
    """Keep the identity projection explicit and reusable."""
    return select(Identity).execution_options(populate_existing=True)


# ==============================================
# BASE MEMBERSHIP SELECT
# ==============================================


def _base_membership_select() -> Select[tuple[OrganizationMembership]]:
    """Refresh persisted authority, never an identity-map-only permission."""
    return select(OrganizationMembership).execution_options(populate_existing=True)


# ==============================================
# BASE ORGANIZATION SELECT
# ==============================================


def _base_organization_select() -> Select[tuple[Organization]]:
    """Return the company projection without owner-derived authority."""
    return select(Organization).execution_options(populate_existing=True)


# ==============================================
# BASE ROLE SELECT
# ==============================================


def _base_role_select() -> Select[tuple[TenantRole]]:
    """Refresh the explicit tenant policy record independently of platform RBAC."""
    return select(TenantRole).execution_options(populate_existing=True)


# ==============================================
# BASE PERMISSION SELECT
# ==============================================


def _base_permission_select() -> Select[tuple[str]]:
    """Project persisted permission codes without supplying default grants."""
    return select(TenantRolePermission.permission_code)


# ==============================================
# BASE GRANT SELECT
# ==============================================


def _base_grant_select() -> Select[tuple[int]]:
    """Project explicit restaurant grants before applying membership scope."""
    return select(MembershipRestaurantGrant.restaurant_id)


# ==============================================
# BASE RESTAURANT COMPANY SELECT
# ==============================================


def _base_restaurant_company_select() -> Select[tuple[int | None]]:
    """Project the staged company reference without altering live ORM mappings."""
    return select(restaurant_reference.c.organization_id)


# ==============================================
# BASE ACTIVE OWNER COUNT SELECT
# ==============================================


def _base_active_owner_count_select() -> Select[tuple[int]]:
    """Count accepted active owners whose local identity remains active."""
    return (
        select(func.count())
        .select_from(OrganizationMembership)
        .join(Identity, Identity.id == OrganizationMembership.identity_id)
        .where(
            OrganizationMembership.role_code == "owner",
            OrganizationMembership.status == "active",
            OrganizationMembership.access_mode == "company-wide",
            OrganizationMembership.accepted_at.is_not(None),
            OrganizationMembership.activated_at.is_not(None),
            Identity.status == "active",
        )
    )


# ==============================================
# BASE RESTAURANT OUTPUT PROJECTION
# ==============================================


def _base_restaurant_summary_select() -> Select[RestaurantRecord]:
    """Select scalar business fields without lazy-loading owner relationships."""
    return select(
        Restaurant.id,
        Restaurant.name,
        Restaurant.type,
        Restaurant.wilaya,
        Restaurant.is_active,
    )


class IdentityRepository:
    """Resolve exact preapproved associations without provisioning methods."""

    # ==============================================
    # INITIALIZE INSTANCE
    # ==============================================

    def __init__(self, *, session: AsyncSession) -> None:
        """Store the request session and prepare collaborators without SQL IO."""
        self.session = session

    # ==============================================
    # FIND
    # ==============================================

    async def find(self, *, issuer: str, subject: str) -> Identity | None:
        """Find an exact pair; a missing row is never created."""
        result = await self.session.execute(
            _base_identity_select().where(
                Identity.issuer == issuer, Identity.subject == subject
            )
        )
        return result.scalar_one_or_none()

    # ==============================================
    # LOCK
    # ==============================================

    async def lock(self, *, identity_id: int) -> Identity | None:
        """Hold a shared identity lock during bounded authorized work."""
        result = await self.session.execute(
            _base_identity_select()
            .where(Identity.id == identity_id)
            .with_for_update(read=True)
        )
        return result.scalar_one_or_none()


class TenantRepository:
    """Execute company-qualified queries inside a caller-owned transaction."""

    # ==============================================
    # INITIALIZE INSTANCE
    # ==============================================

    def __init__(self, *, session: AsyncSession) -> None:
        """Store the request session and prepare collaborators without SQL IO."""
        self.session = session

    # ==============================================
    # OWN MEMBERSHIP DISCOVERY
    # ==============================================

    async def own_memberships(
        self, *, identity_id: int, after_id: int, limit: int
    ) -> tuple[OrganizationMembership, ...]:
        """Return personal association metadata, never company business records.

        This discovery projection can include inactive history; it grants no
        company selection or restaurant access. The service verifies identity.
        """
        result = await self.session.execute(
            _base_membership_select()
            .join(Identity, Identity.id == OrganizationMembership.identity_id)
            .join(
                TenantRolePermission,
                TenantRolePermission.role_code == OrganizationMembership.role_code,
            )
            .where(
                OrganizationMembership.identity_id == identity_id,
                OrganizationMembership.id > after_id,
                Identity.status == "active",
                TenantRolePermission.permission_code == "tenant.membership.self.read",
            )
            .order_by(OrganizationMembership.id)
            .limit(limit)
        )
        return tuple(result.scalars())

    # ==============================================
    # COMPANY-QUALIFIED RESTAURANT READ
    # ==============================================

    async def restaurants(
        self,
        *,
        organization_id: int,
        scope: ColumnElement[bool],
        after_id: int,
        limit: int,
        restaurant_id: int | None = None
    ) -> tuple[RestaurantRecord, ...]:
        """Apply an explicit company boundary and the service's existing scope.

        The subquery uses the staged reference contract without changing the
        legacy Restaurant mapper or duplicating permission/grant evaluation.
        """
        eligible = select(restaurant_reference.c.id).where(
            restaurant_reference.c.organization_id == organization_id, scope
        )
        statement = (
            _base_restaurant_summary_select()
            .where(Restaurant.id.in_(eligible), Restaurant.id > after_id)
            .order_by(Restaurant.id)
            .limit(limit)
        )
        if restaurant_id is not None:
            statement = statement.where(Restaurant.id == restaurant_id)
        result = await self.session.execute(statement)
        return tuple(result.tuples())

    # ==============================================
    # MEMBERSHIP
    # ==============================================

    async def membership(
        self, *, organization_id: int, identity_id: int
    ) -> OrganizationMembership | None:
        """Find one association without widening to another company."""
        result = await self.session.execute(
            _base_membership_select().where(
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.identity_id == identity_id,
            )
        )
        return result.scalar_one_or_none()

    # ==============================================
    # LOCK ROLE
    # ==============================================

    async def lock_role(self, *, role_code: str) -> TenantRole | None:
        """Prevent concurrent role-policy changes for this transaction."""
        result = await self.session.execute(
            _base_role_select()
            .where(TenantRole.code == role_code)
            .with_for_update(read=True)
        )
        return result.scalar_one_or_none()

    # ==============================================
    # LOCK ORGANIZATION
    # ==============================================

    async def lock_organization(
        self, *, organization_id: int, governance: bool
    ) -> Organization | None:
        """Serialize governance against ordinary shared company operations."""
        result = await self.session.execute(
            _base_organization_select()
            .where(Organization.id == organization_id)
            .with_for_update(read=not governance)
        )
        return result.scalar_one_or_none()

    # ==============================================
    # LOCK MEMBERSHIP
    # ==============================================

    async def lock_membership(
        self, *, organization_id: int, membership_id: int, exclusive: bool = False
    ) -> OrganizationMembership | None:
        """Lock only the selected company's association."""
        result = await self.session.execute(
            _base_membership_select()
            .where(
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.id == membership_id,
            )
            .with_for_update(read=not exclusive)
        )
        return result.scalar_one_or_none()

    # ==============================================
    # PERMISSIONS
    # ==============================================

    async def permissions(self, *, role_code: str) -> frozenset[str]:
        """Read explicit rows; never substitute a default policy template."""
        result = await self.session.execute(
            _base_permission_select().where(TenantRolePermission.role_code == role_code)
        )
        return frozenset(result.scalars())

    # ==============================================
    # GRANTS
    # ==============================================

    async def grants(
        self, *, organization_id: int, membership_id: int
    ) -> frozenset[int]:
        """Read grants with both company and association predicates."""
        result = await self.session.execute(
            _base_grant_select().where(
                MembershipRestaurantGrant.organization_id == organization_id,
                MembershipRestaurantGrant.membership_id == membership_id,
            )
        )
        return frozenset(result.scalars())

    # ==============================================
    # RESTAURANT COMPANY
    # ==============================================

    async def restaurant_company(self, *, restaurant_id: int) -> int | None:
        """Read a schema reference without altering the legacy ORM mapping."""
        result = await self.session.execute(
            _base_restaurant_company_select().where(
                restaurant_reference.c.id == restaurant_id
            )
        )
        return result.scalar_one_or_none()

    # ==============================================
    # HAS ACTIVE OWNER
    # ==============================================

    async def has_active_owner(self, *, organization_id: int) -> bool:
        """Deny unusable staged companies even before E1 trigger installation."""
        result = await self.session.execute(
            _base_active_owner_count_select().where(
                OrganizationMembership.organization_id == organization_id,
            )
        )
        return result.scalar_one() > 0

    # ==============================================
    # REVOKE NON OWNER
    # ==============================================

    async def revoke_non_owner(
        self,
        *,
        membership: OrganizationMembership,
        expected_revision: int,
        now: datetime
    ) -> bool:
        """CAS-revoke only a locked non-owner and clear grants atomically upstream."""
        result = await self.session.execute(
            update(OrganizationMembership)
            .where(
                OrganizationMembership.id == membership.id,
                OrganizationMembership.organization_id == membership.organization_id,
                OrganizationMembership.revision == expected_revision,
                OrganizationMembership.role_code != "owner",
                OrganizationMembership.status.in_(("pending", "active", "suspended")),
            )
            .values(status="revoked", revoked_at=now, revision=expected_revision + 1)
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            return False
        await self.session.execute(
            delete(MembershipRestaurantGrant).where(
                MembershipRestaurantGrant.organization_id == membership.organization_id,
                MembershipRestaurantGrant.membership_id == membership.id,
            )
        )
        return True

    # ==============================================
    # APPEND AUDIT
    # ==============================================

    async def append_audit(self, *, event: TenantAuditEvent) -> None:
        """Flush audit evidence in the mutation transaction without committing."""
        self.session.add(event)
        await self.session.flush()
