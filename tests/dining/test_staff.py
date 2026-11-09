# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# SIGNED PROFESSIONAL LIFECYCLE REGRESSIONS
# Drive real owner and personal routes, then inspect independent committed sessions.
# ==============================================

"""Disposable D1d only; local issuer identities are fixtures, not Keycloak accounts."""

from __future__ import annotations

# isort: split
# ==============================================
# EXISTING SIGNED HTTP FIXTURE
# Keep application authorization, actual SQL commits and rollback boundaries enabled.
# ==============================================

import asyncio
from copy import copy

import pytest
from httpx import Response
from sqlalchemy import text

from tests.dining.test_signed_http import SignedFlow
from tests.dining.test_signed_http import flow as flow  # noqa: PLC0414

pytestmark = pytest.mark.dining_postgres


# ==============================================
# FIXTURE ACCOUNT REGISTRATION
# Prepare only the local issuer identity; all employment mutations use real routes.
# ==============================================


async def account(
    *, flow: SignedFlow, actor: str = "new_employee", offset: int = 80
) -> None:
    """An identity exists before invitation, with no membership or restaurant authority."""
    principal = flow.graph.principal(actor=actor)
    flow.issuer.principals[actor] = principal
    async with flow.graph.factory() as session, session.begin():
        if (
            await session.scalar(
                text(
                    "SELECT id FROM identities WHERE issuer=:issuer AND subject=:subject"
                ),
                {"issuer": principal.issuer, "subject": principal.subject},
            )
            is not None
        ):
            return
        await session.execute(
            text(
                "INSERT INTO identities(id,issuer,subject,status) VALUES (:id,:issuer,:subject,'active')"
            ),
            {
                "id": flow.graph.base + offset,
                "issuer": principal.issuer,
                "subject": principal.subject,
            },
        )


# ==============================================
# TYPED INVITATION THROUGH OWNER HTTP
# Knowing a subject never activates the account or grants a service capability.
# ==============================================


async def invite(
    *, flow: SignedFlow, actor: str = "new_employee", code: str = "EMP-LOCAL"
) -> Response:
    """Submit one pending relationship for an already registered fixture identity."""
    principal = flow.graph.principal(actor=actor)
    return await flow.client.post(
        flow.root + "/staff",
        json={
            "operation": "invite",
            "issuer": principal.issuer,
            "subject": principal.subject,
            "employee_code": code,
            "display_name": "Employé fictif",
        },
    )


# ==============================================
# INDEPENDENT COMMITTED MEMBERSHIP READER
# No outer rollback fixture can conceal partial service writes from these assertions.
# ==============================================


async def member(*, flow: SignedFlow, identifier: int) -> dict[str, object]:
    """Read the actual persisted relationship from a separate connection/session."""
    async with flow.graph.factory() as session:
        row = (
            (
                await session.execute(
                    text(
                        "SELECT id,status,revision,accepted_at,activated_at,enrollment_generation FROM organization_memberships WHERE id=:id"
                    ),
                    {"id": identifier},
                )
            )
            .mappings()
            .one()
        )
        return dict(row)


# ==============================================
# OWNER ACTIVATION REQUEST
# The current persisted revision is a prerequisite, not a bypass of personal consent.
# ==============================================


async def change_status(*, flow: SignedFlow, identifier: int, status: str) -> Response:
    """Drive activation/suspension/revocation with the genuinely observed revision."""
    current = await member(flow=flow, identifier=identifier)
    return await flow.client.post(
        flow.root + "/staff",
        json={
            "operation": "status",
            "membership_id": identifier,
            "expected_revision": current["revision"],
            "status": status,
            "reason": "Décision fictive de recette",
        },
    )


# ==============================================
# COMPLETE PERSONAL CONSENT AND OWNER ACTIVATION
# Keep the account switch genuine; neither caller can impersonate the other.
# ==============================================


async def activated(*, flow: SignedFlow) -> int:
    """Create one accepted employee without assigning any implicit operational grant."""
    await account(flow=flow)
    await flow.login(actor="owner")
    response = await invite(flow=flow)
    assert response.status_code == 200, response.text
    identifier = response.json()["identifier"]
    await flow.login(actor="new_employee")
    url = f"/local-d1/dining/employment/{flow.graph.base+10}/{identifier}/accept"
    response = await flow.client.post(url)
    assert response.status_code == 200, response.text
    await flow.login(actor="owner")
    response = await change_status(flow=flow, identifier=identifier, status="active")
    assert response.status_code == 200, response.text
    return identifier


