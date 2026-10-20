# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Verify owner predicates and write boundaries using real disposable SQL.

These tests use local SQLite only; they do not validate asyncpg or PostgreSQL
locking. Fixture setup is trusted and unscoped. Every operation under test
uses the production session guard and real SQLAlchemy statements.
"""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi import HTTPException
from greenlet import getcurrent
from sqlalchemy import (
    create_engine,
    delete,
    event,
    func,
    insert,
    select,
    text,
    update,
)
from sqlalchemy.orm import (
    Session,
    aliased,
    raiseload,
)
from sqlalchemy.exc import MissingGreenlet
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.tenant_scope import (
    TenantModel,
    bind_owner_scope,
)
from app.models.agent import (
    Agent,
    Channel,
    Conversation,
    Message,
)
from app.models.base import Base
from app.models.branch import Branch
from app.models.category import Category
from app.models.option_group import OptionGroup
from app.models.owner import Owner
from app.models.product import Product
from app.models.product_option import ProductOption
from app.models.restaurant import Restaurant
from app.services.business.branch_service import BranchService

MODEL_DATA: dict[TenantModel, dict[str, Any]] = {
    Restaurant: {
        "owner_id": 1,
        "name": "Restaurant",
        "type": "cafe",
        "phone": "fixture",
        "wilaya": "Test",
    },
    Category: {"restaurant_id": 1, "name": "Lunch"},
    Product: {"restaurant_id": 1, "category_id": 1, "name": "Soup", "price": 450},
    OptionGroup: {"product_id": 1, "name": "Extras"},
    ProductOption: {"group_id": 1, "name": "Cheese", "extra_price": 50},
    Agent: {"restaurant_id": 1, "name": "Assistant"},
    Channel: {"agent_id": 1, "type": "telegram", "name": "Orders"},
    Conversation: {"agent_id": 1, "channel_id": 1, "user_id": "customer"},
    Message: {"conversation_id": 1, "role": "user", "content": "Lunch"},
    Branch: {"restaurant_id": 1, "name": "Downtown"},
}


# ==============================================
# ISOLATED TWO-OWNER DATABASE
# ==============================================


@pytest.fixture
def tenant_session() -> Iterator[Session]:
    """Create a separate private database for every security assertion."""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(
            Owner.__table__.insert(),
            [{"id": 1, "chat_id": 101}, {"id": 2, "chat_id": 202}],
        )
        for model, payload in MODEL_DATA.items():
            for identifier in (1, 2):
                values = {
                    key: identifier if key.endswith("_id") else value
                    for key, value in payload.items()
                }
                if model is Conversation:
                    values["user_id"] = "customer"
                connection.execute(
                    model.__table__.insert().values(id=identifier, **values)
                )
    with Session(engine, expire_on_commit=False) as session:
        writes: list[str] = []
        session.info["observed_write_verbs"] = writes

        @event.listens_for(engine, "before_cursor_execute")
        def record_write(
            connection: Any,
            cursor: Any,
            statement: str,
            parameters: Any,
            context: Any,
            executemany: bool,
        ) -> None:
            """Record mutation types without collecting SQL parameters."""
            verb = statement.lstrip().split(" ", 1)[0].upper()
            if verb in {"INSERT", "UPDATE", "DELETE"}:
                writes.append(verb)

        yield session
    engine.dispose()


# ==============================================
# READS, AGGREGATES, ALIASES AND OWNER SEPARATION
# ==============================================


@pytest.mark.parametrize("model", MODEL_DATA)
def test_select_count_and_aliases_exclude_other_owner(
    tenant_session: Session,
    model: TenantModel,
) -> None:
    """Owner criteria cover scalar, aggregate, aliased and entity selects."""
    bind_owner_scope(session=tenant_session, owner_id=1)
    assert tenant_session.scalars(select(model.id)).all() == [1]
    assert tenant_session.scalar(select(func.count()).select_from(model)) == 1
    assert (
        tenant_session.scalar(
            select(func.count()).select_from(model).where(model.id.in_([1, 2]))
        )
        == 1
    )
    assert (
        tenant_session.scalar(
            select(func.count()).select_from(model).where(model.id == 2)
        )
        == 0
    )
    alias = aliased(model)
    assert tenant_session.scalars(select(alias.id)).all() == [1]
    assert tenant_session.scalar(select(model.id).where(model.id == 2)) is None


def test_sessions_keep_independent_bound_owner_values(tenant_session: Session) -> None:
    """Statement caching cannot reuse one owner's predicate for another owner."""
    bind_owner_scope(session=tenant_session, owner_id=1)
    statement = select(Product.id)
    assert tenant_session.scalars(statement).all() == [1]
    with Session(tenant_session.get_bind()) as other:
        bind_owner_scope(session=other, owner_id=2)
        assert other.scalars(statement).all() == [2]
    assert tenant_session.scalars(statement).all() == [1]


