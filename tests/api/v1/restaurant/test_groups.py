# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.owner import Owner
from app.models.restaurant import Restaurant


# ==============================================
# 📋 TESTS - RESTAURANT GROUPS
# ==============================================

class TestRestaurantGroupsAPI:
    """
    اختبارات نقاط نهاية مجموعات المطاعم.
    """

    @pytest.fixture(autouse=True)
    async def setup(
        self,
        db_session: AsyncSession,
        sample_owner_data,
        sample_restaurant_data,
    ) -> None:
        """
        تهيئة بيانات الاختبار.
        
        ✅ التصحيح: استخدام flush() بدلاً من commit()
        
        Args:
            db_session: جلسة قاعدة البيانات
            sample_owner_data: بيانات مالك نموذجية
            sample_restaurant_data: بيانات مطعم نموذجية
        """
        # إنشاء مالك
        self.owner = Owner(**sample_owner_data)
        db_session.add(self.owner)
        await db_session.flush()
        await db_session.refresh(self.owner)

        # إنشاء مطاعم للاختبار
        self.restaurants = []
        for i in range(3):
            restaurant = Restaurant(
                **{
                    **sample_restaurant_data,
                    "owner_id": self.owner.id,
                    "name": f"{sample_restaurant_data['name']} {i+1}",
                }
            )
            db_session.add(restaurant)
            self.restaurants.append(restaurant)
        await db_session.flush()
        for r in self.restaurants:
            await db_session.refresh(r)

        self.owner_id = self.owner.id
        self.restaurant_ids = [r.id for r in self.restaurants]

    # ==============================================
    # TEST CREATE GROUP
    # ==============================================

    async def test_create_group(
        self,
        client: AsyncClient,
        sample_group_data,
    ) -> None:
        """
        اختبار إنشاء مجموعة مطاعم.
        
        Args:
            client: عميل HTTP غير متزامن
            sample_group_data: بيانات مجموعة نموذجية
        """
        data = {
            "owner_id": self.owner_id,
            **sample_group_data
        }
        response = await client.post("/api/v1/restaurant-groups/", json=data)
        
        assert response.status_code == 201
        
        data = response.json()
        assert data["name"] == sample_group_data["name"]
        assert data["owner_id"] == self.owner_id

    # ==============================================
    # TEST GET GROUP BY ID
    # ==============================================

    async def test_get_group_by_id(
        self,
        client: AsyncClient,
        sample_group_data,
    ) -> None:
        """
        اختبار الحصول على مجموعة مطاعم بالمعرف.
        
        Args:
            client: عميل HTTP غير متزامن
            sample_group_data: بيانات مجموعة نموذجية
        """
        # إنشاء مجموعة أولاً
        create_data = {"owner_id": self.owner_id, **sample_group_data}
        create_response = await client.post(
            "/api/v1/restaurant-groups/",
            json=create_data,
        )
        group_id = create_response.json()["id"]

        response = await client.get(f"/api/v1/restaurant-groups/{group_id}")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == group_id
        assert data["name"] == sample_group_data["name"]

    # ==============================================
    # TEST ADD BRANCHES TO GROUP
    # ==============================================

    async def test_add_branches_to_group(
        self,
        client: AsyncClient,
        sample_group_data,
    ) -> None:
        """
        اختبار إضافة فروع إلى مجموعة.
        
        Args:
            client: عميل HTTP غير متزامن
            sample_group_data: بيانات مجموعة نموذجية
        """
        # إنشاء مجموعة أولاً
        create_data = {"owner_id": self.owner_id, **sample_group_data}
        create_response = await client.post(
            "/api/v1/restaurant-groups/",
            json=create_data,
        )
        group_id = create_response.json()["id"]

        # إضافة فروع
        data = {
            "group_id": group_id,
            "restaurant_ids": self.restaurant_ids
        }
        response = await client.post(
            f"/api/v1/restaurant-groups/{group_id}/branches",
            json=data
        )
        
        assert response.status_code == 201
        
        branches = response.json()
        assert len(branches) == len(self.restaurant_ids)

    # ==============================================
    # TEST REMOVE BRANCH FROM GROUP
    # ==============================================

    async def test_remove_branch_from_group(
        self,
        client: AsyncClient,
        sample_group_data,
    ) -> None:
        """
        اختبار إزالة فرع من مجموعة.
        
        Args:
            client: عميل HTTP غير متزامن
            sample_group_data: بيانات مجموعة نموذجية
        """
        # إنشاء مجموعة أولاً
        create_data = {"owner_id": self.owner_id, **sample_group_data}
        create_response = await client.post(
            "/api/v1/restaurant-groups/",
            json=create_data,
        )
        group_id = create_response.json()["id"]

        # إضافة فروع
        data = {"group_id": group_id, "restaurant_ids": self.restaurant_ids}
        await client.post(f"/api/v1/restaurant-groups/{group_id}/branches", json=data)

        # إزالة فرع
        restaurant_id = self.restaurant_ids[0]
        response = await client.delete(
            f"/api/v1/restaurant-groups/{group_id}/branches/{restaurant_id}"
        )
        
        assert response.status_code == 204


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "TestRestaurantGroupsAPI",
]