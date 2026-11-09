# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# SIGNED LOCAL HTTP TO PERSISTED D1 WORKFLOWS
# Drive genuine routes and services, then inspect committed state independently.
# ==============================================

"""No dependency principal override, external issuer, rollback fixture or live transport."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND EXPLICIT LOCAL CONTRACTS
# Reuse typed module dependencies without creating a connection or enabling a transport.
# ==============================================

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from decimal import Decimal

import pytest
from fastapi import FastAPI
from httpx import (
    ASGITransport,
    AsyncClient,
    Response,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.schemas.dining import JsonObject
from app.services.business.dining.service import DiningUnit
from test_support.dining_http import (
    LocalIdentityIssuer,
    create_local_dining_app,
)
from test_support.dining_seed import prepare_dining_rehearsal
from test_support.local_postgres import LocalPostgresSettings
from tests.dining.support import DiningGraph

pytestmark = pytest.mark.dining_postgres


# ==============================================
# SIGNEDFLOW
# Keep local credentials in RAM only; never include them in diagnostic output.
# ==============================================


@dataclass
class SignedFlow:
    """Keep local credentials in RAM only; never include them in diagnostic output."""

    client: AsyncClient
    app: FastAPI
    graph: DiningGraph
    issuer: LocalIdentityIssuer
    root: str
    proof: str = ""

    # ==============================================
    # LOGIN
    # Select a fixture actor, then let normal route authentication verify its cookie.
    # ==============================================

    async def login(self, *, actor: str) -> None:
        """Select a fixture actor, then let normal route authentication verify its cookie."""
        response = await self.client.post("/local-d1/session", json={"actor": actor})
        assert response.status_code == 200
        session = await self.client.get("/local-d1/session")
        assert session.status_code == 200
        self.proof = session.json()["customer_proofs"].get(
            str(self.graph.base + 300), ""
        )

    # ==============================================
    # COMMAND
    # Send one genuine typed form request, with a separate customer assertion.
    # ==============================================

    async def command(self, *, operation: str, **values: object) -> Response:
        """Send one genuine typed form request, with a separate customer assertion."""
        return await self.client.post(
            self.root + "/commands",
            json={"operation": operation, **values},
            headers={"X-Customer-Proof": self.proof} if self.proof else {},
        )

    # ==============================================
    # WORKSPACE
    # Reload actual server state rather than use an optimistic client model.
    # ==============================================

    async def workspace(self) -> JsonObject:
        """Reload actual server state rather than use an optimistic client model."""
        response = await self.client.get(self.root + "/workspace")
        assert response.status_code == 200
        return response.json()


# ==============================================
# FLOW
# Attest a disposable target, seed fiction, and create an in-process signed app.
# ==============================================


@pytest.fixture
async def flow(dining_engine: AsyncEngine) -> AsyncIterator[SignedFlow]:
    """Attest a disposable target, seed fiction, and create an in-process signed app."""
    graph = await prepare_dining_rehearsal(
        engine=dining_engine,
        configuration=LocalPostgresSettings(),
        now=datetime(2026, 11, 3, 18, tzinfo=timezone.utc),
    )
    # Explicit fixture grants are independent from a service role and are not migration seeds.
    async with graph.unit() as unit:
        for capability in (
            "finance.read",
            "invoices.create",
            "invoices.finalize",
            "advances.allocate",
        ):
            await unit.grant(
                membership_id=graph.base + 38,
                capability=capability,
                actor_kind="human",
                active=True,
            )
        await unit.grant(
            membership_id=graph.base + 31,
            capability="finance.read",
            actor_kind="human",
            active=True,
        )
        await unit.grant(
            membership_id=graph.base + 39,
            capability="finance.read",
            actor_kind="human",
            active=True,
        )
    app, issuer = await create_local_dining_app(
        configuration=LocalPostgresSettings(), graph=graph
    )
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://127.0.0.1:5581",
        headers={"Origin": "http://127.0.0.1:5581"},
    ) as client:
        yield SignedFlow(
            client=client,
            app=app,
            graph=graph,
            issuer=issuer,
            root=f"/local-d1/organizations/{graph.base+10}/restaurants/{graph.base+200}/branches/{graph.base+300}/dining",
        )


# ==============================================
# PREPARED
# Create, agree and hold through real signed requests; no receipt is fabricated.
# ==============================================


async def prepared(
    *, flow: SignedFlow, special_menu: bool = False
) -> tuple[int, int, int]:
    """Create, agree and hold through real signed requests; no receipt is fabricated."""
    await flow.login(actor="owner")
    state = await flow.workspace()
    menu = (
        [{"product_id": state["products"][0]["id"], "quantity": "2"}]
        if special_menu
        else []
    )
    result = await flow.command(
        operation="request",
        data={
            "customer_name": "Synthetic route customer",
            "contact": "route@example.invalid",
            "starts_at": "2026-11-03T20:00:00Z",
            "duration_seconds": 5400,
            "party_size": 4,
            "table_ids": [flow.graph.table_id],
            "criteria": {},
            "event_id": None,
            "preparation": False,
            "menu": menu,
        },
    )
    assert result.status_code == 200, result.text
    request_id = result.json()["identifier"]
    result = await flow.command(
        operation="quote",
        request_id=request_id,
        currency="DZD",
        expires_at="2026-11-03T19:00:00Z",
    )
    assert result.status_code == 200, result.text
    quote_id = result.json()["identifier"]
    state = await flow.workspace()
    quote = next(row for row in state["quotes"] if row["id"] == quote_id)
    await flow.login(actor="customer")
    result = await flow.client.post(
        f"/local-d1/dining/restaurants/{flow.graph.base+200}/branches/{flow.graph.base+300}/quotes/{quote_id}/accept",
        json={"digest": quote["digest"]},
    )
    assert result.status_code == 200, result.text
    await flow.login(actor="service")
    if special_menu:
        refused = await flow.command(
            operation="hold", request_id=request_id, quote_id=quote_id
        )
        assert refused.status_code == 409
        result = await flow.command(
            operation="restaurant_consent", quote_id=quote_id, digest=quote["digest"]
        )
        assert result.status_code == 200
    result = await flow.command(
        operation="hold", request_id=request_id, quote_id=quote_id
    )
    assert result.status_code == 200, result.text
    return request_id, quote_id, 0


# ==============================================
# RECEIVED
# The separately habilitated collector records a fictional but committed receipt.
# ==============================================


async def received(
    *, flow: SignedFlow, request_id: int, quote_id: int, amount: str = "1500"
) -> int:
    """The separately habilitated collector records a fictional but committed receipt."""
    await flow.login(actor="collector")
    response = await flow.client.post(
        flow.root + "/receipts",
        json={
            "request_id": request_id,
            "quote_id": quote_id,
            "received_amount": amount,
            "currency": "DZD",
            "mode": "cash",
            "reference": "LOCAL-RECEIPT-ONE",
            "received_at": flow.graph.clock.value.isoformat(),
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["receipt_id"]


# ==============================================
# CONFIRMED
# Use distinct receipt and human-proof actions, followed by atomic confirmation.
# ==============================================


async def confirmed(*, flow: SignedFlow) -> tuple[int, int, int, str]:
    """Use distinct receipt and human-proof actions, followed by atomic confirmation."""
    request_id, quote_id, _ = await prepared(flow=flow)
    receipt_id = await received(flow=flow, request_id=request_id, quote_id=quote_id)
    await flow.login(actor="service")
    proof = await flow.command(
        operation="human_proof",
        request_id=request_id,
        table_ids=[flow.graph.table_id],
        starts_at="2026-11-03T20:00:00Z",
        ends_at="2026-11-03T21:30:00Z",
    )
    assert proof.status_code == 200, proof.text
    response = await flow.command(
        operation="confirm_human",
        request_id=request_id,
        quote_id=quote_id,
        receipt_id=receipt_id,
    )
    assert response.status_code == 200, response.text
    return request_id, quote_id, receipt_id, response.json()["qr_token"]


# ==============================================
# TEST NOMINAL SIGNED HTTP INVOICE RELOAD AND DISTINCT CLEANING
# Run customer consent to paid service, invoice, departure and cleaning through HTTP.
# ==============================================


async def test_nominal_signed_http_invoice_reload_and_distinct_cleaning(
    flow: SignedFlow, dining_engine: AsyncEngine
) -> None:
    """Run customer consent to paid service, invoice, departure and cleaning through HTTP."""
    request_id, _quote_id, receipt_id, token = await confirmed(flow=flow)
    for locale in ("fr", "en", "ar"):
        response = await flow.client.get(
            flow.root + f"/requests/{request_id}/confirmation",
            params={"locale": locale},
        )
        assert (
            response.status_code == 200
            and f'lang="{locale}"' in response.text
            and "<svg" in response.text
        )
        assert ('dir="rtl"' in response.text) == (locale == "ar")
    flow.graph.clock.value = datetime(2026, 11, 3, 20, tzinfo=timezone.utc)
    arrived = await flow.command(
        operation="arrival",
        request_id=request_id,
        table_ids=[flow.graph.table_id],
        party_size=4,
        expected_end="2026-11-03T21:30:00Z",
    )
    assert arrived.status_code == 200, arrived.text
    occupation = arrived.json()["identifier"]
    await flow.login(actor="finance")
    state = await flow.workspace()
    order = state["food_orders"][0]
    line = order["items"][0]
    invoice = await flow.command(
        operation="invoice",
        data={
            "request_id": request_id,
            "currency": "DZD",
            "lines": [
                {
                    "order_id": order["id"],
                    "order_item_id": line["id"],
                    "description": "Synthetic food",
                    "quantity": "1",
                    "unit_price": "6000",
                    "source_reference": "reviewed exact synthetic source",
                }
            ],
            "currency_source": "synthetic DZD source",
            "rounding_source": "approved final HALF_UP",
            "reconciliation_reference": "local human reconciliation",
            "legacy_discrepancies_acknowledged": False,
        },
    )
    assert invoice.status_code == 200, invoice.text
    identifier = invoice.json()["identifier"]
    for _ in range(2):
        final = await flow.command(
            operation="finalize_invoice", invoice_id=identifier, expected_revision=1
        )
        assert final.status_code == 200, final.text
    state = await flow.workspace()
    assert len(state["allocations"]) == 1
    assert Decimal(state["allocations"][0]["balance"]) == Decimal(4500)
    await flow.login(actor="cleaner")
    assert (
        await flow.command(
            operation="human_proof",
            request_id=request_id,
            table_ids=[flow.graph.table_id],
            starts_at="2026-11-03T20:00:00Z",
            ends_at="2026-11-03T21:30:00Z",
        )
    ).status_code == 403
    for operation in ("departure", "start_cleaning", "finish_cleaning"):
        assert (
            await flow.command(operation=operation, occupation_id=occupation)
        ).status_code == 200
    state = await flow.workspace()
    assert (
        "receipts" not in state and "invoices" not in state and "requests" not in state
    )
    assert (
        next(row for row in state["tables"] if row["id"] == flow.graph.table_id)[
            "physical_state"
        ]
        == "available"
    )
    async with dining_engine.connect() as observer:
        assert (
            await observer.scalar(
                text("SELECT count(*) FROM dining_allocations WHERE receipt_id=:id"),
                {"id": receipt_id},
            )
            == 1
        )
        assert (
            await observer.scalar(
                text("SELECT count(*) FROM dining_receipts WHERE id=:id"),
                {"id": receipt_id},
            )
            == 1
        )
    verified = await flow.client.post(
        "/dining/verify-reservation", json={"token": token}
    )
    assert verified.status_code == 200 and verified.json()["valid"] is True


# ==============================================
# TEST CANCELLATION DEDICATED GRANT REPEAT AND INVALID QR
# Service role alone cannot cancel; dedicated authority releases only this slot.
# ==============================================


async def test_cancellation_dedicated_grant_repeat_and_invalid_qr(
    flow: SignedFlow, dining_engine: AsyncEngine
) -> None:
    """Service role alone cannot cancel; dedicated authority releases only this slot."""
    request_id, _quote_id, receipt_id, token = await confirmed(flow=flow)
    assert (
        await flow.command(
            operation="cancel_before_arrival",
            request_id=request_id,
            reason="Synthetic cancellation",
            origin="customer",
        )
    ).status_code == 403
    await flow.login(actor="canceller")
    for _ in range(2):
        response = await flow.command(
            operation="cancel_before_arrival",
            request_id=request_id,
            reason="Synthetic cancellation",
            origin="customer",
        )
        assert response.status_code == 200, response.text
    verified = await flow.client.post(
        "/dining/verify-reservation", json={"token": token}
    )
    assert verified.json() == {
        "reference": verified.json()["reference"],
        "status": "cancelled",
        "valid": False,
    }
    async with dining_engine.connect() as observer:
        assert (
            await observer.scalar(
                text(
                    "SELECT count(*) FROM dining_claims WHERE request_id=:id AND active"
                ),
                {"id": request_id},
            )
            == 0
        )
        assert (
            await observer.scalar(
                text("SELECT status FROM dining_receipts WHERE id=:id"),
                {"id": receipt_id},
            )
            == "verified"
        )
        assert (
            await observer.scalar(
                text("SELECT physical_state FROM dining_tables WHERE id=:id"),
                {"id": flow.graph.table_id},
            )
            == "available"
        )
        assert (
            await observer.scalar(
                text(
                    "SELECT count(*) FROM dining_events WHERE request_id=:id AND kind='reservation.cancelled'"
                ),
                {"id": request_id},
            )
            == 1
        )


# ==============================================
# TEST FINALIZATION REFUSALS PRESERVE RECEIPT
# A failed actual route cannot commit a partial reservation or erase received funds.
# ==============================================


@pytest.mark.parametrize(
    "failure",
    ["missing_proof", "invalidated_proof", "expired_hold", "unverified_payment"],
)
async def test_finalization_refusals_preserve_receipt(
    flow: SignedFlow, dining_engine: AsyncEngine, failure: str
) -> None:
    """A failed actual route cannot commit a partial reservation or erase received funds."""
    request_id, quote_id, _ = await prepared(flow=flow)
    receipt_id = await received(
        flow=flow,
        request_id=request_id,
        quote_id=quote_id,
        amount="1400" if failure == "unverified_payment" else "1500",
    )
    await flow.login(actor="owner")
    if failure != "missing_proof":
        assert (
            await flow.command(
                operation="human_proof",
                request_id=request_id,
                table_ids=[flow.graph.table_id],
                starts_at="2026-11-03T20:00:00Z",
                ends_at="2026-11-03T21:30:00Z",
            )
        ).status_code == 200
    if failure == "expired_hold":
        flow.graph.clock.value += timedelta(hours=2)
    if failure == "invalidated_proof":
        assert (
            await flow.command(
                operation="blackout",
                starts_at="2026-11-03T20:00:00Z",
                ends_at="2026-11-03T21:00:00Z",
                kind="maintenance",
                reason="Synthetic invalidation",
                table_id=flow.graph.table_id,
                zone_id=None,
                acknowledge_conflicts=True,
            )
        ).status_code == 200
    response = await flow.command(
        operation="confirm_human",
        request_id=request_id,
        quote_id=quote_id,
        receipt_id=receipt_id,
    )
    assert response.status_code == 409, response.text
    async with dining_engine.connect() as observer:
        assert (
            await observer.scalar(
                text("SELECT qr_token FROM dining_requests WHERE id=:id"),
                {"id": request_id},
            )
            is None
        )
        assert (
            await observer.scalar(
                text("SELECT count(*) FROM dining_receipts WHERE id=:id"),
                {"id": receipt_id},
            )
            == 1
        )


# ==============================================
# TEST WRONG SIGNATURE EXPIRED AND CROSS TENANT DENIED
# Cryptographic failures and a real foreign stored membership never become staff access.
# ==============================================


async def test_wrong_signature_expired_and_cross_tenant_denied(
    flow: SignedFlow,
) -> None:
    """Cryptographic failures and a real foreign stored membership never become staff access."""
    assert (await flow.client.get(flow.root + "/workspace")).status_code == 401
    await flow.login(actor="outsider")
    assert (await flow.client.get(flow.root + "/workspace")).status_code == 403
    wrong = LocalIdentityIssuer(principals=flow.issuer.principals).issue(actor="owner")
    cookie_name = next(cookie.name for cookie in flow.client.cookies.jar)
    flow.client.cookies.clear()
    flow.client.cookies.set(cookie_name, wrong, path="/local-d1")
    assert (await flow.client.get(flow.root + "/workspace")).status_code == 401
    # Keep malformed credentials only in request memory, never diagnostic output.
    cookie_name = next(cookie.name for cookie in flow.client.cookies.jar)
    flow.client.cookies.clear()
    flow.client.cookies.set(
        cookie_name, flow.issuer.issue(actor="owner", expired=True), path="/local-d1"
    )
    assert (await flow.client.get(flow.root + "/workspace")).status_code == 401


# ==============================================
# INVOICE DRAFT
# Reconcile the complete fictional source order using explicit exact-price evidence.
# ==============================================


async def invoice_draft(*, flow: SignedFlow, request_id: int) -> int:
    """Reconcile the complete fictional source order using explicit exact-price evidence."""
    await flow.login(actor="finance")
    state = await flow.workspace()
    order = state["food_orders"][0]
    line = order["items"][0]
    response = await flow.command(
        operation="invoice",
        data={
            "request_id": request_id,
            "currency": "DZD",
            "lines": [
                {
                    "order_id": order["id"],
                    "order_item_id": line["id"],
                    "description": "Synthetic food",
                    "quantity": "1",
                    "unit_price": "6000",
                    "source_reference": "reviewed exact synthetic source",
                }
            ],
            "currency_source": "synthetic DZD source",
            "rounding_source": "approved final HALF_UP",
            "reconciliation_reference": "local human reconciliation",
            "legacy_discrepancies_acknowledged": False,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["identifier"]


# ==============================================
# TEST SIGNED CONFLICT AND SCOPE FORGERY
# Existing SQL-protected holds survive conflicting or cross-establishment HTTP commands.
# ==============================================


async def test_signed_conflict_and_scope_forgery(flow: SignedFlow) -> None:
    """Existing SQL-protected holds survive conflicting or cross-establishment HTTP commands."""
    first, quote_id, _ = await prepared(flow=flow)
    await flow.login(actor="owner")
    other = await flow.command(
        operation="request",
        data={
            "customer_name": "Synthetic second customer",
            "contact": "second@example.invalid",
            "starts_at": "2026-11-03T20:00:00Z",
            "duration_seconds": 5400,
            "party_size": 4,
            "table_ids": [flow.graph.table_id],
            "criteria": {},
            "preparation": False,
            "menu": [],
        },
    )
    assert other.status_code == 200
    identifier = other.json()["identifier"]
    quote = await flow.command(
        operation="quote",
        request_id=identifier,
        currency="DZD",
        expires_at="2026-11-03T19:00:00Z",
    )
    assert quote.status_code == 200, quote.text
    second_quote = quote.json()["identifier"]
    data = await flow.workspace()
    digest = next(row for row in data["quotes"] if row["id"] == second_quote)["digest"]
    await flow.login(actor="customer")
    accepted = await flow.client.post(
        f"/local-d1/dining/restaurants/{flow.graph.base+200}/branches/{flow.graph.base+300}/quotes/{second_quote}/accept",
        json={"digest": digest},
    )
    assert accepted.status_code == 200
    await flow.login(actor="owner")
    refused = await flow.command(
        operation="hold", request_id=identifier, quote_id=second_quote
    )
    assert refused.status_code == 409, refused.text
    foreign = flow.root.replace(str(flow.graph.base + 300), str(flow.graph.base + 301))
    response = await flow.client.post(
        foreign + "/commands",
        json={
            "operation": "cancel_before_arrival",
            "request_id": first,
            "reason": "wrong branch",
            "origin": "human",
        },
    )
    assert response.status_code == 403
    state = await flow.workspace()
    assert (
        next(row for row in state["requests"] if row["id"] == first)["status"] == "held"
    )
    assert any(row["id"] == quote_id for row in state["quotes"])


# ==============================================
# TEST LATE HTTP FAILURE ROLLS BACK AFTER FLUSH
# Inject a technical error after real writes; observe rollback through another connection.
# ==============================================


@pytest.mark.parametrize("failure_kind", ["reservation.confirmed", "invoice.finalized"])
async def test_late_http_failure_rolls_back_after_flush(
    flow: SignedFlow,
    dining_engine: AsyncEngine,
    monkeypatch: pytest.MonkeyPatch,
    failure_kind: str,
) -> None:
    """Inject a technical error after real writes; observe rollback through another connection."""
    if failure_kind == "reservation.confirmed":
        request_id, quote_id, _ = await prepared(flow=flow)
        receipt_id = await received(flow=flow, request_id=request_id, quote_id=quote_id)
        await flow.login(actor="service")
        proof = await flow.command(
            operation="human_proof",
            request_id=request_id,
            table_ids=[flow.graph.table_id],
            starts_at="2026-11-03T20:00:00Z",
            ends_at="2026-11-03T21:30:00Z",
        )
        assert proof.status_code == 200
        values = {
            "operation": "confirm_human",
            "request_id": request_id,
            "quote_id": quote_id,
            "receipt_id": receipt_id,
        }
        invoice_id = None
    else:
        request_id, _, receipt_id, _ = await confirmed(flow=flow)
        flow.graph.clock.value = datetime(2026, 11, 3, 20, tzinfo=timezone.utc)
        assert (
            await flow.command(
                operation="arrival",
                request_id=request_id,
                table_ids=[flow.graph.table_id],
                party_size=4,
                expected_end="2026-11-03T21:30:00Z",
            )
        ).status_code == 200
        invoice_id = await invoice_draft(flow=flow, request_id=request_id)
        values = {
            "operation": "finalize_invoice",
            "invoice_id": invoice_id,
            "expected_revision": 1,
        }
    original = DiningUnit.event

    # ==============================================
    # FAIL EVENT
    # Fail only the selected already-flushed operation, leaving earlier commits intact.
    # ==============================================

    async def fail_event(self: DiningUnit, *, kind: str, **kwargs: object) -> None:
        """Fail only the selected already-flushed operation, leaving earlier commits intact."""
        if kind == failure_kind:
            await self.session.flush()
            raise RuntimeError("synthetic_late_failure")
        await original(self, kind=kind, **kwargs)

    monkeypatch.setattr(DiningUnit, "event", fail_event)
    response = await flow.command(**values)
    assert response.status_code == 500
    async with dining_engine.connect() as observer:
        assert (
            await observer.scalar(
                text("SELECT count(*) FROM dining_receipts WHERE id=:id"),
                {"id": receipt_id},
            )
            == 1
        )
        assert (
            await observer.scalar(
                text(
                    "SELECT count(*) FROM dining_events WHERE request_id=:id AND kind=:kind"
                ),
                {"id": request_id, "kind": failure_kind},
            )
            == 0
        )
        if invoice_id is None:
            row = (
                await observer.execute(
                    text("SELECT status,qr_token FROM dining_requests WHERE id=:id"),
                    {"id": request_id},
                )
            ).one()
            assert row == ("held", None)
            assert (
                await observer.scalar(
                    text(
                        "SELECT count(*) FROM dining_claims WHERE request_id=:id AND kind='hold' AND active"
                    ),
                    {"id": request_id},
                )
                == 1
            )
        else:
            assert (
                await observer.scalar(
                    text("SELECT status FROM dining_invoices WHERE id=:id"),
                    {"id": invoice_id},
                )
                == "draft"
            )
            assert (
                await observer.scalar(
                    text(
                        "SELECT count(*) FROM dining_allocations WHERE receipt_id=:id"
                    ),
                    {"id": receipt_id},
                )
                == 0
            )


# ==============================================
# TEST CUSTOMER SIGNAL DOES NOT CANCEL AND TARGETS ONLY AUTHORIZED
# A client or AI signal cannot substitute for a separately authorized human decision.
# ==============================================


async def test_customer_signal_does_not_cancel_and_targets_only_authorized(
    flow: SignedFlow,
) -> None:
    """A client or AI signal cannot substitute for a separately authorized human decision."""
    request_id, _, _, _ = await confirmed(flow=flow)
    await flow.login(actor="customer")
    response = await flow.client.post(
        f"/local-d1/dining/restaurants/{flow.graph.base+200}/branches/{flow.graph.base+300}/requests/{request_id}/cancellation-request",
        json={"reason": "Synthetic client request"},
    )
    assert response.status_code == 200 and response.json()["cancelled"] is False
    assert response.json()["forwarded_to_habilitated"] == 2
    await flow.login(actor="assistant")
    response = await flow.command(
        operation="signal",
        request_id=request_id,
        kind="customer_cancellation_requested",
        reason="Synthetic AI forwarding",
    )
    assert response.status_code == 200, response.text
    assert (
        await flow.command(
            operation="cancel_before_arrival",
            request_id=request_id,
            reason="AI may not decide",
            origin="assistant",
        )
    ).status_code == 403
    await flow.login(actor="owner")
    state = await flow.workspace()
    assert (
        next(row for row in state["requests"] if row["id"] == request_id)["status"]
        == "confirmed"
    )
    jobs = [
        row
        for row in state["outbox"]
        if row["event_key"].startswith("cancellation.request:")
    ]
    assert len(jobs) == 4
    assert {row["target"] for row in jobs} == {
        f"membership:{flow.graph.base+30}",
        f"membership:{flow.graph.base+37}",
    }
    assert all(row["attempts"] == 0 and row["status"] == "pending" for row in jobs)


# ==============================================
# TEST DRAFT INVOICE BLOCKS CANCELLATION BEFORE ARRIVAL
# Invoicing already begun is a policy boundary even before physical arrival.
# ==============================================


async def test_draft_invoice_blocks_cancellation_before_arrival(
    flow: SignedFlow,
) -> None:
    """Invoicing already begun is a policy boundary even before physical arrival."""
    request_id, _, _, _ = await confirmed(flow=flow)
    await invoice_draft(flow=flow, request_id=request_id)
    await flow.login(actor="canceller")
    response = await flow.command(
        operation="cancel_before_arrival",
        request_id=request_id,
        reason="Invoice exists",
        origin="human",
    )
    assert response.status_code == 409


# ==============================================
# TEST CANCEL ARRIVAL RACE HAS ONE PERSISTED WINNER
# Independent signed sessions race; the policy/request locks enforce one coherent outcome.
# ==============================================


async def test_cancel_arrival_race_has_one_persisted_winner(
    flow: SignedFlow, dining_engine: AsyncEngine
) -> None:
    """Independent signed sessions race; the policy/request locks enforce one coherent outcome."""
    request_id, _, receipt_id, _ = await confirmed(flow=flow)
    flow.graph.clock.value = datetime(2026, 11, 3, 20, tzinfo=timezone.utc)
    async with AsyncClient(
        transport=ASGITransport(app=flow.app),
        base_url="http://127.0.0.1:5581",
        headers={"Origin": "http://127.0.0.1:5581"},
    ) as other:
        assert (
            await other.post("/local-d1/session", json={"actor": "canceller"})
        ).status_code == 200
        cancelled, arrived = await asyncio.gather(
            other.post(
                flow.root + "/commands",
                json={
                    "operation": "cancel_before_arrival",
                    "request_id": request_id,
                    "reason": "Synthetic race",
                    "origin": "human",
                },
            ),
            flow.command(
                operation="arrival",
                request_id=request_id,
                table_ids=[flow.graph.table_id],
                party_size=4,
                expected_end="2026-11-03T21:30:00Z",
            ),
        )
    assert sorted([cancelled.status_code, arrived.status_code]) == [200, 409]
    async with dining_engine.connect() as observer:
        status = await observer.scalar(
            text("SELECT status FROM dining_requests WHERE id=:id"), {"id": request_id}
        )
        occupations = await observer.scalar(
            text("SELECT count(*) FROM dining_occupations WHERE request_id=:id"),
            {"id": request_id},
        )
        assert (status, occupations) in {("arrived", 1), ("cancelled", 0)}
        assert (
            await observer.scalar(
                text("SELECT count(*) FROM dining_receipts WHERE id=:id"),
                {"id": receipt_id},
            )
            == 1
        )


# ==============================================
# TEST DUAL ROLE TWO ACTIONS AND CONCURRENT INVOICE NO DOUBLE FINANCE
# Two grants retain two separate events; repeated finance has a unique real allocation.
# ==============================================


async def test_dual_role_two_actions_and_concurrent_invoice_no_double_finance(
    flow: SignedFlow, dining_engine: AsyncEngine
) -> None:
    """Two grants retain two separate events; repeated finance has a unique real allocation."""
    request_id, _, receipt_id, _ = await confirmed(flow=flow)
    flow.graph.clock.value = datetime(2026, 11, 3, 20, tzinfo=timezone.utc)
    await flow.login(actor="service_cleaner")
    occupation = await flow.command(
        operation="arrival",
        request_id=request_id,
        table_ids=[flow.graph.table_id],
        party_size=4,
        expected_end="2026-11-03T21:30:00Z",
    )
    assert occupation.status_code == 200
    invoice_id = await invoice_draft(flow=flow, request_id=request_id)
    results = await asyncio.gather(
        *[
            flow.command(
                operation="finalize_invoice", invoice_id=invoice_id, expected_revision=1
            )
            for _ in range(2)
        ]
    )
    assert all(row.status_code == 200 for row in results)
    await flow.login(actor="service_cleaner")
    assert (
        await flow.command(
            operation="departure", occupation_id=occupation.json()["identifier"]
        )
    ).status_code == 200
    state = await flow.workspace()
    assert (
        next(row for row in state["tables"] if row["id"] == flow.graph.table_id)[
            "physical_state"
        ]
        == "dirty"
    )
    assert any(
        row["kind"] == "occupation.departure_observed" for row in state["events"]
    )
    assert not any(row["kind"] == "cleaning.completed" for row in state["events"])
    for operation in ("start_cleaning", "finish_cleaning"):
        assert (
            await flow.command(
                operation=operation, occupation_id=occupation.json()["identifier"]
            )
        ).status_code == 200
    proof = await flow.command(
        operation="human_proof",
        request_id=None,
        table_ids=[flow.graph.table_id],
        starts_at="2026-11-03T22:00:00Z",
        ends_at="2026-11-03T23:00:00Z",
    )
    assert proof.status_code == 200
    async with dining_engine.connect() as observer:
        assert (
            await observer.scalar(
                text("SELECT count(*) FROM dining_allocations WHERE receipt_id=:id"),
                {"id": receipt_id},
            )
            == 1
        )
        rows = (
            await observer.execute(
                text(
                    "SELECT kind,author FROM dining_events WHERE restaurant_id=:r AND kind IN ('cleaning.completed','availability.human_confirmed')"
                ),
                {"r": flow.graph.base + 200},
            )
        ).all()
        dual = [
            row for row in rows if row.author["membership_id"] == flow.graph.base + 36
        ]
        assert len(dual) == 2
        assert {row.kind for row in dual} == {
            "cleaning.completed",
            "availability.human_confirmed",
        }


# ==============================================
# TEST SIGNED OWNER CONFIGURATION EDITS AND RELOADS
# Owner forms persist reference, table, combination, calendar and scoped blackout changes.
# ==============================================


async def test_signed_owner_configuration_edits_and_reloads(flow: SignedFlow) -> None:
    """Owner forms persist reference, table, combination, calendar and scoped blackout changes."""
    await flow.login(actor="owner")
    state = await flow.workspace()
    reference = await flow.command(
        operation="reference",
        data={
            "kind": "feature",
            "code": "http_feature",
            "labels": {"fr": "Locale", "en": "Local", "ar": "محلية"},
            "active": True,
            "pricing_ref": None,
        },
    )
    assert reference.status_code == 200, reference.text
    reference_id = reference.json()["identifier"]
    amended = await flow.command(
        operation="reference",
        identifier=reference_id,
        data={
            "kind": "feature",
            "code": "http_feature",
            "labels": {"fr": "Modifiée", "en": "Changed", "ar": "معدلة"},
            "active": False,
            "pricing_ref": None,
        },
    )
    assert amended.status_code == 200
    original = state["tables"][0]
    table_data = {
        key: original[key]
        for key in (
            "code",
            "name",
            "min_capacity",
            "max_capacity",
            "shape_id",
            "category_id",
            "zone_id",
            "location_id",
            "description",
            "photos",
            "pricing_ref",
            "in_service",
        )
    }
    table_data["trait_ids"] = [
        row["reference_id"]
        for row in state["traits"]
        if row["table_id"] == original["id"]
    ]
    table_data["description"] = "Changed by signed local HTTP"
    assert (
        await flow.command(
            operation="table", identifier=original["id"], data=table_data
        )
    ).status_code == 200
    pair = state["tables"][:2]
    grouping = {
        "code": "HTTP-PAIR",
        "table_ids": [row["id"] for row in pair],
        "min_capacity": 1,
        "max_capacity": sum(row["max_capacity"] for row in pair),
        "pricing_ref": "explicit-local-group",
        "active": True,
    }
    created = await flow.command(operation="combination", data=grouping)
    assert created.status_code == 200, created.text
    grouping["active"] = False
    assert (
        await flow.command(
            operation="combination",
            identifier=created.json()["identifier"],
            data=grouping,
        )
    ).status_code == 200
    assert (
        await flow.command(operation="calendar", service_date="2026-11-04", windows=[])
    ).status_code == 200
    block = await flow.command(
        operation="blackout",
        starts_at="2026-11-03T22:00:00Z",
        ends_at="2026-11-03T23:00:00Z",
        kind="maintenance",
        reason="Local observed maintenance",
        table_id=original["id"],
    )
    assert block.status_code == 200
    assert (
        await flow.command(
            operation="close_blackout", identifier=block.json()["identifier"]
        )
    ).status_code == 200
    reloaded = await flow.workspace()
    assert (
        next(row for row in reloaded["references"] if row["id"] == reference_id)[
            "labels"
        ]["ar"]
        == "معدلة"
    )
    assert (
        next(
            row
            for row in reloaded["combinations"]
            if row["id"] == created.json()["identifier"]
        )["active"]
        is False
    )
    assert (
        next(row for row in reloaded["tables"] if row["id"] == original["id"])[
            "description"
        ]
        == table_data["description"]
    )
    assert (
        next(row for row in reloaded["tables"] if row["id"] == original["id"])[
            "physical_state"
        ]
        == original["physical_state"]
    )


# ==============================================
# TEST SPECIAL MENU REQUIRES TWO INDEPENDENT AGREEMENTS
# An actual persisted menu quote cannot be held before customer and restaurant approvals.
# ==============================================


async def test_special_menu_requires_two_independent_agreements(
    flow: SignedFlow,
) -> None:
    """An actual persisted menu quote cannot be held before customer and restaurant approvals."""
    request_id, quote_id, _ = await prepared(flow=flow, special_menu=True)
    state = await flow.workspace()
    quoted = next(row for row in state["quotes"] if row["id"] == quote_id)
    assert Decimal(quoted["amount"]) == Decimal("1520.01")
    assert {
        row["party"] for row in state["acceptances"] if row["quote_id"] == quote_id
    } == {"customer", "restaurant"}
    receipt_id = await received(
        flow=flow, request_id=request_id, quote_id=quote_id, amount="1520.01"
    )
    await flow.login(actor="service")
    assert (
        await flow.command(
            operation="human_proof",
            request_id=request_id,
            table_ids=[flow.graph.table_id],
            starts_at="2026-11-03T20:00:00Z",
            ends_at="2026-11-03T21:30:00Z",
        )
    ).status_code == 200
    assert (
        await flow.command(
            operation="confirm_human",
            request_id=request_id,
            quote_id=quote_id,
            receipt_id=receipt_id,
        )
    ).status_code == 200


# ==============================================
# TEST REVOKED CANCELLATION GRANT AND ARRIVED RESERVATION ARE REFUSED
# Owner-assigned permissions are live data, never cached role-name authority.
# ==============================================


async def test_revoked_cancellation_grant_and_arrived_reservation_are_refused(
    flow: SignedFlow,
) -> None:
    """Owner-assigned permissions are live data, never cached role-name authority."""
    request_id, _, _, _ = await confirmed(flow=flow)
    await flow.login(actor="owner")
    assert (
        await flow.command(
            operation="grant",
            membership_id=flow.graph.base + 37,
            capability="reservations.cancel_before_arrival",
            actor_kind="human",
            active=False,
        )
    ).status_code == 200
    await flow.login(actor="canceller")
    assert (
        await flow.command(
            operation="cancel_before_arrival",
            request_id=request_id,
            reason="Revoked",
            origin="human",
        )
    ).status_code == 403
    await flow.login(actor="owner")
    assert (
        await flow.command(
            operation="grant",
            membership_id=flow.graph.base + 37,
            capability="reservations.cancel_before_arrival",
            actor_kind="human",
            active=True,
        )
    ).status_code == 200
    flow.graph.clock.value = datetime(2026, 11, 3, 20, tzinfo=timezone.utc)
    assert (
        await flow.command(
            operation="arrival",
            request_id=request_id,
            table_ids=[flow.graph.table_id],
            party_size=4,
            expected_end="2026-11-03T21:30:00Z",
        )
    ).status_code == 200
    await flow.login(actor="canceller")
    assert (
        await flow.command(
            operation="cancel_before_arrival",
            request_id=request_id,
            reason="Already arrived",
            origin="human",
        )
    ).status_code == 409


# ==============================================
# TEST ADMITTED CONTEXT NAMES AND CLEANER PROJECTION
# Human-readable labels never broaden scopes or expose customer/financial rows.
# ==============================================


async def test_admitted_context_names_and_cleaner_projection(flow: SignedFlow) -> None:
    """Resolve real names for admitted scopes; deny a direct financial command as cleaner."""
    await flow.login(actor="cleaner")
    response = await flow.client.get("/local-d1/session")
    assert response.status_code == 200
    scopes = response.json()["scopes"]
    assert scopes and all(
        row["restaurant_name"] and row["branch_name"] for row in scopes
    )
    assert all(row["restaurant_id"] == flow.graph.base + 200 for row in scopes)
    state = await flow.workspace()
    assert set(state["capabilities"]) == {"read", "clean"}
    assert (
        "receipts" not in state and "invoices" not in state and "requests" not in state
    )
    refused = await flow.command(operation="allocate", invoice_id=1, receipt_id=1)
    assert refused.status_code == 403


# ==============================================
# TEST ATTESTED VISUAL STATES
# Independent SQL observations prove fixture persistence without inventing receipts.
# ==============================================


async def test_atttested_visual_states_are_persisted_and_financially_empty(
    flow: SignedFlow, dining_engine: AsyncEngine
) -> None:
    """Cover all physical states and independent planning with no seeded payment."""
    from test_support.dining_visual_seed import prepare_visual_states

    await prepare_visual_states(
        graph=flow.graph, engine=dining_engine, configuration=LocalPostgresSettings()
    )
    await flow.login(actor="owner")
    state = await flow.workspace()
    assert {row["physical_state"] for row in state["tables"]} == {
        "available",
        "occupied",
        "dirty",
        "maintenance",
        "out_of_service",
    }
    assert state["receipts"] == [] and state["invoices"] == []
    assert len(state["tables"]) == 8
    response = await flow.client.get(
        flow.root + "/planning",
        params={"starts_at": "2026-11-02T23:00:00Z", "ends_at": "2026-11-03T23:00:00Z"},
    )
    assert response.status_code == 200
    planning = response.json()
    full = next(row for row in planning if row["code"] == "V01")
    assert full["physical_state"] == "available" and full["fully_reserved"] is True
    occupied = next(row for row in planning if row["code"] == "V02")
    assert occupied["physical_state"] == "occupied" and occupied["claims"]
    async with dining_engine.connect() as observer:
        assert (
            await observer.scalar(
                text(
                    "SELECT count(*) FROM dining_tables WHERE restaurant_id=:restaurant AND branch_id=:branch AND code LIKE 'V%'"
                ),
                {"restaurant": flow.graph.base + 200, "branch": flow.graph.base + 300},
            )
            == 6
        )


# ==============================================
# TEST INDEPENDENT FINANCIAL CAPABILITIES
# Viewing a document never permits collection, finalization or allocation.
# ==============================================


@pytest.mark.parametrize("actor", ("service", "cleaner", "finance_reader"))
async def test_reading_or_service_does_not_grant_financial_writes(
    flow: SignedFlow, actor: str
) -> None:
    """Exercise actual command, invoice and receipt routes after signed profile changes."""
    request_id, quote_id, receipt_id, _ = await confirmed(flow=flow)
    invoice_id = await invoice_draft(flow=flow, request_id=request_id)
    snapshot = await flow.workspace()
    source = snapshot["food_orders"][0]
    line = source["items"][0]
    payload = {
        "request_id": request_id,
        "currency": "DZD",
        "lines": [
            {
                "order_id": source["id"],
                "order_item_id": line["id"],
                "description": "Synthetic food",
                "quantity": "1",
                "unit_price": "6000",
                "source_reference": "reviewed exact synthetic source",
            }
        ],
        "currency_source": "synthetic DZD source",
        "rounding_source": "HALF_UP",
        "reconciliation_reference": "local check",
        "legacy_discrepancies_acknowledged": False,
    }
    if actor == "service":
        async with flow.graph.unit() as unit:
            await unit.grant(
                membership_id=flow.graph.base + 31,
                capability="finance.read",
                actor_kind="human",
                active=False,
            )
    await flow.login(actor=actor)
    state = await flow.workspace()
    if actor == "service":
        assert (
            await flow.client.get(flow.root + f"/requests/{request_id}/confirmation")
        ).status_code == 403
    assert ("invoices" in state) is (actor == "finance_reader")
    assert ("receipts" in state) is (actor == "finance_reader")
    assert (
        await flow.client.post(flow.root + "/invoices", json=payload)
    ).status_code == 403
    assert (await flow.command(operation="invoice", data=payload)).status_code == 403
    assert (
        await flow.command(
            operation="finalize_invoice", invoice_id=invoice_id, expected_revision=1
        )
    ).status_code == 403
    assert (
        await flow.client.post(
            flow.root + f"/invoices/{invoice_id}/finalize",
            json={"expected_revision": 1},
        )
    ).status_code == 403
    assert (
        await flow.command(
            operation="allocate", invoice_id=invoice_id, receipt_id=receipt_id
        )
    ).status_code == 403
    response = await flow.client.post(
        flow.root + "/receipts",
        json={
            "request_id": request_id,
            "quote_id": quote_id,
            "received_amount": "1500",
            "currency": "DZD",
            "mode": "cash",
            "reference": "forbidden-reading-write",
            "received_at": "2026-11-03T18:00:00Z",
        },
    )
    assert response.status_code == 403


# ==============================================
# TEST FINALIZATION REQUIRES ALLOCATION AUTHORITY
# Failure after an invoice write must roll back without erasing independently received funds.
# ==============================================


async def test_financial_revocation_and_atomic_allocation_guard(
    flow: SignedFlow, dining_engine: AsyncEngine
) -> None:
    """An already signed financial session loses its powers immediately on server recheck."""
    request_id, _, receipt_id, _ = await confirmed(flow=flow)
    flow.graph.clock.value = datetime(2026, 11, 3, 20, tzinfo=timezone.utc)
    assert (
        await flow.command(
            operation="arrival",
            request_id=request_id,
            table_ids=[flow.graph.table_id],
            party_size=4,
            expected_end="2026-11-03T21:30:00Z",
        )
    ).status_code == 200
    invoice_id = await invoice_draft(flow=flow, request_id=request_id)
    async with flow.graph.unit() as unit:
        await unit.grant(
            membership_id=flow.graph.base + 38,
            capability="advances.allocate",
            actor_kind="human",
            active=False,
        )
    assert (
        await flow.command(
            operation="finalize_invoice", invoice_id=invoice_id, expected_revision=1
        )
    ).status_code == 403

    async with dining_engine.connect() as observer:
        assert (
            await observer.scalar(
                text("SELECT status FROM dining_invoices WHERE id=:id"),
                {"id": invoice_id},
            )
            == "draft"
        )
        assert (
            await observer.scalar(
                text("SELECT count(*) FROM dining_allocations WHERE receipt_id=:id"),
                {"id": receipt_id},
            )
            == 0
        )
        assert (
            await observer.scalar(
                text("SELECT status FROM dining_receipts WHERE id=:id"),
                {"id": receipt_id},
            )
            == "verified"
        )
    async with flow.graph.unit() as unit:
        await unit.grant(
            membership_id=flow.graph.base + 38,
            capability="finance.read",
            actor_kind="human",
            active=False,
        )
        await unit.grant(
            membership_id=flow.graph.base + 38,
            capability="invoices.create",
            actor_kind="human",
            active=False,
        )
        await unit.grant(
            membership_id=flow.graph.base + 38,
            capability="invoices.finalize",
            actor_kind="human",
            active=False,
        )
    assert "invoices" not in await flow.workspace()
    assert (
        await flow.command(
            operation="finalize_invoice", invoice_id=invoice_id, expected_revision=1
        )
    ).status_code == 403


# ==============================================
# TEST ZERO TARIFF WORKSPACE ROUND TRIP
# Numeric zero must remain exact decimal text accepted by the browser contract.
# ==============================================


async def test_zero_tariff_workspace_uses_fixed_decimal_text(flow: SignedFlow) -> None:
    """Persist a free preparation rate through HTTP and re-read its exact value."""
    await flow.login(actor="owner")
    response = await flow.command(
        operation="tariff",
        data={
            "reference": "zero-preparation-regression",
            "component": "preparation",
            "currency": "DZD",
            "unit": "flat",
            "unit_price": "0",
            "valid_from": "2026-11-01T00:00:00Z",
            "valid_until": None,
        },
    )
    assert response.status_code == 200, response.text
    snapshot = await flow.workspace()
    tariff = next(
        row for row in snapshot["tariffs"] if row["id"] == response.json()["identifier"]
    )
    assert tariff["unit_price"] == "0.00000000"
    assert Decimal(tariff["unit_price"]) == Decimal(0)
