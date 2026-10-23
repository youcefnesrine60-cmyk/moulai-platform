# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Catalog HTTP/transaction proofs on the owned disposable loopback PostgreSQL.

No fixture reads DATABASE_URL or TEST_DATABASE_URL. The existing local launcher
provides the independent URL, instance marker and legacy migration profile.
Synthetic rows are retained until that launcher's isolated server is stopped.
"""

from collections.abc import AsyncIterator
from itertools import count
from typing import (
    Annotated,
    Any,
    NamedTuple,
    TypeAlias,
)

import pytest
from fastapi import (
    Depends,
    FastAPI,
)
from sqlalchemy import (
    event,
    func,
    select,
    text,
)
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.api.auth import (
    OwnerPrincipal,
    get_current_owner,
)
from app.core.database import get_db
from app.core.exceptions import ConflictError
from app.models.category import Category
from app.models.option_group import OptionGroup
from app.models.owner import Owner
from app.models.product import Product
from app.models.product_option import ProductOption
from app.models.restaurant import Restaurant
from app.repositories.option_groups_repo import OptionGroupsRepository
from app.repositories.product_option_repo import ProductOptionRepository
from app.schemas.product_option import ProductOptionCreate
from app.services.business.catalog_transaction import catalog_transaction
from app.services.business.product_option_service import ProductOptionService
from test_support.local_postgres import (
    LOCAL_REVISION,
    LocalPostgresSettings,
    read_local_test_identity,
)
from tests.api.unit.business._support import (
    api_module,
    request,
)

pytestmark = pytest.mark.database
SessionFactory: TypeAlias = async_sessionmaker[AsyncSession]
BLOCKS = count(4_000_000, 100)


class CatalogGraph(NamedTuple):
    """Stable synthetic identifiers for one private test's two-owner graph."""

    owner: int
    product: int
    group: int
    option: int
    foreign_product: int
    foreign_group: int


# ==============================================
# LOCAL ADMISSION BEFORE ANY FIXTURE WRITES
# ==============================================


@pytest.fixture
async def catalog_engine() -> AsyncIterator[AsyncEngine]:
    """Attest the launcher's exact local server; never fall back to Neon."""
    configuration = LocalPostgresSettings()
    assert configuration.PROFILE == "legacy"
    engine = create_async_engine(
        configuration.URL.get_secret_value(),
        echo=False,
        hide_parameters=True,
        connect_args={"ssl": False, "timeout": 10, "command_timeout": 20},
    )
    try:
        async with engine.connect() as connection:
            await connection.run_sync(
                lambda sync: read_local_test_identity(sync, configuration=configuration)
            )
            assert (
                await connection.scalar(text("SELECT version_num FROM alembic_version"))
                == LOCAL_REVISION
            )
        yield engine
    finally:
        await engine.dispose()


# ==============================================
# ISOLATED SYNTHETIC OWNER / RESTAURANT / CATALOG GRAPH
# ==============================================


@pytest.fixture
async def catalog_graph(catalog_engine: AsyncEngine) -> CatalogGraph:
    """Seed only the admitted disposable local instance with unique IDs."""
    base = next(BLOCKS)
    async with catalog_engine.begin() as connection:
        for offset in (0, 1):
            await connection.execute(
                Owner.__table__.insert().values(
                    id=base + offset, chat_id=base + offset, full_name="Synthetic owner"
                )
            )
            await connection.execute(
                Restaurant.__table__.insert().values(
                    id=base + 10 + offset,
                    owner_id=base + offset,
                    name="Synthetic restaurant",
                    type="cafe",
                    phone="fixture",
                    wilaya="Test",
                )
            )
            await connection.execute(
                Category.__table__.insert().values(
                    id=base + 20 + offset,
                    restaurant_id=base + 10 + offset,
                    name="Lunch",
                )
            )
            await connection.execute(
                Product.__table__.insert().values(
                    id=base + 30 + offset,
                    restaurant_id=base + 10 + offset,
                    category_id=base + 20 + offset,
                    name="Soup",
                    price=450,
                )
            )
            await connection.execute(
                OptionGroup.__table__.insert().values(
                    id=base + 40 + offset, product_id=base + 30 + offset, name="Extras"
                )
            )
            await connection.execute(
                ProductOption.__table__.insert().values(
                    id=base + 50 + offset,
                    group_id=base + 40 + offset,
                    name="Cheese",
                    extra_price=50,
                )
            )
    return CatalogGraph(base, base + 30, base + 40, base + 50, base + 31, base + 41)


