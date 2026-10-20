# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Explicit G2 W-only PostgreSQL rehearsal; stop at the first unexpected result.

Only synthetic tenant rows may remain. Legacy restaurant fixtures use explicit
IDs and are rolled back, preserving every original sequence and business row.
No engine or database operation occurs on import.
"""

from __future__ import annotations

import argparse
import ast
import asyncio
import hashlib
import json
import os
import sys
from collections.abc import (
    AsyncIterator,
    Awaitable,
    Callable,
)
from contextlib import asynccontextmanager
from datetime import (
    datetime,
    timezone,
)
from pathlib import Path
from typing import Any

from sqlalchemy import (
    func,
    insert,
    select,
    text,
)
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.rehearse_tenant_e1 import (
    ROOT,
    TARGET,
    WRITER_BRANCH,
    BoundRehearsal,
    bind_writer,
    check_connection,
    execute,
    run_alembic,
    verify_e1_catalog,
    verify_original_data,
)

BASE = 1900000000
ISSUER = "https://synthetic.invalid/moulai-g2"
PERMISSION = "tenant.restaurants.read"
CaseAction = Callable[[], Awaitable[dict[str, Any]]]


# ==============================================
# SAFE ERROR OBSERVATIONS
# ==============================================


def sqlstate(error: BaseException) -> str | None:
    """Return a PostgreSQL error code without statement parameters or messages."""
    return getattr(getattr(error, "orig", error), "sqlstate", None)


# ==============================================
# SECRET-SAFE FAILURE LOCATION
# ==============================================


def failure_location(error: BaseException) -> list[dict[str, Any]]:
    """Retain code locations only, never locals, SQL, exception text or values."""
    frames: list[dict[str, Any]] = []
    frame = error.__traceback__
    while frame is not None:
        if str(ROOT) in frame.tb_frame.f_code.co_filename:
            frames.append(
                {
                    "file": Path(frame.tb_frame.f_code.co_filename).name,
                    "function": frame.tb_frame.f_code.co_name,
                    "line": frame.tb_lineno,
                }
            )
        frame = frame.tb_next
    return frames[-6:]


# ==============================================
# CHECKED W TRANSACTION (DB HELPER)
# ==============================================


@asynccontextmanager
async def checked_transaction(
    engine: AsyncEngine,
    *,
    bound: BoundRehearsal,
    commit: bool = False,
    isolation: str = "READ COMMITTED",
) -> AsyncIterator[AsyncConnection]:
    """Attest the actual connection before fixtures, with full rollback on error."""
    async with engine.connect() as raw:
        connection = await raw.execution_options(isolation_level=isolation)
        transaction = await connection.begin()
        try:
            await connection.run_sync(
                lambda c: check_connection(c, bound=bound, expected_revision=TARGET)
            )
            await connection.execute(text("SET LOCAL lock_timeout = '8s'"))
            await connection.execute(text("SET LOCAL statement_timeout = '20s'"))
            yield connection
            if commit:
                await transaction.commit()
            else:
                await transaction.rollback()
        except BaseException:
            await transaction.rollback()
            raise


# ==============================================
# SYNTHETIC INSERT HELPERS (DB HELPERS)
# ==============================================


async def identity(connection: AsyncConnection, *, number: int) -> None:
    """Use a collision-detected positive ID and a non-real issuer/subject."""
    await connection.execute(
        text(
            "INSERT INTO public.identities(id,issuer,subject,status) VALUES (:id,:issuer,:subject,'active')"
        ),
        {"id": BASE + number, "issuer": ISSUER, "subject": f"synthetic-{number}"},
    )


async def company(connection: AsyncConnection, *, number: int) -> None:
    """Create only a draft synthetic company, never a real enrollment."""
    await connection.execute(
        text("INSERT INTO public.organizations(id,name) VALUES (:id,:name)"),
        {"id": BASE + number, "name": f"G2 synthetic company {number}"},
    )


async def member(
    connection: AsyncConnection,
    *,
    number: int,
    organization: int,
    person: int,
    role: str = "owner",
) -> None:
    """Store explicit acceptance evidence for synthetic memberships only."""
    await connection.execute(
        text(
            "INSERT INTO public.organization_memberships(id,organization_id,identity_id,role_code,access_mode,status,enrollment_generation,accepted_at,activated_at) VALUES (:id,:organization,:person,:role,:mode,'active',1,now(),now())"
        ),
        {
            "id": BASE + number,
            "organization": BASE + organization,
            "person": BASE + person,
            "role": role,
            "mode": "company-wide" if role == "owner" else "explicit-grants",
        },
    )


async def activate(connection: AsyncConnection, *, organization: int) -> None:
    """Activate a synthetic company after its qualifying membership exists."""
    await connection.execute(
        text(
            "UPDATE public.organizations SET status='active',tenant_enforced_at=now(),revision=revision+1 WHERE id=:id"
        ),
        {"id": BASE + organization},
    )


# ==============================================
# EXPECTED SQL REJECTION (DB HELPER)
# ==============================================


async def reject_sql(
    connection: AsyncConnection,
    *,
    statement: str,
    parameters: dict[str, Any] | None = None,
    states: frozenset[str] = frozenset({"23514"}),
) -> str:
    """Isolate an expected refusal in a savepoint, retaining the outer fixture."""
    savepoint = await connection.begin_nested()
    try:
        await connection.execute(text(statement), parameters or {})
    except DBAPIError as error:
        await savepoint.rollback()
        state = sqlstate(error)
        if state not in states:
            raise AssertionError("unexpected_sqlstate") from None
        return str(state)
    else:
        await savepoint.rollback()
        raise AssertionError("expected_database_refusal")


# ==============================================
# SYNTHETIC FOUNDATION AND ACTUAL COMMIT
# ==============================================


async def provision(*, engine: AsyncEngine, bound: BoundRehearsal) -> dict[str, Any]:
    """Commit an explicitly bounded tenant fixture, preserving legacy tables."""
    async with checked_transaction(engine, bound=bound, commit=True) as connection:
        for number in range(1, 8):
            await identity(connection, number=number)
        for number in (11, 12, 13):
            await company(connection, number=number)
        await member(connection, number=21, organization=11, person=1)
        await member(connection, number=22, organization=12, person=1)
        await member(connection, number=23, organization=11, person=2)
        await member(connection, number=24, organization=11, person=3, role="employee")
        await member(connection, number=25, organization=11, person=4, role="manager")
        await activate(connection, organization=11)
        await activate(connection, organization=12)
    return {"synthetic_id_range": [BASE + 1, BASE + 25], "legacy_rows_inserted": 0}


# ==============================================
# DEFERRED OWNER CHECKS AND VALID OWNER REPLACEMENT
# ==============================================


async def owner_checks(*, engine: AsyncEngine, bound: BoundRehearsal) -> dict[str, Any]:
    """Exercise deferred timing, actual failed commit and final-owner reductions."""
    failures: list[str] = []
    try:
        async with checked_transaction(engine, bound=bound, commit=True) as connection:
            await company(connection, number=80)
            await activate(connection, organization=80)
    except DBAPIError as error:
        if sqlstate(error) != "23514":
            raise
        failures.append("actual_commit_without_owner")
    else:
        raise AssertionError("invalid_company_committed")
    async with checked_transaction(engine, bound=bound) as connection:
        assert (
            await connection.scalar(
                text("SELECT count(*) FROM public.organizations WHERE id=:id"),
                {"id": BASE + 80},
            )
            == 0
        )
        for statement in (
            "UPDATE public.organization_memberships SET role_code='manager',revision=revision+1 WHERE id=:id",
            "UPDATE public.organization_memberships SET status='suspended',suspended_at=now(),revision=revision+1 WHERE id=:id",
            "UPDATE public.organization_memberships SET status='revoked',revoked_at=now(),revision=revision+1 WHERE id=:id",
        ):
            savepoint = await connection.begin_nested()
            await connection.execute(text(statement), {"id": BASE + 22})
            try:
                await connection.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
            except DBAPIError as error:
                if sqlstate(error) != "23514":
                    raise
                failures.append("last_owner_membership")
                await savepoint.rollback()
            else:
                raise AssertionError("last_owner_reduction_allowed")
        for status in ("suspended", "retired"):
            savepoint = await connection.begin_nested()
            await connection.execute(
                text(
                    "UPDATE public.identities SET status=:status,revision=revision+1 WHERE id=:id"
                ),
                {"status": status, "id": BASE + 1},
            )
            try:
                await connection.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
            except DBAPIError as error:
                if sqlstate(error) != "23514":
                    raise
                failures.append("last_owner_identity")
                await savepoint.rollback()
            else:
                raise AssertionError("last_owner_identity_allowed")
    # Commit a valid atomic replacement: old owner can leave only with a successor.
    async with checked_transaction(engine, bound=bound, commit=True) as connection:
        await member(connection, number=26, organization=12, person=2)
        await connection.execute(
            text(
                "UPDATE public.organization_memberships SET status='suspended',suspended_at=now(),revision=revision+1 WHERE id=:id"
            ),
            {"id": BASE + 22},
        )
    return {"expected_refusals": failures, "atomic_replacement_committed": True}


# ==============================================
# REAL BLOCKING OBSERVATION (DB HELPER)
# ==============================================


async def wait_blocked(
    connection: AsyncConnection, *, waiter: int, blocker: int
) -> None:
    """Require a real server lock wait, rather than relying on sleep timing."""
    for _ in range(60):
        if await connection.scalar(
            text("SELECT :blocker = ANY(pg_catalog.pg_blocking_pids(:waiter))"),
            {"blocker": blocker, "waiter": waiter},
        ):
            return
        await asyncio.sleep(0.05)
    raise AssertionError("expected_lock_overlap_not_observed")


# ==============================================
# TWO-OWNER CONCURRENT REMOVAL AND SNAPSHOT CONFLICT
# ==============================================


async def owner_race(
    *, engine: AsyncEngine, bound: BoundRehearsal, isolation: str
) -> dict[str, Any]:
    """Use two pinned real transactions and observe shared-company serialization."""
    async with checked_transaction(engine, bound=bound, commit=True) as connection:
        await connection.execute(
            text(
                "UPDATE public.organization_memberships SET status='active',revision=revision+1 WHERE id=:id"
            ),
            {"id": BASE + 21},
        )
    ready = asyncio.Event()
    release = asyncio.Event()
    pids: dict[str, int] = {}

    # ==============================================
    # FIRST SERIALIZED WRITER
    # ==============================================
    async def first() -> str:
        """Hold the company write until the competing writer really blocks."""
        async with checked_transaction(
            engine, bound=bound, commit=True, isolation=isolation
        ) as connection:
            pids["first"] = int(
                await connection.scalar(text("SELECT pg_backend_pid()"))
            )
            await connection.execute(
                text(
                    "UPDATE public.organization_memberships SET status='suspended',suspended_at=now(),revision=revision+1 WHERE id=:id"
                ),
                {"id": BASE + 21},
            )
            ready.set()
            await asyncio.wait_for(release.wait(), timeout=15)
        return "committed"

    # ==============================================
    # COMPETING OWNER WRITER
    # ==============================================
    async def second() -> str:
        """Require owner-invariant refusal or a whole-transaction snapshot abort."""
        await ready.wait()
        try:
            async with checked_transaction(
                engine, bound=bound, commit=True, isolation=isolation
            ) as connection:
                pids["second"] = int(
                    await connection.scalar(text("SELECT pg_backend_pid()"))
                )
                await connection.execute(
                    text(
                        "UPDATE public.organization_memberships SET status='suspended',suspended_at=now(),revision=revision+1 WHERE id=:id"
                    ),
                    {"id": BASE + 23},
                )
        except DBAPIError as error:
            expected = "23514" if isolation == "READ COMMITTED" else "40001"
            if sqlstate(error) != expected:
                raise
            return expected
        raise AssertionError("both_owner_removals_committed")

    tasks = [asyncio.create_task(first()), asyncio.create_task(second())]
    try:
        await asyncio.wait_for(ready.wait(), timeout=15)
        for _ in range(100):
            if "second" in pids:
                break
            await asyncio.sleep(0.05)
        async with checked_transaction(engine, bound=bound) as observer:
            await wait_blocked(observer, waiter=pids["second"], blocker=pids["first"])
        release.set()
        results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=25)
    finally:
        release.set()
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    retry_count = 0
    if isolation == "REPEATABLE READ":
        try:
            async with checked_transaction(
                engine, bound=bound, commit=True
            ) as connection:
                await connection.execute(
                    text(
                        "UPDATE public.organization_memberships SET status='suspended',suspended_at=now(),revision=revision+1 WHERE id=1900000023"
                    )
                )
        except DBAPIError as error:
            if sqlstate(error) != "23514":
                raise
            retry_count = 1
        else:
            raise AssertionError("retry_removed_last_owner")
    return {
        "isolation": isolation,
        "outcomes": results,
        "server_lock_overlap": True,
        "fresh_transaction_retry_count": retry_count,
    }


# ==============================================
# RAW SQL GOVERNANCE, IMMUTABILITY AND RETENTION
# ==============================================


async def direct_sql(*, engine: AsyncEngine, bound: BoundRehearsal) -> dict[str, Any]:
    """Prove direct SQL cannot bypass retained records or closed policy editing."""
    refusals: list[str] = []
    async with checked_transaction(engine, bound=bound) as connection:
        for statement in (
            "UPDATE public.identities SET subject='changed',revision=revision+1 WHERE id=1900000001",
            "UPDATE public.identities SET revision=revision WHERE id=1900000001",
            "UPDATE public.organizations SET tenant_enforced_at=NULL,revision=revision+1 WHERE id=1900000011",
            "UPDATE public.organization_memberships SET identity_id=1900000007,revision=revision+1 WHERE id=1900000024",
            "DELETE FROM public.identities WHERE id=1900000001",
            "DELETE FROM public.organizations WHERE id=1900000011",
            "DELETE FROM public.organization_memberships WHERE id=1900000024",
            "UPDATE public.tenant_roles SET policy_revision=policy_revision+1 WHERE code='employee'",
            "INSERT INTO public.tenant_role_permissions(role_code,permission_code) VALUES ('employee','tenant.orders.fulfill')",
            "DELETE FROM public.tenant_role_permissions WHERE role_code='employee'",
            "INSERT INTO public.membership_change_proposals(id) VALUES (1900000090)",
            "INSERT INTO public.membership_proposal_restaurants(id) VALUES (1900000090)",
        ):
            refusals.append(await reject_sql(connection, statement=statement))
        # TRUNCATE without CASCADE on a leaf table actually reaches its trigger.
        refusals.append(
            await reject_sql(
                connection, statement="TRUNCATE public.tenant_audit_events"
            )
        )
        # Issuer qualification allows equal subjects across different issuers.
        await connection.execute(
            text(
                "INSERT INTO public.identities(id,issuer,subject,status) VALUES (1900000091,'https://other.synthetic.invalid','synthetic-1','active')"
            )
        )
        refusals.append(
            await reject_sql(
                connection,
                statement="INSERT INTO public.identities(id,issuer,subject,status) VALUES (1900000092,'https://synthetic.invalid/moulai-g2','synthetic-1','active')",
                states=frozenset({"23505"}),
            )
        )
    return {"expected_refusals": len(refusals), "sqlstates": sorted(set(refusals))}


# ==============================================
# IDENTITY SUSPENSION VERSUS NEW OWNER MEMBERSHIP
# ==============================================


async def identity_race(
    *, engine: AsyncEngine, bound: BoundRehearsal
) -> dict[str, Any]:
    """Serialize a previously unassociated identity against a new active owner."""
    async with checked_transaction(engine, bound=bound, commit=True) as first:
        first_pid = int(await first.scalar(text("SELECT pg_backend_pid()")))
        await first.execute(
            text(
                "UPDATE public.identities SET status='suspended',revision=revision+1 WHERE id=1900000005"
            )
        )
        waiter: dict[str, int] = {}

        # ==============================================
        # NEW MEMBERSHIP ON THE COMPETING CONNECTION
        # ==============================================
        async def enroll() -> str:
            """Require the final deferred check to see the suspended identity."""
            try:
                async with checked_transaction(
                    engine, bound=bound, commit=True
                ) as second:
                    waiter["pid"] = int(
                        await second.scalar(text("SELECT pg_backend_pid()"))
                    )
                    await member(second, number=27, organization=13, person=5)
                    await activate(second, organization=13)
            except DBAPIError as error:
                if sqlstate(error) != "23514":
                    raise
                return "23514"
            raise AssertionError("suspended_identity_activated_company")

        task = asyncio.create_task(enroll())
        try:
            for _ in range(100):
                if "pid" in waiter:
                    break
                await asyncio.sleep(0.05)
            await wait_blocked(first, waiter=waiter["pid"], blocker=first_pid)
        except BaseException:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            raise
    outcome = await asyncio.wait_for(task, timeout=20)
    return {"server_lock_overlap": True, "new_owner_refused": outcome}


# ==============================================
# BOUNDED AUTHORIZED WORK VERSUS REVOCATION
# ==============================================


async def revocation_race(
    *, engine: AsyncEngine, bound: BoundRehearsal
) -> dict[str, Any]:
    """Prove revocation waits for bounded work and a fresh session denies access."""
    from app.core.security.oidc import OIDCPrincipal
    from app.core.security.tenant_types import TenantAccessDenied
    from app.services.business.tenant_foundation import (
        TenantAuthorizationService,
        TenantContextResolver,
        tenant_unit_of_work,
    )

    principal = OIDCPrincipal(
        subject="synthetic-3", issuer=ISSUER, realm_roles=frozenset({"owner"})
    )
    waiter: dict[str, int] = {}
    task: asyncio.Task[str] | None = None
    async with checked_transaction(engine, bound=bound, commit=True) as first:
        first_pid = int(await first.scalar(text("SELECT pg_backend_pid()")))
        async with AsyncSession(  # noqa: SIM117
            bind=first, join_transaction_mode="create_savepoint"
        ) as session:
            async with tenant_unit_of_work(session=session):
                context = await TenantContextResolver(session=session).resolve(
                    principal=principal, organization_id=BASE + 11
                )

                # ==============================================
                # CONCURRENT MEMBERSHIP REVOCATION
                # ==============================================
                async def revoke() -> str:
                    """Use a complete checked write transaction, not stale authority."""
                    async with checked_transaction(
                        engine, bound=bound, commit=True
                    ) as second:
                        waiter["pid"] = int(
                            await second.scalar(text("SELECT pg_backend_pid()"))
                        )
                        await second.execute(
                            text(
                                "UPDATE public.organization_memberships SET status='revoked',revoked_at=now(),revision=revision+1 WHERE id=1900000024"
                            )
                        )
                    return "committed"

                task = asyncio.create_task(revoke())
                try:
                    for _ in range(100):
                        if "pid" in waiter:
                            break
                        await asyncio.sleep(0.05)
                    await wait_blocked(first, waiter=waiter["pid"], blocker=first_pid)
                    await TenantAuthorizationService(session=session).require_current(
                        context=context, permission=PERMISSION
                    )
                except BaseException:
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
                    raise
    assert task is not None
    assert await asyncio.wait_for(task, timeout=20) == "committed"
    async with checked_transaction(engine, bound=bound) as connection, AsyncSession(
        bind=connection, join_transaction_mode="create_savepoint"
    ) as session:
        try:
            async with tenant_unit_of_work(session=session):
                await TenantContextResolver(session=session).resolve(
                    principal=principal, organization_id=BASE + 11
                )
        except TenantAccessDenied:
            pass
        else:
            raise AssertionError("revoked_identity_access_allowed")
    return {"bounded_work_serialized": True, "post_revocation_access_denied": True}


# ==============================================
# ACTUAL DEADLOCK AND BOUNDED WHOLE-TRANSACTION RETRY
# ==============================================


async def deadlock(*, engine: AsyncEngine, bound: BoundRehearsal) -> dict[str, Any]:
    """Deliberately reverse two synthetic identity locks and retry the victim."""
    barrier = asyncio.Barrier(2)

    # ==============================================
    # COMPETING SYNTHETIC IDENTITY WRITER
    # ==============================================
    async def writer(*, first: int, second: int) -> str:
        """Hold one real row before requesting the opposite writer's row."""
        try:
            async with checked_transaction(
                engine, bound=bound, commit=True
            ) as connection:
                await connection.execute(
                    text(
                        "UPDATE public.identities SET revision=revision+1 WHERE id=:id"
                    ),
                    {"id": BASE + first},
                )
                await asyncio.wait_for(barrier.wait(), timeout=15)
                await connection.execute(
                    text(
                        "UPDATE public.identities SET revision=revision+1 WHERE id=:id"
                    ),
                    {"id": BASE + second},
                )
        except DBAPIError as error:
            if sqlstate(error) != "40P01":
                raise
            return "40P01"
        return "committed"

    tasks = [
        asyncio.create_task(writer(first=6, second=7)),
        asyncio.create_task(writer(first=7, second=6)),
    ]
    try:
        outcomes = await asyncio.wait_for(asyncio.gather(*tasks), timeout=35)
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    assert sorted(outcomes) == ["40P01", "committed"]
    async with checked_transaction(engine, bound=bound, commit=True) as connection:
        for number in (6, 7):
            await connection.execute(
                text("UPDATE public.identities SET revision=revision+1 WHERE id=:id"),
                {"id": BASE + number},
            )
    return {"outcomes": outcomes, "fresh_ordered_transaction_retry_count": 1}


