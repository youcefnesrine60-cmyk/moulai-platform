# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""K10 HTTP and transaction proofs on the launcher's disposable local E1 DB."""

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import (
    datetime,
    timezone,
)
from itertools import count

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from httpx import (
    ASGITransport,
    AsyncClient,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.security.oidc import OIDCPrincipal
from app.core.security.tenant_types import (
    TenantAccessDenied,
    TenantConflict,
)
from app.services.business.tenant_access import TenantAccessService
from test_support.local_postgres import (
    LOCAL_E1_REVISION,
    LocalPostgresSettings,
    read_local_test_identity,
)
from test_support.tenant_http_app import create_tenant_test_app
from tests.test_tenant_access_http import (
    jwks,
    rsa_keys,
    token,
)
from tests.test_tenant_foundation import ISSUER

__all__ = ["jwks", "rsa_keys"]
pytestmark = pytest.mark.k10_postgres
BLOCKS = count(1_000_000, 100)


@dataclass(frozen=True, slots=True)
class Graph:
    """Explicit synthetic links; no lookup or creation of real user profiles."""

    base: int

    # ==============================================
    # UNIQUE SYNTHETIC SUBJECT
    # ==============================================
    def subject(self, *, actor: str) -> str:
        """Keep every test's committed retained identities independent."""
        return f"k10-{self.base}-{actor}"


# ==============================================
# LOCAL E1 SERVER ADMISSION BEFORE FIXTURE WRITES
# ==============================================


@pytest.fixture
async def k10_engine() -> AsyncIterator[AsyncEngine]:
    """Never read DATABASE_URL, TEST_DATABASE_URL or the remote fixture engine."""
    configuration = LocalPostgresSettings()
    assert configuration.PROFILE == "k10"
    engine = create_async_engine(
        configuration.URL.get_secret_value(),
        echo=False,
        connect_args={"ssl": False, "timeout": 10, "command_timeout": 15},
        hide_parameters=True,
    )
    try:
        async with engine.connect() as connection:
            await connection.run_sync(
                lambda sync: read_local_test_identity(sync, configuration=configuration)
            )
            assert (
                await connection.scalar(text("SELECT version_num FROM alembic_version"))
                == LOCAL_E1_REVISION
            )
        yield engine
    finally:
        await engine.dispose()


# ==============================================
# EXPLICIT TEMPORARY IDENTITY / COMPANY / MEMBERSHIP LINKS
# ==============================================


@pytest.fixture
async def graph(k10_engine: AsyncEngine) -> Graph:
    """Commit synthetic graphs with E1 protections intact; retain until server stop."""
    graph = Graph(base=next(BLOCKS))
    b = graph.base
    actors = ("owner", "manager", "employee", "empty", "pending", "outsider", "c-owner")
    async with k10_engine.begin() as connection:
        for offset, actor in enumerate(actors):
            await connection.execute(
                text(
                    "INSERT INTO identities (id,issuer,subject,status) VALUES (:id,:iss,:sub,'active')"
                ),
                {"id": b + offset, "iss": ISSUER, "sub": graph.subject(actor=actor)},
            )
        # A matching subject at another issuer must never resolve through sub alone.
        await connection.execute(
            text(
                "INSERT INTO identities (id,issuer,subject,status) VALUES (:id,:iss,:sub,'active')"
            ),
            {
                "id": b + 7,
                "iss": ISSUER + "-other",
                "sub": graph.subject(actor="issuer-only"),
            },
        )
        for offset, label in enumerate(("A", "B", "C")):
            await connection.execute(
                text("INSERT INTO organizations (id,name) VALUES (:id,:name)"),
                {"id": b + 10 + offset, "name": f"K10 {b} {label}"},
            )
        await connection.execute(
            text(
                "INSERT INTO owners (id,chat_id,full_name,registration_status) VALUES (:id,:chat,'Synthetic K10','approved')"
            ),
            {"id": b + 50, "chat": b + 50},
        )
        for offset, company in ((60, 10), (61, 10), (62, 11), (63, 12)):
            await connection.execute(
                text(
                    "INSERT INTO restaurants (id,owner_id,organization_id,name,type,phone,wilaya,is_active) VALUES (:id,:owner,:org,:name,'cafe','synthetic','Test',true)"
                ),
                {
                    "id": b + offset,
                    "owner": b + 50,
                    "org": b + company,
                    "name": f"K10 {b + offset}",
                },
            )
        memberships = (
            (30, 10, 0, "owner", "company-wide", "active"),
            (31, 11, 0, "owner", "company-wide", "active"),
            (32, 12, 6, "owner", "company-wide", "active"),
            (33, 10, 1, "manager", "explicit-grants", "active"),
            (34, 10, 2, "employee", "explicit-grants", "active"),
            (35, 10, 3, "employee", "explicit-grants", "active"),
            (36, 10, 4, "employee", "explicit-grants", "pending"),
        )
        for member, company, identity, role, mode, status in memberships:
            await connection.execute(
                text(
                    "INSERT INTO organization_memberships (id,organization_id,identity_id,role_code,access_mode,status,enrollment_generation,accepted_at,activated_at) VALUES (:id,:org,:identity,:role,:mode,:status,1,:accepted,:activated)"
                ),
                {
                    "id": b + member,
                    "org": b + company,
                    "identity": b + identity,
                    "role": role,
                    "mode": mode,
                    "status": status,
                    "accepted": (
                        datetime.now(timezone.utc) if status == "active" else None
                    ),
                    "activated": (
                        datetime.now(timezone.utc) if status == "active" else None
                    ),
                },
            )
        for member, restaurant in ((33, 60), (34, 61)):
            await connection.execute(
                text(
                    "INSERT INTO membership_restaurant_grants (id,organization_id,membership_id,restaurant_id) VALUES (:id,:org,:member,:restaurant)"
                ),
                {
                    "id": b + member + 50,
                    "org": b + 10,
                    "member": b + member,
                    "restaurant": b + restaurant,
                },
            )
        for company in (10, 11, 12):
            await connection.execute(
                text(
                    "UPDATE organizations SET status='active',tenant_enforced_at=now(),revision=revision+1 WHERE id=:id"
                ),
                {"id": b + company},
            )
    return graph


# ==============================================
# HTTP APPLICATION WITH REQUEST-LOCAL SESSIONS ONLY
# ==============================================


def test_app(
    *, engine: AsyncEngine, permission: str = "tenant.restaurants.read"
) -> FastAPI:
    """Reuse opt-in dependencies without loading the runtime application's routes."""
    factory = async_sessionmaker(engine, expire_on_commit=False)

    # ==============================================
    # DEDICATED REQUEST SESSION
    # ==============================================
    async def session_dependency() -> AsyncIterator[AsyncSession]:
        """Close transaction and identity map at the end of each HTTP request."""
        async with factory() as session:
            yield session

    return create_tenant_test_app(
        session_dependency=session_dependency, restaurant_permission=permission
    )


test_app.__test__ = False


# ==============================================
# ACTUAL STORED ROLES AND GRANTS, NEVER KEYCLOAK ROLE INFERENCE
# ==============================================


@pytest.mark.parametrize(
    "actor,offsets",
    [("owner", [60, 61]), ("manager", [60]), ("employee", [61]), ("empty", [])],
)
async def test_postgres_role_and_resource_scope(
    k10_engine: AsyncEngine,
    graph: Graph,
    jwks: object,
    rsa_keys: tuple[rsa.RSAPrivateKey, rsa.RSAPrivateKey],
    actor: str,
    offsets: list[int],
) -> None:
    """All JWTs claim owner/admin; PostgreSQL alone controls actual access."""
    app = test_app(engine=k10_engine)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        client.headers["Authorization"] = "Bearer " + token(
            rsa_keys=rsa_keys, subject=graph.subject(actor=actor)
        )
        response = await client.get(
            f"/test/organizations/{graph.base + 10}/restaurants"
        )
        assert response.status_code == 200
        assert [row["id"] for row in response.json()] == [
            graph.base + i for i in offsets
        ]
        for offset in (60, 61, 62, 63, 99):
            result = await client.get(
                f"/test/organizations/{graph.base + 10}/restaurants/{graph.base + offset}"
            )
            assert result.status_code == (200 if offset in offsets else 404)


# ==============================================
# ONE OWNER, TWO COMPANIES, NO UNION OR UNAUTHORIZED SWITCH
# ==============================================


async def test_postgres_same_owner_company_isolation(
    k10_engine: AsyncEngine,
    graph: Graph,
    jwks: object,
    rsa_keys: tuple[rsa.RSAPrivateKey, rsa.RSAPrivateKey],
) -> None:
    """Personal association discovery never merges company-qualified resources."""
    async with AsyncClient(
        transport=ASGITransport(app=test_app(engine=k10_engine)), base_url="http://test"
    ) as client:
        client.headers["Authorization"] = "Bearer " + token(
            rsa_keys=rsa_keys, subject=graph.subject(actor="owner")
        )
        own = await client.get("/test/memberships")
        assert own.status_code == 200
        assert [row["organization_id"] for row in own.json()] == [
            graph.base + 10,
            graph.base + 11,
        ]
        page = await client.get("/test/memberships?limit=1")
        assert len(page.json()) == 1
        second = await client.get(
            f"/test/memberships?after_id={page.json()[0]['id']}&limit=1"
        )
        assert second.json()[0]["organization_id"] == graph.base + 11
        for org, expected in ((11, [62]), (12, None)):
            result = await client.get(
                f"/test/organizations/{graph.base + org}/restaurants",
                headers={"X-Organization-ID": str(graph.base + 10)},
            )
            assert result.status_code == (200 if expected else 404)
            if expected:
                assert [row["id"] for row in result.json()] == [
                    graph.base + i for i in expected
                ]
        for path in (
            "/test/memberships?limit=101",
            "/test/organizations/0/restaurants",
        ):
            assert (await client.get(path)).status_code == 422
        assert (await client.get("/test/organizations/restaurants")).status_code == 404


# ==============================================
# EXACT ISSUER-QUALIFIED IDENTITY AND ACCEPTED MEMBERSHIP
# ==============================================


@pytest.mark.parametrize(
    "actor,expected",
    [("missing", 403), ("issuer-only", 403), ("outsider", 404), ("pending", 403)],
)
async def test_postgres_unlinked_or_unaccepted_denied(
    k10_engine: AsyncEngine,
    graph: Graph,
    jwks: object,
    rsa_keys: tuple[rsa.RSAPrivateKey, rsa.RSAPrivateKey],
    actor: str,
    expected: int,
) -> None:
    """No identity provisioning, cross-issuer link or pending membership bypass."""
    async with AsyncClient(
        transport=ASGITransport(app=test_app(engine=k10_engine)), base_url="http://test"
    ) as client:
        client.headers["Authorization"] = "Bearer " + token(
            rsa_keys=rsa_keys, subject=graph.subject(actor=actor)
        )
        assert (
            await client.get(f"/test/organizations/{graph.base + 10}/restaurants")
        ).status_code == expected
        discovery = await client.get("/test/memberships")
        assert discovery.status_code == (
            403 if actor in {"missing", "issuer-only"} else 200
        )
    async with k10_engine.connect() as connection:
        assert (
            await connection.scalar(
                text(
                    "SELECT count(*) FROM identities WHERE issuer=:iss AND subject=:sub"
                ),
                {"iss": ISSUER, "sub": graph.subject(actor="missing")},
            )
            == 0
        )


# ==============================================
# SEEDED PERMISSIONS, WITHOUT POLICY MUTATION OR PLATFORM GRANTS
# ==============================================


@pytest.mark.parametrize(
    "actor,expected", [("owner", 200), ("manager", 403), ("employee", 403)]
)
async def test_postgres_missing_stored_permission_denied(
    k10_engine: AsyncEngine,
    graph: Graph,
    jwks: object,
    rsa_keys: tuple[rsa.RSAPrivateKey, rsa.RSAPrivateKey],
    actor: str,
    expected: int,
) -> None:
    """Require an additional approved permission through the existing dependency."""
    app = test_app(engine=k10_engine, permission="tenant.billing.read")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            f"/test/organizations/{graph.base + 10}/restaurants",
            headers={
                "Authorization": "Bearer "
                + token(rsa_keys=rsa_keys, subject=graph.subject(actor=actor))
            },
        )
        assert response.status_code == expected
    async with k10_engine.connect() as connection:
        assert await connection.scalar(text("SELECT count(*) FROM tenant_roles")) == 3
        assert (
            await connection.scalar(
                text("SELECT count(*) FROM tenant_role_permissions")
            )
            == 49
        )
        assert (
            await connection.scalar(
                text(
                    "SELECT count(*) FROM tenant_role_permissions WHERE permission_code='tenant.orders.fulfill' OR permission_code NOT LIKE 'tenant.%'"
                )
            )
            == 0
        )


