# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Verify the explicit option-group context at the real business boundary."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.schemas.product_option import ProductOptionCreate
from app.services.business.product_option_service import (
    MAX_OPTIONS_PER_GROUP,
    ProductOptionService,
)
from tests.api.unit.business.test_catalog_http import OPTION


def option_service(
    *, group_exists: bool = True, duplicate: bool = False, count: int = 0
) -> ProductOptionService:
    """Retain business logic while replacing repository I/O with strict doubles."""
    service = ProductOptionService(session=AsyncSession(), owner_id=7)
    service.group_repo = SimpleNamespace(
        get_by_id=AsyncMock(return_value=object() if group_exists else None)
    )
    service.repo = SimpleNamespace(
        get_by_name=AsyncMock(return_value=object() if duplicate else None),
        create=AsyncMock(return_value=SimpleNamespace(**OPTION)),
    )
    service.count_by_group = AsyncMock(return_value=count)
    return service


@pytest.mark.asyncio
async def test_option_creation_uses_explicit_group_for_lookups_and_insert() -> None:
    """A valid public create schema need not have an undeclared group attribute."""
    service = option_service()
    payload = ProductOptionCreate(name="Cheese", extra_price=50.0)
    result = await service.create_option(group_id=41, option_data=payload)
    assert result.id == 51
    assert result.group_id == 41
    service.group_repo.get_by_id.assert_awaited_once_with(id=41)
    service.count_by_group.assert_awaited_once_with(group_id=41, only_available=False)
    service.repo.get_by_name.assert_awaited_once_with(group_id=41, name="Cheese")
    service.repo.create.assert_awaited_once_with(
        data={
            "group_id": 41,
            "name": "Cheese",
            "extra_price": 50.0,
            "is_available": True,
            "sort_order": 0,
        }
    )
    assert "group_id" not in payload.model_dump()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "group_exists,duplicate,count,exception",
    [
        (False, False, 0, NotFoundError),
        (True, True, 0, ConflictError),
        (True, False, MAX_OPTIONS_PER_GROUP, ValidationError),
    ],
)
async def test_option_creation_does_not_insert_after_group_checks_fail(
    group_exists: bool, duplicate: bool, count: int, exception: type[Exception]
) -> None:
    """Missing groups, duplicate names and quota violations stop before insertion."""
    service = option_service(
        group_exists=group_exists, duplicate=duplicate, count=count
    )
    with pytest.raises(exception):
        await service.create_option(
            group_id=41,
            option_data=ProductOptionCreate(name="Cheese", extra_price=50.0),
        )
    service.repo.create.assert_not_awaited()
