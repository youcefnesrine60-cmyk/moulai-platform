# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

"""Verify branch tenant isolation and administrative global-user access offline."""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any
from unittest.mock import (
    AsyncMock,
    Mock,
)

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from httpx import (
    ASGITransport,
    AsyncClient,
)
from sqlalchemy import (
    select,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import auth
from app.api.v1 import (
    branches,
    user,
)
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import UnauthorizedError
from app.models.branch import Branch
from app.models.feature_pricing import FeatureUsageCounter
from app.services.business import branch_service
from app.services.business.admin import admin_service
from tests.api.unit.business.test_catalog_sqlite_authorization import (
    SQLiteCatalogSession,
    catalog_app,
    catalog_database as catalog_database,
)

# ==============================================
# REAL ROUTE INVENTORY AND AUTHENTICATION
# ==============================================


@dataclass(frozen=True)
class Endpoint:
    """Describe one operation using the actual application's router inventory."""

    module: str
    method: str
    path: str


def endpoints() -> tuple[Endpoint, ...]:
    """Cover every branch and global-user route, including static statistics."""
    result: list[Endpoint] = []
    for module in (branches, user):
        for route in module.router.routes:
            if isinstance(route, APIRoute):
                path = route.path_format
                for parameter in route.param_convertors:
                    path = path.replace("{" + parameter + "}", "7")
                result.extend(
                    Endpoint(module.__name__.rsplit(".", 1)[-1], method, path)
                    for method in sorted(route.methods)
                )
    return tuple(result)


ENDPOINTS = endpoints()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "endpoint", ENDPOINTS, ids=lambda item: f"{item.method}:{item.path}"
)
@pytest.mark.parametrize(
    "configured,bearer", [(False, False), (False, True), (True, False), (True, True)]
)
async def test_each_route_rejects_untrusted_identifiers_before_business_io(
    monkeypatch: pytest.MonkeyPatch,
    endpoint: Endpoint,
    configured: bool,
    bearer: bool,
) -> None:
    """Neither owner/admin/chat IDs nor forged bearer strings can grant access."""
    module = branches if endpoint.module == "branches" else user
    app = FastAPI()
    app.include_router(module.router)
    session = AsyncMock(spec=AsyncSession)
    business = AsyncMock(side_effect=AssertionError("Unauthorized service access"))
    key_lookup = Mock(side_effect=AssertionError("Unexpected signing-key lookup"))
    monkeypatch.setattr(auth, "_get_jwks_client", key_lookup)
    for name, value in (
        ("OIDC_ISSUER", "https://keycloak.test/realms/local"),
        ("OIDC_AUDIENCE", "local-api"),
        ("OIDC_JWKS_URL", "https://keycloak.test/realms/local/certs"),
    ):
        monkeypatch.setattr(settings, name, value if configured else None)

    async def database_boundary() -> AsyncIterator[AsyncMock]:
        """Supply only an inert ORM double while keeping identity guards real."""
        yield session

    async def business_boundary() -> None:
        """Detect business dependency resolution before authorization succeeds."""
        await business()

    dependency = (
        branches.get_branch_service if module is branches else user.get_user_service
    )
    app.dependency_overrides[get_db] = database_boundary
    app.dependency_overrides[dependency] = business_boundary
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="https://local.test"
    ) as client:
        response = await client.request(
            endpoint.method,
            endpoint.path,
            params={"restaurant_id": 11, "admin_id": 7, "owner_id": 7, "chat_id": 7},
            headers={"Authorization": "Bearer forged-identifier-7"} if bearer else {},
            json={"chat_id": 7, "admin_id": 7, "owner_id": 7, "name": "Intrusion"},
        )
    expected = 401 if configured or (module is branches and not bearer) else 503
    assert response.status_code == expected, response.text
    business.assert_not_awaited()
    session.execute.assert_not_awaited()
    session.scalar.assert_not_awaited()
    session.commit.assert_not_awaited()
    key_lookup.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "endpoint",
    [item for item in ENDPOINTS if item.module == "user"],
    ids=lambda item: f"{item.method}:{item.path}",
)
async def test_global_user_registry_rechecks_admin_permission_for_every_operation(
    monkeypatch: pytest.MonkeyPatch, endpoint: Endpoint
) -> None:
    """A verified identity cannot read or mutate global customer records without RBAC."""
    app = FastAPI()
    app.include_router(user.router)
    check_permission = AsyncMock(side_effect=UnauthorizedError("Permission revoked"))
    monkeypatch.setattr(
        admin_service,
        "AdminService",
        Mock(return_value=Mock(check_admin_permission=check_permission)),
    )
    session = AsyncMock(spec=AsyncSession)
    business = AsyncMock(side_effect=AssertionError("Unauthorized service access"))

    async def principal() -> auth.AdminPrincipal:
        """Represent verified identity while retaining the real permission guard."""
        return auth.AdminPrincipal(admin_id=71)

    async def database_boundary() -> AsyncMock:
        """Keep permission resolution independent of any real database."""
        return session

    async def business_boundary() -> None:
        """Detect any permission bypass before profile access."""
        await business()

    app.dependency_overrides[auth.get_current_admin] = principal
    app.dependency_overrides[get_db] = database_boundary
    app.dependency_overrides[user.get_user_service] = business_boundary
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="https://local.test"
    ) as client:
        response = await client.request(
            endpoint.method, endpoint.path, json={"chat_id": 7}
        )
    assert response.status_code == 403, response.text
    check_permission.assert_awaited_once_with(
        admin_id=71, required_permission="admins.manage"
    )
    business.assert_not_awaited()
    session.execute.assert_not_awaited()


