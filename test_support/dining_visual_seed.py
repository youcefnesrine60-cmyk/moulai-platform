# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# OPTIONAL PERSISTED VISUAL FIXTURE
# Add unmistakably fictional state snapshots only after attesting the owned local database.
# ==============================================

"""Display fixtures are initial observations, not evidence of a completed booking workflow."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND CLOSED FIXTURE TARGET
# Reuse exact scoped records without any financial entry or notification transport.
# ==============================================

from datetime import timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.models.dining import (
    DiningBlackout,
    DiningClaim,
    DiningOccupation,
    DiningOccupationTable,
    DiningRequest,
    DiningRequestTable,
    DiningTable,
)
from app.schemas.dining import TableInput
from test_support.local_postgres import (
    LocalPostgresSettings,
    read_local_test_identity,
)
from tests.dining.support import DiningGraph

# ==============================================
# PREPARE VISUAL STATES
# Require the attested local profile and retain the two nominal-workflow tables unchanged.
# ==============================================


async def prepare_visual_states(
    *, graph: DiningGraph, engine: AsyncEngine, configuration: LocalPostgresSettings
) -> None:
    """Persist six labeled observation fixtures; never collect or allocate funds.

    Only the owned disposable profile is accepted. Dates derive from its initial
    branch day, and every display reservation is explicitly labeled a fixture.
    These snapshots do not claim a successful financial confirmation workflow.
    """
    if (
        configuration.PROFILE != "dining"
        or engine.url.render_as_string(hide_password=False)
        != configuration.URL.get_secret_value()
    ):
        raise RuntimeError("visual_fixture_target_not_attested")
    async with engine.connect() as connection:
        await connection.run_sync(
            lambda sync: read_local_test_identity(sync, configuration=configuration)
        )
    if graph.references is None:
        raise RuntimeError("visual_fixture_references_required")
    now = graph.clock.value
    ids: list[int] = []
    async with graph.unit() as unit:
        for index, state in enumerate(
            (
                "available",
                "occupied",
                "dirty",
                "maintenance",
                "out_of_service",
                "available",
            ),
            start=1,
        ):
            ids.append(
                await unit.create_table(
                    data=TableInput(
                        code=f"V{index:02d}",
                        name="VISUAL FIXTURE — fictive",
                        min_capacity=1,
                        max_capacity=4,
                        shape_id=graph.references["shape"],
                        category_id=graph.references["category"],
                        zone_id=graph.references["zone"],
                        location_id=graph.references["location"],
                        description="Local observation fixture, not a real customer booking",
                        photos=(),
                        pricing_ref="test-table",
                        in_service=state != "out_of_service",
                        trait_ids=(),
                    ),
                    initial_state="available",
                )
            )
    scope = {"restaurant_id": graph.base + 200, "branch_id": graph.base + 300}
    midnight = now.astimezone(ZoneInfo("Africa/Algiers")).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    async with graph.factory() as session, session.begin():
        # ==============================================
        # VISIBLE CONTEXT LABELS
        # Names are fictional and scoped; no commercial identity is overwritten.
        # ==============================================

        await session.execute(
            text("UPDATE restaurants SET name=:name WHERE id=:id"),
            {"name": "Bistro MoulAI — Démonstration", "id": scope["restaurant_id"]},
        )
        await session.execute(
            text(
                "UPDATE branches SET name=:name WHERE id=:id AND restaurant_id=:restaurant"
            ),
            {
                "name": "Centre-ville — Démonstration",
                "id": scope["branch_id"],
                "restaurant": scope["restaurant_id"],
            },
        )
        for index, state in enumerate(
            (
                "available",
                "occupied",
                "dirty",
                "maintenance",
                "out_of_service",
                "available",
            )
        ):
            table = await session.get(DiningTable, ids[index])
            if table is None:
                raise RuntimeError("visual_fixture_table_missing")
            table.physical_state = state
        for index, status in ((1, "occupied"), (2, "cleaning")):
            occupation = DiningOccupation(
                **scope,
                request_id=None,
                party_size=2,
                arrived_at=now - timedelta(hours=2),
                expected_end=now - timedelta(minutes=30),
                cleaning_expected_start=now - timedelta(minutes=30),
                cleaning_expected_end=now - timedelta(minutes=15),
                departed_at=(
                    now - timedelta(minutes=25) if status == "cleaning" else None
                ),
                cleaning_actual_start=(
                    now - timedelta(minutes=20) if status == "cleaning" else None
                ),
                status=status,
                installed_by=graph.base + 30,
                departure_by=graph.base + 30 if status == "cleaning" else None,
            )
            session.add(occupation)
            await session.flush()
            session.add(
                DiningOccupationTable(
                    **scope,
                    occupation_id=occupation.id,
                    table_id=ids[index],
                    active=True,
                )
            )
        for index, kind in ((3, "maintenance"), (4, "closure")):
            session.add(
                DiningBlackout(
                    **scope,
                    table_id=ids[index],
                    zone_id=None,
                    starts_at=now - timedelta(hours=1),
                    ends_at=now + timedelta(hours=4),
                    kind=kind,
                    reason="VISUAL FIXTURE — contrôle et réparation / inspection / صيانة",
                    active=True,
                )
            )
        for index, kind in ((0, "reservation"), (1, "reservation"), (5, "hold")):
            start = midnight if index == 0 else now + timedelta(hours=2)
            end = (
                midnight + timedelta(days=1)
                if index == 0
                else start + timedelta(hours=2)
            )
            request = DiningRequest(
                **scope,
                reference=f"VISUAL-FIXTURE-{index}",
                customer_issuer="https://fixture.example.invalid",
                customer_subject=f"visual-{index}",
                customer_name="Fictional observation fixture",
                contact="fixture@example.invalid",
                starts_at=start,
                ends_at=end,
                party_size=2,
                preparation=False,
                criteria={},
                menu=[],
                status="confirmed" if kind == "reservation" else "held",
            )
            session.add(request)
            await session.flush()
            session.add(
                DiningRequestTable(**scope, request_id=request.id, table_id=ids[index])
            )
            session.add(
                DiningClaim(
                    **scope,
                    request_id=request.id,
                    table_id=ids[index],
                    starts_at=start,
                    ends_at=end,
                    kind=kind,
                    active=True,
                    expires_at=now + timedelta(minutes=20) if kind == "hold" else None,
                )
            )
