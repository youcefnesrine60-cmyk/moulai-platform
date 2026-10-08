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
# 📋 TESTS - METRICS
# ==============================================

class TestMetricsAPI:
    """
    اختبارات نقاط نهاية مقاييس المطعم.
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
        # Seed IDs are retained after commit; do not reopen an idle read transaction.
        self.owner = Owner(**sample_owner_data)
        db_session.add(self.owner)
        await db_session.commit()

        # إنشاء مطعم
        self.restaurant = Restaurant(
            **{**sample_restaurant_data, "owner_id": self.owner.id}
        )
        db_session.add(self.restaurant)
        await db_session.commit()

        self.restaurant_id = self.restaurant.id

    # ==============================================
    # TEST INITIALIZE METRICS
    # ==============================================

    async def test_initialize_metrics(
        self,
        client: AsyncClient,
    ) -> None:
        """
        اختبار تهيئة مقاييس المطعم.
        
        Args:
            client: عميل HTTP غير متزامن
        """
        response = await client.post(
            f"/api/v1/restaurant-metrics/{self.restaurant_id}/initialize"
        )
        
        assert response.status_code == 201
        
        data = response.json()
        assert data["restaurant_id"] == self.restaurant_id
        assert data["products_count"] == 0
        assert data["categories_count"] == 0
        assert data["monthly_orders"] == 0
        assert data["average_order_value"] == 0

    # ==============================================
    # TEST GET METRICS
    # ==============================================

    async def test_get_metrics(
        self,
        client: AsyncClient,
    ) -> None:
        """
        اختبار الحصول على مقاييس المطعم.
        
        Args:
            client: عميل HTTP غير متزامن
        """
        # تهيئة المقاييس أولاً
        await client.post(f"/api/v1/restaurant-metrics/{self.restaurant_id}/initialize")

        response = await client.get(f"/api/v1/restaurant-metrics/{self.restaurant_id}")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["restaurant_id"] == self.restaurant_id

    # ==============================================
    # TEST UPDATE METRICS
    # ==============================================

    async def test_update_metrics(
        self,
        client: AsyncClient,
        sample_metric_data,
    ) -> None:
        """
        اختبار تحديث مقاييس المطعم.
        
        Args:
            client: عميل HTTP غير متزامن
            sample_metric_data: بيانات مقاييس نموذجية
        """
        # تهيئة المقاييس أولاً
        await client.post(f"/api/v1/restaurant-metrics/{self.restaurant_id}/initialize")

        response = await client.patch(
            f"/api/v1/restaurant-metrics/{self.restaurant_id}",
            json=sample_metric_data
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["products_count"] == sample_metric_data["products_count"]
        assert data["categories_count"] == sample_metric_data["categories_count"]

    # ==============================================
    # TEST GET METRICS SUMMARY
    # ==============================================

    async def test_get_metrics_summary(
        self,
        client: AsyncClient,
    ) -> None:
        """
        اختبار الحصول على ملخص مقاييس المطعم.
        
        Args:
            client: عميل HTTP غير متزامن
        """
        # تهيئة المقاييس أولاً
        await client.post(f"/api/v1/restaurant-metrics/{self.restaurant_id}/initialize")

        response = await client.get(
            f"/api/v1/restaurant-metrics/{self.restaurant_id}/summary"
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["restaurant_id"] == self.restaurant_id

    # ==============================================
    # TEST RESET METRICS
    # ==============================================

    async def test_reset_metrics(
        self,
        client: AsyncClient,
    ) -> None:
        """
        اختبار إعادة تعيين مقاييس المطعم.
        
        Args:
            client: عميل HTTP غير متزامن
        """
        # تهيئة المقاييس أولاً
        await client.post(f"/api/v1/restaurant-metrics/{self.restaurant_id}/initialize")

        response = await client.post(
            f"/api/v1/restaurant-metrics/{self.restaurant_id}/reset"
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["products_count"] == 0
        assert data["categories_count"] == 0
        assert data["monthly_orders"] == 0
        assert data["average_order_value"] == 0


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "TestMetricsAPI",
]