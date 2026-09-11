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

from typing import (
    Any,
    Dict,
)

import pytest


# ==============================================
# 📦 DATA FACTORIES - ✅ بدون chat_id
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


@pytest.fixture
def sample_restaurant_group_data() -> Dict[str, Any]:
    """بيانات مجموعة مطاعم نموذجية للاختبار."""
    return {
        "name": "مجموعة المطاعم الذهبية",
        "is_active": True,
    }


@pytest.fixture
def sample_restaurant_branch_data() -> Dict[str, Any]:
    """بيانات فرع مطعم نموذجية للاختبار."""
    return {
        "group_id": 1,
        "restaurant_id": 1,
    }


@pytest.fixture
def sample_bulk_branches_data() -> Dict[str, Any]:
    """بيانات فروع متعددة نموذجية للاختبار."""
    return {
        "group_id": 1,
        "restaurant_ids": [1, 2, 3],
    }


@pytest.fixture
def sample_metric_data() -> Dict[str, Any]:
    """بيانات مقاييس نموذجية للاختبار."""
    return {
        "products_count": 10,
        "categories_count": 5,
        "monthly_orders": 100,
        "average_order_value": 1500.00,
    }


@pytest.fixture
def sample_order_counter_data() -> Dict[str, Any]:
    """بيانات عداد طلبات نموذجية للاختبار."""
    return {
        "last_number": 0,
    }


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
    "sample_restaurant_branch_data",
    "sample_bulk_branches_data",
    "sample_metric_data",
    "sample_order_counter_data",
    "sample_payment_settings_data",
    "sample_order_data",
    "sample_product_data",
    "sample_category_data",
]