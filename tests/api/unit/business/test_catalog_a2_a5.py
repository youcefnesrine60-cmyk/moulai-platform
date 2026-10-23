# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Targeted catalog security checks and atomicity acceptance reproductions.

Reuse the existing disposable SQLite fixture and actual API/business/repository
code. No application lifecycle, shared database fixture or remote service runs.
The atomicity assertions express the required behavior; failures are findings,
not permission to change the business code during this audit.
"""

from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from httpx import (
    ASGITransport,
    AsyncClient,
)
from sqlalchemy import (
    event,
    select,
)

from app.core.config import settings
from app.core.database import get_db
from app.models.category import Category
from app.models.option_group import OptionGroup
from app.models.product import Product
from app.models.product_option import ProductOption
from app.models.restaurant import Restaurant
from tests.api.unit.business._support import (
    api_module,
    request,
)
from tests.api.unit.business.test_catalog_sqlite_authorization import (
    SQLiteCatalogSession,
    catalog_app,
)

pytest_plugins = ("tests.api.unit.business.test_catalog_sqlite_authorization",)

CATALOG_ROUTES = [
    (
        module_name,
        method,
        route.path.format(**{name: 41 for name in route.param_convertors}),
    )
    for module_name in ("products", "categories", "option_group", "product_option")
    for route in api_module(name=module_name).router.routes
    if isinstance(route, APIRoute)
    for method in sorted(route.methods)
]

# ==============================================
# INVALID BEARER AND CLIENT-SUPPLIED OWNER IDS
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("module_name,method,url", CATALOG_ROUTES)
@pytest.mark.parametrize("bearer", [None, "Bearer synthetic-invalid"])
async def test_every_catalog_operation_rejects_missing_or_invalid_bearer(
    module_name: str,
    method: str,
    url: str,
    bearer: str | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject missing/invalid tokens on every actual route before database use."""
    monkeypatch.setattr(settings, "OIDC_ISSUER", "https://identity.example.test")
    monkeypatch.setattr(settings, "OIDC_AUDIENCE", "moulai-api")
    monkeypatch.setattr(
        settings, "OIDC_JWKS_URL", "https://identity.example.test/certs"
    )
    app = FastAPI()
    app.include_router(api_module(name=module_name).router)
    database = AsyncMock(name="no_database_access_for_invalid_identity")

    async def database_dependency() -> AsyncMock:
        """Supply an observable sentinel without starting a database connection."""
        return database

    app.dependency_overrides[get_db] = database_dependency
    headers = {"X-Owner-ID": "8"}
    if bearer is not None:
        headers["Authorization"] = bearer
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://offline-api.test"
    ) as client:
        response = await client.request(
            method,
            url + "?owner_id=8",
            headers=headers,
        )
    assert response.status_code == 401, response.text
    assert response.headers["www-authenticate"] == "Bearer"
    database.execute.assert_not_awaited()
    database.flush.assert_not_awaited()
    database.commit.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "module_name,prefix,own_id,foreign_id",
    [
        ("products", "/products", 31, 32),
        ("categories", "/categories", 21, 22),
        ("option_group", "/option-groups", 41, 42),
        ("product_option", "/product-options", 51, 52),
    ],
)
async def test_client_owner_parameter_cannot_change_verified_scope(
    catalog_database: SQLiteCatalogSession,
    module_name: str,
    prefix: str,
    own_id: int,
    foreign_id: int,
) -> None:
    """An owner_id query parameter cannot select a foreign SQL identity."""
    app = catalog_app(module_name=module_name, session=catalog_database)
    listed = await request(
        app=app, method="GET", url=f"{prefix}/?owner_id=8&only_available=false"
    )
    assert listed.status_code == 200, listed.text
    assert [item["id"] for item in listed.json()["items"]] == [own_id]
    foreign = await request(
        app=app, method="GET", url=f"{prefix}/{foreign_id}?owner_id=8"
    )
    assert foreign.status_code == 404, foreign.text
    assert catalog_database.info["test_sql_write_verbs"] == []


# ==============================================
# SAME OWNER, DIFFERENT RESTAURANTS
# ==============================================


