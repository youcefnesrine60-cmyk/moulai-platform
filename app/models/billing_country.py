# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# OWNED BILLING COUNTRY AND ENROLLMENT MODELS
# Map O4's explicit evidence and decisions without creating DDL or implicit relationships.
# ==============================================

"""The reviewed migration owns cross-metadata tenant foreign keys and immutable-history triggers."""

from __future__ import annotations

# isort: split
# ==============================================
# EXACT PERSISTENCE CONTRACTS
# Keep private document bytes separate from public projections and preserve UTC decision dates.
# ==============================================

from datetime import datetime

from pydantic import JsonValue
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Integer,
    LargeBinary,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from app.models.base import Base

# ==============================================
# SERIALIZED ORGANIZATION COUNTRY PROFILE
# The revision coordinates requests and decisions without storing another unversioned validated country.
# ==============================================


class BillingCountryProfile(Base):
    """One lockable revision per organization; decisions are the authoritative validated history."""

    __tablename__ = "billing_country_profiles"
    organization_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    revision: Mapped[int] = mapped_column(BigInteger, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# ==============================================
# PRIVATE SYNTHETIC REHEARSAL EVIDENCE
# Content is served only after identity/permission checks; no public static file path is retained.
# ==============================================


class BillingCountryEvidence(Base):
    """Local test documents only until a real-data retention policy is approved."""

    __tablename__ = "billing_country_evidence"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    organization_id: Mapped[int] = mapped_column(Integer)
    submitted_identity_id: Mapped[int] = mapped_column(Integer)
    filename: Mapped[str] = mapped_column(String(180))
    media_type: Mapped[str] = mapped_column(String(80))
    content: Mapped[bytes] = mapped_column(LargeBinary, deferred=True)
    sha256: Mapped[str] = mapped_column(String(64))
    synthetic: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# ==============================================
# DECLARED COUNTRY AND REVIEW REQUEST
# Preserve the declared country independently from any administrative decision.
# ==============================================


class BillingCountryRequest(Base):
    """An immutable request payload whose review status changes under its profile lock."""

    __tablename__ = "billing_country_requests"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    organization_id: Mapped[int] = mapped_column(Integer)
    submitted_identity_id: Mapped[int] = mapped_column(Integer)
    declared_country: Mapped[str] = mapped_column(String(2))
    legal_entity_reference: Mapped[str] = mapped_column(String(180))
    reason: Mapped[str] = mapped_column(Text)
    evidence_id: Mapped[str] = mapped_column(String(32))
    expected_revision: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(24))
    idempotency_key: Mapped[str] = mapped_column(String(80))
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# ==============================================
# RETAINED ADMINISTRATIVE COUNTRY DECISION
# An account deletion cannot cascade through this history or change a purchased period.
# ==============================================


class BillingCountryDecision(Base):
    """Validated country with its exact proof, author and future renewal effective instant."""

    __tablename__ = "billing_country_decisions"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    organization_id: Mapped[int] = mapped_column(Integer)
    request_id: Mapped[int] = mapped_column(BigInteger)
    previous_country: Mapped[str | None] = mapped_column(String(2))
    validated_country: Mapped[str] = mapped_column(String(2))
    legal_entity_reference: Mapped[str] = mapped_column(String(180))
    evidence_id: Mapped[str] = mapped_column(String(32))
    author_admin_id: Mapped[int] = mapped_column(Integer)
    justification: Mapped[str] = mapped_column(Text)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    profile_revision: Mapped[int] = mapped_column(BigInteger)


# ==============================================
# VERSIONED PRESENTED DOCUMENT
# Only explicitly published test content may be used in the isolated enrollment rehearsal.
# ==============================================


class EnrollmentDocument(Base):
    """Purpose, language content and hash distinguish acceptance from information and optional consent."""

    __tablename__ = "enrollment_documents"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    purpose: Mapped[str] = mapped_column(String(40))
    version: Mapped[str] = mapped_column(String(80))
    response_kind: Mapped[str] = mapped_column(String(30))
    contents: Mapped[dict[str, JsonValue]] = mapped_column(JSONB)
    sha256: Mapped[str] = mapped_column(String(64))
    required: Mapped[bool] = mapped_column(Boolean)
    synthetic: Mapped[bool] = mapped_column(Boolean)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# ==============================================
# SELF-SERVICE ENROLLMENT DOSSIER
# Link the authenticated identity to existing registration services and one stable draft company.
# ==============================================


class EnrollmentDossier(Base):
    """The CLI is not involved in creating this company or first establishment."""

    __tablename__ = "enrollment_dossiers"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    identity_id: Mapped[int] = mapped_column(Integer)
    organization_id: Mapped[int] = mapped_column(Integer)
    registration_request_id: Mapped[int] = mapped_column(Integer)
    legal_entity_reference: Mapped[str] = mapped_column(String(180))
    branch_name: Mapped[str] = mapped_column(String(180))
    status: Mapped[str] = mapped_column(String(30))
    revision: Mapped[int] = mapped_column(BigInteger, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    restaurant_id: Mapped[int | None] = mapped_column(Integer)


# ==============================================
# DOCUMENT PRESENTATION AND RESPONSE EVIDENCE
# A record of presentation is distinct from an explicit acceptance or optional refusal.
# ==============================================


class EnrollmentDocumentEvent(Base):
    """Retain the account, document/version hash, language, response type and occurrence time."""

    __tablename__ = "enrollment_document_events"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    dossier_id: Mapped[int] = mapped_column(BigInteger)
    identity_id: Mapped[int] = mapped_column(Integer)
    document_id: Mapped[int] = mapped_column(BigInteger)
    locale: Mapped[str] = mapped_column(String(2))
    document_sha256: Mapped[str] = mapped_column(String(64))
    event: Mapped[str] = mapped_column(String(16))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
