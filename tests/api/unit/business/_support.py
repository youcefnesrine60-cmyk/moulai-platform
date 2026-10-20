# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Construct isolated HTTP applications without application startup or a database."""

from collections.abc import Callable
from importlib import import_module
from types import ModuleType
from typing import (
    Any,
    get_type_hints,
)
from unittest.mock import (
    AsyncMock,
    NonCallableMagicMock,
    create_autospec,
)

from fastapi import FastAPI
from httpx import (
    ASGITransport,
    AsyncClient,
    Response,
)
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.auth import (
    OwnerPrincipal,
    get_current_owner,
)

# ==============================================
# HTTP TEST BOUNDARY
# ==============================================


def api_module(*, name: str) -> ModuleType:
    """Import the actual router module rather than a test reimplementation."""
    return import_module(f"app.api.v1.{name}")


def service_double(
    *, dependency: Callable[..., Any], methods: tuple[str, ...]
) -> NonCallableMagicMock:
    """Enforce the real service, repository and session method signatures.

    These constructors only assemble collaborators. The sentinel deliberately
    has no database operations, so construction cannot issue a query. No real
    service method is invoked; only the constructor's instance shape is used.
    """
    service_type = get_type_hints(dependency)["return"]
    if service_type.__name__ in {
        "CategoryService",
        "ProductService",
        "OptionGroupsService",
        "ProductOptionService",
    }:
        instance = service_type(session=AsyncSession(), owner_id=7)
    else:
        instance = service_type(session=object())
    service = create_autospec(instance, instance=True, spec_set=True)
    service.repo = create_autospec(type(instance.repo), instance=True, spec_set=True)
    service.session = create_autospec(AsyncSession, instance=True, spec_set=True)
    for name in methods:
        if not isinstance(getattr(service, name), AsyncMock):
            raise TypeError("async_service_method_required")
    return service


def make_app(
    *,
    module: ModuleType,
    dependencies: dict[Callable[..., Any], object],
) -> FastAPI:
    """Mount one real router and substitute only its external dependencies."""
    app = FastAPI()
    app.include_router(module.router)

    def override_value(value: object) -> Callable[[], object]:
        """Bind one replacement without exposing parameters to FastAPI."""

        def override() -> object:
            """Return the dependency belonging to this test only."""
            return value

        return override

    for dependency, value in dependencies.items():
        app.dependency_overrides[dependency] = override_value(value)
    app.dependency_overrides[get_db] = override_value(
        AsyncMock(name="database_access_is_not_allowed")
    )
    if module.__name__.rsplit(".", 1)[-1] in {
        "products",
        "categories",
        "option_group",
        "product_option",
    }:
        app.dependency_overrides[get_current_owner] = override_value(
            OwnerPrincipal(owner_id=7)
        )
    return app


async def request(
    *,
    app: FastAPI,
    method: str,
    url: str,
    body: object | None = None,
) -> Response:
    """Send an in-process HTTP request without opening a network connection."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://offline-api.test"
    ) as client:
        return await client.request(method=method, url=url, json=body)


def assert_call_fields(*, method: AsyncMock, expected: dict[str, object]) -> None:
    """Check context IDs exactly and inspect validated request model fields."""
    method.assert_awaited_once()
    assert method.await_args is not None
    assert method.await_args.args == ()
    actual = method.await_args.kwargs
    assert actual.keys() == expected.keys()
    for name, value in expected.items():
        if isinstance(actual[name], BaseModel):
            payload = actual[name].model_dump(exclude_unset=True)
            assert payload == value
        elif isinstance(actual[name], list):
            payload = [
                (
                    item.model_dump(exclude_unset=True)
                    if isinstance(item, BaseModel)
                    else item
                )
                for item in actual[name]
            ]
            assert payload == value
        else:
            assert actual[name] == value
