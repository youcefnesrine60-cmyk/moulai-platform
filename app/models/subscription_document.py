# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# IMMUTABLE SAAS DOCUMENT MODELS
# Map issued financial snapshots and append-only decisions without loading bank evidence or mutable catalogue data.
# ==============================================

"""O5 migration owns foreign keys and database history guards, including cross-metadata organization links."""

from __future__ import annotations

# isort: split
# ==============================================
# TYPED PERSISTENCE CONTRACT
# UTC issuance and decision timestamps remain distinct from the retained service period.
# ==============================================

from datetime import datetime

from pydantic import JsonValue
from sqlalchemy import (
    BigInteger,
    DateTime,
    Integer,
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
# RETAINED ISSUED VERSION
# Scope and financial source identifiers are frozen with the exact content and its digest.
# ==============================================


class SubscriptionDocument(Base):
    """An immutable version; invalidation is represented by a separate retained event."""

    __tablename__ = "subscription_documents"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(43))
    organization_id: Mapped[int] = mapped_column(Integer)
    restaurant_id: Mapped[int] = mapped_column(Integer)
    payment_id: Mapped[int] = mapped_column(Integer)
    subscription_id: Mapped[int] = mapped_column(Integer)
    snapshot_id: Mapped[int] = mapped_column(Integer)
    version: Mapped[int] = mapped_column(Integer)
    replaces_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    content: Mapped[dict[str, JsonValue]] = mapped_column(JSONB)
    sha256: Mapped[str] = mapped_column(String(64))
    author_admin_id: Mapped[int] = mapped_column(Integer)
    author_name: Mapped[str] = mapped_column(String(255))
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# ==============================================
# APPEND-ONLY DOCUMENT DECISIONS
# Author snapshots survive account deletion and never confer authority to later callers.
# ==============================================


class SubscriptionDocumentEvent(Base):
    """One issuance and at most one invalidation per version, without financial side effects."""

    __tablename__ = "subscription_document_events"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    document_id: Mapped[int] = mapped_column(BigInteger)
    event: Mapped[str] = mapped_column(String(16))
    author_admin_id: Mapped[int] = mapped_column(Integer)
    author_name: Mapped[str] = mapped_column(String(255))
    reason: Mapped[str] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
