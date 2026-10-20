# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🧪 RESTAURANT TESTS FIXTURES
# إعدادات خاصة باختبارات المطاعم
# ==============================================

"""Automated tests for conftest.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from collections.abc import AsyncIterator
from typing import (
    Any,
    Dict,
)

import pytest
from httpx import AsyncClient

from app.api.auth import AdminPrincipal
from app.api.v1.restaurant import require_restaurant_administration
from app.main import app

# ==============================================
# AUTHORIZED RESTAURANT BUSINESS CONTRACT CLIENT
# ==============================================


@pytest.fixture
async def client(client: AsyncClient) -> AsyncIterator[AsyncClient]:
    """Keep legacy database cases focused on authorized business behavior.

    The parent fixture still owns guarded database selection and cleanup.
    Only this directory's business tests substitute the administrative boundary;
    offline security tests separately exercise real identity and RBAC denials.
    No administrator or permission is inserted into any database.
    """
    previous = app.dependency_overrides.get(require_restaurant_administration)
    app.dependency_overrides[require_restaurant_administration] = (
        lambda: AdminPrincipal(admin_id=7)
    )
    try:
        yield client
    finally:
        if previous is None:
            app.dependency_overrides.pop(require_restaurant_administration, None)
        else:
            app.dependency_overrides[require_restaurant_administration] = previous


# ==============================================
# 📦 DATA FACTORIES - ✅ بدون is_active للمجموعة
# ==============================================


@pytest.fixture
def sample_restaurant_data() -> Dict[str, Any]:
    """بيانات مطعم نموذجية للاختبار."""
    return {
        "name": "مطعم البيتزا الذهبية",
        "type": "restaurant",
        "phone": "+213551234567",
        "wilaya": "الجزائر",
        "lat": 36.7538,
        "lng": 3.0588,
        "is_active": True,
    }


# ==============================================
# SAMPLE RESTAURANT GROUP DATA
# ==============================================


@pytest.fixture
def sample_restaurant_group_data() -> Dict[str, Any]:
    """
    بيانات مجموعة مطاعم نموذجية للاختبار.

    ✅ التصحيح: إزالة is_active لأن RestaurantGroup لا يحتوي عليه
    """
    return {
        "name": "مجموعة المطاعم الذهبية",
    }


# ==============================================
# SAMPLE GROUP DATA
# ==============================================


@pytest.fixture
def sample_group_data() -> Dict[str, Any]:
    """
    بيانات مجموعة نموذجية للاختبار.

    ✅ التصحيح: إزالة is_active
    """
    return {
        "name": "مجموعة المطاعم الذهبية",
    }


# ==============================================
# SAMPLE RESTAURANT BRANCH DATA
# ==============================================


@pytest.fixture
def sample_restaurant_branch_data() -> Dict[str, Any]:
    """بيانات فرع مطعم نموذجية للاختبار."""
    return {
        "group_id": 1,
        "restaurant_id": 1,
    }


# ==============================================
# SAMPLE BULK BRANCHES DATA
# ==============================================


@pytest.fixture
def sample_bulk_branches_data() -> Dict[str, Any]:
    """بيانات فروع متعددة نموذجية للاختبار."""
    return {
        "group_id": 1,
        "restaurant_ids": [1, 2, 3],
    }


# ==============================================
# SAMPLE METRIC DATA
# ==============================================


@pytest.fixture
def sample_metric_data() -> Dict[str, Any]:
    """بيانات مقاييس نموذجية للاختبار."""
    return {
        "products_count": 10,
        "categories_count": 5,
        "monthly_orders": 100,
        "average_order_value": 1500.00,
    }


# ==============================================
# SAMPLE ORDER COUNTER DATA
# ==============================================


@pytest.fixture
def sample_order_counter_data() -> Dict[str, Any]:
    """بيانات عداد طلبات نموذجية للاختبار."""
    return {
        "last_number": 0,
    }


# ==============================================
# SAMPLE PAYMENT SETTINGS DATA
# ==============================================


@pytest.fixture
def sample_payment_settings_data() -> Dict[str, Any]:
    """بيانات إعدادات دفع نموذجية للاختبار."""
    return {
        "allow_cash": True,
        "allow_card": True,
        "allow_ccp": False,
        "allow_baridimob": False,
        "allow_stripe": False,
        "allow_paypal": False,
    }


# ==============================================
# SAMPLE ORDER DATA
# ==============================================


@pytest.fixture
def sample_order_data() -> Dict[str, Any]:
    """بيانات طلب نموذجية للاختبار."""
    return {
        "order_number": "RST1-000001",
        "order_type": "dine_in",
        "customer_name": "علي أحمد",
        "customer_phone": "0555123456",
        "delivery_address": None,
        "customer_note": "بدون بصل",
        "subtotal_amount": 100.00,
        "discount_amount": 0.00,
        "tax_amount": 0.00,
        "delivery_amount": 0.00,
        "total_amount": 100.00,
        "status": "pending",
    }


# ==============================================
# SAMPLE PRODUCT DATA
# ==============================================


@pytest.fixture
def sample_product_data() -> Dict[str, Any]:
    """بيانات منتج نموذجية للاختبار."""
    return {
        "name": "بيتزا مارجريتا",
        "description": "بيتزا كلاسيكية بصلصة الطماطم والجبن",
        "price": 800.00,
        "image_url": None,
        "sort_order": 0,
        "is_available": True,
        "is_active": True,
    }


# ==============================================
# SAMPLE CATEGORY DATA
# ==============================================


@pytest.fixture
def sample_category_data() -> Dict[str, Any]:
    """بيانات تصنيف نموذجية للاختبار."""
    return {
        "name": "بيتزا",
        "description": "جميع أنواع البيتزا",
        "sort_order": 0,
        "is_active": True,
    }


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "sample_restaurant_data",
    "sample_restaurant_group_data",
    "sample_group_data",
    "sample_restaurant_branch_data",
    "sample_bulk_branches_data",
    "sample_metric_data",
    "sample_order_counter_data",
    "sample_payment_settings_data",
    "sample_order_data",
    "sample_product_data",
    "sample_category_data",
]
