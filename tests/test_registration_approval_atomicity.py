# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# REAL REGISTRATION APPROVAL ATOMICITY
# Observe committed S1a state through independent sessions after failures, retries and races.
# ==============================================

"""Use real transactions and committed fixtures; cleanup is never the atomicity proof."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND PERSISTED TEST CONTRACTS
# Keep all identities, trial configuration and outbox recipients synthetic and local.
# ==============================================

import asyncio
import json
from collections.abc import (
    Awaitable,
    Callable,
)
from dataclasses import dataclass
from pathlib import Path
from typing import (
    Literal,
    TypeAlias,
)

import pytest
from sqlalchemy import (
    event,
    insert,
    text,
)
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.admin_session import AdminSession
from app.models.agent import (
    Agent,
    Channel,
    Conversation,
)
from app.models.owner import Owner
from app.models.registration_request import RegistrationRequest
from app.models.restaurant import Restaurant
from app.models.subscription import (
    Feature,
    SubscriptionPlan,
)

from app.services.business.registration_request_service import RegistrationRequestService  # isort: skip  # fmt: skip
from app.services.business.subscription_contract import INCLUDED
from test_support.local_postgres import LocalPostgresSettings

SessionFactory: TypeAlias = async_sessionmaker[AsyncSession]
State: TypeAlias = dict[str, tuple[int, str]]
FailureStage: TypeAlias = Literal[
    "owner",
    "restaurant",
    "trial_row",
    "rights",
    "outbox",
    "trial_complete",
    "final_request",
    "commit",
]
TABLES = (
    "owners",
    "restaurants",
    "registration_requests",
    "subscriptions",
    "subscription_features",
    "subscription_reminders",
)


# ==============================================
# EXPLICIT FAILURE INJECTION
# Raise only after the selected real domain or SQL operation has executed.
# ==============================================


class InjectedFailure(RuntimeError):
    """Identify an intentional local failure without replacing any database transaction."""


@dataclass(frozen=True)
class ApprovalGraph:
    """Identify committed fixtures and the independent sessions observing their state."""

    sessions: SessionFactory
    engine: AsyncEngine
    request: int
    owner: int | None
    unrelated_owner: int
    unrelated_restaurant: int
    plan: int
    features: tuple[int, ...]


# ==============================================
# COMMITTED SYNTHETIC SETUP
# Commit the pending request and unrelated tenant before any approval operation begins.
# ==============================================


@pytest.fixture
async def approval_graph(
    request: pytest.FixtureRequest,
    test_database_engine: AsyncEngine,
    cleanup_test_database: None,
) -> ApprovalGraph:
    """Create real committed prerequisites, without binding service sessions to fixture transactions."""
    configuration = test_database_engine.sync_engine.get_execution_options().get(
        "moulai_local_configuration"
    )
    if (
        not isinstance(configuration, LocalPostgresSettings)
        or configuration.PROFILE != "main"
    ):
        raise RuntimeError("approval_atomicity_requires_main_local_profile")
    sessions = async_sessionmaker(test_database_engine, expire_on_commit=False)
    async with sessions() as session, session.begin():
        plan = (
            await session.execute(
                insert(SubscriptionPlan)
                .values(
                    code="trial",
                    name="Synthetic trial",
                    base_price=0,
                    plan_discount_percent=0,
                    active=True,
                )
                .returning(SubscriptionPlan.id)
            )
        ).scalar_one()
        features: list[int] = []
        for code in sorted(INCLUDED["trial"]):
            features.append(
                (
                    await session.execute(
                        insert(Feature)
                        .values(code=code, name="Synthetic " + code)
                        .returning(Feature.id)
                    )
                ).scalar_one()
            )
        unrelated_owner = (
            await session.execute(
                insert(Owner)
                .values(
                    chat_id=99077001,
                    full_name="Unrelated synthetic owner",
                    phone="0555000000",
                    registration_status="approved",
                    trial_used=True,
                )
                .returning(Owner.id)
            )
        ).scalar_one()
        unrelated_restaurant = (
            await session.execute(
                insert(Restaurant)
                .values(
                    owner_id=unrelated_owner,
                    name="Unrelated synthetic restaurant",
                    type="restaurant",
                    phone="0555000000",
                    wilaya="Test",
                )
                .returning(Restaurant.id)
            )
        ).scalar_one()
        owner = None
        if getattr(request, "param", False):
            owner = (
                await session.execute(
                    insert(Owner)
                    .values(
                        chat_id=99077002,
                        full_name="Existing synthetic applicant",
                        phone="0555000000",
                        registration_status="pending",
                        trial_used=False,
                    )
                    .returning(Owner.id)
                )
            ).scalar_one()
        identifier = (
            await session.execute(
                insert(RegistrationRequest)
                .values(
                    chat_id=99077002,
                    full_name="Synthetic applicant",
                    owner_phone="0555000000",
                    restaurant_name="Synthetic new restaurant",
                    restaurant_type="restaurant",
                    restaurant_phone="0555000000",
                    wilaya="Test",
                    status="pending",
                    owner_id=owner,
                )
                .returning(RegistrationRequest.id)
            )
        ).scalar_one()
    return ApprovalGraph(
        sessions,
        test_database_engine,
        identifier,
        owner,
        unrelated_owner,
        unrelated_restaurant,
        plan,
        tuple(features),
    )


# ==============================================
# INDEPENDENT PERSISTED SNAPSHOT
# Read committed rows and complete row fingerprints with a brand-new observer session.
# ==============================================


async def persisted_state(*, graph: ApprovalGraph) -> State:
    """Compare all approval-related rows, including pre-existing tenants and trial eligibility."""
    result: State = {}
    async with graph.sessions() as observer:
        for table in TABLES:
            row = (
                await observer.execute(
                    text(
                        f"SELECT count(*) AS count, md5(coalesce(string_agg(md5(to_jsonb(t)::text),'' ORDER BY md5(to_jsonb(t)::text)),'')) AS fingerprint FROM public.{table} t"
                    )
                )
            ).one()
            result[table] = (row[0], row[1])
    return result


# ==============================================
# INJECT FAILURES WITHOUT MOCKING PERSISTENCE
# Reuse real repository methods and inject only a post-operation exception.
# ==============================================


def inject_failure(
    *,
    monkeypatch: pytest.MonkeyPatch,
    service: RegistrationRequestService,
    stage: FailureStage,
    engine: AsyncEngine,
) -> Callable[[], None]:
    """Return listener cleanup; never replace commit, rollback, SQL queries or their results."""
    if stage in {"rights", "commit"}:
        fired = False
        if stage == "rights":
            # SQLAlchemy's event callback must retain its required positional signature.
            def after_sql(
                connection: Connection,
                cursor: object,
                statement: str,
                parameters: object,
                context: object,
                executemany: bool,
            ) -> None:
                """Fail after a real entitlement INSERT has reached PostgreSQL."""
                nonlocal fired
                if not fired and statement.lower().replace('"', "").lstrip().startswith(
                    "insert into subscription_features"
                ):
                    fired = True
                    raise InjectedFailure("rights_insert")

            event.listen(engine.sync_engine, "after_cursor_execute", after_sql)
            return lambda: event.remove(
                engine.sync_engine, "after_cursor_execute", after_sql
            )

        def before_commit(session: Session) -> None:
            """Reject the real outer commit after all staged writes, but not nested savepoints."""
            nonlocal fired
            if not fired and not session.in_nested_transaction():
                fired = True
                raise InjectedFailure("commit")

        event.listen(service.session.sync_session, "before_commit", before_commit)
        return lambda: event.remove(
            service.session.sync_session, "before_commit", before_commit
        )
    target: object
    name: str
    if stage == "owner":
        target, name = service.owner_service, "create_owner"
    elif stage == "restaurant":
        target, name = service.restaurant_repo, "create"
    elif stage == "trial_row":
        target, name = service.subscription_service.repo, "create"
    elif stage == "trial_complete":
        target, name = service.subscription_service, "create_trial_subscription"
    elif stage == "final_request":
        target, name = service.repo, "approve"
    else:
        from app.services.business import subscription_reminders

        target, name = subscription_reminders, "schedule"
    original: Callable[..., Awaitable[object]] = getattr(target, name)

    async def after_operation(**kwargs: object) -> object:
        """Execute the actual operation before raising the selected intentional failure."""
        await original(**kwargs)
        raise InjectedFailure(stage)

    monkeypatch.setattr(target, name, after_operation)
    return lambda: None


# ==============================================
# CONFIGURATION BEFORE ANY CREATION
# Prove missing prerequisites cause no owner/restaurant/trial INSERT, even temporarily.
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "missing", ["plan", "inactive_plan", "feature", "reminder_config", "reminder_days"]
)
async def test_configuration_is_checked_before_creating_records(
    approval_graph: ApprovalGraph, missing: str
) -> None:
    """Check actual INSERT statements and independent committed state after the rejected attempt."""
    graph = approval_graph
    async with graph.sessions() as setup, setup.begin():
        if missing == "plan":
            await setup.execute(
                text("DELETE FROM subscription_plans WHERE id=:id"), {"id": graph.plan}
            )
        elif missing == "inactive_plan":
            await setup.execute(
                text("UPDATE subscription_plans SET active=false WHERE id=:id"),
                {"id": graph.plan},
            )
        elif missing == "feature":
            await setup.execute(
                text("DELETE FROM features WHERE id=:id"), {"id": graph.features[0]}
            )
        elif missing == "reminder_config":
            await setup.execute(text("DELETE FROM subscription_pricing_config"))
        else:
            await setup.execute(
                text("UPDATE subscription_pricing_config SET policies='{}'::json")
            )
    before = await persisted_state(graph=graph)
    inserts: list[str] = []

    def observe(
        connection: Connection,
        cursor: object,
        statement: str,
        parameters: object,
        context: object,
        executemany: bool,
    ) -> None:
        """Record only statement categories, without parameters or personal fields."""
        normalized = statement.lower().replace('"', "").lstrip()
        if normalized.startswith("insert into"):
            inserts.append(normalized.split()[2])

    event.listen(graph.engine.sync_engine, "before_cursor_execute", observe)
    try:
        async with graph.sessions() as writer:
            with pytest.raises(ValueError):
                await RegistrationRequestService(session=writer).approve(
                    request_id=graph.request
                )
            await writer.commit()
    finally:
        event.remove(graph.engine.sync_engine, "before_cursor_execute", observe)
    assert not inserts
    assert await persisted_state(graph=graph) == before


# ==============================================
# FAILURES AT EACH MUTATION STAGE
# A caller catching the exception and committing still cannot persist partial approval rows.
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "approval_graph,stage",
    [
        (existing, stage)
        for existing in (False, True)
        for stage in (
            "owner",
            "restaurant",
            "trial_row",
            "rights",
            "outbox",
            "trial_complete",
            "final_request",
            "commit",
        )
        if not (existing and stage == "owner")
    ],
    indirect=["approval_graph"],
)
async def test_failure_cannot_persist_partial_records(
    approval_graph: ApprovalGraph, monkeypatch: pytest.MonkeyPatch, stage: FailureStage
) -> None:
    """Observe the database independently after failure and an explicit caller commit."""
    graph = approval_graph
    before = await persisted_state(graph=graph)
    async with graph.sessions() as writer:
        service = RegistrationRequestService(session=writer)
        remove = inject_failure(
            monkeypatch=monkeypatch, service=service, stage=stage, engine=graph.engine
        )
        try:
            with pytest.raises(InjectedFailure):
                await service.approve(request_id=graph.request)
            assert "defer_repository_commit" not in writer.info
            await writer.commit()
            after = await persisted_state(graph=graph)
            assert after == before
            async with graph.sessions() as observer:
                trial_used = (
                    await observer.execute(
                        text("SELECT trial_used FROM owners WHERE chat_id=99077002")
                    )
                ).scalar_one_or_none()
            configuration = graph.engine.sync_engine.get_execution_options()[
                "moulai_local_configuration"
            ]
            output = (
                Path(__file__).resolve().parents[1]
                / "artifacts/postgres-local-tests"
                / configuration.INSTANCE_ID
            )
            (
                output
                / f"failure-proof-{stage}-{'existing' if graph.owner is not None else 'new'}.json"
            ).write_text(
                json.dumps(
                    {
                        "stage": stage,
                        "preexisting_applicant": graph.owner is not None,
                        "observed_from_independent_session": True,
                        "caller_committed_after_error": True,
                        "before": before,
                        "after": after,
                        "applicant_trial_used_after": trial_used,
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
        finally:
            remove()


# ==============================================
# SUCCESS AND REPEAT AFTER COMMIT
# Persist exactly one new trial, its rights and both reminder schedules in one outer commit.
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("approval_graph", [False, True], indirect=True)
async def test_success_commits_once_and_repeat_creates_nothing(
    approval_graph: ApprovalGraph,
) -> None:
    """Read every successful effect through another session and refuse repeated approval."""
    graph = approval_graph
    outer_commits: list[int] = []
    async with graph.sessions() as writer:

        def committed(session: Session) -> None:
            """Count only the outer business commit, not the nested trial savepoint."""
            if not session.in_nested_transaction():
                outer_commits.append(1)

        event.listen(writer.sync_session, "before_commit", committed)
        result = await RegistrationRequestService(session=writer).approve(
            request_id=graph.request
        )
    assert outer_commits == [1]
    async with graph.sessions() as observer:
        row = (
            await observer.execute(
                text("SELECT status,owner_id FROM registration_requests WHERE id=:id"),
                {"id": graph.request},
            )
        ).one()
        assert row.status == "approved" and row.owner_id == result.owner_id
        assert (
            await observer.execute(
                text("SELECT trial_used FROM owners WHERE id=:id"),
                {"id": result.owner_id},
            )
        ).scalar_one() is True
        assert (
            await observer.execute(text("SELECT count(*) FROM subscription_features"))
        ).scalar_one() == len(graph.features)
        assert (
            await observer.execute(text("SELECT count(*) FROM subscription_reminders"))
        ).scalar_one() == 8
    state = await persisted_state(graph=graph)
    async with graph.sessions() as writer:
        with pytest.raises(ValidationError):
            await RegistrationRequestService(session=writer).approve(
                request_id=graph.request
            )
        await writer.commit()
    assert await persisted_state(graph=graph) == state


# ==============================================
# RETRY AFTER A FULLY ROLLED-BACK ATTEMPT
# Restore the right to a first trial and retain all pre-existing tenant data.
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("approval_graph", [False, True], indirect=True)
async def test_failed_attempt_can_be_retried_without_losing_existing_data(
    approval_graph: ApprovalGraph, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A final-request failure spends no trial right; a later clean attempt succeeds once."""
    graph = approval_graph
    before = await persisted_state(graph=graph)
    async with graph.sessions() as writer:
        with monkeypatch.context() as patch:
            service = RegistrationRequestService(session=writer)
            inject_failure(
                monkeypatch=patch,
                service=service,
                stage="final_request",
                engine=graph.engine,
            )
            with pytest.raises(InjectedFailure):
                await service.approve(request_id=graph.request)
            await writer.commit()
    assert await persisted_state(graph=graph) == before
    async with graph.sessions() as writer:
        result = await RegistrationRequestService(session=writer).approve(
            request_id=graph.request
        )
    if graph.owner is not None:
        assert result.owner_id == graph.owner
    async with graph.sessions() as observer:
        assert (
            await observer.execute(text("SELECT count(*) FROM subscriptions"))
        ).scalar_one() == 1
        assert (
            await observer.execute(
                text("SELECT name FROM restaurants WHERE id=:id"),
                {"id": graph.unrelated_restaurant},
            )
        ).scalar_one() == "Unrelated synthetic restaurant"


