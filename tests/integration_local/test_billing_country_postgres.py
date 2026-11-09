# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# O4 COUNTRY AND ENROLLMENT POSTGRESQL PROOFS
# Exercise committed account-scoped documents and country decisions on a separately attested disposable cluster.
# ==============================================

"""No shared destructive fixtures, real documents, remote calls or commercial test-price publication."""

from __future__ import annotations

# isort: split
# ==============================================
# CONTROLLED LOCAL TEST DEPENDENCIES
# Every fixture verifies the actual target before creating synthetic identities or exact permissions.
# ==============================================

import asyncio
import os
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import (
    insert,
    text,
)
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.security.oidc import OIDCPrincipal
from app.models.admin import Admin
from app.models.billing_country import EnrollmentDocumentEvent
from app.models.rbac import (
    Permission,
    Role,
    role_permissions,
)
from app.models.tenant.schema import (
    Identity,
    TenantRole,
    TenantRolePermission,
)
from app.repositories.subscription_queries import base_select
from app.schemas.billing_country import (
    CountryDeclaration,
    CountryReview,
)
from app.schemas.enrollment import EnrollmentInput
from app.services.business.billing_country import BillingCountryService
from app.services.business.enrollment import EnrollmentService
from app.services.business.enrollment_documents import (
    WARNINGS,
    present_documents,
    publish_rehearsal_documents,
    require_document_rehearsal,
    require_document_responses,
    respond_to_document,
)
from app.services.business.tenant_foundation import tenant_unit_of_work

# ==============================================
# DEDICATED COUNTRY AND ENROLLMENT SCHEMA
# General collection reports these database cases separately instead of accepting ambient database credentials.
# ==============================================

pytestmark = pytest.mark.country_rehearsal

# ==============================================
# ATTESTED DISPOSABLE SESSION FACTORY
# Reattest using the same guard as the application; a production-shaped fixture cannot be admitted.
# ==============================================


