# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Exercise real tenant-filtered catalog SQL against disposable in-memory SQLite.

The adapter forwards async session operations to SQLite's synchronous driver;
it preserves SQLAlchemy session events and real repository/business operations.
These relational tests complement PostgreSQL validation, without claiming to
exercise asyncpg, production data, or PostgreSQL transaction semantics.
"""

from collections.abc import (
    Iterator,
    Sequence,
)
from typing import Any

import pytest
from fastapi import FastAPI
from sqlalchemy import (
    create_engine,
    event,
    select,
)
from sqlalchemy.engine import Result
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy.sql import Executable

from app.api.auth import (
    OwnerPrincipal,
    get_current_owner,
)
from app.core.database import get_db
from app.models.base import Base
from app.models.category import Category
from app.models.option_group import OptionGroup
from app.models.owner import Owner
from app.models.product import Product
from app.models.product_option import ProductOption
from app.models.restaurant import Restaurant
from tests.api.unit.business._support import (
    api_module,
    request,
)

# ==============================================
# DISPOSABLE REAL SQL ADAPTER
# ==============================================


class SQLiteCatalogSession(AsyncSession):
    """Keep the production session and guard contracts over a local SQL engine."""

    async def execute(
        self, statement: Executable, *args: Any, **kwargs: Any
    ) -> Result[Any]:
        """Run real SQL with all normal synchronous session authorization hooks."""
        return self.sync_session.execute(statement, *args, **kwargs)

    async def flush(self, objects: Sequence[object] | None = None) -> None:
        """Exercise before_flush tenant checks and real SQLite writes."""
        self.sync_session.flush(objects)

    async def commit(self) -> None:
        """Persist only into the fixture's private in-memory SQLite engine."""
        self.sync_session.commit()

    async def rollback(self) -> None:
        """Discard changes in the same disposable engine."""
        self.sync_session.rollback()

    async def close(self) -> None:
        """Release fixture state without using a remote database driver."""
        self.sync_session.close()


@pytest.fixture
def catalog_database() -> Iterator[SQLiteCatalogSession]:
    """Seed two isolated owners using trusted fixture setup outside scoped SQL."""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(
            Owner.__table__.insert(),
            [{"id": 7, "chat_id": 7007}, {"id": 8, "chat_id": 8008}],
        )
        for suffix, owner_id in [(1, 7), (2, 8)]:
            connection.execute(
                Restaurant.__table__.insert().values(
                    id=10 + suffix,
                    owner_id=owner_id,
                    name=f"Restaurant {suffix}",
                    type="cafe",
                    phone="fixture",
                    wilaya="fixture",
                )
            )
            connection.execute(
                Category.__table__.insert().values(
                    id=20 + suffix, restaurant_id=10 + suffix, name="Lunch"
                )
            )
            connection.execute(
                Product.__table__.insert().values(
                    id=30 + suffix,
                    restaurant_id=10 + suffix,
                    category_id=20 + suffix,
                    name="Soup",
                    price=450,
                )
            )
            connection.execute(
                OptionGroup.__table__.insert().values(
                    id=40 + suffix, product_id=30 + suffix, name="Extras"
                )
            )
            connection.execute(
                ProductOption.__table__.insert().values(
                    id=50 + suffix,
                    group_id=40 + suffix,
                    name="Cheese",
                    extra_price=50,
                )
            )
    synchronous = Session(bind=engine, expire_on_commit=False)
    session = SQLiteCatalogSession(sync_session_class=lambda **_: synchronous)
    writes: list[str] = []
    session.info["test_sql_write_verbs"] = writes

    @event.listens_for(engine, "before_cursor_execute")
    def record_mutation(
        connection: object,
        cursor: object,
        statement: str,
        parameters: object,
        context: object,
        executemany: bool,
    ) -> None:
        """Record mutation verbs after fixture setup without retaining data values."""
        verb = statement.lstrip().split(" ", 1)[0].upper()
        if verb in {"INSERT", "UPDATE", "DELETE"}:
            writes.append(verb)

    try:
        yield session
    finally:
        synchronous.close()
        engine.dispose()


def catalog_app(*, module_name: str, session: SQLiteCatalogSession) -> FastAPI:
    """Mount real factories/services/repositories with one verified test owner."""
    app = FastAPI()
    app.include_router(api_module(name=module_name).router)

    async def database_dependency() -> SQLiteCatalogSession:
        """Return only the fixture's private relational database session."""
        return session

    async def owner_dependency() -> OwnerPrincipal:
        """Provide a verified identity fixture; no real OIDC identity is created."""
        return OwnerPrincipal(owner_id=7)

    app.dependency_overrides[get_db] = database_dependency
    app.dependency_overrides[get_current_owner] = owner_dependency
    return app


