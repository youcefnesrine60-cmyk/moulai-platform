# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Execute owner-isolated agent HTTP operations against private in-memory SQL.

The real routers, services, repositories, ORM session, and tenant hooks run here.
SQLite verifies predicates and persistence; PostgreSQL locking is outside scope.
Only identity verification is substituted, using an explicit authenticated owner.
"""

# ==============================================
# IMPORTS
# ==============================================

from collections.abc import (
    AsyncIterator,
    Iterator,
    Mapping,
)
from dataclasses import dataclass
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import (
    ASGITransport,
    AsyncClient,
    Response,
)
from sqlalchemy import (
    create_engine,
    event,
    func,
    select,
)
from sqlalchemy.engine import (
    Engine,
    Result,
)
from sqlalchemy.dialects.postgresql import dialect as postgresql_dialect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import (
    ORMExecuteState,
    Session,
    noload,
)
from sqlalchemy.sql import Executable
from sqlalchemy.util.concurrency import greenlet_spawn

from app.api.auth import (
    OwnerPrincipal,
    get_current_owner,
)
from app.api.v1.agent import (
    agent,
    channel,
    conversation,
    message,
)
from app.core.database import get_db
from app.models.agent import (
    CONVERSATION_STATUS_KEY,
    MESSAGE_CONTENT_TYPE_KEY,
    Agent,
    Channel,
    Conversation,
    Message,
)
from app.models.base import Base
from app.models.owner import Owner
from app.models.restaurant import Restaurant

# ==============================================
# PRIVATE DATABASE AND REAL ASGI APPLICATION
# ==============================================


class InMemoryAsyncSession(AsyncSession):
    """Expose real SQLite ORM results through the application's async boundary.

    SQLite uses a synchronous DBAPI here. Bypass AsyncSession's async-driver
    cursor cleanup while retaining its real sync session, transaction, flush,
    and SQLAlchemy security events. This adapter never replaces SQL or rows.
    """

    async def execute(
        self,
        statement: Executable,
        params: Any = None,
        *,
        execution_options: Mapping[str, Any] | None = None,
        bind_arguments: dict[str, Any] | None = None,
        **options: Any,
    ) -> Result[Any]:
        """Execute and buffer the actual local statement without an async DBAPI."""
        return await greenlet_spawn(
            self.sync_session.execute,
            statement,
            params=params,
            execution_options=execution_options or {},
            bind_arguments=bind_arguments,
            **options,
        )


@dataclass
class TenantHarness:
    """Keep a test-owned SQL engine and selectable verified owner principal."""

    app: FastAPI
    engine: Engine
    owner_id: int = 1

    async def request(
        self,
        *,
        method: str,
        path: str,
        parameters: dict[str, Any] | None = None,
        body: Any = None,
    ) -> Response:
        """Exercise the real HTTP stack without network or application startup."""
        async with AsyncClient(
            transport=ASGITransport(app=self.app),
            base_url="https://tenant.local.test",
        ) as client:
            return await client.request(
                method,
                "/api/v1" + path,
                params=parameters,
                json=body,
            )

    def scalar(self, *, statement: Any) -> Any:
        """Inspect committed SQL through the fixture's private connection only."""
        with self.engine.connect() as connection:
            return connection.execute(statement).scalar_one()


