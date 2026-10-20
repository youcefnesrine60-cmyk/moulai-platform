# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Bind owner authorization to a request's SQLAlchemy unit of work.

The listeners are local to one session. Trusted internal bot repositories keep
their existing explicit restaurant contracts. HTTP callers cannot choose the
owner: authentication supplies it before these repositories are constructed.
This is application authorization, not a replacement for database privileges.
"""

from typing import (
    Any,
    TypeAlias,
)

from fastapi import HTTPException
from sqlalchemy import (
    Column,
    and_,
    event,
    inspect,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import (
    ORMExecuteState,
    Session,
    with_loader_criteria,
)
from sqlalchemy.sql import visitors
from sqlalchemy.sql.elements import (
    ColumnElement,
    TextClause,
)

from app.core.logger import logger
from app.models.agent import (
    Agent,
    Channel,
    Conversation,
    Message,
)
from app.models.branch import Branch
from app.models.category import Category
from app.models.option_group import OptionGroup
from app.models.product import Product
from app.models.product_option import ProductOption
from app.models.restaurant import Restaurant

TenantModel: TypeAlias = type[
    Restaurant
    | Category
    | Product
    | OptionGroup
    | ProductOption
    | Agent
    | Channel
    | Conversation
    | Message
    | Branch
]
ScopeCriteria: TypeAlias = dict[TenantModel, ColumnElement[bool]]

_SCOPE_KEY = "moulai_authenticated_owner_scope"
_EXECUTION_KEY = "moulai_owner_scoped_internal_execution"
_PARENT_KEYS = frozenset(
    {
        "id",
        "owner_id",
        "restaurant_id",
        "product_id",
        "group_id",
        "agent_id",
        "channel_id",
        "conversation_id",
        "category_id",
    }
)


# ==============================================
# BASE SELECT AND OWNER CRITERIA
# ==============================================


def _owner_criteria(*, owner_id: int) -> ScopeCriteria:
    """Build bound predicates without sharing cached owner values."""
    restaurants = select(Restaurant.id).where(Restaurant.owner_id == owner_id)
    products = select(Product.id).where(Product.restaurant_id.in_(restaurants))
    groups = select(OptionGroup.id).where(OptionGroup.product_id.in_(products))
    agents = select(Agent.id).where(Agent.restaurant_id.in_(restaurants))
    channels = select(Channel.id).where(Channel.agent_id.in_(agents))
    conversations = select(Conversation.id).where(
        Conversation.agent_id.in_(agents),
        Conversation.channel_id.in_(channels),
    )
    return {
        Restaurant: Restaurant.owner_id == owner_id,
        Category: Category.restaurant_id.in_(restaurants),
        Product: Product.restaurant_id.in_(restaurants),
        OptionGroup: OptionGroup.product_id.in_(products),
        ProductOption: ProductOption.group_id.in_(groups),
        Agent: Agent.restaurant_id.in_(restaurants),
        Channel: Channel.agent_id.in_(agents),
        Conversation: and_(
            Conversation.agent_id.in_(agents),
            Conversation.channel_id.in_(channels),
        ),
        Message: Message.conversation_id.in_(conversations),
        Branch: Branch.restaurant_id.in_(restaurants),
    }


def _deny(*, detail: str = "Resource not found", status_code: int = 404) -> None:
    """Reject a boundary violation without exposing another owner's data."""
    logger.warning("Owner-scoped database operation rejected")
    raise HTTPException(status_code=status_code, detail=detail)


# ==============================================
# SQL EXECUTION GUARD
# ==============================================