# ==============================================
# NO IMPLICIT ACTIVATION OR AUTHORITY
# Acceptance, activation and actual permission assignment are three separate actions.
# ==============================================


async def test_invitation_requires_personal_consent_and_owner_activation(
    flow: SignedFlow,
) -> None:
    """Only the signed target may accept; even an active employee needs explicit D1 rights."""
    await account(flow=flow)
    await flow.login(actor="owner")
    response = await invite(flow=flow)
    assert response.status_code == 200, response.text
    identifier = response.json()["identifier"]
    assert (await member(flow=flow, identifier=identifier))["status"] == "pending"
    assert (
        await change_status(flow=flow, identifier=identifier, status="active")
    ).status_code == 409
    url = f"/local-d1/dining/employment/{flow.graph.base+10}/{identifier}/accept"
    assert (await flow.client.post(url)).status_code == 403
    await flow.login(actor="new_employee")
    discovery = await flow.client.get("/local-d1/dining/employment/invitations")
    assert (
        discovery.status_code == 200
        and discovery.json()[0]["membership_id"] == identifier
    )
    assert (await flow.client.get(flow.root + "/workspace")).status_code == 403
    assert (await flow.client.post(url)).status_code == 200
    assert (await flow.client.post(url)).status_code == 200
    current = await member(flow=flow, identifier=identifier)
    assert current["status"] == "pending" and current["activated_at"] is None
    await flow.login(actor="owner")
    assert (
        await change_status(flow=flow, identifier=identifier, status="active")
    ).status_code == 200
    await flow.login(actor="new_employee")
    assert (await flow.client.get(flow.root + "/workspace")).status_code == 403


# ==============================================
# FUNCTION CUMULATION REMAINS DESCRIPTIVE
# Assigning service and cleaning responsibilities cannot create those permissions.
# ==============================================


async def test_functions_and_assignments_do_not_grant_permissions(
    flow: SignedFlow,
) -> None:
    """Two named functions coexist while the employee's authority remains unchanged."""
    identifier = await activated(flow=flow)
    for code in ("service", "cleaning"):
        response = await flow.client.post(
            flow.root + "/staff",
            json={
                "operation": "function",
                "code": code,
                "labels": {"fr": code, "en": code, "ar": "وظيفة"},
                "tasks": ["Description seulement"],
                "active": True,
            },
        )
        assert response.status_code == 200, response.text
        assigned = await flow.client.post(
            flow.root + "/staff",
            json={
                "operation": "assignment",
                "membership_id": identifier,
                "function_id": response.json()["identifier"],
                "active": True,
            },
        )
        assert assigned.status_code == 200, assigned.text
    await flow.login(actor="new_employee")
    assert (
        await flow.command(
            operation="physical_state", table_id=flow.graph.table_id, state="available"
        )
    ).status_code == 403
    assert (await flow.client.get(flow.root + "/workspace")).status_code == 403
    async with flow.graph.factory() as session:
        assert (
            await session.scalar(
                text(
                    "SELECT count(*) FROM dining_staff_assignments WHERE membership_id=:id AND active"
                ),
                {"id": identifier},
            )
            == 2
        )
        assert (
            await session.scalar(
                text(
                    "SELECT count(*) FROM dining_grants WHERE membership_id=:id AND active"
                ),
                {"id": identifier},
            )
            == 0
        )


# ==============================================
# MID-SESSION SUSPENSION AND PERMANENT REVOCATION
# The same valid cookie loses authority; resumption cannot restore old grants silently.
# ==============================================


