# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Verify private Telegram billing without Telegram, Redis, or database I/O."""

# ==============================================
# IMPORTS
# ==============================================

import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from types import SimpleNamespace
from typing import (
    Any,
    TypeAlias,
)
from unittest.mock import (
    AsyncMock,
    Mock,
)

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from app.handlers import (
    callback_handler,
    manual_billing_handler,
    message_handler,
)
from app.repositories.telegram_billing_repo import TelegramBillingRepository
from app.services.business import telegram_billing_service
from app.services.telegram import files

# ==============================================
# TYPES AND LOCAL EVIDENCE
# ==============================================

Payload: TypeAlias = dict[str, Any]
PNG_RECEIPT = b"\x89PNG\r\n\x1a\nprivate-local-test-receipt"
JPEG_RECEIPT = b"\xff\xd8\xffprivate-local-test-receipt\xff\xd9"


# ==============================================
# OFFLINE WORKFLOW HARNESS
# ==============================================


@dataclass
class BillingHarness:
    """Capture authorization, durable service calls, and ephemeral flow state."""

    states: dict[int, Payload]
    billing: Mock
    payments: Mock
    session: AsyncMock
    send: AsyncMock
    download: AsyncMock
    delete: AsyncMock


@pytest.fixture
def billing_harness(monkeypatch: pytest.MonkeyPatch) -> BillingHarness:
    """Replace all external boundaries while executing real flow transitions."""
    states: dict[int, Payload] = {}
    billing = Mock()
    billing.owner_id = AsyncMock(return_value=10)
    billing.repo = SimpleNamespace(
        restaurants=AsyncMock(return_value=[(55, "Owned restaurant")]),
        pending_payments=AsyncMock(return_value=[77]),
        plans=AsyncMock(return_value=[(3, "Local plan")]),
    )
    payments = Mock()
    payments.get_invoice = AsyncMock(
        return_value=SimpleNamespace(
            id=77,
            status="pending",
            amount=50.0,
            currency="DZD",
            payment_method="ccp",
        )
    )
    payments.get_receipt = AsyncMock(
        return_value=SimpleNamespace(
            id=8,
            payment_id=77,
            review_status="pending",
            transaction_reference="CCP12345",
            media_type="image/png",
            content=PNG_RECEIPT,
        )
    )
    payments.submit_receipt = AsyncMock()
    payments.review = AsyncMock(
        return_value=SimpleNamespace(id=8, review_status="approved")
    )
    payments.repo = SimpleNamespace(
        list_pending=AsyncMock(return_value=[SimpleNamespace(payment_id=77)]),
        get_payment=AsyncMock(
            return_value=SimpleNamespace(amount=50.0, currency="DZD")
        ),
    )
    session = AsyncMock(spec=AsyncSession)
    session.__aenter__.return_value = session
    session.__aexit__.return_value = False
    send = AsyncMock(return_value={"ok": True})
    download = AsyncMock(return_value=PNG_RECEIPT)

    async def read_state(*, chat_id: int) -> Payload | None:
        """Read only this chat's local workflow state."""
        return states.get(chat_id)

    async def write_state(*, chat_id: int, state: Payload) -> None:
        """Persist flow transitions in an isolated in-memory state store."""
        states[chat_id] = dict(state)

    async def delete_state(*, chat_id: int) -> None:
        """Remove a completed or explicitly cancelled local flow."""
        states.pop(chat_id, None)

    delete = AsyncMock(side_effect=delete_state)
    monkeypatch.setattr(manual_billing_handler, "get_state", read_state)
    monkeypatch.setattr(manual_billing_handler, "set_state", write_state)
    monkeypatch.setattr(manual_billing_handler, "delete_state", delete)
    monkeypatch.setattr(
        manual_billing_handler, "get_session", AsyncMock(return_value=session)
    )
    monkeypatch.setattr(
        manual_billing_handler, "TelegramBillingService", Mock(return_value=billing)
    )
    monkeypatch.setattr(
        manual_billing_handler, "ManualPaymentService", Mock(return_value=payments)
    )
    monkeypatch.setattr(manual_billing_handler, "send_message", send)
    monkeypatch.setattr(manual_billing_handler, "download_receipt", download)
    monkeypatch.setattr(manual_billing_handler.time, "time", lambda: 1000.0)
    return BillingHarness(states, billing, payments, session, send, download, delete)


