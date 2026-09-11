# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🧪 RESTAURANT API TESTS PACKAGE
# ==============================================

"""
حزمة اختبارات واجهات برمجة التطبيقات للمطاعم.

تحتوي على اختبارات لجميع نقاط نهاية المطاعم:
- test_restaurants.py: اختبارات المطاعم
- test_metrics.py: اختبارات مقاييس المطعم
- test_order_counter.py: اختبارات عداد الطلبات
- test_payment_settings.py: اختبارات إعدادات الدفع
- test_groups.py: اختبارات مجموعات المطاعم
- test_branches.py: اختبارات فروع المطاعم
"""

from tests.api.v1.restaurant.test_restaurants import TestRestaurantsAPI
from tests.api.v1.restaurant.test_metrics import TestMetricsAPI
from tests.api.v1.restaurant.test_order_counter import TestOrderCounterAPI
from tests.api.v1.restaurant.test_payment_settings import TestPaymentSettingsAPI
from tests.api.v1.restaurant.test_groups import TestRestaurantGroupsAPI
from tests.api.v1.restaurant.test_branches import TestRestaurantBranchesAPI


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "TestRestaurantsAPI",
    "TestMetricsAPI",
    "TestOrderCounterAPI",
    "TestPaymentSettingsAPI",
    "TestRestaurantGroupsAPI",
    "TestRestaurantBranchesAPI",
]