# ==============================================
# LEGACY FIXTURES, RESTAURANT SCOPE AND COMPOSITE FKS
# ==============================================


async def resource_isolation(
    *, engine: AsyncEngine, bound: BoundRehearsal
) -> dict[str, Any]:
    """Test one owner across two companies and empty grants using actual services."""
    from app.core.security.oidc import OIDCPrincipal
    from app.core.security.tenant_types import TenantAccessDenied
    from app.models.owner import Owner
    from app.models.restaurant import Restaurant
    from app.models.tenant.schema import restaurant_reference
    from app.services.business.tenant_foundation import (
        TenantAuthorizationService,
        TenantContextResolver,
        restaurant_scope,
        tenant_unit_of_work,
    )

    async with checked_transaction(engine, bound=bound) as connection:
        for number in (61, 62):
            await company(connection, number=number)
            await member(connection, number=number, organization=number, person=1)
        await member(connection, number=63, organization=61, person=3, role="employee")
        # Legacy timestamps use the server clock and their existing SQL types.
        now = func.now()
        await connection.execute(
            insert(Owner.__table__).values(
                id=BASE + 70,
                chat_id=-(BASE + 70),
                registration_status="pending",
                created_at=now,
                updated_at=now,
            )
        )
        for number, organization in ((71, 61), (72, 62)):
            await connection.execute(
                insert(Restaurant.__table__).values(
                    id=BASE + number,
                    owner_id=BASE + 70,
                    name=f"Synthetic {number}",
                    type="synthetic",
                    phone=f"synthetic-{number}",
                    wilaya="synthetic",
                    created_at=now,
                    updated_at=now,
                )
            )
            await connection.execute(
                text(
                    "UPDATE public.restaurants SET organization_id=:organization WHERE id=:id"
                ),
                {"organization": BASE + organization, "id": BASE + number},
            )
        await activate(connection, organization=61)
        await activate(connection, organization=62)
        await connection.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        owner = OIDCPrincipal(
            subject="synthetic-1", issuer=ISSUER, realm_roles=frozenset({"owner"})
        )
        employee = OIDCPrincipal(
            subject="synthetic-3", issuer=ISSUER, realm_roles=frozenset({"admin"})
        )
        for principal, expected in ((owner, [BASE + 71]), (employee, [])):
            async with AsyncSession(
                bind=connection,
                join_transaction_mode="create_savepoint",
                expire_on_commit=False,
            ) as session, tenant_unit_of_work(session=session):
                context = await TenantContextResolver(session=session).resolve(
                    principal=principal, organization_id=BASE + 61
                )
                authorization = TenantAuthorizationService(session=session)
                await authorization.require_current(
                    context=context, permission=PERMISSION
                )
                values = (
                    await session.scalars(
                        select(restaurant_reference.c.id).where(
                            restaurant_scope(context=context)
                        )
                    )
                ).all()
                assert values == expected
                try:
                    await authorization.require_restaurant(
                        context=context,
                        restaurant_id=BASE + 72,
                        permission=PERMISSION,
                    )
                except TenantAccessDenied:
                    pass
                else:
                    raise AssertionError("cross_company_access_allowed")
                if principal is employee:
                    try:
                        await authorization.require_restaurant(
                            context=context,
                            restaurant_id=BASE + 71,
                            permission=PERMISSION,
                        )
                    except TenantAccessDenied:
                        pass
                    else:
                        raise AssertionError("empty_grants_allowed_access")
        await reject_sql(
            connection,
            statement="INSERT INTO public.membership_restaurant_grants(id,organization_id,membership_id,restaurant_id) VALUES (1900000093,1900000061,1900000063,1900000072)",
            states=frozenset({"23503"}),
        )
        await reject_sql(
            connection,
            statement="INSERT INTO public.membership_restaurant_grants(id,organization_id,membership_id,restaurant_id) VALUES (1900000093,1900000061,1900000061,1900000071)",
            states=frozenset({"23503"}),
        )
        await reject_sql(
            connection,
            statement="INSERT INTO public.tenant_audit_events(id,organization_id,actor_kind,actor_membership_id,actor_identity_id,target_membership_id,target_identity_id,action,previous_revision,resulting_revision,enrollment_generation,reason_code,correlation_id,policy_before,policy_after) VALUES (1900000094,1900000061,'tenant',1900000061,1900000001,1900000062,1900000001,'synthetic',1,2,1,'synthetic','synthetic','{}','{}')",
            states=frozenset({"23503"}),
        )
        await connection.execute(
            text(
                "INSERT INTO public.membership_restaurant_grants(id,organization_id,membership_id,restaurant_id) VALUES (1900000093,1900000061,1900000063,1900000071)"
            )
        )
        await reject_sql(
            connection,
            statement="UPDATE public.restaurants SET organization_id=1900000062 WHERE id=1900000071",
        )
        await reject_sql(
            connection, statement="DELETE FROM public.owners WHERE id=1900000070"
        )
    return {
        "same_owner_two_companies": True,
        "empty_grants_denied": True,
        "realm_admin_not_platform_permission": True,
        "cross_company_fk_rejected": True,
        "legacy_fixtures_rolled_back": True,
    }


