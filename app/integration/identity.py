# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# LOCAL KEYCLOAK AUTHORIZATION CODE CLIENT
# Reuse strict JWT validation while keeping code verifiers and tokens on the server.
# ==============================================

"""No role selector, password grant for users, token storage in JavaScript or remote issuer."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Limit provider traffic to the configured TLS loopback origin, without environment proxies.
# ==============================================

import asyncio
import hashlib
import secrets
import ssl
import time
from base64 import urlsafe_b64encode
from dataclasses import (
    dataclass,
    field,
)
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.api import auth
from app.core.logger import logger
from app.core.security.oidc import (
    OIDCPrincipal,
    extract_realm_roles,
)
from app.integration.config import IntegrationConfig
from app.integration.sessions import BrowserSessions

# ==============================================
# LOGINATTEMPT
# Bind one expiring OAuth request to one browser cookie and PKCE verifier.
# ==============================================


@dataclass(frozen=True, kw_only=True)
class LoginAttempt:
    """Bind one expiring OAuth request to one browser cookie and PKCE verifier."""

    cookie: str
    nonce: str
    verifier: str
    expires: float


# ==============================================
# BROWSERIDENTITY
# Carry verifier-issued identity; realm roles never grant local tenant authority.
# ==============================================


@dataclass(frozen=True, kw_only=True)
class BrowserIdentity:
    """Carry verifier-issued identity; realm roles never grant local tenant authority."""

    principal: OIDCPrincipal
    name: str
    access_token: str = field(repr=False)
    expires_at: int = 0


# ==============================================
# KEYCLOAKBROWSERCLIENT
# Perform only the pinned local provider exchanges needed for browser authentication.
# ==============================================


class KeycloakBrowserClient:
    """Perform only the pinned local provider exchanges needed for browser authentication."""

    # ==============================================
    # INIT
    # Install exact HTTPS trust and no redirect/retry behavior for provider requests.
    # ==============================================

    def __init__(
        self, *, configuration: IntegrationConfig, sessions: BrowserSessions
    ) -> None:
        """Install exact HTTPS trust and no redirect/retry behavior for provider requests."""
        self.configuration = configuration
        self.sessions = sessions
        self.pending: dict[str, LoginAttempt] = {}
        self.http = httpx.AsyncClient(
            verify=ssl.create_default_context(cafile=str(configuration.ca_file)),
            trust_env=False,
            timeout=8,
            follow_redirects=False,
        )
        self.endpoint = configuration.issuer + "/protocol/openid-connect"

    # ==============================================
    # BEGIN
    # Issue a one-use state/nonce/verifier without accepting an arbitrary return URL.
    # ==============================================

    def begin(self, *, registration: bool = False) -> tuple[str, str]:
        """Issue a one-use state/nonce/verifier without accepting an arbitrary return URL."""
        now = time.monotonic()
        self.pending = {
            key: value for key, value in self.pending.items() if value.expires > now
        }
        if len(self.pending) >= 100:
            raise HTTPException(status_code=429, detail="Too many login attempts")
        state, cookie, nonce, verifier = (secrets.token_urlsafe(32) for _ in range(4))
        self.pending[state] = LoginAttempt(
            cookie=cookie, nonce=nonce, verifier=verifier, expires=now + 300
        )
        query = urlencode(
            {
                "client_id": self.configuration.client_id,
                "redirect_uri": self.configuration.origin + "/api/web/auth/callback",
                "response_type": "code",
                "scope": "openid profile",
                "state": state,
                "nonce": nonce,
                "code_challenge": urlsafe_b64encode(
                    hashlib.sha256(verifier.encode()).digest()
                )
                .rstrip(b"=")
                .decode(),
                "code_challenge_method": "S256",
            }
        )
        return (
            self.endpoint + ("/registrations?" if registration else "/auth?") + query,
            cookie,
        )

    # ==============================================
    # FINISH
    # Consume matching browser state, verify both tokens and persist only after validation.
    # ==============================================

    async def finish(self, *, state: str, cookie: str, code: str) -> tuple[str, int]:
        """Consume matching browser state, verify both tokens and persist only after validation."""
        attempt = self.pending.pop(state, None)
        if (
            not attempt
            or attempt.expires <= time.monotonic()
            or not secrets.compare_digest(attempt.cookie, cookie)
        ):
            raise HTTPException(
                status_code=401, detail="Invalid or expired login attempt"
            )
        try:
            response = await self.http.post(
                self.endpoint + "/token",
                data={
                    "grant_type": "authorization_code",
                    "client_id": self.configuration.client_id,
                    "client_secret": self.configuration.client_secret,
                    "redirect_uri": self.configuration.origin
                    + "/api/web/auth/callback",
                    "code": code,
                    "code_verifier": attempt.verifier,
                },
            )
            response.raise_for_status()
            tokens = response.json()
            access = tokens["access_token"]
            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer", credentials=access
            )
            claims = await auth._verified_access_token_claims(credentials=credentials)
            signing = await asyncio.to_thread(
                auth._get_jwks_client(
                    self.endpoint + "/certs"
                ).get_signing_key_from_jwt,
                tokens["id_token"],
            )
            identity = jwt.decode(
                tokens["id_token"],
                signing.key,
                algorithms=["RS256"],
                issuer=self.configuration.issuer,
                audience=self.configuration.client_id,
                options={"require": ["exp", "iat", "sub", "iss", "aud", "nonce"]},
            )
            if (
                identity.get("nonce") != attempt.nonce
                or identity.get("sub") != claims["sub"]
                or identity.get("azp", self.configuration.client_id)
                != self.configuration.client_id
            ):
                raise ValueError("identity_token_binding_invalid")
            expires = int(claims["exp"])
            identifier = await self.sessions.create(
                tokens={
                    "access_token": access,
                    "refresh_token": tokens.get("refresh_token", ""),
                },
                expires=expires,
            )
            logger.info(
                "Local browser session established",
                extra={
                    "event": "local_oidc_login_committed",
                    "provider": "keycloak-local",
                },
            )
            return identifier, max(0, expires - int(time.time()))
        except (
            httpx.HTTPError,
            jwt.PyJWTError,
            ValueError,
            KeyError,
            TypeError,
        ) as error:
            logger.warning(
                "Local identity exchange refused",
                extra={
                    "event": "local_oidc_exchange_refused",
                    "category": type(error).__name__,
                },
            )
            raise HTTPException(
                status_code=401, detail="Local identity exchange refused"
            ) from error

    # ==============================================
    # IDENTITY
    # Verify current JWT and provider session on every protected HTTP request.
    # ==============================================

    async def identity(self, *, identifier: str) -> BrowserIdentity:
        """Verify current JWT and provider session on every protected HTTP request."""
        stored = await self.sessions.read(identifier=identifier)
        if not stored or not isinstance(stored.get("access_token"), str):
            raise HTTPException(status_code=401, detail="Session expired")
        token = str(stored["access_token"])
        claims = await auth._verified_access_token_claims(
            credentials=HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        )
        try:
            response = await self.http.post(
                self.endpoint + "/token/introspect",
                data={
                    "client_id": self.configuration.client_id,
                    "client_secret": self.configuration.client_secret,
                    "token": token,
                },
            )
            response.raise_for_status()
            active = response.json()
            if active.get("active") is not True or active.get("sub") != claims["sub"]:
                raise HTTPException(status_code=401, detail="Provider session inactive")
        except httpx.HTTPError as error:
            raise HTTPException(
                status_code=503, detail="Local identity provider unavailable"
            ) from error
        return BrowserIdentity(
            principal=OIDCPrincipal(
                issuer=claims["iss"],
                subject=claims["sub"],
                realm_roles=extract_realm_roles(claims=claims),
            ),
            name=str(
                claims.get("name")
                or claims.get("preferred_username")
                or "Authenticated account"
            )[:255],
            access_token=token,
            expires_at=int(claims["exp"]),
        )

    # ==============================================
    # LOGOUT
    # Always invalidate the local session, then revoke the actual local Keycloak session.
    # ==============================================

    async def logout(self, *, identifier: str) -> None:
        """Always invalidate the local session, then revoke the actual local Keycloak session."""
        stored = await self.sessions.read(identifier=identifier)
        await self.sessions.delete(identifier=identifier)
        logger.info(
            "Local browser session invalidated",
            extra={"event": "local_browser_logout_committed"},
        )
        if stored and stored.get("refresh_token"):
            try:
                response = await self.http.post(
                    self.endpoint + "/logout",
                    data={
                        "client_id": self.configuration.client_id,
                        "client_secret": self.configuration.client_secret,
                        "refresh_token": str(stored["refresh_token"]),
                    },
                )
                response.raise_for_status()
            except httpx.HTTPError as error:
                raise HTTPException(
                    status_code=503,
                    detail="Local logout completed; provider logout unavailable",
                ) from error
