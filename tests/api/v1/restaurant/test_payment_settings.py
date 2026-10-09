# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# TEST MODULE - TESTS / API / V1 / RESTAURANT / TEST PAYMENT SETTINGS
# Automated test coverage for the MoulAI platform.
# ==============================================

"""Automated tests for test payment settings.

Part of MoulAI Platform - Agent-as-a-Service.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.restaurant_payment_setting import RestaurantPaymentSetting

from app.models.owner import Owner
from app.models.restaurant import Restaurant

# ==============================================
# 📋 TESTS - PAYMENT SETTINGS
# ==============================================


class TestPaymentSettingsAPI:
    """
    اختبارات نقاط نهاية إعدادات الدفع.
    """

    # ==============================================
    # SETUP
    # ==============================================

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
    # TEST CREATE PAYMENT SETTINGS
    # ==============================================

    async def test_create_payment_settings(
        self,
        client: AsyncClient,
        sample_payment_settings_data,
    ) -> None:
        """
        اختبار إنشاء إعدادات الدفع.

        Args:
            client: عميل HTTP غير متزامن
            sample_payment_settings_data: بيانات إعدادات دفع نموذجية
        """
        data = {"restaurant_id": self.restaurant_id, **sample_payment_settings_data}
        response = await client.post(
            "/api/v1/restaurant-payment-settings/",
            json=data,
        )

        assert response.status_code == 201

        data = response.json()
        assert data["restaurant_id"] == self.restaurant_id
        assert data["allow_cash"] is True
        assert data["allow_card"] is True

    # ==============================================
    # TEST GET PAYMENT SETTINGS
    # ==============================================

    async def test_get_payment_settings(
        self,
        client: AsyncClient,
        sample_payment_settings_data,
    ) -> None:
        """
        اختبار الحصول على إعدادات الدفع.

        Args:
            client: عميل HTTP غير متزامن
            sample_payment_settings_data: بيانات إعدادات دفع نموذجية
        """
        # إنشاء الإعدادات أولاً
        create_data = {
            "restaurant_id": self.restaurant_id,
            **sample_payment_settings_data,
        }
        await client.post("/api/v1/restaurant-payment-settings/", json=create_data)

        response = await client.get(
            f"/api/v1/restaurant-payment-settings/{self.restaurant_id}"
        )

        assert response.status_code == 200

        data = response.json()
        assert data["restaurant_id"] == self.restaurant_id

    # ==============================================
    # TEST UPDATE PAYMENT METHODS
    # ==============================================

    async def test_update_payment_methods(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_payment_settings_data,
    ) -> None:
        """
        اختبار تحديث طرق الدفع.

        Args:
            client: عميل HTTP غير متزامن
            sample_payment_settings_data: بيانات إعدادات دفع نموذجية
        """
        # إنشاء الإعدادات أولاً
        create_data = {
            "restaurant_id": self.restaurant_id,
            **sample_payment_settings_data,
        }
        await client.post("/api/v1/restaurant-payment-settings/", json=create_data)

        # تحديث طرق الدفع
        statements = []

        # ==============================================
        # RECORD SQL
        # ==============================================

        def record_sql(connection, cursor, statement, parameters, context, executemany):
            statements.append(statement.lower())

        engine = db_session.bind.sync_engine
        event.listen(engine, "before_cursor_execute", record_sql)
        try:
            response = await client.patch(
                f"/api/v1/restaurant-payment-settings/{self.restaurant_id}/methods",
                params={"allow_ccp": True, "allow_paypal": True},
            )
        finally:
            event.remove(engine, "before_cursor_execute", record_sql)

        assert response.status_code == 200

        data = response.json()
        assert data["allow_ccp"] is True
        assert data["allow_paypal"] is True

        # Updating settings must not traverse the restaurant/catalog graph.
        assert not any(
            "from products" in sql
            or "from restaurants" in sql
            or "from categories" in sql
            for sql in statements
        )
        persisted = (
            await db_session.execute(
                select(
                    RestaurantPaymentSetting.allow_ccp,
                    RestaurantPaymentSetting.allow_paypal,
                ).where(RestaurantPaymentSetting.restaurant_id == self.restaurant_id)
            )
        ).one()
        assert tuple(persisted) == (True, True)

    # ==============================================
    # TEST ENABLE PAYMENT METHOD
    # ==============================================

    async def test_enable_payment_method(
        self,
        client: AsyncClient,
        sample_payment_settings_data,
    ) -> None:
        """
        اختبار تفعيل طريقة دفع.

        Args:
            client: عميل HTTP غير متزامن
            sample_payment_settings_data: بيانات إعدادات دفع نموذجية
        """
        # إنشاء الإعدادات أولاً
        create_data = {
            "restaurant_id": self.restaurant_id,
            **sample_payment_settings_data,
        }
        await client.post("/api/v1/restaurant-payment-settings/", json=create_data)

        # تفعيل طريقة دفع
        response = await client.post(
            f"/api/v1/restaurant-payment-settings/{self.restaurant_id}/methods/stripe/enable"
        )

        assert response.status_code == 200

        data = response.json()
        assert data["allow_stripe"] is True


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "TestPaymentSettingsAPI",
]
