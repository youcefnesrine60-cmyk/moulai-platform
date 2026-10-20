# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Exercise real JWT/JWKS verification without a live identity provider or DB."""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import (
    datetime,
    timezone,
)
from io import BytesIO
import json
import logging
import os
from pathlib import Path
from ssl import SSLContext
import subprocess
import sys
from types import SimpleNamespace
from typing import (
    Any,
    TypeAlias,
)
from unittest.mock import AsyncMock
from urllib.error import URLError
from urllib.request import Request

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
    Response,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import auth
from app.api.v1.oidc_diagnostics import router
from app.core.config import settings
from app.core.database import get_db
from app.core.security.oidc import OIDCPrincipal

Claims: TypeAlias = dict[str, Any]
LOCAL_ISSUER = "http://localhost:8080/realms/moulai"
LOCAL_JWKS = LOCAL_ISSUER + "/protocol/openid-connect/certs"
AUDIENCE = "moulai-api"
SUBJECT = "unit-test-only-subject"


# ==============================================
# EPHEMERAL SIGNATURES AND SIMULATED JWKS TRANSPORT
# ==============================================


@pytest.fixture(scope="module")
def signing_keys() -> tuple[rsa.RSAPrivateKey, rsa.RSAPrivateKey]:
    """Create independent ephemeral trusted and untrusted RSA private keys."""
    return (
        rsa.generate_private_key(public_exponent=65537, key_size=2048),
        rsa.generate_private_key(public_exponent=65537, key_size=2048),
    )


@dataclass
class OIDCHarness:
    """Use genuine RSA verification with an in-memory JWKS HTTP response."""

    key: rsa.RSAPrivateKey
    other_key: rsa.RSAPrivateKey
    jwks: dict[str, Any]
    requested_urls: list[str]
    app: FastAPI

    def token(
        self,
        *,
        changes: Claims | None = None,
        missing: tuple[str, ...] = (),
        headers: Claims | None = None,
        wrong_signature: bool = False,
    ) -> str:
        """Sign a short-lived fixture token; never contact Keycloak or persist it."""
        now = int(datetime.now(timezone.utc).timestamp())
        claims: Claims = {
            "iss": LOCAL_ISSUER,
            "aud": AUDIENCE,
            "sub": SUBJECT,
            "iat": now - 5,
            "exp": now + 300,
            "typ": "Bearer",
            "realm_access": {"roles": ["owner"]},
        }
        claims.update(changes or {})
        for name in missing:
            claims.pop(name, None)
        return jwt.encode(
            claims,
            self.other_key if wrong_signature else self.key,
            algorithm="RS256",
            headers={"kid": "trusted-fixture-key", **(headers or {})},
        )


@pytest.fixture
def oidc_harness(
    monkeypatch: pytest.MonkeyPatch,
    signing_keys: tuple[rsa.RSAPrivateKey, rsa.RSAPrivateKey],
) -> Iterator[OIDCHarness]:
    """Replace only the JWKS transport; keep key selection and verification real."""
    for name, value in {
        "APP_ENV": "development",
        "DATABASE_TARGET": "development",
        "DEBUG": False,
        "DB_ECHO": False,
        "OIDC_DIAGNOSTICS_ENABLED": True,
        "OIDC_ALLOW_LOCAL_HTTP": True,
        "OIDC_ISSUER": LOCAL_ISSUER,
        "OIDC_AUDIENCE": AUDIENCE,
        "OIDC_JWKS_URL": LOCAL_JWKS,
    }.items():
        monkeypatch.setattr(settings, name, value)
    key, other_key = signing_keys
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()))
    jwk.update({"kid": "trusted-fixture-key", "alg": "RS256", "use": "sig"})
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    async def forbidden_database() -> None:
        """Fail immediately if a diagnostic acquires a database dependency."""
        raise AssertionError("OIDC diagnostics must not acquire a database session")

    app.dependency_overrides[get_db] = forbidden_database
    harness = OIDCHarness(key, other_key, {"keys": [jwk]}, [], app)

    def simulated_jwks(
        request: Request, *, timeout: float, context: SSLContext | None
    ) -> BytesIO:
        """Serve public fixture keys while checking bounded configured transport."""
        assert timeout == 5
        harness.requested_urls.append(request.full_url)
        return BytesIO(json.dumps(harness.jwks).encode("utf-8"))

    monkeypatch.setattr("urllib.request.urlopen", simulated_jwks)
    auth._get_jwks_client.cache_clear()
    try:
        yield harness
    finally:
        auth._get_jwks_client.cache_clear()


