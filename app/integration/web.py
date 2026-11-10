# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# AUTHENTICATED OPERATIONAL HTTP HOST
# Compose existing tenant and dining services behind one opaque browser session.
# ==============================================

"""Validated local/staging factories, without deployed main, fixtures or workers."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Projections below require existing database authority; role names grant nothing.
# ==============================================

import json
import re
import ssl
import time
from collections import (
    defaultdict,
    deque,
)
from collections.abc import (
    AsyncIterator,
    Awaitable,
    Callable,
)
from contextlib import asynccontextmanager
from ipaddress import ip_address
from typing import (
    Annotated,
    TypeAlias,
    TypedDict,
)

from fastapi import (
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Path,
    Request,
    Response,
)
from fastapi.responses import (
    JSONResponse,
    RedirectResponse,
)
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.api import auth
from app.api.dining import dining_router
from app.api.dining_public import PublicReadInput
from app.core.exceptions import AppException
from app.core.security.oidc import OIDCPrincipal
from app.core.security.tenant_types import (
    TenantAccessDenied,
    TenantConflict,
)
from app.integration.config import IntegrationConfig
from app.integration.enrollment_routes import mount_enrollment_routes
from app.integration.identity import (
    BrowserIdentity,
    KeycloakBrowserClient,
)
from app.integration.offers import (
    OfferInput,
    available_offer,
    simulate_offer,
)
from app.integration.queries import base_select
from app.integration.saas_payment_routes import mount_saas_payment_routes
from app.integration.sessions import BrowserSessions
from app.integration.settlements import (
    SettlementInput,
    invoice_balance,
    own_invoice,
    record_settlement,
)
from app.models.admin import Admin
from app.models.branch import Branch
from app.models.dining import DiningInvoice
from app.models.rbac import (
    Permission,
    Role,
    role_permissions,
)
from app.models.tenant.schema import Organization
from app.schemas.saas_pricing import (
    BasePriceCommand,
    CampaignCommand,
    ReminderCommand,
)
from app.services.business.dining.service import DiningService
from app.services.business.dining.values import DiningError
from app.services.business.saas_pricing_admin import (
    BasePriceView,
    CampaignView,
    PricingAuditView,
    SaasPricingAdministration,
)
from app.services.business.tenant_access import TenantAccessService
from app.staging.config import StagingConfig

JsonView: TypeAlias = dict[str, object]

# ==============================================
# RESTAURANTVIEW
# Carry typed authorized projections, never arbitrary cross-tenant dictionaries.
# ==============================================


class RestaurantView(TypedDict):
    """Carry typed authorized projections, never arbitrary cross-tenant dictionaries."""

    id: int
    organizationId: int
    name: dict[str, str]
    city: dict[str, str]
    active: bool


COOKIE = "__Secure-moulai-session"
PENDING = "__Secure-moulai-login"


# ==============================================
# LOCALIZED
# Retain stored business names without manufacturing translations.
# ==============================================


def localized(*, value: str) -> dict[str, str]:
    """Retain stored business names without manufacturing translations."""
    return {language: value for language in ("fr", "en", "ar")}


# ==============================================
# ATTEST DATABASE
# Refuse an unexpected cluster, owner, marker or unapplied main D1d schema.
# ==============================================


async def attest_database(
    *, session: AsyncSession, configuration: IntegrationConfig
) -> None:
    """Refuse an unexpected cluster, owner, marker or unapplied main D1d schema."""
    row = (
        await session.execute(
            text(
                "SELECT current_database(),current_user,inet_server_port(),shobj_description(oid,'pg_database') FROM pg_database WHERE datname=current_database()"
            )
        )
    ).one()
    revision = await session.scalar(
        text("SELECT version_num FROM public.alembic_version")
    )
    if (
        tuple(row)
        != (
            "moulai_integrated",
            "moulai_integrated",
            55433,
            "moulai-operational-local:" + configuration.instance_id,
        )
        or revision != "o420261108"
    ):
        raise RuntimeError("integration_database_identity_or_revision_mismatch")


# ==============================================
# CREATE OPERATIONAL APP
# Mount reviewed business routes only on the explicitly configured local host.
# ==============================================


def compose_browser_app(*, configuration: IntegrationConfig | StagingConfig) -> FastAPI:
    """Reuse business routes with distinct, validated local or staging boundaries."""
    if not isinstance(configuration, (IntegrationConfig, StagingConfig)):
        raise TypeError("validated_browser_configuration_required")
    staging = isinstance(configuration, StagingConfig)
    if (
        auth.settings.OIDC_ISSUER != configuration.issuer
        or auth.settings.DATABASE_URL != configuration.database_url
        or auth.settings.OIDC_ALLOW_LOCAL_HTTP
    ):
        raise RuntimeError("integration_process_settings_not_installed")
    engine = create_async_engine(
        configuration.database_url,
        hide_parameters=True,
        connect_args={
            "ssl": ssl.create_default_context() if staging else False,
            "command_timeout": 30,
        },
    )
    # Preserve the existing business host's explicit-flush transaction contract.
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    store = BrowserSessions(
        path=configuration.directory / "private" / "sessions.sqlite3",
        key=configuration.session_key,
    )
    provider = KeycloakBrowserClient(configuration=configuration, sessions=store)

    # ==============================================
    # LIFESPAN
    # Attest before accepting traffic and close only resources owned by this host.
    # ==============================================

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        """Attest before accepting traffic and close only resources owned by this host."""
        async with factory() as session:
            if isinstance(configuration, StagingConfig):
                await session.run_sync(
                    lambda sync: configuration.target.attest(
                        connection=sync.connection(),
                        migration=False,
                        require_revision=True,
                    )
                )
            else:
                await attest_database(session=session, configuration=configuration)
        try:
            yield
        finally:
            await provider.http.aclose()
            await engine.dispose()

    app = FastAPI(
        title=(
            "MoulAI — isolated staging"
            if staging
            else "MoulAI — local operational integration"
        ),
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.browser_provider = provider
    app.state.browser_engine = engine
    windows: dict[str, deque[float]] = defaultdict(deque)

    # ==============================================
    # LOCAL LAUNCHER READINESS IDENTITY
    # This loopback-only host exposes no account, secret or business data; successful startup has already attested its database.
    # ==============================================

    @app.get("/api/web/local-status")
    async def local_status() -> dict[str, str]:
        """Identify this isolated host so a second launcher cannot mistake another service for the active review."""
        return {
            "service": "moulai-staging" if staging else "moulai-operational-local",
            "instance_id": configuration.instance_id,
            "url": configuration.origin + "/access",
        }

    # ==============================================
    # LOCAL BOUNDARY
    # Reject foreign origins, hosts and excess local requests before any mutation.
    # ==============================================

    @app.middleware("http")
    async def local_boundary(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Reject foreign origins, hosts and excess local requests before any mutation."""
        if staging and request.url.path == "/health" and request.method == "GET":
            return JSONResponse(
                {"status": "ready", "environment": "staging", "syntheticOnly": True}
            )
        if isinstance(configuration, StagingConfig):
            try:
                peer = ip_address(request.client.host) if request.client else None
            except ValueError:
                peer = None
            from urllib.parse import urlsplit

            admitted = (
                peer is not None
                and any(peer in network for network in configuration.proxy_networks)
                and request.headers.get("host") == urlsplit(configuration.origin).netloc
                and request.headers.get("x-forwarded-proto") == "https"
            )
        else:
            admitted = (
                request.client is not None
                and request.client.host == "127.0.0.1"
                and request.headers.get("host") in {"127.0.0.1:5582", "127.0.0.1:5180"}
            )
        if not admitted:
            return JSONResponse({"detail": "Local host required"}, status_code=403)
        origin = request.headers.get("origin")
        if (
            origin is not None
            and origin != configuration.origin
            or request.method not in {"GET", "HEAD", "OPTIONS"}
            and origin != configuration.origin
        ):
            return JSONResponse({"detail": "Origin refused"}, status_code=403)
        now = time.monotonic()
        category = (
            "login"
            if "/auth/" in request.url.path
            else "write" if request.method not in {"GET", "HEAD"} else "read"
        )
        window = windows[category]
        while window and window[0] < now - 60:
            window.popleft()
        if len(window) >= {"login": 60, "write": 120, "read": 1200}[category]:
            return JSONResponse(
                {"detail": "Local request limit reached"}, status_code=429
            )
        window.append(now)
        if (
            staging
            and request.url.path.startswith("/api/web/")
            and not request.url.path.startswith("/api/web/auth/")
            and request.url.path not in {"/api/web/session", "/api/web/local-status"}
        ):
            try:
                request.state.staging_identity = await provider.identity(
                    identifier=request.cookies.get(COOKIE, "")
                )
            except HTTPException as error:
                return JSONResponse(
                    {"detail": "Staging tester session required"},
                    status_code=error.status_code,
                )
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    # ==============================================
    # DENIED
    # Keep unavailable identities and foreign resources outside response details.
    # ==============================================

    @app.exception_handler(TenantAccessDenied)
    async def denied(_request: Request, _error: TenantAccessDenied) -> JSONResponse:
        """Keep unavailable identities and foreign resources outside response details."""
        return JSONResponse({"detail": "Tenant access denied"}, status_code=403)

    # ==============================================
    # CONFLICT
    # Reject incompatible transactions without committing unrelated work.
    # ==============================================

    @app.exception_handler(TenantConflict)
    async def conflict(_request: Request, _error: TenantConflict) -> JSONResponse:
        """Reject incompatible transactions without committing unrelated work."""
        return JSONResponse({"detail": "Tenant operation conflict"}, status_code=409)

    # ==============================================
    # SAFE ENROLLMENT CONFIGURATION FAILURES
    # Expose only closed domain codes; never serialize a SQL statement, private proof or exception payload.
    # ==============================================

    @app.exception_handler(ValueError)
    async def enrollment_conflict(_request: Request, error: ValueError) -> JSONResponse:
        """Return an actionable domain code without leaking arbitrary exception text."""
        value = str(error)
        safe = (
            value
            if re.fullmatch(
                r"(?:enrollment|billing_country|billing_legal_entity|country_base|validated_billing_country|fictitious_enrollment|trial|subscription|mandatory_feature|offer|payment_adjustment)[a-z_]{0,100}",
                value,
            )
            else "operation_requires_review"
        )
        return JSONResponse({"detail": {"code": safe}}, status_code=409)

    # ==============================================
    # EXISTING BUSINESS FAILURE CONTRACT
    # Preserve expected refusal status without returning private payment, SQL or document exception details.
    # ==============================================

    @app.exception_handler(AppException)
    async def business_refusal(_request: Request, error: AppException) -> JSONResponse:
        """Keep domain refusals distinct from server failures and never disclose arbitrary exception messages."""
        status = (
            error.status_code
            if error.status_code in {400, 401, 403, 404, 409, 422, 429}
            else 500
        )
        return JSONResponse(
            {"detail": {"code": "business_operation_refused"}}, status_code=status
        )

    # ==============================================
    # SESSIONS
    # Give each request its own clean session; never share a tenant context.
    # ==============================================

    async def sessions() -> AsyncIterator[AsyncSession]:
        """Give each request its own clean session; never share a tenant context."""
        async with factory() as session:
            yield session

    # ==============================================
    # IDENTITY
    # Accept only an opaque secure cookie issued after a completed OIDC exchange.
    # ==============================================

    async def identity(request: Request) -> BrowserIdentity:
        """Accept only an opaque secure cookie issued after a completed OIDC exchange."""
        admitted = getattr(request.state, "staging_identity", None)
        if isinstance(admitted, BrowserIdentity):
            return admitted
        return await provider.identity(identifier=request.cookies.get(COOKIE, ""))

    identity_dep = Depends(identity)
    session_dep = Depends(sessions)
    mount_enrollment_routes(
        app=app,
        configuration=configuration,
        identity_dep=identity_dep,
        session_dep=session_dep,
    )
    mount_saas_payment_routes(
        app=app, identity_dep=identity_dep, session_dep=session_dep
    )

    # ==============================================
    # EXPLICIT RECOVERABLE ENROLLMENT TEXT
    # Recheck the stored identity and absence of a completed dossier at every access.
    # ==============================================

    @app.api_route("/api/web/enrollment-draft", methods=["GET", "PUT", "DELETE"])
    async def enrollment_draft(
        request: Request,
        person: BrowserIdentity = identity_dep,
        session: AsyncSession = session_dep,
    ) -> JsonView | None:
        """Retain bounded text locally for 30 minutes; never restore an acceptance or submit a command."""
        from pydantic import ValidationError as DraftValidationError

        from app.models.tenant.schema import (
            Identity,
            OrganizationMembership,
        )
        from app.schemas.enrollment import EnrollmentDraftInput
        from app.services.business.enrollment import EnrollmentService

        async with session.begin():
            account = await session.scalar(
                base_select(Identity).where(
                    Identity.issuer == person.principal.issuer,
                    Identity.subject == person.principal.subject,
                    Identity.status == "active",
                )
            )
            if account is None:
                raise HTTPException(status_code=403, detail="Active account required")
            assigned = await session.scalar(
                base_select(OrganizationMembership)
                .with_only_columns(OrganizationMembership.id)
                .where(OrganizationMembership.identity_id == account.id)
                .limit(1)
            )
            if assigned is not None and request.method != "DELETE":
                raise HTTPException(
                    status_code=403, detail="Unassigned account required"
                )
            try:
                dossier = await EnrollmentService(
                    session=session, marker=configuration.instance_id
                ).view(principal=person.principal)
            except TenantAccessDenied as error:
                if str(error) != "enrollment_dossier_unavailable":
                    raise
                # Absence is expected before first submission, not a permission failure.
                dossier = None
            if dossier is not None and request.method != "DELETE":
                raise HTTPException(
                    status_code=409,
                    detail="Dossier already persisted; use its current state",
                )
        owner = json.dumps([person.principal.issuer, person.principal.subject])
        payload = None
        if request.method == "PUT":
            if int(request.headers.get("content-length", "0")) > 4096:
                raise HTTPException(status_code=413, detail="Draft too large")
            content = await request.body()
            if len(content) > 4096:
                raise HTTPException(status_code=413, detail="Draft too large")
            try:
                payload = EnrollmentDraftInput.model_validate_json(
                    content
                ).model_dump_json()
            except DraftValidationError as error:
                raise HTTPException(
                    status_code=422, detail="Invalid enrollment text draft"
                ) from error
        return await store.draft(
            owner=owner, payload=payload, delete=request.method == "DELETE"
        )

    # ==============================================
    # PRINCIPAL
    # Forward a verifier-issued identity, never caller role or owner parameters.
    # ==============================================

    async def principal(person: BrowserIdentity = identity_dep) -> OIDCPrincipal:
        """Forward a verifier-issued identity, never caller role or owner parameters."""
        return person.principal

    # ==============================================
    # LOGIN
    # Redirect to the actual local provider, using state, nonce and PKCE S256.
    # ==============================================

    @app.get("/api/web/auth/register")
    @app.get("/api/web/auth/login")
    async def login(request: Request) -> RedirectResponse:
        """Redirect to the actual local provider, using state, nonce and PKCE S256."""
        if staging and request.url.path.endswith("/register"):
            raise HTTPException(
                status_code=403,
                detail="Staging accounts require explicit tester invitation",
            )
        url, cookie = provider.begin(
            registration=request.url.path.endswith("/register")
        )
        response = RedirectResponse(url, status_code=302)
        response.set_cookie(
            PENDING,
            cookie,
            max_age=300,
            secure=True,
            httponly=True,
            samesite="lax",
            path="/api/web",
        )
        return response

    # ==============================================
    # CALLBACK
    # Complete only this browser's one-use login and redirect to a fixed application path.
    # ==============================================

    @app.get("/api/web/auth/callback")
    async def callback(
        request: Request, state: str = "", code: str = ""
    ) -> RedirectResponse:
        """Complete only this browser's one-use login and redirect to a fixed application path."""
        identifier, lifetime = await provider.finish(
            state=state, cookie=request.cookies.get(PENDING, ""), code=code
        )
        # The account has just passed the same JWT, nonce and provider-session
        # checks as login. Bind only its identity; grant no company or permission.
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        from app.models.tenant.schema import Identity

        person = await provider.identity(identifier=identifier)
        async with factory() as session, session.begin():
            await session.execute(
                pg_insert(Identity)
                .values(
                    issuer=person.principal.issuer,
                    subject=person.principal.subject,
                    status="active",
                    revision=1,
                )
                .on_conflict_do_nothing(
                    index_elements=[Identity.issuer, Identity.subject]
                )
            )
        response = RedirectResponse("/access", status_code=303)
        response.delete_cookie(
            PENDING, secure=True, httponly=True, samesite="lax", path="/api/web"
        )
        response.set_cookie(
            COOKIE,
            identifier,
            max_age=lifetime,
            secure=True,
            httponly=True,
            samesite="lax",
            path="/api/web",
        )
        return response

    # ==============================================
    # LOGOUT
    # Remove local custody and revoke the provider session; never touch business rows.
    # ==============================================

    @app.post("/api/web/auth/logout")
    async def logout(request: Request) -> Response:
        """Remove local custody and revoke the provider session; never touch business rows."""
        try:
            await provider.logout(identifier=request.cookies.get(COOKIE, ""))
            response = Response(status_code=204)
        except HTTPException:
            response = JSONResponse(
                {"detail": "Provider logout unavailable; local session removed"},
                status_code=503,
            )
        response.delete_cookie(
            COOKIE, secure=True, httponly=True, samesite="lax", path="/api/web"
        )
        return response

    # ==============================================
    # CURRENT SESSION
    # Restore a live provider session and classify only an active persisted admin mapping.
    # ==============================================

    @app.get("/api/web/session")
    async def current_session(request: Request) -> JsonView | None:
        """Restore a live provider session and classify only an active persisted admin mapping."""
        if not request.cookies.get(COOKIE):
            return None
        try:
            person = await identity(request)
        except HTTPException as error:
            if error.status_code == 401:
                return None
            raise
        async with factory() as session:
            admin = (
                await session.execute(
                    base_select(Admin)
                    .with_only_columns(Admin.id)
                    .where(
                        Admin.auth_subject == person.principal.subject,
                        Admin.is_active.is_(True),
                    )
                )
            ).scalar_one_or_none()
            permissions = ()
            if admin is not None:
                permissions = (
                    (
                        await session.execute(
                            base_select(Permission)
                            .with_only_columns(Permission.code)
                            .join(
                                role_permissions,
                                role_permissions.c.permission_id == Permission.id,
                            )
                            .join(Role, Role.id == role_permissions.c.role_id)
                            .join(Admin, Admin.role_id == Role.id)
                            .where(
                                Admin.id == admin,
                                Admin.is_active.is_(True),
                                Role.is_active.is_(True),
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
        return {
            "issuer": person.principal.issuer,
            "subject": person.principal.subject,
            "displayName": localized(value=person.name),
            "area": "platform" if admin is not None else "tenant",
            "source": "authenticated-staging" if staging else "authenticated-local",
            "platformPermissions": sorted(permissions),
            "expiresAt": person.expires_at,
        }

    # ==============================================
    # PLATFORM ACCESS
    # Reuse the existing active-admin mapping; a tenant owner gains no global access.
    # ==============================================

    @app.get("/api/web/platform/access")
    async def platform_access(
        person: BrowserIdentity = identity_dep,
        session: AsyncSession = session_dep,
    ) -> JsonView:
        """Reuse the existing active-admin mapping; a tenant owner gains no global access."""
        admin = await auth.get_current_admin(
            credentials=HTTPAuthorizationCredentials(
                scheme="Bearer", credentials=person.access_token
            ),
            session=session,
        )
        return {"admin_id": admin.admin_id, "authenticated": True}

    # ==============================================
    # EXPLICIT SAAS PRICING PERMISSION BOUNDARY
    # All campaign operations share one exact server-side grant; no owner mutation API exists.
    # ==============================================

    @app.get("/api/web/platform/pricing/campaigns")
    async def campaigns(
        person: BrowserIdentity = identity_dep,
        session: AsyncSession = session_dep,
    ) -> list[CampaignView]:
        """Read actual platform campaigns without loading synthetic offers."""
        return await SaasPricingAdministration(session=session).campaigns(
            principal=person.principal
        )

    # ==============================================
    # CAMPAIGN CHANGE
    # Require exact pricing authority for creation, edits, publication and deactivation.
    # ==============================================

    @app.post("/api/web/platform/pricing/campaigns")
    async def campaign_change(
        command: CampaignCommand,
        person: BrowserIdentity = identity_dep,
        session: AsyncSession = session_dep,
    ) -> CampaignView:
        """Require exact pricing authority for creation, edits, publication and deactivation."""
        return await SaasPricingAdministration(session=session).execute(
            principal=person.principal, command=command
        )

    # ==============================================
    # EXISTING BASE PARAMETER EDITOR
    # Only explicitly authorized immediate changes are supported; no competing storage is added.
    # ==============================================

    @app.get("/api/web/platform/pricing/base")
    async def pricing_base(
        person: BrowserIdentity = identity_dep,
        session: AsyncSession = session_dep,
        country_code: str = "DZ",
        currency: str = "DZD",
    ) -> BasePriceView:
        """Read the existing singleton and its current revision."""
        return await SaasPricingAdministration(session=session).current_base(
            principal=person.principal, country_code=country_code, currency=currency
        )

    # ==============================================
    # CONFIGURED COUNTRY AND CURRENCY CONTEXTS
    # Never manufacture another market price or derive an exchange rate for this administration selector.
    # ==============================================

    @app.get("/api/web/platform/pricing/base-contexts")
    async def price_contexts(
        person: BrowserIdentity = identity_dep, session: AsyncSession = session_dep
    ) -> list[dict[str, object]]:
        """Expose only persisted applicable price pairs to explicitly authorized pricing administrators."""
        return await SaasPricingAdministration(session=session).base_contexts(
            principal=person.principal
        )

    # ==============================================
    # PRICING BASE CHANGE
    # Require the same exact pricing grant on direct API mutation.
    # ==============================================

    @app.post("/api/web/platform/pricing/base")
    async def pricing_base_change(
        command: BasePriceCommand,
        person: BrowserIdentity = identity_dep,
        session: AsyncSession = session_dep,
    ) -> BasePriceView:
        """Require the same exact pricing grant on direct API mutation."""
        return await SaasPricingAdministration(session=session).change_base(
            principal=person.principal, command=command
        )

    # ==============================================
    # RETAINED PRICING AUDIT
    # Read committed actor and value history under the same exact management permission.
    # ==============================================

    @app.get("/api/web/platform/pricing/base/history")
    async def pricing_base_history(
        person: BrowserIdentity = identity_dep, session: AsyncSession = session_dep
    ) -> list[PricingAuditView]:
        """Consult the base parameter journal without recomputing historical invoices."""
        return await SaasPricingAdministration(session=session).history(
            principal=person.principal, resource="saas_base", identifier=1
        )

    # ==============================================
    # CAMPAIGN HISTORY
    # Consult only retained entries for the requested administrative campaign.
    # ==============================================

    @app.get("/api/web/platform/pricing/campaigns/{identifier}/history")
    async def campaign_history(
        identifier: Annotated[int, Path(gt=0)],
        person: BrowserIdentity = identity_dep,
        session: AsyncSession = session_dep,
    ) -> list[PricingAuditView]:
        """Consult only retained entries for the requested administrative campaign."""
        return await SaasPricingAdministration(session=session).history(
            principal=person.principal, resource="saas_promotion", identifier=identifier
        )

    # ==============================================
    # ORGANIZATIONS
    # Discover own associations, then revalidate each active company before naming it.
    # ==============================================

    @app.get("/api/web/platform/pricing/reminders")
    async def read_reminders(
        person: BrowserIdentity = identity_dep, session: AsyncSession = session_dep
    ) -> JsonView:
        """Read real offsets without disclosing recipient credentials or starting a worker."""
        return await SaasPricingAdministration(session=session).reminder_configuration(
            principal=person.principal
        )

    # ==============================================
    # EDIT REMINDERS
    # Require explicit pricing authority and versioned intent for the next schedules.
    # ==============================================

    @app.post("/api/web/platform/pricing/reminders")
    async def edit_reminders(
        data: ReminderCommand,
        person: BrowserIdentity = identity_dep,
        session: AsyncSession = session_dep,
    ) -> JsonView:
        """Require explicit pricing authority and versioned intent for the next schedules."""
        return await SaasPricingAdministration(session=session).change_reminders(
            principal=person.principal, command=data
        )

    # ==============================================
    # RETAINED REMINDER POLICY DECISIONS
    # History stays readable through retained actor snapshots even after account deletion.
    # ==============================================

    @app.get("/api/web/platform/pricing/reminders/history")
    async def reminders_history(
        person: BrowserIdentity = identity_dep, session: AsyncSession = session_dep
    ) -> list[PricingAuditView]:
        """Consult committed reminder changes under the exact existing pricing permission."""
        return await SaasPricingAdministration(session=session).history(
            principal=person.principal, resource="saas_configuration", identifier=1
        )

    # ==============================================
    # ORGANIZATIONS
    # Discover own associations, then revalidate each active company before naming it.
    # ==============================================

    @app.get("/api/web/organizations")
    async def organizations(
        person: BrowserIdentity = identity_dep,
    ) -> list[JsonView]:
        """Discover own associations, then revalidate each active company before naming it."""
        async with factory() as session:
            memberships = await TenantAccessService(session=session).own_memberships(
                principal=person.principal, limit=100
            )
        result = []
        for member in memberships:
            if member.status != "active":
                continue
            async with (
                factory() as session,
                TenantAccessService(session=session).authorized(
                    principal=person.principal,
                    organization_id=member.organization_id,
                    permission="tenant.restaurants.read",
                ) as unit,
            ):
                name = await session.scalar(
                    base_select(Organization)
                    .with_only_columns(Organization.name)
                    .where(Organization.id == unit.context.organization_id)
                )
                result.append(
                    {
                        "id": member.organization_id,
                        "name": localized(value=str(name)),
                        "city": localized(value=""),
                        "role": unit.context.role_code,
                        "accessMode": (
                            "company-wide"
                            if unit.context.access_mode == "company-wide"
                            else "explicit"
                        ),
                        "permissions": sorted(unit.context.permissions),
                    }
                )
        if not result and any(m.status == "suspended" for m in memberships):
            raise HTTPException(status_code=403, detail={"code": "suspended"})
        return result

    # ==============================================
    # RESTAURANTS VIEW
    # Read only current restaurant projections admitted by the existing tenant unit.
    # ==============================================

    async def restaurants_view(
        *,
        person: BrowserIdentity,
        organization_id: int,
        restaurant_id: int | None = None,
    ) -> list[RestaurantView]:
        """Read only current restaurant projections admitted by the existing tenant unit."""
        async with (
            factory() as session,
            TenantAccessService(session=session).authorized(
                principal=person.principal,
                organization_id=organization_id,
                permission="tenant.restaurants.read",
            ) as unit,
        ):
            records = (
                await unit.restaurants(limit=100)
                if restaurant_id is None
                else (await unit.restaurant(restaurant_id=restaurant_id),)
            )
            return [
                {
                    "id": r.id,
                    "organizationId": organization_id,
                    "name": localized(value=r.name),
                    "city": localized(value=r.wilaya or ""),
                    "active": r.is_active is True,
                }
                for r in records
            ]

    # ==============================================
    # RESTAURANTS
    # Never infer a first organization from a caller's URL.
    # ==============================================

    @app.get("/api/web/organizations/{organization_id}/restaurants")
    async def restaurants(
        organization_id: int, person: BrowserIdentity = identity_dep
    ) -> list[RestaurantView]:
        """Never infer a first organization from a caller's URL."""
        return await restaurants_view(person=person, organization_id=organization_id)

    # ==============================================
    # RESTAURANT
    # Deny an absent, foreign or ungranted restaurant through the same tenant boundary.
    # ==============================================

    @app.get("/api/web/organizations/{organization_id}/restaurants/{restaurant_id}")
    async def restaurant(
        organization_id: int,
        restaurant_id: int,
        person: BrowserIdentity = identity_dep,
    ) -> RestaurantView:
        """Deny an absent, foreign or ungranted restaurant through the same tenant boundary."""
        return (
            await restaurants_view(
                person=person,
                organization_id=organization_id,
                restaurant_id=restaurant_id,
            )
        )[0]

    # ==============================================
    # DINING SESSION
    # Return genuine current branch scope; there is no second login or customer proof
    # fixture.
    # ==============================================

    @app.get("/api/web/dining-session")
    async def dining_session(person: BrowserIdentity = identity_dep) -> JsonView:
        """Return genuine current branch scope; there is no second login or customer proof fixture."""
        async with factory() as session:
            memberships = await TenantAccessService(session=session).own_memberships(
                principal=person.principal, limit=100
            )
        scopes = []
        for member in memberships:
            if member.status != "active":
                continue
            records = await restaurants_view(
                person=person, organization_id=member.organization_id
            )
            for record in records:
                async with factory() as session:
                    branches = (
                        await session.execute(
                            base_select(Branch)
                            .with_only_columns(Branch.id, Branch.name)
                            .where(
                                Branch.restaurant_id == record["id"],
                                Branch.is_active.is_(True),
                            )
                            .order_by(Branch.id)
                            .limit(100)
                        )
                    ).all()
                for branch in branches:
                    try:
                        async with (
                            factory() as session,
                            DiningService(session=session).authorized(
                                principal=person.principal,
                                organization_id=member.organization_id,
                                restaurant_id=int(record["id"]),
                                branch_id=branch.id,
                            ) as unit,
                        ):
                            await unit.guard(capability="read")
                            scopes.append(
                                {
                                    "organization_id": member.organization_id,
                                    "restaurant_id": record["id"],
                                    "branch_id": branch.id,
                                    "role": member.role,
                                    "restaurant_name": record["name"]["fr"],
                                    "branch_name": branch.name,
                                }
                            )
                    except TenantAccessDenied:
                        continue
        return {
            "actor": person.name,
            "identity_provider": "keycloak-staging" if staging else "keycloak-local",
            "persistence": (
                "postgres-staging-persistent"
                if staging
                else "postgres-local-persistent"
            ),
            "scopes": scopes,
            "customer_proofs": {},
        }

    # ==============================================
    # EXACT FOOD SETTLEMENT AND OWN CUSTOMER BALANCE
    # Reuse current tenant and human grants; a public visit proof cannot record payment.
    # ==============================================

    @app.get(
        "/api/web/organizations/{organization_id}/restaurants/{restaurant_id}/offer"
    )
    async def owner_offer(
        organization_id: int,
        restaurant_id: int,
        person: BrowserIdentity = identity_dep,
        session: AsyncSession = session_dep,
    ) -> JsonView:
        """Consult an owned offer without the platform pricing-edit permission."""
        async with TenantAccessService(session=session).authorized(
            principal=person.principal,
            organization_id=organization_id,
            permission="tenant.billing.read",
        ) as unit:
            await unit.restaurant(restaurant_id=restaurant_id)
            try:
                return await available_offer(
                    session=session, restaurant_id=restaurant_id
                )
            except ValueError as error:
                raise HTTPException(
                    status_code=409,
                    detail={"code": "subscription_pricing_configuration_missing"},
                ) from error

    # ==============================================
    # OWNER SIMULATION
    # Run the single authoritative engine for the selected authorized context, with no activation.
    # ==============================================

    @app.post(
        "/api/web/organizations/{organization_id}/restaurants/{restaurant_id}/offer/simulation"
    )
    async def owner_simulation(
        organization_id: int,
        restaurant_id: int,
        data: OfferInput,
        person: BrowserIdentity = identity_dep,
        session: AsyncSession = session_dep,
    ) -> JsonView:
        """Run the single authoritative engine for the selected authorized context, with no activation."""
        async with TenantAccessService(session=session).authorized(
            principal=person.principal,
            organization_id=organization_id,
            permission="tenant.billing.read",
        ) as unit:
            await unit.restaurant(restaurant_id=restaurant_id)
            try:
                return await simulate_offer(
                    session=session, restaurant_id=restaurant_id, data=data
                )
            except ValueError as error:
                known = {
                    "subscription_reference_missing",
                    "paid_service_history_incomplete",
                    "last_active_month_missing",
                    "trial_period_not_finished",
                    "mandatory_feature_configuration_missing",
                    "feature_price_missing",
                    "branch_grid_missing",
                    "branch_grid_ambiguous",
                }
                code = (
                    str(error)
                    if str(error) in known
                    else "subscription_configuration_requires_review"
                )
                raise HTTPException(status_code=409, detail={"code": code}) from error

    # ==============================================
    # DINING ERROR
    # Return a safe domain code without SQL details or customer credentials.
    # ==============================================

    @app.exception_handler(DiningError)
    async def dining_error(_request: Request, error: DiningError) -> JSONResponse:
        """Return a safe domain code without SQL details or customer credentials."""
        return JSONResponse({"detail": {"code": error.code}}, status_code=409)

    # ==============================================
    # INTEGRITY ERROR
    # A duplicate or invalid receipt rolls back its request and exposes no database contents.
    # ==============================================

    @app.exception_handler(IntegrityError)
    async def integrity_error(
        _request: Request, _error: IntegrityError
    ) -> JSONResponse:
        """A duplicate or invalid receipt rolls back its request and exposes no database contents."""
        return JSONResponse(
            {"detail": {"code": "persisted_constraint_conflict"}}, status_code=409
        )

    # ==============================================
    # FOOD BALANCE
    # Consult only a currently authorized branch invoice with the existing financial read permission.
    # ==============================================

    @app.get(
        "/api/web/organizations/{organization_id}/restaurants/{restaurant_id}/branches/{branch_id}/dining/invoices/{invoice_id}/balance"
    )
    async def food_balance(
        organization_id: int,
        restaurant_id: int,
        branch_id: int,
        invoice_id: Annotated[int, Path(gt=0)],
        person: BrowserIdentity = identity_dep,
        session: AsyncSession = session_dep,
    ) -> JsonView:
        """Consult only a currently authorized branch invoice with the existing financial read permission."""
        async with DiningService(session=session).authorized(
            principal=person.principal,
            organization_id=organization_id,
            restaurant_id=restaurant_id,
            branch_id=branch_id,
        ) as unit:
            await unit.guard(capability="finance.read", human=True)
            invoice = await unit.repo.one(
                model=DiningInvoice, identifier=invoice_id, lock=True
            )
            return await invoice_balance(session=session, invoice=invoice)

    # ==============================================
    # FOOD SETTLEMENT
    # Commit an observed exact remaining balance once; no external payment is performed.
    # ==============================================

    @app.post(
        "/api/web/organizations/{organization_id}/restaurants/{restaurant_id}/branches/{branch_id}/dining/invoices/{invoice_id}/settlement"
    )
    async def food_settlement(
        organization_id: int,
        restaurant_id: int,
        branch_id: int,
        invoice_id: Annotated[int, Path(gt=0)],
        data: SettlementInput,
        person: BrowserIdentity = identity_dep,
        session: AsyncSession = session_dep,
    ) -> JsonView:
        """Commit an observed exact remaining balance once; no external payment is performed."""
        async with DiningService(session=session).authorized(
            principal=person.principal,
            organization_id=organization_id,
            restaurant_id=restaurant_id,
            branch_id=branch_id,
        ) as unit:
            result = await record_settlement(
                unit=unit, invoice_id=invoice_id, data=data
            )
        return result

    # ==============================================
    # CUSTOMER INVOICE
    # Read only this visit's finalized invoice; never infer customer authority from a staff session.
    # ==============================================

    @app.post("/api/web/dining/public/invoice")
    async def customer_invoice(
        data: PublicReadInput,
        visit_token: Annotated[str, Header(alias="X-Visit-Token")],
        session: AsyncSession = session_dep,
    ) -> JsonView:
        """Read only this visit's finalized invoice; never infer customer authority from a staff session."""
        return await own_invoice(
            session=session, public_id=data.public_id, token=visit_token
        )

    app.include_router(
        dining_router(
            session_dependency=sessions,
            principal_dependency=principal,
            verification_origin=configuration.origin,
        ),
        prefix="/api/web",
    )
    return app


# ==============================================
# STRICT LOCAL COMPATIBILITY ENTRY
# Existing launchers and tests retain their exact local configuration contract.
# ==============================================


def create_operational_app(*, configuration: IntegrationConfig) -> FastAPI:
    """Keep remote configuration unavailable through the local entry point."""
    if not isinstance(configuration, IntegrationConfig):
        raise TypeError("local_integration_configuration_required")
    return compose_browser_app(configuration=configuration)
