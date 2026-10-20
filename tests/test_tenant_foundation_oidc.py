# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Verify B1 input through the unchanged HTTPS JWT verifier and simulated JWKS."""

from datetime import (
    datetime,
    timezone,
)
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.api import auth
from app.core.security.oidc import OIDCPrincipal

ISSUER = "https://identity.example.test/realms/moulai"


# ==============================================
# KEYS
# ==============================================


@pytest.fixture(scope="module")
def keys() -> tuple[rsa.RSAPrivateKey, rsa.RSAPrivateKey]:
    """Generate memory-only keys; no provider credentials or token files."""
    return tuple(
        rsa.generate_private_key(public_exponent=65537, key_size=2048) for _ in range(2)
    )


# ==============================================
# TEST EXISTING VERIFIER WITH SIMULATED JWKS
# ==============================================


@pytest.mark.parametrize(
    "case", ["valid", "expired", "signature", "issuer", "audience", "subject", "absent"]
)
async def test_existing_verifier_with_simulated_jwks(
    monkeypatch: pytest.MonkeyPatch,
    keys: tuple[rsa.RSAPrivateKey, rsa.RSAPrivateKey],
    case: str,
) -> None:
    """Exercise real RS256 validation without opening sockets or diagnostics."""
    monkeypatch.setattr(auth.settings, "OIDC_ISSUER", ISSUER)
    monkeypatch.setattr(auth.settings, "OIDC_AUDIENCE", "moulai-api")
    monkeypatch.setattr(
        auth.settings, "OIDC_JWKS_URL", ISSUER + "/protocol/openid-connect/certs"
    )
    assert auth.settings.OIDC_DIAGNOSTICS_ENABLED is False
    assert auth.settings.OIDC_ALLOW_LOCAL_HTTP is False
    jwk = jwt.algorithms.RSAAlgorithm.to_jwk(keys[0].public_key(), as_dict=True)
    jwk.update({"kid": "fixture-key", "alg": "RS256", "use": "sig"})

    # ==============================================
    # FETCH DATA
    # ==============================================

    def fetch_data(client: jwt.PyJWKClient) -> dict[str, Any]:
        """Return only the simulated in-memory JWKS without making an HTTP request."""
        return {"keys": [jwk]}

    monkeypatch.setattr(jwt.PyJWKClient, "fetch_data", fetch_data)
    auth._get_jwks_client.cache_clear()
    now = int(datetime.now(timezone.utc).timestamp())
    claims: dict[str, Any] = {
        "iss": ISSUER,
        "sub": "fixture-owner",
        "aud": "moulai-api",
        "iat": now - 120,
        "exp": now + 120,
        "typ": "Bearer",
        "realm_access": {"roles": ["owner"]},
    }
    if case == "expired":
        claims["exp"] = now - 1
    elif case == "issuer":
        claims["iss"] = "https://other.example.test"
    elif case == "audience":
        claims["aud"] = "another-api"
    elif case == "subject":
        claims.pop("sub")
    token = jwt.encode(
        claims,
        keys[1] if case == "signature" else keys[0],
        algorithm="RS256",
        headers={"kid": "fixture-key", "typ": "JWT"},
    )
    credentials = (
        None
        if case == "absent"
        else HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    )
    try:
        if case == "valid":
            verified = await auth._verified_access_token_claims(credentials=credentials)
            principal = OIDCPrincipal(
                subject=verified["sub"],
                issuer=verified["iss"],
                realm_roles=frozenset({"owner"}),
            )
            assert principal.subject == "fixture-owner"
            assert principal.issuer == ISSUER
        else:
            with pytest.raises(HTTPException) as failure:
                await auth._verified_access_token_claims(credentials=credentials)
            assert failure.value.status_code == 401
    finally:
        auth._get_jwks_client.cache_clear()