# ==============================================
# REAL LOCAL SESSIONS AND ISOLATED HTTP ROUTERS
# ==============================================


@pytest.fixture
def catalog_sessions(catalog_engine: AsyncEngine) -> SessionFactory:
    """Use real asyncpg sessions with the existing production transaction options."""
    return async_sessionmaker(catalog_engine, expire_on_commit=False, autoflush=False)


# ==============================================
# BUILD AN ISOLATED CATALOG HTTP APPLICATION
# ==============================================


def catalog_http_app(
    *, module_name: str, sessions: SessionFactory, owner_id: int
) -> FastAPI:
    """Reuse real routing/authorization with an explicitly trusted fixture identity."""
    app = FastAPI()
    app.include_router(api_module(name=module_name).router)

    # ==============================================
    # REQUEST-OWNED LOCAL SESSION
    # ==============================================

    async def local_session() -> AsyncIterator[AsyncSession]:
        """Close or roll back only this HTTP request's local PostgreSQL session."""
        async with sessions() as session:
            try:
                yield session
            finally:
                await session.rollback()

    # ==============================================
    # TRUSTED FIXTURE IDENTITY LOOKUP
    # ==============================================

    async def fixture_owner(
        session: Annotated[AsyncSession, Depends(get_db)],
    ) -> OwnerPrincipal:
        """Perform the fixture lookup so the request starts with a real AUTOBEGIN."""
        assert (
            await session.scalar(select(Owner.id).where(Owner.id == owner_id))
            == owner_id
        )
        return OwnerPrincipal(owner_id=owner_id)

    app.dependency_overrides[get_db] = local_session
    app.dependency_overrides[get_current_owner] = fixture_owner
    return app


# ==============================================
# BULK SUCCESS, NATURAL CONFLICT AND FOREIGN PARENT
# ==============================================


@pytest.mark.parametrize("case", ["success", "conflict", "foreign"])
async def test_local_bulk_http_is_atomic_and_owner_scoped(
    catalog_sessions: SessionFactory, catalog_graph: CatalogGraph, case: str
) -> None:
    """Verify committed rows through another real session after the HTTP response."""
    graph = catalog_graph
    app = catalog_http_app(
        module_name="product_option", sessions=catalog_sessions, owner_id=graph.owner
    )
    response = await request(
        app=app,
        method="POST",
        url="/product-options/bulk",
        body={
            "group_id": graph.foreign_group if case == "foreign" else graph.group,
            "options": [
                {"name": "First batch item", "extra_price": 10},
                {
                    "name": "Cheese" if case == "conflict" else "Second batch item",
                    "extra_price": 20,
                },
            ],
        },
    )
    assert (
        response.status_code == {"success": 201, "conflict": 409, "foreign": 404}[case]
    )
    async with catalog_sessions() as observer:
        for group in (graph.group, graph.foreign_group):
            names = (
                await observer.scalars(
                    select(ProductOption.name).where(ProductOption.group_id == group)
                )
            ).all()
            expected = {"Cheese"}
            if case == "success" and group == graph.group:
                expected |= {"First batch item", "Second batch item"}
            assert set(names) == expected


# ==============================================
# LATE REORDER FAILURE WITH REAL POSTGRESQL ROLLBACK
# ==============================================


