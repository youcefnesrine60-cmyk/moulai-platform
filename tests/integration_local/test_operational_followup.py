# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================


# ==============================================
# LOCAL FOLLOWUP SAFETY REGRESSIONS
# Check explicit payment parameters, encrypted draft isolation and database-clock writes.
# ==============================================

"""Offline tests make no network, database, provider or microphone call."""

from __future__ import annotations

# isort: split
# ==============================================
# EXPLICIT TEST DEPENDENCIES
# Use temporary encrypted files and verified-value doubles, never ambient credentials.
# ==============================================

import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError

from app.integration import sessions
from app.integration.sessions import BrowserSessions
from app.repositories.admin import admin_repo
from app.schemas.enrollment import EnrollmentDraftInput
from app.services.business.pricing_service import calculate_payment_adjustment

# ==============================================
# APPROVED PAYMENT BASIS AND EXACT PRECISION
# Verify the configured rate applies to the supplied pre-payment amount, never B.
# ==============================================


@pytest.mark.parametrize(
    "amount,method,expected",
    [
        ("3000", "electronic", "-60"),
        ("10000", "electronic", "-200"),
        ("3500.1234", "electronic", "-70.002468"),
        ("10000", "cash", "200"),
    ],
)
def test_configured_adjustment(*, amount: str, method: str, expected: str) -> None:
    """No intermediate rounding and no implicit modification of a separate B value."""
    base = Decimal(3000)
    assert calculate_payment_adjustment(
        amount=Decimal(amount),
        payment_method=method,
        rates={"electronic": "-0.02", "cash": "0.02"},
    ) == Decimal(expected)
    assert base == Decimal(3000)


# ==============================================
# MISSING OR INVALID PAYMENT PARAMETERS
# Configuration omissions and wrong signs cannot silently choose a default rate.
# ==============================================


@pytest.mark.parametrize(
    "rates",
    [
        {},
        {"electronic": "-0.02"},
        {"electronic": "NaN", "cash": "0.02"},
        {"electronic": "invalid", "cash": "0.02"},
        {"electronic": "0.02", "cash": "0.02"},
        {"electronic": "-0.02", "cash": "-0.02"},
    ],
)
def test_invalid_adjustment_refused(*, rates: dict[str, str]) -> None:
    """Fail closed rather than quote with absent or contradictory persisted policy."""
    with pytest.raises(ValueError, match="payment_adjustment_configuration"):
        calculate_payment_adjustment(
            amount=Decimal(10000), payment_method="electronic", rates=rates
        )


# ==============================================
# ENCRYPTED DRAFT OWNERSHIP, TTL AND EXPLICIT DELETION
# Reconnection can recover only the same account's text within the retention window.
# ==============================================


@pytest.mark.asyncio
async def test_private_draft_recovery(
    *, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Prove ciphertext custody, other-identity denial, expiry and deletion without business submission."""
    clock = [1000]
    monkeypatch.setattr(sessions.time, "time", lambda: clock[0])
    path = tmp_path / "sessions.sqlite3"
    store = BrowserSessions(path=path, key=Fernet.generate_key().decode())
    payload = EnrollmentDraftInput(
        company_name="FICTITIOUS PRIVATE COMPANY"
    ).model_dump_json()
    own = json.dumps(["issuer-local", "account-a"])
    await store.draft(owner=own, payload=payload)
    assert b"FICTITIOUS PRIVATE COMPANY" not in path.read_bytes()
    assert await store.draft(owner=json.dumps(["issuer-local", "account-b"])) is None
    assert await store.draft(owner=json.dumps(["other-issuer", "account-a"])) is None
    restored = await store.draft(owner=own)
    assert restored is not None and restored["expires_at"] == 2800
    assert restored["fields"]["company_name"] == "FICTITIOUS PRIVATE COMPANY"
    clock[0] = 2800
    assert await store.draft(owner=own) is None
    await store.draft(owner=own, payload=payload)
    await store.draft(owner=own, delete=True)
    assert await store.draft(owner=own) is None


# ==============================================
# CLOSED PARTIAL-FORM CONTRACT
# Passwords, tokens, evidence and consent actions cannot enter draft storage.
# ==============================================


@pytest.mark.parametrize(
    "field",
    [
        "password",
        "access_token",
        "receipt",
        "file",
        "accepted",
        "owner_id",
        "permission",
    ],
)
def test_draft_refuses_sensitive_fields(*, field: str) -> None:
    """Even an API caller cannot extend the allowlist with credential or command data."""
    with pytest.raises(ValidationError):
        EnrollmentDraftInput.model_validate({"company_name": "Local", field: "secret"})


# ==============================================
# DATABASE-CLOCK ADMIN WRITE WITHOUT HISTORY REINTERPRETATION
# The real DDL uses timestamp without time zone and now(), under the database timezone.
# ==============================================


@pytest.mark.asyncio
async def test_admin_update_uses_database_clock() -> None:
    """Preserve the DDL clock instead of assigning a guessed UTC/local Python date."""
    from sqlalchemy import func

    repo = admin_repo.AdminRepository(session=AsyncMock())
    repo.update = AsyncMock(return_value=None)
    await repo.update_admin(admin_id=1, full_name="Local administrator")
    expression = repo.update.await_args.kwargs["data"]["updated_at"]
    assert expression.compare(func.now())


# ==============================================
# EXACT O4 DINING COMPATIBILITY ADMISSION
# Admit the reviewed additive descendants and continue refusing unknown schemas.
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "revision,allowed",
    [("o320261108", True), ("o420261108", True), ("unreviewed", False)],
)
async def test_dining_schema_admission(*, revision: str, allowed: bool) -> None:
    """A version list is explicit; no wildcard or automatic schema repair is introduced."""
    from app.services.business.dining.staff import require_service_schema
    from app.services.business.dining.values import DiningError

    session = AsyncMock()
    session.scalar.return_value = revision
    if allowed:
        await require_service_schema(session=session)
    else:
        with pytest.raises(DiningError):
            await require_service_schema(session=session)


# ==============================================
# NONSENSITIVE ADMIN UPDATE LOGGING
# Retain the persistence value while logging only its field name.
# ==============================================


@pytest.mark.asyncio
async def test_admin_update_log_excludes_hash(
    *, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A reviewed update must never copy credential material into diagnostic metadata."""
    from unittest.mock import Mock

    captured = Mock()
    monkeypatch.setattr(admin_repo.logger, "info", captured)
    repo = admin_repo.AdminRepository(session=AsyncMock())
    repo.update = AsyncMock(return_value=None)
    value = "SYNTHETIC-CREDENTIAL-HASH-NOT-A-REAL-SECRET"
    await repo.update_admin(admin_id=1, password_hash=value)
    assert repo.update.await_args.kwargs["data"]["password_hash"] == value
    assert value not in repr(captured.call_args_list)
    assert captured.call_args.kwargs["extra"]["updated_fields"] == ["password_hash"]
