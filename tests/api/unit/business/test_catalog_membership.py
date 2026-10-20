# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Verify catalog parent membership is checked before any write occurs."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    NotFoundError,
    ValidationError,
)
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
)
from app.services.business.category_service import CategoryService
from app.services.business.product_option_service import ProductOptionService
from app.services.business.product_service import ProductService

# ==============================================
# REORDER VALIDATION BOUNDARIES
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("missing", [False, True])
async def test_category_reorder_validates_late_members_before_any_update(
    missing: bool,
) -> None:
    """A foreign or missing second category leaves the first category untouched."""
    service = CategoryService(session=AsyncSession(), owner_id=7)
    service.repo = SimpleNamespace(
        get_by_id=AsyncMock(
            side_effect=[
                SimpleNamespace(id=21, restaurant_id=11),
                None if missing else SimpleNamespace(id=22, restaurant_id=12),
            ]
        ),
        update=AsyncMock(),
    )
    with pytest.raises(NotFoundError if missing else ValidationError):
        await service.reorder_categories(restaurant_id=11, category_order=[21, 22])
    service.repo.update.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("missing", [False, True])
async def test_option_reorder_validates_late_members_before_any_update(
    missing: bool,
) -> None:
    """An invalid later option cannot persist an earlier ordering change."""
    service = ProductOptionService(session=AsyncSession(), owner_id=7)
    service.group_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=object()))
    service.repo = SimpleNamespace(
        get_by_id=AsyncMock(
            side_effect=[
                SimpleNamespace(id=51, group_id=41),
                None if missing else SimpleNamespace(id=52, group_id=42),
            ]
        ),
        update_sort_order=AsyncMock(),
    )
    with pytest.raises(NotFoundError if missing else ValidationError):
        await service.reorder_options(group_id=41, option_order=[51, 52])
    service.repo.update_sort_order.assert_not_awaited()


# ==============================================
# PRODUCT CATEGORY RESTAURANT BOUNDARY
# ==============================================


@pytest.mark.asyncio
@pytest.mark.parametrize("updating", [False, True])
async def test_product_rejects_category_from_another_restaurant_before_writes(
    updating: bool,
) -> None:
    """Category validation applies both when creating and when moving a product."""
    session = AsyncSession()
    session.execute = AsyncMock(
        return_value=SimpleNamespace(scalar_one_or_none=lambda: None)
    )
    service = ProductService(session=session, owner_id=7)
    service.repo = SimpleNamespace(
        get_by_id=AsyncMock(return_value=SimpleNamespace(id=31, restaurant_id=11)),
        create=AsyncMock(),
        update=AsyncMock(),
    )
    with pytest.raises(NotFoundError, match="Category not found"):
        if updating:
            await service.update_product(
                product_id=31, update_data=ProductUpdate(category_id=22)
            )
        else:
            await service.create_product(
                restaurant_id=11,
                product_data=ProductCreate(category_id=22, name="Soup", price=450),
            )
    query = session.execute.await_args.args[0]
    sql = str(query)
    assert "categories.id =" in sql
    assert "categories.restaurant_id =" in sql
    assert set(query.compile().params.values()) >= {11, 22}
    service.repo.create.assert_not_awaited()
    service.repo.update.assert_not_awaited()