# ==============================================
# CONCURRENT APPROVALS OF ONE OR TWO REQUESTS
# Exercise separate real sessions, including the identity race before an owner exists.
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("approval_graph", [False, True], indirect=True)
@pytest.mark.parametrize("same_request", [False, True])
async def test_concurrent_approvals_grant_one_trial_only(
    approval_graph: ApprovalGraph, same_request: bool
) -> None:
    """Row/identity/owner locks leave one winner and no partial losing restaurant."""
    graph = approval_graph
    second = graph.request
    if not same_request:
        async with graph.sessions() as setup, setup.begin():
            second = (
                await setup.execute(
                    insert(RegistrationRequest)
                    .values(
                        chat_id=99077002,
                        full_name="Synthetic applicant",
                        owner_phone="0555000000",
                        restaurant_name="Second synthetic request",
                        restaurant_type="restaurant",
                        restaurant_phone="0555000000",
                        wilaya="Test",
                        status="pending",
                        owner_id=graph.owner,
                    )
                    .returning(RegistrationRequest.id)
                )
            ).scalar_one()
    start = asyncio.Event()

    async def run(identifier: int) -> bool:
        """Start each approval on its own unbound session and preserve the domain refusal."""
        async with graph.sessions() as writer:
            await start.wait()
            try:
                await RegistrationRequestService(session=writer).approve(
                    request_id=identifier
                )
            except (ValidationError, ValueError):
                return False
            return True

    tasks = [asyncio.create_task(run(graph.request)), asyncio.create_task(run(second))]
    start.set()
    outcomes = await asyncio.wait_for(asyncio.gather(*tasks), timeout=30)
    assert sorted(outcomes) == [False, True]
    async with graph.sessions() as observer:
        assert (
            await observer.execute(
                text("SELECT count(*) FROM owners WHERE chat_id=99077002")
            )
        ).scalar_one() == 1
        assert (
            await observer.execute(text("SELECT count(*) FROM restaurants"))
        ).scalar_one() == 2
        assert (
            await observer.execute(text("SELECT count(*) FROM subscriptions"))
        ).scalar_one() == 1
        assert (
            await observer.execute(text("SELECT count(*) FROM subscription_features"))
        ).scalar_one() == len(graph.features)
        assert (
            await observer.execute(
                text(
                    "SELECT count(*) FROM registration_requests WHERE status='approved'"
                )
            )
        ).scalar_one() == 1


