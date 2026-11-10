# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# LOCAL ENROLLMENT DOCUMENT EVIDENCE
# Separate presentation, contractual acceptance, information and optional choices without creating legal approval.
# ==============================================

"""Attested local-only fictitious documents with immutable content and account-scoped evidence."""

from __future__ import annotations

# isort: split
# ==============================================
# DOCUMENT AND IDENTITY CONTRACTS
# Read the authenticated identity and actual database identity before admitting any test document.
# ==============================================

import hashlib
import json
import os
import re
from datetime import (
    datetime,
    timezone,
)
from pathlib import Path
from typing import Literal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security.oidc import OIDCPrincipal
from app.core.security.tenant_types import TenantAccessDenied
from app.models.billing_country import (
    EnrollmentDocument,
    EnrollmentDocumentEvent,
    EnrollmentDossier,
)
from app.models.tenant.schema import Identity
from app.repositories.subscription_queries import base_select
from app.services.business.subscription_types import JsonValue

WARNINGS = {
    "fr": "DOCUMENT FICTIF DE RECETTE — SANS VALEUR CONTRACTUELLE — NE PAS UTILISER EN PRODUCTION",
    "en": "FICTITIOUS ACCEPTANCE TEST DOCUMENT — NO CONTRACTUAL VALUE — DO NOT USE IN PRODUCTION",
    "ar": "وثيقة وهمية للاختبار — دون أي قيمة تعاقدية — يُمنع استخدامها في بيئة الإنتاج",
}

# ==============================================
# LIVE LOCAL ATTESTATION
# Parameters alone cannot authorize synthetic content against a remote or unmarked database.
# ==============================================


async def require_document_rehearsal(*, session: AsyncSession, marker: str) -> None:
    """Refuse production, an unknown marker, role, database, address, port or migration revision."""
    if settings.APP_ENV == "staging":
        from app.staging.target import StagingTarget

        if os.environ.get("MOULAI_STAGING_SYNTHETIC_ONLY") != "true":
            raise ValueError("fictitious_enrollment_documents_local_only")
        target = StagingTarget.load(path=Path(os.environ["MOULAI_STAGING_TARGET_FILE"]))
        if marker != target.instance_id:
            raise ValueError("enrollment_local_marker_required")
        await session.run_sync(
            lambda sync: target.attest(
                connection=sync.connection(), migration=False, require_revision=True
            )
        )
        return
    if settings.APP_ENV not in {"development", "test"}:
        raise ValueError("fictitious_enrollment_documents_local_only")
    if re.fullmatch(r"[0-9a-f]{32}", marker) is None:
        raise ValueError("enrollment_local_marker_required")
    row = (
        await session.execute(
            text(
                "SELECT current_database(),current_user,host(inet_server_addr()),inet_server_port(),"
                "shobj_description(oid,'pg_database') FROM pg_database WHERE datname=current_database()"
            )
        )
    ).one()
    allowed = {
        (
            "moulai_integrated",
            "moulai_integrated",
            "127.0.0.1",
            55433,
            "moulai-operational-local:" + marker,
        ),
        (
            "moulai_base_rehearsal",
            "moulai_base_rehearsal",
            "127.0.0.1",
            55434,
            "moulai-country-base:" + marker,
        ),
    }
    if (
        tuple(row) not in allowed
        or await session.scalar(text("SELECT version_num FROM public.alembic_version"))
        != "o420261108"
    ):
        raise ValueError("fictitious_enrollment_documents_local_only")


# ==============================================
# CANONICAL RETAINED CONTENT
# The same hash covers all language versions; formatting never substitutes another text for accepted evidence.
# ==============================================


