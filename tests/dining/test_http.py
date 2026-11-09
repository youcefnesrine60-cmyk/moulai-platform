# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# OPT-IN HTTP AUTHENTICATION AND COMMIT BOUNDARY
# Prove that current identities and scoped grants still control local HTTP reads.
# ==============================================

"""ASGI in-process only; no public server, real token, JWKS or external transport."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND LOCAL SESSION FACTORY
# Inject only the real disposable D1 engine and synthetic verified principals.
# ==============================================

from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import (
    ASGITransport,
    AsyncClient,
)
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
)

from app.api.dining import dining_router
from app.api.tenant_dependencies import get_business_oidc_principal
from app.core.security.oidc import OIDCPrincipal
from tests.dining.support import (
    configure_graph,
    create_graph,
)

pytestmark = pytest.mark.dining_postgres


# ==============================================
# TEST OPT IN HTTP DENIES UNAUTHENTICATED AND FOREIGN SCOPE
# Mount only this local test router; normal app.main stays untouched.
# ==============================================


async def test_opt_in_http_denies_unauthenticated_and_foreign_scope(
    dining_engine: AsyncEngine,
) -> None:
    """Mount only this local test router; normal app.main stays untouched."""
    graph = await configure_graph(graph=await create_graph(engine=dining_engine))

    # ==============================================
    # SESSIONS
    # Supply clean independent local sessions, with no ambient outer fixture.
    # ==============================================

    async def sessions() -> AsyncIterator[AsyncSession]:
        """Supply clean independent local sessions, with no ambient outer fixture."""
        async with graph.factory() as session:
            yield session

    app = FastAPI()
    app.include_router(dining_router(session_dependency=sessions))
    route = f"/organizations/{graph.base+10}/restaurants/{graph.base+200}/branches/{graph.base+300}/dining/planning"
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://inprocess.local"
    ) as client:
        assert (
            await client.get(
                route,
                params={
                    "starts_at": "2026-11-03T20:00:00Z",
                    "ends_at": "2026-11-03T21:30:00Z",
                },
            )
        ).status_code == 401

        # ==============================================
        # PRINCIPAL
        # Test-only verified identity override, never a deployed authentication path.
        # ==============================================

        async def principal() -> OIDCPrincipal:
            """Test-only verified identity override, never a deployed authentication path."""
            return graph.principal(actor="cleaner")

        app.dependency_overrides[get_business_oidc_principal] = principal
        response = await client.get(
            route,
            params={
                "starts_at": "2026-11-03T20:00:00Z",
                "ends_at": "2026-11-03T21:30:00Z",
            },
        )
        assert response.status_code == 200 and len(response.json()) == 2
        foreign = route.replace(
            f"branches/{graph.base+300}", f"branches/{graph.base+301}"
        )
        assert (
            await client.get(
                foreign,
                params={
                    "starts_at": "2026-11-03T20:00:00Z",
                    "ends_at": "2026-11-03T21:30:00Z",
                },
            )
        ).status_code in {403, 409}
        viewer = await client.get("/verify-reservation")
        assert viewer.status_code == 200 and "credentials:'omit'" in viewer.text
        assert "script-src 'sha256-" in viewer.headers["Content-Security-Policy"]
        assert (
            await client.post("/dining/verify-reservation", json={"token": "a" * 43})
        ).status_code == 404