# ==============================================
# REFRESH A REQUEST ALREADY CACHED BY THE CALLER
# Never trust the stale pending status from an earlier read-triggered transaction.
# ==============================================


@pytest.mark.asyncio
async def test_cached_pending_request_is_refreshed_under_lock(
    approval_graph: ApprovalGraph,
) -> None:
    """A second session's committed approval defeats the caller's stale identity-map entry."""
    graph = approval_graph
    async with graph.sessions() as stale:
        await stale.get(RegistrationRequest, graph.request)
        async with graph.sessions() as writer:
            await RegistrationRequestService(session=writer).approve(
                request_id=graph.request
            )
        before = await persisted_state(graph=graph)
        with pytest.raises(ValidationError):
            await RegistrationRequestService(session=stale).approve(
                request_id=graph.request
            )
        await stale.commit()
    assert await persisted_state(graph=graph) == before


# ==============================================
# EXPLICIT CALLER TRANSACTION OWNERSHIP
# Outbox rows stay invisible until the caller commits, and a failed attempt preserves their work.
# ==============================================


@pytest.mark.asyncio
async def test_caller_transaction_controls_success_visibility(
    approval_graph: ApprovalGraph,
) -> None:
    """Approval joins an explicit unit of work without publishing trial or outbox early."""
    graph = approval_graph
    before = await persisted_state(graph=graph)
    async with graph.sessions() as writer:
        async with writer.begin():
            await RegistrationRequestService(session=writer).approve(
                request_id=graph.request
            )
            assert await persisted_state(graph=graph) == before
        assert (await persisted_state(graph=graph))["subscriptions"][0] == 1