# ==============================================
# REAL SQLITE BRANCH QUERIES AND FOREIGN MUTATIONS
# ==============================================


@pytest.fixture
def branch_database(catalog_database: SQLiteCatalogSession) -> SQLiteCatalogSession:
    """Seed one branch per owner into the shared disposable relational fixture."""
    with catalog_database.sync_session.get_bind().begin() as connection:
        connection.execute(
            Branch.__table__.insert(),
            [
                {"id": 61, "restaurant_id": 11, "name": "Central", "wilaya": "Alger"},
                {"id": 62, "restaurant_id": 12, "name": "Central", "wilaya": "Alger"},
            ],
        )
    catalog_database.info["test_sql_write_verbs"].clear()
    return catalog_database


async def branch_request(
    *, session: SQLiteCatalogSession, method: str, path: str, body: Any = None
) -> Any:
    """Execute actual branch factories and services with verified owner seven."""
    app = catalog_app(module_name="branches", session=session)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="https://local.test"
    ) as client:
        return await client.request(method, "/branches" + path, json=body)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query", ["", "search=Central", "wilaya=Alger", "restaurant_id=11"]
)
async def test_branch_lists_and_totals_execute_owner_scoped_sql(
    branch_database: SQLiteCatalogSession, query: str
) -> None:
    """List, search, regional and restaurant filters return only the current owner."""
    response = await branch_request(
        session=branch_database, method="GET", path="/?" + query
    )
    assert response.status_code == 200, response.text
    assert response.json()["total"] == 1
    assert [row["id"] for row in response.json()["items"]] == [61]
    assert branch_database.info["test_sql_write_verbs"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path,body",
    [
        ("GET", "/62", None),
        ("GET", "/62/cost", None),
        ("PATCH", "/62", {"name": "Intrusion"}),
        ("PATCH", "/62/status", {"is_active": False}),
        ("POST", "/62/activate", None),
        ("POST", "/62/deactivate", None),
        ("DELETE", "/62", None),
        ("DELETE", "/62?permanent=true", None),
    ],
)
async def test_foreign_branch_operations_have_no_data_or_counter_side_effects(
    branch_database: SQLiteCatalogSession,
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
    body: Any,
) -> None:
    """Execute real foreign-ID lookups and deny before branch or usage mutations."""
    increase = AsyncMock()
    decrease = AsyncMock()
    monkeypatch.setattr(branch_service, "increase_usage", increase)
    monkeypatch.setattr(branch_service, "decrease_usage", decrease)
    response = await branch_request(
        session=branch_database, method=method, path=path, body=body
    )
    assert response.status_code == 404, response.text
    increase.assert_not_awaited()
    decrease.assert_not_awaited()
    assert branch_database.info["test_sql_write_verbs"] == []
    with branch_database.sync_session.get_bind().connect() as connection:
        assert (
            connection.execute(select(Branch.name).where(Branch.id == 62)).scalar_one()
            == "Central"
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path,body",
    [
        ("GET", "/?restaurant_id=12", None),
        ("GET", "/?search=Central&restaurant_id=12", None),
        ("GET", "/restaurant/12", None),
        ("GET", "/stats/summary?restaurant_id=12", None),
        ("POST", "/?restaurant_id=12", {"name": "Intrusion"}),
    ],
)
async def test_foreign_restaurant_is_rejected_before_features_or_branch_queries(
    branch_database: SQLiteCatalogSession,
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
    body: Any,
) -> None:
    """An existing foreign restaurant is hidden before quota checks and all writes."""
    feature = AsyncMock()
    increase = AsyncMock()
    monkeypatch.setattr(branch_service, "require_feature", feature)
    monkeypatch.setattr(branch_service, "increase_usage", increase)
    response = await branch_request(
        session=branch_database, method=method, path=path, body=body
    )
    assert response.status_code == 404, response.text
    feature.assert_not_awaited()
    increase.assert_not_awaited()
    assert branch_database.info["test_sql_write_verbs"] == []