async def test_suspension_and_revocation_invalidate_existing_session(
    flow: SignedFlow,
) -> None:
    """Retain the employment and audit history while clearing effective powers."""
    identifier = await activated(flow=flow)
    result = await flow.command(
        operation="grant",
        membership_id=identifier,
        capability="read",
        actor_kind="human",
        active=True,
    )
    assert result.status_code == 200, result.text
    await flow.login(actor="new_employee")
    assert (await flow.client.get(flow.root + "/workspace")).status_code == 200
    # Keep the original employee cookie in RAM; do not issue a fresh employee token.
    employee_cookies = [copy(cookie) for cookie in flow.client.cookies.jar]
    await flow.login(actor="owner")
    assert (
        await change_status(flow=flow, identifier=identifier, status="suspended")
    ).status_code == 200
    flow.client.cookies.clear()
    for cookie in employee_cookies:
        flow.client.cookies.jar.set_cookie(copy(cookie))
    assert (await flow.client.get(flow.root + "/workspace")).status_code == 403
    await flow.login(actor="owner")
    assert (
        await change_status(flow=flow, identifier=identifier, status="active")
    ).status_code == 200
    flow.client.cookies.clear()
    for cookie in employee_cookies:
        flow.client.cookies.jar.set_cookie(copy(cookie))
    assert (await flow.client.get(flow.root + "/workspace")).status_code == 403
    await flow.login(actor="owner")
    assert (
        await change_status(flow=flow, identifier=identifier, status="revoked")
    ).status_code == 200
    assert (
        await change_status(flow=flow, identifier=identifier, status="revoked")
    ).status_code == 200
    current = await member(flow=flow, identifier=identifier)
    assert current["status"] == "revoked"
    async with flow.graph.factory() as session:
        assert (
            await session.scalar(
                text(
                    "SELECT count(*) FROM tenant_audit_events WHERE target_membership_id=:id"
                ),
                {"id": identifier},
            )
            >= 4
        )
        assert (
            await session.scalar(
                text(
                    "SELECT count(*) FROM dining_grants WHERE membership_id=:id AND active"
                ),
                {"id": identifier},
            )
            == 0
        )


# ==============================================
# OWNER CEILING AND CROSS-ESTABLISHMENT REJECTION
# Direct API access cannot bypass the role or target scope checked by the service.
# ==============================================


@pytest.mark.parametrize(
    "actor", ["service", "cleaner", "finance", "assistant", "outsider"]
)
async def test_non_owner_cannot_manage_staff(flow: SignedFlow, actor: str) -> None:
    """Function management and state mutation both require current owner authority."""
    await flow.login(actor=actor)
    response = await flow.client.post(
        flow.root + "/staff",
        json={
            "operation": "function",
            "code": "forbidden",
            "labels": {"fr": "Non", "en": "No", "ar": "لا"},
            "tasks": [],
            "active": True,
        },
    )
    assert response.status_code == 403, response.text


# ==============================================
# COMPETING OWNER DECISIONS
# The organization write lock and target revision allow only one conflicting transition.
# ==============================================


async def test_competing_status_changes_keep_one_committed_transition(
    flow: SignedFlow,
) -> None:
    """Simultaneous suspension/revocation cannot both apply the same target revision."""
    identifier = await activated(flow=flow)
    current = await member(flow=flow, identifier=identifier)
    responses = await asyncio.gather(
        *(
            flow.client.post(
                flow.root + "/staff",
                json={
                    "operation": "status",
                    "membership_id": identifier,
                    "expected_revision": current["revision"],
                    "status": status,
                    "reason": "Décision concurrente fictive",
                },
            )
            for status in ("suspended", "revoked")
        )
    )
    assert sorted(response.status_code for response in responses) == [200, 409]
    after = await member(flow=flow, identifier=identifier)
    assert after["revision"] == current["revision"] + 1


# ==============================================
# FAILED INVITATION HAS NO PARTIAL RELATIONSHIP
# A duplicate professional code must roll back membership, grants and staged audit.
# ==============================================


async def test_failed_profile_creation_rolls_back_entire_invitation(
    flow: SignedFlow,
) -> None:
    """An independent session proves that the rejected account gained no relationship."""
    await account(flow=flow)
    await account(flow=flow, actor="second_employee", offset=81)
    await flow.login(actor="owner")
    assert (await invite(flow=flow)).status_code == 200
    assert (await invite(flow=flow, actor="second_employee")).status_code == 409
    async with flow.graph.factory() as session:
        assert (
            await session.scalar(
                text(
                    "SELECT count(*) FROM organization_memberships WHERE identity_id=:id"
                ),
                {"id": flow.graph.base + 81},
            )
            == 0
        )