@pytest.fixture
def sql_harness() -> Iterator[TenantHarness]:
    """Seed three agent trees belonging to two independent owner identities."""
    engine = create_engine("sqlite+pysqlite:///:memory:")
    models = (Owner, Restaurant, Agent, Channel, Conversation, Message)
    Base.metadata.create_all(engine, tables=[model.__table__ for model in models])
    with engine.begin() as connection:
        connection.execute(
            Owner.__table__.insert(),
            [
                {"id": 1, "chat_id": 101, "auth_subject": "owner-one"},
                {"id": 2, "chat_id": 202, "auth_subject": "owner-two"},
            ],
        )
        connection.execute(
            Restaurant.__table__.insert(),
            [
                {
                    "id": restaurant_id,
                    "owner_id": owner_id,
                    "name": f"Restaurant {restaurant_id}",
                    "type": "restaurant",
                    "phone": "local-test",
                    "wilaya": "Test",
                }
                for restaurant_id, owner_id in ((31, 1), (32, 1), (41, 2))
            ],
        )
        connection.execute(
            Agent.__table__.insert(),
            [
                {
                    "id": agent_id,
                    "restaurant_id": restaurant_id,
                    "name": f"Assistant {agent_id}",
                }
                for agent_id, restaurant_id in ((7, 31), (8, 32), (17, 41))
            ],
        )
        connection.execute(
            Channel.__table__.insert(),
            [
                {
                    "id": channel_id,
                    "agent_id": agent_id,
                    "type": "telegram",
                    "name": f"Orders {channel_id}",
                }
                for channel_id, agent_id in ((9, 7), (10, 8), (19, 17))
            ],
        )
        connection.execute(
            Conversation.__table__.insert(),
            [
                {
                    "id": conversation_id,
                    "agent_id": agent_id,
                    "channel_id": channel_id,
                    "user_id": "customer-search",
                    "user_name": "Customer search",
                }
                for conversation_id, agent_id, channel_id in (
                    (11, 7, 9),
                    (12, 8, 10),
                    (21, 17, 19),
                )
            ],
        )
        connection.execute(
            Message.__table__.insert(),
            [
                {
                    "id": message_id,
                    "conversation_id": conversation_id,
                    "role": "user",
                    "content": f"A table for message {message_id}",
                }
                for message_id, conversation_id in ((13, 11), (14, 12), (23, 21))
            ],
        )

    app = FastAPI()
    for module in (agent, channel, conversation, message):
        app.include_router(module.router, prefix="/api/v1")
    harness = TenantHarness(app=app, engine=engine)

    def local_session(**options: Any) -> Session:
        """Give AsyncSession a real synchronous SQLite session via greenlets."""
        options.pop("bind", None)
        options.pop("binds", None)
        session = Session(bind=engine, **options)

        def limit_fixture_relationships(state: ORMExecuteState) -> None:
            """Avoid querying unrelated application tables outside this fixture."""
            if state.is_select:
                state.statement = state.statement.options(noload("*"))

        event.listen(session, "do_orm_execute", limit_fixture_relationships)
        return session

    async def database_boundary() -> AsyncIterator[AsyncSession]:
        """Preserve real session hooks while forbidding external DB creation."""
        async with InMemoryAsyncSession(
            sync_session_class=local_session,
            expire_on_commit=False,
        ) as session:
            yield session

    async def owner_boundary() -> OwnerPrincipal:
        """Represent an identity that already passed central Keycloak checks."""
        return OwnerPrincipal(owner_id=harness.owner_id)

    app.dependency_overrides[get_db] = database_boundary
    app.dependency_overrides[get_current_owner] = owner_boundary
    try:
        yield harness
    finally:
        engine.dispose()


# ==============================================
# OWNER-SCOPED READS, SEARCH, AND COUNTS
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "parameters", "owner_one_ids", "owner_two_ids"),
    [
        ("/agents/search", {"query": "Assistant"}, {7, 8}, {17}),
        ("/agents/status", {}, {7, 8}, {17}),
        ("/channels/search", {"query": "Orders"}, {9, 10}, {19}),
        ("/conversations/search", {"query": "search"}, {11, 12}, {21}),
        ("/messages/search", {"query": "table"}, {13, 14}, {23}),
    ],
)
async def test_global_search_and_totals_include_only_authenticated_owner(
    *,
    sql_harness: TenantHarness,
    path: str,
    parameters: dict[str, Any],
    owner_one_ids: set[int],
    owner_two_ids: set[int],
) -> None:
    """Global filters and aggregate counts must enforce the same tenant scope."""
    for owner_id, expected_ids in ((1, owner_one_ids), (2, owner_two_ids)):
        sql_harness.owner_id = owner_id
        response = await sql_harness.request(
            method="GET", path=path, parameters=parameters
        )
        assert response.status_code == 200, response.text
        assert {item["id"] for item in response.json()["items"]} == expected_ids
        assert response.json()["total"] == len(expected_ids)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        "/agents/17",
        "/agents/17/with-channels",
        "/channels/19",
        "/conversations/21",
        "/conversations/21/with-messages",
        "/messages/23",
    ],
)
async def test_foreign_record_identifiers_are_hidden(
    *, sql_harness: TenantHarness, path: str
) -> None:
    """A foreign primary key must not expose records or their eager children."""
    response = await sql_harness.request(method="GET", path=path)
    assert response.status_code == 404, response.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "parameters"),
    [
        ("/agents/search", {"query": "Assistant", "restaurant_id": 41}),
        ("/channels/search", {"query": "Orders", "agent_id": 17}),
        ("/conversations/search", {"query": "search", "agent_id": 17}),
        ("/messages/search", {"query": "table", "conversation_id": 21}),
    ],
)
async def test_foreign_parent_search_filter_cannot_expand_scope(
    *,
    sql_harness: TenantHarness,
    path: str,
    parameters: dict[str, Any],
) -> None:
    """Caller-selected filters can only reduce the authenticated owner's rows."""
    response = await sql_harness.request(method="GET", path=path, parameters=parameters)
    assert response.status_code == 200, response.text
    assert response.json()["items"] == []
    assert response.json()["total"] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        "/channels/statistics/17",
        "/conversations/statistics/17",
        "/messages/statistics/21",
    ],
)
async def test_statistics_cannot_reveal_foreign_parent_counts(
    *, sql_harness: TenantHarness, path: str
) -> None:
    """An aggregate endpoint cannot bypass ownership through its parent ID."""
    response = await sql_harness.request(method="GET", path=path)
    assert response.status_code == 404, response.text


