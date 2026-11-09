# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# SIGNED QR TO REAL VISIT REHEARSAL
# Exercise actual routes, commits, kitchen permissions and independent database observers.
# ==============================================

"""All identities, tariffs, money facts and data belong to one disposable local fixture."""

from __future__ import annotations

# isort: split
# ==============================================
# REAL HTTP FIXTURE AND BOUNDED SOURCE DATA
# No mocked business methods, remote targets or outer rollback fixture can hide partial writes.
# ==============================================

import asyncio
import secrets
from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import text

from app.schemas.dining import TariffInput
from tests.dining.test_signed_http import (
    SignedFlow,
    confirmed,
)
from tests.dining.test_signed_http import flow as flow  # noqa: PLC0414

# ==============================================
# DELIBERATE STORAGE FAILURE CONTRACT
# Distinguish injected persistence failure from a caller type or validation mistake.
# ==============================================


class SnapshotStorageFailure(RuntimeError):
    """Represent one deliberate local storage fault after otherwise valid writes."""


pytestmark = pytest.mark.dining_postgres
PUBLIC = "/local-d1/dining/public"

# ==============================================
# OWNER-PUBLISHED EXACT MENU AND TABLE LINK
# Synthetic tariff configuration stays in the fixture and is never a migration seed.
# ==============================================