# ==============================================
# ORM REVOCATION, CAS, REVISIONS AND APPEND-ONLY AUDIT
# ==============================================


async def orm_revocation(
    *, engine: AsyncEngine, bound: BoundRehearsal
) -> dict[str, Any]:
    """Execute the preparatory service against actual triggers, without HTTP routes."""
    from app.core.security.oidc import OIDCPrincipal
    from app.core.security.tenant_types import TenantConflict
    from app.services.business.tenant_foundation import (
        MembershipService,
        tenant_unit_of_work,
    )

    principal = OIDCPrincipal(
        subject="synthetic-2", issuer=ISSUER, realm_roles=frozenset()
    )
    async with checked_transaction(engine, bound=bound) as connection:
        before = int(
            await connection.scalar(
                text("SELECT revision FROM public.organizations WHERE id=1900000011")
            )
        )
        async with AsyncSession(
            bind=connection,
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,
        ) as session, tenant_unit_of_work(session=session):
            mutation = await MembershipService(session=session).revoke_non_owner(
                principal=principal,
                organization_id=BASE + 11,
                membership_id=BASE + 25,
                expected_revision=1,
            )
            assert mutation.revision == 2 and mutation.status == "revoked"
        assert (
            int(
                await connection.scalar(
                    text(
                        "SELECT revision FROM public.organizations WHERE id=1900000011"
                    )
                )
            )
            == before + 1
        )
        assert (
            int(
                await connection.scalar(
                    text("SELECT count(*) FROM public.tenant_audit_events")
                )
            )
            == 1
        )
        async with AsyncSession(
            bind=connection, join_transaction_mode="create_savepoint"
        ) as session:
            try:
                async with tenant_unit_of_work(session=session):
                    await MembershipService(session=session).revoke_non_owner(
                        principal=principal,
                        organization_id=BASE + 11,
                        membership_id=BASE + 25,
                        expected_revision=1,
                    )
            except TenantConflict:
                pass
            else:
                raise AssertionError("stale_cas_accepted")
        await reject_sql(
            connection,
            statement="UPDATE public.tenant_audit_events SET action='changed'",
        )
        await reject_sql(connection, statement="DELETE FROM public.tenant_audit_events")
        await reject_sql(
            connection,
            statement="UPDATE public.organization_memberships SET status='active',revision=revision+1 WHERE id=1900000025",
        )
        await connection.execute(
            text(
                "UPDATE public.organization_memberships SET status='pending',access_mode='explicit-grants',enrollment_generation=enrollment_generation+1,accepted_at=NULL,activated_at=NULL,suspended_at=NULL,revoked_at=NULL,revision=revision+1 WHERE id=1900000025"
            )
        )
    return {
        "service_cas_audit": True,
        "trigger_company_revision_refreshed": True,
        "retention_refusals": 2,
        "fresh_pending_enrollment": True,
    }