def private_message(*, text: str = "", **attachment: Any) -> Payload:
    """Build a human private update with no identity supplied by flow state."""
    return {
        "chat": {"id": 101, "type": "private"},
        "from": {"id": 101, "is_bot": False},
        "message_id": 900,
        "text": text,
        **attachment,
    }


def active_state(*, step: str, **data: Any) -> Payload:
    """Build bounded workflow data without granting any authorization."""
    return {
        "flow": manual_billing_handler.BILLING_FLOW,
        "step": step,
        "payment_id": 77,
        "expires_at": 2000.0,
        **data,
    }


async def billing_callback(*, data: str) -> None:
    """Invoke the billing callback after private actor validation boundaries."""
    match = re.fullmatch(r"mb:.*", data)
    assert match is not None
    await manual_billing_handler.billing_callback(
        chat_id=101, message_id=900, callback_data=data, match=match
    )


# ==============================================
# PRIVATE ACTOR AND DISPATCH CONTRACTS
# ==============================================


@pytest.mark.parametrize(
    "chat,actor",
    [
        ({"id": 101, "type": "private"}, {"id": 202, "is_bot": False}),
        ({"id": -101, "type": "group"}, {"id": 101, "is_bot": False}),
        ({"id": 101, "type": "private"}, {"id": 101, "is_bot": True}),
        ({"id": 101, "type": "private"}, {"id": 101}),
        ({"id": "101", "type": "private"}, {"id": 101, "is_bot": False}),
        ({"id": True, "type": "private"}, {"id": True, "is_bot": False}),
        ({"id": 1, "type": "private"}, {"id": True, "is_bot": False}),
        (None, {"id": 101, "is_bot": False}),
        ({"id": 101, "type": "private"}, None),
    ],
    ids=[
        "different-actor",
        "group",
        "bot",
        "missing-human-flag",
        "string-id",
        "boolean-chat-id",
        "boolean-actor-id",
        "invalid-chat",
        "invalid-actor",
    ],
)
def test_private_actor_rejects_spoofed_and_malformed_updates(
    chat: Any,
    actor: Any,
) -> None:
    """No group, bot, boolean identifier, or forged sender enters billing."""
    assert not manual_billing_handler.is_private_actor(
        message={"chat": chat}, actor=actor
    )


