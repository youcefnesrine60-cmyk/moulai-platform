# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# READ-ONLY HISTORY HTTP PROOFS
# Exercise real signed authority and committed append-only events on disposable D1d.
# ==============================================

"""Independent observers prove reads preserve history and do not widen tenant access."""

from __future__ import annotations

# isort: split
# ==============================================
# REAL ROUTES AND INDEPENDENT OBSERVERS
# Reuse the established isolated fixture without dependency principal overrides.
# ==============================================

import hashlib

import pytest
from sqlalchemy import text

from tests.dining.test_signed_http import SignedFlow
from tests.dining.test_signed_http import flow as flow  # noqa: PLC0414

pytestmark = pytest.mark.dining_postgres

# ==============================================
# SNAPSHOT OBSERVER
# Hash the committed journal from a separate session, including unprojected source details.
# ==============================================


async def digest(*, flow: SignedFlow) -> str:
    """Read committed audit content independently; never roll back service writes externally."""
    async with flow.graph.factory() as session:
        rows = (
            await session.execute(
                text(
                    "SELECT id, kind, author::text, details::text, occurred_at FROM dining_events WHERE restaurant_id=:restaurant ORDER BY id"
                ),
                {"restaurant": flow.graph.base + 200},
            )
        ).all()
    return hashlib.sha256(repr(rows).encode()).hexdigest()


# ==============================================
# PINNED FILTERED PAGES
# New events cannot shift prior pages, and all recorded rows remain persisted unchanged.
# ==============================================


async def test_history_pages_filters_and_preservation(*, flow: SignedFlow) -> None:
    """Filter real data by kind, author and local day; preserve raw unknown events."""
    await flow.login(actor="owner")
    async with flow.graph.unit() as unit:
        for number in range(105):
            await unit.event(
                kind="reference.created",
                details={
                    "kind": "zone",
                    "reference_id": number + 1,
                    "reason": "Synthetic history pagination",
                },
            )
        await unit.event(
            kind="future.event",
            details={
                "active": False,
                "password": "NEVER_PROJECT",
                "amount": "123.00",
                "before": {"state": "dirty", "token": "NEVER_PROJECT"},
                "after": {"state": "available"},
            },
        )
    before = await digest(flow=flow)
    response = await flow.client.get(flow.root + "/events")
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    first = response.json()
    assert len(first["items"]) == 20 and first["total"] > 100
    unknown = first["items"][0]
    assert unknown["kind"] == "future.event" and unknown["details"]["active"] is False
    assert unknown["details"]["amount"] == "123.00"
    await flow.login(actor="assistant")
    limited = await flow.client.get(flow.root + "/events")
    assert "amount" not in limited.json()["items"][0]["details"]
    await flow.login(actor="owner")
    assert "NEVER_PROJECT" not in response.text
    params = {"snapshot_id": first["snapshot_id"], "page": 2}
    second = (await flow.client.get(flow.root + "/events", params=params)).json()
    assert not {row["id"] for row in first["items"]} & {
        row["id"] for row in second["items"]
    }
    filtered = (
        await flow.client.get(
            flow.root + "/events",
            params={
                "kind": "reference.created",
                "author": unknown["author_key"],
                "from_day": "2026-11-03",
                "until_day": "2026-11-03",
            },
        )
    ).json()
    assert filtered["total"] >= 105
    assert all(row["kind"] == "reference.created" for row in filtered["items"])
    empty = await flow.client.get(
        flow.root + "/events", params={"from_day": "2026-11-04"}
    )
    assert empty.json()["total"] == 0
    assert before == await digest(flow=flow)
    async with flow.graph.unit() as unit:
        await unit.event(
            kind="future.event", details={"reason": "new after pinned page"}
        )
    pinned = (await flow.client.get(flow.root + "/events", params=params)).json()
    assert pinned == second
    assert (await flow.client.get(flow.root + "/events")).json()["total"] == first[
        "total"
    ] + 1