# ==============================================
# POPULATED DOWNGRADE MUST REFUSE BEFORE DROPS
# ==============================================


async def populated_downgrade(
    *, engine: AsyncEngine, bound: BoundRehearsal
) -> dict[str, Any]:
    """Attempt the approved downgrade on W and verify atomic refusal afterward."""
    try:
        async with checked_transaction(engine, bound=bound) as connection:
            await connection.run_sync(
                lambda c: run_alembic(c, bound=bound, direction="downgrade")
            )
    except DBAPIError as error:
        if sqlstate(error) != "23514":
            raise
    else:
        raise AssertionError("populated_downgrade_allowed")
    async with checked_transaction(engine, bound=bound) as connection:
        catalog = await verify_e1_catalog(
            connection, legacy_tables=set(bound.baseline["tables"])
        )
    return {"sqlstate": "23514", "catalog_intact": catalog}


# ==============================================
# COMPLETE-TRANSACTION TIMEOUT AND RETRY
# ==============================================


async def timeouts(*, engine: AsyncEngine, bound: BoundRehearsal) -> dict[str, Any]:
    """Verify statement timeout abort and retry using a fresh full transaction."""
    try:
        async with checked_transaction(engine, bound=bound, commit=True) as connection:
            await connection.execute(
                text(
                    "UPDATE public.identities SET revision=revision+1 WHERE id=1900000007"
                )
            )
            await connection.execute(text("SET LOCAL statement_timeout = '50ms'"))
            await connection.execute(text("SELECT pg_sleep(0.2)"))
    except DBAPIError as error:
        if sqlstate(error) != "57014":
            raise
    else:
        raise AssertionError("statement_timeout_missing")
    async with checked_transaction(engine, bound=bound, commit=True) as connection:
        assert (
            await connection.scalar(
                text("SELECT revision FROM public.identities WHERE id=1900000007")
            )
            == 1
        )
        await connection.execute(
            text("UPDATE public.identities SET revision=revision+1 WHERE id=1900000007")
        )
    async with checked_transaction(engine, bound=bound) as blocker:
        await blocker.execute(
            text("SELECT id FROM public.identities WHERE id=1900000006 FOR UPDATE")
        )
        try:
            async with checked_transaction(engine, bound=bound, commit=True) as waiter:
                await waiter.execute(text("SET LOCAL lock_timeout = '50ms'"))
                await waiter.execute(
                    text(
                        "UPDATE public.identities SET revision=revision+1 WHERE id=1900000006"
                    )
                )
        except DBAPIError as error:
            if sqlstate(error) != "55P03":
                raise
        else:
            raise AssertionError("lock_timeout_missing")
    return {
        "sqlstate": "57014",
        "lock_timeout_sqlstate": "55P03",
        "full_rollback": True,
        "fresh_transaction_retry_count": 1,
    }


