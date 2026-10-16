# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Verify trusted Keycloak access tokens before administrative billing access."""

# ==============================================
# IMPORTS
# ==============================================

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import (
    datetime,
    timezone,
)
from types import SimpleNamespace
from typing import (
    Any,
    TypeAlias,
)
from unittest.mock import (
    AsyncMock,
    Mock,
)

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import (
    FastAPI,
    HTTPException,
)
from fastapi.security import HTTPAuthorizationCredentials
from httpx import (
    ASGITransport,
    AsyncClient,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import auth
from app.api.v1.manual_payments import router
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import UnauthorizedError
from app.services.business.admin import admin_service

# ==============================================
# LOCAL SIGNATURE AND DATABASE BOUNDARIES
# ==============================================

Claims: TypeAlias = dict[str, Any]
TEST_ISSUER = "https://keycloak.test/realms/local"
TEST_JWKS = TEST_ISSUER + "/protocol/openid-connect/certs"
TEST_AUDIENCE = "billing-api"
TEST_SUBJECT = "verified-local-admin-subject"


@dataclass
class KeycloakHarness:
    """Use local RSA signatures and a mocked verified-subject database lookup."""

    key: rsa.RSAPrivateKey
    session: AsyncMock
    key_lookup: Mock

    def credentials(
        self,
        *,
        changes: Claims | None = None,
        missing: tuple[str, ...] = (),
        headers: Claims | None = None,
    ) -> HTTPAuthorizationCredentials:
        """Mint test-only access tokens without contacting or configuring a realm."""
        now = int(datetime.now(timezone.utc).timestamp())
        claims: Claims = {
            "iss": TEST_ISSUER,
            "aud": TEST_AUDIENCE,
            "sub": TEST_SUBJECT,
            "iat": now - 1,
            "exp": now + 300,
            "typ": "Bearer",
        }
        claims.update(changes or {})
        for name in missing:
            claims.pop(name, None)
        token = jwt.encode(
            claims,
            self.key,
            algorithm="RS256",
            headers={"kid": "local-key", **(headers or {})},
        )
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


@pytest.fixture
def keycloak_harness(monkeypatch: pytest.MonkeyPatch) -> KeycloakHarness:
    """Keep synthetic identity values confined to this isolated unit fixture."""
    monkeypatch.setattr(settings, "OIDC_ISSUER", TEST_ISSUER)
    monkeypatch.setattr(settings, "OIDC_AUDIENCE", TEST_AUDIENCE)
    monkeypatch.setattr(settings, "OIDC_JWKS_URL", TEST_JWKS)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    lookup = Mock(return_value=SimpleNamespace(key=key.public_key()))
    monkeypatch.setattr(
        auth,
        "_get_jwks_client",
        Mock(return_value=SimpleNamespace(get_signing_key_from_jwt=lookup)),
    )
    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = SimpleNamespace(scalar_one_or_none=lambda: 7)
    return KeycloakHarness(key, session, lookup)


# ==============================================
# MISSING TRUST AND INVALID CONFIGURATION
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "missing", ["all", "OIDC_ISSUER", "OIDC_AUDIENCE", "OIDC_JWKS_URL"]
)
@pytest.mark.parametrize("bearer", [False, True])
async def test_missing_keycloak_configuration_prevents_admin_lookup(
    monkeypatch: pytest.MonkeyPatch,
    keycloak_harness: KeycloakHarness,
    missing: str,
    bearer: bool,
) -> None:
    """An admin ID, chat mapping, or bearer string cannot replace trusted configuration."""
    for name in ("OIDC_ISSUER", "OIDC_AUDIENCE", "OIDC_JWKS_URL"):
        if missing in {"all", name}:
            monkeypatch.setattr(settings, name, None)
    credentials = keycloak_harness.credentials() if bearer else None
    with pytest.raises(HTTPException) as error:
        await auth.get_current_admin(
            credentials=credentials, session=keycloak_harness.session
        )
    assert error.value.status_code == 503
    keycloak_harness.key_lookup.assert_not_called()
    keycloak_harness.session.execute.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "value",
    [
        "http://keycloak.test/realms/local",
        "https:///realms/local",
        "https://user:password@keycloak.test/realms/local",
        "https://keycloak.test/realms/local?realm=other",
        "https://keycloak.test/realms/local#other",
        " https://keycloak.test/realms/local",
        "https://keycloak.test/realms/lo\ncal",
        "https://keycloak.test:bad/realms/local",
        "https://[broken/realms/local",
        "https://keycloak.test/realms/local\\other",
    ],
    ids=[
        "http",
        "missing-host",
        "userinfo",
        "query",
        "fragment",
        "whitespace",
        "control",
        "invalid-port",
        "invalid-host",
        "backslash",
    ],
)
@pytest.mark.parametrize("name", ["OIDC_ISSUER", "OIDC_JWKS_URL"])
async def test_invalid_keycloak_endpoint_fails_closed_before_keys_or_database(
    monkeypatch: pytest.MonkeyPatch,
    keycloak_harness: KeycloakHarness,
    name: str,
    value: str,
) -> None:
    """Reject ambiguous or insecure configured endpoints without normalizing them."""
    monkeypatch.setattr(settings, name, value)
    with pytest.raises(HTTPException) as error:
        await auth.get_current_admin(
            credentials=keycloak_harness.credentials(), session=keycloak_harness.session
        )
    assert error.value.status_code == 503
    keycloak_harness.key_lookup.assert_not_called()
    keycloak_harness.session.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_unconfigured_review_api_returns_503_without_bearer_or_db_access(
    monkeypatch: pytest.MonkeyPatch,
    keycloak_harness: KeycloakHarness,
) -> None:
    """The concrete admin billing endpoint remains closed until real trust is supplied."""
    for name in ("OIDC_ISSUER", "OIDC_AUDIENCE", "OIDC_JWKS_URL"):
        monkeypatch.setattr(settings, name, None)
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    async def session_override() -> AsyncIterator[AsyncSession]:
        """Provide a local database sentinel to detect accidental financial access."""
        yield keycloak_harness.session

    app.dependency_overrides[get_db] = session_override
    async with AsyncClient(
        transport=ASGITransport(app), base_url="https://test"
    ) as client:
        response = await client.post(
            "/api/v1/admin/manual-payments/77/review",
            json={"decision": "reject", "note": "Bank funds not received"},
        )
    assert response.status_code == 503
    keycloak_harness.session.execute.assert_not_awaited()
    keycloak_harness.key_lookup.assert_not_called()