# ==============================================
# AUTHORITY AND VISIBILITY BOUNDARIES
# A role label cannot grant journal or financial access; branch scope remains mandatory.
# ==============================================


@pytest.mark.parametrize("actor", ["cleaner", "kitchen", "customer", "outsider"])
async def test_history_refuses_other_roles(*, flow: SignedFlow, actor: str) -> None:
    """Enforce current signed server authority on every page request."""
    await flow.login(actor=actor)
    before = await digest(flow=flow)
    response = await flow.client.get(flow.root + "/events")
    assert response.status_code in {403, 404}, response.text
    assert before == await digest(flow=flow)


async def test_history_rechecks_revocation_and_branch(*, flow: SignedFlow) -> None:
    """The same signed cookie cannot retain revoked journal eligibility or read another branch."""
    await flow.login(actor="assistant")
    assert (await flow.client.get(flow.root + "/events")).status_code == 200
    async with flow.graph.unit() as unit:
        await unit.grant(
            membership_id=flow.graph.base + 34,
            capability="assistant",
            actor_kind="assistant",
            active=False,
        )
    assert (await flow.client.get(flow.root + "/events")).status_code == 403
    await flow.login(actor="owner")
    other = flow.root.replace(str(flow.graph.base + 300), str(flow.graph.base + 301))
    # Company-wide owner may read this branch, but never its neighbour's events.
    permitted = await flow.client.get(other + "/events")
    assert permitted.status_code == 200 and permitted.json()["total"] == 0
    foreign = flow.root.replace(str(flow.graph.base + 200), str(flow.graph.base + 201))
    assert (await flow.client.get(foreign + "/events")).status_code in {403, 404}


# ==============================================
# EXACT FILTER REFUSALS
# Invalid pagination and date ranges fail closed without changing the journal.
# ==============================================


@pytest.mark.parametrize(
    "params",
    [
        {"page": 0},
        {"page_size": 51},
        {"snapshot_id": -1},
        {"kind": "x' OR true"},
        {"author": "member:0"},
        {"from_day": "2026-11-04", "until_day": "2026-11-03"},
    ],
)
async def test_history_invalid_filters(
    *, flow: SignedFlow, params: dict[str, str | int]
) -> None:
    """Malformed filters do not bypass permissions or mutate source records."""
    await flow.login(actor="owner")
    before = await digest(flow=flow)
    response = await flow.client.get(flow.root + "/events", params=params)
    assert response.status_code in {409, 422}, response.text
    assert before == await digest(flow=flow)


# ==============================================
# CURRENT AUTHORIZED PROFESSIONAL LABELS
# Names do not become historical assertions or leak to a journal-only reader.
# ==============================================


async def test_history_names_follow_profile_permission(*, flow: SignedFlow) -> None:
    """Only configure readers receive the current scoped professional display name."""
    async with flow.graph.factory() as session, session.begin():
        await session.execute(
            text(
                "INSERT INTO dining_staff_profiles(restaurant_id,branch_id,membership_id,employee_code,display_name,enrollment_generation) VALUES (:restaurant,:branch,:member,'history-reader','Synthetic professional name',1)"
            ),
            {
                "restaurant": flow.graph.base + 200,
                "branch": flow.graph.base + 300,
                "member": flow.graph.base + 31,
            },
        )
    async with flow.graph.unit(actor="service") as unit:
        await unit.event(
            kind="occupation.extended",
            details={
                "previous_expected_end": "2026-11-03T20:00:00Z",
                "expected_end": "2026-11-03T21:00:00Z",
            },
        )
    before = await digest(flow=flow)
    await flow.login(actor="owner")
    owner = (await flow.client.get(flow.root + "/events")).json()["items"][0]
    assert owner["author_name"] == "Synthetic professional name"
    assert owner["author_name_source"] == "current_profile"
    await flow.login(actor="service")
    service = await flow.client.get(flow.root + "/events")
    assert service.json()["items"][0]["author_name"] is None
    assert "Synthetic professional name" not in service.text
    assert before == await digest(flow=flow)
