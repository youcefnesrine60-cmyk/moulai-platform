# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Verify the real global restaurant router's administrative boundary offline."""

import re
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import (
    AsyncMock,
    Mock,
)

import pytest
from fastapi import FastAPI
from httpx import (
    ASGITransport,
    AsyncClient,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import auth
from app.api.v1.restaurant import router
from app.api.v1.restaurant.restaurants import restaurant_router
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import (
    NotFoundError,
    UnauthorizedError,
)
from app.services.business.admin.admin_service import AdminService

# ==============================================
# REAL AGGREGATE AND INERT IO BOUNDARIES
# ==============================================


def restaurant_app() -> FastAPI:
    """Mount the same guarded aggregate included by the production application."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return app


OPERATIONS = tuple(
    (method.upper(), re.sub(r"\{[^}]+\}", "7", path))
    for path, operations in restaurant_app().openapi()["paths"].items()
    for method in operations
    if method in {"get", "post", "put", "patch", "delete"}
)


def inert_database(*, app: FastAPI) -> AsyncMock:
    """Replace storage while retaining the actual authentication dependencies."""
    session = AsyncMock(spec=AsyncSession)

    async def database() -> AsyncIterator[AsyncSession]:
        """Provide a session double that cannot connect to a live database."""
        yield session

    app.dependency_overrides[get_db] = database
    return session


async def send(*, app: FastAPI, method: str, path: str) -> Any:
    """Send forged identifiers over the real in-process HTTP request boundary."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="https://local.test"
    ) as client:
        return await client.request(
            method,
            path,
            params={"owner_id": 7, "admin_id": 7, "chat_id": 7},
            json={"owner_id": 7, "admin_id": 7, "chat_id": 7, "role": "superadmin"},
        )


# ==============================================
# AUTHENTICATION AND LIVE PERMISSION CHECKS
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", OPERATIONS)
@pytest.mark.parametrize("configured", [False, True])
async def test_every_operation_rejects_unauthenticated_identifiers(
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
    configured: bool,
) -> None:
    """Global restaurant operations require identity before any storage call."""
    for name, value in {
        "OIDC_ISSUER": "https://identity.invalid/realms/test",
        "OIDC_AUDIENCE": "test-api",
        "OIDC_JWKS_URL": "https://identity.invalid/realms/test/certs",
    }.items():
        monkeypatch.setattr(settings, name, value if configured else None)
    app = restaurant_app()
    session = inert_database(app=app)
    response = await send(app=app, method=method, path=path)
    assert response.status_code == (401 if configured else 503), response.text
    session.execute.assert_not_awaited()
    session.commit.assert_not_awaited()
    session.flush.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", OPERATIONS)
async def test_every_operation_rechecks_restaurant_administration_permission(
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
) -> None:
    """A verified administrator without the current permission is still denied."""
    app = restaurant_app()
    session = inert_database(app=app)
    app.dependency_overrides[auth.get_current_admin] = lambda: auth.AdminPrincipal(
        admin_id=7
    )
    permission = AsyncMock(side_effect=UnauthorizedError(message="Permission denied"))
    monkeypatch.setattr(AdminService, "check_admin_permission", permission)
    response = await send(app=app, method=method, path=path)
    assert response.status_code == 403, response.text
    permission.assert_awaited_once_with(
        admin_id=7, required_permission="restaurants.manage"
    )
    session.execute.assert_not_awaited()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_authorized_administrator_reaches_restaurant_business_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The guard permits a legitimate administrative request after RBAC succeeds."""
    app = restaurant_app()
    inert_database(app=app)
    app.dependency_overrides[auth.get_current_admin] = lambda: auth.AdminPrincipal(
        admin_id=7
    )
    permission = AsyncMock()
    monkeypatch.setattr(AdminService, "check_admin_permission", permission)
    service = Mock(spec=["get_restaurant"])
    service.get_restaurant = AsyncMock(
        side_effect=NotFoundError(message="Restaurant not found")
    )
    app.dependency_overrides[restaurant_router.get_restaurant_service] = lambda: service
    response = await send(app=app, method="GET", path="/api/v1/restaurants/7")
    assert response.status_code == 404, response.text
    permission.assert_awaited_once_with(
        admin_id=7, required_permission="restaurants.manage"
    )
    service.get_restaurant.assert_awaited_once_with(restaurant_id=7)


@pytest.mark.asyncio
async def test_simulation_routes_are_not_exposed_by_application_aggregate() -> None:
    """Synthetic metric mutations cannot be invoked through the deployed router."""
    app = restaurant_app()
    assert OPERATIONS
    assert not any("simulate" in path for path in app.openapi()["paths"])
    response = await send(
        app=app, method="POST", path="/api/v1/restaurant-metrics/7/simulate-order"
    )
    assert response.status_code == 404