@pytest.mark.asyncio
async def test_restaurant_statistics_do_not_count_foreign_agents(
    *, sql_harness: TenantHarness
) -> None:
    """The restaurant aggregate must apply owner scope to count and detail queries."""
    response = await sql_harness.request(method="GET", path="/agents/statistics/41")
    assert response.status_code == 200, response.text
    assert response.json()["total_agents"] == 0
    assert response.json()["active_agents"] == 0
    assert response.json()["inactive_agents"] == 0
    assert response.json()["language_distribution"] == {}


# ==============================================
# MUTATIONS AND PARENT CONSISTENCY
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("PATCH", "/agents/17", {"name": "Foreign update"}),
        ("PATCH", "/channels/19", {"name": "Foreign update"}),
        ("PATCH", "/conversations/21", {"status": "closed"}),
        ("PATCH", "/messages/23", {"content": "Foreign update"}),
        ("DELETE", "/agents/17", None),
        ("DELETE", "/channels/19", None),
        ("DELETE", "/conversations/21", None),
        ("DELETE", "/messages/23", None),
        ("DELETE", "/messages/conversation/21", None),
        ("DELETE", "/channels/agent/17", None),
    ],
)
async def test_foreign_mutation_is_rejected_without_changing_rows(
    *,
    sql_harness: TenantHarness,
    method: str,
    path: str,
    body: Any,
) -> None:
    """Get/update/delete and destructive child operations cannot cross owners."""
    response = await sql_harness.request(method=method, path=path, body=body)
    assert response.status_code == 404, response.text
    assert (
        sql_harness.scalar(statement=select(Agent.name).where(Agent.id == 17))
        == "Assistant 17"
    )
    assert (
        sql_harness.scalar(statement=select(Channel.name).where(Channel.id == 19))
        == "Orders 19"
    )
    assert (
        sql_harness.scalar(
            statement=select(Conversation.is_active).where(Conversation.id == 21)
        )
        is True
    )
    assert (
        sql_harness.scalar(statement=select(Message.content).where(Message.id == 23))
        == "A table for message 23"
    )


@pytest.mark.asyncio
async def test_bulk_status_update_filters_foreign_agent_ids(
    *, sql_harness: TenantHarness
) -> None:
    """A mixed bulk request changes only owned rows and reports their exact count."""
    response = await sql_harness.request(
        method="PATCH",
        path="/agents/bulk/toggle-status",
        parameters={"agent_ids": [7, 17], "is_active": False},
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"updated_count": 1, "is_active": False}
    assert (
        sql_harness.scalar(statement=select(Agent.is_active).where(Agent.id == 7))
        is False
    )
    assert (
        sql_harness.scalar(statement=select(Agent.is_active).where(Agent.id == 17))
        is True
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "body"),
    [
        ("/agents/", {"restaurant_id": 41, "name": "Unauthorized assistant"}),
        ("/channels/", {"agent_id": 17, "type": "web", "name": "Unauthorized"}),
        (
            "/conversations/",
            {"agent_id": 17, "channel_id": 19, "user_id": "new-user"},
        ),
        (
            "/messages/",
            {"conversation_id": 21, "role": "user", "content": "Unauthorized"},
        ),
    ],
)
async def test_create_cannot_attach_rows_to_a_foreign_parent(
    *,
    sql_harness: TenantHarness,
    path: str,
    body: dict[str, Any],
) -> None:
    """Creating a child cannot transfer ownership through a supplied parent ID."""
    response = await sql_harness.request(method="POST", path=path, body=body)
    assert response.status_code == 404, response.text