async def published(*, flow: SignedFlow) -> tuple[str, int, int]:
    """Configure explicit exact public prices and independent branch powers through existing service."""
    await flow.login(actor="owner")
    state = await flow.workspace()
    product = state["products"][0]["id"]
    async with flow.graph.unit() as unit:
        await unit.create_tariff(
            data=TariffInput(
                reference="public-product:" + str(product),
                component="menu",
                currency="DZD",
                unit="per_item",
                unit_price=Decimal("125.125"),
                valid_from=flow.graph.clock.value - timedelta(days=1),
                valid_until=None,
            )
        )
        for member, cap in [
            (31, "orders.read"),
            (31, "orders.approve"),
            (31, "orders.complete"),
            (32, "orders.read"),
            (32, "orders.prepare"),
            (38, "documents.issue"),
            (30, "documents.issue"),
        ]:
            await unit.grant(
                membership_id=flow.graph.base + member,
                capability=cap,
                actor_kind="human",
                active=True,
            )
    async with flow.graph.factory() as session, session.begin():
        await session.execute(
            text(
                "INSERT INTO features(id,name,code) VALUES (6,'Synthetic orders only','synthetic-orders') ON CONFLICT (id) DO NOTHING"
            )
        )
    response = await flow.client.post(
        flow.root + "/public-links",
        json={
            "operation": "rotate",
            "kind": "table",
            "resource_id": flow.graph.table_id,
            "public_physical_state": True,
            "reason": "Explicit public physical state for local rehearsal",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["public_id"], response.json()["identifier"], product


# ==============================================
# CUSTOMER READ AND SIGNAL
# The QR and even a client signal cannot move the actual table or approve a visit.
# ==============================================


async def signalled(*, flow: SignedFlow, public_id: str, token: str) -> int:
    """Use a separate tab secret and verify signal idempotency."""
    response = await flow.client.post(
        PUBLIC + "/presence",
        json={"public_id": public_id, "party_size": 4},
        headers={"X-Visit-Token": token},
    )
    assert response.status_code == 200, response.text
    return response.json()["identifier"]


# ==============================================
# STAFF OBSERVATION AND INSTALLATION
# Reuse independent D1 service proof and the actual route-owned occupation transaction.
# ==============================================


async def installed(*, flow: SignedFlow, public_id: str, token: str) -> tuple[int, int]:
    """An authorized human, not the QR bearer, creates the real occupation and visit."""
    presence = await signalled(flow=flow, public_id=public_id, token=token)
    await flow.login(actor="service")
    response = await flow.client.post(
        flow.root + "/presence/install",
        json={
            "presence_id": presence,
            "expected_end": "2026-11-03T19:00:00Z",
            "request_id": None,
            "observed": True,
        },
    )
    assert response.status_code == 200, response.text
    state = await flow.workspace()
    visit = next(
        row for row in state["visits"] if row["id"] == response.json()["identifier"]
    )
    return visit["id"], visit["occupation_id"]


# ==============================================
# EXACT CUSTOMER ORDER INPUT
# No price, payment or kitchen-approval field is supplied by the visitor.
# ==============================================


async def order_input(
    *, flow: SignedFlow, public_id: str, product: int
) -> dict[str, object]:
    """Read the actual reviewed menu digest and select an integer quantity."""
    menu = await flow.client.post(
        PUBLIC + "/menu", json={"public_id": public_id, "currency": "DZD"}
    )
    assert menu.status_code == 200, menu.text
    return {
        "public_id": public_id,
        "currency": "DZD",
        "menu_digest": menu.json()["menu_digest"],
        "idempotency_key": "same-submission-0001",
        "lines": [{"product_id": product, "quantity": 2}],
    }


# ==============================================
# COMPLETE PERSISTED SERVICE JOURNEY
# Separate visit requests, staff/kitchen approvals, exact invoice and physical cleaning.
# ==============================================


async def test_qr_visit_order_invoice_departure_cleaning(flow: SignedFlow) -> None:
    """Prove the nominal path and replay behavior through real signed HTTP routes."""
    public_id, _link_id, product = await published(flow=flow)
    token = secrets.token_urlsafe(32)
    menu = await flow.client.post(
        PUBLIC + "/menu", json={"public_id": public_id, "currency": "DZD"}
    )
    assert menu.status_code == 200, menu.text
    assert (
        menu.json()["table"]["code"] == "T1"
        and menu.json()["scan_confirms_presence"] is False
    )
    unselected = await flow.client.post(PUBLIC + "/menu", json={"public_id": public_id})
    assert unselected.status_code == 200 and unselected.json()["currency"] is None
    assert unselected.json()["currencies"] == ["DZD", "JPY", "USD"]
    assert all(
        not row["orderable"] and row["unit_price"] is None
        for row in unselected.json()["products"]
    )
    assert menu.json()["products"][0]["unit_price"] == "125.12500000"
    async with flow.graph.factory() as session:
        assert (
            await session.scalar(
                text(
                    "SELECT count(*) FROM dining_presence_signals WHERE restaurant_id=:r"
                ),
                {"r": flow.graph.base + 200},
            )
            == 0
        )
        assert (
            await session.scalar(
                text("SELECT physical_state FROM dining_tables WHERE id=:id"),
                {"id": flow.graph.table_id},
            )
            == "available"
        )
    await installed(flow=flow, public_id=public_id, token=token)
    data = await order_input(flow=flow, public_id=public_id, product=product)
    headers = {"X-Visit-Token": token}
    responses = await asyncio.gather(
        *(
            flow.client.post(PUBLIC + "/orders", json=data, headers=headers)
            for _ in range(2)
        )
    )
    assert [r.status_code for r in responses] == [200, 200], [r.text for r in responses]
    identifier = responses[0].json()["identifier"]
    assert {r.json()["identifier"] for r in responses} == {identifier}
    assert Decimal(responses[0].json()["total"]) == Decimal("250.25")
    # Service has no kitchen power, and kitchen has no service approval.
    response = await flow.client.post(
        flow.root + "/visit-orders/transition",
        json={"order_id": identifier, "action": "prepare", "observed": True},
    )
    assert response.status_code == 403
    response = await flow.client.post(
        flow.root + "/visit-orders/transition",
        json={"order_id": identifier, "action": "approve", "observed": True},
    )
    assert response.status_code == 200, response.text
    await flow.login(actor="cleaner")
    inbox = await flow.workspace()
    assert inbox["event_transport"] == "local-persisted-no-delivery"
    assert all(
        row["kind"].startswith(("visit.order.", "occupation.departure", "cleaning."))
        for row in inbox["service_events"]
    )
    assert "token_hash" not in str(inbox["service_events"])
    for action in ["prepare", "ready"]:
        response = await flow.client.post(
            flow.root + "/visit-orders/transition",
            json={"order_id": identifier, "action": action, "observed": True},
        )
        assert response.status_code == 200, response.text
    response = await flow.client.post(
        flow.root + "/visit-orders/transition",
        json={"order_id": identifier, "action": "served", "observed": True},
    )
    assert response.status_code == 403
    await flow.login(actor="service")
    for _ in range(2):
        response = await flow.client.post(
            flow.root + "/visit-orders/transition",
            json={"order_id": identifier, "action": "served", "observed": True},
        )
        assert response.status_code == 200, response.text
    state = await flow.workspace()
    occupation = state["visits"][0]["occupation_id"]
    await flow.login(actor="finance")
    state = await flow.workspace()
    source = next(row for row in state["visit_orders"] if row["order_id"] == identifier)
    line = source["exact_lines"][0]
    invoice = await flow.command(
        operation="invoice",
        data={
            "occupation_id": occupation,
            "currency": "DZD",
            "lines": [
                {
                    "order_id": identifier,
                    "order_item_id": line["order_item_id"],
                    "description": line["description"],
                    "quantity": line["quantity"],
                    "unit_price": line["unit_price"],
                    "source_reference": "tariff:" + str(line["tariff_id"]),
                }
            ],
            "currency_source": "Exact published DZD tariff",
            "rounding_source": "Final HALF_UP 2",
            "reconciliation_reference": "Disposable visit rehearsal",
            "legacy_discrepancies_acknowledged": False,
        },
    )
    assert invoice.status_code == 200, invoice.text
    invoice_id = invoice.json()["identifier"]
    final = await flow.command(
        operation="finalize_invoice", invoice_id=invoice_id, expected_revision=1
    )
    assert final.status_code == 200, final.text
    issued = await flow.client.post(
        flow.root + "/public-links",
        json={"operation": "issue", "kind": "food_invoice", "resource_id": invoice_id},
    )
    assert issued.status_code == 200, issued.text
    reprint = await flow.client.post(
        flow.root + "/public-links",
        json={"operation": "issue", "kind": "food_invoice", "resource_id": invoice_id},
    )
    assert reprint.json() == issued.json()
    verified = await flow.client.post(
        PUBLIC + "/verify", json={"public_id": issued.json()["public_id"]}
    )
    assert verified.json()["status"] == "valid" and "total" not in verified.json()
    for locale in ["fr", "en", "ar"]:
        printed = await flow.client.get(
            flow.root
            + f'/public-links/{issued.json()["identifier"]}/print?locale={locale}'
        )
        assert (
            printed.status_code == 200
            and "<svg" in printed.text
            and f'lang="{locale}"' in printed.text
        )
        assert ('dir="rtl"' in printed.text) == (locale == "ar")
    # Only actual departure ends ordering; a planned end is not an automatic release.
    await flow.login(actor="cleaner")
    response = await flow.command(operation="departure", occupation_id=occupation)
    assert response.status_code == 200, response.text
    denied = await flow.client.post(
        PUBLIC + "/orders",
        json={**data, "idempotency_key": "after-departure-0001"},
        headers=headers,
    )
    assert denied.status_code == 409
    ended = await flow.client.post(
        PUBLIC + "/visit", json={"public_id": public_id}, headers=headers
    )
    assert ended.status_code == 200 and ended.json() == {
        "status": "ended",
        "orders": [],
    }
    for action in ["start_cleaning", "finish_cleaning"]:
        response = await flow.command(operation=action, occupation_id=occupation)
        assert response.status_code == 200, response.text
    async with flow.graph.factory() as session:
        assert (
            await session.scalar(
                text("SELECT physical_state FROM dining_tables WHERE id=:id"),
                {"id": flow.graph.table_id},
            )
            == "available"
        )
        assert (
            await session.scalar(
                text("SELECT count(*) FROM dining_visit_orders WHERE restaurant_id=:r"),
                {"r": flow.graph.base + 200},
            )
            == 1
        )
        assert (
            await session.scalar(
                text("SELECT count(*) FROM dining_allocations WHERE invoice_id=:id"),
                {"id": invoice_id},
            )
            == 0
        )
        assert await session.scalar(
            text("SELECT total FROM dining_invoices WHERE id=:id"), {"id": invoice_id}
        ) == Decimal("250.25")


# ==============================================
# INVALID, REVOKED AND UNINSTALLED QR SAFETY
# A copied public reference or secret never supplies another visit or staff authority.
# ==============================================


async def test_public_link_revocation_and_direct_order_refusal(
    flow: SignedFlow,
) -> None:
    """Keep old QR invalid, disable ordering immediately and retain all prior evidence."""
    public_id, _link_id, product = await published(flow=flow)
    token = secrets.token_urlsafe(32)
    data = await order_input(flow=flow, public_id=public_id, product=product)
    denied = await flow.client.post(
        PUBLIC + "/orders", json=data, headers={"X-Visit-Token": token}
    )
    assert denied.status_code == 409
    first = await signalled(flow=flow, public_id=public_id, token=token)
    assert await signalled(flow=flow, public_id=public_id, token=token) == first
    await flow.login(actor="cleaner")
    denied = await flow.client.post(
        flow.root + "/presence/install",
        json={
            "presence_id": first,
            "expected_end": "2026-11-03T19:00:00Z",
            "observed": True,
        },
    )
    assert denied.status_code == 403
    await installed(flow=flow, public_id=public_id, token=token)
    other = await flow.client.post(
        PUBLIC + "/visit",
        json={"public_id": public_id},
        headers={"X-Visit-Token": secrets.token_urlsafe(32)},
    )
    assert other.json() == {"status": "not_signalled", "orders": []}
    await flow.login(actor="owner")
    rotation = await flow.client.post(
        flow.root + "/public-links",
        json={
            "operation": "rotate",
            "kind": "table",
            "resource_id": flow.graph.table_id,
            "reason": "compromised print",
        },
    )
    assert (
        rotation.status_code == 200 and rotation.json()["public_id"] != public_id
    ), rotation.text
    denied = await flow.client.post(
        PUBLIC + "/menu", json={"public_id": public_id, "currency": "DZD"}
    )
    assert denied.status_code == 409
    denied = await flow.client.post(
        PUBLIC + "/orders", json=data, headers={"X-Visit-Token": token}
    )
    assert denied.status_code == 409
    verified = await flow.client.post(PUBLIC + "/verify", json={"public_id": public_id})
    assert verified.json()["status"] == "invalidated"
    invalid = await flow.client.post(
        PUBLIC + "/verify", json={"public_id": secrets.token_urlsafe(32)}
    )
    assert invalid.json() == {"status": "invalid"}


# ==============================================
# CANCELLED ISSUED RESERVATION
# Retained historical content stays intact while the public verifier reports current cancellation.
# ==============================================


async def test_issued_reservation_cancellation_invalidates_status(
    flow: SignedFlow,
) -> None:
    """Issue an existing supported document, cancel it and inspect current redacted validity."""
    request_id, _quote, receipt_id, _token = await confirmed(flow=flow)
    async with flow.graph.unit() as unit:
        await unit.grant(
            membership_id=flow.graph.base + 31,
            capability="documents.issue",
            actor_kind="human",
            active=True,
        )
    response = await flow.client.post(
        flow.root + "/public-links",
        json={"operation": "issue", "kind": "reservation", "resource_id": request_id},
    )
    assert response.status_code == 200, response.text
    public_id = response.json()["public_id"]
    await flow.login(actor="finance_reader")
    private_print = await flow.client.get(
        flow.root + f"/public-links/{response.json()['identifier']}/print?locale=fr"
    )
    assert private_print.status_code == 403
    minimal = await flow.client.post(PUBLIC + "/verify", json={"public_id": public_id})
    assert minimal.status_code == 200 and minimal.json()["status"] == "valid"
    assert "customer" not in minimal.json() and "total" not in minimal.json()
    await flow.login(actor="canceller")
    result = await flow.command(
        operation="cancel_before_arrival",
        request_id=request_id,
        reason="Local cancellation test",
        origin="customer",
    )
    assert result.status_code == 200, result.text
    verified = await flow.client.post(PUBLIC + "/verify", json={"public_id": public_id})
    assert verified.json()["status"] == "cancelled"
    async with flow.graph.factory() as session:
        assert (
            await session.scalar(
                text("SELECT count(*) FROM dining_receipts WHERE id=:id"),
                {"id": receipt_id},
            )
            == 1
        )


# ==============================================
# FOREIGN TARGET AND CURRENT ROLE REFUSALS
# Direct HTTP calls cannot use another establishment's resource or retain revoked grants.
# ==============================================


async def test_foreign_targets_and_current_order_grant(flow: SignedFlow) -> None:
    """Cross-scope IDs and a revoked power fail even with the same valid signed cookie."""
    public_id, _link, product = await published(flow=flow)
    token = secrets.token_urlsafe(32)
    _visit, occupation = await installed(flow=flow, public_id=public_id, token=token)
    data = await order_input(flow=flow, public_id=public_id, product=product)
    response = await flow.client.post(
        PUBLIC + "/orders", json=data, headers={"X-Visit-Token": token}
    )
    assert response.status_code == 200, response.text
    identifier = response.json()["identifier"]
    await flow.login(actor="outsider")
    refused = await flow.client.post(
        flow.root + "/visit-orders/transition",
        json={"order_id": identifier, "action": "approve", "observed": True},
    )
    assert refused.status_code == 403
    refused = await flow.client.post(
        flow.root + "/public-links",
        json={
            "operation": "issue",
            "kind": "table",
            "resource_id": flow.graph.table_id,
        },
    )
    assert refused.status_code == 403
    await flow.login(actor="service")
    async with flow.graph.unit() as unit:
        await unit.grant(
            membership_id=flow.graph.base + 31,
            capability="orders.approve",
            actor_kind="human",
            active=False,
        )
    refused = await flow.client.post(
        flow.root + "/visit-orders/transition",
        json={"order_id": identifier, "action": "approve", "observed": True},
    )
    assert refused.status_code == 403
    # A valid table QR for T2 does not authorize T1's already-installed visit.
    await flow.login(actor="owner")
    second = await flow.client.post(
        flow.root + "/public-links",
        json={
            "operation": "issue",
            "kind": "table",
            "resource_id": flow.graph.second_table_id,
        },
    )
    assert second.status_code == 200, second.text
    refused = await flow.client.post(
        PUBLIC + "/orders",
        json={**data, "public_id": second.json()["public_id"]},
        headers={"X-Visit-Token": token},
    )
    assert refused.status_code == 409
    async with flow.graph.factory() as session:
        assert (
            await session.scalar(
                text("SELECT status FROM orders WHERE id=:id"), {"id": identifier}
            )
            == "pending"
        )
        assert (
            await session.scalar(
                text("SELECT status FROM dining_occupations WHERE id=:id"),
                {"id": occupation},
            )
            == "occupied"
        )


# ==============================================
# EXPIRED SIGNAL AND INVALID HUMAN OBSERVATION
# A signal's technical lifetime is separate from the customer's real physical occupation.
# ==============================================


async def test_expired_signal_and_false_observation_do_not_install(
    flow: SignedFlow,
) -> None:
    """Reject stale or unobserved installation without changing the table or creating a visit."""
    public_id, _link, _product = await published(flow=flow)
    presence = await signalled(
        flow=flow, public_id=public_id, token=secrets.token_urlsafe(32)
    )
    await flow.login(actor="service")
    for observed in [False, 1]:
        response = await flow.client.post(
            flow.root + "/presence/install",
            json={
                "presence_id": presence,
                "expected_end": "2026-11-03T19:00:00Z",
                "observed": observed,
            },
        )
        assert response.status_code in {409, 422}
    flow.graph.clock.value += timedelta(minutes=15)
    response = await flow.client.post(
        flow.root + "/presence/install",
        json={
            "presence_id": presence,
            "expected_end": "2026-11-03T19:00:00Z",
            "observed": True,
        },
    )
    assert response.status_code == 409
    async with flow.graph.factory() as session:
        assert (
            await session.scalar(
                text("SELECT physical_state FROM dining_tables WHERE id=:id"),
                {"id": flow.graph.table_id},
            )
            == "available"
        )
        assert (
            await session.scalar(
                text("SELECT count(*) FROM dining_visits WHERE restaurant_id=:r"),
                {"r": flow.graph.base + 200},
            )
            == 0
        )


# ==============================================
# IDEMPOTENCY CONTENT AND AUTHORITATIVE SOURCE FAILURE
# A reused nonce cannot substitute another cart, stale menu or caller-chosen amount.
# ==============================================


async def test_changed_cart_menu_and_exact_invoice_are_refused(
    flow: SignedFlow,
) -> None:
    """Retain one exact order and refuse both stale inputs and a rewritten invoice unit price."""
    public_id, _link, product = await published(flow=flow)
    token = secrets.token_urlsafe(32)
    _visit, occupation = await installed(flow=flow, public_id=public_id, token=token)
    data = await order_input(flow=flow, public_id=public_id, product=product)
    headers = {"X-Visit-Token": token}
    response = await flow.client.post(
        PUBLIC + "/orders", json={**data, "menu_digest": "0" * 64}, headers=headers
    )
    assert response.status_code == 409
    response = await flow.client.post(PUBLIC + "/orders", json=data, headers=headers)
    assert response.status_code == 200, response.text
    identifier = response.json()["identifier"]
    changed = await flow.client.post(
        PUBLIC + "/orders",
        json={**data, "lines": [{"product_id": product, "quantity": 3}]},
        headers=headers,
    )
    assert changed.status_code == 409
    for actor, actions in [
        ("service", ["approve"]),
        ("cleaner", ["prepare", "ready"]),
        ("service", ["served"]),
    ]:
        await flow.login(actor=actor)
        for action in actions:
            result = await flow.client.post(
                flow.root + "/visit-orders/transition",
                json={"order_id": identifier, "action": action, "observed": True},
            )
            assert result.status_code == 200, result.text
    await flow.login(actor="finance")
    state = await flow.workspace()
    source = state["visit_orders"][0]
    line = source["exact_lines"][0]
    wrong = await flow.command(
        operation="invoice",
        data={
            "occupation_id": occupation,
            "currency": "DZD",
            "lines": [
                {
                    "order_id": identifier,
                    "order_item_id": line["order_item_id"],
                    "description": line["description"],
                    "quantity": line["quantity"],
                    "unit_price": "1",
                    "source_reference": "tampered",
                }
            ],
            "currency_source": "DZD exact source",
            "rounding_source": "Final HALF_UP",
            "reconciliation_reference": "Deliberate refusal",
            "legacy_discrepancies_acknowledged": True,
        },
    )
    assert (
        wrong.status_code == 409
        and wrong.json()["detail"]["code"]
        == "dining_visit_invoice_exact_source_mismatch"
    )
    async with flow.graph.factory() as session:
        assert (
            await session.scalar(
                text("SELECT count(*) FROM dining_invoices WHERE occupation_id=:id"),
                {"id": occupation},
            )
            == 0
        )
        assert (
            await session.scalar(
                text("SELECT count(*) FROM dining_visit_orders WHERE restaurant_id=:r"),
                {"r": flow.graph.base + 200},
            )
            == 1
        )


# ==============================================
# FAILURE AFTER LEGACY ORDER PERSISTENCE
# An injected late storage failure proves the service owns rollback, not a fixture wrapper.
# ==============================================


async def test_exact_order_failure_rolls_back_legacy_order_and_metrics(
    flow: SignedFlow, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Observe committed SQL from another session after the real route fails after order creation."""
    from app.models.dining_service import DiningVisitOrder
    from app.repositories.dining_repo import (
        DiningRecord,
        DiningRepository,
    )

    public_id, _link, product = await published(flow=flow)
    token = secrets.token_urlsafe(32)
    await installed(flow=flow, public_id=public_id, token=token)
    data = await order_input(flow=flow, public_id=public_id, product=product)
    original = DiningRepository.persist

    # ==============================================
    # FAIL EXACT
    # Inject only the authorized storage failure, after the legacy writes were attempted.
    # ==============================================

    async def fail_exact(
        self: DiningRepository, *, record: DiningRecord
    ) -> DiningRecord:
        """Inject only the authorized storage failure, after the legacy writes were attempted."""
        if isinstance(record, DiningVisitOrder):
            # A storage failure is deliberate after a correctly typed record.
            raise SnapshotStorageFailure("local_exact_snapshot_fault")
        return await original(self, record=record)

    async with flow.graph.factory() as session:
        before = await session.scalar(
            text("SELECT count(*) FROM orders WHERE restaurant_id=:r"),
            {"r": flow.graph.base + 200},
        )
        usage = await session.scalar(
            text(
                "SELECT coalesce(sum(usage_count),0) FROM feature_usage_counters WHERE restaurant_id=:r"
            ),
            {"r": flow.graph.base + 200},
        )
    monkeypatch.setattr(DiningRepository, "persist", fail_exact)
    response = await flow.client.post(
        PUBLIC + "/orders", json=data, headers={"X-Visit-Token": token}
    )
    assert response.status_code == 500
    async with flow.graph.factory() as session:
        assert (
            await session.scalar(
                text("SELECT count(*) FROM orders WHERE restaurant_id=:r"),
                {"r": flow.graph.base + 200},
            )
            == before
        )
        assert (
            await session.scalar(
                text(
                    "SELECT coalesce(sum(usage_count),0) FROM feature_usage_counters WHERE restaurant_id=:r"
                ),
                {"r": flow.graph.base + 200},
            )
            == usage
        )
        assert (
            await session.scalar(
                text("SELECT count(*) FROM dining_visit_orders WHERE restaurant_id=:r"),
                {"r": flow.graph.base + 200},
            )
            == 0
        )


# ==============================================
# LIVE METADATA AND DISABLED PHYSICAL TABLE
# The permanent reference resolves current location while disabled tables reject public reads.
# ==============================================


async def test_table_link_reprint_metadata_and_disable(flow: SignedFlow) -> None:
    """A reprint retains its reference; live metadata is not copied into the QR payload."""
    from app.schemas.dining import TableInput

    public_id, link, _product = await published(flow=flow)
    state = await flow.workspace()
    table = next(row for row in state["tables"] if row["id"] == flow.graph.table_id)
    keys = set(TableInput.model_fields)
    current = {key: value for key, value in table.items() if key in keys}
    current["trait_ids"] = []
    current["floor_label"] = "Second floor"
    current["room_label"] = "Salon local"
    async with flow.graph.unit() as unit:
        await unit.update_table(
            table_id=flow.graph.table_id,
            data=TableInput.model_validate(current),
            acknowledge_conflicts=False,
        )
    menu = await flow.client.post(
        PUBLIC + "/menu", json={"public_id": public_id, "currency": "DZD"}
    )
    assert menu.status_code == 200 and menu.json()["table"]["floor"] == "Second floor"
    reprint = await flow.client.post(
        flow.root + "/public-links",
        json={
            "operation": "issue",
            "kind": "table",
            "resource_id": flow.graph.table_id,
            "public_physical_state": True,
        },
    )
    assert reprint.json()["identifier"] == link
    current["in_service"] = False
    async with flow.graph.unit() as unit:
        await unit.update_table(
            table_id=flow.graph.table_id,
            data=TableInput.model_validate(current),
            acknowledge_conflicts=False,
        )
    menu = await flow.client.post(
        PUBLIC + "/menu", json={"public_id": public_id, "currency": "DZD"}
    )
    assert menu.status_code == 409


# ==============================================
# EVERY TABLE HAS A PERMANENT READ TARGET
# Existing-table migration backfill is idempotent and cannot re-enable an already revoked link.
# ==============================================


async def test_automatic_table_qr_and_legacy_backfill(flow: SignedFlow) -> None:
    """Cover new tables, representative historical data and retained immutable public identities."""
    from migration_support.dining_d1d import backfill_table_links

    await flow.login(actor="owner")
    state = await flow.workspace()
    table_links = [row for row in state["public_links"] if row["kind"] == "table"]
    assert {row["table_id"] for row in table_links} == {
        flow.graph.table_id,
        flow.graph.second_table_id,
    }
    legacy = flow.graph.base + 900
    async with flow.graph.factory() as session, session.begin():
        await session.execute(
            text(
                "INSERT INTO public.dining_tables SELECT (jsonb_populate_record(NULL::public.dining_tables,to_jsonb(t)||jsonb_build_object('id',CAST(:new AS integer),'code','LEGACY-QR'))).* FROM public.dining_tables t WHERE t.id=:id"
            ),
            {"new": legacy, "id": flow.graph.table_id},
        )
        connection = await session.connection()
        assert (
            await connection.run_sync(
                lambda sync: backfill_table_links(connection=sync)
            )
            == 1
        )
        assert (
            await connection.run_sync(
                lambda sync: backfill_table_links(connection=sync)
            )
            == 0
        )
    async with flow.graph.factory() as observer:
        row = (
            (
                await observer.execute(
                    text(
                        "SELECT public_id,snapshot,digest FROM dining_public_links WHERE table_id=:id"
                    ),
                    {"id": legacy},
                )
            )
            .mappings()
            .one()
        )
        from app.services.business.dining.values import content_digest

        assert row["snapshot"]["public_physical_state"] is False
        assert row["digest"] == content_digest(value=row["snapshot"])
        public_id = row["public_id"]
    menu = await flow.client.post(PUBLIC + "/menu", json={"public_id": public_id})
    assert menu.status_code == 200 and menu.json()["table"]["code"] == "LEGACY-QR"
    assert menu.json()["table"]["physical_state"] is None


# ==============================================
# TABLE AND QR CREATION SHARE ONE COMMIT
# A late QR storage fault must not leave a table without its permanent reference.
# ==============================================


async def test_failed_automatic_qr_rolls_back_new_table(
    flow: SignedFlow, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Inspect committed rows independently after the actual configuration route fails."""
    from app.models.dining_service import DiningPublicLink
    from app.repositories.dining_repo import DiningRecord, DiningRepository
    from app.schemas.dining import TableInput

    await flow.login(actor="owner")
    source = (await flow.workspace())["tables"][0]
    values = {key: source[key] for key in TableInput.model_fields if key in source}
    values.update({"code": "QR-ROLLBACK", "trait_ids": []})
    original = DiningRepository.persist

    # ==============================================
    # DELIBERATE LATE QR WRITE FAILURE
    # Keep the earlier real table insert and transaction boundary active until this fault.
    # ==============================================

    async def fail_link(
        self: DiningRepository, *, record: DiningRecord
    ) -> DiningRecord:
        """Fail only immutable-link persistence after the new table was flushed."""
        if isinstance(record, DiningPublicLink):
            raise SnapshotStorageFailure("local_table_qr_fault")
        return await original(self, record=record)

    monkeypatch.setattr(DiningRepository, "persist", fail_link)
    response = await flow.command(
        operation="table", initial_state="available", data=values
    )
    assert response.status_code == 500
    async with flow.graph.factory() as observer:
        assert (
            await observer.scalar(
                text(
                    "SELECT count(*) FROM dining_tables WHERE restaurant_id=:r AND code='QR-ROLLBACK'"
                ),
                {"r": flow.graph.base + 200},
            )
            == 0
        )
        assert (
            await observer.scalar(
                text(
                    "SELECT count(*) FROM dining_public_links WHERE restaurant_id=:r AND kind='table'"
                ),
                {"r": flow.graph.base + 200},
            )
            == 2
        )
