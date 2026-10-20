# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Targeted offline checks for the K10 opt-in HTTP composition."""

from collections.abc import AsyncIterator

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import (
    ASGITransport,
    AsyncClient,
)
from sqlalchemy import Engine
from sqlalchemy.ext.asyncio import AsyncSession

from test_support.tenant_http_app import create_tenant_test_app
from tests.test_tenant_access import read_engine
from tests.test_tenant_access_http import (
    jwks,
    rsa_keys,
    token,
)
from tests.test_tenant_foundation import (
    MemoryAsyncSession,
    local_engine,
)

__all__ = ["jwks", "local_engine", "read_engine", "rsa_keys"]


# ==============================================
# PERSONAL ASSOCIATION DISCOVERY THROUGH THE REAL DEPENDENCY
# ==============================================


@pytest.mark.parametrize(
    "subject,expected", [("fixture-owner", 200), ("missing", 403), (None, 401)]
)
async def test_personal_membership_dependency(
    read_engine: Engine,
    jwks: object,
    rsa_keys: tuple[rsa.RSAPrivateKey, rsa.RSAPrivateKey],
    subject: str | None,
    expected: int,
) -> None:
    """Authenticate and resolve the local identity without implicit tenant selection."""

    # ==============================================
    # MEMORY-ONLY REQUEST SESSION
    # ==============================================
    async def session_dependency() -> AsyncIterator[AsyncSession]:
        """Reuse the K9 SQL fixture, with no connection to a configured database."""
        session = MemoryAsyncSession(expire_on_commit=False)
        session.sync_session.bind = read_engine
        try:
            yield session
        finally:
            session.sync_session.close()

    app = create_tenant_test_app(session_dependency=session_dependency)
    assert len(app.routes) == 3
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        if subject is not None:
            client.headers["Authorization"] = "Bearer " + token(
                rsa_keys=rsa_keys, subject=subject
            )
        response = await client.get("/test/memberships")
        assert response.status_code == expected
        if expected == 200:
            assert {row["organization_id"] for row in response.json()} == {1, 2}
            assert (await client.get("/test/memberships?limit=0")).status_code == 422
            assert (
                await client.get("/test/memberships?after_id=-1")
            ).status_code == 422
            assert (await client.get("/test/memberships?limit=101")).status_code == 422


# ==============================================
# UNRELEASED AND PLATFORM PERMISSIONS REMAIN UNAVAILABLE
# ==============================================


@pytest.mark.parametrize(
    "permission", ["tenant.orders.fulfill", "payments.review", "*", "unknown"]
)
def test_test_app_rejects_permission_escalation(permission: str) -> None:
    """The factory cannot install a permissive parallel authorization vocabulary."""
    with pytest.raises(ValueError, match="tenant_permission_unavailable"):
        create_tenant_test_app(
            session_dependency=MemoryAsyncSession, restaurant_permission=permission
        )
