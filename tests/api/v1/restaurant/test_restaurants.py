# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🧪 TEST RESTAURANTS API
# اختبارات واجهات برمجة التطبيقات للمطاعم
# ==============================================

from typing import (
    Any,
    Dict,
)

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


# ==============================================
# 🏪 TEST RESTAURANTS API
# ==============================================

class TestRestaurantsAPI:
    """
    اختبارات نقاط نهاية المطاعم.
    
    تختبر جميع عمليات CRUD للمطاعم:
        - إنشاء مطعم
        - قراءة مطعم
        - تحديث مطعم
        - حذف مطعم
        - إحصائيات المطاعم
    """

    @pytest.fixture(autouse=True)
    async def setup(
        self,
        db_session: AsyncSession,
    ) -> None:
        """
        تهيئة بيانات الاختبار.
        
        Args:
            db_session: جلسة قاعدة البيانات غير المتزامنة
        """
        self.db_session = db_session

    # ==========================================
    # 🔧 HELPER FUNCTIONS
    # ==========================================

    async def _create_test_owner_via_api(
        self,
        client: AsyncClient,
        sample_owner_data: Dict[str, Any],
    ) -> int:
        """
        إنشاء مالك عبر API.
        
        ✅ استخدام API بدلاً من DB المباشر
        
        Args:
            client: عميل HTTP غير متزامن
            sample_owner_data: بيانات المالك
            
        Returns:
            int: معرف المالك المنشأ
        """
        response = await client.post("/api/v1/owners/", json=sample_owner_data)
        
        # إذا فشل الإنشاء، نحاول مرة أخرى مع بيانات فريدة
        if response.status_code != 201:
            # تعديل البيانات لجعلها فريدة
            import time
            unique_id = int(time.time() * 1000) % 1000000000
            sample_owner_data["chat_id"] = unique_id
            sample_owner_data["email"] = f"owner_{unique_id}@example.com"
            response = await client.post("/api/v1/owners/", json=sample_owner_data)
            
        assert response.status_code == 201
        return response.json()["id"]

    # ==========================================
    # 📖 GET ENDPOINTS TESTS
    # ==========================================

    @pytest.mark.asyncio
    async def test_list_restaurants_empty(
        self,
        client: AsyncClient,
    ) -> None:
        """
        اختبار جلب قائمة المطاعم عندما تكون فارغة.
        
        Args:
            client: عميل HTTP غير متزامن للاختبار
        """
        response = await client.get("/api/v1/restaurants/")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_list_restaurants_with_data(
        self,
        client: AsyncClient,
        sample_restaurant_data: Dict[str, Any],
        sample_owner_data: Dict[str, Any],
    ) -> None:
        """
        اختبار جلب قائمة المطاعم عندما تحتوي على بيانات.
        
        Args:
            client: عميل HTTP غير متزامن للاختبار
            sample_restaurant_data: بيانات مطعم نموذجية
            sample_owner_data: بيانات مالك نموذجية
        """
        owner_id: int = await self._create_test_owner_via_api(
            client=client,
            sample_owner_data=sample_owner_data,
        )

        data: Dict[str, Any] = {
            **sample_restaurant_data,
            "owner_id": owner_id,
        }
        await client.post("/api/v1/restaurants/", json=data)

        second_restaurant: Dict[str, Any] = {
            **sample_restaurant_data,
            "name": "مطعم الشرق الأوسط",
            "owner_id": owner_id,
        }
        await client.post("/api/v1/restaurants/", json=second_restaurant)

        response = await client.get("/api/v1/restaurants/")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] >= 2
        assert len(data["items"]) >= 2

    # ==========================================
    # 📥 CREATE ENDPOINT TESTS
    # ==========================================

    @pytest.mark.asyncio
    async def test_create_restaurant_success(
        self,
        client: AsyncClient,
        sample_restaurant_data: Dict[str, Any],
        sample_owner_data: Dict[str, Any],
    ) -> None:
        """
        اختبار إنشاء مطعم جديد بنجاح.
        
        Args:
            client: عميل HTTP غير متزامن للاختبار
            sample_restaurant_data: بيانات مطعم نموذجية
            sample_owner_data: بيانات مالك نموذجية
        """
        owner_id: int = await self._create_test_owner_via_api(
            client=client,
            sample_owner_data=sample_owner_data,
        )

        data: Dict[str, Any] = {
            **sample_restaurant_data,
            "owner_id": owner_id,
        }
        response = await client.post("/api/v1/restaurants/", json=data)

        assert response.status_code == 201
        
        data = response.json()
        assert data["name"] == sample_restaurant_data["name"]
        assert data["owner_id"] == owner_id
        assert data["is_active"] is True
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_restaurant_duplicate_name(
        self,
        client: AsyncClient,
        sample_restaurant_data: Dict[str, Any],
        sample_owner_data: Dict[str, Any],
    ) -> None:
        """
        اختبار إنشاء مطعم باسم مكرر.
        
        Args:
            client: عميل HTTP غير متزامن للاختبار
            sample_restaurant_data: بيانات مطعم نموذجية
            sample_owner_data: بيانات مالك نموذجية
        """
        owner_id: int = await self._create_test_owner_via_api(
            client=client,
            sample_owner_data=sample_owner_data,
        )

        data: Dict[str, Any] = {
            **sample_restaurant_data,
            "owner_id": owner_id,
        }
        await client.post("/api/v1/restaurants/", json=data)

        response = await client.post("/api/v1/restaurants/", json=data)
        
        assert response.status_code == 409
        assert "موجود مسبقاً" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_restaurant_invalid_data(
        self,
        client: AsyncClient,
        sample_owner_data: Dict[str, Any],
    ) -> None:
        """
        اختبار إنشاء مطعم ببيانات غير صالحة.
        
        Args:
            client: عميل HTTP غير متزامن للاختبار
            sample_owner_data: بيانات مالك نموذجية
        """
        owner_id: int = await self._create_test_owner_via_api(
            client=client,
            sample_owner_data=sample_owner_data,
        )

        data: Dict[str, Any] = {
            "owner_id": owner_id,
            "name": "",
            "type": "invalid_type",
            "phone": "123",
        }
        response = await client.post("/api/v1/restaurants/", json=data)
        
        assert response.status_code == 422

    # ==========================================
    # 📖 GET BY ID ENDPOINT TESTS
    # ==========================================

    @pytest.mark.asyncio
    async def test_get_restaurant_by_id_success(
        self,
        client: AsyncClient,
        sample_restaurant_data: Dict[str, Any],
        sample_owner_data: Dict[str, Any],
    ) -> None:
        """
        اختبار الحصول على مطعم بالمعرف بنجاح.
        
        Args:
            client: عميل HTTP غير متزامن للاختبار
            sample_restaurant_data: بيانات مطعم نموذجية
            sample_owner_data: بيانات مالك نموذجية
        """
        owner_id: int = await self._create_test_owner_via_api(
            client=client,
            sample_owner_data=sample_owner_data,
        )

        data: Dict[str, Any] = {
            **sample_restaurant_data,
            "owner_id": owner_id,
        }
        create_response = await client.post("/api/v1/restaurants/", json=data)
        
        assert create_response.status_code == 201
        
        restaurant_id: int = create_response.json()["id"]

        response = await client.get(f"/api/v1/restaurants/{restaurant_id}")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == restaurant_id
        assert data["name"] == sample_restaurant_data["name"]

    @pytest.mark.asyncio
    async def test_get_restaurant_by_id_not_found(
        self,
        client: AsyncClient,
    ) -> None:
        """
        اختبار الحصول على مطعم غير موجود.
        
        Args:
            client: عميل HTTP غير متزامن للاختبار
        """
        response = await client.get("/api/v1/restaurants/99999")
        
        assert response.status_code == 404
        assert "غير موجود" in response.json()["detail"]

    # ==========================================
    # ✏️ UPDATE ENDPOINT TESTS
    # ==========================================

    @pytest.mark.asyncio
    async def test_update_restaurant_success(
        self,
        client: AsyncClient,
        sample_restaurant_data: Dict[str, Any],
        sample_owner_data: Dict[str, Any],
    ) -> None:
        """
        اختبار تحديث مطعم بنجاح.
        
        Args:
            client: عميل HTTP غير متزامن للاختبار
            sample_restaurant_data: بيانات مطعم نموذجية
            sample_owner_data: بيانات مالك نموذجية
        """
        owner_id: int = await self._create_test_owner_via_api(
            client=client,
            sample_owner_data=sample_owner_data,
        )

        data: Dict[str, Any] = {
            **sample_restaurant_data,
            "owner_id": owner_id,
        }
        create_response = await client.post("/api/v1/restaurants/", json=data)
        
        assert create_response.status_code == 201
        
        restaurant_id: int = create_response.json()["id"]

        update_data: Dict[str, Any] = {"name": "مطعم البيتزا الذهبية - فرع 2"}
        response = await client.patch(
            f"/api/v1/restaurants/{restaurant_id}",
            json=update_data,
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == restaurant_id
        assert data["name"] == update_data["name"]

    @pytest.mark.asyncio
    async def test_update_restaurant_not_found(
        self,
        client: AsyncClient,
    ) -> None:
        """
        اختبار تحديث مطعم غير موجود.
        
        Args:
            client: عميل HTTP غير متزامن للاختبار
        """
        update_data: Dict[str, Any] = {"name": "مطعم جديد"}
        response = await client.patch("/api/v1/restaurants/99999", json=update_data)
        
        assert response.status_code == 404

    # ==========================================
    # 🔄 STATUS TOGGLE ENDPOINT TESTS
    # ==========================================

    @pytest.mark.asyncio
    async def test_toggle_restaurant_status_success(
        self,
        client: AsyncClient,
        sample_restaurant_data: Dict[str, Any],
        sample_owner_data: Dict[str, Any],
    ) -> None:
        """
        اختبار تبديل حالة المطعم بنجاح.
        
        Args:
            client: عميل HTTP غير متزامن للاختبار
            sample_restaurant_data: بيانات مطعم نموذجية
            sample_owner_data: بيانات مالك نموذجية
        """
        owner_id: int = await self._create_test_owner_via_api(
            client=client,
            sample_owner_data=sample_owner_data,
        )

        data: Dict[str, Any] = {
            **sample_restaurant_data,
            "owner_id": owner_id,
        }
        create_response = await client.post("/api/v1/restaurants/", json=data)
        
        assert create_response.status_code == 201
        
        restaurant_id: int = create_response.json()["id"]

        response = await client.patch(
            f"/api/v1/restaurants/{restaurant_id}/status",
            params={"is_active": False},
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["is_active"] is False

        response = await client.patch(
            f"/api/v1/restaurants/{restaurant_id}/status",
            params={"is_active": True},
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_toggle_restaurant_status_not_found(
        self,
        client: AsyncClient,
    ) -> None:
        """
        اختبار تبديل حالة مطعم غير موجود.
        
        Args:
            client: عميل HTTP غير متزامن للاختبار
        """
        response = await client.patch(
            "/api/v1/restaurants/99999/status",
            params={"is_active": False},
        )
        
        assert response.status_code == 404

    # ==========================================
    # 🗑️ DELETE ENDPOINT TESTS
    # ==========================================

    @pytest.mark.asyncio
    async def test_delete_restaurant_soft(
        self,
        client: AsyncClient,
        sample_restaurant_data: Dict[str, Any],
        sample_owner_data: Dict[str, Any],
    ) -> None:
        """
        اختبار الحذف المنطقي للمطعم.
        
        Args:
            client: عميل HTTP غير متزامن للاختبار
            sample_restaurant_data: بيانات مطعم نموذجية
            sample_owner_data: بيانات مالك نموذجية
        """
        owner_id: int = await self._create_test_owner_via_api(
            client=client,
            sample_owner_data=sample_owner_data,
        )

        data: Dict[str, Any] = {
            **sample_restaurant_data,
            "owner_id": owner_id,
        }
        create_response = await client.post("/api/v1/restaurants/", json=data)
        
        assert create_response.status_code == 201
        
        restaurant_id: int = create_response.json()["id"]

        response = await client.delete(
            f"/api/v1/restaurants/{restaurant_id}",
            params={"permanent": False},
        )
        assert response.status_code == 204

        response = await client.get(f"/api/v1/restaurants/{restaurant_id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_restaurant_permanent(
        self,
        client: AsyncClient,
        sample_restaurant_data: Dict[str, Any],
        sample_owner_data: Dict[str, Any],
    ) -> None:
        """
        اختبار الحذف النهائي للمطعم.
        
        Args:
            client: عميل HTTP غير متزامن للاختبار
            sample_restaurant_data: بيانات مطعم نموذجية
            sample_owner_data: بيانات مالك نموذجية
        """
        owner_id: int = await self._create_test_owner_via_api(
            client=client,
            sample_owner_data=sample_owner_data,
        )

        data: Dict[str, Any] = {
            **sample_restaurant_data,
            "owner_id": owner_id,
        }
        create_response = await client.post("/api/v1/restaurants/", json=data)
        
        assert create_response.status_code == 201
        
        restaurant_id: int = create_response.json()["id"]

        response = await client.delete(
            f"/api/v1/restaurants/{restaurant_id}",
            params={"permanent": True},
        )
        assert response.status_code == 204

        response = await client.get(
            f"/api/v1/restaurants/{restaurant_id}",
            params={"include_inactive": True},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_restaurant_not_found(
        self,
        client: AsyncClient,
    ) -> None:
        """
        اختبار حذف مطعم غير موجود.
        
        Args:
            client: عميل HTTP غير متزامن للاختبار
        """
        response = await client.delete("/api/v1/restaurants/99999")
        
        assert response.status_code == 404

    # ==========================================
    # 📊 STATISTICS ENDPOINT TESTS
    # ==========================================

    @pytest.mark.asyncio
    async def test_get_restaurant_stats(
        self,
        client: AsyncClient,
        sample_restaurant_data: Dict[str, Any],
        sample_owner_data: Dict[str, Any],
    ) -> None:
        """
        اختبار الحصول على إحصائيات المطعم.
        
        Args:
            client: عميل HTTP غير متزامن للاختبار
            sample_restaurant_data: بيانات مطعم نموذجية
            sample_owner_data: بيانات مالك نموذجية
        """
        owner_id: int = await self._create_test_owner_via_api(
            client=client,
            sample_owner_data=sample_owner_data,
        )

        data: Dict[str, Any] = {
            **sample_restaurant_data,
            "owner_id": owner_id,
        }
        await client.post("/api/v1/restaurants/", json=data)

        second_restaurant: Dict[str, Any] = {
            **sample_restaurant_data,
            "name": "مطعم الشرق الأوسط",
            "owner_id": owner_id,
        }
        await client.post("/api/v1/restaurants/", json=second_restaurant)

        response = await client.get(f"/api/v1/restaurants/stats/{owner_id}")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_restaurants"] >= 2
        assert data["active_restaurants"] >= 2

    @pytest.mark.asyncio
    async def test_get_restaurant_stats_owner_not_found(
        self,
        client: AsyncClient,
    ) -> None:
        """
        اختبار الحصول على إحصائيات لمالك غير موجود.
        
        Args:
            client: عميل HTTP غير متزامن للاختبار
        """
        response = await client.get("/api/v1/restaurants/stats/99999")
        
        assert response.status_code == 404


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "TestRestaurantsAPI",
]