def test_binding_does_not_modify_trusted_internal_sessions(
    tenant_session: Session,
) -> None:
    """Explicitly scoped requests do not install global ORM event listeners."""
    bind_owner_scope(session=tenant_session, owner_id=1)
    with Session(tenant_session.get_bind()) as trusted:
        assert trusted.scalars(select(Product.id).order_by(Product.id)).all() == [1, 2]


# ==============================================
# ORM AND BULK MUTATION BOUNDARIES
# ==============================================


@pytest.mark.parametrize("model", MODEL_DATA)
def test_bulk_delete_cannot_delete_foreign_rows(
    tenant_session: Session,
    model: TenantModel,
) -> None:
    """A forged identifier never reaches a foreign row through bulk deletion."""
    bind_owner_scope(session=tenant_session, owner_id=1)
    result = tenant_session.execute(delete(model).where(model.id == 2))
    assert result.rowcount == 0
    with tenant_session.get_bind().connect() as connection:
        assert (
            connection.scalar(
                select(model.__table__.c.id).where(model.__table__.c.id == 2)
            )
            == 2
        )


def test_mixed_bulk_update_modifies_only_owned_records(tenant_session: Session) -> None:
    """Unfiltered or mixed-ID ORM bulk updates inherit the owner predicate."""
    bind_owner_scope(session=tenant_session, owner_id=1)
    tenant_session.execute(
        update(Agent).where(Agent.id.in_([1, 2])).values(is_active=False)
    )
    tenant_session.commit()
    with tenant_session.get_bind().connect() as connection:
        assert connection.execute(
            select(Agent.__table__.c.is_active).order_by(Agent.id)
        ).scalars().all() == [False, True]


@pytest.mark.parametrize("model", MODEL_DATA)
def test_foreign_parent_creation_is_denied_before_any_insert(
    tenant_session: Session,
    model: TenantModel,
) -> None:
    """A forged parent cannot create resources inside another owner's tree."""
    bind_owner_scope(session=tenant_session, owner_id=1)
    values = {
        key: 2 if key.endswith("_id") else value
        for key, value in MODEL_DATA[model].items()
    }
    if model is Conversation:
        values["user_id"] = "customer"
    tenant_session.add(model(**values))
    with pytest.raises(HTTPException) as error:
        tenant_session.flush()
    assert error.value.status_code == 404
    assert tenant_session.info["observed_write_verbs"] == []


def test_mixed_pending_batch_fails_before_first_write(tenant_session: Session) -> None:
    """An invalid late object prevents partial insertion of earlier valid rows."""
    bind_owner_scope(session=tenant_session, owner_id=1)
    tenant_session.add_all(
        [
            Category(restaurant_id=1, name="Valid"),
            Category(restaurant_id=2, name="Foreign"),
        ]
    )
    with pytest.raises(HTTPException):
        tenant_session.flush()
    assert tenant_session.info["observed_write_verbs"] == []


def test_authorized_creation_update_and_delete_persist(tenant_session: Session) -> None:
    """The scope permits a complete legitimate ORM lifecycle."""
    bind_owner_scope(session=tenant_session, owner_id=1)
    category = Category(restaurant_id=1, name="New")
    tenant_session.add(category)
    tenant_session.flush()
    category.name = "Changed"
    tenant_session.commit()
    assert (
        tenant_session.scalar(select(Category.name).where(Category.id == category.id))
        == "Changed"
    )
    tenant_session.delete(category)
    tenant_session.commit()
    assert (
        tenant_session.scalar(select(Category.id).where(Category.id == category.id))
        is None
    )