@pytest.mark.asyncio
async def test_owned_branch_update_uses_actual_scoped_repository(
    branch_database: SQLiteCatalogSession,
) -> None:
    """An authorized owner can still update their own branch through real SQL."""
    response = await branch_request(
        session=branch_database,
        method="PATCH",
        path="/61",
        body={"name": "Updated central"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["name"] == "Updated central"
    assert "UPDATE" in branch_database.info["test_sql_write_verbs"]
    with branch_database.sync_session.get_bind().connect() as connection:
        assert (
            connection.execute(select(Branch.name).where(Branch.id == 62)).scalar_one()
            == "Central"
        )


# ==============================================
# ENTITLEMENTS, IDEMPOTENCE AND ATOMIC ROLLBACK
# ==============================================


def set_branch_state(*, session: SQLiteCatalogSession, active: bool) -> None:
    """Set trusted fixture state before the request establishes its owner scope."""
    with session.sync_session.get_bind().begin() as connection:
        connection.execute(
            update(Branch).where(Branch.id == 61).values(is_active=active)
        )
    session.info["test_sql_write_verbs"].clear()


@pytest.mark.asyncio
@pytest.mark.parametrize("via_status", [False, True])
@pytest.mark.parametrize(
    "error_code",
    ["no_active_subscription", "feature_not_available", "feature_limit_reached"],
)
async def test_inactive_branch_activation_cannot_bypass_subscription_entitlement(
    branch_database: SQLiteCatalogSession,
    monkeypatch: pytest.MonkeyPatch,
    via_status: bool,
    error_code: str,
) -> None:
    """Both activation entrypoints deny before changing the row or usage counter."""
    set_branch_state(session=branch_database, active=False)
    feature = AsyncMock(side_effect=ValueError(error_code))
    increase = AsyncMock()
    monkeypatch.setattr(branch_service, "require_feature", feature)
    monkeypatch.setattr(branch_service, "increase_usage", increase)
    response = await branch_request(
        session=branch_database,
        method="PATCH" if via_status else "POST",
        path="/61/status" if via_status else "/61/activate",
        body={"is_active": True} if via_status else None,
    )
    assert response.status_code == 403, response.text
    assert response.json()["detail"]["code"] == error_code
    feature.assert_awaited_once_with(
        session=branch_database, restaurant_id=11, feature_id=3
    )
    increase.assert_not_awaited()
    assert branch_database.info["test_sql_write_verbs"] == []


@pytest.mark.asyncio
async def test_branch_activation_enforces_active_branch_capacity(
    branch_database: SQLiteCatalogSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An inactive existing branch cannot evade the maximum active-branch count."""
    set_branch_state(session=branch_database, active=False)
    with branch_database.sync_session.get_bind().begin() as connection:
        connection.execute(
            Branch.__table__.insert(),
            [
                {
                    "id": 70 + index,
                    "restaurant_id": 11,
                    "name": f"Active {index}",
                    "is_active": True,
                }
                for index in range(10)
            ],
        )
    branch_database.info["test_sql_write_verbs"].clear()
    feature = AsyncMock()
    increase = AsyncMock()
    monkeypatch.setattr(branch_service, "require_feature", feature)
    monkeypatch.setattr(branch_service, "increase_usage", increase)
    response = await branch_request(
        session=branch_database, method="POST", path="/61/activate"
    )
    assert response.status_code == 400, response.text
    increase.assert_not_awaited()
    assert branch_database.info["test_sql_write_verbs"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize("activate", [False, True])
async def test_repeated_branch_status_transition_counts_only_once(
    branch_database: SQLiteCatalogSession,
    monkeypatch: pytest.MonkeyPatch,
    activate: bool,
) -> None:
    """Retrying a completed state transition neither double-counts nor rechecks quota."""
    set_branch_state(session=branch_database, active=not activate)
    feature = AsyncMock()
    increase = AsyncMock(return_value=1)
    decrease = AsyncMock(return_value=0)
    monkeypatch.setattr(branch_service, "require_feature", feature)
    monkeypatch.setattr(branch_service, "increase_usage", increase)
    monkeypatch.setattr(branch_service, "decrease_usage", decrease)
    path = "/61/activate" if activate else "/61/deactivate"
    for _ in range(2):
        response = await branch_request(
            session=branch_database, method="POST", path=path
        )
        assert response.status_code == 200, response.text
        assert response.json()["is_active"] is activate
    changed = increase if activate else decrease
    unchanged = decrease if activate else increase
    changed.assert_awaited_once_with(
        session=branch_database, restaurant_id=11, feature_id=3
    )
    unchanged.assert_not_awaited()
    assert feature.await_count == int(activate)
    assert branch_database.info["test_sql_write_verbs"].count("UPDATE") == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("active", [False, True])
@pytest.mark.parametrize("permanent", [False, True])
async def test_branch_deletion_decrements_usage_only_for_active_records(
    branch_database: SQLiteCatalogSession,
    monkeypatch: pytest.MonkeyPatch,
    active: bool,
    permanent: bool,
) -> None:
    """Soft retries and removal of inactive history do not decrement usage again."""
    set_branch_state(session=branch_database, active=active)
    decrease = AsyncMock(return_value=0)
    monkeypatch.setattr(branch_service, "decrease_usage", decrease)
    for _ in range(1 if permanent else 2):
        response = await branch_request(
            session=branch_database,
            method="DELETE",
            path="/61?permanent=" + str(permanent).lower(),
        )
        assert response.status_code == 204, response.text
    assert decrease.await_count == int(active)
    with branch_database.sync_session.get_bind().connect() as connection:
        remaining = connection.execute(
            select(Branch.id).where(Branch.id == 61)
        ).scalar_one_or_none()
    assert (remaining is None) is permanent


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "operation", ["create", "activate", "deactivate", "soft-delete", "hard-delete"]
)
async def test_branch_and_counter_sql_roll_back_together_on_counter_failure(
    branch_database: SQLiteCatalogSession,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    """Roll back actual branch and counter DML, including failures after counter SQL."""
    activating = operation in {"create", "activate"}
    initial_active = not activating
    set_branch_state(session=branch_database, active=initial_active)
    initial_count = int(initial_active)
    with branch_database.sync_session.get_bind().begin() as connection:
        connection.execute(
            FeatureUsageCounter.__table__.insert().values(
                id=71,
                restaurant_id=11,
                feature_id=3,
                period_year=2026,
                period_month=10,
                usage_count=initial_count,
            )
        )
    branch_database.info["test_sql_write_verbs"].clear()

    async def failing_counter(
        *, session: AsyncSession, restaurant_id: int, feature_id: int, amount: int = 1
    ) -> int:
        """Change the real counter inside the branch transaction before failing."""
        await session.execute(
            update(FeatureUsageCounter)
            .where(
                FeatureUsageCounter.restaurant_id == restaurant_id,
                FeatureUsageCounter.feature_id == feature_id,
            )
            .values(usage_count=initial_count + (amount if activating else -amount))
        )
        raise RuntimeError("private-counter-storage-failure")

    monkeypatch.setattr(branch_service, "require_feature", AsyncMock())
    monkeypatch.setattr(
        branch_service,
        "increase_usage" if activating else "decrease_usage",
        failing_counter,
    )
    method, path, body = {
        "create": ("POST", "/?restaurant_id=11", {"name": "New atomic branch"}),
        "activate": ("POST", "/61/activate", None),
        "deactivate": ("POST", "/61/deactivate", None),
        "soft-delete": ("DELETE", "/61", None),
        "hard-delete": ("DELETE", "/61?permanent=true", None),
    }[operation]
    response = await branch_request(
        session=branch_database, method=method, path=path, body=body
    )
    assert response.status_code == 500, response.text
    assert "private-counter-storage-failure" not in response.text
    assert "UPDATE" in branch_database.info["test_sql_write_verbs"]
    with branch_database.sync_session.get_bind().connect() as connection:
        actual_active = connection.execute(
            select(Branch.is_active).where(Branch.id == 61)
        ).scalar_one()
        actual_count = connection.execute(
            select(FeatureUsageCounter.usage_count).where(FeatureUsageCounter.id == 71)
        ).scalar_one()
        new_branch = connection.execute(
            select(Branch.id).where(Branch.name == "New atomic branch")
        ).scalar_one_or_none()
    assert actual_active is initial_active
    assert actual_count == initial_count
    assert new_branch is None
