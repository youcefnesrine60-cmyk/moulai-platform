# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Disposable HTTP integration with signed JWTs, mocked JWKS and local SQL."""

import ast
from collections.abc import AsyncIterator
from datetime import (
    datetime,
    timezone,
)
from pathlib import Path
from types import SimpleNamespace
from typing import (
    Annotated,
    Any,
)
from unittest.mock import MagicMock

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import (
    Depends,
    FastAPI,
    Query,
)
from httpx import (
    ASGITransport,
    AsyncClient,
)
from sqlalchemy import (
    Engine,
    delete,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import auth
from app.api.tenant_dependencies import tenant_read_access
from app.core.database import get_db
from app.core.security.tenant_scope import bind_owner_scope
from app.models.tenant.schema import (
    MembershipRestaurantGrant,
    TenantRolePermission,
)
from app.services.business.tenant_access import TenantReadUnit
from tests.test_tenant_access import read_engine
from tests.test_tenant_foundation import (
    ISSUER,
    MemoryAsyncSession,
    local_engine,
)

__all__ = ["local_engine", "read_engine"]


# ==============================================
# MEMORY-ONLY KEYS AND MOCKED JWKS
# ==============================================


@pytest.fixture(scope="module")
def rsa_keys() -> tuple[rsa.RSAPrivateKey, rsa.RSAPrivateKey]:
    """Create real signing keys in memory, never a live Keycloak session."""
    return (
        rsa.generate_private_key(public_exponent=65537, key_size=2048),
        rsa.generate_private_key(public_exponent=65537, key_size=2048),
    )


@pytest.fixture
def jwks(
    monkeypatch: pytest.MonkeyPatch,
    rsa_keys: tuple[rsa.RSAPrivateKey, rsa.RSAPrivateKey],
) -> MagicMock:
    """Keep diagnostics disabled and reuse the actual strict JWT validator."""
    for name, value in {
        "OIDC_ISSUER": ISSUER,
        "OIDC_AUDIENCE": "moulai-api",
        "OIDC_JWKS_URL": ISSUER + "/protocol/openid-connect/certs",
    }.items():
        monkeypatch.setattr(auth.settings, name, value)
    assert not auth.settings.OIDC_DIAGNOSTICS_ENABLED
    assert not auth.settings.OIDC_ALLOW_LOCAL_HTTP
    provider = MagicMock()
    provider.get_signing_key_from_jwt.return_value = SimpleNamespace(
        key=rsa_keys[0].public_key()
    )
    monkeypatch.setattr(auth, "_get_jwks_client", MagicMock(return_value=provider))
    return provider


# ==============================================
# SYNTHETIC ACCESS TOKEN IN MEMORY ONLY
# ==============================================


def token(
    *,
    rsa_keys: tuple[rsa.RSAPrivateKey, rsa.RSAPrivateKey],
    subject: str = "fixture-owner",
    case: str = "valid",
) -> str:
    """Sign an API access token without persisting it or its signing material."""
    now = int(datetime.now(timezone.utc).timestamp())
    claims: dict[str, Any] = {
        "iss": ISSUER,
        "aud": "moulai-api",
        "sub": subject,
        "iat": now,
        "exp": now + 300,
        "typ": "Bearer",
        "realm_access": {"roles": ["owner", "admin"]},
    }
    if case == "expired":
        claims["exp"] = now - 60
    elif case == "issuer":
        claims["iss"] = "https://untrusted.example.test/realm"
    elif case == "audience":
        claims["aud"] = "another-api"
    elif case == "roles":
        claims["realm_access"] = {"roles": "admin"}
    return jwt.encode(
        claims,
        rsa_keys[1] if case == "signature" else rsa_keys[0],
        algorithm="RS256",
        headers={"kid": "offline-key", "typ": "JWT"},
    )


# ==============================================
# DISPOSABLE ROUTES, NEVER REGISTERED IN THE APPLICATION
# ==============================================


@pytest.fixture
def isolated_app(read_engine: Engine) -> FastAPI:
    """Exercise future integration with an isolated app and request-local session."""
    app = FastAPI()
    read = tenant_read_access(permission="tenant.restaurants.read")
    self_read = tenant_read_access(permission="tenant.membership.self.read")

    # ==============================================
    # MEMORY-ONLY REQUEST SESSION
    # ==============================================
    async def session_dependency() -> AsyncIterator[AsyncSession]:
        """Never use the application engine or any environment connection URL."""
        session = MemoryAsyncSession(expire_on_commit=False)
        session.sync_session.bind = read_engine
        try:
            yield session
        finally:
            session.sync_session.close()

    app.dependency_overrides[get_db] = session_dependency

    # ==============================================
    # TEST RESTAURANT LIST
    # ==============================================
    @app.get("/test/organizations/{organization_id}/restaurants")
    async def restaurants(
        unit: Annotated[TenantReadUnit, Depends(read, scope="function")],
        after_id: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
    ) -> Any:
        """Return detached authorized data before transaction cleanup."""
        return await unit.restaurants(after_id=after_id, limit=limit)

    # ==============================================
    # TEST RESTAURANT DETAIL
    # ==============================================
    @app.get("/test/organizations/{organization_id}/restaurants/{restaurant_id}")
    async def restaurant(
        restaurant_id: int,
        unit: Annotated[TenantReadUnit, Depends(read, scope="function")],
    ) -> Any:
        """Use the same generic not-found response for all unavailable IDs."""
        return await unit.restaurant(restaurant_id=restaurant_id)

    # ==============================================
    # TEST MINIMAL PERSONAL MEMBERSHIP
    # ==============================================
    @app.get("/test/organizations/{organization_id}/membership")
    async def membership(
        unit: Annotated[TenantReadUnit, Depends(self_read, scope="function")],
    ) -> Any:
        """Read only personal metadata, independently of restaurant grants."""
        return await unit.membership()

    return app


# ==============================================
# REAL JWT VALIDATION AND HTTP 401
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case", ["absent", "expired", "signature", "issuer", "audience", "roles"]
)
async def test_invalid_access_tokens_are_401(
    isolated_app: FastAPI,
    jwks: MagicMock,
    rsa_keys: tuple[rsa.RSAPrivateKey, rsa.RSAPrivateKey],
    case: str,
) -> None:
    """Only simulated JWKS is replaced; token verification executes unchanged."""
    headers = (
        {}
        if case == "absent"
        else {"Authorization": "Bearer " + token(rsa_keys=rsa_keys, case=case)}
    )
    async with AsyncClient(
        transport=ASGITransport(app=isolated_app), base_url="https://offline.test"
    ) as client:
        response = await client.get(
            "/test/organizations/1/restaurants", headers=headers
        )
    assert (
        response.status_code == 401 and response.headers["www-authenticate"] == "Bearer"
    )
    if case == "absent":
        jwks.get_signing_key_from_jwt.assert_not_called()


