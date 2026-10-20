# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Targeted tenant reads using actual local SQL; no G2 migration repetition."""

from collections.abc import Iterator
from dataclasses import FrozenInstanceError
from typing import Any

import pytest
from sqlalchemy import (
    Engine,
    delete,
    event,
    text,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.oidc import OIDCPrincipal
from app.core.security.tenant_scope import bind_owner_scope
from app.core.security.tenant_types import (
    TenantAccessDenied,
    TenantConflict,
)
from app.models.tenant.schema import (
    Identity,
    MembershipRestaurantGrant,
    Organization,
    OrganizationMembership,
    TenantRolePermission,
)
from app.services.business.tenant_access import TenantAccessService
from tests.test_tenant_foundation import (
    ISSUER,
    MemoryAsyncSession,
    local_engine,
    principal,
)

__all__ = ["local_engine"]

READ = "tenant.restaurants.read"


# ==============================================
# EXTEND ONLY THE DISPOSABLE MEMORY RESTAURANT PROJECTION
# ==============================================


@pytest.fixture
def read_engine(local_engine: Engine) -> Engine:
    """Add scalar fields to the existing B1 memory fixture, never a live schema."""
    with local_engine.begin() as connection:
        for column in (
            "name TEXT NOT NULL DEFAULT 'Synthetic'",
            "type TEXT NOT NULL DEFAULT 'fixture'",
            "wilaya TEXT NOT NULL DEFAULT 'Fixture'",
            "is_active BOOLEAN DEFAULT 1",
        ):
            connection.exec_driver_sql("ALTER TABLE restaurants ADD COLUMN " + column)
        connection.execute(text("UPDATE restaurants SET name='Restaurant ' || id"))
    return local_engine


# ==============================================
# DEDICATED REAL ASYNCSESSION INTERFACE
# ==============================================


@pytest.fixture
def read_session(read_engine: Engine) -> Iterator[AsyncSession]:
    """Execute real SQL in memory without asyncpg or an external connection."""
    session = MemoryAsyncSession(expire_on_commit=False)
    session.sync_session.bind = read_engine
    yield session
    session.sync_session.close()


# ==============================================
# SAME OWNER, DISTINCT COMPANIES AND DETACHED OUTPUTS
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("company,expected", [(1, [100, 101]), (2, [200])])
async def test_company_read_does_not_union_owner_restaurants(
    read_session: AsyncSession, company: int, expected: list[int]
) -> None:
    """Actual SQL stays company-qualified despite a shared legacy owner ID."""
    async with TenantAccessService(session=read_session).authorized(
        principal=principal(), organization_id=company, permission=READ
    ) as unit:
        rows = await unit.restaurants()
        assert [row.id for row in rows] == expected
        assert rows[0].name == f"Restaurant {expected[0]}"
        assert (await unit.membership()).organization_id == company
        assert (await unit.restaurant(restaurant_id=expected[0])).id == expected[0]
        with pytest.raises(FrozenInstanceError):
            rows[0].name = "Changed"  # type: ignore[misc]
    assert not read_session.in_transaction()
    with pytest.raises(TenantConflict, match="tenant_read_unit_closed"):
        await unit.restaurants()
    assert rows[0].name == f"Restaurant {expected[0]}"


# ==============================================
# EXACT EMPLOYEE GRANTS AND EMPTY SET DENIAL
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("empty", [False, True])
async def test_employee_scope_and_personal_metadata(
    read_session: AsyncSession, read_engine: Engine, empty: bool
) -> None:
    """An empty grant set retains only personal metadata, with zero restaurants."""
    if empty:
        with read_engine.begin() as connection:
            connection.execute(
                delete(MembershipRestaurantGrant).where(
                    MembershipRestaurantGrant.membership_id == 20
                )
            )
    async with TenantAccessService(session=read_session).authorized(
        principal=principal(subject="fixture-employee"),
        organization_id=1,
        permission=READ,
    ) as unit:
        assert [row.id for row in await unit.restaurants()] == ([] if empty else [100])
        assert (await unit.membership()).id == 20
        for value in ([100, 101, 200, 999] if empty else [101, 200, 999]):
            with pytest.raises(TenantAccessDenied, match="tenant_resource_unavailable"):
                await unit.restaurant(restaurant_id=value)


# ==============================================
# PERSONAL DISCOVERY IS NOT BUSINESS ACCESS
# ==============================================


@pytest.mark.asyncio
async def test_own_memberships_are_identity_qualified(
    read_session: AsyncSession, read_engine: Engine
) -> None:
    """Return only own minimal associations, including inactive history."""
    with read_engine.begin() as connection:
        connection.execute(
            update(OrganizationMembership)
            .where(OrganizationMembership.id == 11)
            .values(status="revoked", revoked_at=text("CURRENT_TIMESTAMP"), revision=2)
        )
    service = TenantAccessService(session=read_session)
    rows = await service.own_memberships(principal=principal())
    assert [row.id for row in rows] == [10, 11]
    assert rows[1].status == "revoked"
    assert not hasattr(rows[0], "permissions") and not hasattr(rows[0], "issuer")
    assert [
        row.id
        for row in await service.own_memberships(
            principal=principal(), after_id=10, limit=1
        )
    ] == [11]
    with pytest.raises(TenantAccessDenied):
        async with service.authorized(
            principal=principal(), organization_id=2, permission=READ
        ):
            pytest.fail("inactive history authorized business access")


# ==============================================
# ABSENT IDENTITY AND ISSUER COLLISIONS NEVER ENROLL
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "subject,issuer",
    [
        ("owner-test", ISSUER),
        ("fixture-owner", "https://other.example.test/realm"),
        ("fixture-unlinked", ISSUER),
    ],
)
async def test_no_automatic_identity_or_membership_link(
    read_session: AsyncSession, read_engine: Engine, subject: str, issuer: str
) -> None:
    """Realm owner/admin roles cannot create an association or borrow a subject."""
    user = OIDCPrincipal(
        subject=subject, issuer=issuer, realm_roles=frozenset({"owner", "admin"})
    )
    with read_engine.connect() as connection:
        before = connection.scalar(text("SELECT count(*) FROM identities"))
    service = TenantAccessService(session=read_session)
    with pytest.raises(TenantAccessDenied):
        async with service.authorized(
            principal=user, organization_id=1, permission=READ
        ):
            pytest.fail("unassociated caller entered the company")
    with read_engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM identities")) == before


