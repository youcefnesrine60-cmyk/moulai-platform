# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# CLOSED ENROLLMENT AND PRODUCTION REFUSAL
# Verify local-document admission and immutable content contracts without making any database or provider connection.
# ==============================================

"""Offline guards supplement real PostgreSQL and browser proofs; they do not establish an operational identity flow."""

import asyncio
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.schemas.enrollment import (
    DocumentResponseInput,
    EnrollmentInput,
)
from app.services.business.enrollment_documents import (
    WARNINGS,
    document_digest,
    require_document_rehearsal,
)
from scripts.prepare_operational_o4 import canonical_text_arrays
from test_support.local_postgres import (
    LocalPostgresNetworkGuard,
    LocalPostgresSettings,
    validate_local_test_url,
)

# ==============================================
# PRODUCTION DOES NOT REACH SQL
# A production flag must reject fictitious documents even before a database can answer the local attestation query.
# ==============================================


def test_production_refuses_fictitious_documents_before_io(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A visual warning or supplied marker cannot override the server environment boundary."""
    monkeypatch.setattr(settings, "APP_ENV", "production")
    session = AsyncMock(spec=AsyncSession)
    with pytest.raises(ValueError, match="local_only"):
        asyncio.run(require_document_rehearsal(session=session, marker="a" * 32))
    session.execute.assert_not_awaited()


# ==============================================
# EXACT CONTENT IDENTITY
# All languages must contain the approved test warning, and changing any text changes the retained evidence hash.
# ==============================================


def test_document_hash_preserves_languages_and_content() -> None:
    """JSON key order is irrelevant; missing language or warning and changed content cannot pass silently."""
    contents = dict(WARNINGS)
    expected = document_digest(contents=contents)
    assert document_digest(contents=dict(reversed(list(contents.items())))) == expected
    assert (
        document_digest(contents={**contents, "fr": contents["fr"] + "\nversion 2"})
        != expected
    )
    with pytest.raises(ValueError, match="warning_or_language_missing"):
        document_digest(contents={"fr": WARNINGS["fr"]})
    with pytest.raises(ValueError, match="warning_or_language_missing"):
        document_digest(contents={**contents, "en": "approved legal contract"})


# ==============================================
# NO GLOBAL CONSENT OR CALLER AUTHORITY
# Closed schemas keep identity, rights and trial eligibility outside owner input.
# ==============================================


@pytest.mark.parametrize(
    "forbidden",
    [
        "owner_id",
        "identity_id",
        "validated_country",
        "role",
        "trial_used",
        "accept_all",
    ],
)
def test_enrollment_cannot_select_authority(forbidden: str) -> None:
    """Extra fields are rejected before any service may create a business graph."""
    with pytest.raises(ValidationError):
        EnrollmentInput.model_validate(
            {
                "company_name": "Local test",
                "legal_entity_reference": "LOCAL-FAKE",
                "full_name": "Local owner",
                "phone": "0000",
                "restaurant_name": "Local restaurant",
                "branch_name": "Local branch",
                forbidden: True,
            }
        )


@pytest.mark.parametrize(
    "change",
    [
        {"version": ""},
        {"document_id": 0},
        {"sha256": "unknown"},
        {"action": "accept_all"},
        {"locale": "dz"},
        {"identity_id": 1},
    ],
)
def test_document_response_requires_exact_separate_contract(
    change: dict[str, object],
) -> None:
    """Unknown versions and actions cannot be represented as a blanket acceptance."""
    with pytest.raises(ValidationError):
        DocumentResponseInput.model_validate(
            {
                "document_id": 1,
                "version": "LOCAL-TEST-v1",
                "sha256": "a" * 64,
                "locale": "fr",
                "action": "accepted",
                **change,
            }
        )


# ==============================================
# NARROW POSTGRESQL DEPARSE NORMALIZATION
# Equivalent array casts may compare equally, but changed states, operators and validation clauses must remain different.
# ==============================================


def test_alternate_local_test_port_is_explicit_and_exclusive() -> None:
    """Keep the old review unreachable to the new test guard and reject a port mismatch before opening any socket."""
    url = (
        "postgresql+asyncpg://moulai_pytest:"
        + "a" * 32
        + "@127.0.0.1:55435/moulai_pytest"
    )
    with pytest.raises(ValueError, match="not_allowlisted"):
        validate_local_test_url(value=url)
    configuration = LocalPostgresSettings(
        CLIENT_PORT=55435, URL=url, INSTANCE_ID="a" * 32, SERVER_PORT=55435
    )
    assert configuration.CLIENT_PORT == 55435
    guard = LocalPostgresNetworkGuard(client_port=55435)
    guard("socket.connect", (None, ("127.0.0.1", 55435)))
    for port in (55432, 55433, 55434, 5432):
        with pytest.raises(RuntimeError):
            guard("socket.connect", (None, ("127.0.0.1", port)))


# ==============================================
# CHANGED EXPRESSIONS STILL FAIL
# A narrow normalization never equates changed state values, operators or NOT VALID clauses.
# ==============================================


@pytest.mark.parametrize("change", ["literal", "operator", "not_valid"])
def test_restore_normalization_does_not_hide_semantic_change(change: str) -> None:
    """Use only the observed literal-array cast equivalence; preserve actual integrity changes."""
    original = "CHECK (status::text = ANY (ARRAY['trial'::character varying, 'active'::character varying]::text[]))"
    restored = "CHECK (status::text = ANY (ARRAY['trial'::character varying::text, 'active'::character varying::text]))"
    assert canonical_text_arrays(definition=original) == canonical_text_arrays(
        definition=restored
    )
    altered = (
        restored.replace("'trial'", "'pending'")
        if change == "literal"
        else (
            restored.replace(" = ANY", " <> ALL")
            if change == "operator"
            else restored + " NOT VALID"
        )
    )
    assert canonical_text_arrays(definition=original) != canonical_text_arrays(
        definition=altered
    )
