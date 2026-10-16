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

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

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
        self.restaurant_id = restaurant.id

    async def test_category_crud_lifecycle(self, client: AsyncClient) -> None:
        """Create, read, update, list, and delete one category."""
        created = await client.post(
            f"/api/v1/categories/?restaurant_id={self.restaurant_id}",
            json={"name": "Pizza", "description": "Fresh pizzas", "sort_order": 2},
        )
        assert created.status_code == 201
        category = created.json()
        assert category["restaurant_id"] == self.restaurant_id

        category_id = category["id"]
        fetched = await client.get(f"/api/v1/categories/{category_id}")
        assert fetched.status_code == 200
        assert fetched.json()["name"] == "Pizza"

        updated = await client.patch(
            f"/api/v1/categories/{category_id}", json={"name": "Pizza special"}
        )
        assert updated.status_code == 200
        assert updated.json()["name"] == "Pizza special"

        listed = await client.get(f"/api/v1/categories/restaurant/{self.restaurant_id}")
        assert listed.status_code == 200
        assert [item["id"] for item in listed.json()["items"]] == [category_id]

        deleted = await client.delete(f"/api/v1/categories/{category_id}")
        assert deleted.status_code == 204
        assert (
            await client.get(f"/api/v1/categories/{category_id}")
        ).status_code == 404

    async def test_category_list_is_scoped_to_restaurant(
        self, client: AsyncClient
    ) -> None:
        """Ensure a restaurant list does not expose another restaurant's category."""
        first = await client.post(
            f"/api/v1/categories/?restaurant_id={self.restaurant_id}",
            json={"name": "First", "sort_order": 1},
        )
        assert first.status_code == 201
        other = await client.get("/api/v1/categories/restaurant/999999")
        assert other.status_code == 200
        assert other.json()["items"] == []

    async def test_missing_category_returns_not_found(
        self, client: AsyncClient
    ) -> None:
        """Return a stable 404 for a category that does not exist."""
        response = await client.get("/api/v1/categories/999999")
        assert response.status_code == 404