# ==============================================
# HTTP 200 AND COMPANY-SELECTION ISOLATION
# ==============================================


@pytest.mark.asyncio
async def test_authenticated_owner_selects_one_company(
    isolated_app: FastAPI,
    jwks: MagicMock,
    rsa_keys: tuple[rsa.RSAPrivateKey, rsa.RSAPrivateKey],
) -> None:
    """The same authenticated owner has distinct results for companies A/B."""
    headers = {"Authorization": "Bearer " + token(rsa_keys=rsa_keys)}
    async with AsyncClient(
        transport=ASGITransport(app=isolated_app), base_url="https://offline.test"
    ) as client:
        for company, expected in ((1, [100, 101]), (2, [200])):
            response = await client.get(
                f"/test/organizations/{company}/restaurants", headers=headers
            )
            assert response.status_code == 200
            assert [row["id"] for row in response.json()] == expected
        page = await client.get(
            "/test/organizations/1/restaurants?after_id=100&limit=1", headers=headers
        )
        assert [row["id"] for row in page.json()] == [101]
        foreign = await client.get(
            "/test/organizations/1/restaurants/200", headers=headers
        )
        absent = await client.get(
            "/test/organizations/1/restaurants/999", headers=headers
        )
    assert (
        foreign.status_code == absent.status_code == 404
        and foreign.json() == absent.json()
    )
    assert "owner_id" not in page.json()[0] and "sub" not in page.json()[0]


# ==============================================
# KEYCLOAK ROLES NEVER SUBSTITUTE LOCAL MEMBERSHIP
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "subject,status", [("owner-test", 403), ("fixture-unlinked", 404)]
)
async def test_role_only_identity_has_no_business_access(
    isolated_app: FastAPI,
    jwks: MagicMock,
    rsa_keys: tuple[rsa.RSAPrivateKey, rsa.RSAPrivateKey],
    subject: str,
    status: int,
) -> None:
    """A valid signature plus owner/admin realm roles creates no association."""
    async with AsyncClient(
        transport=ASGITransport(app=isolated_app), base_url="https://offline.test"
    ) as client:
        response = await client.get(
            "/test/organizations/1/restaurants",
            headers={
                "Authorization": "Bearer " + token(rsa_keys=rsa_keys, subject=subject)
            },
        )
    assert response.status_code == status


# ==============================================
# EXPLICIT EMPTY GRANTS AND MISSING PERMISSION
# ==============================================