@pytest.mark.asyncio
async def test_failed_nested_approval_preserves_caller_changes(
    approval_graph: ApprovalGraph, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The approval savepoint rolls back its records while an unrelated caller edit survives."""
    graph = approval_graph
    async with graph.sessions() as writer, writer.begin():
        await writer.execute(
            text("UPDATE restaurants SET name='Caller-owned change' WHERE id=:id"),
            {"id": graph.unrelated_restaurant},
        )
        service = RegistrationRequestService(session=writer)
        inject_failure(
            monkeypatch=monkeypatch,
            service=service,
            stage="final_request",
            engine=graph.engine,
        )
        with pytest.raises(InjectedFailure):
            await service.approve(request_id=graph.request)
    async with graph.sessions() as observer:
        assert (
            await observer.execute(
                text("SELECT name FROM restaurants WHERE id=:id"),
                {"id": graph.unrelated_restaurant},
            )
        ).scalar_one() == "Caller-owned change"
        assert (
            await observer.execute(text("SELECT count(*) FROM subscriptions"))
        ).scalar_one() == 0
        assert (
            await observer.execute(
                text("SELECT status FROM registration_requests WHERE id=:id"),
                {"id": graph.request},
            )
        ).scalar_one() == "pending"


# ==============================================
# ORM DECLARATIONS MATCH THE RETAINED DDL
# Validate only the five expressly authorized metadata alignments.
# ==============================================


@pytest.mark.parametrize("model", [Agent, Channel, Conversation, AdminSession])
def test_activity_boolean_is_not_nullable_in_orm(
    model: type[Agent | Channel | Conversation | AdminSession],
) -> None:
    """The four activity booleans now declare the existing main NOT NULL contract."""
    assert model.__table__.c.is_active.nullable is False


def test_registration_owner_foreign_key_matches_set_null() -> None:
    """Nullable owner references preserve the main migration's explicit SET NULL action."""
    column = RegistrationRequest.__table__.c.owner_id
    assert column.nullable is True
    assert next(iter(column.foreign_keys)).ondelete == "SET NULL"


# ==============================================
# PRE-EXISTING TRIAL CONSUMPTION AND HISTORY
# Preserve refusal even when an old historical record is present but the boolean is stale.
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("approval_graph", [True], indirect=True)
@pytest.mark.parametrize("history", [False, True])
async def test_existing_trial_right_cannot_be_reissued(
    approval_graph: ApprovalGraph, history: bool
) -> None:
    """Neither a consumed flag nor a prior trial may be bypassed by a fresh registration request."""
    graph = approval_graph
    async with graph.sessions() as setup, setup.begin():
        if history:
            restaurant = (
                await setup.execute(
                    insert(Restaurant)
                    .values(
                        owner_id=graph.owner,
                        name="Existing owned restaurant",
                        type="restaurant",
                        phone="0555000000",
                        wilaya="Test",
                    )
                    .returning(Restaurant.id)
                )
            ).scalar_one()
            await setup.execute(
                text(
                    "INSERT INTO subscriptions (owner_id,restaurant_id,plan_id,billing_cycle,amount,status) VALUES (:owner,:restaurant,:plan,'trial',0,'expired')"
                ),
                {"owner": graph.owner, "restaurant": restaurant, "plan": graph.plan},
            )
        else:
            await setup.execute(
                text("UPDATE owners SET trial_used=true WHERE id=:id"),
                {"id": graph.owner},
            )
    before = await persisted_state(graph=graph)
    async with graph.sessions() as writer:
        with pytest.raises(ValueError, match="trial_already_used"):
            await RegistrationRequestService(session=writer).approve(
                request_id=graph.request
            )
        await writer.commit()
    assert await persisted_state(graph=graph) == before


# ==============================================
# AUTOBEGIN FROM A NORMAL CALLER READ
# Verify the service commits its complete unit even when authentication/lookup read first.
# ==============================================


@pytest.mark.asyncio
async def test_read_autobegin_success_is_committed_by_service(
    approval_graph: ApprovalGraph,
) -> None:
    """A read-triggered transaction is completed by the service and visible independently."""
    graph = approval_graph
    async with graph.sessions() as writer:
        cached = await writer.get(RegistrationRequest, graph.request)
        assert cached is not None
        await RegistrationRequestService(session=writer).approve(
            request_id=graph.request
        )
        assert not writer.in_transaction()
        assert (await persisted_state(graph=graph))["subscriptions"][0] == 1