# ==============================================
# REAL VERIFIER, IN-MEMORY SIGNATURES AND MOCKED JWKS ONLY
# ==============================================


@pytest.mark.parametrize(
    "case", ["absent", "expired", "signature", "issuer", "audience", "roles"]
)
async def test_postgres_http_jwt_refusal(
    k10_engine: AsyncEngine,
    graph: Graph,
    jwks: object,
    rsa_keys: tuple[rsa.RSAPrivateKey, rsa.RSAPrivateKey],
    case: str,
) -> None:
    """Invalid bearer credentials fail before any tenant authorization succeeds."""
    async with AsyncClient(
        transport=ASGITransport(app=test_app(engine=k10_engine)), base_url="http://test"
    ) as client:
        if case != "absent":
            client.headers["Authorization"] = "Bearer " + token(
                rsa_keys=rsa_keys, subject=graph.subject(actor="owner"), case=case
            )
        response = await client.get(
            f"/test/organizations/{graph.base + 10}/restaurants"
        )
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"


# ==============================================
# COMMITTED SUSPENSION / REVOCATION APPLIES TO THE NEXT REQUEST
# ==============================================


@pytest.mark.parametrize(
    "change",
    [
        "identity-suspended",
        "identity-retired",
        "membership-suspended",
        "membership-revoked",
        "organization-suspended",
        "grant-removed",
    ],
)
async def test_postgres_revocation_refresh(
    k10_engine: AsyncEngine,
    graph: Graph,
    jwks: object,
    rsa_keys: tuple[rsa.RSAPrivateKey, rsa.RSAPrivateKey],
    change: str,
) -> None:
    """A previously valid JWT never freezes local membership or resource access."""
    path = f"/test/organizations/{graph.base + 10}/restaurants"
    async with AsyncClient(
        transport=ASGITransport(app=test_app(engine=k10_engine)), base_url="http://test"
    ) as client:
        client.headers["Authorization"] = "Bearer " + token(
            rsa_keys=rsa_keys, subject=graph.subject(actor="employee")
        )
        assert (await client.get(path)).status_code == 200
        async with k10_engine.begin() as connection:
            if change.startswith("identity-"):
                await connection.execute(
                    text(
                        "UPDATE identities SET status=:status,revision=revision+1 WHERE id=:id"
                    ),
                    {"status": change.removeprefix("identity-"), "id": graph.base + 2},
                )
            elif change.startswith("membership-"):
                status = change.removeprefix("membership-")
                timestamp = "suspended_at" if status == "suspended" else "revoked_at"
                await connection.execute(
                    text(
                        f"UPDATE organization_memberships SET status=:status,{timestamp}=now(),revision=revision+1 WHERE id=:id"
                    ),
                    {"status": status, "id": graph.base + 34},
                )
            elif change == "organization-suspended":
                await connection.execute(
                    text(
                        "UPDATE organizations SET status='suspended',revision=revision+1 WHERE id=:id"
                    ),
                    {"id": graph.base + 10},
                )
            else:
                await connection.execute(
                    text(
                        "DELETE FROM membership_restaurant_grants WHERE membership_id=:id"
                    ),
                    {"id": graph.base + 34},
                )
        response = await client.get(path)
        assert response.status_code == (200 if change == "grant-removed" else 403)
        if change == "grant-removed":
            assert response.json() == []
            assert (await client.get(path + f"/{graph.base + 61}")).status_code == 404