# ==============================================
# PERSONAL PAGINATION IS BOUNDED BEFORE SQL
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "after,limit", [(-1, 10), (True, 10), (0, 0), (0, 101), (0, True)]
)
async def test_invalid_page_is_rejected_before_io(
    read_session: AsyncSession, read_engine: Engine, after: int, limit: int
) -> None:
    """Malformed pagination cannot reach even an identity lookup."""
    statements: list[str] = []

    # ==============================================
    # OBSERVE ACTUAL MEMORY SQL
    # ==============================================
    def observe(
        connection: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        """Keep only local fixture statements for the no-IO assertion."""
        statements.append(statement)

    event.listen(read_engine, "before_cursor_execute", observe)
    with pytest.raises(ValueError, match="tenant_page_invalid"):
        await TenantAccessService(session=read_session).own_memberships(
            principal=principal(), after_id=after, limit=limit
        )
    assert not statements and not read_session.in_transaction()


# ==============================================
# CURSOR BOUNDS AND CROSS-COMPANY DIRECT READS
# ==============================================


@pytest.mark.asyncio
async def test_pagination_and_foreign_resource_are_scoped(
    read_session: AsyncSession,
) -> None:
    """A cursor cannot widen scope, and direct foreign IDs have no fallback."""
    async with TenantAccessService(session=read_session).authorized(
        principal=principal(), organization_id=1, permission=READ
    ) as unit:
        assert [row.id for row in await unit.restaurants(limit=1)] == [100]
        assert [row.id for row in await unit.restaurants(after_id=100, limit=1)] == [
            101
        ]
        assert await unit.restaurants(after_id=101) == ()
        with pytest.raises(TenantAccessDenied):
            await unit.restaurant(restaurant_id=200)


# ==============================================
# DATABASE STATES AND STORED POLICY ARE AUTHORITATIVE
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "change", ["identity", "company", "membership", "policy", "enforcement"]
)
async def test_current_database_authority_is_required(
    read_session: AsyncSession, read_engine: Engine, change: str
) -> None:
    """Stored suspension, missing permission or missing enforcement denies reads."""
    with read_engine.begin() as connection:
        if change == "identity":
            connection.execute(
                update(Identity)
                .where(Identity.id == 1)
                .values(status="suspended", revision=2)
            )
        elif change == "company":
            connection.execute(
                update(Organization)
                .where(Organization.id == 1)
                .values(status="suspended", revision=2)
            )
        elif change == "membership":
            connection.execute(
                update(OrganizationMembership)
                .where(OrganizationMembership.id == 10)
                .values(
                    status="suspended",
                    suspended_at=text("CURRENT_TIMESTAMP"),
                    revision=2,
                )
            )
        elif change == "enforcement":
            connection.execute(
                update(Organization)
                .where(Organization.id == 1)
                .values(status="draft", tenant_enforced_at=None, revision=2)
            )
        else:
            connection.execute(
                delete(TenantRolePermission).where(
                    TenantRolePermission.role_code == "owner",
                    TenantRolePermission.permission_code == READ,
                )
            )
    with pytest.raises(TenantAccessDenied):
        async with TenantAccessService(session=read_session).authorized(
            principal=principal(), organization_id=1, permission=READ
        ):
            pytest.fail("unavailable authority yielded a read facade")
    assert not read_session.in_transaction()


