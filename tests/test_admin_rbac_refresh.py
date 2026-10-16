# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Prove PostgreSQL administrative revocations refresh an existing ORM session."""

# ==============================================
# IMPORTS
# ==============================================

from dataclasses import dataclass
from typing import (
    Literal,
    TypeAlias,
)

import pytest
from sqlalchemy import (
    delete,
    insert,
    update,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from app.core.exceptions import UnauthorizedError
from app.models.admin import Admin
from app.models.rbac import (
    Permission,
    Role,
    role_permissions,
)
from app.services.business.admin.admin_service import AdminService

# ==============================================
# ISOLATED AUTHORIZATION GRAPH
# ==============================================

Revocation: TypeAlias = Literal["permission", "role", "admin"]


@dataclass(frozen=True)
class AuthorizationGraph:
    """Retain only fixture identifiers and the guarded test session factory."""

    admin_id: int
    role_id: int
    permission_id: int
    sessions: async_sessionmaker[AsyncSession]


@pytest.fixture
async def authorization_graph(db_session: AsyncSession) -> AuthorizationGraph:
    """Persist an active reviewer role without modifying seeded production data.

    The repository's db_session fixture enforces neondb_test and performs
    cleanup. Committing this graph permits an independent writer session.
    """
    role_id = (
        await db_session.execute(
            insert(Role)
            .values(code="refresh-test-finance", name="Refresh finance", is_active=True)
            .returning(Role.id)
        )
    ).scalar_one()
    permission_id = (
        await db_session.execute(
            insert(Permission)
            .values(code="payments.review", name="Review manual transfers")
            .returning(Permission.id)
        )
    ).scalar_one()
    await db_session.execute(
        insert(role_permissions).values(role_id=role_id, permission_id=permission_id)
    )
    admin_id = (
        await db_session.execute(
            insert(Admin)
            .values(
                chat_id=950001,
                role="admin",
                role_id=role_id,
                auth_subject="refresh-test-verified-subject",
                is_active=True,
            )
            .returning(Admin.id)
        )
    ).scalar_one()
    await db_session.commit()
    sessions = async_sessionmaker(
        db_session.bind, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    return AuthorizationGraph(
        admin_id=admin_id,
        role_id=role_id,
        permission_id=permission_id,
        sessions=sessions,
    )


# ==============================================
# REVOKE THROUGH AN INDEPENDENT TRANSACTION
# ==============================================


async def revoke_authorization(
    *, graph: AuthorizationGraph, change: Revocation
) -> None:
    """Commit a real authorization change independently of the cached reader."""
    async with graph.sessions() as writer, writer.begin():
        if change == "permission":
            await writer.execute(
                delete(role_permissions).where(
                    role_permissions.c.role_id == graph.role_id,
                    role_permissions.c.permission_id == graph.permission_id,
                )
            )
        elif change == "role":
            await writer.execute(
                update(Role).where(Role.id == graph.role_id).values(is_active=False)
            )
        else:
            await writer.execute(
                update(Admin).where(Admin.id == graph.admin_id).values(is_active=False)
            )


# ==============================================
# CACHED SESSION REVOCATION PROOF
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["permission", "role", "admin"])
async def test_committed_revocation_denies_the_next_cached_session_decision(
    authorization_graph: AuthorizationGraph, change: Revocation
) -> None:
    """A cached allowed graph must not survive a committed role or grant revocation."""
    graph = authorization_graph
    async with graph.sessions() as reader:
        service = AdminService(reader)
        cached_admin = await service.admin_repo.get_authorization_context(
            admin_id=graph.admin_id
        )
        assert cached_admin is not None
        cached_role = cached_admin.role_record
        assert cached_role is not None
        assert cached_admin.is_active is True
        assert cached_role.is_active is True
        assert "payments.review" in {item.code for item in cached_role.permissions}
        assert await service.check_admin_permission(
            admin_id=graph.admin_id, required_permission="payments.review"
        )

        await revoke_authorization(graph=graph, change=change)

        # Strong references preserve the previously authorized identity graph.
        # No explicit expire, refresh, rollback, or session replacement occurs.
        assert cached_admin.is_active is True
        assert cached_role.is_active is True
        assert "payments.review" in {item.code for item in cached_role.permissions}
        with pytest.raises(UnauthorizedError):
            await service.check_admin_permission(
                admin_id=graph.admin_id, required_permission="payments.review"
            )

        if change == "permission":
            assert cached_role.permissions == []
        elif change == "role":
            assert cached_role.is_active is False
        else:
            assert cached_admin.is_active is False
