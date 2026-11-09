# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# VERIFIED BILLING COUNTRY WORKFLOW
# Keep owner declarations, restricted proof and administrative validation separate until an effective decision exists.
# ==============================================

"""Caller-owned transactions; no notification, legal verification provider or automatic country inference."""

from __future__ import annotations

# isort: split
# ==============================================
# SCOPED AUTHORITY AND RETAINED DATA
# Use the existing identity/tenant services and exact platform permission, never role-based inference.
# ==============================================

import hashlib
import json
from datetime import (
    datetime,
    timezone,
)
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import undefer

from app.core.logger import logger
from app.core.security.oidc import OIDCPrincipal
from app.core.security.platform_permissions import TENANT_BILLING_COUNTRY_MANAGE
from app.core.security.tenant_types import TenantAccessDenied
from app.models.admin_log import AdminLog
from app.models.billing_country import (
    BillingCountryDecision,
    BillingCountryEvidence,
    BillingCountryProfile,
    BillingCountryRequest,
    EnrollmentDossier,
)
from app.models.restaurant import Restaurant
from app.models.subscription import Subscription
from app.models.subscription_pricing import SubscriptionPricingSnapshot
from app.models.tenant.schema import (
    Identity,
    Organization,
)
from app.repositories.restaurant_context import company_column
from app.repositories.subscription_queries import base_select
from app.schemas.billing_country import (
    CountryDeclaration,
    CountryReview,
)
from app.services.business.manual_payment_service import validate_receipt_content
from app.services.business.platform_authority import require_platform_permission
from app.services.business.subscription_types import JsonValue
from app.services.business.tenant_foundation import (
    TenantAuthorizationService,
    TenantContextResolver,
)

# ==============================================
# TRANSACTIONAL COUNTRY FACADE
# Every write serializes on the selected organization/profile and keeps its decision audit in the same transaction.
# ==============================================