@pytest.mark.asyncio
async def test_spoofed_callback_never_reaches_router(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An embedded message chat cannot impersonate its actual callback sender."""
    dispatch = AsyncMock()
    answer = AsyncMock()
    monkeypatch.setattr(callback_handler.router, "dispatch", dispatch)
    monkeypatch.setattr(callback_handler, "answer_callback", answer)
    message = private_message()
    await callback_handler.handle_callback(
        data={
            "callback_query": {
                "id": "local-callback",
                "message": message,
                "from": {"id": 202, "is_bot": False},
                "data": "mb:upload:77",
            }
        }
    )
    answer.assert_awaited_once_with(callback_id="local-callback")
    dispatch.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("step", ["receipt", "approve"])
async def test_receipts_and_review_messages_are_consumed_before_agent(
    monkeypatch: pytest.MonkeyPatch,
    billing_harness: BillingHarness,
    step: str,
) -> None:
    """Raw evidence and bank review inputs bypass general agent processing."""
    billing_harness.states[101] = active_state(step=step, reference="CCP12345")
    is_required = AsyncMock(return_value=False)
    process = AsyncMock()
    append = AsyncMock()
    monkeypatch.setattr(message_handler.CaptchaManager, "is_required", is_required)
    monkeypatch.setattr(message_handler.agent_engine, "process", process)
    monkeypatch.setattr(message_handler, "append_to_state_list", append)
    message = (
        private_message(
            document={
                "file_id": "local-file",
                "mime_type": "image/png",
                "file_size": 45,
            }
        )
        if step == "receipt"
        else private_message(text="50.00 | CCP-12345 | Independently verified")
    )
    await message_handler.handle_message(data={"message": message})
    process.assert_not_awaited()
    append.assert_not_awaited()


@pytest.mark.asyncio
async def test_admin_review_command_is_consumed_before_agent_without_db_access(
    monkeypatch: pytest.MonkeyPatch,
    billing_harness: BillingHarness,
) -> None:
    """Telegram directs reviewers to trusted Keycloak without granting authority."""
    monkeypatch.setattr(
        message_handler.CaptchaManager, "is_required", AsyncMock(return_value=False)
    )
    process = AsyncMock()
    monkeypatch.setattr(message_handler.agent_engine, "process", process)
    await message_handler.handle_message(
        data={"message": private_message(text="/payments_review")}
    )
    process.assert_not_awaited()
    billing_harness.session.__aenter__.assert_not_awaited()
    billing_harness.download.assert_not_awaited()
    billing_harness.payments.review.assert_not_awaited()
    assert "Keycloak" in billing_harness.send.await_args.kwargs["text"]


# ==============================================
# RECEIPT AUTHORIZATION AND FINANCIAL BOUNDARIES
# ==============================================


@pytest.mark.asyncio
async def test_reference_then_upload_preserves_pending_settlement(
    billing_harness: BillingHarness,
) -> None:
    """Evidence uses the persisted owner and never invokes financial approval."""
    billing_harness.states[101] = active_state(step="reference", owner_id=999)
    assert await manual_billing_handler.handle_billing_message(
        message=private_message(text="CCP / 123-45")
    )
    assert billing_harness.states[101]["reference"] == "CCP12345"
    assert billing_harness.states[101]["step"] == "receipt"
    billing_harness.payments.submit_receipt.assert_not_awaited()

    assert await manual_billing_handler.handle_billing_message(
        message=private_message(
            document={
                "file_id": "local-file",
                "mime_type": "image/png",
                "file_size": 45,
            }
        )
    )
    billing_harness.download.assert_awaited_once_with(file_id="local-file")
    billing_harness.payments.submit_receipt.assert_awaited_once_with(
        payment_id=77,
        owner_id=10,
        transaction_reference="CCP12345",
        content=PNG_RECEIPT,
        media_type="image/png",
    )
    billing_harness.payments.review.assert_not_awaited()
    assert 101 not in billing_harness.states


@pytest.mark.asyncio
@pytest.mark.parametrize("unavailable", ["disabled-method", "missing-beneficiary"])
async def test_pending_invoice_remains_visible_without_available_transfer(
    monkeypatch: pytest.MonkeyPatch,
    billing_harness: BillingHarness,
    unavailable: str,
) -> None:
    """Keep invoice reads available while excluding unconfigured transfer actions."""
    monkeypatch.setattr(
        settings, "MANUAL_CCP_ENABLED", unavailable != "disabled-method"
    )
    monkeypatch.setattr(settings, "MANUAL_BARIDIMOB_ENABLED", True)
    monkeypatch.setattr(
        settings,
        "MANUAL_TRANSFER_BENEFICIARY",
        None if unavailable == "missing-beneficiary" else "Local test beneficiary",
    )
    monkeypatch.setattr(settings, "MANUAL_CCP_ACCOUNT", "LOCAL-TEST-CCP-ACCOUNT")
    monkeypatch.setattr(settings, "MANUAL_CCP_KEY", "12")
    monkeypatch.setattr(settings, "MANUAL_BARIDIMOB_RIP", "LOCAL-TEST-BARIDIMOB-RIP")
    billing_harness.payments.get_receipt.side_effect = NotFoundError(
        message="Receipt not found"
    )

    await billing_callback(data="mb:invoice:77")

    billing_harness.billing.owner_id.assert_awaited_once_with(chat_id=101)
    billing_harness.payments.get_invoice.assert_awaited_once_with(
        payment_id=77, owner_id=10
    )
    billing_harness.payments.get_receipt.assert_awaited_once_with(
        payment_id=77, owner_id=10
    )
    invoice_response = billing_harness.send.await_args.kwargs
    assert "#77" in invoice_response["text"]
    assert "MOULAI-PAY-77" in invoice_response["text"]
    assert "50.00 DZD" in invoice_response["text"]
    assert "بانتظار التحقق" in invoice_response["text"]
    assert "طريقة التحويل غير متاحة حالياً" in invoice_response["text"]
    assert "Local test beneficiary" not in invoice_response["text"]
    assert "LOCAL-TEST-CCP-ACCOUNT" not in invoice_response["text"]
    assert "LOCAL-TEST-BARIDIMOB-RIP" not in invoice_response["text"]
    invoice_rows = invoice_response["reply_markup"]["inline_keyboard"]
    assert [button["callback_data"] for row in invoice_rows for button in row] == [
        "mb:invoice:77"
    ]
    assert billing_harness.payments.get_invoice.return_value.status == "pending"

    billing_harness.send.reset_mock()
    await billing_callback(data="mb:method:55:3:monthly")

    method_response = billing_harness.send.await_args.kwargs
    if unavailable == "disabled-method":
        method_rows = method_response["reply_markup"]["inline_keyboard"]
        assert [button["callback_data"] for row in method_rows for button in row] == [
            "mb:checkout:55:3:monthly:baridimob"
        ]
    else:
        assert method_response["reply_markup"] is None
        assert "بيانات استقبال التحويل غير متاحة حالياً" in method_response["text"]
    billing_harness.payments.submit_receipt.assert_not_awaited()
    billing_harness.payments.review.assert_not_awaited()
    billing_harness.download.assert_not_awaited()
    billing_harness.delete.assert_not_awaited()
    assert billing_harness.states == {}


@pytest.mark.asyncio
async def test_other_tenant_invoice_is_rejected_before_download(
    billing_harness: BillingHarness,
) -> None:
    """Guessed invoice IDs cannot fetch or submit private Telegram evidence."""
    billing_harness.states[101] = active_state(step="receipt", reference="CCP12345")
    billing_harness.payments.get_invoice.side_effect = NotFoundError(
        message="Payment not found"
    )
    assert await manual_billing_handler.handle_billing_message(
        message=private_message(
            document={
                "file_id": "local-file",
                "mime_type": "image/png",
                "file_size": 45,
            }
        )
    )
    billing_harness.download.assert_not_awaited()
    billing_harness.payments.submit_receipt.assert_not_awaited()
    billing_harness.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_owner_authorization_is_renewed_after_download(
    billing_harness: BillingHarness,
) -> None:
    """Revoked ownership after file retrieval cannot reach receipt persistence."""
    billing_harness.states[101] = active_state(step="receipt", reference="CCP12345")
    billing_harness.billing.owner_id.side_effect = [
        10,
        UnauthorizedError(message="Billing access denied"),
    ]
    assert await manual_billing_handler.handle_billing_message(
        message=private_message(
            document={
                "file_id": "local-file",
                "mime_type": "image/png",
                "file_size": 45,
            }
        )
    )
    billing_harness.download.assert_awaited_once()
    billing_harness.payments.submit_receipt.assert_not_awaited()
    assert billing_harness.states[101]["step"] == "receipt"


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["download", "duplicate"])
async def test_failed_submission_and_error_reply_preserve_pending_state(
    billing_harness: BillingHarness,
    failure: str,
) -> None:
    """A transient fetch failure or duplicate evidence does not abandon the flow."""
    billing_harness.states[101] = active_state(step="receipt", reference="CCP12345")
    billing_harness.send.return_value = {"ok": False}
    if failure == "download":
        billing_harness.download.side_effect = ValidationError(message="Unavailable")
    else:
        billing_harness.payments.submit_receipt.side_effect = ConflictError(
            message="Receipt reused"
        )
    assert await manual_billing_handler.handle_billing_message(
        message=private_message(
            document={
                "file_id": "local-file",
                "mime_type": "image/png",
                "file_size": 45,
            }
        )
    )
    assert billing_harness.states[101]["step"] == "receipt"
    billing_harness.delete.assert_not_awaited()
    billing_harness.payments.review.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "document",
    [
        {"file_id": "local-file", "mime_type": "text/html", "file_size": 45},
        {
            "file_id": "local-file",
            "mime_type": "image/png",
            "file_size": manual_billing_handler.MAX_RECEIPT_BYTES + 1,
        },
    ],
    ids=["unsupported-media", "declared-oversize"],
)
async def test_invalid_attachment_is_rejected_without_network_fetch(
    billing_harness: BillingHarness,
    document: Payload,
) -> None:
    """Reject unsupported media and declared large files before downloading."""
    billing_harness.states[101] = active_state(step="receipt", reference="CCP12345")
    await manual_billing_handler.handle_billing_message(
        message=private_message(document=document)
    )
    billing_harness.download.assert_not_awaited()
    billing_harness.payments.submit_receipt.assert_not_awaited()


@pytest.mark.asyncio
async def test_photo_upload_uses_largest_photo_and_jpeg_media(
    billing_harness: BillingHarness,
) -> None:
    """Telegram photo variants use the same canonical private evidence service."""
    billing_harness.states[101] = active_state(step="receipt", reference="CCP12345")
    billing_harness.download.return_value = JPEG_RECEIPT
    await manual_billing_handler.handle_billing_message(
        message=private_message(
            photo=[{"file_id": "thumbnail"}, {"file_id": "full-photo", "file_size": 45}]
        )
    )
    billing_harness.download.assert_awaited_once_with(file_id="full-photo")
    assert (
        billing_harness.payments.submit_receipt.await_args.kwargs["media_type"]
        == "image/jpeg"
    )
    billing_harness.payments.review.assert_not_awaited()


# ==============================================
# TELEGRAM ADMINISTRATION FAILS CLOSED
# ==============================================


# ==============================================
@pytest.mark.asyncio
@pytest.mark.parametrize("configured", [False, True])
@pytest.mark.parametrize(
    "data",
    [
        "mb:queue:0",
        "mb:review:77",
        "mb:file:77",
        "mb:approve:77",
        "mb:reject:77",
        "mb:confirm:77",
    ],
)
async def test_administrative_callbacks_never_gain_authority_from_chat_id(
    monkeypatch: pytest.MonkeyPatch,
    billing_harness: BillingHarness,
    configured: bool,
    data: str,
) -> None:
    """Even configured OIDC and legacy chat state cannot authorize Telegram review."""
    monkeypatch.setattr(
        settings,
        "OIDC_ISSUER",
        "https://keycloak.test/realms/local" if configured else None,
    )
    monkeypatch.setattr(
        settings, "OIDC_AUDIENCE", "billing-api" if configured else None
    )
    monkeypatch.setattr(
        settings,
        "OIDC_JWKS_URL",
        "https://keycloak.test/realms/local/protocol/openid-connect/certs"
        if configured
        else None,
    )
    billing_harness.states[101] = active_state(
        step="confirm",
        admin_id=7,
        funds_received=True,
        review={"decision": "approve", "funds_received": True},
    )
    await billing_callback(data=data)
    billing_harness.session.__aenter__.assert_not_awaited()
    billing_harness.payments.get_receipt.assert_not_awaited()
    billing_harness.payments.review.assert_not_awaited()
    billing_harness.payments.submit_receipt.assert_not_awaited()
    billing_harness.download.assert_not_awaited()
    assert billing_harness.states[101]["step"] == "confirm"


@pytest.mark.asyncio
@pytest.mark.parametrize("step", ["approve", "reject", "confirm"])
async def test_legacy_admin_state_is_discarded_without_financial_access(
    billing_harness: BillingHarness,
    step: str,
) -> None:
    """Old Redis review steps cannot survive the trusted identity requirement."""
    billing_harness.states[101] = active_state(
        step=step,
        admin_id=7,
        received_amount="50.00",
        funds_received=True,
    )
    assert await manual_billing_handler.handle_billing_message(
        message=private_message(text="50.00 | CCP12345 | Verified")
    )
    assert 101 not in billing_harness.states
    billing_harness.session.__aenter__.assert_not_awaited()
    billing_harness.download.assert_not_awaited()
    billing_harness.payments.review.assert_not_awaited()


# ==============================================
# PERSISTED OWNER IDENTITY AND TENANT QUERY CONTRACTS
# ==============================================


@pytest.mark.asyncio
async def test_billing_service_rejects_nonowned_restaurant() -> None:
    """A stored owner mapping does not authorize a guessed restaurant ID."""
    service = telegram_billing_service.TelegramBillingService(
        session=Mock(spec=AsyncSession)
    )
    service.repo = SimpleNamespace(
        owner_id=AsyncMock(return_value=10),
        owns_restaurant=AsyncMock(return_value=False),
    )
    with pytest.raises(UnauthorizedError):
        await service.owner_id(chat_id=101, restaurant_id=999)
    service.repo.owns_restaurant.assert_awaited_once_with(
        owner_id=10, restaurant_id=999
    )


# ==============================================
# PERSISTED IDENTITY AND TENANT QUERY CONTRACTS
# ==============================================


@pytest.mark.asyncio
async def test_owner_and_pending_invoice_queries_include_tenant_guards() -> None:
    """Repository reads constrain approved identity and restaurant ownership."""
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = 10
    session.scalars.return_value = [77]
    repository = TelegramBillingRepository(session=session)
    assert await repository.owner_id(chat_id=101) == 10
    owner_query = session.scalar.await_args.args[0]
    assert "owners.registration_status" in str(owner_query)
    assert owner_query.compile().params["chat_id_1"] == 101

    assert await repository.pending_payments(owner_id=10) == [77]
    pending_query = session.scalars.await_args.args[0]
    sql = str(pending_query)
    assert "payments.owner_id" in sql and "restaurants.owner_id" in sql
    assert "manual_transfer" in pending_query.compile().params.values()
    assert "pending" in pending_query.compile().params.values()


# ==============================================
# OFFICIAL FILE TRANSPORT AND BOUNDED STREAMING
# ==============================================


class LocalChunks(httpx.AsyncByteStream):
    """Yield deterministic local chunks without opening a network connection."""

    def __init__(self, *, chunks: list[bytes]) -> None:
        self.chunks = chunks

    async def __aiter__(self) -> AsyncIterator[bytes]:
        """Expose chunks through the same interface as HTTPX streamed responses."""
        for chunk in self.chunks:
            yield chunk


@pytest.mark.asyncio
async def test_download_uses_official_host_without_redirects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No arbitrary attachment URL or token-bearing URL is returned to callers."""
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        """Serve metadata and private bytes from an entirely local transport."""
        requests.append(request)
        assert request.url.host == "api.telegram.org"
        if request.url.path.endswith("/getFile"):
            return httpx.Response(
                200,
                json={
                    "ok": True,
                    "result": {
                        "file_path": "documents/file_123.png",
                        "file_size": len(PNG_RECEIPT),
                    },
                },
            )
        return httpx.Response(200, content=PNG_RECEIPT)

    monkeypatch.setattr(settings, "BOT_TOKEN", "offline-test-token")
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        monkeypatch.setattr(files, "client", client)
        assert await files.download_receipt(file_id="local-file") == PNG_RECEIPT
    assert len(requests) == 2
    assert requests[0].method == "POST"
    assert requests[1].method == "GET"
    assert requests[1].url.path.endswith("/documents/file_123.png")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        "../file.png",
        "documents/../file.png",
        "/file.png",
        "//example.org/file.png",
        "https://example.org/file.png",
        "documents\\file.png",
        "file.png?url=x",
        "file.png#fragment",
        "%2e%2e/file.png",
        "documents/%2Ffile.png",
        "documents/file\n.png",
        "documents/file name.png",
    ],
    ids=[
        "parent",
        "embedded-parent",
        "absolute",
        "foreign-host",
        "scheme",
        "backslash",
        "query",
        "fragment",
        "encoded-parent",
        "encoded-slash",
        "control-character",
        "space",
    ],
)
async def test_invalid_telegram_file_path_never_downloads(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
) -> None:
    """Even provider metadata cannot redirect receipt retrieval outside its path."""
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        """Return untrusted metadata and detect any unintended binary fetch."""
        requests.append(request)
        if request.url.path.endswith("/getFile"):
            return httpx.Response(
                200,
                json={
                    "ok": True,
                    "result": {"file_path": path, "file_size": 45},
                },
            )
        return httpx.Response(200, content=PNG_RECEIPT)

    monkeypatch.setattr(settings, "BOT_TOKEN", "offline-test-token")
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        monkeypatch.setattr(files, "client", client)
        with pytest.raises(ValidationError):
            await files.download_receipt(file_id="local-file")
    assert len(requests) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        [],
        {"ok": True, "result": None},
        {"ok": True, "result": {"file_path": "file.png", "file_size": "45"}},
        {"ok": True, "result": {"file_path": "file.png", "file_size": -1}},
        {"ok": True, "result": {"file_path": "file.png", "file_size": True}},
        {
            "ok": True,
            "result": {
                "file_path": "file.png",
                "file_size": files.MAX_RECEIPT_BYTES + 1,
            },
        },
    ],
    ids=[
        "invalid-envelope",
        "invalid-result",
        "string-size",
        "negative-size",
        "boolean-size",
        "metadata-oversize",
    ],
)
async def test_malformed_file_metadata_fails_closed_before_fetch(
    monkeypatch: pytest.MonkeyPatch,
    payload: Any,
) -> None:
    """Malformed metadata becomes a domain failure without a second HTTP request."""
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        """Return malformed JSON metadata through the real HTTPX decoder."""
        requests.append(request)
        if request.url.path.endswith("/getFile"):
            return httpx.Response(200, json=payload)
        return httpx.Response(200, content=PNG_RECEIPT)

    monkeypatch.setattr(settings, "BOT_TOKEN", "offline-test-token")
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        monkeypatch.setattr(files, "client", client)
        with pytest.raises(ValidationError):
            await files.download_receipt(file_id="local-file")
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_stream_limit_holds_when_metadata_omits_size(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing or understated metadata cannot bypass the streamed byte limit."""

    def respond(request: httpx.Request) -> httpx.Response:
        """Serve an oversized receipt through incremental local HTTPX chunks."""
        if request.url.path.endswith("/getFile"):
            return httpx.Response(
                200,
                json={
                    "ok": True,
                    "result": {"file_path": "documents/file.png"},
                },
            )
        return httpx.Response(
            200,
            stream=LocalChunks(
                chunks=[
                    b"x" * files.MAX_RECEIPT_BYTES,
                    b"x",
                ]
            ),
        )

    monkeypatch.setattr(settings, "BOT_TOKEN", "offline-test-token")
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        monkeypatch.setattr(files, "client", client)
        with pytest.raises(ValidationError):
            await files.download_receipt(file_id="local-file")


@pytest.mark.asyncio
async def test_redirect_response_is_not_followed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A file response cannot send the bot token or request to an external host."""
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        """Return an external redirect after otherwise valid official metadata."""
        requests.append(request)
        if request.url.path.endswith("/getFile"):
            return httpx.Response(
                200,
                json={
                    "ok": True,
                    "result": {"file_path": "documents/file.png"},
                },
            )
        return httpx.Response(302, headers={"Location": "https://example.org/file"})

    monkeypatch.setattr(settings, "BOT_TOKEN", "offline-test-token")
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(respond), follow_redirects=True
    ) as client:
        monkeypatch.setattr(files, "client", client)
        with pytest.raises(ValidationError):
            await files.download_receipt(file_id="local-file")
    assert len(requests) == 2
    assert all(request.url.host == "api.telegram.org" for request in requests)
