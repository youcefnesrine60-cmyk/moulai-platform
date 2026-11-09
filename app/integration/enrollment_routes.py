# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# LOCAL AUTHENTICATED ENROLLMENT HTTP ADAPTER
# Expose existing transactional services through opaque browser authentication, not browser-selected identities or roles.
# ==============================================

"""Mounted only by the pinned local operational factory; no deployment route registration."""

from __future__ import annotations

# isort: split
# ==============================================
# CLOSED ROUTE DEPENDENCIES
# Request sessions and principals are injected by the existing verified browser transport.
# ==============================================

from typing import Literal

from fastapi import (
    FastAPI,
    HTTPException,
    Request,
    Response,
)
from fastapi.params import Depends
from pydantic import JsonValue
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.platform_permissions import TENANT_BILLING_COUNTRY_MANAGE
from app.core.security.tenant_types import TenantAccessDenied
from app.integration.config import IntegrationConfig
from app.integration.identity import BrowserIdentity
from app.models.billing_country import BillingCountryRequest
from app.models.tenant.schema import Organization
from app.repositories.subscription_queries import base_select
from app.schemas.billing_country import (
    CountryDeclaration,
    CountryReview,
)
from app.schemas.enrollment import (
    DocumentResponseInput,
    EnrollmentInput,
)
from app.services.business.billing_country import BillingCountryService
from app.services.business.enrollment import EnrollmentService
from app.services.business.enrollment_documents import (
    present_documents,
    respond_to_document,
)
from app.services.business.platform_authority import require_platform_permission
from app.services.business.tenant_foundation import tenant_unit_of_work

# ==============================================
# EXPLICIT LOCAL COMPOSITION
# The production application never imports this adapter or admits fictitious document endpoints implicitly.
# ==============================================