# ==============================================
# ORIGINAL CATALOG AND SQL AUTHORIZATION PRESERVATION
# ==============================================


async def original_catalogs(
    connection: AsyncConnection, *, bound: BoundRehearsal
) -> dict[str, Any]:
    """Compare original schema/ACL hashes, excluding only reviewed E1 additions."""
    from migration_support.tenant_e1 import operation_metadata
    from migration_support.tenant_e1_sql import (
        FUNCTION_SIGNATURES,
        TRIGGER_DEFINITIONS,
    )

    path = ROOT / "scripts/tenant_catalog_queries.py"
    if (
        hashlib.sha256(path.read_bytes()).hexdigest()
        != "e66ac287ae8f1d97d9ba886a9c22c72a1dae11a7f79756ae834111116e6387d2"
    ):
        raise RuntimeError("reviewed_catalog_contract_changed")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    catalog_node = next(
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "CATALOGS"
            for target in node.targets
        )
    )
    queries: dict[str, str] = ast.literal_eval(catalog_node.value)
    metadata = operation_metadata()
    legacy = set(bound.baseline["tables"])
    sequences = set(bound.baseline["sequences"])
    added_constraints = {
        (name, str(c.name))
        for name, table in metadata.tables.items()
        for c in table.constraints
    }
    added_indexes = {
        (name, str(index.name))
        for name, table in metadata.tables.items()
        for index in table.indexes
    } | added_constraints
    functions = {signature.split("(")[0] for signature in FUNCTION_SIGNATURES}
    added_triggers = {(table, name) for table, name, _ in TRIGGER_DEFINITIONS}

    # ==============================================
    # DRIVER CHAR NORMALIZATION
    # ==============================================
    def normalize(value: Any) -> Any:
        """Match G1's canonical representation without exporting SQL literals."""
        if isinstance(value, bytes):
            return value.decode("ascii")
        if isinstance(value, dict):
            return {key: normalize(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [normalize(item) for item in value]
        return value

    evidence: dict[str, Any] = {}
    for category, query in queries.items():
        rows = [dict(row) for row in (await connection.execute(text(query))).mappings()]
        if category == "columns":
            rows = [
                row
                for row in rows
                if row["table_name"] in legacy
                and row["attname"]
                in bound.baseline["tables"][row["table_name"]]["columns"]
            ]
        elif category == "constraints":
            rows = [
                row
                for row in rows
                if row["table_name"] in legacy
                and (row["table_name"], row["conname"]) not in added_constraints
            ]
        elif category == "indexes":
            rows = [
                row
                for row in rows
                if row["table_name"] in legacy
                and (row["table_name"], row["name"]) not in added_indexes
            ]
        elif category == "relations":
            rows = [row for row in rows if row["relname"] in legacy | sequences]
        elif category == "sequence_definitions":
            rows = [row for row in rows if row["relname"] in sequences]
        elif category == "triggers":
            rows = [
                row
                for row in rows
                if (row["table_name"], row["tgname"]) not in added_triggers
            ]
        elif category == "routines":
            rows = [row for row in rows if row["proname"] not in functions]
        digest = hashlib.sha256(
            json.dumps(
                normalize(rows), sort_keys=True, separators=(",", ":"), default=str
            ).encode("utf-8")
        ).hexdigest()
        actual = {"count": len(rows), "sha256": digest}
        if actual != bound.baseline["catalogs"][category]:
            raise RuntimeError("original_catalog_changed_" + category)
        evidence[category] = actual
    return evidence


# ==============================================
# FAIL-FAST G2 EXECUTION AND SANITIZED RESULTS
# ==============================================


async def run_suite(*, bound: BoundRehearsal, output: Path) -> int:
    """Apply only E1, then stop on any unexpected SQL or authorization outcome."""
    from app.core.test_database import isolated_connection_arguments

    upgrade = output.parent / "second-upgrade.json"
    if await execute(bound=bound, direction="upgrade", output=upgrade):
        return 1
    engine = create_async_engine(
        bound.url,
        echo=False,
        poolclass=NullPool,
        connect_args=isolated_connection_arguments(),
    )
    results: list[dict[str, Any]] = []
    cases: list[tuple[str, str, CaseAction]] = [
        (
            "P03/P05",
            "synthetic foundation",
            lambda: provision(engine=engine, bound=bound),
        ),
        (
            "P04/P05/P06",
            "owner lifecycle and real commit",
            lambda: owner_checks(engine=engine, bound=bound),
        ),
        (
            "P07",
            "concurrent owner removal",
            lambda: owner_race(engine=engine, bound=bound, isolation="READ COMMITTED"),
        ),
        (
            "P07",
            "identity status versus new membership",
            lambda: identity_race(engine=engine, bound=bound),
        ),
        (
            "P08/P09/P10/P12",
            "same-owner resource isolation",
            lambda: resource_isolation(engine=engine, bound=bound),
        ),
        (
            "P12/P14/P15",
            "SQL bypass and retention",
            lambda: direct_sql(engine=engine, bound=bound),
        ),
        (
            "P13/P16",
            "ORM CAS and audit",
            lambda: orm_revocation(engine=engine, bound=bound),
        ),
        (
            "P11",
            "bounded work versus revocation",
            lambda: revocation_race(engine=engine, bound=bound),
        ),
        (
            "P17",
            "repeatable-read owner race",
            lambda: owner_race(engine=engine, bound=bound, isolation="REPEATABLE READ"),
        ),
        (
            "P17",
            "timeout and whole transaction retry",
            lambda: timeouts(engine=engine, bound=bound),
        ),
        (
            "P17",
            "deadlock and whole transaction retry",
            lambda: deadlock(engine=engine, bound=bound),
        ),
        (
            "P18",
            "populated downgrade refusal",
            lambda: populated_downgrade(engine=engine, bound=bound),
        ),
    ]
    failure: dict[str, Any] | None = None
    try:
        for case_id, name, action in cases:
            try:
                evidence = await asyncio.wait_for(action(), timeout=150)
            # Never record arbitrary exception text, SQL, credentials or rows.
            except Exception as error:  # noqa: BLE001
                failure = {
                    "id": case_id,
                    "name": name,
                    "error_class": type(error).__name__,
                    "sqlstate": sqlstate(error),
                    "locations": failure_location(error),
                }
                results.append({**failure, "status": "failed"})
                output.write_text(
                    json.dumps({"cases": results, "stopped_on_failure": True}, indent=2)
                    + "\n",
                    encoding="utf-8",
                )
                break
            results.append(
                {"id": case_id, "name": name, "status": "passed", "evidence": evidence}
            )
            print(json.dumps({"id": case_id, "status": "passed"}), flush=True)
            output.write_text(
                json.dumps({"cases": results, "in_progress": True}, indent=2) + "\n",
                encoding="utf-8",
            )
        # This inspection is read-only, including after a failed test.
        async with engine.connect() as connection, connection.begin():
            await connection.execute(text("SET TRANSACTION READ ONLY"))
            await connection.run_sync(
                lambda c: check_connection(c, bound=bound, expected_revision=TARGET)
            )
            await verify_original_data(
                connection, baseline=bound.baseline, revision=TARGET
            )
            catalog = await verify_e1_catalog(
                connection, legacy_tables=set(bound.baseline["tables"])
            )
            preserved_catalogs = await original_catalogs(connection, bound=bound)
    finally:
        await engine.dispose()
    report = {
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "writer_branch": WRITER_BRANCH,
        "cases": results,
        "stopped_on_failure": failure is not None,
        "original_rows_and_sequences_unchanged": True,
        "final_revision": TARGET,
        "catalog": catalog,
        "original_catalogs": preserved_catalogs,
    }
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 1 if failure else 0


# ==============================================
# EXPLICIT LOCAL ENTRY POINT
# ==============================================


def main() -> int:
    """Accept only reviewed files, with no URL, branch or revision override."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--approved-sha256", required=True)
    parser.add_argument("--proof", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    os.chdir(ROOT)
    os.environ.update(
        {
            "DEBUG": "false",
            "DB_ECHO": "false",
            "OIDC_DIAGNOSTICS_ENABLED": "false",
            "OIDC_ALLOW_LOCAL_HTTP": "false",
        }
    )
    sys.path.insert(0, str(ROOT))
    try:
        bound = bind_writer(
            manifest_path=arguments.manifest,
            approved_sha256=arguments.approved_sha256,
            proof_path=arguments.proof,
            baseline_path=arguments.baseline,
        )
        return asyncio.run(run_suite(bound=bound, output=arguments.output))
    # Keep the process boundary secret-safe even when Settings fail validation.
    except Exception as error:  # noqa: BLE001
        report = (
            json.loads(arguments.output.read_text(encoding="utf-8"))
            if arguments.output.exists()
            else {}
        )
        report.update(
            status="blocked",
            error_class=type(error).__name__,
            sqlstate=sqlstate(error),
            locations=failure_location(error),
        )
        arguments.output.write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(report))
        return 1


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    raise SystemExit(main())