# ==============================================
# REAL SESSION TRANSACTIONS, COMPANY BINDING AND LEASE CLOSURE
# ==============================================


async def test_postgres_transaction_failure_closes_unit(
    k10_engine: AsyncEngine, graph: Graph
) -> None:
    """A failed business read rolls back, closes its lease and never changes tenant."""
    principal = OIDCPrincipal(
        issuer=ISSUER, subject=graph.subject(actor="owner"), realm_roles=frozenset()
    )
    async with AsyncSession(k10_engine, expire_on_commit=False) as session:
        service = TenantAccessService(session=session)
        with pytest.raises(TenantAccessDenied):
            async with service.authorized(
                principal=principal,
                organization_id=graph.base + 10,
                permission="tenant.restaurants.read",
            ) as unit:
                await unit.restaurant(restaurant_id=graph.base + 62)
        assert not session.in_transaction()
        with pytest.raises(TenantConflict, match="closed"):
            await unit.restaurants()
        with pytest.raises(TenantConflict):
            async with service.authorized(
                principal=principal,
                organization_id=graph.base + 11,
                permission="tenant.restaurants.read",
            ):
                pytest.fail("Session company binding must not be transferable")
        assert not session.in_transaction()


# ==============================================
# REAL CONCURRENT REVOCATION SERIALIZES WITH A BOUNDED AUTHORIZED READ
# ==============================================


