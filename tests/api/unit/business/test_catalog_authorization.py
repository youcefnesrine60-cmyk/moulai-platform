# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Exercise the catalog authentication boundary independently of service mocks."""

from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI

from app.core.database import get_db
from tests.api.unit.business._support import (
    api_module,
    request,
)
from tests.api.unit.business.test_catalog_http import (
    OPERATIONS,
    CatalogOperation,
)

# ==============================================
# AUTHENTICATION BEFORE CATALOG ACCESS
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", OPERATIONS)
async def test_catalog_rejects_missing_bearer_before_any_database_access(
    operation: CatalogOperation,
) -> None:
    """Every existing catalog operation rejects an unauthenticated HTTP caller."""
    module = api_module(name=operation.module)
    app = FastAPI()
    app.include_router(module.router)
    database = AsyncMock(name="database_not_available_to_anonymous_caller")

    async def database_dependency() -> AsyncMock:
        """Supply a strict database sentinel without enabling application startup."""
        return database

    app.dependency_overrides[get_db] = database_dependency
    response = await request(
        app=app,
        method=operation.method,
        url=operation.url,
        body=operation.body,
    )
    assert response.status_code == 401, response.text
    assert response.headers["www-authenticate"] == "Bearer"
    database.execute.assert_not_awaited()
    database.flush.assert_not_awaited()
    database.commit.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "module_name,url",
    [
        ("products", "/products/"),
        ("products", "/products/?search=Soup"),
        ("categories", "/categories/"),
        ("categories", "/categories/?search=Lunch"),
        ("option_group", "/option-groups/"),
        ("option_group", "/option-groups/?search=Extras"),
        ("product_option", "/product-options/"),
        ("product_option", "/product-options/?search=Cheese"),
    ],
)
async def test_catalog_lists_and_search_require_verified_owner(
    module_name: str, url: str
) -> None:
    """Omitting a filter never turns catalog administration into a public list."""
    app = FastAPI()
    app.include_router(api_module(name=module_name).router)
    database = AsyncMock()

    async def database_dependency() -> AsyncMock:
        """Keep all database operations as observable test sentinels."""
        return database

    app.dependency_overrides[get_db] = database_dependency
    response = await request(app=app, method="GET", url=url)
    assert response.status_code == 401, response.text
    database.execute.assert_not_awaited()