def _add_second_owned_restaurant(*, session: SQLiteCatalogSession) -> None:
    """Extend only the private fixture before binding its request owner scope."""
    with session.sync_session.get_bind().begin() as connection:
        connection.execute(
            Restaurant.__table__.insert().values(
                id=13,
                owner_id=7,
                name="Second owned restaurant",
                type="cafe",
                phone="fixture",
                wilaya="fixture",
            )
        )
        connection.execute(
            Category.__table__.insert().values(id=23, restaurant_id=13, name="Other")
        )
        connection.execute(
            Product.__table__.insert().values(
                id=33, restaurant_id=13, category_id=23, name="Other", price=450
            )
        )
        connection.execute(
            OptionGroup.__table__.insert().values(id=43, product_id=33, name="Other")
        )
        connection.execute(
            ProductOption.__table__.insert().values(
                id=53, group_id=43, name="Other", extra_price=20
            )
        )
    session.info["test_sql_write_verbs"].clear()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "module_name,method,url,body,expected",
    [
        (
            "products",
            "POST",
            "/products/?restaurant_id=11",
            {"category_id": 23, "name": "Invalid association", "price": 450},
            404,
        ),
        ("products", "PATCH", "/products/31", {"category_id": 23}, 404),
        (
            "categories",
            "POST",
            "/categories/reorder?restaurant_id=11&category_order=21&category_order=23",
            None,
            422,
        ),
        (
            "option_group",
            "POST",
            "/option-groups/reorder?product_id=31&group_order=41&group_order=43",
            None,
            422,
        ),
        (
            "product_option",
            "POST",
            "/product-options/reorder?group_id=41&option_order=51&option_order=53",
            None,
            422,
        ),
    ],
)
async def test_same_owner_does_not_allow_cross_restaurant_relationships(
    catalog_database: SQLiteCatalogSession,
    module_name: str,
    method: str,
    url: str,
    body: dict[str, object] | None,
    expected: int,
) -> None:
    """A valid common owner does not authorize inconsistent resource parents."""
    _add_second_owned_restaurant(session=catalog_database)
    app = catalog_app(module_name=module_name, session=catalog_database)
    response = await request(app=app, method=method, url=url, body=body)
    assert response.status_code == expected, response.text
    assert catalog_database.info["test_sql_write_verbs"] == []


# ==============================================
# LEGITIMATE SUMMARY RESPONSE CONTRACTS
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "module_name,url",
    [
        ("option_group", "/option-groups/product/31/summary"),
        ("product_option", "/product-options/group/41/summary"),
    ],
)
async def test_owned_option_summary_must_return_its_declared_contract(
    catalog_database: SQLiteCatalogSession, module_name: str, url: str
) -> None:
    """Confirm that legitimate summaries work through real SQL and serializers."""
    app = catalog_app(module_name=module_name, session=catalog_database)
    response = await request(app=app, method="GET", url=url)
    assert response.status_code == 200, response.text
    assert catalog_database.info["test_sql_write_verbs"] == []


# ==============================================
# ATOMICITY ACCEPTANCE: REPRODUCE BEFORE PROPOSING CHANGES
# ==============================================


@pytest.mark.asyncio
async def test_bulk_conflict_must_not_leave_a_committed_first_option(
    catalog_database: SQLiteCatalogSession,
) -> None:
    """A naturally conflicting second item must roll back the complete HTTP batch."""
    app = catalog_app(module_name="product_option", session=catalog_database)
    response = await request(
        app=app,
        method="POST",
        url="/product-options/bulk",
        body={
            "group_id": 41,
            "options": [
                {"name": "Audit first item", "extra_price": 10},
                {"name": "Cheese", "extra_price": 50},
            ],
        },
    )
    assert response.status_code == 409, response.text
    # Match get_db's exception rollback even though the fixture overrides it.
    await catalog_database.rollback()
    with catalog_database.sync_session.get_bind().connect() as connection:
        names = (
            connection.execute(
                select(ProductOption.name).where(ProductOption.group_id == 41)
            )
            .scalars()
            .all()
        )
    assert "Audit first item" not in names, "409 left the first option committed"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "module_name,model,payload,url",
    [
        (
            "categories",
            Category,
            {"restaurant_id": 11, "name": "Audit"},
            "/categories/reorder?restaurant_id=11&category_order=61&category_order=21",
        ),
        (
            "option_group",
            OptionGroup,
            {"product_id": 31, "name": "Audit"},
            "/option-groups/reorder?product_id=31&group_order=61&group_order=41",
        ),
        (
            "product_option",
            ProductOption,
            {"group_id": 41, "name": "Audit", "extra_price": 10},
            "/product-options/reorder?group_id=41&option_order=61&option_order=51",
        ),
    ],
)
async def test_second_update_failure_must_rollback_complete_reorder(
    catalog_database: SQLiteCatalogSession,
    module_name: str,
    model: type[Category] | type[OptionGroup] | type[ProductOption],
    payload: dict[str, object],
    url: str,
) -> None:
    """A deterministic late storage failure must not preserve an earlier commit."""
    engine = catalog_database.sync_session.get_bind()
    with engine.begin() as connection:
        connection.execute(
            model.__table__.insert().values(id=61, sort_order=9, **payload)
        )
    app = catalog_app(module_name=module_name, session=catalog_database)
    updates = 0

    def fail_second_update(
        connection: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        """Inject only a local synthetic failure before the second actual UPDATE."""
        nonlocal updates
        if statement.lstrip().upper().startswith("UPDATE "):
            updates += 1
            if updates == 2:
                raise RuntimeError("Synthetic second catalog UPDATE failure")

    event.listen(engine, "before_cursor_execute", fail_second_update)
    try:
        response = await request(app=app, method="POST", url=url)
    finally:
        event.remove(engine, "before_cursor_execute", fail_second_update)
    assert response.status_code == 500, response.text
    assert updates == 2
    await catalog_database.rollback()
    with engine.connect() as connection:
        actual = connection.execute(
            select(model.sort_order).where(model.id == 61)
        ).scalar_one()
    assert actual == 9, "500 left the first reorder UPDATE committed"