@pytest.mark.asyncio
async def test_employee_empty_grants_and_database_policy(
    isolated_app: FastAPI,
    read_engine: Engine,
    jwks: MagicMock,
    rsa_keys: tuple[rsa.RSAPrivateKey, rsa.RSAPrivateKey],
) -> None:
    """Employee realm admin still sees zero restaurants and obeys SQL policy."""
    with read_engine.begin() as connection:
        connection.execute(
            delete(MembershipRestaurantGrant).where(
                MembershipRestaurantGrant.membership_id == 20
            )
        )
    headers = {
        "Authorization": "Bearer "
        + token(rsa_keys=rsa_keys, subject="fixture-employee")
    }
    async with AsyncClient(
        transport=ASGITransport(app=isolated_app), base_url="https://offline.test"
    ) as client:
        response = await client.get(
            "/test/organizations/1/restaurants", headers=headers
        )
        assert response.status_code == 200 and response.json() == []
        own = await client.get("/test/organizations/1/membership", headers=headers)
        assert own.status_code == 200 and own.json()["role"] == "employee"
        with read_engine.begin() as connection:
            connection.execute(
                delete(TenantRolePermission).where(
                    TenantRolePermission.role_code == "employee",
                    TenantRolePermission.permission_code == "tenant.restaurants.read",
                )
            )
        denied = await client.get("/test/organizations/1/restaurants", headers=headers)
    assert denied.status_code == 403 and denied.json() == {
        "detail": "Tenant access denied"
    }


# ==============================================
# BOUNDARY VALIDATION AND DISABLED LOCAL HTTP
# ==============================================


@pytest.mark.asyncio
async def test_business_auth_does_not_enable_local_oidc(
    isolated_app: FastAPI,
    jwks: MagicMock,
    rsa_keys: tuple[rsa.RSAPrivateKey, rsa.RSAPrivateKey],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Business validation rejects localhost HTTP while diagnostics remain false."""
    monkeypatch.setattr(
        auth.settings, "OIDC_ISSUER", "http://localhost:8080/realms/moulai"
    )
    monkeypatch.setattr(
        auth.settings,
        "OIDC_JWKS_URL",
        "http://localhost:8080/realms/moulai/protocol/openid-connect/certs",
    )
    async with AsyncClient(
        transport=ASGITransport(app=isolated_app), base_url="https://offline.test"
    ) as client:
        response = await client.get(
            "/test/organizations/1/restaurants",
            headers={"Authorization": "Bearer " + token(rsa_keys=rsa_keys)},
        )
    assert response.status_code == 503
    jwks.get_signing_key_from_jwt.assert_not_called()


# ==============================================
# PRODUCTION ROUTE REGISTRATION REMAINS UNCHANGED
# ==============================================


def test_new_dependencies_are_not_registered() -> None:
    """The delivery introduces no tenant router or startup import side effect."""
    source = (Path(__file__).resolve().parents[1] / "app/main.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    assert not any(
        isinstance(node, ast.ImportFrom)
        and node.module
        and "tenant_dependencies" in node.module
        for node in ast.walk(tree)
    )
    for name in ("payments.review", "tenant.orders.fulfill"):
        with pytest.raises(ValueError):
            tenant_read_access(permission=name)


# ==============================================
# INVALID SELECTION NEVER DEFAULTS TO A MEMBERSHIP
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("company", ["0", "-1", "not-an-id"])
async def test_invalid_company_selection_is_422(
    isolated_app: FastAPI,
    jwks: MagicMock,
    rsa_keys: tuple[rsa.RSAPrivateKey, rsa.RSAPrivateKey],
    company: str,
) -> None:
    """An authenticated user must explicitly select a positive company ID."""
    async with AsyncClient(
        transport=ASGITransport(app=isolated_app), base_url="https://offline.test"
    ) as client:
        response = await client.get(
            f"/test/organizations/{company}/restaurants",
            headers={"Authorization": "Bearer " + token(rsa_keys=rsa_keys)},
        )
    assert response.status_code == 422


# ==============================================
# UNSAFE DEPENDENCY COMPOSITION FAILS WITH GENERIC HTTP 409
# ==============================================


@pytest.mark.asyncio
async def test_owner_scoped_session_is_rejected_by_dependency(
    isolated_app: FastAPI,
    read_engine: Engine,
    jwks: MagicMock,
    rsa_keys: tuple[rsa.RSAPrivateKey, rsa.RSAPrivateKey],
) -> None:
    """A legacy owner dependency cannot supply the tenant integration's session."""

    # ==============================================
    # SIMULATE A MISWIRED LEGACY REQUEST SESSION
    # ==============================================
    async def owner_session() -> AsyncIterator[AsyncSession]:
        """Bind only a disposable local session to the existing owner guard."""
        session = MemoryAsyncSession(expire_on_commit=False)
        session.sync_session.bind = read_engine
        bind_owner_scope(session=session, owner_id=77)
        try:
            yield session
        finally:
            session.sync_session.close()

    isolated_app.dependency_overrides[get_db] = owner_session
    async with AsyncClient(
        transport=ASGITransport(app=isolated_app), base_url="https://offline.test"
    ) as client:
        response = await client.get(
            "/test/organizations/1/restaurants",
            headers={"Authorization": "Bearer " + token(rsa_keys=rsa_keys)},
        )
    assert response.status_code == 409 and response.json() == {
        "detail": "Tenant operation conflict"
    }
