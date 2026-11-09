# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# ENROLLMENT HTTP RESPONSE REGRESSION
# Execute actual ASGI routing and response validation while explicitly replacing identity and persistence IO.
# ==============================================

"""This offline serialization proof is separate from actual local Keycloak and PostgreSQL acceptance."""

# isort: split
# ==============================================
# CONTROLLED OFFLINE DEPENDENCIES
# No database session or identity provider connection can be opened by these tests.
# ==============================================

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import (
    Depends,
    FastAPI,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.oidc import OIDCPrincipal
from app.integration.config import IntegrationConfig
from app.integration.enrollment_routes import mount_enrollment_routes
from app.integration.identity import BrowserIdentity
from app.services.business.enrollment import EnrollmentService

# ==============================================
# JSON ALIAS RESOLUTION AT THE REAL HTTP BOUNDARY
# Both a first-time null dossier and nested JSON must survive FastAPI's response adapter.
# ==============================================


@pytest.mark.parametrize(
    "value", [None, {"id": 1, "nested": {"items": ["fr", 2, True, None]}}]
)
def test_enrollment_route_serializes_json(
    value: dict[str, object] | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reproduce the formerly unresolved recursive alias without bypassing response validation."""
    app = FastAPI()
    session = AsyncMock(spec=AsyncSession)
    person = BrowserIdentity(
        principal=OIDCPrincipal(
            issuer="https://local.test", subject="test-account", realm_roles=frozenset()
        ),
        name="Offline test",
        access_token="OFFLINE-NO-PROVIDER",
    )

    # ==============================================
    # FRAMEWORK DEPENDENCIES
    # Typed synthetic dependencies establish only the response test context, never an operational login.
    # ==============================================

    async def identity() -> BrowserIdentity:
        """Return the synthetic principal used exclusively by this offline HTTP test."""
        return person

    async def sessions() -> AsyncSession:
        """Return a mock transaction boundary without performing persistence IO."""
        return session

    configuration = IntegrationConfig(
        directory=Path("D:/MoulAI/artifacts/offline"),
        instance_id="a" * 32,
        database_url="postgresql+asyncpg://moulai_integrated:"
        + "a" * 64
        + "@127.0.0.1:55433/moulai_integrated",
        client_secret="offline",
        session_key="offline",
        admin_password="offline",
    )
    monkeypatch.setattr(EnrollmentService, "view", AsyncMock(return_value=value))
    mount_enrollment_routes(
        app=app,
        configuration=configuration,
        identity_dep=Depends(identity),
        session_dep=Depends(sessions),
    )

    # ==============================================
    # ACTUAL ASGI EXECUTION
    # Transport stays in process and FastAPI performs its ordinary serializer validation.
    # ==============================================

    async def scenario() -> None:
        """Require the actual HTTP response status and exact JSON without opening a socket."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="https://offline.test"
        ) as client:
            response = await client.get("/api/web/enrollment")
            assert response.status_code == 200
            assert response.json() == value

    asyncio.run(scenario())
