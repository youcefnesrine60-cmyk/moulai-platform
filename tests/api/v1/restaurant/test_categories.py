# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# TEST MODULE - CATEGORY API
# Regression coverage for SQLAlchemy category flows.
# ==============================================

"""Integration tests for category API CRUD and restaurant scoping."""

from collections.abc import AsyncIterator

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import (
    OwnerPrincipal,
    get_current_owner,
)
from app.main import app
from app.models.category import Category
from app.models.owner import Owner
from app.models.restaurant import Restaurant


class TestCategoriesAPI:
    """Verify category endpoints against the asynchronous test database."""

    @pytest.fixture(autouse=True)
    async def setup(
        self,
        db_session: AsyncSession,
        sample_owner_data: dict[str, object],
        sample_restaurant_data: dict[str, object],
    ) -> None:
        """Create an owner and an isolated restaurant for every test."""
        owner = Owner(**sample_owner_data)
        db_session.add(owner)
        await db_session.commit()
        restaurant = Restaurant(**{**sample_restaurant_data, "owner_id": owner.id})
        db_session.add(restaurant)
        await db_session.commit()
        self.owner_id = owner.id
        self.restaurant_id = restaurant.id

    @pytest.fixture
    async def owner_client(self, client: AsyncClient) -> AsyncIterator[AsyncClient]:
        """Substitute verified identity only for explicitly authorized CRUD cases.

        The actual request dependency still binds its real async database
        session. Anonymous cases use the original client without this fixture.
        No identity or administrator permission is created in storage.
        """

        async def authenticated_owner() -> OwnerPrincipal:
            """Resolve the owner seeded by this test's isolated database setup."""
            return OwnerPrincipal(owner_id=self.owner_id)

        previous = app.dependency_overrides.get(get_current_owner)
        app.dependency_overrides[get_current_owner] = authenticated_owner
        try:
            yield client
        finally:
            if previous is None:
                app.dependency_overrides.pop(get_current_owner, None)
            else:
                app.dependency_overrides[get_current_owner] = previous

    async def test_category_crud_lifecycle(self, owner_client: AsyncClient) -> None:
        """Create, read, update, list, and delete one category."""
        created = await owner_client.post(
            f"/api/v1/categories/?restaurant_id={self.restaurant_id}",
            json={"name": "Pizza", "description": "Fresh pizzas", "sort_order": 2},
        )
        assert created.status_code == 201
        category = created.json()
        assert category["restaurant_id"] == self.restaurant_id

        category_id = category["id"]
        fetched = await owner_client.get(f"/api/v1/categories/{category_id}")
        assert fetched.status_code == 200
        assert fetched.json()["name"] == "Pizza"

        updated = await owner_client.patch(
            f"/api/v1/categories/{category_id}", json={"name": "Pizza special"}
        )
        assert updated.status_code == 200
        assert updated.json()["name"] == "Pizza special"

        listed = await owner_client.get(
            f"/api/v1/categories/restaurant/{self.restaurant_id}"
        )
        assert listed.status_code == 200
        assert [item["id"] for item in listed.json()["items"]] == [category_id]

        deleted = await owner_client.delete(f"/api/v1/categories/{category_id}")
        assert deleted.status_code == 204
        assert (
            await owner_client.get(f"/api/v1/categories/{category_id}")
        ).status_code == 404

    async def test_category_list_is_scoped_to_restaurant(
        self, owner_client: AsyncClient
    ) -> None:
        """Ensure a restaurant list does not expose another restaurant's category."""
        first = await owner_client.post(
            f"/api/v1/categories/?restaurant_id={self.restaurant_id}",
            json={"name": "First", "sort_order": 1},
        )
        assert first.status_code == 201
        other = await owner_client.get("/api/v1/categories/restaurant/999999")
        assert other.status_code == 200
        assert other.json()["items"] == []

    async def test_missing_category_returns_not_found(
        self, owner_client: AsyncClient
    ) -> None:
        """Return a stable 404 for a category that does not exist."""
        response = await owner_client.get("/api/v1/categories/999999")
        assert response.status_code == 404

    async def test_anonymous_category_creation_remains_unauthorized(
        self, client: AsyncClient
    ) -> None:
        """An administrative business fixture must not authorize owner routes."""
        response = await client.post(
            f"/api/v1/categories/?restaurant_id={self.restaurant_id}",
            json={"name": "Unauthenticated category"},
        )
        assert response.status_code == 401

    async def test_authenticated_owner_cannot_access_foreign_categories(
        self, owner_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Real stored foreign resources stay hidden across CRUD operations."""
        foreign_owner = Owner(chat_id=999_000_002, full_name="Foreign test owner")
        db_session.add(foreign_owner)
        await db_session.flush()
        foreign_restaurant = Restaurant(
            owner_id=foreign_owner.id,
            name="Foreign restaurant",
            type="restaurant",
            phone="0555000000",
            wilaya="Test",
        )
        db_session.add(foreign_restaurant)
        await db_session.flush()
        category = Category(
            restaurant_id=foreign_restaurant.id, name="Private category"
        )
        db_session.add(category)
        await db_session.commit()

        assert (
            await owner_client.get(f"/api/v1/categories/{category.id}")
        ).status_code == 404
        assert (
            await owner_client.patch(
                f"/api/v1/categories/{category.id}",
                json={"name": "Forbidden change"},
            )
        ).status_code == 404
        assert (
            await owner_client.delete(f"/api/v1/categories/{category.id}")
        ).status_code == 404
        created = await owner_client.post(
            f"/api/v1/categories/?restaurant_id={foreign_restaurant.id}",
            json={"name": "Forbidden creation"},
        )
        assert created.status_code == 404
        await db_session.refresh(category)
        assert category.name == "Private category"
