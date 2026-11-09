# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# ISOLATED SIGNED LOCAL DINING APPLICATION
# Use ephemeral RSA identities and real tenant/database checks only on an attested local target.
# ==============================================

"""Rehearsal identity issuance is simulated; JWT verification and D1 persistence are real."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND EXPLICIT LOCAL CONTRACTS
# Reuse typed module dependencies without creating a connection or enabling a transport.
# ==============================================

import secrets
import time
from collections.abc import (
    AsyncIterator,
    Awaitable,
    Callable,
)
from dataclasses import (
    dataclass,
    field,
)
from datetime import datetime
from typing import Annotated

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import (
    FastAPI,
    Header,
    HTTPException,
    Request,
    Response,
)
from fastapi.responses import JSONResponse
from pydantic import (
    BaseModel,
    ConfigDict,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dining import dining_router
from app.core.security.oidc import OIDCPrincipal
from app.core.security.tenant_types import TenantAccessDenied
from app.models.branch import Branch
from app.models.restaurant import Restaurant
from app.models.tenant.schema import restaurant_reference
from app.services.business.dining.service import DiningService
from app.services.business.dining.values import DiningError
from test_support.local_postgres import (
    LocalPostgresSettings,
    read_local_test_identity,
)
from tests.dining.support import DiningGraph

LOCAL_FRONTEND = "http://127.0.0.1:5574"
LOCAL_BACKEND = "http://127.0.0.1:5581"
ISSUER = "https://dining.example.invalid/realms/synthetic"
AUDIENCE = "moulai-dining-local"


# ==============================================
# LOCALIDENTITYISSUER
# Keep a per-run private key in RAM; it is never written, printed or sent to clients.
# ==============================================


@dataclass(kw_only=True)
class LocalIdentityIssuer:
    """Keep a per-run private key in RAM; it is never written, printed or sent to clients."""

    principals: dict[str, OIDCPrincipal]
    _key: rsa.RSAPrivateKey = field(
        default_factory=lambda: rsa.generate_private_key(
            public_exponent=65537, key_size=2048
        ),
        repr=False,
    )

    # ==============================================
    # ISSUE
    # Mint only a known fictional identity, with bounded actual wall-clock expiry.
    # ==============================================

    def issue(
        self,
        *,
        actor: str,
        audience: str = AUDIENCE,
        restaurant_id: int | None = None,
        branch_id: int | None = None,
        expired: bool = False,
    ) -> str:
        """Mint only a known fictional identity, with bounded actual wall-clock expiry."""
        principal = self.principals[actor]
        now = int(time.time())
        claims = {
            "iss": ISSUER,
            "sub": principal.subject,
            "aud": audience,
            "iat": now - 120 if expired else now,
            "nbf": now - 120 if expired else now,
            "exp": now - 60 if expired else now + 3600,
            "jti": secrets.token_hex(16),
        }
        if restaurant_id is not None:
            claims["restaurant_id"] = restaurant_id
        if branch_id is not None:
            claims["branch_id"] = branch_id
        return jwt.encode(
            claims,
            self._key,
            algorithm="RS256",
            headers={"kid": "ephemeral-local-dining", "typ": "JWT"},
        )

    # ==============================================
    # VERIFY
    # Verify signature, algorithm, exact issuer/audience, lifetime and known subject.
    # ==============================================

    def verify(
        self,
        *,
        token: str,
        audience: str = AUDIENCE,
        restaurant_id: int | None = None,
        branch_id: int | None = None,
    ) -> OIDCPrincipal:
        """Verify signature, algorithm, exact issuer/audience, lifetime and known subject."""
        try:
            if len(token) > 12000:
                raise ValueError("bounded")
            header = jwt.get_unverified_header(token)
            if (
                header.get("alg") != "RS256"
                or header.get("kid") != "ephemeral-local-dining"
                or header.get("typ") != "JWT"
            ):
                raise ValueError("header")
            claims = jwt.decode(
                token,
                self._key.public_key(),
                algorithms=["RS256"],
                audience=audience,
                issuer=ISSUER,
                options={"require": ["iss", "sub", "aud", "exp", "iat", "nbf", "jti"]},
            )
            if (
                restaurant_id is not None
                and claims.get("restaurant_id") != restaurant_id
            ):
                raise ValueError("scope")
            if branch_id is not None and claims.get("branch_id") != branch_id:
                raise ValueError("scope")
            matches = [
                principal
                for principal in self.principals.values()
                if principal.subject == claims["sub"]
                and principal.issuer == claims["iss"]
            ]
            if len(matches) != 1:
                raise ValueError("subject")
        except (jwt.InvalidTokenError, ValueError, TypeError, KeyError) as error:
            raise HTTPException(
                status_code=401, detail="Invalid local rehearsal credential"
            ) from error
        # Realm-role claims are intentionally irrelevant to stored E1/module authority.
        return OIDCPrincipal(
            subject=matches[0].subject,
            issuer=matches[0].issuer,
            realm_roles=frozenset(),
        )


# ==============================================
# LOGININPUT
# Select an explicitly simulated local identity; never accept caller role claims.
# ==============================================


class LoginInput(BaseModel):
    """Select an explicitly simulated local identity; never accept caller role claims."""

    model_config = ConfigDict(extra="forbid")
    actor: str


# ==============================================
# CREATE LOCAL DINING APP
# Refuse non-attested targets before making the opt-in router accessible.
# ==============================================


async def create_local_dining_app(
    *,
    configuration: LocalPostgresSettings,
    graph: DiningGraph,
    clock: Callable[[], datetime] | None = None,
) -> tuple[FastAPI, LocalIdentityIssuer]:
    """Refuse non-attested targets before making the opt-in router accessible."""
    async with graph.factory() as session:
        connection = await session.connection()
        await connection.run_sync(
            lambda sync: read_local_test_identity(sync, configuration=configuration)
        )
    business_clock = clock or graph.clock
    actors = (
        "owner",
        "service",
        "cleaner",
        "collector",
        "finance",
        "finance_reader",
        "kitchen",
        "assistant",
        "outsider",
        "service_cleaner",
        "canceller",
        "customer",
        "new_employee",
    )
    issuer = LocalIdentityIssuer(
        principals={actor: graph.principal(actor=actor) for actor in actors}
    )
    cookie_name = "moulai_d1_" + configuration.INSTANCE_ID[:12]
    app = FastAPI(
        title="MoulAI — local disposable D1 rehearsal",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    # ==============================================
    # LOCAL BOUNDARY
    # Refuse foreign hosts, peers and write origins before a business dependency.
    # ==============================================

    @app.middleware("http")
    async def local_boundary(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Refuse foreign hosts, peers and write origins before a business dependency."""
        if (
            request.client is None
            or request.client.host != "127.0.0.1"
            or request.headers.get("host") not in {"127.0.0.1:5581", "127.0.0.1:5574"}
        ):
            return JSONResponse({"detail": "Local rehearsal only"}, status_code=403)
        origin = request.headers.get("origin")
        if (origin is not None and origin not in {LOCAL_FRONTEND, LOCAL_BACKEND}) or (
            request.method not in {"GET", "HEAD", "OPTIONS"}
            and origin not in {LOCAL_FRONTEND, LOCAL_BACKEND}
        ):
            return JSONResponse({"detail": "Origin refused"}, status_code=403)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    # ==============================================
    # SESSIONS
    # Give each request an independent clean local session, with no ambient fixture.
    # ==============================================

    async def sessions() -> AsyncIterator[AsyncSession]:
        """Give each request an independent clean local session, with no ambient fixture."""
        async with graph.factory() as session:
            yield session

    # ==============================================
    # PRINCIPAL
    # Every route invocation verifies the current signed cookie afresh.
    # ==============================================

    async def principal(request: Request) -> OIDCPrincipal:
        """Every route invocation verifies the current signed cookie afresh."""
        token = request.cookies.get(cookie_name)
        if token is None:
            raise HTTPException(status_code=401, detail="Local sign-in required")
        return issuer.verify(token=token)

    # ==============================================
    # CUSTOMER PROOF
    # A staff request needs a separately signed scope-bound fictional customer proof.
    # ==============================================

    async def customer_proof(
        *,
        restaurant_id: int,
        branch_id: int,
        proof: Annotated[str | None, Header(alias="X-Customer-Proof")] = None,
    ) -> OIDCPrincipal | None:
        """A staff request needs a separately signed scope-bound fictional customer proof."""
        if proof is None:
            return None
        customer = issuer.verify(
            token=proof,
            audience="moulai-dining-customer",
            restaurant_id=restaurant_id,
            branch_id=branch_id,
        )
        if customer.subject != issuer.principals["customer"].subject:
            raise HTTPException(status_code=401, detail="Customer proof required")
        return customer

    router = dining_router(
        session_dependency=sessions,
        principal_dependency=principal,
        customer_dependency=customer_proof,
        clock=business_clock,
        verification_origin=LOCAL_FRONTEND,
    )
    app.include_router(router, prefix="/local-d1")
    for route in router.routes:
        if getattr(route, "path", None) in {
            "/verify-reservation",
            "/dining/verify-reservation",
        }:
            app.router.routes.append(route)

    # ==============================================
    # LOGIN
    # Issue a local-only signed session; this is not a production login provider.
    # ==============================================

    @app.post("/local-d1/session")
    async def login(data: LoginInput, response: Response) -> dict[str, str]:
        """Issue a local-only signed session; this is not a production login provider."""
        if data.actor not in issuer.principals:
            raise HTTPException(status_code=401, detail="Unknown rehearsal actor")
        response.set_cookie(
            cookie_name,
            issuer.issue(actor=data.actor),
            httponly=True,
            samesite="strict",
            secure=False,
            max_age=3600,
            path="/local-d1",
        )
        return {"identity_provider": "simulated-local-rs256", "actor": data.actor}

    # ==============================================
    # LOGOUT
    # Invalidate only this run's local browser cookie.
    # ==============================================

    @app.delete("/local-d1/session")
    async def logout(response: Response) -> dict[str, str]:
        """Invalidate only this run's local browser cookie."""
        response.delete_cookie(cookie_name, path="/local-d1")
        return {"status": "signed_out"}

    # ==============================================
    # SESSION VIEW
    # Return real admitted fixture scopes; cookies/keys are never returned.
    # ==============================================

    @app.get("/local-d1/session")
    async def session_view(request: Request) -> dict[str, object]:
        """Return real admitted fixture scopes; cookies/keys are never returned."""
        person = await principal(request)
        actor = next(
            name
            for name, value in issuer.principals.items()
            if value.subject == person.subject
        )
        candidates = [
            (graph.base + 10, graph.base + 200, graph.base + 300),
            (graph.base + 10, graph.base + 200, graph.base + 301),
            (graph.base + 11, graph.base + 201, graph.base + 302),
        ]
        scopes = []
        for company, restaurant, branch in candidates:
            if actor == "customer":
                if branch == graph.base + 300:
                    scopes.append(
                        {
                            "organization_id": company,
                            "restaurant_id": restaurant,
                            "branch_id": branch,
                            "role": "customer",
                        }
                    )
                continue
            try:
                async with graph.factory() as session, DiningService(
                    session=session, clock=business_clock
                ).authorized(
                    principal=person,
                    organization_id=company,
                    restaurant_id=restaurant,
                    branch_id=branch,
                ) as unit:
                    await unit.guard(capability="read")
                    scopes.append(
                        {
                            "organization_id": company,
                            "restaurant_id": restaurant,
                            "branch_id": branch,
                            "role": unit.context.role_code,
                        }
                    )
            except (TenantAccessDenied, DiningError):
                continue
        # ==============================================
        # ADMITTED CONTEXT LABELS
        # Resolve names only for scopes already admitted above, retaining every tenant predicate.
        # ==============================================

        async with graph.factory() as session:
            for scope in scopes:
                names = (
                    await session.execute(
                        select(Restaurant.name, Branch.name)
                        .select_from(Restaurant)
                        .join(Branch, Branch.restaurant_id == Restaurant.id)
                        .where(
                            Restaurant.id.in_(
                                select(restaurant_reference.c.id).where(
                                    restaurant_reference.c.organization_id
                                    == scope["organization_id"]
                                )
                            ),
                            Restaurant.id == scope["restaurant_id"],
                            Branch.id == scope["branch_id"],
                        )
                    )
                ).one()
                scope["restaurant_name"] = names[0]
                scope["branch_name"] = names[1]
        proofs = {
            str(scope["branch_id"]): issuer.issue(
                actor="customer",
                audience="moulai-dining-customer",
                restaurant_id=int(scope["restaurant_id"]),
                branch_id=int(scope["branch_id"]),
            )
            for scope in scopes
            if actor != "customer"
        }
        return {
            "actor": actor,
            "identity_provider": "simulated-local-rs256",
            "persistence": "real-disposable-postgres",
            "scopes": scopes,
            "customer_proofs": proofs,
        }

    # ==============================================
    # HEALTH
    # Bounded readiness only; no background job or external connection starts.
    # ==============================================

    @app.get("/local-d1/health")
    async def health() -> dict[str, str]:
        """Bounded readiness only; no background job or external connection starts."""
        return {"status": "local-d1-ready", "persistence": "real-disposable-postgres"}

    return app, issuer