class BillingCountryService:
    """Read and stage owned declarations or explicitly authorized reviews; the caller commits once."""

    # ==============================================
    # SESSION BOUNDARY
    # Reusing a caller transaction allows enrollment and financial context to remain atomic.
    # ==============================================

    def __init__(self, *, session: AsyncSession) -> None:
        """Retain the request-local session; no connection or transaction is opened implicitly."""
        self.session = session

    # ==============================================
    # AUTHENTICATED OWNER OR THEIR OWN DRAFT DOSSIER
    # An unfinished registration may access only its own dossier, not arbitrary tenant data.
    # ==============================================

    async def require_owner(
        self, *, principal: OIDCPrincipal, organization_id: int
    ) -> int:
        """Resolve the active stored identity, then require an owned draft or verified owner membership."""
        identity = await self.session.scalar(
            base_select(Identity).where(
                Identity.issuer == principal.issuer,
                Identity.subject == principal.subject,
                Identity.status == "active",
            )
        )
        if identity is None:
            raise TenantAccessDenied("identity_unavailable")
        draft = await self.session.scalar(
            base_select(EnrollmentDossier)
            .with_only_columns(EnrollmentDossier.id)
            .join(Organization, Organization.id == EnrollmentDossier.organization_id)
            .where(
                EnrollmentDossier.organization_id == organization_id,
                EnrollmentDossier.identity_id == identity.id,
                EnrollmentDossier.status != "completed",
                Organization.status == "draft",
            )
        )
        if draft is not None:
            return identity.id
        context = await TenantContextResolver(session=self.session).resolve(
            principal=principal, organization_id=organization_id
        )
        await TenantAuthorizationService(session=self.session).require_current(
            context=context, permission="tenant.billing.read"
        )
        if context.role_code != "owner" or context.identity_id != identity.id:
            raise TenantAccessDenied("billing_country_owner_required")
        return identity.id

    # ==============================================
    # SERIALIZED PROFILE INITIALIZATION
    # Lock the existing organization before creating the single revision row.
    # ==============================================

    async def profile(
        self, *, organization_id: int, lock: bool
    ) -> BillingCountryProfile | None:
        """Read or initialize only under an explicit caller-owned write transaction."""
        if lock:
            found = await self.session.scalar(
                base_select(Organization)
                .with_only_columns(Organization.id)
                .where(Organization.id == organization_id)
                .with_for_update()
            )
            if found is None:
                raise TenantAccessDenied("organization_unavailable")
        statement = base_select(BillingCountryProfile).where(
            BillingCountryProfile.organization_id == organization_id
        )
        if lock:
            statement = statement.with_for_update()
        profile = await self.session.scalar(statement)
        if profile is None and lock:
            profile = BillingCountryProfile(organization_id=organization_id, revision=1)
            self.session.add(profile)
            await self.session.flush()
        return profile

    # ==============================================
    # PRIVATE PROOF STORAGE
    # A local synthetic-document declaration is required; the content is never published as a static asset.
    # ==============================================

    async def store_evidence(
        self,
        *,
        principal: OIDCPrincipal,
        organization_id: int,
        content: bytes,
        filename: str,
        media_type: str,
        synthetic: bool,
    ) -> str:
        """Validate bounded file signatures and persist the proof for its verified owner only."""
        identity = await self.require_owner(
            principal=principal, organization_id=organization_id
        )
        if synthetic is not True:
            raise ValueError("real_billing_documents_retention_not_approved")
        if (
            not filename.strip()
            or len(filename) > 180
            or any(c in filename for c in "/\\\r\n\x00")
        ):
            raise ValueError("billing_document_filename_invalid")
        validate_receipt_content(content=content, media_type=media_type)
        await self.profile(organization_id=organization_id, lock=True)
        proof = BillingCountryEvidence(
            id=uuid4().hex,
            organization_id=organization_id,
            submitted_identity_id=identity,
            filename=filename,
            media_type=media_type,
            content=content,
            sha256=hashlib.sha256(content).hexdigest(),
            synthetic=True,
        )
        self.session.add(proof)
        await self.session.flush()
        return proof.id

    # ==============================================
    # PRIVATE PROOF READ
    # Either the current organization owner or an explicitly habilitated platform reviewer may see the bytes.
    # ==============================================

    async def evidence(
        self, *, principal: OIDCPrincipal, evidence_id: str, reviewer: bool
    ) -> BillingCountryEvidence:
        """Authorize before loading the deferred document body; keep foreign denials generic."""
        row = await self.session.scalar(
            base_select(BillingCountryEvidence).where(
                BillingCountryEvidence.id == evidence_id
            )
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Evidence unavailable")
        if reviewer:
            await require_platform_permission(
                session=self.session,
                principal=principal,
                permission=TENANT_BILLING_COUNTRY_MANAGE,
            )
        else:
            await self.require_owner(
                principal=principal, organization_id=row.organization_id
            )
        result = await self.session.scalar(
            base_select(BillingCountryEvidence)
            .options(undefer(BillingCountryEvidence.content))
            .where(BillingCountryEvidence.id == evidence_id)
        )
        if result is None:
            raise HTTPException(status_code=404, detail="Evidence unavailable")
        return result

    # ==============================================
    # IDEMPOTENT OWNER DECLARATION
    # The country remains declared until a separate human review succeeds.
    # ==============================================

    async def declare(
        self,
        *,
        principal: OIDCPrincipal,
        organization_id: int,
        data: CountryDeclaration,
    ) -> dict[str, JsonValue]:
        """Stage a new request, or return the same intent; never reuse a foreign proof or changed key payload."""
        identity = await self.require_owner(
            principal=principal, organization_id=organization_id
        )
        profile = await self.profile(organization_id=organization_id, lock=True)
        if profile is None:
            raise RuntimeError("billing_country_profile_unavailable")
        existing = await self.session.scalar(
            base_select(BillingCountryRequest).where(
                BillingCountryRequest.organization_id == organization_id,
                BillingCountryRequest.idempotency_key == data.idempotency_key,
            )
        )
        if existing is not None:
            if (
                existing.declared_country,
                existing.legal_entity_reference,
                existing.reason,
                existing.evidence_id,
            ) != (
                data.declared_country,
                data.legal_entity_reference.strip(),
                data.reason.strip(),
                data.evidence_id,
            ):
                raise ValueError("billing_country_idempotency_conflict")
            return await self.view(organization_id=organization_id)
        if (
            data.expected_revision != profile.revision
            or not data.reason.strip()
            or not data.legal_entity_reference.strip()
        ):
            raise ValueError("billing_country_revision_changed")
        proof = await self.session.scalar(
            base_select(BillingCountryEvidence)
            .with_only_columns(BillingCountryEvidence.id)
            .where(
                BillingCountryEvidence.id == data.evidence_id,
                BillingCountryEvidence.organization_id == organization_id,
                BillingCountryEvidence.submitted_identity_id == identity,
            )
        )
        if proof is None:
            raise ValueError("billing_country_proof_required")
        pending = (
            await self.session.scalars(
                base_select(BillingCountryRequest)
                .where(
                    BillingCountryRequest.organization_id == organization_id,
                    BillingCountryRequest.status.in_(["pending", "needs_information"]),
                )
                .with_for_update()
            )
        ).all()
        for previous in pending:
            if previous.status == "pending":
                raise ValueError("billing_country_review_already_pending")
            previous.status = "superseded"
        await self.session.flush()
        self.session.add(
            BillingCountryRequest(
                organization_id=organization_id,
                submitted_identity_id=identity,
                declared_country=data.declared_country,
                legal_entity_reference=data.legal_entity_reference.strip(),
                reason=data.reason.strip(),
                evidence_id=data.evidence_id,
                expected_revision=profile.revision,
                status="pending",
                idempotency_key=data.idempotency_key,
            )
        )
        profile.revision += 1
        await self.session.flush()
        return await self.view(organization_id=organization_id)

    # ==============================================
    # AUTHORIZED HUMAN REVIEW
    # The server determines timing; current coverage and an existing legal entity cannot be rewritten.
    # ==============================================

    async def review(
        self, *, principal: OIDCPrincipal, request_id: int, data: CountryReview
    ) -> dict[str, JsonValue]:
        """Approve, refuse or request details under the exact country permission and profile revision."""
        author = await require_platform_permission(
            session=self.session,
            principal=principal,
            permission=TENANT_BILLING_COUNTRY_MANAGE,
        )
        request = await self.session.scalar(
            base_select(BillingCountryRequest).where(
                BillingCountryRequest.id == request_id
            )
        )
        if request is None:
            raise HTTPException(status_code=404, detail="Country request unavailable")
        profile = await self.profile(organization_id=request.organization_id, lock=True)
        await self.session.refresh(request)
        if (
            profile is None
            or profile.revision != data.expected_revision
            or request.status != "pending"
            or not data.justification.strip()
        ):
            raise ValueError("billing_country_review_changed")
        now = datetime.now(timezone.utc)
        previous = await self.session.scalar(
            base_select(BillingCountryDecision)
            .where(BillingCountryDecision.organization_id == request.organization_id)
            .order_by(
                BillingCountryDecision.effective_at.desc(),
                BillingCountryDecision.id.desc(),
            )
            .limit(1)
        )
        if data.decision == "approve":
            if not data.evidence_checked:
                raise ValueError("billing_country_official_evidence_review_required")
            if not data.same_legal_entity or (
                previous is not None
                and previous.legal_entity_reference != request.legal_entity_reference
            ):
                raise ValueError("billing_legal_entity_change_requires_separate_review")
            if previous is not None and (
                previous.effective_at > now
                or previous.validated_country == request.declared_country
            ):
                raise ValueError("billing_country_change_already_pending_or_unchanged")
            effective = now
            # A decision is validated for the company now. Each renewal reads it at
            # its own next service start; committed periods retain their snapshots.
            # One subscription remains one deadline even if it covers several sites.
            profile.revision += 1
            self.session.add(
                BillingCountryDecision(
                    organization_id=request.organization_id,
                    request_id=request.id,
                    previous_country=previous.validated_country if previous else None,
                    validated_country=request.declared_country,
                    legal_entity_reference=request.legal_entity_reference,
                    evidence_id=request.evidence_id,
                    author_admin_id=author,
                    justification=data.justification.strip(),
                    decided_at=now,
                    effective_at=effective,
                    profile_revision=profile.revision,
                )
            )
            request.status = "approved"
        else:
            effective = None
            profile.revision += 1
            request.status = (
                "rejected" if data.decision == "reject" else "needs_information"
            )
        self.session.add(
            AdminLog(
                admin_id=author,
                action="billing.country." + request.status,
                resource="billing_country_request",
                resource_id=request.id,
                timestamp=now.replace(tzinfo=None),
                details=json.dumps(
                    {
                        "organization_id": request.organization_id,
                        "request_id": request.id,
                        "previous_country": (
                            previous.validated_country if previous else None
                        ),
                        "declared_country": request.declared_country,
                        "evidence_id": request.evidence_id,
                        "justification": data.justification.strip(),
                        "effective_at": effective.isoformat() if effective else None,
                        "profile_revision": profile.revision,
                    },
                    sort_keys=True,
                ),
            )
        )
        await self.session.flush()
        logger.info(
            "Country review staged in caller transaction",
            extra={
                "request_id": request.id,
                "admin_id": author,
                "decision": request.status,
            },
        )
        return await self.view(organization_id=request.organization_id)

    # ==============================================
    # DETACHED DECLARED AND VALIDATED PROJECTION
    # Proof bytes and identity identifiers are never part of this overview.
    # ==============================================

    async def view(self, *, organization_id: int) -> dict[str, JsonValue]:
        """Read within an already authorized request transaction, separating pending and effective countries."""
        profile = await self.profile(organization_id=organization_id, lock=False)
        requests = (
            await self.session.scalars(
                base_select(BillingCountryRequest)
                .where(BillingCountryRequest.organization_id == organization_id)
                .order_by(BillingCountryRequest.id.desc())
                .limit(20)
            )
        ).all()
        decisions = (
            await self.session.scalars(
                base_select(BillingCountryDecision)
                .where(BillingCountryDecision.organization_id == organization_id)
                .order_by(
                    BillingCountryDecision.effective_at.desc(),
                    BillingCountryDecision.id.desc(),
                )
                .limit(20)
            )
        ).all()
        now = datetime.now(timezone.utc)
        active = next((d for d in decisions if d.effective_at <= now), None)
        pending = next((d for d in decisions if d.effective_at > now), None)
        return {
            "organization_id": organization_id,
            "revision": profile.revision if profile else 1,
            "declared_country": requests[0].declared_country if requests else None,
            "validated_country": active.validated_country if active else None,
            "pending_country": pending.validated_country if pending else None,
            "pending_effective_at": (
                pending.effective_at.isoformat() if pending else None
            ),
            "requests": [
                {
                    "id": r.id,
                    "country": r.declared_country,
                    "status": r.status,
                    "evidence_id": r.evidence_id,
                    "legal_entity_reference": r.legal_entity_reference,
                    "submitted_at": r.submitted_at.isoformat(),
                }
                for r in requests
            ],
            "decisions": [
                {
                    "id": d.id,
                    "country": d.validated_country,
                    "previous_country": d.previous_country,
                    "effective_at": d.effective_at.isoformat(),
                    "decided_at": d.decided_at.isoformat(),
                    "author_admin_id": d.author_admin_id,
                    "evidence_id": d.evidence_id,
                    "justification": d.justification,
                }
                for d in decisions
            ],
            "synthetic_documents_only": True,
        }


# ==============================================
# SERVER-OWNED RENEWAL COUNTRY CONTEXT
# A browser-selected country or unvalidated declaration can never determine a binding price.
# ==============================================


async def validated_country_for_subscription(
    *, session: AsyncSession, owner_id: int, restaurant_id: int, currency: str | None
) -> tuple[str, int, datetime]:
    """Resolve the effective decision at the next service start, preserving early-renewal coverage."""
    organization = await session.scalar(
        base_select(Restaurant)
        .with_only_columns(company_column(), maintain_column_froms=True)
        .where(Restaurant.id == restaurant_id, Restaurant.owner_id == owner_id)
    )
    if organization is None:
        raise ValueError("validated_billing_country_required")
    profile = await session.scalar(
        base_select(BillingCountryProfile)
        .where(BillingCountryProfile.organization_id == organization)
        .with_for_update(read=True)
    )
    if profile is None:
        raise ValueError("validated_billing_country_required")
    now = datetime.now(timezone.utc)
    expires = await session.scalar(
        base_select(Subscription)
        .with_only_columns(func.max(Subscription.expires_at))
        .where(
            Subscription.restaurant_id == restaurant_id,
            Subscription.owner_id == owner_id,
            Subscription.status.in_(["active", "trial"]),
            Subscription.expires_at > now.replace(tzinfo=None),
        )
    )
    service_start = expires.replace(tzinfo=timezone.utc) if expires is not None else now
    decision = await session.scalar(
        base_select(BillingCountryDecision)
        .where(
            BillingCountryDecision.organization_id == organization,
            BillingCountryDecision.effective_at <= service_start,
        )
        .order_by(
            BillingCountryDecision.effective_at.desc(), BillingCountryDecision.id.desc()
        )
        .limit(1)
    )
    if decision is None:
        raise ValueError("validated_billing_country_required")
    from app.services.business.subscription_country_base import resolve_country_base

    # Price selection uses the calculation time; the new country's applicability uses coverage start.
    if currency is not None:
        await resolve_country_base(
            session=session,
            country_code=decision.validated_country,
            currency=currency,
            at=now,
        )
    return decision.validated_country, decision.id, service_start


# ==============================================
# UNFINALIZED COUNTRY AND PRICE REVALIDATION
# Retain the old calculation as evidence but refuse settlement after its applicable context has changed.
# ==============================================


async def require_pending_country_context(
    *, session: AsyncSession, subscription: Subscription
) -> None:
    """Require a new quote rather than rewriting pending evidence or applying a country chosen by the browser."""
    from app.repositories.subscription_configuration import country_storage_enabled
    from app.services.business.subscription_country_base import resolve_country_base

    if not await country_storage_enabled(session=session):
        return
    if subscription.status not in {"pending", "pending_payment"}:
        return
    country, decision, _starts = await validated_country_for_subscription(
        session=session,
        owner_id=subscription.owner_id,
        restaurant_id=subscription.restaurant_id,
        currency=subscription.currency,
    )
    parameters = await session.scalar(
        base_select(SubscriptionPricingSnapshot)
        .with_only_columns(SubscriptionPricingSnapshot.parameters)
        .where(SubscriptionPricingSnapshot.subscription_id == subscription.id)
    )
    current = await resolve_country_base(
        session=session,
        country_code=country,
        currency=subscription.currency,
        at=datetime.now(timezone.utc),
    )
    from app.repositories.subscription_configuration import read_pricing_policy

    policies = await read_pricing_policy(session=session)
    if (
        parameters is None
        or parameters.get("billing_country_decision_id") != decision
        or parameters.get("base_revision") != current.revision
        or parameters.get("payment_adjustment_rates")
        != policies.get("payment_adjustment_rates")
    ):
        raise ValueError("billing_country_pending_offer_requires_recalculation")