async def diagnostic_request(
    *, harness: OIDCHarness, path: str = "me", token: str | None = None
) -> Response:
    """Execute the actual FastAPI dependency graph without application startup."""
    async with AsyncClient(
        transport=ASGITransport(harness.app), base_url="http://127.0.0.1:8000"
    ) as client:
        return await client.get(
            "/api/v1/diagnostics/oidc/" + path,
            headers={"Authorization": "Bearer " + token} if token else {},
        )


# ==============================================
# HTTP 200, 401 AND 403 WITH REAL JWKS KEY SELECTION
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("audience", [AUDIENCE, ["account", AUDIENCE]])
async def test_valid_access_token_returns_minimal_identity(
    oidc_harness: OIDCHarness, audience: str | list[str]
) -> None:
    """A valid signed API audience succeeds without exposing credentials."""
    token = oidc_harness.token(changes={"aud": audience})
    response = await diagnostic_request(harness=oidc_harness, token=token)
    assert response.status_code == 200
    assert response.json() == {
        "authenticated": True,
        "subject": SUBJECT,
        "issuer": LOCAL_ISSUER,
        "realm_roles": ["owner"],
    }
    assert response.headers["cache-control"] == "no-store"
    assert token not in response.text
    assert oidc_harness.requested_urls == [LOCAL_JWKS]


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["me", "owner", "admin"])
async def test_no_credentials_returns_401(oidc_harness: OIDCHarness, path: str) -> None:
    """All probes require a bearer token before JWKS retrieval."""
    response = await diagnostic_request(harness=oidc_harness, path=path)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert not oidc_harness.requested_urls


