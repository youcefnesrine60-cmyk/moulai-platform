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
from app.models.restaurant_group import RestaurantGroup


# ==============================================
# 📋 TESTS - RESTAURANT BRANCHES
# ==============================================

class TestRestaurantBranchesAPI:
    """
    اختبارات نقاط نهاية فروع المطاعم.
    """

    @pytest.fixture(autouse=True)
    async def setup(
        self,
        db_session: AsyncSession,
        sample_owner_data,
        sample_restaurant_data,
        sample_group_data,
    ) -> None:
        """
        تهيئة بيانات الاختبار.
        
        ✅ التصحيح: استخدام flush() بدلاً من commit()
        
        Args:
            db_session: جلسة قاعدة البيانات
            sample_owner_data: بيانات مالك نموذجية
            sample_restaurant_data: بيانات مطعم نموذجية
            sample_group_data: بيانات مجموعة نموذجية
        """
        self.db_session = db_session
        self.sample_restaurant_data = sample_restaurant_data
        self.sample_group_data = sample_group_data

        # إنشاء مالك
        self.owner = Owner(**sample_owner_data)
        db_session.add(self.owner)
        await db_session.flush()
        await db_session.refresh(self.owner)

        # إنشاء مطعم
        self.restaurant = Restaurant(
            **{**sample_restaurant_data, "owner_id": self.owner.id}
        )
        db_session.add(self.restaurant)
        await db_session.flush()
        await db_session.refresh(self.restaurant)

        # إنشاء مجموعة
        self.group = RestaurantGroup(
            **{**sample_group_data, "owner_id": self.owner.id}
        )
        db_session.add(self.group)
        await db_session.flush()
        await db_session.refresh(self.group)

        self.restaurant_id = self.restaurant.id
        self.group_id = self.group.id

    # ==============================================
    # TEST CREATE BRANCH
    # ==============================================

    async def test_create_branch(
        self,
        client: AsyncClient,
    ) -> None:
        """
        اختبار إنشاء فرع مطعم.
        
        Args:
            client: عميل HTTP غير متزامن
        """
        data = {
            "group_id": self.group_id,
            "restaurant_id": self.restaurant_id,
        }
        response = await client.post("/api/v1/restaurant-branches/", json=data)
        
        assert response.status_code == 201
        
        data = response.json()
        assert data["group_id"] == self.group_id
        assert data["restaurant_id"] == self.restaurant_id

    # ==============================================
    # TEST GET BRANCH BY ID
    # ==============================================

    async def test_get_branch_by_id(
        self,
        client: AsyncClient,
    ) -> None:
        """
        اختبار الحصول على فرع مطعم بالمعرف.
        
        Args:
            client: عميل HTTP غير متزامن
        """
        # إنشاء فرع أولاً
        create_data = {
            "group_id": self.group_id,
            "restaurant_id": self.restaurant_id,
        }
        create_response = await client.post(
            "/api/v1/restaurant-branches/",
            json=create_data,
        )
        branch_id = create_response.json()["id"]

        response = await client.get(f"/api/v1/restaurant-branches/{branch_id}")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == branch_id
        assert data["group_id"] == self.group_id
        assert data["restaurant_id"] == self.restaurant_id

    # ==============================================
    # TEST GET BRANCH WITH DETAILS
    # ==============================================

    async def test_get_branch_with_details(
        self,
        client: AsyncClient,
    ) -> None:
        """
        اختبار الحصول على فرع مطعم مع تفاصيله.
        
        Args:
            client: عميل HTTP غير متزامن
        """
        # إنشاء فرع أولاً
        create_data = {
            "group_id": self.group_id,
            "restaurant_id": self.restaurant_id,
        }
        create_response = await client.post(
            "/api/v1/restaurant-branches/",
            json=create_data,
        )
        branch_id = create_response.json()["id"]

        response = await client.get(
            f"/api/v1/restaurant-branches/{branch_id}/details",
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == branch_id
        assert data["group_id"] == self.group_id
        assert data["restaurant_id"] == self.restaurant_id

    # ==============================================
    # TEST LIST BRANCHES BY GROUP
    # ==============================================

    async def test_list_branches_by_group(
        self,
        client: AsyncClient,
    ) -> None:
        """
        اختبار جلب فروع مجموعة معينة.
        
        Args:
            client: عميل HTTP غير متزامن
        """
        # إنشاء فرع أولاً
        create_data = {
            "group_id": self.group_id,
            "restaurant_id": self.restaurant_id,
        }
        await client.post("/api/v1/restaurant-branches/", json=create_data)

        response = await client.get(
            f"/api/v1/restaurant-branches/group/{self.group_id}",
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1
        assert data["items"][0]["group_id"] == self.group_id

    # ==============================================
    # TEST LIST BRANCHES BY RESTAURANT
    # ==============================================

    async def test_list_branches_by_restaurant(
        self,
        client: AsyncClient,
    ) -> None:
        """
        اختبار جلب فروع مطعم معين.
        
        Args:
            client: عميل HTTP غير متزامن
        """
        # إنشاء فرع أولاً
        create_data = {
            "group_id": self.group_id,
            "restaurant_id": self.restaurant_id,
        }
        await client.post("/api/v1/restaurant-branches/", json=create_data)

        response = await client.get(
            f"/api/v1/restaurant-branches/restaurant/{self.restaurant_id}",
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1
        assert data["items"][0]["restaurant_id"] == self.restaurant_id

    # ==============================================
    # TEST GET BRANCH NOT FOUND
    # ==============================================

    async def test_get_branch_not_found(
        self,
        client: AsyncClient,
    ) -> None:
        """
        اختبار الحصول على فرع غير موجود.
        
        Args:
            client: عميل HTTP غير متزامن
        """
        response = await client.get("/api/v1/restaurant-branches/9999")
        
        assert response.status_code == 404

    # ==============================================
    # TEST CREATE DUPLICATE BRANCH
    # ==============================================

    async def test_create_duplicate_branch(
        self,
        client: AsyncClient,
    ) -> None:
        """
        اختبار إنشاء فرع مكرر.
        
        Args:
            client: عميل HTTP غير متزامن
        """
        data = {
            "group_id": self.group_id,
            "restaurant_id": self.restaurant_id,
        }
        # إنشاء فرع أولاً
        await client.post("/api/v1/restaurant-branches/", json=data)

        # محاولة إنشاء فرع مكرر
        response = await client.post("/api/v1/restaurant-branches/", json=data)
        
        assert response.status_code == 409

    # ==============================================
    # TEST DELETE BRANCH
    # ==============================================

    async def test_delete_branch(
        self,
        client: AsyncClient,
    ) -> None:
        """
        اختبار حذف فرع مطعم.
        
        Args:
            client: عميل HTTP غير متزامن
        """
        # إنشاء فرع أولاً
        create_data = {
            "group_id": self.group_id,
            "restaurant_id": self.restaurant_id,
        }
        create_response = await client.post(
            "/api/v1/restaurant-branches/",
            json=create_data,
        )
        branch_id = create_response.json()["id"]

        # حذف الفرع
        response = await client.delete(f"/api/v1/restaurant-branches/{branch_id}")
        assert response.status_code == 204

        # التحقق من الحذف
        get_response = await client.get(f"/api/v1/restaurant-branches/{branch_id}")
        assert get_response.status_code == 404

    # ==============================================
    # TEST DELETE BRANCH NOT FOUND
    # ==============================================

    async def test_delete_branch_not_found(
        self,
        client: AsyncClient,
    ) -> None:
        """
        اختبار حذف فرع غير موجود.
        
        Args:
            client: عميل HTTP غير متزامن
        """
        response = await client.delete("/api/v1/restaurant-branches/9999")
        
        assert response.status_code == 404

    # ==============================================
    # TEST CREATE BRANCH WITH NON-EXISTENT GROUP
    # ==============================================

    async def test_create_branch_non_existent_group(
        self,
        client: AsyncClient,
    ) -> None:
        """
        اختبار إنشاء فرع بمجموعة غير موجودة.
        
        Args:
            client: عميل HTTP غير متزامن
        """
        data = {
            "group_id": 9999,
            "restaurant_id": self.restaurant_id,
        }
        response = await client.post("/api/v1/restaurant-branches/", json=data)
        
        assert response.status_code == 404

    # ==============================================
    # TEST CREATE BRANCH WITH NON-EXISTENT RESTAURANT
    # ==============================================

    async def test_create_branch_non_existent_restaurant(
        self,
        client: AsyncClient,
    ) -> None:
        """
        اختبار إنشاء فرع بمطعم غير موجود.
        
        Args:
            client: عميل HTTP غير متزامن
        """
        data = {
            "group_id": self.group_id,
            "restaurant_id": 9999,
        }
        response = await client.post("/api/v1/restaurant-branches/", json=data)
        
        assert response.status_code == 404

    # ==============================================
    # TEST LIST BRANCHES BY GROUP WITH PAGINATION
    # ==============================================

    async def test_list_branches_by_group_with_pagination(
        self,
        client: AsyncClient,
    ) -> None:
        """
        اختبار جلب فروع مجموعة معينة مع التصفح.
        
        Args:
            client: عميل HTTP غير متزامن
        """
        # إنشاء فروع متعددة
        restaurant_ids = []
        for i in range(5):
            restaurant = Restaurant(
                **{
                    **self.sample_restaurant_data,
                    "owner_id": self.owner.id,
                    "name": f"مطعم {i+1}",
                }
            )
            self.db_session.add(restaurant)
            restaurant_ids.append(restaurant.id)
        await self.db_session.flush()

        # إضافة الفروع إلى المجموعة
        for rid in restaurant_ids:
            data = {"group_id": self.group_id, "restaurant_id": rid}
            await client.post("/api/v1/restaurant-branches/", json=data)

        # اختبار التصفح
        response = await client.get(
            f"/api/v1/restaurant-branches/group/{self.group_id}",
            params={"skip": 0, "limit": 3},
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 3
        assert data["skip"] == 0
        assert data["limit"] == 3

        # اختبار الصفحة الثانية
        response = await client.get(
            f"/api/v1/restaurant-branches/group/{self.group_id}",
            params={"skip": 3, "limit": 3},
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["skip"] == 3
        assert data["limit"] == 3


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "TestRestaurantBranchesAPI",
]