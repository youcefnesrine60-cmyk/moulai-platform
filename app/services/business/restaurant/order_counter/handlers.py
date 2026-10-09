# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🔢 RESTAURANT ORDER COUNTER HANDLERS
# معالجات أحداث عداد طلبات المطعم
# ==============================================

"""MoulAI operational module for handlers.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.business.restaurant.order_counter.service import (
    RestaurantOrderCounterService,
)

# ==============================================
# 🔢 ORDER COUNTER EVENT HANDLERS
# ==============================================


class OrderCounterEventHandlers:
    """
    معالجات أحداث عداد طلبات المطعم.

    تتعامل مع عمليات إنشاء وتحديث وزيادة وإعادة تعيين عداد الطلبات.

    Attributes:
        session: جلسة قاعدة البيانات غير المتزامنة
        service: خدمة عداد الطلبات
    """

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة معالجات الأحداث.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        self.session = session
        self.service = RestaurantOrderCounterService(session)


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "OrderCounterEventHandlers",
]
