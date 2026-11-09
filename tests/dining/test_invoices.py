# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# FOOD INVOICE AND ADVANCE INTEGRITY PROOFS
# Observe Decimal totals, unique credit and real rollback from separate sessions.
# ==============================================

"""Only real disposable PostgreSQL rows; no outer rollback fixture masks results."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND EXPLICIT LOCAL PROFILE
# Historical Float values are test fixtures with separately identified exact sources.
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
from sqlalchemy.ext.asyncio import AsyncEngine

from app.models.dining import DiningBase
from app.repositories.dining_repo import DiningRepository
from app.schemas.dining import (
    InvoiceInput,
    InvoiceLineInput,
)
from tests.dining.support import (
    DiningGraph,
    accept_and_hold,
    configure_graph,
    confirm_booking,
    create_graph,
    create_request_quote,
    receive_advance,
)

pytestmark = pytest.mark.dining_postgres


# ==============================================
# COMMITTED ARRIVAL AND FOOD SOURCE ROWS
# Real legacy orders remain unchanged while the new invoice stores exact evidence.
# ==============================================


async def invoicing_graph(
    *, engine: AsyncEngine, food_total: int = 6000, invoice_currency: str = "DZD"
) -> tuple[DiningGraph, int, int, int]:
    """Create a booked/arrived party, verified advance and explicitly reconciled food."""
    graph = await configure_graph(graph=await create_graph(engine=engine))
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
        await unit.install(
            table_ids=(graph.table_id,),
            party_size=4,
            expected_end=graph.clock.value + timedelta(minutes=90),
            request_id=request_id,
        )
    async with engine.begin() as connection:
        category_id = await connection.scalar(
            text(
                "INSERT INTO categories(restaurant_id,name) VALUES (:restaurant,'Synthetic food') RETURNING id"
            ),
            {"restaurant": graph.base + 200},
        )
        product_id = await connection.scalar(
            text(
                "INSERT INTO products(restaurant_id,category_id,name,price,is_available) VALUES (:restaurant,:category,'Synthetic food',:amount,true) RETURNING id"
            ),
            {
                "restaurant": graph.base + 200,
                "category": category_id,
                "amount": food_total,
            },
        )
        order_id = await connection.scalar(
            text(
                "INSERT INTO orders(restaurant_id,branch_id,table_id,order_number,order_type,status,subtotal_amount,discount_amount,tax_amount,delivery_amount,total_amount) VALUES (:restaurant,:branch,:table,:number,'dine_in','completed',:amount,0,0,0,:amount) RETURNING id"
            ),
            {
                "restaurant": graph.base + 200,
                "branch": graph.base + 300,
                "table": graph.table_id,
                "number": f"SYNTHETIC-DINING-{graph.base}",
                "amount": food_total,
            },
        )
        item_id = await connection.scalar(
            text(
                "INSERT INTO order_items(order_id,product_id,product_name,unit_price,quantity,total_price) VALUES (:order,:product,'Synthetic food',:amount,1,:amount) RETURNING id"
            ),
            {"order": order_id, "product": product_id, "amount": food_total},
        )
    assert isinstance(order_id, int) and isinstance(item_id, int)
    data = InvoiceInput(
        request_id=request_id,
        currency=invoice_currency,
        lines=(
            InvoiceLineInput(
                order_id=order_id,
                order_item_id=item_id,
                description="Synthetic food",
                quantity=Decimal(1),
                unit_price=Decimal(food_total),
                source_reference="synthetic-approved-decimal-food-record",
            ),
        ),
        currency_source="synthetic restaurant DZD record",
        rounding_source="owner-approved final ROUND_HALF_UP",
        reconciliation_reference="synthetic-human-reviewed-order-link",
        legacy_discrepancies_acknowledged=False,
    )
    async with graph.unit(actor="owner") as unit:
        invoice_id = await unit.prepare_invoice(data=data)
    return graph, request_id, receipt_id, invoice_id


# ==============================================
# AUTOMATIC ONE-TIME ADVANCE APPLICATION
# The food sales total stays 6000 while the already-received 1500 reduces the balance.
# ==============================================


async def test_invoice_6000_advance_1500_balance_4500_and_concurrent_retry(
    dining_engine: AsyncEngine,
) -> None:
    """Finalize and apply once; repeated/concurrent requests cannot duplicate credit."""
    graph, _request_id, receipt_id, invoice_id = await invoicing_graph(
        engine=dining_engine
    )
    async with graph.unit(actor="owner") as unit:
        assert await unit.finalize_invoice(
            invoice_id=invoice_id, expected_revision=1
        ) == Decimal(6000)

    # ==============================================
    # REPEAT
    # Use a separate real transaction for each concurrent credit request.
    # ==============================================

    async def repeat() -> dict[str, str | int]:
        """Use a separate real transaction for each concurrent credit request."""
        async with graph.unit(actor="collector") as unit:
            return await unit.allocate_advance(
                invoice_id=invoice_id, receipt_id=receipt_id
            )

    a, b = await asyncio.gather(repeat(), repeat())
    assert a == b
    assert Decimal(str(a["invoice_total"])) == Decimal(6000)
    assert Decimal(str(a["advance"])) == Decimal(1500)
    assert Decimal(str(a["balance"])) == Decimal(4500)
    async with dining_engine.connect() as observer:
        assert (
            await observer.scalar(
                text("SELECT count(*) FROM dining_allocations WHERE receipt_id=:id"),
                {"id": receipt_id},
            )
            == 1
        )
        assert await observer.scalar(
            text("SELECT total FROM dining_invoices WHERE id=:id"), {"id": invoice_id}
        ) == Decimal(6000)
        assert await observer.scalar(
            text("SELECT received_amount FROM dining_receipts WHERE id=:id"),
            {"id": receipt_id},
        ) == Decimal(1500)


# ==============================================
# REAL INVOICE TRANSACTION ROLLBACK
# A failed allocation must preserve the earlier committed receipt and draft invoice.
# ==============================================


async def test_allocation_failure_rolls_back_invoice_not_received_funds(
    dining_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Inject a late write error and inspect actual persistence independently."""
    graph, _request_id, receipt_id, invoice_id = await invoicing_graph(
        engine=dining_engine
    )
    original = DiningRepository.persist

    # ==============================================
    # FAIL ALLOCATION
    # Fail only the allocation write after invoice finalization was staged.
    # ==============================================

    async def fail_allocation(
        self: DiningRepository, *, record: DiningBase
    ) -> DiningBase:
        """Fail only the allocation write after invoice finalization was staged."""
        if record.__table__.name == "dining_allocations":
            raise RuntimeError("synthetic-allocation-write-failure")
        return await original(self, record=record)

    with monkeypatch.context() as patcher:
        patcher.setattr(DiningRepository, "persist", fail_allocation)
        with pytest.raises(RuntimeError, match="synthetic-allocation"):
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
    async with graph.unit(actor="owner") as unit:
        await unit.finalize_invoice(invoice_id=invoice_id, expected_revision=1)


