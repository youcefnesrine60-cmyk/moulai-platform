# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""HTTP regressions for owner isolation and protected administrative operations."""

from collections.abc import AsyncIterator
from typing import (
    Any,
    cast,
)
from unittest.mock import (
    AsyncMock,
    MagicMock,
    create_autospec,
)

import pytest
from fastapi import FastAPI
from httpx import (
    ASGITransport,
    AsyncClient,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import auth
from app.api.auth import (
    AdminPrincipal,
    OwnerPrincipal,
    get_current_owner,
)
from app.api.v1.owners import (
    ADMIN_DEPENDENCIES,
    get_owner_service,
    router,
)
from app.core.exceptions import ValidationError
from app.core.database import get_db
from app.services.business.owner_service import OwnerService
from tests.test_owner_statistics_contracts import owner_record

# ==============================================
# ISOLATED HTTP APPLICATION
# ==============================================


@pytest.fixture
def owner_application() -> tuple[FastAPI, MagicMock]:
    """Create an API application whose business methods require no network."""
    application = FastAPI()
    application.include_router(router)
    service = create_autospec(OwnerService, instance=True)
    application.dependency_overrides[get_owner_service] = lambda: service
    application.dependency_overrides[get_current_owner] = lambda: OwnerPrincipal(
        owner_id=17,
    )
    return application, service


def authorize_administrator(*, application: FastAPI) -> None:
    """Override the live permission dependency only for authorized test requests."""
    application.dependency_overrides[ADMIN_DEPENDENCIES[0].dependency] = lambda: (
        AdminPrincipal(admin_id=3)
    )


# ==============================================
# TENANT ISOLATION
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "body"),
    [
        ("GET", None),
        ("PATCH", {"full_name": "Another Owner"}),
        ("DELETE", None),
    ],
)
async def test_owner_cannot_read_change_or_delete_another_owner(
    owner_application: tuple[FastAPI, MagicMock],
    method: str,
    body: dict[str, Any] | None,
) -> None:
    """Another owner's identifier is rejected before reaching the service."""
    application, service = owner_application
    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://test",
    ) as client:
        response = await client.request(method, "/owners/18", json=body)

    assert response.status_code == 404
    service.get_owner_by_id.assert_not_awaited()
    service.update_owner.assert_not_awaited()
    service.delete_owner.assert_not_awaited()


@pytest.mark.asyncio
async def test_chat_lookup_uses_the_authenticated_owner_only(
    owner_application: tuple[FastAPI, MagicMock],
) -> None:
    """A foreign Telegram chat identifier never selects another owner's record."""
    application, service = owner_application
    service.get_owner_by_id.return_value = owner_record()
    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://test",
    ) as client:
        response = await client.get("/owners/chat/999")

    assert response.status_code == 404
    service.get_owner_by_id.assert_awaited_once_with(owner_id=17)
    service.get_owner_by_chat_id.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [{"trial_used": False}, {"registration_status": "approved"}],
)
async def test_owner_profile_update_cannot_change_administrative_fields(
    owner_application: tuple[FastAPI, MagicMock],
    body: dict[str, Any],
) -> None:
    """Self-service cannot grant approval or reset trial entitlement."""
    application, service = owner_application
    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://test",
    ) as client:
        response = await client.patch("/owners/17", json=body)

    assert response.status_code == 403
    service.update_owner.assert_not_awaited()


# ==============================================
# ADMINISTRATIVE PERMISSIONS
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("GET", "/owners/", None),
        ("GET", "/owners/stats", None),
        ("GET", "/owners/search?query=Owner", None),
        ("GET", "/owners/status/approved", None),
        (
            "POST",
            "/owners/",
            {
                "chat_id": 425,
                "full_name": "Owner Example",
                "registration_status": "approved",
            },
        ),
        ("PATCH", "/owners/17/status", {"registration_status": "approved"}),
        ("POST", "/owners/17/approve", None),
        ("POST", "/owners/17/reject", None),
    ],
    ids=[
        "list",
        "statistics",
        "search",
        "status-list",
        "create",
        "status",
        "approve",
        "reject",
    ],
)
async def test_owner_administration_is_disabled_without_configured_keycloak(
    owner_application: tuple[FastAPI, MagicMock],
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
    body: dict[str, Any] | None,
) -> None:
    """Absent Keycloak disables administration before any identity or billing lookup."""
    application, service = owner_application
    for setting_name in ("OIDC_ISSUER", "OIDC_AUDIENCE", "OIDC_JWKS_URL"):
        monkeypatch.setattr(auth.settings, setting_name, None)
    session = AsyncMock(spec=AsyncSession)

    async def unused_session() -> AsyncIterator[AsyncSession]:
        """Expose a typed session spy without opening any database connection."""
        yield cast(AsyncSession, session)

    application.dependency_overrides[get_db] = unused_session
    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://test",
    ) as client:
        response = await client.request(method, path, json=body)

    assert response.status_code == 503
    assert (
        response.json()["detail"] == "Trusted Keycloak authentication is not configured"
    )
    session.execute.assert_not_awaited()
    session.flush.assert_not_awaited()
    session.commit.assert_not_awaited()
    assert service.mock_calls == []


@pytest.mark.asyncio
async def test_statistics_route_returns_real_trial_counts_before_id_matching(
    owner_application: tuple[FastAPI, MagicMock],
) -> None:
    """The static /stats route is reachable and exposes persisted trial counters."""
    application, service = owner_application
    authorize_administrator(application=application)
    statistics = {
        "total": 4,
        "pending": 1,
        "approved": 2,
        "rejected": 1,
        "trial_used": 1,
        "trial_available": 3,
    }
    service.get_owner_statistics.return_value = statistics
    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://test",
    ) as client:
        response = await client.get("/owners/stats")

    assert response.status_code == 200
    assert response.json() == statistics
    service.get_owner_statistics.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_search_route_precedes_the_dynamic_owner_id_route(
    owner_application: tuple[FastAPI, MagicMock],
) -> None:
    """The static search route does not parse 'search' as an integer owner ID."""
    application, service = owner_application
    authorize_administrator(application=application)
    service.search_owners.return_value = []
    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://test",
    ) as client:
        response = await client.get("/owners/search?query=Owner")

    assert response.status_code == 200
    service.search_owners.assert_awaited_once_with(query="Owner", skip=0, limit=100)


@pytest.mark.asyncio
async def test_invalid_registration_filter_keeps_the_http_status_module(
    owner_application: tuple[FastAPI, MagicMock],
) -> None:
    """A filter called status cannot shadow the HTTP response status constants."""
    application, service = owner_application
    authorize_administrator(application=application)
    service.get_owners_by_status.side_effect = ValidationError(message="Invalid status")
    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://test",
    ) as client:
        response = await client.get("/owners/status/unknown")

    assert response.status_code == 400