# ==============================================
# EVERY BUSINESS METHOD RECHECKS ITS OWN PERMISSION
# ==============================================


@pytest.mark.asyncio
async def test_metadata_permission_does_not_authorize_restaurant_reads(
    read_session: AsyncSession, read_engine: Engine
) -> None:
    """A minimal membership dependency cannot bypass the action's stored policy."""
    with read_engine.begin() as connection:
        connection.execute(
            delete(TenantRolePermission).where(
                TenantRolePermission.role_code == "employee",
                TenantRolePermission.permission_code == READ,
            )
        )
    async with TenantAccessService(session=read_session).authorized(
        principal=principal(subject="fixture-employee"),
        organization_id=1,
        permission="tenant.membership.self.read",
    ) as unit:
        assert (await unit.membership()).id == 20
        with pytest.raises(TenantAccessDenied, match="tenant_permission_denied"):
            await unit.restaurants()


# ==============================================
# TRANSACTION BOUNDARIES AND NO OWNER-SCOPE MIXING
# ==============================================


@pytest.mark.asyncio
async def test_legacy_scope_and_existing_transaction_are_refused(
    read_session: AsyncSession,
) -> None:
    """The new facade neither adopts owner scope nor commits an existing unit."""
    await read_session.execute(text("SELECT 1"))
    with pytest.raises(TenantConflict, match="tenant_clean_transaction_required"):
        async with TenantAccessService(session=read_session).authorized(
            principal=principal(), organization_id=1, permission=READ
        ):
            pytest.fail("autobegun transaction was adopted")
    assert read_session.in_transaction()
    await read_session.rollback()
    bind_owner_scope(session=read_session, owner_id=77)
    with pytest.raises(TenantConflict, match="tenant_owner_session_mixing_forbidden"):
        TenantAccessService(session=read_session)


# ==============================================
# NO REBIND OR UNRELEASED ACTION
# ==============================================


@pytest.mark.asyncio
async def test_no_company_switch_or_platform_permission(
    read_session: AsyncSession,
) -> None:
    """One session stays company-bound, and platform/fulfillment names fail shut."""
    service = TenantAccessService(session=read_session)
    for permission in ("payments.review", "tenant.orders.fulfill", "tenant.unknown"):
        with pytest.raises(ValueError, match="tenant_permission_unavailable"):
            async with service.authorized(
                principal=principal(), organization_id=1, permission=permission
            ):
                pytest.fail("unreleased permission accepted")
    async with service.authorized(
        principal=principal(), organization_id=1, permission=READ
    ):
        pass
    with pytest.raises(TenantConflict, match="tenant_session_cannot_rebind_or_upgrade"):
        async with service.authorized(
            principal=principal(), organization_id=2, permission=READ
        ):
            pytest.fail("company binding was changed")


# ==============================================
# STALE DATABASE SNAPSHOT CANNOT AUTHORIZE ANOTHER READ
# ==============================================


@pytest.mark.asyncio
async def test_each_read_revalidates_context_revision(
    read_session: AsyncSession,
) -> None:
    """Simulate revision drift in the local fixture after context resolution."""
    with pytest.raises(TenantAccessDenied, match="tenant_context_stale_or_revoked"):
        async with TenantAccessService(session=read_session).authorized(
            principal=principal(), organization_id=1, permission=READ
        ) as unit:
            await read_session.execute(
                update(Identity).where(Identity.id == 1).values(revision=2)
            )
            await unit.restaurants()
    assert not read_session.in_transaction()


# ==============================================
# FAILED HANDLER CLOSES ITS READ LEASE AND TRANSACTION
# ==============================================


@pytest.mark.asyncio
async def test_failed_operation_closes_read_unit(read_session: AsyncSession) -> None:
    """No facade survives an exception leaving its owned unit of work."""
    with pytest.raises(RuntimeError, match="synthetic_handler_failure"):
        async with TenantAccessService(session=read_session).authorized(
            principal=principal(), organization_id=1, permission=READ
        ) as unit:
            raise RuntimeError("synthetic_handler_failure")
    assert not read_session.in_transaction()
    with pytest.raises(TenantConflict, match="tenant_read_unit_closed"):
        await unit.membership()


# ==============================================
# DISCOVERY ALSO REQUIRES AN EXPLICIT STORED SELF-READ PERMISSION
# ==============================================


@pytest.mark.asyncio
async def test_membership_discovery_has_no_permission_fallback(
    read_session: AsyncSession, read_engine: Engine
) -> None:
    """Removing the stored self-read row hides personal associations as well."""
    with read_engine.begin() as connection:
        connection.execute(
            delete(TenantRolePermission).where(
                TenantRolePermission.role_code == "owner",
                TenantRolePermission.permission_code == "tenant.membership.self.read",
            )
        )
    assert (
        await TenantAccessService(session=read_session).own_memberships(
            principal=principal()
        )
        == ()
    )
