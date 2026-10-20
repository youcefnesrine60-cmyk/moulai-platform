# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Functional tenant reads through the existing PostgreSQL authority services."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import (
    dataclass,
    field,
)
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.oidc import OIDCPrincipal
from app.core.security.tenant_context import TenantContext
from app.core.security.tenant_types import (
    BLOCKED_B1_PERMISSIONS,
    TENANT_PERMISSIONS,
    RestaurantAccessMode,
    TenantAccessDenied,
    TenantConflict,
    TenantRoleCode,
    positive_id,
)
from app.repositories.tenant_repo import TenantRepository
from app.schemas.tenant_access import (
    MembershipStatus,
    MembershipSummary,
    RestaurantRecord,
    RestaurantSummary,
)
from app.services.business.tenant_foundation import (
    IdentityService,
    TenantAuthorizationService,
    TenantContextResolver,
    restaurant_scope,
    tenant_unit_of_work,
)

# ==============================================
# BOUNDED PAGINATION
# ==============================================


def validate_page(*, after_id: int, limit: int) -> None:
    """Reject bools, negative cursors and unbounded reads before SQL."""
    if (
        type(after_id) is not int
        or after_id < 0
        or type(limit) is not int
        or not 1 <= limit <= 100
    ):
        raise ValueError("tenant_page_invalid")


# ==============================================
# CLOSED PERMISSION VOCABULARY
# ==============================================


def validate_permission(*, permission: str) -> None:
    """Refuse platform permissions, unknown names and unreleased fulfillment."""
    if permission not in TENANT_PERMISSIONS or permission in BLOCKED_B1_PERMISSIONS:
        raise ValueError("tenant_permission_unavailable")


# ==============================================
# DETACHED RESTAURANT OUTPUT
# ==============================================


def _restaurant_output(*, record: RestaurantRecord) -> RestaurantSummary:
    """Copy only authorized scalar fields; never return an ORM entity."""
    return RestaurantSummary(
        id=record[0],
        name=record[1],
        type=record[2],
        wilaya=record[3],
        is_active=record[4],
    )


@dataclass(slots=True)
class _ReadLease:
    """Close the functional facade when its transaction ends."""

    active: bool = True


@dataclass(frozen=True, slots=True, kw_only=True)
class TenantReadUnit:
    """Expose bounded reads for one resolved company inside its live transaction."""

    context: TenantContext
    _session: AsyncSession = field(repr=False)
    _lease: _ReadLease = field(repr=False)

    # ==============================================
    # LIVE TRANSACTION AND CURRENT DATABASE AUTHORITY
    # ==============================================

    async def _require(self, *, permission: str) -> None:
        """Revalidate through the existing service for every business operation."""
        if not self._lease.active:
            raise TenantConflict("tenant_read_unit_closed")
        await TenantAuthorizationService(session=self._session).require_current(
            context=self.context, permission=permission
        )

    # ==============================================
    # SELECTED OWN MEMBERSHIP METADATA
    # ==============================================

    async def membership(self) -> MembershipSummary:
        """Allow minimal personal metadata even when explicit grants are empty."""
        await self._require(permission="tenant.membership.self.read")
        return MembershipSummary(
            id=self.context.membership_id,
            organization_id=self.context.organization_id,
            role=self.context.role_code,
            access_mode=self.context.access_mode,
            status="active",
            revision=self.context.membership_revision,
        )

    # ==============================================
    # VISIBLE RESTAURANTS
    # ==============================================

    async def restaurants(
        self, *, after_id: int = 0, limit: int = 50
    ) -> tuple[RestaurantSummary, ...]:
        """Read only the selected company's current permitted restaurant set."""
        validate_page(after_id=after_id, limit=limit)
        await self._require(permission="tenant.restaurants.read")
        records = await TenantRepository(session=self._session).restaurants(
            organization_id=self.context.organization_id,
            scope=restaurant_scope(context=self.context),
            after_id=after_id,
            limit=limit,
        )
        return tuple(_restaurant_output(record=record) for record in records)

    # ==============================================
    # ONE PERMITTED RESTAURANT
    # ==============================================

    async def restaurant(self, *, restaurant_id: int) -> RestaurantSummary:
        """Use the same denial for an absent, foreign or ungranted resource."""
        positive_id(value=restaurant_id)
        await self._require(permission="tenant.restaurants.read")
        await TenantAuthorizationService(session=self._session).require_restaurant(
            context=self.context,
            restaurant_id=restaurant_id,
            permission="tenant.restaurants.read",
        )
        records = await TenantRepository(session=self._session).restaurants(
            organization_id=self.context.organization_id,
            scope=restaurant_scope(context=self.context),
            after_id=0,
            limit=1,
            restaurant_id=restaurant_id,
        )
        if not records:
            raise TenantAccessDenied("tenant_resource_unavailable")
        return _restaurant_output(record=records[0])


class TenantAccessService:
    """Compose existing identity/membership/context services without new grants."""

    # ==============================================
    # ISOLATED REQUEST SESSION
    # ==============================================

    def __init__(self, *, session: AsyncSession) -> None:
        """Require a dedicated SQLAlchemy session, separate from owner scoping."""
        if not isinstance(session, AsyncSession):
            raise TypeError("tenant_async_session_required")
        # This is the established owner guard's session binding; never mix it
        # with membership authorization on the same identity map/transaction.
        if "moulai_authenticated_owner_scope" in session.info:
            raise TenantConflict("tenant_owner_session_mixing_forbidden")
        self.session = session

    # ==============================================
    # PERSONAL MEMBERSHIP DISCOVERY
    # ==============================================

    async def own_memberships(
        self, *, principal: OIDCPrincipal, after_id: int = 0, limit: int = 50
    ) -> tuple[MembershipSummary, ...]:
        """List personal metadata only; inactive entries never authorize entry."""
        validate_page(after_id=after_id, limit=limit)
        async with tenant_unit_of_work(session=self.session):
            identity_id = await IdentityService(session=self.session).resolve_id(
                principal=principal
            )
            rows = await TenantRepository(session=self.session).own_memberships(
                identity_id=identity_id, after_id=after_id, limit=limit
            )
            return tuple(
                MembershipSummary(
                    id=row.id,
                    organization_id=row.organization_id,
                    role=cast(TenantRoleCode, row.role_code),
                    access_mode=cast(RestaurantAccessMode, row.access_mode),
                    status=cast(MembershipStatus, row.status),
                    revision=row.revision,
                )
                for row in rows
            )

    # ==============================================
    # ONE COMPANY, ONE OWNED AUTHORIZED TRANSACTION
    # ==============================================

    @asynccontextmanager
    async def authorized(
        self, *, principal: OIDCPrincipal, organization_id: int, permission: str
    ) -> AsyncIterator[TenantReadUnit]:
        """Keep current authority locked until the bounded operation completes."""
        positive_id(value=organization_id)
        validate_permission(permission=permission)
        lease = _ReadLease()
        try:
            async with tenant_unit_of_work(session=self.session):
                context = await TenantContextResolver(session=self.session).resolve(
                    principal=principal, organization_id=organization_id
                )
                await TenantAuthorizationService(session=self.session).require_current(
                    context=context, permission=permission
                )
                yield TenantReadUnit(
                    context=context, _session=self.session, _lease=lease
                )
        finally:
            lease.active = False
