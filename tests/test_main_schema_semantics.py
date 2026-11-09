# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MAIN S1A SCHEMA SEMANTIC REGRESSIONS
# Exercise SQL defaults, nullability, owner deletion and existing uniqueness in isolation.
# ==============================================

"""Verify observable compatibility decisions using raw SQL and real local services."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS AND EXPLICIT SCALAR CONTRACTS
# Keep SQL fixtures synthetic and avoid ORM defaults when testing database defaults.
# ==============================================

import json
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal
from pathlib import Path
from typing import (
    Literal,
    TypeAlias,
)
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
)

from app.core.exceptions import ValidationError
from app.schemas.agent.agent import AgentUpdate
from app.schemas.agent.channel import ChannelUpdate
from app.schemas.agent.conversation import ConversationUpdate
from app.services.business.agent.agent_service import AgentService
from app.services.business.agent.channel_service import ChannelService
from app.services.business.agent.conversation_service import ConversationService
from app.services.business.owner_service import OwnerService

from app.services.business.registration_request_service import RegistrationRequestService  # isort: skip  # fmt: skip
from app.services.business.subscription_contract import INCLUDED
from test_support.local_postgres import LocalPostgresSettings

SqlScalar: TypeAlias = str | int | bool | datetime | Decimal | None
ActivityTable: TypeAlias = Literal["agents", "channels", "conversations"]


# ==============================================
# EXPECTED DATABASE CONTRACT
# Record the fifteen approved historical defaults independently of current ORM metadata.
# ==============================================


@dataclass(frozen=True)
class DefaultCase:
    """Describe an omitted value, an explicit override and permitted NULL storage."""

    # ==============================================
    # EXPECTED FIELD CONTRACT
    # Keep nullability explicit so assertions do not infer their expectations from the database.
    # ==============================================

    table: str
    column: str
    expected: str | bool
    alternate: str | bool
    nullable: bool = False


CASES = (
    DefaultCase("agents", "is_active", True, False),
    DefaultCase("channels", "is_active", True, False),
    DefaultCase("conversations", "is_active", True, False),
    DefaultCase("admin_sessions", "is_active", True, False),
    DefaultCase("agents", "name", "My Assistant", "Synthetic explicit name"),
    DefaultCase("agents", "language", "ar", "fr", True),
    DefaultCase("agents", "tone", "professional", "casual", True),
    DefaultCase("restaurant_payment_settings", "allow_cash", True, False),
    DefaultCase("restaurant_payment_settings", "allow_card", True, False),
    DefaultCase("restaurant_payment_settings", "allow_ccp", False, True),
    DefaultCase("restaurant_payment_settings", "allow_baridimob", False, True),
    DefaultCase("restaurant_payment_settings", "allow_stripe", False, True),
    DefaultCase("restaurant_payment_settings", "allow_paypal", False, True),
    DefaultCase("roles", "is_active", True, False),
    DefaultCase("users", "consent", False, True, True),
)


# ==============================================
# ROLLBACK-ONLY LOCAL CONNECTION
# Never use the destructive global cleanup fixture or a permanent database for these probes.
# ==============================================


@pytest.fixture
async def schema_connection(
    test_database_engine: AsyncEngine, verify_test_schema_revision: None
) -> AsyncGenerator[AsyncConnection, None]:
    """Require the main local profile and roll back every row, including service commits."""
    configuration = test_database_engine.sync_engine.get_execution_options().get(
        "moulai_local_configuration"
    )
    if (
        not isinstance(configuration, LocalPostgresSettings)
        or configuration.PROFILE != "main"
    ):
        raise RuntimeError("schema_semantics_require_disposable_main_profile")
    async with test_database_engine.connect() as connection:
        transaction = await connection.begin()
        try:
            yield connection
        finally:
            if not transaction.is_active:
                raise RuntimeError("semantic_probe_escaped_outer_transaction")
            await transaction.rollback()


# ==============================================
# RAW SYNTHETIC INSERT
# Execute plain bound SQL so SQLAlchemy Python-side defaults cannot mask omitted fields.
# ==============================================


async def insert_row(
    *, connection: AsyncConnection, table: str, values: dict[str, SqlScalar]
) -> int:
    """Return one synthetic identifier using only simple internal table/column names."""
    if not table.isidentifier() or any(not key.isidentifier() for key in values):
        raise ValueError("fixture_identifier_not_simple")
    names = ", ".join(f'"{key}"' for key in values)
    placeholders = ", ".join(f":{key}" for key in values)
    statement = (
        f'INSERT INTO public."{table}" ({names}) VALUES ({placeholders}) RETURNING id'
    )
    return int((await connection.execute(text(statement), values)).scalar_one())


# ==============================================
# MINIMAL SYNTHETIC RELATIONSHIPS
# Create no plans, prices, permissions, channels or identities outside the rollback transaction.
# ==============================================


@dataclass(frozen=True)
class Graph:
    """Hold only identifiers required by the schema and service probes."""

    # ==============================================
    # SYNTHETIC PARENT IDENTIFIERS
    # Share only transaction-local keys between related insert probes.
    # ==============================================

    owner: int
    restaurant: int
    admin: int
    agent: int
    channel: int
    conversation: int


# ==============================================
# SYNTHETIC GRAPH FIXTURE
# Supply valid JSON response fields while leaving the tested SQL defaults omitted.
# ==============================================


@pytest.fixture
async def schema_graph(schema_connection: AsyncConnection) -> Graph:
    """Create synthetic untagged parents without real Telegram identities or external calls."""
    owner = await insert_row(
        connection=schema_connection,
        table="owners",
        values={
            "chat_id": 99188001,
            "registration_status": "approved",
            "full_name": "Synthetic owner",
            "phone": "0555000000",
            "trial_used": True,
        },
    )
    restaurant = await insert_row(
        connection=schema_connection,
        table="restaurants",
        values={
            "owner_id": owner,
            "name": "Synthetic restaurant",
            "type": "restaurant",
            "phone": "0555000000",
            "wilaya": "Test",
            "is_active": True,
        },
    )
    admin = await insert_row(
        connection=schema_connection,
        table="admins",
        values={
            "chat_id": 99188002,
            "role": "support",
            "full_name": "Synthetic admin",
            "is_active": True,
        },
    )
    agent = await insert_row(
        connection=schema_connection,
        table="agents",
        values={"restaurant_id": restaurant, "config": "{}", "ai_config": "{}"},
    )
    channel = await insert_row(
        connection=schema_connection,
        table="channels",
        values={
            "agent_id": agent,
            "type": "web",
            "name": "Synthetic channel",
            "config": "{}",
        },
    )
    conversation = await insert_row(
        connection=schema_connection,
        table="conversations",
        values={"agent_id": agent, "channel_id": channel, "user_id": "synthetic-user"},
    )
    return Graph(owner, restaurant, admin, agent, channel, conversation)


# ==============================================
# DEFAULTS AND EXPLICIT NULL BEHAVIOR
# Exercise omission, override, NULL INSERT and NULL UPDATE for each changed default.
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("case", CASES, ids=lambda case: f"{case.table}.{case.column}")
async def test_changed_default_omission_override_and_explicit_null(
    schema_connection: AsyncConnection, schema_graph: Graph, case: DefaultCase
) -> None:
    """Defaults fill omissions only; explicit false/text survives, and NOT NULL rejects NULL."""
    graph = schema_graph
    payloads: dict[str, dict[str, SqlScalar]] = {
        "agents": {"restaurant_id": graph.restaurant, "name": "Synthetic agent"},
        "channels": {
            "agent_id": graph.agent,
            "type": "web",
            "name": "Synthetic other channel",
        },
        "conversations": {
            "agent_id": graph.agent,
            "channel_id": graph.channel,
            "user_id": "synthetic-other-user",
        },
        "admin_sessions": {
            "admin_id": graph.admin,
            "session_token": uuid4().hex,
            "expires_at": datetime(2030, 1, 1, tzinfo=timezone.utc).replace(
                tzinfo=None
            ),
        },
        "restaurant_payment_settings": {"restaurant_id": graph.restaurant},
        "roles": {"code": "synthetic-probe", "name": "Synthetic role"},
        "users": {"chat_id": 99188003},
    }
    payload = payloads[case.table]
    payload.pop(case.column, None)
    row = await insert_row(
        connection=schema_connection, table=case.table, values=payload
    )
    query = text(f'SELECT "{case.column}" FROM public."{case.table}" WHERE id=:id')
    assert (
        await schema_connection.execute(query, {"id": row})
    ).scalar_one() == case.expected
    await schema_connection.execute(
        text(f'UPDATE public."{case.table}" SET "{case.column}"=:value WHERE id=:id'),
        {"value": case.alternate, "id": row},
    )
    assert (
        await schema_connection.execute(query, {"id": row})
    ).scalar_one() == case.alternate
    # Reuse the same identifiers only inside a savepoint, avoiding unrelated unique conflicts.
    for operation in ("insert", "update"):
        nested = await schema_connection.begin_nested()
        try:
            if operation == "insert":
                await schema_connection.execute(
                    text(f'DELETE FROM public."{case.table}" WHERE id=:id'), {"id": row}
                )
                action = insert_row(
                    connection=schema_connection,
                    table=case.table,
                    values={**payload, case.column: None},
                )
            else:
                action = schema_connection.execute(
                    text(
                        f'UPDATE public."{case.table}" SET "{case.column}"=NULL WHERE id=:id'
                    ),
                    {"id": row},
                )
            if case.nullable:
                inserted_or_result = await action
                null_row = inserted_or_result if operation == "insert" else row
                assert (
                    await schema_connection.execute(query, {"id": null_row})
                ).scalar_one() is None
            else:
                with pytest.raises(IntegrityError) as error:
                    await action
                assert getattr(error.value.orig, "sqlstate", None) == "23502"
        finally:
            await nested.rollback()
    assert (
        await schema_connection.execute(query, {"id": row})
    ).scalar_one() == case.alternate


# ==============================================
# REAL SERVICE NULL PATCHES
# Prove the repository ignores None while preserving explicit false on active-state updates.
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("table", ["agents", "channels", "conversations"])
async def test_activity_service_false_and_null_patch_are_compatible(
    schema_connection: AsyncConnection, schema_graph: Graph, table: ActivityTable
) -> None:
    """An explicit false remains false; nullable PATCH input does not write a database NULL."""
    async with AsyncSession(
        bind=schema_connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    ) as session:
        for active in (False, None):
            if table == "agents":
                response = await AgentService(
                    session=session, owner_id=schema_graph.owner
                ).update(
                    agent_id=schema_graph.agent,
                    update_data=AgentUpdate(is_active=active),
                )
            elif table == "channels":
                response = await ChannelService(
                    session=session, owner_id=schema_graph.owner
                ).update(
                    channel_id=schema_graph.channel,
                    update_data=ChannelUpdate(is_active=active),
                )
            else:
                response = await ConversationService(
                    session=session, owner_id=schema_graph.owner
                ).update(
                    conversation_id=schema_graph.conversation,
                    update_data=ConversationUpdate(is_active=active),
                )
            assert response.is_active is False
        assert (
            await schema_connection.execute(
                text(f'SELECT is_active FROM public."{table}" WHERE id=:id'),
                {
                    "id": getattr(
                        schema_graph,
                        {
                            "agents": "agent",
                            "channels": "channel",
                            "conversations": "conversation",
                        }[table],
                    )
                },
            )
        ).scalar_one() is False


# ==============================================
# SYNTHETIC OWNER AND REGISTRATION RECORD
# Build a request without restaurants so owner deletion is within the existing service policy.
# ==============================================


async def owner_and_request(
    *, connection: AsyncConnection, status: str, trial_used: bool = True
) -> tuple[int, int]:
    """Create a disposable untagged owner and a linked request with preserved personal fields."""
    owner = await insert_row(
        connection=connection,
        table="owners",
        values={
            "chat_id": 99188004,
            "registration_status": "approved",
            "full_name": "Synthetic former owner",
            "phone": "0555000000",
            "trial_used": trial_used,
        },
    )
    request = await insert_row(
        connection=connection,
        table="registration_requests",
        values={
            "chat_id": 99188004,
            "full_name": "Synthetic former owner",
            "owner_phone": "0555000000",
            "restaurant_name": "Synthetic proposed restaurant",
            "restaurant_type": "restaurant",
            "restaurant_phone": "0555000000",
            "status": status,
            "owner_id": owner,
        },
    )
    return owner, request


# ==============================================
# DATABASE SET NULL ACTION
# Prove direct SQL deletion preserves the request independently of ORM relationship handling.
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["pending", "approved"])
async def test_registration_request_survives_direct_owner_delete(
    schema_connection: AsyncConnection, status: str
) -> None:
    """A request survives deletion with NULL owner_id, unchanged status and original form fields."""
    owner, request = await owner_and_request(
        connection=schema_connection, status=status
    )
    await schema_connection.execute(
        text("DELETE FROM owners WHERE id=:id"), {"id": owner}
    )
    row = (
        (
            await schema_connection.execute(
                text(
                    "SELECT owner_id,status,full_name FROM registration_requests WHERE id=:id"
                ),
                {"id": request},
            )
        )
        .mappings()
        .one()
    )
    assert row == {
        "owner_id": None,
        "status": status,
        "full_name": "Synthetic former owner",
    }
    with pytest.raises(IntegrityError) as error:
        async with schema_connection.begin_nested():
            await schema_connection.execute(
                text("UPDATE registration_requests SET owner_id=:owner WHERE id=:id"),
                {"owner": owner, "id": request},
            )
    assert getattr(error.value.orig, "sqlstate", None) == "23503"


# ==============================================
# EXISTING OWNER DELETION AND REGISTRATION READING
# Follow the real ORM service and reject reapproval without granting another trial.
# ==============================================


@pytest.mark.asyncio
async def test_owner_service_delete_preserves_approved_request_and_blocks_reapproval(
    schema_connection: AsyncConnection,
) -> None:
    """Read an orphan request normally and refuse repeated approval without recreating its owner."""
    owner, request = await owner_and_request(
        connection=schema_connection, status="approved"
    )
    async with AsyncSession(
        bind=schema_connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    ) as session:
        await OwnerService(session=session).delete_owner(owner_id=owner)
        registration = RegistrationRequestService(session)
        result = await registration.get_by_id(request_id=request)
        assert result.owner_id is None and result.status == "approved"
        result_by_chat = await registration.get_by_chat_id(chat_id=99188004)
        assert result_by_chat is not None and result_by_chat.owner_id is None
        with pytest.raises(ValidationError):
            await registration.approve(request_id=request)
    assert (
        await schema_connection.execute(
            text("SELECT count(*) FROM owners WHERE chat_id=99188004")
        )
    ).scalar_one() == 0
    assert (
        await schema_connection.execute(text("SELECT count(*) FROM subscriptions"))
    ).scalar_one() == 0


# ==============================================
# BUSINESS DELETION GUARD
# Keep restaurant ownership restrictions independent of the nullable registration reference.
# ==============================================


@pytest.mark.asyncio
async def test_owner_with_restaurant_cannot_be_deleted(
    schema_connection: AsyncConnection, schema_graph: Graph
) -> None:
    """SET NULL on registration does not relax the existing restaurant deletion precondition."""
    async with AsyncSession(
        bind=schema_connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    ) as session:
        with pytest.raises(ValidationError):
            await OwnerService(session=session).delete_owner(
                owner_id=schema_graph.owner
            )
    assert (
        await schema_connection.execute(
            text("SELECT count(*) FROM owners WHERE id=:id"), {"id": schema_graph.owner}
        )
    ).scalar_one() == 1


# ==============================================
# EXISTING CHAT ID UNIQUENESS
# Check duplicates are rejected and multiple NULL chat IDs retain their previous semantics.
# ==============================================


@pytest.mark.asyncio
async def test_user_chat_unique_constraint_preserves_null_semantics(
    schema_connection: AsyncConnection,
) -> None:
    """The extra constraint does not invent a new rule beyond the existing unique index."""
    await insert_row(
        connection=schema_connection, table="users", values={"chat_id": 99188005}
    )
    with pytest.raises(IntegrityError) as error:
        async with schema_connection.begin_nested():
            await insert_row(
                connection=schema_connection,
                table="users",
                values={"chat_id": 99188005},
            )
    assert getattr(error.value.orig, "sqlstate", None) == "23505"
    for _ in range(2):
        await insert_row(
            connection=schema_connection, table="users", values={"chat_id": None}
        )


# ==============================================
# EXISTING SESSION TOKEN UNIQUENESS
# Verify that replacing a unique index with a named UNIQUE constraint remains global.
# ==============================================


@pytest.mark.asyncio
async def test_admin_session_token_remains_globally_unique(
    schema_connection: AsyncConnection, schema_graph: Graph
) -> None:
    """A session token cannot be reused even for a different administrator."""
    other = await insert_row(
        connection=schema_connection,
        table="admins",
        values={"chat_id": 99188006, "role": "support"},
    )
    payload: dict[str, SqlScalar] = {
        "admin_id": schema_graph.admin,
        "session_token": "synthetic-unique-token",
        "expires_at": datetime(2030, 1, 1, tzinfo=timezone.utc).replace(tzinfo=None),
    }
    await insert_row(
        connection=schema_connection, table="admin_sessions", values=payload
    )
    with pytest.raises(IntegrityError) as error:
        async with schema_connection.begin_nested():
            await insert_row(
                connection=schema_connection,
                table="admin_sessions",
                values={**payload, "admin_id": other},
            )
    assert getattr(error.value.orig, "sqlstate", None) == "23505"


# ==============================================
# EXISTING PARTIAL SUBSCRIPTION UNIQUENESS
# Retain one trial/active row per restaurant while allowing historical inactive rows.
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("initial", ["trial", "active"])
async def test_active_subscription_index_preserves_eligible_set(
    schema_connection: AsyncConnection, schema_graph: Graph, initial: str
) -> None:
    """Both active states participate in uniqueness; expired history remains admissible."""
    plan = await insert_row(
        connection=schema_connection,
        table="subscription_plans",
        values={
            "code": "synthetic-schema-only",
            "name": "Synthetic schema fixture",
            "base_price": 0,
            "plan_discount_percent": 0,
        },
    )
    payload: dict[str, SqlScalar] = {
        "owner_id": schema_graph.owner,
        "restaurant_id": schema_graph.restaurant,
        "plan_id": plan,
        "billing_cycle": "monthly",
        "amount": Decimal("1.00"),
        "status": initial,
    }
    await insert_row(
        connection=schema_connection, table="subscriptions", values=payload
    )
    with pytest.raises(IntegrityError) as error:
        async with schema_connection.begin_nested():
            await insert_row(
                connection=schema_connection,
                table="subscriptions",
                values={
                    **payload,
                    "status": "active" if initial == "trial" else "trial",
                },
            )
    assert getattr(error.value.orig, "sqlstate", None) == "23505"
    for _ in range(2):
        await insert_row(
            connection=schema_connection,
            table="subscriptions",
            values={**payload, "status": "expired"},
        )


# ==============================================
# PENDING ORPHAN WITH EXPLICIT SYNTHETIC TRIAL CONFIGURATION
# Exercise approval and one trial without inventing or persisting paid feature prices.
# ==============================================


@pytest.mark.asyncio
async def test_pending_orphan_can_complete_configured_trial_approval(
    schema_connection: AsyncConnection,
) -> None:
    """A pending request can relink through the existing approval service with trial prerequisites."""
    old_owner, request = await owner_and_request(
        connection=schema_connection, status="pending", trial_used=False
    )
    await schema_connection.execute(
        text("DELETE FROM owners WHERE id=:id"), {"id": old_owner}
    )
    await insert_row(
        connection=schema_connection,
        table="subscription_plans",
        values={
            "code": "trial",
            "name": "Synthetic trial only",
            "base_price": 0,
            "plan_discount_percent": 0,
            "active": True,
        },
    )
    for code in sorted(INCLUDED["trial"]):
        await insert_row(
            connection=schema_connection,
            table="features",
            values={"code": code, "name": "Synthetic " + code},
        )
    async with AsyncSession(
        bind=schema_connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    ) as session:
        service = RegistrationRequestService(session)
        response = await service.approve(request_id=request)
        assert (
            response.status == "approved"
            and response.owner_id is not None
            and response.owner_id != old_owner
        )
        with pytest.raises(ValidationError):
            await service.approve(request_id=request)
    trials = (
        (
            await schema_connection.execute(
                text("SELECT status,amount FROM subscriptions")
            )
        )
        .mappings()
        .all()
    )
    assert trials == [{"status": "trial", "amount": Decimal(0)}]
    assert (
        await schema_connection.execute(text("SELECT count(*) FROM feature_pricing"))
    ).scalar_one() == 0


# ==============================================
# MISSING TRIAL CONFIGURATION CHARACTERIZATION
# Reject missing trial configuration without persisting an intermediate profile.
# ==============================================


@pytest.mark.asyncio
async def test_missing_trial_plan_leaves_no_partial_progress(
    schema_connection: AsyncConnection,
) -> None:
    """Verify configuration failure leaves no owner, restaurant or subscription behind."""
    old_owner, request = await owner_and_request(
        connection=schema_connection, status="pending", trial_used=False
    )
    await schema_connection.execute(
        text("DELETE FROM owners WHERE id=:id"), {"id": old_owner}
    )
    # Compare complete persisted rows, including unrelated synthetic data left
    # by earlier suites; an empty database is not a prerequisite for approval.
    before = {
        table: await schema_connection.scalar(
            text(
                f"SELECT coalesce(jsonb_agg(to_jsonb(t) ORDER BY t.id), '[]'::jsonb) "
                f'FROM public."{table}" AS t'
            )
        )
        for table in ("owners", "restaurants", "subscriptions")
    }
    async with AsyncSession(
        bind=schema_connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    ) as session:
        with pytest.raises(ValueError, match="trial_plan_not_found"):
            await RegistrationRequestService(session).approve(request_id=request)
    row = (
        (
            await schema_connection.execute(
                text("SELECT status,owner_id FROM registration_requests WHERE id=:id"),
                {"id": request},
            )
        )
        .mappings()
        .one()
    )
    counts = {
        table: int(
            (
                await schema_connection.execute(
                    text(f'SELECT count(*) FROM public."{table}"')
                )
            ).scalar_one()
        )
        for table in ("owners", "restaurants", "subscriptions")
    }
    after = {
        table: await schema_connection.scalar(
            text(
                f"SELECT coalesce(jsonb_agg(to_jsonb(t) ORDER BY t.id), '[]'::jsonb) "
                f'FROM public."{table}" AS t'
            )
        )
        for table in before
    }
    configuration = LocalPostgresSettings()
    output = (
        Path(__file__).resolve().parents[1]
        / "artifacts/postgres-local-tests"
        / configuration.INSTANCE_ID
    )
    observed = {
        "exception": "trial_plan_not_found",
        "request": dict(row),
        "rows_after_error_within_isolated_probe": counts,
        "preexisting_rows_unchanged": after == before,
        "writes_confined_to_outer_test_transaction": True,
        "remote_operations": 0,
    }
    (output / "registration-missing-config.json").write_text(
        json.dumps(observed, indent=2) + "\n", encoding="utf-8"
    )
    assert row == {"status": "pending", "owner_id": None}
    assert after == before
