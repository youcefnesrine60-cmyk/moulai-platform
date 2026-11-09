# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# REAL DINING WORKFLOW SMOKE PROOFS
# Observe committed exact pricing, independent receipts and physical transitions.
# ==============================================

"""These tests use the real migrated local schema and independent observer sessions."""

# isort: split
# ==============================================
# IMPORTS AND EXPLICIT DINING PROFILE MARKER
# Test-only identities and prices never leave the owned disposable server.
# ==============================================

from datetime import (
    datetime,
    timedelta,
    timezone,
)
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from tests.dining.support import (
    accept_and_hold,
    configure_graph,
    confirm_booking,
    create_graph,
    create_request_quote,
    receive_advance,
)

pytestmark = pytest.mark.dining_postgres


# ==============================================
# EXACT PROPORTIONAL QUOTE AND ATOMIC CONFIRMATION
# A ninety-minute rate is not rounded to two hours; receipt persists separately.
# ==============================================


async def test_real_quote_receipt_confirmation_and_cleaning(
    dining_engine: AsyncEngine,
) -> None:
    """Complete the real service path, with no outer transaction masking commits."""
    graph = await configure_graph(graph=await create_graph(engine=dining_engine))
    request_id, quote_id = await create_request_quote(graph=graph)
    quote = await graph.quote(identifier=quote_id)
    assert quote.amount == Decimal(1500)
    assert quote.components[0]["quantity"] == "1.5"
    await accept_and_hold(graph=graph, request_id=request_id, quote_id=quote_id)
    receipt_id = await receive_advance(
        graph=graph, request_id=request_id, quote_id=quote_id
    )
    ticket = await confirm_booking(
        graph=graph, request_id=request_id, quote_id=quote_id, receipt_id=receipt_id
    )
    assert ticket["status"] == "confirmed"
    async with dining_engine.connect() as observer:
        assert (
            await observer.scalar(
                text("SELECT status FROM dining_receipts WHERE id=:id"),
                {"id": receipt_id},
            )
            == "verified"
        )
        assert (
            await observer.scalar(
                text(
                    "SELECT count(*) FROM dining_claims WHERE request_id=:id AND kind='reservation' AND active"
                ),
                {"id": request_id},
            )
            == 1
        )
    graph.clock.value = datetime(2026, 11, 3, 20, tzinfo=timezone.utc)
    async with graph.unit(actor="service") as unit:
        occupation_id = await unit.install(
            table_ids=(graph.table_id,),
            party_size=3,
            expected_end=graph.clock.value + timedelta(minutes=90),
            request_id=request_id,
        )
    graph.clock.value += timedelta(hours=2)
    async with dining_engine.connect() as observer:
        assert (
            await observer.scalar(
                text("SELECT physical_state FROM dining_tables WHERE id=:id"),
                {"id": graph.table_id},
            )
            == "occupied"
        )
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
            == "available"
        )
        assert (
            await observer.scalar(
                text("SELECT status FROM dining_requests WHERE id=:id"),
                {"id": request_id},
            )
            == "served"
        )
