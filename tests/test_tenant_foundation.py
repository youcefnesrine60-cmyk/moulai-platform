# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Execute isolated SQL contracts; never connect to Neon or real Keycloak."""

import re
from collections.abc import Iterator
from dataclasses import (
    FrozenInstanceError,
    asdict,
    replace,
)
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from pathlib import Path
from sqlite3 import Connection as SQLiteConnection
from typing import Any
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import (
    Connection,
    Engine,
    create_engine,
    delete,
    event,
    func,
    insert,
    select,
    update,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Result
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import configure_mappers
from sqlalchemy.pool import ConnectionPoolEntry
from sqlalchemy.schema import CreateTable
from sqlalchemy.sql import Executable

from app.core.security.oidc import OIDCPrincipal
from app.core.security.tenant_context import TenantContext
from app.core.security.tenant_types import (
    TENANT_PERMISSIONS,
    TENANT_ROLES,
    TenantAccessDenied,
    TenantConflict,
    permission_ceiling,
    validate_identity_key,
)
from app.models.base import Base
from app.models.restaurant import Restaurant
from app.models.tenant.schema import (
    TENANT_METADATA,
    Identity,
    MembershipChangeProposal,
    MembershipProposalRestaurant,
    MembershipRestaurantGrant,
    Organization,
    OrganizationMembership,
    TenantAuditEvent,
    TenantBase,
    TenantRole,
    TenantRolePermission,
    restaurant_reference,
)
from app.repositories.tenant_repo import TenantRepository
from app.services.business.tenant_foundation import (
    IdentityService,
    MembershipService,
    TenantAuthorizationService,
    TenantContextResolver,
    restaurant_scope,
    tenant_unit_of_work,
)

ISSUER = "https://identity.example.test/realms/moulai"
NOW = datetime.now(timezone.utc)


# ==============================================
# PRINCIPAL
# ==============================================


def principal(*, subject: str = "fixture-owner", issuer: str = ISSUER) -> OIDCPrincipal:
    """Represent an already verified internal principal, not an HTTP body."""
    return OIDCPrincipal(
        subject=subject, issuer=issuer, realm_roles=frozenset({"owner", "admin"})
    )


# ==============================================
# LOCAL SQLITE FIXTURE AND REAL ASYNCSESSION INTERFACE
# ==============================================


# ==============================================
# LOCAL ENGINE
# ==============================================


@pytest.fixture
def local_engine() -> Iterator[Engine]:
    """Create a disposable memory DB with FKs; SQL never leaves this process.

    AsyncSession's public sync_session is bound to local SQLite for unit SQL
    execution, not async-driver/locking evidence. PostgreSQL semantics need B2.
    """
    engine = create_engine("sqlite+pysqlite:///:memory:")

    # ==============================================
    # SETUP
    # ==============================================

    @event.listens_for(engine, "connect")
    def setup(connection: SQLiteConnection, record: ConnectionPoolEntry) -> None:
        """Enable exact collation, foreign keys and explicit memory transactions."""
        connection.isolation_level = None
        connection.create_collation(
            "C", lambda left, right: (left > right) - (left < right)
        )
        connection.execute("PRAGMA foreign_keys=ON")

    # ==============================================
    # BEGIN
    # ==============================================

    @event.listens_for(engine, "begin")
    def begin(connection: Connection) -> None:
        """Begin an actual SQLite transaction for reliable savepoint rollback tests."""
        connection.exec_driver_sql("BEGIN")

    TENANT_METADATA.create_all(engine)
    with engine.begin() as connection:
        for role in sorted(TENANT_ROLES):
            connection.execute(insert(TenantRole).values(code=role, policy_revision=1))
            connection.execute(
                insert(TenantRolePermission),
                [
                    {"role_code": role, "permission_code": code}
                    for code in sorted(permission_ceiling(role_code=role))
                ],
            )
        connection.execute(
            insert(Identity),
            [
                {
                    "id": 1,
                    "issuer": ISSUER,
                    "subject": "fixture-owner",
                    "status": "active",
                    "revision": 1,
                },
                {
                    "id": 2,
                    "issuer": ISSUER,
                    "subject": "fixture-employee",
                    "status": "active",
                    "revision": 1,
                },
                {
                    "id": 3,
                    "issuer": ISSUER,
                    "subject": "fixture-manager",
                    "status": "active",
                    "revision": 1,
                },
                {
                    "id": 4,
                    "issuer": ISSUER,
                    "subject": "fixture-unlinked",
                    "status": "active",
                    "revision": 1,
                },
                {
                    "id": 5,
                    "issuer": ISSUER,
                    "subject": "fixture-other-owner",
                    "status": "active",
                    "revision": 1,
                },
                {
                    "id": 6,
                    "issuer": "https://other.example.test/realm",
                    "subject": "fixture-owner",
                    "status": "active",
                    "revision": 1,
                },
            ],
        )
        connection.execute(
            insert(Organization),
            [
                {
                    "id": org,
                    "name": name,
                    "status": "active",
                    "revision": 1,
                    "tenant_enforced_at": NOW,
                }
                for org, name in ((1, "Company A"), (2, "Company B"), (3, "Company C"))
            ],
        )
        connection.execute(
            insert(restaurant_reference),
            [
                {"id": 100, "owner_id": 77, "organization_id": 1},
                {"id": 101, "owner_id": 77, "organization_id": 1},
                {"id": 200, "owner_id": 77, "organization_id": 2},
                {"id": 300, "owner_id": 88, "organization_id": 3},
            ],
        )
        connection.execute(
            insert(OrganizationMembership),
            [
                {
                    "id": member,
                    "organization_id": org,
                    "identity_id": identity,
                    "role_code": role,
                    "access_mode": mode,
                    "status": "active",
                    "revision": 1,
                    "enrollment_generation": 1,
                    "accepted_at": NOW,
                    "activated_at": NOW,
                }
                for member, org, identity, role, mode in (
                    (10, 1, 1, "owner", "company-wide"),
                    (11, 2, 1, "owner", "company-wide"),
                    (20, 1, 2, "employee", "explicit-grants"),
                    (30, 1, 3, "manager", "explicit-grants"),
                    (50, 3, 5, "owner", "company-wide"),
                )
            ],
        )
        connection.execute(
            insert(MembershipRestaurantGrant),
            [
                {
                    "organization_id": 1,
                    "membership_id": member,
                    "restaurant_id": 100,
                    "access_mode": "explicit-grants",
                }
                for member in (20, 30)
            ],
        )
    yield engine
    engine.dispose()


class MemoryAsyncSession(AsyncSession):
    """Bridge synchronous memory SQLite through SQLAlchemy's public run_sync.

    This unit adapter executes real SQL/savepoints, but deliberately supplies no
    evidence about asyncpg IO or PostgreSQL row locks.
    """

    # ==============================================
    # EXECUTE
    # ==============================================

    async def execute(
        self, statement: Executable, params: dict[str, Any] | None = None, **kwargs: Any
    ) -> Result[Any]:
        """Buffer local SQLite Core and ORM results without an async driver."""
        return await self.run_sync(lambda db: db.execute(statement, params, **kwargs))


# ==============================================
# SESSION
# ==============================================


@pytest.fixture
def session(local_engine: Engine) -> Iterator[AsyncSession]:
    """Use actual AsyncSession transactions with an explicit memory-only bind."""
    value = MemoryAsyncSession(expire_on_commit=False)
    value.sync_session.bind = local_engine
    yield value
    value.sync_session.close()


# ==============================================
# CONTEXT FOR
# ==============================================


async def context_for(
    *, session: AsyncSession, subject: str = "fixture-owner", company: int = 1
) -> TenantContext:
    """Resolve only inside the operation's caller-owned transaction."""
    return await TenantContextResolver(session=session).resolve(
        principal=principal(subject=subject), organization_id=company
    )


# ==============================================
# SCHEMA AND BOUNDARY CONTRACTS
# ==============================================


# ==============================================
# TEST STAGED METADATA PRESERVES LEGACY MAPPING
# ==============================================


def test_staged_metadata_preserves_legacy_mapping() -> None:
    """Verify staged metadata preserves legacy mappings and non-destructive relationships."""
    configure_mappers()
    assert TenantBase.registry is Base.registry
    assert TENANT_METADATA is not Base.metadata
    assert "organization_id" not in Restaurant.__table__.c
    assert "group_id" in Restaurant.__table__.c
    assert "identities" not in Base.metadata.tables
    assert not any(
        fk.ondelete == "CASCADE"
        for table in TENANT_METADATA.tables.values()
        for fk in table.foreign_key_constraints
    )
    assert all(
        not mapper.relationships
        for mapper in (
            Identity.__mapper__,
            Organization.__mapper__,
            OrganizationMembership.__mapper__,
        )
    )


# ==============================================
# TEST POSTGRES DDL COMPILES ALL CONSTRAINTS
# ==============================================


def test_postgres_ddl_compiles_all_constraints() -> None:
    """Compile the PostgreSQL schema without creating or contacting a database."""
    sql = "\n".join(
        str(CreateTable(table).compile(dialect=postgresql.dialect()))
        for table in TENANT_METADATA.sorted_tables
        if not table.info.get("external_reference")
    )
    for marker in (
        "ck_identity_ascii",
        'COLLATE "C"',
        "fk_grant_membership",
        "fk_grant_restaurant",
        "ck_proposal_actor",
        "ck_tenant_role_permission",
        "ON DELETE RESTRICT",
    ):
        assert marker in sql
    assert "ON DELETE CASCADE" not in sql


# ==============================================
# TEST INVALID IDENTITY KEYS DENIED
# ==============================================


@pytest.mark.parametrize(
    "issuer,subject",
    [
        (ISSUER, ""),
        (ISSUER, " x"),
        (ISSUER, "x\n"),
        (ISSUER, "é"),
        (ISSUER, "x" * 256),
        ("http://localhost:8080/realm", "x"),
        (ISSUER + "?query=1", "x"),
        ("https://user:password@example.test", "x"),
        ("https://example.test:bad", "x"),
    ],
)
def test_invalid_identity_keys_denied(issuer: str, subject: str) -> None:
    """Reject malformed issuer and subject pairs before identity lookup."""
    with pytest.raises(ValueError):
        validate_identity_key(issuer=issuer, subject=subject)


# ==============================================
# TEST IDENTITY KEYS PRESERVE EXACT SUBJECT
# ==============================================


@pytest.mark.parametrize("subject", ["fixture-owner", "FIXTURE-OWNER", "x" * 255])
def test_identity_keys_preserve_exact_subject(subject: str) -> None:
    """Preserve the exact case and content of valid subject identifiers."""
    value = Identity(issuer=ISSUER, subject=subject)
    assert value.subject == subject


# ==============================================
# TEST DATABASE REJECTS FOREIGN DUPLICATE OR COMPANY WIDE GRANTS
# ==============================================


@pytest.mark.parametrize(
    "payload",
    [
        {"organization_id": 2, "membership_id": 20, "restaurant_id": 200},
        {"organization_id": 1, "membership_id": 20, "restaurant_id": 200},
        {"organization_id": 1, "membership_id": 10, "restaurant_id": 100},
        {"organization_id": 1, "membership_id": 20, "restaurant_id": 100},
    ],
)
def test_database_rejects_foreign_duplicate_or_company_wide_grants(
    local_engine: Engine, payload: dict[str, int]
) -> None:
    """Exercise database denial of inconsistent or duplicate restaurant grants."""
    with pytest.raises(IntegrityError), local_engine.begin() as connection:
        connection.execute(insert(MembershipRestaurantGrant).values(**payload))


# ==============================================
# TEST MEMBERSHIP CONSTRAINTS
# ==============================================


@pytest.mark.parametrize(
    "values",
    [
        {
            "organization_id": 1,
            "identity_id": 1,
            "role_code": "owner",
            "access_mode": "company-wide",
        },
        {
            "organization_id": 2,
            "identity_id": 4,
            "role_code": "owner",
            "access_mode": "explicit-grants",
        },
        {
            "organization_id": 2,
            "identity_id": 4,
            "role_code": "employee",
            "access_mode": "anything",
        },
        {
            "organization_id": 2,
            "identity_id": 4,
            "role_code": "employee",
            "status": "active",
        },
        {"organization_id": 2, "identity_id": 4, "role_code": "super_admin"},
        {
            "organization_id": 2,
            "identity_id": 4,
            "role_code": "employee",
            "revision": 0,
        },
    ],
)
def test_membership_constraints(
    local_engine: Engine, values: dict[str, object]
) -> None:
    """Reject memberships that violate identity, role, scope or lifecycle constraints."""
    with pytest.raises(IntegrityError), local_engine.begin() as connection:
        connection.execute(insert(OrganizationMembership).values(**values))


# ==============================================
# TEST ROLE POLICY NEVER ACCEPTS PLATFORM OR ESCALATED PERMISSIONS
# ==============================================


@pytest.mark.parametrize(
    "role,permission",
    [
        ("employee", "tenant.memberships.manage"),
        ("manager", "tenant.billing.read"),
        ("owner", "*"),
        ("owner", "admins.manage"),
        ("owner", "payments.review"),
        ("super_admin", "tenant.orders.read"),
    ],
)
def test_role_policy_never_accepts_platform_or_escalated_permissions(
    local_engine: Engine, role: str, permission: str
) -> None:
    """Keep tenant role assignments within their explicit permission ceiling."""
    with pytest.raises(IntegrityError), local_engine.begin() as connection:
        connection.execute(
            insert(TenantRolePermission).values(
                role_code=role, permission_code=permission
            )
        )


# ==============================================
# TEST SAME OWNER COMPANIES ARE ISOLATED
# ==============================================


@pytest.mark.parametrize(
    "company,restaurant,allowed",
    [
        (1, 100, True),
        (1, 101, True),
        (1, 200, False),
        (1, 300, False),
        (2, 100, False),
        (2, 200, True),
    ],
)
async def test_same_owner_companies_are_isolated(
    session: AsyncSession, company: int, restaurant: int, allowed: bool
) -> None:
    """Keep companies separate even when their restaurants share a legacy owner."""
    async with tenant_unit_of_work(session=session):
        context = await context_for(session=session, company=company)
        service = TenantAuthorizationService(session=session)
        if allowed:
            await service.require_restaurant(
                context=context,
                restaurant_id=restaurant,
                permission="tenant.restaurants.read",
            )
        else:
            with pytest.raises(TenantAccessDenied):
                await service.require_restaurant(
                    context=context,
                    restaurant_id=restaurant,
                    permission="tenant.restaurants.read",
                )
        rows = await session.execute(
            select(restaurant_reference.c.id).where(restaurant_scope(context=context))
        )
        assert set(rows.scalars()) == ({100, 101} if company == 1 else {200})


# ==============================================
# TEST EMPLOYEE GRANTS ARE EXACT
# ==============================================


@pytest.mark.parametrize(
    "restaurant,allowed", [(100, True), (101, False), (200, False), (300, False)]
)
async def test_employee_grants_are_exact(
    session: AsyncSession, restaurant: int, allowed: bool
) -> None:
    """Authorize employees only for their explicitly granted restaurants."""
    async with tenant_unit_of_work(session=session):
        context = await context_for(session=session, subject="fixture-employee")
        if allowed:
            await TenantAuthorizationService(session=session).require_restaurant(
                context=context,
                restaurant_id=restaurant,
                permission="tenant.orders.read",
            )
        else:
            with pytest.raises(TenantAccessDenied):
                await TenantAuthorizationService(session=session).require_restaurant(
                    context=context,
                    restaurant_id=restaurant,
                    permission="tenant.orders.read",
                )


# ==============================================
# TEST EMPTY EXPLICIT GRANTS ARE FALSE
# ==============================================


async def test_empty_explicit_grants_are_false(
    local_engine: Engine, session: AsyncSession
) -> None:
    """Prove empty grant sets authorize no restaurant rows or mutations."""
    with local_engine.begin() as connection:
        connection.execute(
            delete(MembershipRestaurantGrant).where(
                MembershipRestaurantGrant.membership_id == 20
            )
        )
    async with tenant_unit_of_work(session=session):
        context = await context_for(session=session, subject="fixture-employee")
        assert context.restaurant_ids == frozenset()
        rows = await session.execute(
            select(func.count())
            .select_from(restaurant_reference)
            .where(restaurant_scope(context=context))
        )
        assert rows.scalar_one() == 0
        with pytest.raises(TenantAccessDenied):
            await TenantAuthorizationService(session=session).require_restaurant(
                context=context, restaurant_id=100, permission="tenant.orders.read"
            )
        context.require(permission="tenant.membership.self.read")


# ==============================================
# TEST ROLES NEVER BOOTSTRAP OR LINK
# ==============================================


@pytest.mark.parametrize(
    "subject,issuer",
    [
        ("owner-test", ISSUER),
        ("fixture-unlinked", ISSUER),
        ("fixture-owner", "https://other.example.test/realm"),
        ("FIXTURE-OWNER", ISSUER),
        ("fixture-owner", ISSUER + "/"),
    ],
)
async def test_roles_never_bootstrap_or_link(
    session: AsyncSession, subject: str, issuer: str
) -> None:
    """Deny unassociated identities without provisioning or linking records."""
    async with tenant_unit_of_work(session=session):
        before = (
            await session.execute(select(func.count()).select_from(Identity))
        ).scalar_one()
        with pytest.raises(TenantAccessDenied):
            await TenantContextResolver(session=session).resolve(
                principal=principal(subject=subject, issuer=issuer), organization_id=1
            )
        assert (
            await session.execute(select(func.count()).select_from(Identity))
        ).scalar_one() == before


# ==============================================
# TEST CONTEXT FROZEN SLOTTED AND NOT HTTP CONSTRUCTIBLE
# ==============================================


async def test_context_frozen_slotted_and_not_http_constructible(
    session: AsyncSession,
) -> None:
    """Reject context mutation, reconstruction and unverified issuance."""
    async with tenant_unit_of_work(session=session):
        context = await context_for(session=session)
        assert not hasattr(context, "__dict__")
        with pytest.raises(FrozenInstanceError):
            context.organization_id = 2
        with pytest.raises((ValueError, TypeError)):
            replace(context, organization_id=2)
        payload = {
            key: value for key, value in asdict(context).items() if key != "_seal"
        }
        with pytest.raises(TenantAccessDenied):
            TenantContext(**payload, _proof="http-input")
        forged = object.__new__(TenantContext)
        with pytest.raises(TenantAccessDenied):
            forged.assert_verified()


# ==============================================
# TEST FULFILLMENT IS BLOCKED FOR ALL ROLES
# ==============================================


@pytest.mark.parametrize(
    "subject", ["fixture-owner", "fixture-manager", "fixture-employee"]
)
async def test_fulfillment_is_blocked_for_all_roles(
    session: AsyncSession, subject: str
) -> None:
    """Deny fulfillment and platform permissions through tenant authorization."""
    async with tenant_unit_of_work(session=session):
        context = await context_for(session=session, subject=subject)
        assert "tenant.orders.fulfill" not in context.permissions
        for permission in (
            "tenant.orders.fulfill",
            "payments.review",
            "admins.manage",
            "*",
            "unknown",
        ):
            with pytest.raises(TenantAccessDenied):
                context.require(permission=permission)


# ==============================================
# TEST MISSING POLICY ROWS NEVER FALL BACK
# ==============================================


async def test_missing_policy_rows_never_fall_back(
    local_engine: Engine, session: AsyncSession
) -> None:
    """Prove missing persisted policy rows do not yield default permissions."""
    with local_engine.begin() as connection:
        connection.execute(
            delete(TenantRolePermission).where(
                TenantRolePermission.role_code == "employee"
            )
        )
    async with tenant_unit_of_work(session=session):
        context = await context_for(session=session, subject="fixture-employee")
        assert not context.permissions
        with pytest.raises(TenantAccessDenied):
            context.require(permission="tenant.orders.read")


# ==============================================
# TEST OLD CONTEXT IS REVALIDATED
# ==============================================


@pytest.mark.parametrize(
    "table,criteria,values",
    [
        (Identity, Identity.id == 2, {"status": "suspended", "revision": 2}),
        (Organization, Organization.id == 1, {"status": "suspended", "revision": 2}),
        (
            OrganizationMembership,
            OrganizationMembership.id == 20,
            {"status": "revoked", "revoked_at": NOW, "revision": 2},
        ),
        (TenantRole, TenantRole.code == "employee", {"policy_revision": 2}),
    ],
)
async def test_old_context_is_revalidated(
    local_engine: Engine,
    session: AsyncSession,
    table: object,
    criteria: object,
    values: dict[str, object],
) -> None:
    """Reject previously issued contexts after persisted authority changes."""
    async with tenant_unit_of_work(session=session):
        context = await context_for(session=session, subject="fixture-employee")
    with local_engine.begin() as connection:
        connection.execute(update(table).where(criteria).values(**values))
    async with tenant_unit_of_work(session=session):
        with pytest.raises(TenantAccessDenied):
            await TenantAuthorizationService(session=session).require_restaurant(
                context=context, restaurant_id=100, permission="tenant.orders.read"
            )


# ==============================================
# TEST BINDING CANNOT SWITCH COMPANY
# ==============================================


async def test_binding_cannot_switch_company(session: AsyncSession) -> None:
    """Reject company changes within an already bound request session."""
    async with tenant_unit_of_work(session=session):
        await context_for(session=session)
        with pytest.raises(TenantConflict):
            await context_for(session=session, company=2)


# ==============================================
# TEST UNIT MUST PRECEDE DATABASE LOOKUP
# ==============================================


async def test_unit_must_precede_database_lookup(session: AsyncSession) -> None:
    """Require transaction ownership before identity resolution performs SQL."""
    with pytest.raises(TenantConflict):
        await IdentityService(session=session).resolve_id(principal=principal())
    await session.execute(select(Identity.id))
    with pytest.raises(TenantConflict):
        async with tenant_unit_of_work(session=session):
            pytest.fail("must not enter an already autobegun transaction")
    await session.rollback()


# ==============================================
# TEST REVOCATION DENIES DELEGATION FOREIGN COMPANY AND OWNER
# ==============================================


@pytest.mark.parametrize(
    "subject,company,target",
    [
        ("fixture-manager", 1, 20),
        ("fixture-employee", 1, 30),
        ("fixture-owner", 2, 20),
        ("fixture-owner", 1, 10),
    ],
)
async def test_revocation_denies_delegation_foreign_company_and_owner(
    session: AsyncSession, subject: str, company: int, target: int
) -> None:
    """Reject unauthorized revocation across role, company and owner boundaries."""
    async with tenant_unit_of_work(session=session):
        with pytest.raises(TenantAccessDenied):
            await MembershipService(session=session).revoke_non_owner(
                principal=principal(subject=subject),
                organization_id=company,
                membership_id=target,
                expected_revision=1,
            )


# ==============================================
# TEST REVOCATION IS ATOMIC AND AUDITED
# ==============================================


async def test_revocation_is_atomic_and_audited(session: AsyncSession) -> None:
    """Commit non-owner revocation with grant removal and complete audit evidence."""
    async with tenant_unit_of_work(session=session):
        result = await MembershipService(session=session).revoke_non_owner(
            principal=principal(),
            organization_id=1,
            membership_id=20,
            expected_revision=1,
        )
        assert (result.revision, result.status) == (2, "revoked")
    with session.sync_session.begin():
        member = session.sync_session.get(
            OrganizationMembership, 20, populate_existing=True
        )
        assert member.status == "revoked" and member.revision == 2
        audit = session.sync_session.execute(select(TenantAuditEvent)).scalar_one()
        assert audit.policy_before["restaurant_ids"] == [100]
        assert audit.policy_after["restaurant_ids"] == []
        assert audit.actor_membership_id == 10 and audit.target_membership_id == 20
        assert (
            session.sync_session.scalar(
                select(func.count())
                .select_from(MembershipRestaurantGrant)
                .where(MembershipRestaurantGrant.membership_id == 20)
            )
            == 0
        )


# ==============================================
# TEST AUDIT FAILURE ROLLS BACK EVEN IF CAUGHT
# ==============================================


async def test_audit_failure_rolls_back_even_if_caught(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Roll back the mutation savepoint when required audit persistence fails."""
    monkeypatch.setattr(
        TenantRepository,
        "append_audit",
        AsyncMock(side_effect=RuntimeError("simulated audit failure")),
    )
    async with tenant_unit_of_work(session=session):
        with pytest.raises(RuntimeError, match="simulated audit"):
            await MembershipService(session=session).revoke_non_owner(
                principal=principal(),
                organization_id=1,
                membership_id=20,
                expected_revision=1,
            )
    with session.sync_session.begin():
        assert (
            session.sync_session.get(
                OrganizationMembership, 20, populate_existing=True
            ).status
            == "active"
        )
        assert (
            session.sync_session.scalar(
                select(func.count())
                .select_from(MembershipRestaurantGrant)
                .where(MembershipRestaurantGrant.membership_id == 20)
            )
            == 1
        )
        assert (
            session.sync_session.scalar(
                select(func.count()).select_from(TenantAuditEvent)
            )
            == 0
        )


# ==============================================
# TEST STALE REVISION HAS NO SIDE EFFECTS
# ==============================================


async def test_stale_revision_has_no_side_effects(session: AsyncSession) -> None:
    """Reject stale revision requests before any revocation side effects."""
    async with tenant_unit_of_work(session=session):
        with pytest.raises(TenantConflict):
            await MembershipService(session=session).revoke_non_owner(
                principal=principal(),
                organization_id=1,
                membership_id=20,
                expected_revision=42,
            )
        assert (
            await session.execute(select(func.count()).select_from(TenantAuditEvent))
        ).scalar_one() == 0


# ==============================================
# TEST OUTER ROLLBACK PRESERVES MEMBERSHIP
# ==============================================


async def test_outer_rollback_preserves_membership(session: AsyncSession) -> None:
    """Restore membership, grants and audit when the owning transaction rolls back."""
    with pytest.raises(RuntimeError, match="rollback fixture"):
        async with tenant_unit_of_work(session=session):
            await MembershipService(session=session).revoke_non_owner(
                principal=principal(),
                organization_id=1,
                membership_id=20,
                expected_revision=1,
            )
            raise RuntimeError("rollback fixture")
    with session.sync_session.begin():
        assert (
            session.sync_session.get(
                OrganizationMembership, 20, populate_existing=True
            ).status
            == "active"
        )
        assert (
            session.sync_session.scalar(
                select(func.count()).select_from(TenantAuditEvent)
            )
            == 0
        )
        assert (
            session.sync_session.scalar(
                select(func.count())
                .select_from(MembershipRestaurantGrant)
                .where(MembershipRestaurantGrant.membership_id == 20)
            )
            == 1
        )


# ==============================================
# TEST PROPOSAL INTEGRITY
# ==============================================


@pytest.mark.parametrize(
    "changes",
    [
        {"target_membership_id": 11},
        {"actor_membership_id": 11},
        {"expected_actor_revision": None},
        {"proposed_role_code": "owner"},
        {"status": "applied"},
    ],
)
def test_proposal_integrity(local_engine: Engine, changes: dict[str, object]) -> None:
    """Reject inconsistent proposal actors, targets, scope and application state."""
    values = {
        "organization_id": 1,
        "target_membership_id": 20,
        "target_identity_id": 2,
        "actor_kind": "tenant",
        "actor_membership_id": 10,
        "actor_identity_id": 1,
        "proposed_role_code": "employee",
        "proposed_access_mode": "explicit-grants",
        "expected_actor_revision": 1,
        "expected_target_revision": 1,
        "enrollment_generation": 1,
        "expires_at": NOW + timedelta(hours=1),
        **changes,
    }
    with pytest.raises(IntegrityError), local_engine.begin() as connection:
        connection.execute(insert(MembershipChangeProposal).values(**values))


# ==============================================
# TEST PROPOSAL RESTAURANTS CANNOT CROSS COMPANY
# ==============================================


def test_proposal_restaurants_cannot_cross_company(local_engine: Engine) -> None:
    """Enforce company-qualified foreign keys on proposed restaurant grants."""
    with local_engine.begin() as connection:
        connection.execute(
            insert(MembershipChangeProposal).values(
                id=1,
                organization_id=1,
                target_membership_id=20,
                target_identity_id=2,
                actor_kind="tenant",
                actor_membership_id=10,
                actor_identity_id=1,
                proposed_role_code="employee",
                proposed_access_mode="explicit-grants",
                expected_actor_revision=1,
                expected_target_revision=1,
                enrollment_generation=1,
                expires_at=NOW + timedelta(hours=1),
            )
        )
    with pytest.raises(IntegrityError), local_engine.begin() as connection:
        connection.execute(
            insert(MembershipProposalRestaurant).values(
                organization_id=1, proposal_id=1, restaurant_id=200
            )
        )


# ==============================================
# TEST ORM KEYS CANNOT CHANGE
# ==============================================


@pytest.mark.parametrize(
    "model,identifier,field,value",
    [
        (Identity, 1, "subject", "changed-fixture-subject"),
        (OrganizationMembership, 20, "identity_id", 4),
        (Organization, 1, "tenant_enforced_at", None),
    ],
)
async def test_orm_keys_cannot_change(
    session: AsyncSession, model: object, identifier: int, field: str, value: object
) -> None:
    """Protect immutable identity, membership and enforcement keys through ORM writes."""
    with pytest.raises(ValueError), session.sync_session.begin():
        entity = session.sync_session.get(model, identifier)
        setattr(entity, field, value)
        session.sync_session.flush()


# ==============================================
# TEST AUDIT CANNOT BE EDITED VIA ORM
# ==============================================


async def test_audit_cannot_be_edited_via_orm(session: AsyncSession) -> None:
    """Reject edits to an already persisted tenant audit event."""
    async with tenant_unit_of_work(session=session):
        await MembershipService(session=session).revoke_non_owner(
            principal=principal(),
            organization_id=1,
            membership_id=20,
            expected_revision=1,
        )
    with pytest.raises(ValueError, match="append_only"), session.sync_session.begin():
        entity = session.sync_session.execute(select(TenantAuditEvent)).scalar_one()
        entity.action = "changed"
        session.sync_session.flush()


# ==============================================
# TEST COMPANY WITHOUT ACTIVE OWNER DENIES EMPLOYEE
# ==============================================


async def test_company_without_active_owner_denies_employee(
    local_engine: Engine, session: AsyncSession
) -> None:
    """Deny business authorization when the company lacks a qualifying active owner."""
    with local_engine.begin() as connection:
        connection.execute(
            update(Identity)
            .where(Identity.id == 1)
            .values(status="suspended", revision=2)
        )
    async with tenant_unit_of_work(session=session):
        with pytest.raises(TenantAccessDenied):
            await context_for(session=session, subject="fixture-employee")


# ==============================================
# TEST CATALOGUE MATCHES APPROVED DESIGN
# ==============================================


def test_catalogue_matches_approved_design() -> None:
    """Compare the closed tenant catalogue with the approved design document."""
    document = Path("docs/keycloak-k9-detailed-design.md").read_text(encoding="utf-8")
    assert (
        set(re.findall(r"^\| `(tenant\.[a-z_.]+)` \|", document, re.MULTILINE))
        == TENANT_PERMISSIONS
    )