def _scope_statement(
    *,
    state: ORMExecuteState,
    criteria: ScopeCriteria,
    execution_token: object,
) -> None:
    """Scope ORM reads and bulk writes; reject unguarded SQL escape routes."""
    if not state.is_orm_statement:
        _deny(
            detail="Raw SQL is unavailable in an owner-scoped session", status_code=403
        )
    # Mixed ORM/Core statements are ORM statements too. A raw protected table
    # or column can otherwise escape with_loader_criteria's entity matching.
    # SQLAlchemy's bulk-write synchronization query uses Core PK columns but
    # inherits the parent's criteria and private per-binding execution marker.
    # External statements cannot manufacture this marker from HTTP input.
    internal_sync = (
        state.execution_options.get(_EXECUTION_KEY) is execution_token
        or state.is_relationship_load
        or state.is_column_load
    )
    nodes = () if internal_sync else tuple(visitors.iterate(state.statement))
    protected_tables = {model.__table__ for model in criteria}
    mapped_tables = set()
    mapped_aliases = set()
    # Session.get() builds its PK predicate from unannotated mapper columns.
    # Permit those columns only when that exact table/alias is represented by
    # an ORM projection or annotated FROM. An ORM attribute appearing solely
    # in WHERE must not legitimize an otherwise unscoped Core projection.
    for node in nodes:
        entities = []
        if getattr(node, "__visit_name__", None) in {"table", "alias"}:
            entity = node._annotations.get("parententity")
            if entity is not None:
                entities.append(entity)
        if getattr(node, "__visit_name__", None) == "select":
            # Traversal can deduplicate an annotated explicit FROM against
            # its unannotated table introduced by a WHERE expression. Keep
            # the explicit ORM provenance before that normalization occurs.
            entities.extend(
                entity
                for from_clause in node._from_obj
                if (entity := from_clause._annotations.get("parententity")) is not None
            )
            entities.extend(
                inspect(description["entity"])
                for description in node.column_descriptions
                if description.get("entity") is not None
            )
        for entity in entities:
            mapper = getattr(entity, "mapper", entity)
            mapped_tables.add(mapper.local_table)
            if getattr(entity, "is_aliased_class", False):
                mapped_aliases.add(entity.selectable)
    for node in nodes:
        table = getattr(node, "table", None)
        while getattr(table, "__visit_name__", None) == "alias":
            table = table.original
        raw_alias = getattr(node, "__visit_name__", None) == "alias" and (
            getattr(node, "original", None) in protected_tables
        )
        if (
            isinstance(node, TextClause)
            or (
                isinstance(node, Column)
                and table in protected_tables
                and "parentmapper" not in node._annotations
                and node.table not in mapped_tables
                and node.table not in mapped_aliases
            )
            or (
                raw_alias
                and "parentmapper" not in node._annotations
                and node not in mapped_aliases
            )
            or (
                getattr(node, "__visit_name__", None) == "table"
                and node in protected_tables
                and node not in mapped_tables
            )
        ):
            _deny(
                detail="Use mapped tenant entities in an owner-scoped session",
                status_code=403,
            )
    if state.is_insert:
        # Inserts must pass the before_flush parent checks, including executemany.
        _deny(
            detail="Use validated ORM creation in an owner-scoped session",
            status_code=403,
        )
    if state.is_update:
        values = getattr(state.statement, "_values", None) or {}
        if any(getattr(key, "key", str(key)) in _PARENT_KEYS for key in values):
            _deny(
                detail="Bulk changes to resource ownership are forbidden",
                status_code=403,
            )
        if isinstance(state.parameters, list):
            _deny(
                detail="Use a scoped set-based update instead of executemany",
                status_code=403,
            )
    if state.is_select or state.is_update or state.is_delete:
        state.statement = state.statement.options(
            *(
                with_loader_criteria(model, predicate, include_aliases=True)
                for model, predicate in criteria.items()
            )
        )
        state.update_execution_options(**{_EXECUTION_KEY: execution_token})


# ==============================================
# FLUSH AND PARENT VALIDATION
# ==============================================


def _require_parent(*, session: Session, model: TenantModel, parent_id: int) -> None:
    """Validate an existing parent through the same owner-scoped base select."""
    if session.scalar(select(model.id).where(model.id == parent_id)) is None:
        _deny()