async def test_postgres_concurrent_revocation(
    k10_engine: AsyncEngine,
    graph: Graph,
    jwks: object,
    rsa_keys: tuple[rsa.RSAPrivateKey, rsa.RSAPrivateKey],
) -> None:
    """Exclusive identity lock waits for the read; later requests cannot reuse it."""
    principal = OIDCPrincipal(
        issuer=ISSUER, subject=graph.subject(actor="employee"), realm_roles=frozenset()
    )
    started = asyncio.Event()
    pid: list[int] = []

    # ==============================================
    # SYNTHETIC WRITER USING THE GOVERNANCE LOCK ORDER
    # ==============================================
    async def revoke() -> None:
        """Lock identity first, then mutate membership in one atomic transaction."""
        async with k10_engine.begin() as connection:
            await connection.execute(text("SET LOCAL lock_timeout='5s'"))
            pid.append(await connection.scalar(text("SELECT pg_backend_pid()")))
            started.set()
            await connection.execute(
                text("SELECT id FROM identities WHERE id=:id FOR UPDATE"),
                {"id": graph.base + 2},
            )
            await connection.execute(
                text(
                    "UPDATE organization_memberships SET status='revoked',revoked_at=now(),revision=revision+1 WHERE id=:id"
                ),
                {"id": graph.base + 34},
            )

    task: asyncio.Task[None] | None = None
    try:
        async with AsyncSession(k10_engine, expire_on_commit=False) as session:
            async with TenantAccessService(session=session).authorized(
                principal=principal,
                organization_id=graph.base + 10,
                permission="tenant.restaurants.read",
            ) as unit:
                task = asyncio.create_task(revoke())
                await asyncio.wait_for(started.wait(), timeout=3)
                async with asyncio.timeout(3):
                    while True:
                        async with k10_engine.connect() as observer:
                            waiting = await observer.scalar(
                                text(
                                    "SELECT wait_event_type='Lock' FROM pg_stat_activity WHERE pid=:pid"
                                ),
                                {"pid": pid[0]},
                            )
                        if waiting:
                            break
                        if task.done():
                            await task
                            pytest.fail(
                                "Revocation bypassed the authorization read lock"
                            )
                        await asyncio.sleep(0.02)
                assert [row.id for row in await unit.restaurants()] == [graph.base + 61]
            assert not session.in_transaction()
        await asyncio.wait_for(task, timeout=5)
    finally:
        if task is not None and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
    async with AsyncClient(
        transport=ASGITransport(app=test_app(engine=k10_engine)), base_url="http://test"
    ) as client:
        result = await client.get(
            f"/test/organizations/{graph.base + 10}/restaurants",
            headers={
                "Authorization": "Bearer "
                + token(rsa_keys=rsa_keys, subject=graph.subject(actor="employee"))
            },
        )
        assert result.status_code == 403