@pytest.mark.asyncio
async def test_owner_role_is_not_admin_permission(oidc_harness: OIDCHarness) -> None:
    """A realm owner succeeds on the owner probe and is denied on the admin probe."""
    token = oidc_harness.token()
    owner = await diagnostic_request(harness=oidc_harness, path="owner", token=token)
    admin = await diagnostic_request(harness=oidc_harness, path="admin", token=token)
    assert owner.status_code == 200
    assert admin.status_code == 403
    assert token not in admin.text
    assert oidc_harness.requested_urls == [LOCAL_JWKS]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "changes",
    [
        {"exp": 1},
        {"iss": LOCAL_ISSUER + "/"},
        {"iss": "http://localhost:8080/realms/other"},
        {"aud": "account"},
        {"aud": "moulai-local-test"},
        {"sub": ""},
        {"sub": " invalid-subject "},
        {"sub": 12},
        {"typ": "ID"},
        {"typ": "Refresh"},
        {"exp": "9999999999"},
        {"iat": True},
        {"nbf": 9999999999},
    ],
)
async def test_invalid_access_claims_return_401(
    oidc_harness: OIDCHarness, changes: Claims
) -> None:
    """Exact issuer, API audience, temporal bounds and subject are enforced."""
    response = await diagnostic_request(
        harness=oidc_harness, token=oidc_harness.token(changes=changes)
    )
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.asyncio
@pytest.mark.parametrize("claim", ["iss", "aud", "exp", "sub", "iat", "typ"])
async def test_required_claims_cannot_be_omitted(
    oidc_harness: OIDCHarness, claim: str
) -> None:
    """Mandatory Keycloak access-token claims cannot be omitted."""
    response = await diagnostic_request(
        harness=oidc_harness, token=oidc_harness.token(missing=(claim,))
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_wrong_signature_is_rejected(oidc_harness: OIDCHarness) -> None:
    """An attacker's RSA key cannot impersonate the trusted JWKS signing key."""
    response = await diagnostic_request(
        harness=oidc_harness, token=oidc_harness.token(wrong_signature=True)
    )
    assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("token", ["invalid", "a.b.c", "null"])
async def test_malformed_jwt_returns_401(oidc_harness: OIDCHarness, token: str) -> None:
    """Malformed bearer data is denied before key retrieval, without reflection."""
    response = await diagnostic_request(harness=oidc_harness, token=token)
    assert response.status_code == 401
    assert not oidc_harness.requested_urls


@pytest.mark.asyncio
async def test_malformed_provider_jwks_returns_503(
    oidc_harness: OIDCHarness, caplog: pytest.LogCaptureFixture
) -> None:
    """Invalid public provider data fails closed without an unhandled exception."""
    oidc_harness.jwks["keys"] = []
    token = oidc_harness.token()
    response = await diagnostic_request(harness=oidc_harness, token=token)
    assert response.status_code == 503
    assert token not in response.text
    assert token not in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize("headers", [{"kid": "unknown"}, {"typ": []}, {"kid": ""}])
async def test_invalid_key_or_header_is_rejected(
    oidc_harness: OIDCHarness, headers: Claims
) -> None:
    """Unknown key IDs and malformed header types do not produce server errors."""
    response = await diagnostic_request(
        harness=oidc_harness, token=oidc_harness.token(headers=headers)
    )
    assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("algorithm", ["none", "HS256", "PS256"])
async def test_only_rs256_is_allowed(oidc_harness: OIDCHarness, algorithm: str) -> None:
    """A token cannot choose an unsigned, symmetric or different RSA algorithm."""
    key: Any = None
    if algorithm == "HS256":
        key = "ephemeral-unit-test-symmetric-key-over-thirty-two-bytes"
    elif algorithm == "PS256":
        key = oidc_harness.key
    token = jwt.encode(
        {"sub": SUBJECT}, key, algorithm=algorithm, headers={"kid": "fixture"}
    )
    response = await diagnostic_request(harness=oidc_harness, token=token)
    assert response.status_code == 401
    assert not oidc_harness.requested_urls


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "changes",
    [
        {"realm_access": {}},
        {"realm_access": {"roles": []}},
        {"realm_access": {"roles": ["Owner"]}},
        {"realm_access": {}, "roles": ["owner"]},
        {"realm_access": {}, "resource_access": {AUDIENCE: {"roles": ["owner"]}}},
    ],
)
async def test_missing_realm_role_returns_403(
    oidc_harness: OIDCHarness, changes: Claims
) -> None:
    """Only the exact verified realm role satisfies the owner-role dependency."""
    response = await diagnostic_request(
        harness=oidc_harness, path="owner", token=oidc_harness.token(changes=changes)
    )
    assert response.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "realm_access", [None, [], {"roles": "owner"}, {"roles": [1]}, {"roles": [" "]}]
)
async def test_malformed_roles_return_401(
    oidc_harness: OIDCHarness, realm_access: Any
) -> None:
    """Malformed signed role claims cannot crash or broaden the dependency."""
    response = await diagnostic_request(
        harness=oidc_harness,
        token=oidc_harness.token(changes={"realm_access": realm_access}),
    )
    assert response.status_code == 401


# ==============================================
# LOCAL OPT-IN, AVAILABILITY AND BUSINESS BOUNDARIES
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("OIDC_DIAGNOSTICS_ENABLED", False),
        ("APP_ENV", "production"),
        ("APP_ENV", "staging"),
        ("DATABASE_TARGET", "primary"),
        ("DEBUG", True),
        ("DB_ECHO", True),
    ],
)
async def test_diagnostics_fail_closed_outside_local_profile(
    monkeypatch: pytest.MonkeyPatch,
    oidc_harness: OIDCHarness,
    name: str,
    value: Any,
) -> None:
    """Even an already-mounted route refuses an unsafe runtime profile."""
    monkeypatch.setattr(settings, name, value)
    response = await diagnostic_request(
        harness=oidc_harness, token=oidc_harness.token()
    )
    assert response.status_code == 404
    assert not oidc_harness.requested_urls


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    [
        "http://keycloak.example/realms/moulai",
        "http://localhost.evil/realms/moulai",
        "http://user:secret@localhost:8080/realms/moulai",
        "http://localhost:8080/realms/moulai?other=1",
        "http://127.0.0.2:8080/realms/moulai",
    ],
)
async def test_local_http_exception_rejects_untrusted_endpoints(
    monkeypatch: pytest.MonkeyPatch, oidc_harness: OIDCHarness, url: str
) -> None:
    """The local exception cannot authorize arbitrary insecure endpoints."""
    monkeypatch.setattr(settings, "OIDC_ISSUER", url)
    response = await diagnostic_request(
        harness=oidc_harness, token=oidc_harness.token()
    )
    assert response.status_code == 503
    assert not oidc_harness.requested_urls


