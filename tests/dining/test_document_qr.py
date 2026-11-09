# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# OFFLINE COMMON QR AND ON-SITE TRANSITION CONTRACTS
# Reject unsupported write URLs and preserve the separate delivery transition graph.
# ==============================================

"""No database, network, rendering service or identity provider is needed by these checks."""

from __future__ import annotations

# isort: split
# ==============================================
# OFFLINE ENCODING AND STRICT INPUTS
# Reuse only pure QR helpers and bounded transport contracts.
# ==============================================

import pytest
from pydantic import ValidationError

from app.schemas.dining_public import (
    PresenceInstallationInput,
    VisitOrderTransition,
)
from app.services.business.document_qr import (
    DocumentQrError,
    public_read_url,
    svg_for_public_url,
)

# ==============================================
# CUSTOMER TABLE SUPPORT
# Check original artwork, translated instructions and absence of transient/technical print data.
# ==============================================


@pytest.mark.parametrize("locale", ["fr", "en", "ar"])
def test_table_print_is_customer_facing(*, locale: str) -> None:
    """Print the table identity without implying a permanent physical state or financial authority."""
    import re
    from base64 import b64decode
    from pathlib import Path

    from app.models.dining_service import DiningPublicLink
    from app.services.business.dining.public_print import print_public_document

    link = DiningPublicLink(
        kind="table",
        public_id="a" * 43,
        reference="DOC-TEST",
        digest="b" * 64,
        version=1,
        active=True,
    )
    text = print_public_document(
        link=link,
        document={
            "restaurant": "Restaurant <script>",
            "branch": "Centre",
            "table": "T1",
            "floor": "2",
            "room": "Salon",
            "zone": "Terrasse",
            "physical_state": "occupied",
        },
        origin="http://127.0.0.1:5574",
        locale=locale,
    )
    assert "<svg" in text and 'class="qr"' in text
    assert ('dir="rtl"' in text) == (locale == "ar")
    assert "Restaurant &lt;script&gt;" in text and "<script>" not in text
    assert "occupied" not in text and "SHA-256" not in text and "DOC-TEST" not in text
    assert "Salon" in text and "Terrasse" in text
    encoded = re.search(r"data:image/png;base64,([^\"]+)", text)
    assert encoded is not None
    assert (
        b64decode(encoded.group(1))
        == (
            Path(__file__).resolve().parents[2]
            / "frontend/public/brand/moulai-logo-light01.png"
        ).read_bytes()
    )
    assert {
        "fr": "Scannez pour consulter le menu",
        "en": "Scan to view the menu",
        "ar": "امسح الرمز للاطلاع على القائمة",
    }[locale] in text


# ==============================================
# READ-ONLY OPAQUE ADDRESS
# A generated document URL cannot carry customer details or a write endpoint.
# ==============================================


@pytest.mark.parametrize("locale", ["fr", "en", "ar"])
@pytest.mark.parametrize("page", ["menu", "verify-document", "verify-reservation"])
def test_common_qr_is_real_read_artwork(*, locale: str, page: str) -> None:
    """Encode exactly an approved read URL with the public identifier in the fragment."""
    url = public_read_url(
        origin="http://127.0.0.1:5574", page=page, public_id="a" * 43, locale=locale
    )
    assert url == "http://127.0.0.1:5574/" + page + "?locale=" + locale + "#" + "a" * 43
    svg = svg_for_public_url(value=url)
    assert "<svg" in svg and "<path" in svg


# ==============================================
# UNSUPPORTED OR UNSAFE REFERENCES
# Direct encoder callers cannot bypass the read-page or exact opaque-ID admission.
# ==============================================


@pytest.mark.parametrize(
    "url",
    [
        "https://example.invalid/pay?locale=fr#" + "a" * 43,
        "https://example.invalid/menu?locale=fr&customer=private#" + "a" * 43,
        "https://name:password@example.invalid/menu?locale=fr#" + "a" * 43,
        "http://example.invalid/menu?locale=fr#" + "a" * 43,
        "https://example.invalid/menu?locale=fr#table-1",
        "https://example.invalid/menu?locale=xx#" + "a" * 43,
    ],
)
def test_common_qr_refuses_invalid_payload(*, url: str) -> None:
    """Reject paths or data that exceed the explicit read-only QR contract."""
    with pytest.raises(DocumentQrError):
        svg_for_public_url(value=url)


# ==============================================
# STRICT OBSERVATION TYPE
# Numeric truthiness cannot impersonate the explicit human observation checkbox.
# ==============================================


@pytest.mark.parametrize("value", [1, "true", None])
def test_human_observation_rejects_coercion(*, value: object) -> None:
    """Both independent staff action contracts keep strict boolean input."""
    with pytest.raises(ValidationError):
        PresenceInstallationInput.model_validate(
            {
                "presence_id": 1,
                "expected_end": "2026-11-05T20:00:00Z",
                "observed": value,
            }
        )
    with pytest.raises(ValidationError):
        VisitOrderTransition.model_validate(
            {"order_id": 1, "action": "approve", "observed": value}
        )


# ==============================================
# ON-SITE COMPLETION WITHOUT A FICTITIOUS DELIVERY LEG
# Preserve the delivery/takeaway graph while allowing explicitly authorized actual table service.
# ==============================================


@pytest.mark.parametrize("order_type", ["dine_in", "delivery", "takeaway"])
async def test_ready_completion_is_limited_to_on_site(
    *, order_type: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An on-site terminal transition cannot silently broaden the other existing order graphs."""
    from unittest.mock import AsyncMock

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.core.exceptions import ValidationError as BusinessValidationError
    from app.models.order import Order
    from app.repositories.order_status_history_repo import OrderStatusHistoryRepository
    from app.services.business.orders.update import transition_locked_order

    order = Order(id=1, restaurant_id=2, order_type=order_type, status="ready")
    session = AsyncMock(spec=AsyncSession)
    history = AsyncMock()
    monkeypatch.setattr(OrderStatusHistoryRepository, "create", history)
    if order_type == "dine_in":
        result, changed = await transition_locked_order(
            order=order, new_status="completed", session=session
        )
        assert result is order and changed and order.status == "completed"
        again, changed = await transition_locked_order(
            order=order, new_status="completed", session=session
        )
        assert again is order and not changed
        history.assert_awaited_once()
    else:
        with pytest.raises(BusinessValidationError):
            await transition_locked_order(
                order=order, new_status="completed", session=session
            )
        assert order.status == "ready"
        history.assert_not_awaited()
