# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🏦 RESTAURANT PAYMENT SETTINGS HANDLERS
# معالجات أحداث إعدادات الدفع
# ==============================================

"""MoulAI operational module for handlers.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.business.restaurant.payment_setting.service import (
    RestaurantPaymentSettingsService,
)

# ==============================================
# 🏦 PAYMENT SETTINGS EVENT HANDLERS
# ==============================================


class PaymentSettingsEventHandlers:
    """
    معالجات أحداث إعدادات الدفع للمطعم.

    تتعامل مع عمليات إنشاء وتحديث وحذف إعدادات الدفع.

    Attributes:
        session: جلسة قاعدة البيانات غير المتزامنة
        service: خدمة إعدادات الدفع
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
        self.service = RestaurantPaymentSettingsService(session)


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "PaymentSettingsEventHandlers",
]