# ==============================================
# EXCESS ADVANCE HUMAN REVIEW
# Keep sales and receipt facts intact; do not create negative balance or refund.
# ==============================================


async def test_excess_advance_is_retained_without_automatic_credit_or_refund(
    dining_engine: AsyncEngine,
) -> None:
    """A 1500 advance against 1000 food leaves a visible unallocated excess of 500."""
    graph, _request_id, receipt_id, invoice_id = await invoicing_graph(
        engine=dining_engine, food_total=1000
    )
    async with graph.unit(actor="owner") as unit:
        await unit.finalize_invoice(invoice_id=invoice_id, expected_revision=1)
    async with graph.unit(actor="collector") as unit:
        result = await unit.allocate_advance(
            invoice_id=invoice_id, receipt_id=receipt_id
        )
    assert result["status"] == "manual_review"
    assert Decimal(str(result["unallocated_excess"])) == Decimal(500)
    async with dining_engine.connect() as observer:
        assert (
            await observer.scalar(
                text("SELECT count(*) FROM dining_allocations WHERE receipt_id=:id"),
                {"id": receipt_id},
            )
            == 0
        )
        assert await observer.scalar(
            text("SELECT total FROM dining_invoices WHERE id=:id"), {"id": invoice_id}
        ) == Decimal(1000)