@pytest.mark.asyncio
async def test_owned_but_mismatched_conversation_channel_is_rejected(
    *, sql_harness: TenantHarness
) -> None:
    """Even within one owner, a conversation cannot reference another agent's channel."""
    response = await sql_harness.request(
        method="POST",
        path="/conversations/",
        body={"agent_id": 7, "channel_id": 10, "user_id": "new-user"},
    )
    assert response.status_code == 422, response.text
    assert response.json()["detail"] == "Channel does not belong to the selected agent"


@pytest.mark.asyncio
async def test_owned_mutation_and_creation_remain_available(
    *, sql_harness: TenantHarness
) -> None:
    """The protection must retain authorized functionality through actual persistence."""
    response = await sql_harness.request(
        method="PATCH", path="/agents/7", body={"name": "Updated assistant"}
    )
    assert response.status_code == 200, response.text
    assert response.json()["name"] == "Updated assistant"
    response = await sql_harness.request(
        method="POST",
        path="/messages/",
        body={"conversation_id": 11, "role": "user", "content": "Owned message"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["conversation_id"] == 11
    assert (
        sql_harness.scalar(
            statement=select(Message.content).where(Message.id == response.json()["id"])
        )
        == "Owned message"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("new_status", ["closed", "suspended"])
async def test_conversation_state_roundtrips_queries_and_survives_context_updates(
    *, sql_harness: TenantHarness, new_status: str
) -> None:
    """Persist state without DDL and keep status, activity, queries, and writes aligned."""
    response = await sql_harness.request(
        method="PATCH",
        path="/conversations/11/status",
        parameters={"status": new_status},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == new_status
    assert response.json()["is_active"] is False
    assert (
        sql_harness.scalar(
            statement=select(Conversation.status).where(Conversation.id == 11)
        )
        == new_status
    )
    response = await sql_harness.request(
        method="GET",
        path=f"/conversations/status/{new_status}",
        parameters={"agent_id": 7},
    )
    assert response.status_code == 200, response.text
    assert [item["id"] for item in response.json()["items"]] == [11]
    assert response.json()["total"] == 1
    response = await sql_harness.request(
        method="GET", path="/conversations/statistics/7"
    )
    assert response.status_code == 200, response.text
    assert response.json()["status_summary"] == [{"status": new_status, "count": 1}]
    response = await sql_harness.request(
        method="PATCH",
        path="/conversations/11/context",
        body={CONVERSATION_STATUS_KEY: "active", "order_id": 91},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == new_status
    response = await sql_harness.request(
        method="GET", path="/conversations/11", parameters={"include_inactive": True}
    )
    assert response.status_code == 200, response.text
    assert response.json()["context"]["order_id"] == 91
    assert response.json()["status"] == new_status
    response = await sql_harness.request(
        method="POST",
        path="/messages/",
        body={"conversation_id": 11, "role": "user", "content": "Blocked"},
    )
    assert response.status_code == 422, response.text
    response = await sql_harness.request(
        method="PATCH", path="/conversations/11/toggle-status"
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "active"
    assert response.json()["is_active"] is True


@pytest.mark.asyncio
async def test_message_media_type_roundtrips_and_survives_metadata_replacement(
    *, sql_harness: TenantHarness
) -> None:
    """Persist non-text media, preserve it on update, and filter its real SQL value."""
    response = await sql_harness.request(
        method="POST",
        path="/messages/",
        body={
            "conversation_id": 11,
            "role": "user",
            "content": "Photo attachment",
            "content_type": "image",
            "meta_data": {"language": "en", MESSAGE_CONTENT_TYPE_KEY: "file"},
        },
    )
    assert response.status_code == 201, response.text
    message_id = response.json()["id"]
    assert response.json()["content_type"] == "image"
    assert response.json()["meta_data"]["language"] == "en"
    response = await sql_harness.request(
        method="PATCH",
        path=f"/messages/{message_id}",
        body={
            "meta_data": {"note": "Retained image", MESSAGE_CONTENT_TYPE_KEY: "file"}
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["content_type"] == "image"
    response = await sql_harness.request(
        method="GET", path="/messages/conversation/11/type/image"
    )
    assert response.status_code == 200, response.text
    assert [item["id"] for item in response.json()["items"]] == [message_id]
    assert response.json()["total"] == 1
    assert (
        sql_harness.scalar(
            statement=select(Message.content_type).where(Message.id == message_id)
        )
        == "image"
    )
    assert (
        sql_harness.scalar(
            statement=select(Message.content_type).where(Message.id == 13)
        )
        == "text"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("state", "activity", "expected_status"),
    [("suspended", True, 422), ("active", False, 422), ("suspended", False, 200)],
)
async def test_explicit_activity_cannot_contradict_conversation_state(
    *, sql_harness: TenantHarness, state: str, activity: bool, expected_status: int
) -> None:
    """Reject contradictions and retain a suspended state with matching activity."""
    response = await sql_harness.request(
        method="PATCH",
        path="/conversations/11",
        body={"status": state, "is_active": activity},
    )
    assert response.status_code == expected_status, response.text
    if expected_status == 200:
        assert response.json()["status"] == state
        assert response.json()["is_active"] is activity
    else:
        assert (
            sql_harness.scalar(
                statement=select(Conversation.status).where(Conversation.id == 11)
            )
            == "active"
        )


@pytest.mark.asyncio
async def test_bulk_messages_cannot_bypass_inactive_conversation_restriction(
    *, sql_harness: TenantHarness
) -> None:
    """Bulk creation must obey the same state restriction as single creation."""
    response = await sql_harness.request(
        method="PATCH", path="/conversations/11/status", parameters={"status": "closed"}
    )
    assert response.status_code == 200, response.text
    response = await sql_harness.request(
        method="POST",
        path="/messages/bulk",
        parameters={"conversation_id": 11},
        body=[{"role": "user", "content": "Blocked bulk message"}],
    )
    assert response.status_code == 422, response.text
    assert sql_harness.scalar(statement=select(func.count()).select_from(Message)) == 3


@pytest.mark.asyncio
async def test_invalid_bulk_message_does_not_partially_persist_valid_predecessors(
    *, sql_harness: TenantHarness
) -> None:
    """Validate the entire batch before the repository performs its first write."""
    response = await sql_harness.request(
        method="POST",
        path="/messages/bulk",
        parameters={"conversation_id": 11},
        body=[
            {"role": "user", "content": "Must not be saved"},
            {"role": "user", "content": "Invalid type", "content_type": "binary"},
        ],
    )
    assert response.status_code == 422, response.text
    assert sql_harness.scalar(statement=select(func.count()).select_from(Message)) == 3


@pytest.mark.asyncio
async def test_bulk_media_messages_use_only_the_authorized_parent(
    *, sql_harness: TenantHarness
) -> None:
    """Supplied row IDs and foreign parents cannot escape the validated batch parent."""
    response = await sql_harness.request(
        method="POST",
        path="/messages/bulk",
        parameters={"conversation_id": 11},
        body=[
            {"id": 23, "conversation_id": 21, "role": "user", "content": "Owned text"},
            {"role": "user", "content": "Owned image", "content_type": "image"},
        ],
    )
    assert response.status_code == 201, response.text
    assert len(response.json()) == 2
    assert {item["conversation_id"] for item in response.json()} == {11}
    assert {item["content_type"] for item in response.json()} == {"text", "image"}
    assert 23 not in {item["id"] for item in response.json()}
    assert (
        sql_harness.scalar(statement=select(Message.content).where(Message.id == 23))
        == "A table for message 23"
    )


@pytest.mark.parametrize(
    ("expression", "table_name", "reserved_key"),
    [
        (Conversation.status, "conversations", CONVERSATION_STATUS_KEY),
        (Message.content_type, "messages", MESSAGE_CONTENT_TYPE_KEY),
    ],
)
def test_persisted_state_expressions_compile_for_postgresql(
    *, expression: Any, table_name: str, reserved_key: str
) -> None:
    """Compile the actual mapped SQL expressions without connecting to PostgreSQL."""
    compiled = select(expression).compile(dialect=postgresql_dialect())
    assert "CASE" in str(compiled)
    assert "->>" in str(compiled)
    assert table_name in str(compiled)
    assert reserved_key in compiled.params.values()