# ==============================================
# SIGNED ACCESS TOKEN SEMANTICS
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("audience", [TEST_AUDIENCE, ["other-api", TEST_AUDIENCE]])
async def test_valid_keycloak_access_token_uses_only_stored_subject_mapping(
    keycloak_harness: KeycloakHarness,
    audience: Any,
) -> None:
    """Token admin/chat/role claims never supply the local administrator ID."""
    credentials = keycloak_harness.credentials(
        changes={
            "aud": audience,
            "admin_id": 999,
            "chat_id": 101,
            "realm_access": {"roles": ["super_admin"]},
        }
    )
    principal = await auth.get_current_admin(
        credentials=credentials, session=keycloak_harness.session
    )
    assert principal == auth.AdminPrincipal(admin_id=7)
    query = keycloak_harness.session.execute.await_args.args[0]
    assert "admins.auth_subject" in str(query) and "admins.is_active" in str(query)
    assert TEST_SUBJECT in query.compile().params.values()
    assert 999 not in query.compile().params.values()


@pytest.mark.asyncio
async def test_privileged_claims_do_not_create_or_link_an_unmapped_administrator(
    keycloak_harness: KeycloakHarness,
) -> None:
    """Signed privileged claims cannot bootstrap identity or role mappings."""
    keycloak_harness.session.execute.return_value = SimpleNamespace(
        scalar_one_or_none=lambda: None
    )
    with pytest.raises(HTTPException) as error:
        await auth.get_current_admin(
            credentials=keycloak_harness.credentials(
                changes={
                    "admin_id": 7,
                    "chat_id": 101,
                    "roles": ["admin", "super_admin"],
                }
            ),
            session=keycloak_harness.session,
        )
    assert error.value.status_code == 403
    keycloak_harness.session.add.assert_not_called()
    keycloak_harness.session.commit.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("missing", ["iss", "aud", "sub", "exp", "iat", "typ"])