def _validate_object(*, session: Session, instance: Any, owner_id: int) -> None:
    """Check original ownership and every new parent before emitting SQL writes."""
    model = type(instance)
    state = inspect(instance)
    if state.persistent:
        if state.attrs.id.history.has_changes():
            _deny(detail="Resource identifiers cannot be changed", status_code=403)
        _require_parent(session=session, model=model, parent_id=state.identity[0])
    if instance in session.deleted:
        return
    # API update schemas expose category changes within the same restaurant,
    # but never resource ownership changes. Reject deferred relationship-FK
    # synchronization as well as direct attempts to change immutable parents.
    if state.persistent:
        for key in _PARENT_KEYS.difference({"id", "category_id"}):
            if key in state.attrs and state.attrs[key].history.has_changes():
                _deny(detail="Resource ownership cannot be changed", status_code=403)
    for relationship in state.mapper.relationships:
        if (
            relationship.direction.name == "MANYTOONE"
            and state.attrs[relationship.key].history.has_changes()
        ):
            _deny(
                detail="Use validated parent identifiers for resource relationships",
                status_code=403,
            )
    if isinstance(instance, Restaurant):
        if instance.owner_id != owner_id:
            _deny()
    elif isinstance(instance, (Category, Product, Agent, Branch)):
        _require_parent(
            session=session, model=Restaurant, parent_id=instance.restaurant_id
        )
        if isinstance(instance, Product) and instance.category_id is not None:
            restaurant_id = session.scalar(
                select(Category.restaurant_id).where(
                    Category.id == instance.category_id
                ),
            )
            if restaurant_id is None:
                _deny()
            if restaurant_id != instance.restaurant_id:
                _deny(
                    detail="Category must belong to the product's restaurant",
                    status_code=422,
                )
    elif isinstance(instance, OptionGroup):
        _require_parent(session=session, model=Product, parent_id=instance.product_id)
    elif isinstance(instance, ProductOption):
        _require_parent(session=session, model=OptionGroup, parent_id=instance.group_id)
    elif isinstance(instance, Channel):
        _require_parent(session=session, model=Agent, parent_id=instance.agent_id)
    elif isinstance(instance, Conversation):
        _require_parent(session=session, model=Agent, parent_id=instance.agent_id)
        agent_id = session.scalar(
            select(Channel.agent_id).where(Channel.id == instance.channel_id)
        )
        if agent_id is None:
            _deny()
        if agent_id != instance.agent_id:
            _deny(
                detail="Channel must belong to the conversation's agent",
                status_code=422,
            )
    elif isinstance(instance, Message):
        _require_parent(
            session=session, model=Conversation, parent_id=instance.conversation_id
        )


def _validate_flush(
    *, session: Session, criteria: ScopeCriteria, owner_id: int
) -> None:
    """Validate the complete pending batch before any row is inserted or changed."""
    with session.no_autoflush:
        for instance in set(session.new).union(session.dirty, session.deleted):
            if type(instance) in criteria:
                _validate_object(session=session, instance=instance, owner_id=owner_id)


# ==============================================
# PUBLIC SESSION BINDING
# ==============================================


def bind_owner_scope(*, session: AsyncSession | Session, owner_id: int) -> None:
    """Permanently bind one unit of work to a verified positive owner ID.

    Binding performs no SQL, including when an AsyncSession already contains
    loaded entities. A first binding requires a clean unit of work and evicts
    cached tenant entities so subsequent ORM reads recheck owner predicates.
    Repeated binding to the same owner preserves the current unit of work;
    rebinding to another owner is forbidden. There is no public unbind operation.
    """
    if isinstance(owner_id, bool) or not isinstance(owner_id, int) or owner_id < 1:
        raise ValueError("A verified positive owner ID is required")
    sync_session = (
        session.sync_session if isinstance(session, AsyncSession) else session
    )
    if not isinstance(sync_session, Session):
        raise TypeError("Owner scope requires a real SQLAlchemy session")
    existing_owner = sync_session.info.get(_SCOPE_KEY)
    if existing_owner is not None:
        if existing_owner != owner_id:
            raise ValueError("An owner-scoped session cannot be rebound")
        return
    criteria = _owner_criteria(owner_id=owner_id)
    # Constructor/dependency setup runs outside AsyncSession's greenlet. Never
    # execute synchronous validation SQL here. Cached objects can also bypass
    # SELECT events through Session.get(), so remove their clean identities
    # before installing the boundary. Reject pending changes rather than lose
    # them through relationship-expunge cascades.
    if sync_session.new or sync_session.dirty or sync_session.deleted:
        _deny(
            detail="Bind owner scope before changing the unit of work",
            status_code=403,
        )
    for instance in list(sync_session.identity_map.values()):
        if type(instance) in criteria and inspect(instance).session is sync_session:
            sync_session.expunge(instance)
    execution_token = object()

    def scope_statement(state: ORMExecuteState) -> None:
        """Apply immutable criteria to this session's ORM statements."""
        _scope_statement(
            state=state, criteria=criteria, execution_token=execution_token
        )

    def validate_flush(current: Session, flush_context: Any, instances: Any) -> None:
        """Validate this session's complete pending unit of work."""
        _validate_flush(session=current, criteria=criteria, owner_id=owner_id)

    sync_session.info[_SCOPE_KEY] = owner_id
    event.listen(sync_session, "do_orm_execute", scope_statement)
    event.listen(sync_session, "before_flush", validate_flush)