def document_digest(*, contents: dict[str, JsonValue]) -> str:
    """Hash exact FR/EN/AR strings under one deterministic JSON representation."""
    if set(contents) != set(WARNINGS) or any(
        not isinstance(contents[locale], str)
        or WARNINGS[locale] not in str(contents[locale])
        for locale in WARNINGS
    ):
        raise ValueError("fictitious_document_warning_or_language_missing")
    return hashlib.sha256(
        json.dumps(
            contents, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


# ==============================================
# EXPLICIT TEST REGISTRY INITIALIZATION
# Initialization is a local operator action, never a migration seed or an implicit production fallback.
# ==============================================


async def publish_rehearsal_documents(*, session: AsyncSession, marker: str) -> None:
    """Install only test-owned versions; never overwrite existing content or legal decisions."""
    await require_document_rehearsal(session=session, marker=marker)
    definitions = (
        (
            "test-contract",
            "acceptance",
            True,
            {
                "fr": "J’accepte uniquement les conditions fictives de cette recette locale.",
                "en": "I accept only the fictitious terms of this local acceptance test.",
                "ar": "أوافق فقط على الشروط الوهمية لهذا الاختبار المحلي.",
            },
        ),
        (
            "test-data-information",
            "information",
            True,
            {
                "fr": "Information fictive : cette recette utilise un compte et des documents de développement, sans dossier client réel.",
                "en": "Test information: this rehearsal uses a development account and documents, with no real customer file.",
                "ar": "معلومة للاختبار: يُستخدم حساب ووثائق للتطوير، دون أي ملف لزبون حقيقي.",
            },
        ),
        (
            "test-optional-communications",
            "optional_consent",
            False,
            {
                "fr": "Choix facultatif fictif de communications : aucun message ne sera envoyé.",
                "en": "Fictitious optional communications choice: no message will be sent.",
                "ar": "اختيار وهمي واختياري لتلقي المراسلات: لن تُرسل أي رسالة.",
            },
        ),
    )
    for purpose, kind, required, translations in definitions:
        version = "LOCAL-TEST-20261108-v1"
        contents: dict[str, JsonValue] = {
            locale: WARNINGS[locale]
            + "\n"
            + purpose
            + " / "
            + version
            + "\n"
            + translations[locale]
            for locale in WARNINGS
        }
        digest = document_digest(contents=contents)
        existing = await session.scalar(
            base_select(EnrollmentDocument).where(
                EnrollmentDocument.purpose == purpose,
                EnrollmentDocument.version == version,
            )
        )
        if existing is not None:
            if (
                existing.sha256 != digest
                or existing.contents != contents
                or existing.response_kind != kind
                or existing.required != required
                or not existing.synthetic
            ):
                raise ValueError("enrollment_test_document_version_conflict")
            continue
        session.add(
            EnrollmentDocument(
                purpose=purpose,
                version=version,
                response_kind=kind,
                contents=contents,
                sha256=digest,
                required=required,
                synthetic=True,
                published_at=datetime.now(timezone.utc),
            )
        )
    await session.flush()


# ==============================================
# CURRENT DOCUMENT PRESENTATION
# A verified account receives only published versions, and presentation is not acceptance.
# ==============================================


async def dossier_identity(
    *, session: AsyncSession, principal: OIDCPrincipal, lock: bool = False
) -> EnrollmentDossier:
    """Resolve the exact issuer/subject; never accept a client-supplied identity or dossier owner."""
    statement = (
        base_select(EnrollmentDossier)
        .join(Identity, Identity.id == EnrollmentDossier.identity_id)
        .where(
            Identity.issuer == principal.issuer,
            Identity.subject == principal.subject,
            Identity.status == "active",
        )
    )
    if lock:
        statement = statement.with_for_update(of=EnrollmentDossier)
    dossier = await session.scalar(statement)
    if dossier is None:
        raise TenantAccessDenied("enrollment_dossier_unavailable")
    return dossier


async def present_documents(
    *,
    session: AsyncSession,
    principal: OIDCPrincipal,
    marker: str,
    locale: Literal["fr", "en", "ar"],
) -> list[dict[str, JsonValue]]:
    """Retain the exact account, document hash, locale and presentation instant in the caller transaction."""
    await require_document_rehearsal(session=session, marker=marker)
    dossier = await dossier_identity(session=session, principal=principal, lock=True)
    now = datetime.now(timezone.utc)
    documents = (
        await session.scalars(
            base_select(EnrollmentDocument)
            .where(
                EnrollmentDocument.retired_at.is_(None),
                EnrollmentDocument.published_at <= now,
            )
            .order_by(EnrollmentDocument.id)
        )
    ).all()
    if not documents:
        raise ValueError("enrollment_documents_not_published")
    result: list[dict[str, JsonValue]] = []
    for document in documents:
        if not document.synthetic or document.sha256 != document_digest(
            contents=document.contents
        ):
            raise ValueError("enrollment_document_content_invalid")
        existing = await session.scalar(
            base_select(EnrollmentDocumentEvent).where(
                EnrollmentDocumentEvent.dossier_id == dossier.id,
                EnrollmentDocumentEvent.document_id == document.id,
                EnrollmentDocumentEvent.locale == locale,
                EnrollmentDocumentEvent.event == "presented",
            )
        )
        if existing is None:
            session.add(
                EnrollmentDocumentEvent(
                    dossier_id=dossier.id,
                    identity_id=dossier.identity_id,
                    document_id=document.id,
                    locale=locale,
                    document_sha256=document.sha256,
                    event="presented",
                )
            )
        responses = (
            await session.scalars(
                base_select(EnrollmentDocumentEvent).where(
                    EnrollmentDocumentEvent.dossier_id == dossier.id,
                    EnrollmentDocumentEvent.document_id == document.id,
                    EnrollmentDocumentEvent.event != "presented",
                )
            )
        ).all()
        if len(responses) > 1:
            raise ValueError("enrollment_document_response_ambiguous")
        recorded = responses[0] if responses else None
        result.append(
            {
                "id": document.id,
                "purpose": document.purpose,
                "version": document.version,
                "locale": locale,
                "content": document.contents[locale],
                "sha256": document.sha256,
                "response_kind": document.response_kind,
                "required": document.required,
                "synthetic": True,
                "response": recorded.event if recorded else None,
                "response_locale": recorded.locale if recorded else None,
                "response_at": recorded.occurred_at.isoformat() if recorded else None,
            }
        )
    await session.flush()
    return result


# ==============================================
# EXPLICIT DOCUMENT RESPONSE
# Refuse unknown, absent, retired or unpresented versions and distinguish each response purpose.
# ==============================================


async def respond_to_document(
    *,
    session: AsyncSession,
    principal: OIDCPrincipal,
    marker: str,
    document_id: int,
    version: str,
    sha256: str,
    locale: Literal["fr", "en", "ar"],
    action: Literal["accepted", "acknowledged", "declined"],
) -> None:
    """Persist a separate deliberate action; optional refusal never becomes a blocking requirement."""
    await require_document_rehearsal(session=session, marker=marker)
    dossier = await dossier_identity(session=session, principal=principal, lock=True)
    document = await session.scalar(
        base_select(EnrollmentDocument)
        .where(EnrollmentDocument.id == document_id)
        .with_for_update(read=True)
    )
    now = datetime.now(timezone.utc)
    if (
        document is None
        or document.retired_at is not None
        or document.published_at > now
        or document.version != version
        or document.sha256 != sha256
        or not document.synthetic
        or document_digest(contents=document.contents) != sha256
    ):
        raise ValueError("enrollment_document_version_unavailable")
    allowed = {
        "acceptance": {"accepted"},
        "information": {"acknowledged"},
        "optional_consent": {"accepted", "declined"},
    }
    if action not in allowed[document.response_kind]:
        raise ValueError("enrollment_document_action_invalid")
    events = (
        await session.scalars(
            base_select(EnrollmentDocumentEvent).where(
                EnrollmentDocumentEvent.dossier_id == dossier.id,
                EnrollmentDocumentEvent.document_id == document.id,
            )
        )
    ).all()
    if not any(
        event.event == "presented"
        and event.locale == locale
        and event.document_sha256 == sha256
        for event in events
    ):
        raise ValueError("enrollment_document_not_presented")
    responses = [event for event in events if event.event != "presented"]
    if responses:
        if any(event.event != action or event.locale != locale for event in responses):
            raise ValueError("enrollment_document_response_already_recorded")
        return
    session.add(
        EnrollmentDocumentEvent(
            dossier_id=dossier.id,
            identity_id=dossier.identity_id,
            document_id=document.id,
            locale=locale,
            document_sha256=sha256,
            event=action,
        )
    )
    await session.flush()


# ==============================================
# FINALIZATION EVIDENCE GATE
# A newly published version requires a new action; old events remain unchanged and cannot grant current acceptance.
# ==============================================


async def require_document_responses(
    *, session: AsyncSession, principal: OIDCPrincipal, marker: str
) -> None:
    """Refuse missing current mandatory responses; ignore refusal or omission of an optional choice."""
    await require_document_rehearsal(session=session, marker=marker)
    dossier = await dossier_identity(session=session, principal=principal, lock=True)
    documents = (
        await session.scalars(
            base_select(EnrollmentDocument)
            .where(
                EnrollmentDocument.retired_at.is_(None),
                EnrollmentDocument.required.is_(True),
                EnrollmentDocument.published_at <= datetime.now(timezone.utc),
            )
            .with_for_update(read=True)
        )
    ).all()
    if {document.response_kind for document in documents} != {
        "acceptance",
        "information",
    }:
        raise ValueError("enrollment_required_documents_missing")
    for document in documents:
        if not document.synthetic or document.sha256 != document_digest(
            contents=document.contents
        ):
            raise ValueError("enrollment_document_content_invalid")
        event = await session.scalar(
            base_select(EnrollmentDocumentEvent)
            .with_only_columns(EnrollmentDocumentEvent.id)
            .where(
                EnrollmentDocumentEvent.dossier_id == dossier.id,
                EnrollmentDocumentEvent.identity_id == dossier.identity_id,
                EnrollmentDocumentEvent.document_id == document.id,
                EnrollmentDocumentEvent.document_sha256 == document.sha256,
                EnrollmentDocumentEvent.event
                == (
                    "accepted"
                    if document.response_kind == "acceptance"
                    else "acknowledged"
                ),
            )
        )
        if event is None:
            raise ValueError("enrollment_current_acceptance_required")
