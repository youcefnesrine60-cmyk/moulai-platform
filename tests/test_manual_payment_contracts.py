# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Validation, configuration, and trusted administrative identity contracts."""

from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError as SchemaValidationError

from app.api import auth
from app.core.config import settings
from app.core.exceptions import ValidationError
from app.schemas.manual_payment import (
    ManualPaymentReview,
    ManualSubscriptionCheckout,
)
from app.services.business.manual_payment_service import (
    MAX_RECEIPT_BYTES,
    normalize_transfer_reference,
    validate_receipt_content,
)
from app.services.business.payment_providers import get_payment_provider


@pytest.mark.parametrize(
    "fields",
    [
        {"funds_received": False},
        {"funds_received": "true"},
        {"received_amount": None},
        {"received_currency": None},
        {"received_currency": "USD"},
        {"bank_transaction_reference": None},
        {"received_amount": "NaN"},
        {"received_amount": "50.001"},
    ],
)
def test_receipt_or_checkbox_alone_is_insufficient_for_approval(
    fields: dict[str, Any],
) -> None:
    """Reject missing or unverified settlement evidence independently of receipt upload."""
    data = {
        "decision": "approve",
        "funds_received": True,
        "received_amount": "50.00",
        "received_currency": "DZD",
        "bank_transaction_reference": "CCP-12345",
        "note": "Bank funds checked",
    }
    with pytest.raises(SchemaValidationError):
        ManualPaymentReview(**(data | fields))


@pytest.mark.parametrize("method", ["ccp", "baridimob"])
def test_provider_is_separate_from_method_and_can_be_disabled(
    monkeypatch: pytest.MonkeyPatch, method: str
) -> None:
    """Keep the provider distinct from transfer methods and honor configuration flags."""
    provider = get_payment_provider(method=method)
    instruction = provider.prepare_payment(
        method=method, amount=Decimal("50.00"), currency="DZD"
    )
    assert instruction.provider == "manual_transfer"
    assert instruction.method == method
    assert instruction.requires_receipt and instruction.requires_admin_review
    monkeypatch.setattr(
        settings,
        "MANUAL_CCP_ENABLED" if method == "ccp" else "MANUAL_BARIDIMOB_ENABLED",
        False,
    )
    with pytest.raises(ValidationError):
        get_payment_provider(method=method)


@pytest.mark.parametrize("method", ["stripe", "paypal", "cib", "edahabia"])
def test_unapproved_providers_have_no_adapter(method: str) -> None:
    """Reject providers whose official integrations have not been implemented."""
    with pytest.raises(ValidationError):
        get_payment_provider(method=method)


@pytest.mark.parametrize(
    "content,media_type",
    [
        (b"<html>unsafe</html>", "text/html"),
        (b"plain", "image/png"),
        (b"%PDF-missing-eof", "application/pdf"),
        (b"\x89PNG\r\n\x1a\n" + b"x" * MAX_RECEIPT_BYTES, "image/png"),
    ],
    ids=["html", "bad-signature", "invalid-pdf", "oversize"],
)
def test_receipt_type_and_size_are_bounded(content: bytes, media_type: str) -> None:
    """Reject unsafe media, invalid signatures, and oversized private evidence."""
    with pytest.raises(ValidationError):
        validate_receipt_content(content=content, media_type=media_type)


def test_reference_normalization_and_no_client_price_override() -> None:
    """Normalize bank references and reject client-controlled invoice amounts."""
    assert normalize_transfer_reference(
        value="CCP / 123-45"
    ) == normalize_transfer_reference(value="ccp12345")
    with pytest.raises(ValidationError):
        normalize_transfer_reference(value="💳12345")
    with pytest.raises(SchemaValidationError):
        ManualSubscriptionCheckout(
            restaurant_id=1, plan_id=2, payment_method="ccp", amount=0.01
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("admin_id", [None, 7])
async def test_admin_identity_comes_from_verified_subject_database_mapping(
    monkeypatch: pytest.MonkeyPatch, admin_id: int | None
) -> None:
    """Resolve an active administrator from the trusted subject rather than arbitrary IDs."""
    monkeypatch.setattr(
        auth,
        "_oidc_configuration",
        lambda: ("https://issuer.test/", "billing-api", "https://issuer.test/keys"),
    )
    subject = AsyncMock(return_value="verified-oidc-subject")
    monkeypatch.setattr(auth, "_get_authenticated_subject", subject)
    session = SimpleNamespace(
        execute=AsyncMock(
            return_value=SimpleNamespace(scalar_one_or_none=lambda: admin_id)
        )
    )
    if admin_id is None:
        with pytest.raises(HTTPException) as error:
            await auth.get_current_admin(credentials=None, session=session)
        assert error.value.status_code == 403
    else:
        assert await auth.get_current_admin(
            credentials=None, session=session
        ) == auth.AdminPrincipal(admin_id)
    query = str(session.execute.await_args.args[0])
    assert "admins.auth_subject" in query and "admins.is_active" in query
