# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# AUTHENTICATED COMPANY ENROLLMENT
# Create an owned draft through the browser and reuse atomic registration approval only after all evidence gates.
# ==============================================

"""Local caller-owned enrollment transactions; no CLI company creation, remote notification or inferred platform grant."""

from __future__ import annotations

# isort: split
# ==============================================
# ACCOUNT AND BUSINESS BOUNDARIES
# Existing registration services retain trial creation and entitlement rules; this facade binds their result to a tenant.
# ==============================================

from datetime import (
    datetime,
    timezone,
)

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.oidc import OIDCPrincipal
from app.core.security.tenant_types import (
    TenantAccessDenied,
    permission_ceiling,
)
from app.models.billing_country import (
    BillingCountryDecision,
    BillingCountryProfile,
    EnrollmentDossier,
)
from app.models.branch import Branch
from app.models.owner import Owner
from app.models.registration_request import RegistrationRequest
from app.models.restaurant import Restaurant
from app.models.tenant.schema import (
    Identity,
    Organization,
    OrganizationMembership,
    TenantRolePermission,
)
from app.repositories.restaurant_context import company_column
from app.repositories.subscription_queries import base_select
from app.schemas.enrollment import EnrollmentInput
from app.services.business.enrollment_documents import (
    dossier_identity,
    require_document_rehearsal,
    require_document_responses,
)

from app.services.business.registration_request_service import RegistrationRequestService  # isort: skip  # fmt: skip
from app.services.business.subscription_types import JsonValue

# ==============================================
# DRAFT AND FINALIZATION FACADE
# Lock the exact authenticated identity first so repeated requests cannot create parallel companies or consume two trials.
# ==============================================