async def test_required_keycloak_claims_cannot_be_omitted(
    keycloak_harness: KeycloakHarness,
    missing: str,
) -> None:
    """Incomplete signed JWTs do not reach administrator lookup."""
    with pytest.raises(HTTPException) as error:
        await auth.get_current_admin(
            credentials=keycloak_harness.credentials(missing=(missing,)),
            session=keycloak_harness.session,
        )
    assert error.value.status_code == 401
    keycloak_harness.session.execute.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "changes",
    [
        {"typ": "ID"},
        {"typ": "Refresh"},
        {"typ": "Offline"},
        {"iss": TEST_ISSUER + "/"},
        {"iss": "https://keycloak.test/realms/other"},
        {"aud": "account"},
        {"sub": " "},
        {"sub": " subject-with-spaces "},
        {"iat": True},
        {"iat": "1"},
        {"exp": "9999999999"},
        {"nbf": False},
    ],
    ids=[
        "id-token",
        "refresh-token",
        "offline-token",
        "issuer-slash",
        "wrong-realm",
        "wrong-api",
        "blank-sub",
        "altered-sub",
        "boolean-iat",
        "string-iat",
        "string-exp",
        "boolean-nbf",
    ],
)
async def test_non_access_tokens_and_malformed_claims_are_rejected(
    keycloak_harness: KeycloakHarness,
    changes: Claims,
) -> None:
    """Exact issuer, access-token purpose, and Keycloak numeric dates are mandatory."""
    with pytest.raises(HTTPException) as error:
        await auth.get_current_admin(
            credentials=keycloak_harness.credentials(changes=changes),
            session=keycloak_harness.session,
        )
    assert error.value.status_code == 401
    keycloak_harness.session.execute.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure", ["expired", "future-issued", "future-nbf", "zero-lifetime"]
)
async def test_keycloak_temporal_limits_are_verified(
    keycloak_harness: KeycloakHarness,
    failure: str,
) -> None:
    """Expired, premature, or temporally contradictory tokens cannot review funds."""
    now = int(datetime.now(timezone.utc).timestamp())
    changes: Claims = {}
    if failure == "expired":
        changes = {"iat": now - 100, "exp": now - 1}
    elif failure == "future-issued":
        changes = {"iat": now + 100}
    elif failure == "future-nbf":
        changes = {"nbf": now + 100}
    else:
        changes = {"iat": now - 1, "exp": now - 1}
    with pytest.raises(HTTPException) as error:
        await auth.get_current_admin(
            credentials=keycloak_harness.credentials(changes=changes),
            session=keycloak_harness.session,
        )
    assert error.value.status_code == 401
    keycloak_harness.session.execute.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("algorithm", ["none", "HS256"])
async def test_disallowed_algorithms_fail_before_jwks_lookup(
    keycloak_harness: KeycloakHarness,
    algorithm: str,
) -> None:
    """A header-selected algorithm cannot change the approved RS256 verifier."""
    token = jwt.encode(
        {"sub": TEST_SUBJECT},
        None
        if algorithm == "none"
        else "local-test-symmetric-signing-key-over-32-bytes",
        algorithm=algorithm,
        headers={"kid": "local-key"},
    )
    with pytest.raises(HTTPException) as error:
        await auth.get_current_admin(
            credentials=HTTPAuthorizationCredentials(
                scheme="Bearer", credentials=token
            ),
            session=keycloak_harness.session,
        )
    assert error.value.status_code == 401
    keycloak_harness.key_lookup.assert_not_called()
    keycloak_harness.session.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_verified_identity_still_requires_current_database_rbac(
    monkeypatch: pytest.MonkeyPatch,
    keycloak_harness: KeycloakHarness,
) -> None:
    """Verified access-token identity does not cache or replace a live permission grant."""
    principal = await auth.get_current_admin(
        credentials=keycloak_harness.credentials(), session=keycloak_harness.session
    )
    check = AsyncMock()
    monkeypatch.setattr(
        admin_service,
        "AdminService",
        Mock(return_value=SimpleNamespace(check_admin_permission=check)),
    )
    authorize = auth.require_admin_permission("payments.review")
    assert (
        await authorize(admin=principal, session=keycloak_harness.session) == principal
    )
    check.side_effect = UnauthorizedError(message="Permission revoked")
    with pytest.raises(HTTPException) as error:
        await authorize(admin=principal, session=keycloak_harness.session)
    assert error.value.status_code == 403
    assert check.await_count == 2
    check.assert_awaited_with(admin_id=7, required_permission="payments.review")