def mount_enrollment_routes(
    *,
    app: FastAPI,
    configuration: IntegrationConfig,
    identity_dep: Depends,
    session_dep: Depends,
) -> None:
    """Register bounded owner and platform endpoints with their distinct current server-side authority."""

    # ==============================================
    # OWN DOSSIER CONSULTATION AND CREATION
    # An unassigned authenticated account may start its own draft, never choose another identity.
    # ==============================================

    @app.get("/api/web/enrollment")
    async def own_dossier(
        person: BrowserIdentity = identity_dep, session: AsyncSession = session_dep
    ) -> dict[str, JsonValue] | None:
        """Return only the signed-in account's dossier; absence is a normal first-visit state."""
        async with session.begin():
            try:
                return await EnrollmentService(
                    session=session, marker=configuration.instance_id
                ).view(principal=person.principal)
            except TenantAccessDenied as error:
                if str(error) != "enrollment_dossier_unavailable":
                    raise
                return None

    @app.post("/api/web/enrollment")
    async def create_dossier(
        data: EnrollmentInput,
        person: BrowserIdentity = identity_dep,
        session: AsyncSession = session_dep,
    ) -> dict[str, JsonValue]:
        """Persist an owned draft; this action grants neither trial nor business access."""
        async with session.begin():
            return await EnrollmentService(
                session=session, marker=configuration.instance_id
            ).create(principal=person.principal, data=data)

    # ==============================================
    # EXACT DOCUMENT PRESENTATION AND SEPARATE RESPONSE
    # A presentation POST records evidence; no GET silently claims consent or preselects a response.
    # ==============================================

    @app.post("/api/web/enrollment/documents/present")
    async def documents(
        locale: Literal["fr", "en", "ar"],
        person: BrowserIdentity = identity_dep,
        session: AsyncSession = session_dep,
    ) -> list[dict[str, JsonValue]]:
        """Present and hash the current local test documents in the requested language."""
        async with session.begin():
            return await present_documents(
                session=session,
                principal=person.principal,
                marker=configuration.instance_id,
                locale=locale,
            )

    @app.post("/api/web/enrollment/documents/respond")
    async def document_response(
        data: DocumentResponseInput,
        person: BrowserIdentity = identity_dep,
        session: AsyncSession = session_dep,
    ) -> Response:
        """Record one explicit acceptance, information acknowledgement or optional refusal."""
        async with session.begin():
            await respond_to_document(
                session=session,
                principal=person.principal,
                marker=configuration.instance_id,
                **data.model_dump(),
            )
        return Response(status_code=204)

    @app.post("/api/web/enrollment/finalize")
    async def finalize(
        person: BrowserIdentity = identity_dep, session: AsyncSession = session_dep
    ) -> dict[str, JsonValue]:
        """Approve eligible trial enrollment atomically, after country and current-document gates."""
        async with session.begin():
            return await EnrollmentService(
                session=session, marker=configuration.instance_id
            ).finalize(principal=person.principal)

    # ==============================================
    # OWNER COUNTRY WORKFLOW
    # Existing active owners use the full tenant authority unit; draft access is limited to the dossier owner.
    # ==============================================

    @app.get("/api/web/organizations/{organization_id}/billing-country")
    async def country(
        organization_id: int,
        person: BrowserIdentity = identity_dep,
        session: AsyncSession = session_dep,
    ) -> dict[str, JsonValue]:
        """Keep current validated and owner-declared country separate in the displayed projection."""
        async with tenant_unit_of_work(session=session):
            service = BillingCountryService(session=session)
            await service.require_owner(
                principal=person.principal, organization_id=organization_id
            )
            return await service.view(organization_id=organization_id)

    @app.post("/api/web/organizations/{organization_id}/billing-country/evidence")
    async def upload(
        organization_id: int,
        request: Request,
        filename: str,
        synthetic: bool,
        person: BrowserIdentity = identity_dep,
        session: AsyncSession = session_dep,
    ) -> dict[str, str]:
        """Bound the stream before storing private synthetic proof; never publish a static file URL."""
        body = bytearray()
        async for chunk in request.stream():
            if len(body) + len(chunk) > 2 * 1024 * 1024:
                raise HTTPException(status_code=413, detail="Document too large")
            body.extend(chunk)
        async with tenant_unit_of_work(session=session):
            identifier = await BillingCountryService(session=session).store_evidence(
                principal=person.principal,
                organization_id=organization_id,
                content=bytes(body),
                filename=filename,
                media_type=request.headers.get("content-type", ""),
                synthetic=synthetic,
            )
        return {"id": identifier}

    @app.post("/api/web/organizations/{organization_id}/billing-country")
    async def declare(
        organization_id: int,
        data: CountryDeclaration,
        person: BrowserIdentity = identity_dep,
        session: AsyncSession = session_dep,
    ) -> dict[str, JsonValue]:
        """Store an idempotent motivated request, without changing the validated country."""
        async with tenant_unit_of_work(session=session):
            return await BillingCountryService(session=session).declare(
                principal=person.principal, organization_id=organization_id, data=data
            )

    # ==============================================
    # DISTINCT PLATFORM COUNTRY REVIEW
    # Pricing and payment permissions never substitute the dedicated country-validation grant.
    # ==============================================

    @app.get("/api/web/platform/billing-countries")
    async def review_queue(
        person: BrowserIdentity = identity_dep, session: AsyncSession = session_dep
    ) -> list[dict[str, JsonValue]]:
        """Read at most one hundred pending synthetic dossiers under the exact administrative permission."""
        async with session.begin():
            await require_platform_permission(
                session=session,
                principal=person.principal,
                permission=TENANT_BILLING_COUNTRY_MANAGE,
            )
            rows = (
                await session.execute(
                    base_select(BillingCountryRequest)
                    .with_only_columns(
                        BillingCountryRequest.id,
                        BillingCountryRequest.organization_id,
                        Organization.name,
                        BillingCountryRequest.status,
                    )
                    .join(
                        Organization,
                        Organization.id == BillingCountryRequest.organization_id,
                    )
                    .order_by(BillingCountryRequest.id.desc())
                    .limit(100)
                )
            ).all()
            return [
                {
                    "id": row.id,
                    "organization_id": row.organization_id,
                    "company_name": row.name,
                    "status": row.status,
                }
                for row in rows
            ]

    @app.get("/api/web/platform/billing-countries/{organization_id}")
    async def review_detail(
        organization_id: int,
        person: BrowserIdentity = identity_dep,
        session: AsyncSession = session_dep,
    ) -> dict[str, JsonValue]:
        """Display decision history without proof bytes or another reviewer's authority."""
        async with session.begin():
            await require_platform_permission(
                session=session,
                principal=person.principal,
                permission=TENANT_BILLING_COUNTRY_MANAGE,
            )
            return await BillingCountryService(session=session).view(
                organization_id=organization_id
            )

    @app.post("/api/web/platform/billing-country-requests/{request_id}/review")
    async def review(
        request_id: int,
        data: CountryReview,
        person: BrowserIdentity = identity_dep,
        session: AsyncSession = session_dep,
    ) -> dict[str, JsonValue]:
        """Record a separate human decision, immutable author and server-selected effective date."""
        async with session.begin():
            return await BillingCountryService(session=session).review(
                principal=person.principal, request_id=request_id, data=data
            )

    @app.get("/api/web/billing-country-evidence/{evidence_id}")
    async def proof(
        evidence_id: str,
        reviewer: bool = False,
        person: BrowserIdentity = identity_dep,
        session: AsyncSession = session_dep,
    ) -> Response:
        """Authorize before retrieving private bytes; force download and prohibit browser caching."""
        async with tenant_unit_of_work(session=session):
            row = await BillingCountryService(session=session).evidence(
                principal=person.principal, evidence_id=evidence_id, reviewer=reviewer
            )
            return Response(
                content=row.content,
                media_type=row.media_type,
                headers={
                    "Cache-Control": "no-store",
                    "Content-Disposition": "attachment; filename=billing-proof",
                    "X-Content-Type-Options": "nosniff",
                },
            )