@pytest.fixture(scope="module")
async def factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Use only the runner-owned O4 database and stop before writes on any identity mismatch."""
    engine = create_async_engine(
        os.environ["COUNTRY_BASE_TEST_URL"],
        hide_parameters=True,
        connect_args={"ssl": False},
    )
    result = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with result() as session, session.begin():
        await require_document_rehearsal(
            session=session, marker=os.environ["COUNTRY_BASE_TEST_MARKER"]
        )
        await publish_rehearsal_documents(
            session=session, marker=os.environ["COUNTRY_BASE_TEST_MARKER"]
        )
        role = await session.get(TenantRole, "owner")
        if role is None:
            session.add(TenantRole(code="owner", policy_revision=1))
            await session.flush()
        for permission in (
            "tenant.organization.read",
            "tenant.restaurants.read",
            "tenant.billing.read",
        ):
            existing = await session.scalar(
                base_select(TenantRolePermission).where(
                    TenantRolePermission.role_code == "owner",
                    TenantRolePermission.permission_code == permission,
                )
            )
            if existing is None:
                session.add(
                    TenantRolePermission(role_code="owner", permission_code=permission)
                )
    try:
        yield result
    finally:
        await engine.dispose()


# ==============================================
# EXPLICIT SYNTHETIC ACCOUNT SETUP
# The account's OIDC subject is the authority; the legacy compatibility number never acts as credentials.
# ==============================================


async def draft(
    *, factory: async_sessionmaker[AsyncSession]
) -> tuple[OIDCPrincipal, int]:
    """Commit a real dossier through the enrollment service and return its owned company reference."""
    principal = OIDCPrincipal(
        subject=uuid4().hex,
        issuer="https://local.test/realms/acceptance",
        realm_roles=frozenset(),
    )
    async with factory() as session, session.begin():
        session.add(
            Identity(
                issuer=principal.issuer,
                subject=principal.subject,
                status="active",
                revision=1,
            )
        )
        await session.flush()
        result = await EnrollmentService(
            session=session, marker=os.environ["COUNTRY_BASE_TEST_MARKER"]
        ).create(
            principal=principal,
            data=EnrollmentInput(
                company_name="Fictitious test company",
                legal_entity_reference="LOCAL-FAKE-" + principal.subject,
                full_name="Local test owner",
                phone="0000000000",
                restaurant_name="Local test restaurant",
                branch_name="Local test branch",
            ),
        )
    return principal, int(result["organization_id"])


async def reviewer(
    *, factory: async_sessionmaker[AsyncSession], permission: str
) -> OIDCPrincipal:
    """Assign exactly one test permission to a new synthetic platform account, with no inferred grant."""
    principal = OIDCPrincipal(
        subject=uuid4().hex,
        issuer="https://local.test/realms/acceptance",
        realm_roles=frozenset({"admin"}),
    )
    async with factory() as session, session.begin():
        role = Role(
            code="country-test-" + principal.subject,
            name="Synthetic country reviewer",
            is_active=True,
        )
        session.add(role)
        code = await session.scalar(
            base_select(Permission).where(Permission.code == permission)
        )
        if code is None:
            code = Permission(
                code=permission,
                name="Synthetic local permission",
                description="Synthetic local permission",
            )
            session.add(code)
        await session.flush()
        await session.execute(
            insert(role_permissions).values(role_id=role.id, permission_id=code.id)
        )
        session.add(
            Admin(
                chat_id=int(principal.subject[:12], 16),
                auth_subject=principal.subject,
                full_name="Synthetic country reviewer",
                role_id=role.id,
                is_active=True,
            )
        )
    return principal


async def declaration(
    *,
    factory: async_sessionmaker[AsyncSession],
    principal: OIDCPrincipal,
    organization: int,
) -> dict[str, object]:
    """Commit synthetic private evidence and a distinct pending declaration, with no automatic approval."""
    async with factory() as session, tenant_unit_of_work(session=session):
        service = BillingCountryService(session=session)
        evidence = await service.store_evidence(
            principal=principal,
            organization_id=organization,
            content=b"%PDF-1.4\nFICTITIOUS ESTABLISHMENT PROOF\n%%EOF",
            filename="LOCAL-FAKE.pdf",
            media_type="application/pdf",
            synthetic=True,
        )
        result = await service.declare(
            principal=principal,
            organization_id=organization,
            data=CountryDeclaration(
                declared_country="DZ",
                legal_entity_reference="LOCAL-FAKE-" + principal.subject,
                evidence_id=evidence,
                reason="Synthetic local initial declaration",
                expected_revision=1,
                idempotency_key=uuid4().hex,
            ),
        )
    return result


# ==============================================
# DOCUMENT LIFECYCLE AND LANGUAGE EVIDENCE
# Inspect from independent sessions so fixture rollback cannot hide missing internal persistence.
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("locale", ["fr", "en", "ar"])
async def test_document_presentation_and_optional_refusal(
    factory: async_sessionmaker[AsyncSession], locale: str
) -> None:
    """Retain each separate response; a refused optional choice does not block mandatory evidence."""
    principal, _organization = await draft(factory=factory)
    marker = os.environ["COUNTRY_BASE_TEST_MARKER"]
    async with factory() as session, session.begin():
        documents = await present_documents(
            session=session, principal=principal, marker=marker, locale=locale
        )
    assert len(documents) == 3
    for document in documents:
        assert WARNINGS[locale] in document["content"]
        action = {
            "acceptance": "accepted",
            "information": "acknowledged",
            "optional_consent": "declined",
        }[document["response_kind"]]
        async with factory() as session, session.begin():
            await respond_to_document(
                session=session,
                principal=principal,
                marker=marker,
                document_id=document["id"],
                version=document["version"],
                sha256=document["sha256"],
                locale=locale,
                action=action,
            )
    async with factory() as session, session.begin():
        await require_document_responses(
            session=session, principal=principal, marker=marker
        )
        events = (
            await session.scalars(
                base_select(EnrollmentDocumentEvent)
                .join(Identity, Identity.id == EnrollmentDocumentEvent.identity_id)
                .where(Identity.subject == principal.subject)
            )
        ).all()
        assert len(events) == 6
        assert {event.locale for event in events} == {locale}
        assert {event.event for event in events} == {
            "presented",
            "accepted",
            "acknowledged",
            "declined",
        }


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["missing", "unknown", "version", "sha256"])
async def test_changed_document_refused(
    factory: async_sessionmaker[AsyncSession], change: str
) -> None:
    """Unknown version or content is refused before any acceptance evidence can persist."""
    principal, _organization = await draft(factory=factory)
    marker = os.environ["COUNTRY_BASE_TEST_MARKER"]
    async with factory() as session, session.begin():
        documents = await present_documents(
            session=session, principal=principal, marker=marker, locale="fr"
        )
    document = documents[0]
    async with factory() as session:
        with pytest.raises(
            ValueError,
            match="enrollment_(document_version_unavailable|current_acceptance_required)",
        ):
            async with session.begin():
                if change == "missing":
                    await require_document_responses(
                        session=session, principal=principal, marker=marker
                    )
                else:
                    await respond_to_document(
                        session=session,
                        principal=principal,
                        marker=marker,
                        document_id=99999999 if change == "unknown" else document["id"],
                        version=(
                            "unknown" if change == "version" else document["version"]
                        ),
                        sha256="0" * 64 if change == "sha256" else document["sha256"],
                        locale="fr",
                        action="accepted",
                    )
    async with factory() as session:
        assert (
            await session.scalar(
                text(
                    "SELECT count(*) FROM enrollment_document_events e JOIN identities i ON i.id=e.identity_id WHERE i.subject=:subject AND event<>'presented'"
                ),
                {"subject": principal.subject},
            )
            == 0
        )


@pytest.mark.asyncio
async def test_wrong_local_marker_refused(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    """Even on loopback, an unowned copied marker cannot activate fictitious documents."""
    async with factory() as session:
        with pytest.raises(ValueError, match="local_only"):
            await require_document_rehearsal(session=session, marker="0" * 32)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE enrollment_documents SET contents='{}'::jsonb WHERE id=1",
        "DELETE FROM enrollment_documents WHERE id=1",
        "TRUNCATE enrollment_document_events",
    ],
)
async def test_retained_documents_cannot_be_rewritten(
    factory: async_sessionmaker[AsyncSession], statement: str
) -> None:
    """Database guards retain exact old content and responses independently of application code."""
    async with factory() as session, session.begin():
        with pytest.raises(DBAPIError):
            async with session.begin_nested():
                await session.execute(text(statement))


# ==============================================
# DISTINCT COUNTRY AUTHORITY AND CONCURRENT REVIEW
# A role label, pricing permission or payment permission cannot approve a declared country.
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "permission",
    [
        "subscriptions.pricing.manage",
        "payments.review",
        "restaurants.manage",
        "admins.manage",
    ],
)
async def test_other_platform_grants_cannot_approve_country(
    factory: async_sessionmaker[AsyncSession], permission: str
) -> None:
    """Refuse direct service review under an unrelated exact grant, leaving the request pending."""
    principal, organization = await draft(factory=factory)
    state = await declaration(
        factory=factory, principal=principal, organization=organization
    )
    unauthorized = await reviewer(factory=factory, permission=permission)
    async with factory() as session, session.begin():
        with pytest.raises(HTTPException) as caught:
            await BillingCountryService(session=session).review(
                principal=unauthorized,
                request_id=state["requests"][0]["id"],
                data=CountryReview(
                    decision="approve",
                    expected_revision=state["revision"],
                    justification="Synthetic verification",
                    evidence_checked=True,
                    same_legal_entity=True,
                ),
            )
        assert caught.value.status_code == 403
    async with factory() as session:
        assert (
            await session.scalar(
                text(
                    "SELECT count(*) FROM billing_country_decisions WHERE organization_id=:id"
                ),
                {"id": organization},
            )
            == 0
        )


@pytest.mark.asyncio
async def test_country_approval_is_single_and_does_not_grant_trial(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    """Serialize competing reviewers; approving country alone creates no owner, restaurant or subscription."""
    principal, organization = await draft(factory=factory)
    state = await declaration(
        factory=factory, principal=principal, organization=organization
    )
    authorized = await reviewer(
        factory=factory, permission="tenant.billing_country.manage"
    )

    async def attempt() -> str:
        """Use one independent transaction per competing human decision."""
        async with factory() as session:
            try:
                async with session.begin():
                    await BillingCountryService(session=session).review(
                        principal=authorized,
                        request_id=state["requests"][0]["id"],
                        data=CountryReview(
                            decision="approve",
                            expected_revision=state["revision"],
                            justification="Synthetic official evidence checked",
                            evidence_checked=True,
                            same_legal_entity=True,
                        ),
                    )
                return "committed"
            except ValueError as error:
                assert str(error) == "billing_country_review_changed"
                return "stale"

    assert sorted(await asyncio.gather(attempt(), attempt())) == ["committed", "stale"]
    async with factory() as session:
        assert (
            await session.scalar(
                text(
                    "SELECT count(*) FROM billing_country_decisions WHERE organization_id=:id"
                ),
                {"id": organization},
            )
            == 1
        )
        assert (
            await session.scalar(
                text("SELECT count(*) FROM restaurants WHERE organization_id=:id"),
                {"id": organization},
            )
            == 0
        )
        assert (
            await session.scalar(
                text("SELECT status FROM organizations WHERE id=:id"),
                {"id": organization},
            )
            == "draft"
        )


# ==============================================
# COMPLETE ATOMIC ENROLLMENT
# A valid country does not bypass current documents; completed retries retain one trial and one establishment.
# ==============================================


async def accept_required(
    *, factory: async_sessionmaker[AsyncSession], principal: OIDCPrincipal
) -> None:
    """Record separate explicit actions, including optional refusal, through the real document service."""
    marker = os.environ["COUNTRY_BASE_TEST_MARKER"]
    async with factory() as session, session.begin():
        documents = await present_documents(
            session=session, principal=principal, marker=marker, locale="fr"
        )
        for document in documents:
            await respond_to_document(
                session=session,
                principal=principal,
                marker=marker,
                document_id=document["id"],
                version=document["version"],
                sha256=document["sha256"],
                locale="fr",
                action={
                    "acceptance": "accepted",
                    "information": "acknowledged",
                    "optional_consent": "declined",
                }[document["response_kind"]],
            )


@pytest.mark.asyncio
async def test_enrollment_requires_country_before_creations(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    """A mandatory-document response is not evidence that the country has been approved."""
    principal, organization = await draft(factory=factory)
    await accept_required(factory=factory, principal=principal)
    async with factory() as session:
        with pytest.raises(ValueError, match="validated_country_required"):
            async with session.begin():
                await EnrollmentService(
                    session=session, marker=os.environ["COUNTRY_BASE_TEST_MARKER"]
                ).finalize(principal=principal)
    async with factory() as session:
        assert (
            await session.scalar(
                text("SELECT count(*) FROM restaurants WHERE organization_id=:id"),
                {"id": organization},
            )
            == 0
        )
        assert (
            await session.scalar(
                text("SELECT count(*) FROM owners WHERE auth_subject=:subject"),
                {"subject": principal.subject},
            )
            == 0
        )


@pytest.mark.asyncio
async def test_complete_trial_enrollment_and_repeated_finalization(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    """Observe the committed company, first branch, membership, trial and consumed right from an independent session."""
    principal, organization = await draft(factory=factory)
    await accept_required(factory=factory, principal=principal)
    state = await declaration(
        factory=factory, principal=principal, organization=organization
    )
    authorized = await reviewer(
        factory=factory, permission="tenant.billing_country.manage"
    )
    async with factory() as session, session.begin():
        await BillingCountryService(session=session).review(
            principal=authorized,
            request_id=state["requests"][0]["id"],
            data=CountryReview(
                decision="approve",
                expected_revision=state["revision"],
                justification="Fictitious proof explicitly reviewed",
                evidence_checked=True,
                same_legal_entity=True,
            ),
        )
    for _attempt in range(2):
        async with factory() as session, session.begin():
            result = await EnrollmentService(
                session=session, marker=os.environ["COUNTRY_BASE_TEST_MARKER"]
            ).finalize(principal=principal)
            assert result["status"] == "completed"
    async with factory() as session:
        assert (
            await session.scalar(
                text("SELECT status FROM organizations WHERE id=:id"),
                {"id": organization},
            )
            == "active"
        )
        assert (
            await session.scalar(
                text("SELECT count(*) FROM restaurants WHERE organization_id=:id"),
                {"id": organization},
            )
            == 1
        )
        assert (
            await session.scalar(
                text(
                    "SELECT count(*) FROM branches b JOIN restaurants r ON r.id=b.restaurant_id WHERE r.organization_id=:id"
                ),
                {"id": organization},
            )
            == 1
        )
        assert (
            await session.scalar(
                text(
                    "SELECT count(*) FROM subscriptions s JOIN restaurants r ON r.id=s.restaurant_id WHERE r.organization_id=:id AND s.status='trial'"
                ),
                {"id": organization},
            )
            == 1
        )
        assert (
            await session.scalar(
                text("SELECT trial_used FROM owners WHERE auth_subject=:subject"),
                {"subject": principal.subject},
            )
            is True
        )
        assert (
            await session.scalar(
                text(
                    "SELECT count(*) FROM organization_memberships WHERE organization_id=:id AND status='active' AND role_code='owner'"
                ),
                {"id": organization},
            )
            == 1
        )