# ==============================================
# OWNER SQL FILTERS AND FOREIGN IDENTIFIERS
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "module_name,prefix,own_id,search",
    [
        ("products", "/products/", 31, "Soup"),
        ("categories", "/categories/", 21, "Lunch"),
        ("option_group", "/option-groups/", 41, "Extras"),
        ("product_option", "/product-options/", 51, "Cheese"),
    ],
)
@pytest.mark.parametrize("searching", [False, True])
async def test_catalog_real_sql_lists_and_counts_never_include_another_owner(
    catalog_database: SQLiteCatalogSession,
    module_name: str,
    prefix: str,
    own_id: int,
    search: str,
    searching: bool,
) -> None:
    """List and wildcard search totals are computed from the same owner boundary."""
    app = catalog_app(module_name=module_name, session=catalog_database)
    suffix = f"?search={search}" if searching else "?only_available=false"
    response = await request(app=app, method="GET", url=prefix + suffix)
    assert response.status_code == 200, response.text
    assert response.json()["total"] == 1
    assert [item["id"] for item in response.json()["items"]] == [own_id]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "module_name,prefix,foreign_id",
    [
        ("products", "/products/", 32),
        ("categories", "/categories/", 22),
        ("option_group", "/option-groups/", 42),
        ("product_option", "/product-options/", 52),
    ],
)
@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE"])
async def test_foreign_catalog_identifier_is_hidden_and_never_mutated(
    catalog_database: SQLiteCatalogSession,
    module_name: str,
    prefix: str,
    foreign_id: int,
    method: str,
) -> None:
    """Real API/business/repository paths hide foreign reads, updates and deletion."""
    app = catalog_app(module_name=module_name, session=catalog_database)
    response = await request(
        app=app,
        method=method,
        url=f"{prefix}{foreign_id}",
        body={"name": "Unauthorized change"} if method == "PATCH" else None,
    )
    assert response.status_code == 404, response.text
    assert catalog_database.info["test_sql_write_verbs"] == []
    model = {
        "products": Product,
        "categories": Category,
        "option_group": OptionGroup,
        "product_option": ProductOption,
    }[module_name]
    with catalog_database.sync_session.get_bind().connect() as connection:
        foreign_name = connection.execute(
            select(model.name).where(model.id == foreign_id)
        ).scalar_one()
    assert foreign_name != "Unauthorized change"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "module_name,url,body,model",
    [
        ("categories", "/categories/?restaurant_id=12", {"name": "Other"}, Category),
        (
            "products",
            "/products/?restaurant_id=12",
            {"category_id": 22, "name": "Other", "price": 450},
            Product,
        ),
        (
            "products",
            "/products/?restaurant_id=11",
            {"category_id": 22, "name": "Other", "price": 450},
            Product,
        ),
        (
            "option_group",
            "/option-groups/?product_id=32",
            {"product_id": 32, "name": "Other"},
            OptionGroup,
        ),
        (
            "product_option",
            "/product-options/?group_id=42",
            {"name": "Other", "extra_price": 50},
            ProductOption,
        ),
    ],
)
async def test_catalog_foreign_parent_is_rejected_before_insertion(
    catalog_database: SQLiteCatalogSession,
    module_name: str,
    url: str,
    body: dict[str, object],
    model: type[Base],
) -> None:
    """Foreign restaurants, categories, products and groups cannot acquire rows."""
    app = catalog_app(module_name=module_name, session=catalog_database)
    response = await request(app=app, method="POST", url=url, body=body)
    assert response.status_code == 404, response.text
    assert catalog_database.info["test_sql_write_verbs"] == []
    with catalog_database.sync_session.get_bind().connect() as connection:
        names = connection.execute(select(model.name)).scalars().all()
    assert "Other" not in names


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "module_name,prefix,own_id",
    [
        ("products", "/products/", 31),
        ("categories", "/categories/", 21),
        ("option_group", "/option-groups/", 41),
        ("product_option", "/product-options/", 51),
    ],
)
async def test_verified_owner_can_update_its_own_catalog_rows(
    catalog_database: SQLiteCatalogSession,
    module_name: str,
    prefix: str,
    own_id: int,
) -> None:
    """Authorization still permits a legitimate business/repository write."""
    app = catalog_app(module_name=module_name, session=catalog_database)
    response = await request(
        app=app,
        method="PATCH",
        url=f"{prefix}{own_id}",
        body={"name": "Updated by owner"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["name"] == "Updated by owner"
    assert catalog_database.info["test_sql_write_verbs"] == ["UPDATE"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "module_name,url",
    [
        (
            "categories",
            "/categories/reorder?restaurant_id=11&category_order=21&category_order=22",
        ),
        (
            "option_group",
            "/option-groups/reorder?product_id=31&group_order=41&group_order=42",
        ),
        (
            "product_option",
            "/product-options/reorder?group_id=41&option_order=51&option_order=52",
        ),
    ],
)
async def test_foreign_late_reorder_member_does_not_change_the_first_row(
    catalog_database: SQLiteCatalogSession, module_name: str, url: str
) -> None:
    """An actual mixed-owner HTTP batch is rejected before its first SQL update."""
    app = catalog_app(module_name=module_name, session=catalog_database)
    response = await request(app=app, method="POST", url=url)
    assert response.status_code == 404, response.text
    assert catalog_database.info["test_sql_write_verbs"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "module_name,url,body,parent_key,parent_id",
    [
        (
            "option_group",
            "/option-groups/?product_id=31",
            {"product_id": 31, "name": "Additional"},
            "product_id",
            31,
        ),
        (
            "product_option",
            "/product-options/?group_id=41",
            {"name": "Additional", "extra_price": 20},
            "group_id",
            41,
        ),
    ],
)
async def test_verified_owner_can_create_catalog_options_under_its_own_parent(
    catalog_database: SQLiteCatalogSession,
    module_name: str,
    url: str,
    body: dict[str, object],
    parent_key: str,
    parent_id: int,
) -> None:
    """Validated creation reaches ORM flush and commits only to the owned parent."""
    app = catalog_app(module_name=module_name, session=catalog_database)
    response = await request(app=app, method="POST", url=url, body=body)
    assert response.status_code == 201, response.text
    assert response.json()[parent_key] == parent_id
    assert response.json()["name"] == "Additional"
    assert catalog_database.info["test_sql_write_verbs"] == ["INSERT"]