@pytest.mark.parametrize(
    "operation", ["text", "core-select", "core-update", "bulk-insert", "parent-update"]
)
def test_raw_and_bulk_parent_bypasses_are_rejected(
    tenant_session: Session,
    operation: str,
) -> None:
    """Trusted repository SQL cannot accidentally bypass the request contract."""
    bind_owner_scope(session=tenant_session, owner_id=1)
    statements = {
        "text": text("SELECT id FROM products"),
        "core-select": select(Product.__table__),
        "core-update": Product.__table__.update().values(name="Forbidden"),
        "bulk-insert": insert(Category).values(restaurant_id=2, name="Forbidden"),
        "parent-update": update(Product).values(restaurant_id=2),
    }
    with pytest.raises(HTTPException) as error:
        tenant_session.execute(statements[operation])
    assert error.value.status_code == 403
    assert tenant_session.info["observed_write_verbs"] == []


# ==============================================
# IDENTITY MAP AND SCOPE LIFECYCLE
# ==============================================


@pytest.mark.parametrize("model", MODEL_DATA)
def test_binding_evicts_preloaded_foreign_identity_without_sql(
    tenant_session: Session,
    model: TenantModel,
) -> None:
    """Cached get() cannot expose a row loaded before the owner was verified."""
    foreign = tenant_session.scalar(
        select(model).where(model.id == 2).options(raiseload("*"))
    )
    assert foreign is not None
    statements: list[str] = []

    @event.listens_for(tenant_session.get_bind(), "before_cursor_execute")
    def record_statement(
        connection: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        """Detect implicit reads as well as writes during session binding."""
        statements.append(statement)

    bind_owner_scope(session=tenant_session, owner_id=1)
    assert statements == []
    assert foreign not in tenant_session
    assert tenant_session.get(model, 2, options=[raiseload("*")]) is None
    assert tenant_session.get(model, 1, options=[raiseload("*")]).id == 1
    assert statements


@pytest.mark.asyncio
@pytest.mark.parametrize("expired", [False, True])
async def test_async_service_construction_never_performs_implicit_sql(
    tenant_session: Session,
    expired: bool,
) -> None:
    """Reproduce asyncpg's greenlet requirement over a real local SQL session.

    A real AsyncSession.run_sync supplies SQLAlchemy's greenlet. The local
    cursor hook rejects SQL outside it, just as asyncpg's await_only does.
    This deterministic regression complements the actual PostgreSQL tests.
    """
    session = AsyncSession(sync_session_class=lambda **_: tenant_session)
    restaurant = await session.run_sync(
        lambda current: current.scalar(
            select(Restaurant).where(Restaurant.id == 1).options(raiseload("*"))
        ),
    )
    foreign = await session.run_sync(
        lambda current: current.scalar(
            select(Product).where(Product.id == 2).options(raiseload("*"))
        ),
    )
    if expired:
        session.expire_all()
    statements: list[str] = []

    @event.listens_for(tenant_session.get_bind(), "before_cursor_execute")
    def require_async_greenlet(
        connection: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        """Make constructor I/O fail independently of SQLite's sync tolerance."""
        if not getattr(getcurrent(), "__sqlalchemy_greenlet_provider__", False):
            raise MissingGreenlet("SQL outside AsyncSession greenlet")
        statements.append(statement)

    service = BranchService(session=session, owner_id=1)
    assert service.owner_id == 1
    assert statements == []
    assert restaurant not in tenant_session
    assert foreign not in tenant_session
    assert (
        await session.run_sync(
            lambda current: current.get(Product, 2, options=[raiseload("*")])
        )
        is None
    )
    assert (
        await session.run_sync(
            lambda current: current.scalar(
                select(Restaurant.id).where(Restaurant.id == 1)
            )
        )
        == 1
    )


@pytest.mark.parametrize("pending", ["new", "dirty", "deleted"])
def test_first_binding_preserves_and_rejects_pending_changes(
    tenant_session: Session,
    pending: str,
) -> None:
    """A clean-scope boundary never silently discards an existing unit of work."""
    category = tenant_session.scalar(
        select(Category).where(Category.id == 1).options(raiseload("*"))
    )
    if pending == "new":
        instance = Category(restaurant_id=1, name="Pending")
        tenant_session.add(instance)
    elif pending == "dirty":
        instance = category
        instance.name = "Pending"
    else:
        instance = category
        tenant_session.delete(instance)
    with pytest.raises(HTTPException) as error:
        bind_owner_scope(session=tenant_session, owner_id=1)
    assert error.value.status_code == 403
    assert instance in tenant_session
    assert tenant_session.info["observed_write_verbs"] == []


def test_same_owner_rebinding_preserves_pending_work(tenant_session: Session) -> None:
    """Repeated service construction keeps an already scoped unit of work."""
    bind_owner_scope(session=tenant_session, owner_id=1)
    category = Category(restaurant_id=1, name="Pending")
    tenant_session.add(category)
    bind_owner_scope(session=tenant_session, owner_id=1)
    assert category in tenant_session.new
    tenant_session.flush()
    assert category.id is not None


@pytest.mark.parametrize("owner_id", [0, -1, True, None, "1"])
def test_invalid_owner_cannot_bind(tenant_session: Session, owner_id: Any) -> None:
    """Missing or coerced identity data is never accepted as an owner principal."""
    with pytest.raises(ValueError, match="verified positive"):
        bind_owner_scope(session=tenant_session, owner_id=owner_id)


def test_scope_is_idempotent_and_cannot_be_rebound(tenant_session: Session) -> None:
    """A service may reinforce the scope but cannot silently switch tenants."""
    bind_owner_scope(session=tenant_session, owner_id=1)
    bind_owner_scope(session=tenant_session, owner_id=1)
    with pytest.raises(ValueError, match="cannot be rebound"):
        bind_owner_scope(session=tenant_session, owner_id=2)


def test_reparenting_owned_row_to_foreign_owner_is_rejected(
    tenant_session: Session,
) -> None:
    """Validating original row access alone is insufficient for an ORM update."""
    bind_owner_scope(session=tenant_session, owner_id=1)
    product = tenant_session.scalar(
        select(Product).where(Product.id == 1).options(raiseload("*"))
    )
    product.restaurant_id = 2
    with pytest.raises(HTTPException):
        tenant_session.flush()
    assert tenant_session.info["observed_write_verbs"] == []


def test_relationship_assignment_cannot_bypass_foreign_key_check(
    tenant_session: Session,
) -> None:
    """Relationship synchronization during flush must not move a scoped row."""
    foreign = tenant_session.scalar(
        select(Restaurant).where(Restaurant.id == 2).options(raiseload("*"))
    )
    tenant_session.expunge(foreign)
    bind_owner_scope(session=tenant_session, owner_id=1)
    product = tenant_session.scalar(
        select(Product).where(Product.id == 1).options(raiseload("*"))
    )
    product.restaurant = foreign
    with pytest.raises(HTTPException):
        tenant_session.flush()
    assert tenant_session.info["observed_write_verbs"] == []


def test_mixed_core_and_orm_statement_cannot_read_unscoped_rows(
    tenant_session: Session,
) -> None:
    """Adding an unrelated ORM column cannot disguise an unguarded Core table."""
    bind_owner_scope(session=tenant_session, owner_id=1)
    statement = select(Owner.id, Product.__table__.c.id).where(Owner.id == 1)
    with pytest.raises(HTTPException):
        tenant_session.execute(statement)


def test_core_projection_cannot_borrow_mapping_from_an_orm_predicate(
    tenant_session: Session,
) -> None:
    """An ORM WHERE attribute alone cannot make a raw table owner-scoped."""
    bind_owner_scope(session=tenant_session, owner_id=1)
    statement = select(Owner.id, Product.__table__.c.id).where(Product.id > 0)
    with pytest.raises(HTTPException) as error:
        tenant_session.execute(statement)
    assert error.value.status_code == 403


def test_executemany_primary_key_updates_cannot_bypass_scope(
    tenant_session: Session,
) -> None:
    """Bulk per-primary-key mode must not skip the predicate/flush contract."""
    bind_owner_scope(session=tenant_session, owner_id=1)
    with pytest.raises(HTTPException):
        tenant_session.execute(
            update(Agent), [{"id": 1, "name": "Own"}, {"id": 2, "name": "Foreign"}]
        )
    assert tenant_session.info["observed_write_verbs"] == []


@pytest.mark.parametrize("projection", ["identifier", "count"])
def test_core_alias_cannot_hide_behind_same_mapped_model(
    tenant_session: Session,
    projection: str,
) -> None:
    """A raw alias of a protected table never escapes ORM entity filtering."""
    bind_owner_scope(session=tenant_session, owner_id=1)
    raw_alias = Product.__table__.alias("raw_products")
    statement = (
        select(
            Product.id, raw_alias.c.id if projection == "identifier" else func.count()
        )
        .join(raw_alias, raw_alias.c.id > 0)
        .where(Product.id == 1)
    )
    with pytest.raises(HTTPException) as error:
        tenant_session.execute(statement)
    assert error.value.status_code == 403