class EnrollmentService:
    """Stage a single account-scoped dossier and commit its completed business graph through the caller."""

    # ==============================================
    # REQUEST LOCAL SESSION
    # A trusted instance marker is supplied by the pinned server, never an HTTP field.
    # ==============================================

    def __init__(self, *, session: AsyncSession, marker: str) -> None:
        """Retain the caller transaction and attested local context without opening another connection."""
        self.session = session
        self.marker = marker

    # ==============================================
    # AUTHENTICATED DOSSIER CREATION
    # Enrollment is deliberate; ordinary login continues to create no company or permissions.
    # ==============================================

    async def create(
        self, *, principal: OIDCPrincipal, data: EnrollmentInput
    ) -> dict[str, JsonValue]:
        """Create a draft only once for the active stored identity; refuse an already assigned account."""
        await require_document_rehearsal(session=self.session, marker=self.marker)
        identity = await self.session.scalar(
            base_select(Identity)
            .where(
                Identity.issuer == principal.issuer,
                Identity.subject == principal.subject,
            )
            .with_for_update()
        )
        if identity is None or identity.status != "active":
            raise TenantAccessDenied("enrollment_active_identity_required")
        existing = await self.session.scalar(
            base_select(EnrollmentDossier).where(
                EnrollmentDossier.identity_id == identity.id
            )
        )
        if existing is not None:
            return await self.view(principal=principal)
        membership = await self.session.scalar(
            base_select(OrganizationMembership)
            .with_only_columns(OrganizationMembership.id)
            .where(
                OrganizationMembership.identity_id == identity.id,
                OrganizationMembership.status.in_(["active", "pending", "suspended"]),
            )
            .limit(1)
        )
        if membership is not None:
            raise ValueError("enrollment_account_already_assigned")
        owner = await self.session.scalar(
            base_select(Owner).where(Owner.auth_subject == principal.subject)
        )
        # This reserved local compatibility number is not a Telegram account and
        # never proves identity; every association above uses issuer and subject.
        compatibility_id = owner.chat_id if owner else 9_000_000_000_000 + identity.id
        collision = await self.session.scalar(
            base_select(Owner).where(Owner.chat_id == compatibility_id)
        )
        if collision is not None and collision.auth_subject != principal.subject:
            raise ValueError("enrollment_legacy_identity_collision")
        organization = Organization(name=data.company_name, status="draft", revision=1)
        request = RegistrationRequest(
            chat_id=compatibility_id,
            full_name=data.full_name,
            owner_phone=data.phone,
            email=data.email,
            restaurant_name=data.restaurant_name,
            restaurant_type=data.restaurant_type,
            restaurant_phone=data.phone,
            status="pending",
            owner_id=owner.id if owner else None,
        )
        self.session.add_all([organization, request])
        await self.session.flush()
        self.session.add_all(
            [
                BillingCountryProfile(organization_id=organization.id, revision=1),
                EnrollmentDossier(
                    identity_id=identity.id,
                    organization_id=organization.id,
                    registration_request_id=request.id,
                    legal_entity_reference=data.legal_entity_reference,
                    branch_name=data.branch_name,
                    status="draft",
                    revision=1,
                ),
            ]
        )
        await self.session.flush()
        return await self.view(principal=principal)

    # ==============================================
    # DETACHED OWN DOSSIER
    # Technical references support resumption but never expose another account's evidence or private documents.
    # ==============================================

    async def view(self, *, principal: OIDCPrincipal) -> dict[str, JsonValue]:
        """Read only the verified account's persisted company, establishment and trial readiness."""
        dossier = await dossier_identity(session=self.session, principal=principal)
        organization = await self.session.get(Organization, dossier.organization_id)
        request = await self.session.get(
            RegistrationRequest, dossier.registration_request_id
        )
        if organization is None or request is None:
            raise ValueError("enrollment_graph_incomplete")
        return {
            "id": dossier.id,
            "organization_id": dossier.organization_id,
            "company_name": organization.name,
            "restaurant_name": request.restaurant_name,
            "branch_name": dossier.branch_name,
            "legal_entity_reference": dossier.legal_entity_reference,
            "status": dossier.status,
            "restaurant_id": dossier.restaurant_id,
            "revision": dossier.revision,
            "synthetic_documents_only": True,
        }

    # ==============================================
    # ATOMIC TRIAL ENROLLMENT
    # Country, document evidence, trial right, tenant ownership and first establishment share one transaction.
    # ==============================================

    async def finalize(self, *, principal: OIDCPrincipal) -> dict[str, JsonValue]:
        """Complete an eligible trial without sending messages; any failure rolls back all domain writes."""
        await require_document_responses(
            session=self.session, principal=principal, marker=self.marker
        )
        dossier = await dossier_identity(
            session=self.session, principal=principal, lock=True
        )
        if dossier.status == "completed":
            return await self.view(principal=principal)
        now = datetime.now(timezone.utc)
        organization = await self.session.scalar(
            base_select(Organization)
            .where(Organization.id == dossier.organization_id)
            .with_for_update()
        )
        decision = await self.session.scalar(
            base_select(BillingCountryDecision)
            .where(
                BillingCountryDecision.organization_id == dossier.organization_id,
                BillingCountryDecision.effective_at <= now,
            )
            .order_by(
                BillingCountryDecision.effective_at.desc(),
                BillingCountryDecision.id.desc(),
            )
            .limit(1)
        )
        if (
            organization is None
            or organization.status != "draft"
            or decision is None
            or decision.legal_entity_reference != dossier.legal_entity_reference
        ):
            raise ValueError("enrollment_validated_country_required")
        permissions = set(
            (
                await self.session.scalars(
                    base_select(TenantRolePermission)
                    .with_only_columns(TenantRolePermission.permission_code)
                    .where(TenantRolePermission.role_code == "owner")
                    .with_for_update(read=True)
                )
            ).all()
        )
        if not {
            "tenant.organization.read",
            "tenant.restaurants.read",
            "tenant.billing.read",
        }.issubset(permissions) or not permissions.issubset(
            permission_ceiling(role_code="owner")
        ):
            raise ValueError("enrollment_owner_policy_not_configured")
        response = await RegistrationRequestService(session=self.session).approve(
            request_id=dossier.registration_request_id
        )
        if response.owner_id is None:
            raise ValueError("enrollment_owner_not_created")
        owner = await self.session.scalar(
            base_select(Owner).where(Owner.id == response.owner_id).with_for_update()
        )
        if owner is None or owner.auth_subject not in (None, principal.subject):
            raise TenantAccessDenied("enrollment_owner_identity_mismatch")
        owner.auth_subject = principal.subject
        # The legacy atomic approval creates exactly this request's restaurant;
        # reject ambiguity instead of attaching another preexisting establishment.
        request = await self.session.get(
            RegistrationRequest, dossier.registration_request_id
        )
        if request is None:
            raise ValueError("enrollment_registration_missing")
        restaurants = (
            await self.session.scalars(
                base_select(Restaurant)
                .where(
                    Restaurant.owner_id == owner.id,
                    Restaurant.name == request.restaurant_name,
                    company_column().is_(None),
                )
                .with_for_update()
            )
        ).all()
        if len(restaurants) != 1:
            raise ValueError("enrollment_created_restaurant_ambiguous")
        restaurant = restaurants[0]
        attached = await self.session.scalar(
            text(
                "UPDATE restaurants SET organization_id=:organization WHERE id=:restaurant AND owner_id=:owner AND organization_id IS NULL RETURNING id"
            ),
            {
                "organization": dossier.organization_id,
                "restaurant": restaurant.id,
                "owner": owner.id,
            },
        )
        if attached != restaurant.id:
            raise ValueError("enrollment_restaurant_attachment_changed")
        self.session.add(
            Branch(
                restaurant_id=restaurant.id, name=dossier.branch_name, is_active=True
            )
        )
        self.session.add(
            OrganizationMembership(
                organization_id=dossier.organization_id,
                identity_id=dossier.identity_id,
                role_code="owner",
                access_mode="company-wide",
                status="active",
                revision=1,
                enrollment_generation=1,
                accepted_at=now,
                activated_at=now,
            )
        )
        await self.session.flush()
        await self.session.refresh(organization)
        organization.status = "active"
        organization.tenant_enforced_at = now
        organization.revision += 1
        dossier.status = "completed"
        dossier.completed_at = now
        dossier.restaurant_id = restaurant.id
        dossier.revision += 1
        await self.session.flush()
        return await self.view(principal=principal)
