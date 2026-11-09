# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# DINING AUTHORITY, CONCURRENCY AND DELIVERY REGRESSIONS
# Assert persisted outcomes using independent sessions and real local constraints.
# ==============================================

"""Disposable PostgreSQL only; transports and customer identities are synthetic."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND EXPLICIT PROFILE
# Reuse committed graphs rather than an enclosing transaction that hides defects.
# ==============================================

import asyncio
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.security.tenant_types import TenantAccessDenied
from app.schemas.dining import JsonObject
from app.services.business.dining.notifications import (
    DefinitelyNotDelivered,
    DeliveryAcknowledgement,
    dispatch_outbox,
)
from app.services.business.dining.tickets import (
    ticket_svg,
    verify_ticket,
)
from app.services.business.dining.values import (
    DiningError,
    Period,
)
from tests.dining.support import (
    DiningGraph,
    accept_and_hold,
    configure_graph,
    create_graph,
    create_request_quote,
    receive_advance,
)
from tests.dining.test_invoices import invoicing_graph

pytestmark = pytest.mark.dining_postgres


# ==============================================
# PROOF
# Commit a current human proof before testing assistant authority separately.
# ==============================================


async def proof(*, graph: DiningGraph, request_id: int) -> None:
    """Commit a current human proof before testing assistant authority separately."""
    async with graph.unit(actor="service") as unit:
        await unit.confirm_availability(
            table_ids=(graph.table_id,),
            period=Period(
                start=datetime(2026, 11, 3, 20, tzinfo=timezone.utc),
                end=datetime(2026, 11, 3, 21, 30, tzinfo=timezone.utc),
            ),
            request_id=request_id,
        )


# ==============================================
# TEST CONCURRENT HOLDS CHOOSE ONE AND DATABASE REFUSES OVERLAP
# Two accepted proposals compete; one committed claim wins without duplication.
# ==============================================


async def test_concurrent_holds_choose_one_and_database_refuses_overlap(
    dining_engine: AsyncEngine,
) -> None:
    """Two accepted proposals compete; one committed claim wins without duplication."""
    graph = await configure_graph(graph=await create_graph(engine=dining_engine))
    first, second = await create_request_quote(graph=graph), await create_request_quote(
        graph=graph
    )
    outcomes = await asyncio.gather(
        *(
            accept_and_hold(graph=graph, request_id=request_id, quote_id=quote_id)
            for request_id, quote_id in (first, second)
        ),
        return_exceptions=True,
    )
    assert sum(outcome is None for outcome in outcomes) == 1
    assert sum(isinstance(outcome, DiningError) for outcome in outcomes) == 1
    async with dining_engine.connect() as observer:
        assert (
            await observer.scalar(
                text(
                    "SELECT count(*) FROM dining_claims WHERE branch_id=:id AND active"
                ),
                {"id": graph.base + 300},
            )
            == 1
        )
    with pytest.raises(IntegrityError) as refusal:
        async with dining_engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO dining_claims(restaurant_id,branch_id,table_id,starts_at,ends_at,kind,active) SELECT restaurant_id,branch_id,table_id,starts_at,ends_at,'occupation',true FROM dining_claims WHERE branch_id=:id"
                ),
                {"id": graph.base + 300},
            )
    assert refusal.value.orig.sqlstate == "23P01"


# ==============================================
# TEST SEPARATE HUMAN CAPABILITIES
# Realm role claims do not grant collection, availability or cleaning rights.
# ==============================================


@pytest.mark.parametrize(
    "actor,capability",
    [
        ("assistant", "collect"),
        ("assistant", "service"),
        ("cleaner", "service"),
        ("collector", "clean"),
    ],
)
async def test_separate_human_capabilities(
    dining_engine: AsyncEngine, actor: str, capability: str
) -> None:
    """Realm role claims do not grant collection, availability or cleaning rights."""
    graph = await configure_graph(graph=await create_graph(engine=dining_engine))
    with pytest.raises(TenantAccessDenied):
        async with graph.unit(actor=actor) as unit:
            await unit.guard(capability=capability, human=True)


# ==============================================
# TEST FOREIGN BRANCH AND RESOURCE CANNOT BE READ
# A valid principal cannot substitute a foreign branch or scoped table ID.
# ==============================================


async def test_foreign_branch_and_resource_cannot_be_read(
    dining_engine: AsyncEngine,
) -> None:
    """A valid principal cannot substitute a foreign branch or scoped table ID."""
    graph = await configure_graph(graph=await create_graph(engine=dining_engine))
    other = await configure_graph(graph=await create_graph(engine=dining_engine))
    with pytest.raises(DiningError, match="unavailable"):
        async with graph.unit() as unit:
            await unit.tables(identifiers=(other.table_id,))
    async with graph.factory() as session:
        from app.services.business.dining.service import DiningService

        arguments = graph.arguments()
        arguments["branch_id"] = other.base + 300
        with pytest.raises(TenantAccessDenied):
            async with DiningService(session=session, clock=graph.clock).authorized(
                **arguments
            ):
                pytest.fail("Foreign branch admitted")


# ==============================================
# TEST ATYPICAL RECEIPT RETAINED WITHOUT BOOKING
# Actual funds survive refused finalization; amounts/currencies are not repaired.
# ==============================================


@pytest.mark.parametrize(
    "amount,currency",
    [(Decimal(1400), "DZD"), (Decimal(1600), "DZD"), (Decimal(1500), "USD")],
)
async def test_atypical_receipt_retained_without_booking(
    dining_engine: AsyncEngine, amount: Decimal, currency: str
) -> None:
    """Actual funds survive refused finalization; amounts/currencies are not repaired."""
    graph = await configure_graph(graph=await create_graph(engine=dining_engine))
    request_id, quote_id = await create_request_quote(graph=graph)
    await accept_and_hold(graph=graph, request_id=request_id, quote_id=quote_id)
    receipt_id = await receive_advance(
        graph=graph,
        request_id=request_id,
        quote_id=quote_id,
        amount=amount,
        currency=currency,
    )
    with pytest.raises(DiningError, match="verified_matching_receipt"):
        async with graph.unit(actor="service") as unit:
            await unit.finalize_human(
                request_id=request_id, quote_id=quote_id, receipt_id=receipt_id
            )
    async with dining_engine.connect() as observer:
        row = (
            await observer.execute(
                text(
                    "SELECT status,received_amount,currency FROM dining_receipts WHERE id=:id"
                ),
                {"id": receipt_id},
            )
        ).one()
        assert (row.status, row.received_amount, row.currency) == (
            "manual_review",
            amount,
            currency,
        )
        assert (
            await observer.scalar(
                text("SELECT qr_token FROM dining_requests WHERE id=:id"),
                {"id": request_id},
            )
            is None
        )


# ==============================================
# TEST EXPIRED HOLD KEEPS LATE MONEY FOR REVIEW
# Elapsed hold cannot be revived by payment or an assistant confirmation.
# ==============================================


async def test_expired_hold_keeps_late_money_for_review(
    dining_engine: AsyncEngine,
) -> None:
    """Elapsed hold cannot be revived by payment or an assistant confirmation."""
    graph = await configure_graph(graph=await create_graph(engine=dining_engine))
    request_id, quote_id = await create_request_quote(graph=graph)
    await accept_and_hold(graph=graph, request_id=request_id, quote_id=quote_id)
    graph.clock.value += timedelta(hours=2)
    receipt_id = await receive_advance(
        graph=graph, request_id=request_id, quote_id=quote_id
    )
    async with dining_engine.connect() as observer:
        assert (
            await observer.scalar(
                text("SELECT status FROM dining_receipts WHERE id=:id"),
                {"id": receipt_id},
            )
            == "manual_review"
        )
        assert (
            await observer.scalar(
                text(
                    "SELECT count(*) FROM dining_claims WHERE request_id=:id AND active"
                ),
                {"id": request_id},
            )
            == 0
        )


# ==============================================
# SIMULATEDTRANSPORT
# Explicit fake; no network operation or production channel exists.
# ==============================================


class SimulatedTransport:
    """Explicit fake; no network operation or production channel exists."""

    def __init__(self, *, graph: DiningGraph, outcome: str = "delivered") -> None:
        self.graph, self.outcome, self.keys = graph, outcome, []

    # ==============================================
    # DELIVER
    # Observe committed jobs; return an explicit fake delivery acknowledgement.
    # ==============================================

    async def deliver(
        self, *, key: str, target: str, payload: JsonObject
    ) -> DeliveryAcknowledgement:
        """Observe committed jobs; return an explicit fake delivery acknowledgement."""
        self.keys.append(key)
        if self.outcome == "failed":
            raise DefinitelyNotDelivered
        if self.outcome == "uncertain":
            raise TimeoutError
        return DeliveryAcknowledgement(
            reference=f"synthetic:{key}", delivered_at=self.graph.clock.value
        )


# ==============================================
# DISPATCH
# Run only the explicitly injected local fake transport.
# ==============================================


async def dispatch(
    *, graph: DiningGraph, transport: SimulatedTransport
) -> dict[str, int]:
    """Run only the explicitly injected local fake transport."""
    return await dispatch_outbox(
        factory=graph.factory,
        restaurant_id=graph.base + 200,
        branch_id=graph.base + 300,
        transport=transport,
        timeout_seconds=1,
        clock=graph.clock,
    )


# ==============================================
# TEST ASSISTANT REQUIRES ACTUAL DELIVERY TIMEOUT AND HUMAN PROOF
# Silence, enqueue and realm roles alone never approve a reservation.
# ==============================================


async def test_assistant_requires_actual_delivery_timeout_and_human_proof(
    dining_engine: AsyncEngine,
) -> None:
    """Silence, enqueue and realm roles alone never approve a reservation."""
    graph = await configure_graph(graph=await create_graph(engine=dining_engine))
    request_id, quote_id = await create_request_quote(graph=graph)
    await accept_and_hold(graph=graph, request_id=request_id, quote_id=quote_id)
    receipt_id = await receive_advance(
        graph=graph, request_id=request_id, quote_id=quote_id
    )
    await proof(graph=graph, request_id=request_id)
    with pytest.raises(DiningError, match="effective_transmission"):
        async with graph.unit(actor="assistant") as unit:
            await unit.finalize_assistant(
                request_id=request_id, quote_id=quote_id, receipt_id=receipt_id
            )
    transport = SimulatedTransport(graph=graph)
    assert (await dispatch(graph=graph, transport=transport))["delivered"] >= 1
    with pytest.raises(DiningError, match="deadline_not_elapsed"):
        async with graph.unit(actor="assistant") as unit:
            await unit.finalize_assistant(
                request_id=request_id, quote_id=quote_id, receipt_id=receipt_id
            )
    graph.clock.value += timedelta(seconds=61)
    async with graph.unit(actor="assistant") as unit:
        ticket = await unit.finalize_assistant(
            request_id=request_id, quote_id=quote_id, receipt_id=receipt_id
        )
    async with graph.factory() as session:
        assert await verify_ticket(session=session, token=str(ticket["qr_token"])) == {
            "reference": ticket["reference"],
            "status": "confirmed",
            "valid": True,
        }
    svg = ticket_svg(
        token=str(ticket["qr_token"]), verification_origin="http://127.0.0.1:5173"
    )
    assert "<svg" in svg and "<path" in svg
    assert len(transport.keys) == len(set(transport.keys))


# ==============================================
# TEST DELIVERY FAILURE NEVER PROVES TRANSMISSION
# Definite failures may retry later; ambiguous sends are not automatically retried.
# ==============================================


@pytest.mark.parametrize("outcome", ["failed", "uncertain"])
async def test_delivery_failure_never_proves_transmission(
    dining_engine: AsyncEngine, outcome: str
) -> None:
    """Definite failures may retry later; ambiguous sends are not automatically retried."""
    graph = await configure_graph(graph=await create_graph(engine=dining_engine))
    request_id, _quote_id = await create_request_quote(graph=graph)
    transport = SimulatedTransport(graph=graph, outcome=outcome)
    results = await dispatch(graph=graph, transport=transport)
    assert results[outcome] >= 1
    calls = len(transport.keys)
    async with dining_engine.connect() as observer:
        assert (
            await observer.scalar(
                text("SELECT transmitted_at FROM dining_requests WHERE id=:id"),
                {"id": request_id},
            )
            is None
        )
    await dispatch(graph=graph, transport=transport)
    assert len(transport.keys) == (calls if outcome == "uncertain" else 2 * calls)


# ==============================================
# TEST REVOKED HUMAN PROOF STOPS CONFIRMATION AND RETAINS RECEIPT
# A historical human proof does not survive revocation of its actual author.
# ==============================================


async def test_revoked_human_proof_stops_confirmation_and_retains_receipt(
    dining_engine: AsyncEngine,
) -> None:
    """A historical human proof does not survive revocation of its actual author."""
    graph = await configure_graph(graph=await create_graph(engine=dining_engine))
    request_id, quote_id = await create_request_quote(graph=graph)
    await accept_and_hold(graph=graph, request_id=request_id, quote_id=quote_id)
    receipt_id = await receive_advance(
        graph=graph, request_id=request_id, quote_id=quote_id
    )
    await proof(graph=graph, request_id=request_id)
    async with graph.unit() as unit:
        await unit.grant(
            membership_id=graph.base + 31,
            capability="service",
            actor_kind="human",
            active=False,
        )
    with pytest.raises(DiningError, match="current_human_confirmation"):
        async with graph.unit() as unit:
            await unit.finalize_human(
                request_id=request_id, quote_id=quote_id, receipt_id=receipt_id
            )
    async with dining_engine.connect() as observer:
        assert (
            await observer.scalar(
                text("SELECT count(*) FROM dining_receipts WHERE id=:id"),
                {"id": receipt_id},
            )
            == 1
        )


# ==============================================
# TEST CHANGED SOURCE BLOCKS FINALIZATION WITHOUT LOSING MONEY
# A draft cannot finalize against silently changed food quantities or options.
# ==============================================


async def test_changed_source_blocks_finalization_without_losing_money(
    dining_engine: AsyncEngine,
) -> None:
    """A draft cannot finalize against silently changed food quantities or options."""
    graph, _request_id, receipt_id, invoice_id = await invoicing_graph(
        engine=dining_engine
    )
    async with dining_engine.begin() as connection:
        await connection.execute(
            text(
                "UPDATE order_items SET quantity=2 WHERE order_id IN (SELECT order_id FROM dining_invoice_orders WHERE invoice_id=:id)"
            ),
            {"id": invoice_id},
        )
    with pytest.raises(DiningError, match="source_changed"):
        async with graph.unit(actor="owner") as unit:
            await unit.finalize_invoice(invoice_id=invoice_id, expected_revision=1)
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
        assert await observer.scalar(
            text("SELECT received_amount FROM dining_receipts WHERE id=:id"),
            {"id": receipt_id},
        ) == Decimal(1500)


# ==============================================
# TEST FINAL FINANCIAL HISTORY IS DATABASE IMMUTABLE
# Even direct SQL cannot rewrite finalized sales, receipt or applied credit.
# ==============================================


@pytest.mark.parametrize(
    "table,column,value",
    [
        ("dining_invoices", "total", "1"),
        ("dining_receipts", "received_amount", "1"),
        ("dining_allocations", "amount", "1"),
    ],
)
async def test_final_financial_history_is_database_immutable(
    dining_engine: AsyncEngine, table: str, column: str, value: str
) -> None:
    """Even direct SQL cannot rewrite finalized sales, receipt or applied credit."""
    graph, _request_id, _receipt_id, invoice_id = await invoicing_graph(
        engine=dining_engine
    )
    async with graph.unit(actor="owner") as unit:
        await unit.finalize_invoice(invoice_id=invoice_id, expected_revision=1)
    with pytest.raises(IntegrityError):
        async with dining_engine.begin() as connection:
            # All interpolated identifiers come exclusively from the fixed test cases.
            await connection.execute(
                text(f"UPDATE {table} SET {column}={value} WHERE branch_id=:id"),
                {"id": graph.base + 300},
            )


# ==============================================
# TEST INVOICE CROSS CURRENCY REFUSED ATOMICALLY
# A DZD receipt never credits a USD invoice, even when numeric totals match.
# ==============================================


async def test_invoice_cross_currency_refused_atomically(
    dining_engine: AsyncEngine,
) -> None:
    """A DZD receipt never credits a USD invoice, even when numeric totals match."""
    graph, _request_id, receipt_id, invoice_id = await invoicing_graph(
        engine=dining_engine, invoice_currency="USD"
    )
    with pytest.raises(DiningError, match="cross_currency"):
        async with graph.unit(actor="owner") as unit:
            await unit.finalize_invoice(invoice_id=invoice_id, expected_revision=1)
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
                text("SELECT currency FROM dining_receipts WHERE id=:id"),
                {"id": receipt_id},
            )
            == "DZD"
        )


# ==============================================
# TEST RECEIPT REPEATED AND CONCURRENT COMMITS ONCE
# Independent collection transactions with the same receipt reference deduplicate.
# ==============================================


async def test_receipt_repeated_and_concurrent_commits_once(
    dining_engine: AsyncEngine,
) -> None:
    """Independent collection transactions with the same receipt reference deduplicate."""
    graph = await configure_graph(graph=await create_graph(engine=dining_engine))
    request_id, quote_id = await create_request_quote(graph=graph)
    await accept_and_hold(graph=graph, request_id=request_id, quote_id=quote_id)

    # ==============================================
    # RECEIVE
    # Record the exact same synthetic received-fund facts in a fresh session.
    # ==============================================

    async def receive() -> int:
        """Record the exact same synthetic received-fund facts in a fresh session."""
        return await receive_advance(
            graph=graph, request_id=request_id, quote_id=quote_id
        )

    first, second = await asyncio.gather(receive(), receive())
    assert first == second
    async with dining_engine.connect() as observer:
        assert (
            await observer.scalar(
                text("SELECT count(*) FROM dining_receipts WHERE branch_id=:id"),
                {"id": graph.base + 300},
            )
            == 1
        )


# ==============================================
# TEST PLANNING DISTINGUISHES OCCUPIED AND FULLY RESERVED
# Closed hours never count as bookings; a table may be physically free but booked.
# ==============================================


async def test_planning_distinguishes_occupied_and_fully_reserved(
    dining_engine: AsyncEngine,
) -> None:
    """Closed hours never count as bookings; a table may be physically free but booked."""
    graph, _request_id, _receipt_id, _invoice_id = await invoicing_graph(
        engine=dining_engine
    )
    async with graph.unit(actor="cleaner") as unit:
        rows = await unit.planning(
            period=Period(
                start=datetime(2026, 11, 3, 20, tzinfo=timezone.utc),
                end=datetime(2026, 11, 3, 21, 30, tzinfo=timezone.utc),
            )
        )
    row = next(row for row in rows if row["id"] == graph.table_id)
    assert row["physical_state"] == "occupied" and row["fully_reserved"] is True
    assert row["occupation"] is not None
    assert "customer_name" not in str(rows) and "received_amount" not in str(rows)


# ==============================================
# TEST CONCURRENT CONFIRMATIONS SHARE ONE TICKET AND PRESERVE MONEY
# Repeated human finalization cannot assign the same booking twice.
# ==============================================


async def test_concurrent_confirmations_share_one_ticket_and_preserve_money(
    dining_engine: AsyncEngine,
) -> None:
    """Repeated human finalization cannot assign the same booking twice."""
    graph = await configure_graph(graph=await create_graph(engine=dining_engine))
    request_id, quote_id = await create_request_quote(graph=graph)
    await accept_and_hold(graph=graph, request_id=request_id, quote_id=quote_id)
    receipt_id = await receive_advance(
        graph=graph, request_id=request_id, quote_id=quote_id
    )
    await proof(graph=graph, request_id=request_id)

    # ==============================================
    # FINALIZE
    # Finalize in an independently committed transaction.
    # ==============================================

    async def finalize() -> dict[str, str | int]:
        """Finalize in an independently committed transaction."""
        async with graph.unit(actor="service") as unit:
            return await unit.finalize_human(
                request_id=request_id, quote_id=quote_id, receipt_id=receipt_id
            )

    first, second = await asyncio.gather(finalize(), finalize())
    assert first == second
    # The owner has the explicit financial read grant for this private print.
    # Service confirmation and financial-document consultation remain separate.
    async with graph.unit(actor="owner") as unit:
        document = await unit.confirmation_document(request_id=request_id)
    from app.services.business.dining.tickets import printable_confirmation

    printable = printable_confirmation(
        document=document, verification_origin="http://127.0.0.1:5473"
    )
    assert (
        "Synthetic customer" in printable
        and "<svg" in printable
        and "1500" in printable
    )
    assert "synthetic@example.invalid" not in printable
    async with dining_engine.connect() as observer:
        assert (
            await observer.scalar(
                text(
                    "SELECT count(*) FROM dining_claims WHERE request_id=:id AND active AND kind='reservation'"
                ),
                {"id": request_id},
            )
            == 1
        )
        assert (
            await observer.scalar(
                text(
                    "SELECT count(*) FROM dining_outbox WHERE request_id=:id AND payload->>'kind'='reservation.confirmed'"
                ),
                {"id": request_id},
            )
            == 1
        )


# ==============================================
# TEST MAINTENANCE INVALIDATES PRIOR PROOF WITHOUT DELETING RESERVATION
# A conflicting maintenance observation invalidates proof and preserves funds.
# ==============================================


async def test_maintenance_invalidates_prior_proof_without_deleting_reservation(
    dining_engine: AsyncEngine,
) -> None:
    """A conflicting maintenance observation invalidates proof and preserves funds."""
    graph = await configure_graph(graph=await create_graph(engine=dining_engine))
    request_id, quote_id = await create_request_quote(graph=graph)
    await accept_and_hold(graph=graph, request_id=request_id, quote_id=quote_id)
    receipt_id = await receive_advance(
        graph=graph, request_id=request_id, quote_id=quote_id
    )
    await proof(graph=graph, request_id=request_id)
    period = Period(
        start=datetime(2026, 11, 3, 20, tzinfo=timezone.utc),
        end=datetime(2026, 11, 3, 22, tzinfo=timezone.utc),
    )
    async with graph.unit() as unit:
        _identifier, conflicts = await unit.create_blackout(
            period=period,
            kind="maintenance",
            reason="Synthetic maintenance",
            table_id=graph.table_id,
            zone_id=None,
            acknowledge_conflicts=True,
        )
    assert request_id in conflicts
    with pytest.raises(DiningError):
        async with graph.unit(actor="service") as unit:
            await unit.finalize_human(
                request_id=request_id, quote_id=quote_id, receipt_id=receipt_id
            )
    async with dining_engine.connect() as observer:
        assert (
            await observer.scalar(
                text(
                    "SELECT count(*) FROM dining_claims WHERE request_id=:id AND active"
                ),
                {"id": request_id},
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


# ==============================================
# TEST EXPLICIT GROUP CAPACITY AND TARIFF
# Two tables do not automatically provide their summed capacity or summed price.
# ==============================================


async def test_explicit_group_capacity_and_tariff(dining_engine: AsyncEngine) -> None:
    """Two tables do not automatically provide their summed capacity or summed price."""
    from app.schemas.dining import (
        CombinationInput,
        RequestInput,
    )

    graph = await configure_graph(graph=await create_graph(engine=dining_engine))
    data = RequestInput(
        customer_name="Synthetic group",
        contact="group@example.invalid",
        starts_at=datetime(2026, 11, 3, 20, tzinfo=timezone.utc),
        duration_seconds=5400,
        party_size=6,
        table_ids=(graph.table_id, graph.second_table_id),
        criteria={},
        preparation=False,
        menu=(),
    )
    with pytest.raises(DiningError, match="combination"):
        async with graph.unit(actor="service") as unit:
            await unit.create_request(
                data=data, customer=graph.principal(actor="customer")
            )
    async with graph.unit() as unit:
        await unit.create_combination(
            data=CombinationInput(
                code="G12",
                table_ids=data.table_ids,
                min_capacity=2,
                max_capacity=6,
                pricing_ref="test-table",
                active=True,
            )
        )
    async with graph.unit(actor="service") as unit:
        request_id = await unit.create_request(
            data=data, customer=graph.principal(actor="customer")
        )
        quote_id = await unit.create_quote(
            request_id=request_id,
            currency="DZD",
            expires_at=graph.clock.value + timedelta(hours=1),
        )
    assert (await graph.quote(identifier=quote_id)).amount == Decimal(1500)


# ==============================================
# TEST SPECIAL MENU REQUIRES BOTH EXACT CONSENTS AND FREEZES LINES
# An accepted menu uses explicit Decimal tariffs, never legacy catalogue Float.
# ==============================================


async def test_special_menu_requires_both_exact_consents_and_freezes_lines(
    dining_engine: AsyncEngine,
) -> None:
    """An accepted menu uses explicit Decimal tariffs, never legacy catalogue Float."""
    from app.schemas.dining import (
        MenuItemInput,
        RequestInput,
        TariffInput,
    )
    from app.services.business.dining.customer import accept_customer_quote

    graph = await configure_graph(graph=await create_graph(engine=dining_engine))
    async with dining_engine.begin() as connection:
        category = await connection.scalar(
            text(
                "INSERT INTO categories(restaurant_id,name) VALUES (:restaurant,'Synthetic menu') RETURNING id"
            ),
            {"restaurant": graph.base + 200},
        )
        product = await connection.scalar(
            text(
                "INSERT INTO products(restaurant_id,category_id,name,price,is_available) VALUES (:restaurant,:category,'Synthetic special',999.99,true) RETURNING id"
            ),
            {"restaurant": graph.base + 200, "category": category},
        )
    async with graph.unit() as unit:
        await unit.create_tariff(
            data=TariffInput(
                reference=f"product:{product}",
                component="menu",
                currency="DZD",
                unit="per_item",
                unit_price=Decimal("10.005"),
                valid_from=graph.clock.value,
                valid_until=None,
            )
        )
        request_id = await unit.create_request(
            data=RequestInput(
                customer_name="Synthetic menu guest",
                contact="guest@example.invalid",
                starts_at=datetime(2026, 11, 3, 20, tzinfo=timezone.utc),
                duration_seconds=5400,
                party_size=4,
                table_ids=(graph.table_id,),
                criteria={},
                preparation=False,
                menu=(MenuItemInput(product_id=product, quantity=Decimal(2)),),
            ),
            customer=graph.principal(actor="customer"),
        )
        quote_id = await unit.create_quote(
            request_id=request_id,
            currency="DZD",
            expires_at=graph.clock.value + timedelta(hours=1),
        )
    quote = await graph.quote(identifier=quote_id)
    assert quote.amount == Decimal("1520.01")
    async with graph.factory() as session:
        await accept_customer_quote(
            session=session,
            principal=graph.principal(actor="customer"),
            restaurant_id=graph.base + 200,
            branch_id=graph.base + 300,
            quote_id=quote_id,
            expected_digest=quote.digest,
            clock=graph.clock,
        )
    with pytest.raises(DiningError, match="consents"):
        async with graph.unit(actor="service") as unit:
            await unit.hold(request_id=request_id, quote_id=quote_id)
    async with graph.unit(actor="service") as unit:
        await unit.accept_restaurant_quote(
            quote_id=quote_id, expected_digest=quote.digest
        )
        await unit.hold(request_id=request_id, quote_id=quote_id)
    async with dining_engine.begin() as connection:
        await connection.execute(
            text("UPDATE products SET name='Changed catalogue',price=1 WHERE id=:id"),
            {"id": product},
        )
    frozen = await graph.quote(identifier=quote_id)
    assert frozen.digest == quote.digest and frozen.amount == Decimal("1520.01")
    assert "Synthetic special" in str(frozen.components)


# ==============================================
# TEST LATE OCCUPATION ALERTS REPEAT WITHOUT AUTO RELEASE OR DUPLICATE SENDS
# The configured deadline scanner only queues alerts; physical departure is human.
# ==============================================


async def test_late_occupation_alerts_repeat_without_auto_release_or_duplicate_sends(
    dining_engine: AsyncEngine,
) -> None:
    """The configured deadline scanner only queues alerts; physical departure is human."""
    graph, _request_id, _receipt_id, _invoice_id = await invoicing_graph(
        engine=dining_engine
    )
    graph.clock.value = datetime(2026, 11, 3, 21, 32, tzinfo=timezone.utc)
    async with graph.unit(actor="service") as unit:
        await unit.process_deadlines()
    async with graph.unit(actor="service") as unit:
        await unit.process_deadlines()
    async with dining_engine.connect() as observer:
        assert (
            await observer.scalar(
                text("SELECT physical_state FROM dining_tables WHERE id=:id"),
                {"id": graph.table_id},
            )
            == "occupied"
        )
        count = await observer.scalar(
            text(
                "SELECT count(*) FROM dining_outbox WHERE branch_id=:id AND payload->>'kind' LIKE 'occupation.delay:%'"
            ),
            {"id": graph.base + 300},
        )
        assert count == 4


# ==============================================
# TEST ASSISTANT IDENTITY CANNOT BE AN OWNER
# Reject configuration identities carrying model capabilities by construction.
# ==============================================


async def test_assistant_identity_cannot_be_an_owner(
    dining_engine: AsyncEngine,
) -> None:
    """Reject configuration identities carrying model capabilities by construction."""
    graph = await configure_graph(graph=await create_graph(engine=dining_engine))
    with pytest.raises(TenantAccessDenied, match="assistant_owner"):
        async with graph.unit() as unit:
            await unit.grant(
                membership_id=graph.base + 30,
                capability="assistant",
                actor_kind="assistant",
                active=True,
            )


# ==============================================
# TEST OVERRUN RETAINS NEXT BOOKING AND CLEANING RESPECTS MAINTENANCE
# Actual delay is retained and alerted; cleaning never erases later constraints.
# ==============================================


async def test_overrun_retains_next_booking_and_cleaning_respects_maintenance(
    dining_engine: AsyncEngine,
) -> None:
    """Actual delay is retained and alerted; cleaning never erases later constraints."""
    from app.schemas.dining import RequestInput
    from tests.dining.support import confirm_booking

    graph = await configure_graph(graph=await create_graph(engine=dining_engine))
    request_id, quote_id = await create_request_quote(graph=graph)
    await accept_and_hold(graph=graph, request_id=request_id, quote_id=quote_id)
    receipt_id = await receive_advance(
        graph=graph, request_id=request_id, quote_id=quote_id
    )
    await confirm_booking(
        graph=graph, request_id=request_id, quote_id=quote_id, receipt_id=receipt_id
    )
    graph.clock.value = datetime(2026, 11, 3, 20, tzinfo=timezone.utc)
    async with graph.unit(actor="service") as unit:
        occupation_id = await unit.install(
            table_ids=(graph.table_id,),
            party_size=4,
            expected_end=graph.clock.value + timedelta(minutes=90),
            request_id=request_id,
        )
        next_id = await unit.create_request(
            data=RequestInput(
                customer_name="Synthetic next party",
                contact="next@example.invalid",
                starts_at=graph.clock.value + timedelta(minutes=105),
                duration_seconds=3600,
                party_size=4,
                table_ids=(graph.table_id,),
                criteria={},
                preparation=False,
                menu=(),
            ),
            customer=graph.principal(actor="customer"),
        )
        next_quote = await unit.create_quote(
            request_id=next_id,
            currency="DZD",
            expires_at=graph.clock.value + timedelta(minutes=30),
        )
    await accept_and_hold(graph=graph, request_id=next_id, quote_id=next_quote)
    next_receipt = await receive_advance(
        graph=graph,
        request_id=next_id,
        quote_id=next_quote,
        amount=Decimal(1000),
        reference="synthetic-next",
    )
    async with graph.unit(actor="service") as unit:
        await unit.confirm_availability(
            table_ids=(graph.table_id,),
            period=Period(
                start=graph.clock.value + timedelta(minutes=105),
                end=graph.clock.value + timedelta(minutes=165),
            ),
            request_id=next_id,
        )
        await unit.finalize_human(
            request_id=next_id, quote_id=next_quote, receipt_id=next_receipt
        )
        conflicts = await unit.extend_occupation(
            occupation_id=occupation_id,
            expected_end=graph.clock.value + timedelta(hours=2),
        )
    assert next_id in conflicts
    async with graph.unit() as unit:
        await unit.create_blackout(
            period=Period(
                start=graph.clock.value + timedelta(hours=2),
                end=graph.clock.value + timedelta(hours=3),
            ),
            kind="maintenance",
            reason="Synthetic maintenance",
            table_id=graph.table_id,
            zone_id=None,
            acknowledge_conflicts=True,
        )
    graph.clock.value += timedelta(hours=2, minutes=5)
    async with graph.unit(actor="cleaner") as unit:
        await unit.record_departure(occupation_id=occupation_id)
        await unit.start_cleaning(occupation_id=occupation_id)
        await unit.finish_cleaning(occupation_id=occupation_id)
    async with dining_engine.connect() as observer:
        assert (
            await observer.scalar(
                text("SELECT physical_state FROM dining_tables WHERE id=:id"),
                {"id": graph.table_id},
            )
            == "maintenance"
        )
        assert (
            await observer.scalar(
                text("SELECT status FROM dining_requests WHERE id=:id"), {"id": next_id}
            )
            == "confirmed"
        )
        assert (
            await observer.scalar(
                text(
                    "SELECT count(*) FROM dining_claims WHERE request_id=:id AND active"
                ),
                {"id": next_id},
            )
            == 1
        )


# ==============================================
# TEST PAID ASSIGNMENT CANNOT BE MOVED BY DIRECT SQL
# Received funds freeze the table assignment independently of API validation.
# ==============================================


async def test_paid_assignment_cannot_be_moved_by_direct_sql(
    dining_engine: AsyncEngine,
) -> None:
    """Received funds freeze the table assignment independently of API validation."""
    graph = await configure_graph(graph=await create_graph(engine=dining_engine))
    request_id, quote_id = await create_request_quote(graph=graph)
    await accept_and_hold(graph=graph, request_id=request_id, quote_id=quote_id)
    receipt_id = await receive_advance(
        graph=graph, request_id=request_id, quote_id=quote_id
    )
    with pytest.raises(IntegrityError):
        async with dining_engine.begin() as connection:
            await connection.execute(
                text(
                    "UPDATE dining_request_tables SET table_id=:table WHERE request_id=:id"
                ),
                {"table": graph.second_table_id, "id": request_id},
            )
    async with dining_engine.connect() as observer:
        assert (
            await observer.scalar(
                text("SELECT table_id FROM dining_request_tables WHERE request_id=:id"),
                {"id": request_id},
            )
            == graph.table_id
        )
        assert (
            await observer.scalar(
                text("SELECT count(*) FROM dining_receipts WHERE id=:id"),
                {"id": receipt_id},
            )
            == 1
        )


# ==============================================
# TEST DATABASE REJECTS NAN FINANCIAL INPUT
# PostgreSQL Numeric NaN must not bypass nonnegative financial constraints.
# ==============================================


async def test_database_rejects_nan_financial_input(dining_engine: AsyncEngine) -> None:
    """PostgreSQL Numeric NaN must not bypass nonnegative financial constraints."""
    graph = await configure_graph(graph=await create_graph(engine=dining_engine))
    with pytest.raises(IntegrityError) as refusal:
        async with dining_engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO dining_tariffs(restaurant_id,branch_id,reference,component,currency,unit,unit_price,valid_from) VALUES (:restaurant,:branch,'synthetic-nan','table','DZD','per_hour','NaN'::numeric,:start)"
                ),
                {
                    "restaurant": graph.base + 200,
                    "branch": graph.base + 300,
                    "start": graph.clock.value,
                },
            )
    assert refusal.value.orig.sqlstate == "23514"


# ==============================================
# TEST FAILED PRECOMMIT REQUEST SENDS NOTHING
# An outbox job inside an uncommitted transaction is invisible to dispatch.
# ==============================================


async def test_failed_precommit_request_sends_nothing(
    dining_engine: AsyncEngine,
) -> None:
    """An outbox job inside an uncommitted transaction is invisible to dispatch."""
    from app.schemas.dining import RequestInput

    graph = await configure_graph(graph=await create_graph(engine=dining_engine))
    transport = SimulatedTransport(graph=graph)
    with pytest.raises(RuntimeError, match="synthetic-after-enqueue"):
        async with graph.unit(actor="service") as unit:
            await unit.create_request(
                data=RequestInput(
                    customer_name="Synthetic rollback",
                    contact="rollback@example.invalid",
                    starts_at=datetime(2026, 11, 3, 20, tzinfo=timezone.utc),
                    duration_seconds=3600,
                    party_size=4,
                    table_ids=(graph.table_id,),
                    criteria={},
                    preparation=False,
                    menu=(),
                ),
                customer=graph.principal(actor="customer"),
            )
            assert await dispatch(graph=graph, transport=transport) == {
                "delivered": 0,
                "failed": 0,
                "uncertain": 0,
            }
            raise RuntimeError("synthetic-after-enqueue")
    assert transport.keys == []
    async with dining_engine.connect() as observer:
        assert (
            await observer.scalar(
                text("SELECT count(*) FROM dining_requests WHERE branch_id=:id"),
                {"id": graph.base + 300},
            )
            == 0
        )
        assert (
            await observer.scalar(
                text("SELECT count(*) FROM dining_outbox WHERE branch_id=:id"),
                {"id": graph.base + 300},
            )
            == 0
        )


# ==============================================
# REAL ELAPSED REQUEST TIME ACROSS DST
# Observe persisted UTC boundaries and the actual proportional quote after both changes.
# ==============================================


@pytest.mark.parametrize("month,day", [(3, 28), (10, 31)])
async def test_request_duration_is_elapsed_time_across_dst(
    dining_engine: AsyncEngine, month: int, day: int
) -> None:
    """A ninety-minute request stays ninety minutes during spring and autumn changes."""
    from zoneinfo import ZoneInfo

    from app.schemas.dining import RequestInput

    graph = await configure_graph(graph=await create_graph(engine=dining_engine))
    starts = datetime(2027, month, day, 1, 30, tzinfo=ZoneInfo("Europe/Paris"))
    async with graph.unit(actor="service") as unit:
        request_id = await unit.create_request(
            data=RequestInput(
                customer_name="Synthetic elapsed time",
                contact="clock@example.invalid",
                starts_at=starts,
                duration_seconds=5400,
                party_size=4,
                table_ids=(graph.table_id,),
                criteria={},
                preparation=False,
                menu=(),
            ),
            customer=graph.principal(actor="customer"),
        )
        quote_id = await unit.create_quote(
            request_id=request_id,
            currency="DZD",
            expires_at=graph.clock.value + timedelta(minutes=30),
        )
    async with dining_engine.connect() as observer:
        duration = await observer.scalar(
            text(
                "SELECT EXTRACT(EPOCH FROM ends_at-starts_at) FROM dining_requests WHERE id=:id"
            ),
            {"id": request_id},
        )
        assert duration == Decimal(5400)
    assert (await graph.quote(identifier=quote_id)).amount == Decimal(1500)