@pytest.mark.parametrize("kind", ["category", "group", "option"])
async def test_local_second_reorder_update_rolls_back_every_change(
    catalog_engine: AsyncEngine,
    catalog_sessions: SessionFactory,
    catalog_graph: CatalogGraph,
    kind: str,
) -> None:
    """A synthetic second-write fault must not preserve the actual first UPDATE."""
    graph = catalog_graph
    added = graph.owner + 60
    choices = {
        "category": (
            Category,
            "categories",
            {"restaurant_id": graph.owner + 10},
            f"/categories/reorder?restaurant_id={graph.owner + 10}&category_order={added}&category_order={graph.owner + 20}",
        ),
        "group": (
            OptionGroup,
            "option_group",
            {"product_id": graph.product},
            f"/option-groups/reorder?product_id={graph.product}&group_order={added}&group_order={graph.group}",
        ),
        "option": (
            ProductOption,
            "product_option",
            {"group_id": graph.group},
            f"/product-options/reorder?group_id={graph.group}&option_order={added}&option_order={graph.option}",
        ),
    }
    model, module_name, parent, url = choices[kind]
    async with catalog_engine.begin() as connection:
        await connection.execute(
            model.__table__.insert().values(
                id=added, name="Second owned resource", sort_order=9, **parent
            )
        )
    updates = 0

    # ==============================================
    # CONTROLLED LATE WRITE FAILURE
    # ==============================================

    def fail_second_update(
        connection: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        """Inject a bounded test failure without changing database schema/triggers."""
        nonlocal updates
        if statement.lstrip().upper().startswith("UPDATE "):
            updates += 1
            if updates == 2:
                raise RuntimeError("Synthetic second catalog UPDATE failure")

    app = catalog_http_app(
        module_name=module_name, sessions=catalog_sessions, owner_id=graph.owner
    )
    event.listen(
        catalog_engine.sync_engine, "before_cursor_execute", fail_second_update
    )
    try:
        response = await request(app=app, method="POST", url=url)
    finally:
        event.remove(
            catalog_engine.sync_engine, "before_cursor_execute", fail_second_update
        )
    assert response.status_code == 500 and updates == 2
    async with catalog_sessions() as observer:
        assert (
            await observer.scalar(select(model.sort_order).where(model.id == added))
            == 9
        )


# ==============================================
# LATE PARENT-DELETE FAILURE INCLUDING CASCADED CHILDREN
# ==============================================


@pytest.mark.parametrize("kind", ["group", "option"])
async def test_local_parent_delete_failure_keeps_every_original_row(
    catalog_engine: AsyncEngine,
    catalog_sessions: SessionFactory,
    catalog_graph: CatalogGraph,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    """Run the real first deletion, then reject the next one before final commit."""
    graph = catalog_graph
    added = graph.owner + 60
    if kind == "group":
        model, repository, module_name = (
            OptionGroup,
            OptionGroupsRepository,
            "option_group",
        )
        parent = {"product_id": graph.product}
        url = f"/option-groups/product/{graph.product}"
        original_id = graph.group
    else:
        model, repository, module_name = (
            ProductOption,
            ProductOptionRepository,
            "product_option",
        )
        parent = {"group_id": graph.group}
        url = f"/product-options/group/{graph.group}"
        original_id = graph.option
    async with catalog_engine.begin() as connection:
        await connection.execute(
            model.__table__.insert().values(id=added, name="Other", **parent)
        )
    original_delete = repository.delete
    calls = 0

    # ==============================================
    # CONTROLLED LATE DELETE FAILURE
    # ==============================================

    async def fail_second_delete(
        self: OptionGroupsRepository | ProductOptionRepository, *, id: int
    ) -> bool:
        """Preserve actual repository behavior for the first local deletion."""
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("Synthetic second catalog deletion failure")
        return await original_delete(self, id=id)

    monkeypatch.setattr(repository, "delete", fail_second_delete)
    app = catalog_http_app(
        module_name=module_name, sessions=catalog_sessions, owner_id=graph.owner
    )
    response = await request(app=app, method="DELETE", url=url)
    assert response.status_code == 500 and calls == 2
    async with catalog_sessions() as observer:
        assert set(
            (
                await observer.scalars(
                    select(model.id).where(model.id.in_([original_id, added]))
                )
            ).all()
        ) == {original_id, added}
        assert (
            await observer.scalar(
                select(ProductOption.id).where(ProductOption.id == graph.option)
            )
            == graph.option
        )


# ==============================================
# SCOPED AGGREGATES: EMPTY AND NON-PAGINATED DATA
# ==============================================


@pytest.mark.parametrize("case", ["normal", "empty", "over-page-limit"])
async def test_local_summary_values_are_complete_and_owner_filtered(
    catalog_engine: AsyncEngine,
    catalog_sessions: SessionFactory,
    catalog_graph: CatalogGraph,
    case: str,
) -> None:
    """Verify exact declared fields, including datasets larger than the old limit."""
    graph = catalog_graph
    group = graph.group
    expected_count, expected_total = 1, 50.0
    async with catalog_engine.begin() as connection:
        if case == "empty":
            group = graph.owner + 60
            await connection.execute(
                OptionGroup.__table__.insert().values(
                    id=group, product_id=graph.product, name="Empty"
                )
            )
            expected_count, expected_total = 0, 0.0
        elif case == "over-page-limit":
            await connection.execute(
                ProductOption.__table__.insert(),
                [
                    {
                        "group_id": group,
                        "name": f"Synthetic {number}",
                        "extra_price": 50.0,
                    }
                    for number in range(1001)
                ],
            )
            expected_count, expected_total = 1002, 50100.0
    app = catalog_http_app(
        module_name="product_option", sessions=catalog_sessions, owner_id=graph.owner
    )
    response = await request(
        app=app, method="GET", url=f"/product-options/group/{group}/summary"
    )
    assert response.status_code == 200, response.text
    assert response.json() == {
        "group_id": group,
        "total_options": expected_count,
        "available_options": expected_count,
        "unavailable_options": 0,
        "total_extra_price": expected_total,
        "avg_extra_price": 50.0 if expected_count else 0.0,
        "min_extra_price": 50.0 if expected_count else 0.0,
        "max_extra_price": 50.0 if expected_count else 0.0,
    }
    app = catalog_http_app(
        module_name="option_group", sessions=catalog_sessions, owner_id=graph.owner
    )
    response = await request(
        app=app, method="GET", url=f"/option-groups/product/{graph.product}/summary"
    )
    assert response.status_code == 200, response.text
    assert response.json()["total_options"] == (
        1 if case == "empty" else expected_count
    )
    foreign = await request(
        app=app,
        method="GET",
        url=f"/option-groups/product/{graph.foreign_product}/summary",
    )
    assert foreign.status_code == 200 and foreign.json()["total_options"] == 0


# ==============================================
# CALLER-OWNED TRANSACTIONS AND FLAG RESTORATION
# ==============================================


@pytest.mark.parametrize("mode", ["explicit", "managed-autobegin"])
async def test_local_batch_never_commits_the_callers_transaction(
    catalog_sessions: SessionFactory, catalog_graph: CatalogGraph, mode: str
) -> None:
    """A savepoint release must not expose uncommitted caller-owned rows."""
    graph = catalog_graph
    async with catalog_sessions() as session:
        service = ProductOptionService(session=session, owner_id=graph.owner)
        if mode == "explicit":
            await session.begin()
        else:
            await session.scalar(
                select(ProductOption.id).where(ProductOption.id == graph.option)
            )
            session.info["defer_repository_commit"] = True
        await service.create_options_bulk(
            group_id=graph.group,
            options=[ProductOptionCreate(name="Caller batch", extra_price=10)],
        )
        assert session.in_transaction()
        assert session.info.get("defer_repository_commit") is (
            True if mode == "managed-autobegin" else None
        )
        async with catalog_sessions() as observer:
            assert (
                await observer.scalar(
                    select(func.count(ProductOption.id)).where(
                        ProductOption.group_id == graph.group,
                        ProductOption.name == "Caller batch",
                    )
                )
                == 0
            )
        await session.rollback()
    async with catalog_sessions() as observer:
        assert (
            await observer.scalar(
                select(func.count(ProductOption.id)).where(
                    ProductOption.group_id == graph.group,
                    ProductOption.name == "Caller batch",
                )
            )
            == 0
        )


# ==============================================
# REFUSE UNFLUSHED CALLER WORK
# ==============================================


@pytest.mark.parametrize("pending", ["new", "dirty", "deleted"])
async def test_local_batch_refuses_unflushed_caller_changes(
    catalog_sessions: SessionFactory, catalog_graph: CatalogGraph, pending: str
) -> None:
    """Do not let savepoint construction implicitly flush unrelated pending work."""
    graph = catalog_graph
    async with catalog_sessions() as session:
        service = ProductOptionService(session=session, owner_id=graph.owner)
        if pending == "new":
            session.add(
                ProductOption(
                    group_id=graph.group, name="Caller pending", extra_price=10
                )
            )
        else:
            option = await session.get(ProductOption, graph.option)
            assert option is not None
            if pending == "dirty":
                option.name = "Caller pending"
            else:
                await session.delete(option)
        with pytest.raises(ValueError, match="clean_unit_of_work"):
            await service.create_options_bulk(
                group_id=graph.group, options=[ProductOptionCreate(name="Batch")]
            )
        await session.rollback()
    async with catalog_sessions() as observer:
        assert (
            await observer.scalar(
                select(ProductOption.name).where(ProductOption.id == graph.option)
            )
            == "Cheese"
        )


# ==============================================
# OWNED FRESH / READ-AUTOBEGIN TRANSACTIONS
# ==============================================


@pytest.mark.parametrize("prior_read", [False, True])
@pytest.mark.parametrize("fail", [False, True])
async def test_local_owned_transaction_commits_or_rolls_back_once(
    catalog_sessions: SessionFactory,
    catalog_graph: CatalogGraph,
    prior_read: bool,
    fail: bool,
) -> None:
    """Exercise actual PostgreSQL savepoint/commit behavior and flag cleanup."""
    graph = catalog_graph
    async with catalog_sessions() as session:
        service = ProductOptionService(session=session, owner_id=graph.owner)
        if prior_read:
            await session.scalar(
                select(ProductOption.id).where(ProductOption.id == graph.option)
            )

        # ==============================================
        # OWNED TRANSACTION TEST OPERATION
        # ==============================================

        async def operation() -> None:
            """Write through the real owner-scoped service within the batch context."""
            async with catalog_transaction(session=session):
                await service.create_option(
                    group_id=graph.group,
                    option_data=ProductOptionCreate(name="Owned transaction"),
                )
                if fail:
                    raise RuntimeError("Synthetic owned batch failure")

        if fail:
            with pytest.raises(RuntimeError, match="owned batch failure"):
                await operation()
        else:
            await operation()
        assert "defer_repository_commit" not in session.info
        assert not session.in_transaction()
    async with catalog_sessions() as observer:
        assert await observer.scalar(
            select(func.count(ProductOption.id)).where(
                ProductOption.group_id == graph.group,
                ProductOption.name == "Owned transaction",
            )
        ) == (0 if fail else 1)


# ==============================================
# PRESERVE CALLER WORK AROUND A FAILED SAVEPOINT
# ==============================================


async def test_local_failed_nested_batch_preserves_earlier_caller_work(
    catalog_sessions: SessionFactory, catalog_graph: CatalogGraph
) -> None:
    """Roll back the failed savepoint while retaining the caller's prior writes."""
    graph = catalog_graph
    async with catalog_sessions() as session:
        service = ProductOptionService(session=session, owner_id=graph.owner)
        async with session.begin():
            session.info["defer_repository_commit"] = True
            await service.create_option(
                group_id=graph.group,
                option_data=ProductOptionCreate(name="Outer retained"),
            )
            with pytest.raises(ConflictError):
                await service.create_options_bulk(
                    group_id=graph.group,
                    options=[
                        ProductOptionCreate(name="Inner transient"),
                        ProductOptionCreate(name="Cheese"),
                    ],
                )
            assert session.info["defer_repository_commit"] is True
    async with catalog_sessions() as observer:
        names = set(
            (
                await observer.scalars(
                    select(ProductOption.name).where(
                        ProductOption.group_id == graph.group
                    )
                )
            ).all()
        )
        assert names == {"Cheese", "Outer retained"}
