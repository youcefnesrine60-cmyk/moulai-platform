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
# 📋 TESTS - ORDER COUNTER
# ==============================================

class TestOrderCounterAPI:
    """
    اختبارات نقاط نهاية عداد الطلبات.
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

        # إنشاء مطعم
        self.restaurant = Restaurant(
            **{**sample_restaurant_data, "owner_id": self.owner.id}
        )
        db_session.add(self.restaurant)
        await db_session.flush()
        await db_session.refresh(self.restaurant)

        self.restaurant_id = self.restaurant.id

    # ==============================================
    # TEST INITIALIZE ORDER COUNTER
    # ==============================================

    async def test_initialize_order_counter(
        self,
        client: AsyncClient,
    ) -> None:
        """
        اختبار تهيئة عداد الطلبات.
        
        Args:
            client: عميل HTTP غير متزامن
        """
        response = await client.post(
            f"/api/v1/restaurant-order-counters/{self.restaurant_id}/initialize"
        )
        
        assert response.status_code == 201
        
        data = response.json()
        assert data["restaurant_id"] == self.restaurant_id
        assert data["last_number"] == 0

    # ==============================================
    # TEST GET ORDER COUNTER
    # ==============================================

    async def test_get_order_counter(
        self,
        client: AsyncClient,
    ) -> None:
        """
        اختبار الحصول على عداد الطلبات.
        
        Args:
            client: عميل HTTP غير متزامن
        """
        # تهيئة العداد أولاً
        await client.post(f"/api/v1/restaurant-order-counters/{self.restaurant_id}/initialize")

        response = await client.get(
            f"/api/v1/restaurant-order-counters/{self.restaurant_id}"
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["restaurant_id"] == self.restaurant_id

    # ==============================================
    # TEST GENERATE NEXT ORDER NUMBER
    # ==============================================

    async def test_generate_next_order_number(
        self,
        client: AsyncClient,
    ) -> None:
        """
        اختبار توليد رقم الطلب التالي.
        
        Args:
            client: عميل HTTP غير متزامن
        """
        # تهيئة العداد أولاً
        await client.post(f"/api/v1/restaurant-order-counters/{self.restaurant_id}/initialize")

        response = await client.post(
            f"/api/v1/restaurant-order-counters/{self.restaurant_id}/next"
        )
        
        assert response.status_code == 201
        
        data = response.json()
        assert data["restaurant_id"] == self.restaurant_id
        assert data["next_number"] == 1
        assert data["formatted_number"] == f"RST{self.restaurant_id}-000001"

    # ==============================================
    # TEST INCREMENT ORDER COUNTER
    # ==============================================

    async def test_increment_order_counter(
        self,
        client: AsyncClient,
    ) -> None:
        """
        اختبار زيادة عداد الطلبات.
        
        Args:
            client: عميل HTTP غير متزامن
        """
        # تهيئة العداد أولاً
        await client.post(f"/api/v1/restaurant-order-counters/{self.restaurant_id}/initialize")

        # زيادة العداد
        response = await client.post(
            f"/api/v1/restaurant-order-counters/{self.restaurant_id}/increment"
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["last_number"] == 1


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "TestOrderCounterAPI",
]