@pytest.mark.asyncio
async def test_local_exception_does_not_change_business_authentication(
    oidc_harness: OIDCHarness,
) -> None:
    """A diagnostic owner role does not enable HTTP business subject mapping."""
    session = AsyncMock(spec=AsyncSession)
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials=oidc_harness.token()
    )
    for resolver in (auth.get_current_owner, auth.get_current_admin):
        with pytest.raises(HTTPException) as error:
            await resolver(credentials=credentials, session=session)
        assert error.value.status_code == 503
    session.execute.assert_not_awaited()
    session.add.assert_not_called()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_jwks_outage_is_503_without_token_logging(
    monkeypatch: pytest.MonkeyPatch,
    oidc_harness: OIDCHarness,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A transport failure is operational unavailability, with safe diagnostics."""

    def unavailable(*args: Any, **kwargs: Any) -> None:
        """Simulate an unavailable JWKS endpoint before any network request."""
        raise URLError("simulated unavailable provider")

    monkeypatch.setattr("urllib.request.urlopen", unavailable)
    token = oidc_harness.token()
    with caplog.at_level(logging.ERROR):
        response = await diagnostic_request(harness=oidc_harness, token=token)
    assert response.status_code == 503
    assert token not in response.text
    assert token not in caplog.text


@pytest.mark.asyncio
async def test_role_dependency_requires_every_named_role(
    oidc_harness: OIDCHarness,
) -> None:
    """Reusable role checks use an all-of policy on immutable verified roles."""
    dependency = auth.require_realm_roles(roles=frozenset({"owner", "reviewer"}))
    owner = OIDCPrincipal(SUBJECT, LOCAL_ISSUER, frozenset({"owner"}))
    with pytest.raises(HTTPException) as error:
        await dependency(principal=owner)
    assert error.value.status_code == 403
    authorized = OIDCPrincipal(SUBJECT, LOCAL_ISSUER, frozenset({"owner", "reviewer"}))
    assert await dependency(principal=authorized) is authorized


@pytest.mark.asyncio
async def test_absent_realm_roles_keep_authentication_but_deny_owner(
    oidc_harness: OIDCHarness,
) -> None:
    """An identity without realm roles remains authenticated without gaining one."""
    token = oidc_harness.token(missing=("realm_access",))
    identity = await diagnostic_request(harness=oidc_harness, token=token)
    owner = await diagnostic_request(harness=oidc_harness, path="owner", token=token)
    assert identity.status_code == 200
    assert identity.json()["realm_roles"] == []
    assert owner.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("OIDC_ALLOW_LOCAL_HTTP", False),
        ("OIDC_JWKS_URL", LOCAL_JWKS.replace(":8080", ":8081")),
        ("OIDC_JWKS_URL", LOCAL_JWKS.replace("/moulai/", "/other/")),
        ("OIDC_JWKS_URL", "https://localhost:8080/realms/moulai/certs"),
    ],
)
async def test_http_opt_in_and_same_realm_origin_are_required(
    monkeypatch: pytest.MonkeyPatch,
    oidc_harness: OIDCHarness,
    name: str,
    value: Any,
) -> None:
    """The development exception cannot mix providers, schemes, ports or realms."""
    monkeypatch.setattr(settings, name, value)
    response = await diagnostic_request(
        harness=oidc_harness, token=oidc_harness.token()
    )
    assert response.status_code == 503
    assert not oidc_harness.requested_urls


@pytest.mark.asyncio
@pytest.mark.parametrize("resolver", [auth.get_current_owner, auth.get_current_admin])
async def test_realm_roles_do_not_bootstrap_business_mapping(
    monkeypatch: pytest.MonkeyPatch, oidc_harness: OIDCHarness, resolver: Any
) -> None:
    """Even signed owner/admin roles and forged IDs cannot create local mappings."""
    issuer = LOCAL_ISSUER.replace("http://", "https://")
    monkeypatch.setattr(settings, "OIDC_ISSUER", issuer)
    monkeypatch.setattr(settings, "OIDC_JWKS_URL", issuer + "/certs")
    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = SimpleNamespace(scalar_one_or_none=lambda: None)
    token = oidc_harness.token(
        changes={
            "iss": issuer,
            "realm_access": {"roles": ["owner", "admin"]},
            "owner_id": 999,
            "admin_id": 999,
        }
    )
    with pytest.raises(HTTPException) as error:
        await resolver(
            credentials=HTTPAuthorizationCredentials(
                scheme="Bearer", credentials=token
            ),
            session=session,
        )
    assert error.value.status_code == 403
    statement = session.execute.await_args.args[0]
    assert SUBJECT in statement.compile().params.values()
    assert 999 not in statement.compile().params.values()
    session.add.assert_not_called()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_unknown_kid_refreshes_simulated_jwks_for_rotation(
    oidc_harness: OIDCHarness,
) -> None:
    """A newly published signing key is resolved without an indefinite key cache."""
    first = await diagnostic_request(harness=oidc_harness, token=oidc_harness.token())
    assert first.status_code == 200
    new_jwk = json.loads(
        jwt.algorithms.RSAAlgorithm.to_jwk(oidc_harness.other_key.public_key())
    )
    new_jwk.update({"kid": "rotated-key", "alg": "RS256", "use": "sig"})
    oidc_harness.jwks["keys"].append(new_jwk)
    rotated = oidc_harness.token(headers={"kid": "rotated-key"}, wrong_signature=True)
    response = await diagnostic_request(harness=oidc_harness, token=rotated)
    assert response.status_code == 200
    assert oidc_harness.requested_urls == [LOCAL_JWKS, LOCAL_JWKS]


@pytest.mark.asyncio
async def test_untrusted_header_does_not_select_jwks_endpoint(
    oidc_harness: OIDCHarness,
) -> None:
    """A signed jku header never replaces the configured provider JWKS URL."""
    response = await diagnostic_request(
        harness=oidc_harness,
        token=oidc_harness.token(headers={"jku": "https://untrusted.invalid/keys"}),
    )
    assert response.status_code == 200
    assert oidc_harness.requested_urls == [LOCAL_JWKS]


# ==============================================
# REAL APPLICATION REGISTRATION WITHOUT LIFESPAN OR DATABASE IO
# ==============================================


@pytest.mark.parametrize("enabled", [False, True])
def test_actual_app_exposes_only_explicitly_enabled_probes(enabled: bool) -> None:
    """Check real main-app mounting and bearer metadata in isolated processes."""
    code = """
import asyncio, json, sys
from scripts.run_offline_api_tests import OfflineNetworkGuard
guard = OfflineNetworkGuard()
sys.addaudithook(guard)
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.core.database import get_db
async def no_database():
    raise AssertionError('A diagnostic must not use a database')
app.dependency_overrides[get_db] = no_database
paths = app.openapi()['paths']
probes = {path: values['get'].get('security', []) for path, values in paths.items()
          if path.startswith('/api/v1/diagnostics/oidc/')}
async def check():
    async with AsyncClient(transport=ASGITransport(app), base_url='http://127.0.0.1') as client:
        response = await client.get('/api/v1/diagnostics/oidc/me')
    print(json.dumps({'probes': probes, 'status': response.status_code, 'network_denied': dict(guard.denied)}))
asyncio.run(check())
"""
    environment = {
        **os.environ,
        "APP_ENV": "development",
        "DATABASE_TARGET": "development",
        "DEBUG": "false",
        "DB_ECHO": "false",
        "REDIS_URL": "",
        "OIDC_DIAGNOSTICS_ENABLED": str(enabled).lower(),
        "OIDC_ALLOW_LOCAL_HTTP": "true",
    }
    result = subprocess.run(
        [sys.executable, "-W", "error", "-c", code],
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=90,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout.splitlines()[-1])
    assert report["network_denied"] == {}
    if enabled:
        assert report["status"] == 401
        assert len(report["probes"]) == 3
        assert all(value == [{"HTTPBearer": []}] for value in report["probes"].values())
    else:
        assert report["status"] == 404
        assert report["probes"] == {}
