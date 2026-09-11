# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🏦 RESTAURANT PAYMENT SETTINGS COMPATIBILITY
# دوال متوافقة مع الاستيرادات القديمة
# ==============================================

from typing import (
    Any,
    Dict,
    Optional,
)

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.schemas.restaurant.restaurant_payment_setting import (
    RestaurantPaymentSettingCreate,
    RestaurantPaymentSettingUpdate,
    PaymentMethodsList,
)
from app.services.business.restaurant.payment_setting.service import RestaurantPaymentSettingsService


# ==============================================
# 📦 COMPATIBILITY FUNCTIONS
# ==============================================

# ==============================================
# CREATE PAYMENT SETTINGS
# ==============================================

async def create_payment_settings(
    *,
    restaurant_id: int,
    allow_cash: bool = True,
    allow_card: bool = True,
    allow_ccp: bool = False,
    allow_baridimob: bool = False,
    allow_stripe: bool = False,
    allow_paypal: bool = False,
    session: AsyncSession,
) -> int:
    """
    إنشاء إعدادات دفع جديدة لمطعم (دالة متوافقة مع الإصدار القديم).
    """
    service = RestaurantPaymentSettingsService(session=session)

    settings_data = RestaurantPaymentSettingCreate(
        restaurant_id=restaurant_id,
        allow_cash=allow_cash,
        allow_card=allow_card,
        allow_ccp=allow_ccp,
        allow_baridimob=allow_baridimob,
        allow_stripe=allow_stripe,
        allow_paypal=allow_paypal,
    )

    settings = await service.create_settings(settings_data=settings_data)

    return settings.id


# ==============================================
# GET PAYMENT SETTINGS
# ==============================================

async def get_payment_settings(
    *,
    restaurant_id: int,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على إعدادات الدفع لمطعم معين (دالة متوافقة مع الإصدار القديم).
    """
    service = RestaurantPaymentSettingsService(session=session)

    try:
        settings = await service.get_settings(restaurant_id=restaurant_id)
        return settings.model_dump()
    except Exception:
        return None


# ==============================================
# UPDATE PAYMENT SETTINGS
# ==============================================

async def update_payment_settings(
    *,
    restaurant_id: int,
    data: Dict[str, Any],
    session: AsyncSession,
) -> None:
    """
    تحديث إعدادات الدفع لمطعم (دالة متوافقة مع الإصدار القديم).
    """
    service = RestaurantPaymentSettingsService(session=session)

    update_data = RestaurantPaymentSettingUpdate(**data)

    await service.update_settings(
        restaurant_id=restaurant_id,
        update_data=update_data,
    )

    logger.info(
        "payment_settings_updated",
        extra={"restaurant_id": restaurant_id},
    )


# ==============================================
# UPDATE PAYMENT METHODS
# ==============================================

async def update_payment_methods(
    *,
    restaurant_id: int,
    allow_cash: Optional[bool] = None,
    allow_card: Optional[bool] = None,
    allow_ccp: Optional[bool] = None,
    allow_baridimob: Optional[bool] = None,
    allow_stripe: Optional[bool] = None,
    allow_paypal: Optional[bool] = None,
    session: AsyncSession,
) -> None:
    """
    تحديث طرق الدفع المسموح بها لمطعم (دالة متوافقة مع الإصدار القديم).
    """
    service = RestaurantPaymentSettingsService(session=session)

    await service.update_payment_methods(
        restaurant_id=restaurant_id,
        allow_cash=allow_cash,
        allow_card=allow_card,
        allow_ccp=allow_ccp,
        allow_baridimob=allow_baridimob,
        allow_stripe=allow_stripe,
        allow_paypal=allow_paypal,
    )

    logger.info(
        "payment_methods_updated",
        extra={"restaurant_id": restaurant_id},
    )


# ==============================================
# GET ALLOWED PAYMENT METHODS
# ==============================================

async def get_allowed_payment_methods(
    *,
    restaurant_id: int,
    session: AsyncSession,
) -> PaymentMethodsList:
    """
    الحصول على قائمة طرق الدفع المسموح بها لمطعم معين (دالة متوافقة مع الإصدار القديم).
    """
    service = RestaurantPaymentSettingsService(session=session)

    return await service.get_allowed_methods(restaurant_id=restaurant_id)


# ==============================================
# DELETE PAYMENT SETTINGS
# ==============================================

async def delete_payment_settings(
    *,
    restaurant_id: int,
    session: AsyncSession,
) -> None:
    """
    حذف إعدادات الدفع لمطعم (دالة متوافقة مع الإصدار القديم).
    """
    service = RestaurantPaymentSettingsService(session=session)

    await service.delete_settings(restaurant_id=restaurant_id)

    logger.info(
        "payment_settings_deleted",
        extra={"restaurant_id": restaurant_id},
    )


# ==============================================
# RESET PAYMENT SETTINGS
# ==============================================

async def reset_payment_settings(
    *,
    restaurant_id: int,
    session: AsyncSession,
) -> None:
    """
    إعادة تعيين إعدادات الدفع إلى القيم الافتراضية (دالة متوافقة مع الإصدار القديم).
    """
    service = RestaurantPaymentSettingsService(session=session)

    await service.reset_to_defaults(restaurant_id=restaurant_id)

    logger.info(
        "payment_settings_reset",
        extra={"restaurant_id": restaurant_id},
    )


# ==============================================
# ENABLE PAYMENT METHOD
# ==============================================

async def enable_payment_method(
    *,
    restaurant_id: int,
    method: str,
    session: AsyncSession,
) -> None:
    """
    تفعيل طريقة دفع معينة لمطعم (دالة متوافقة مع الإصدار القديم).
    """
    service = RestaurantPaymentSettingsService(session=session)

    await service.enable_payment_method(
        restaurant_id=restaurant_id,
        method=method,
    )

    logger.info(
        "payment_method_enabled",
        extra={
            "restaurant_id": restaurant_id,
            "method": method,
        },
    )


# ==============================================
# DISABLE PAYMENT METHOD
# ==============================================

async def disable_payment_method(
    *,
    restaurant_id: int,
    method: str,
    session: AsyncSession,
) -> None:
    """
    إلغاء تفعيل طريقة دفع معينة لمطعم (دالة متوافقة مع الإصدار القديم).
    """
    service = RestaurantPaymentSettingsService(session=session)

    await service.disable_payment_method(
        restaurant_id=restaurant_id,
        method=method,
    )

    logger.info(
        "payment_method_disabled",
        extra={
            "restaurant_id": restaurant_id,
            "method": method,
        },
    )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "create_payment_settings",
    "get_payment_settings",
    "update_payment_settings",
    "update_payment_methods",
    "get_allowed_payment_methods",
    "delete_payment_settings",
    "reset_payment_settings",
    "enable_payment_method",
    "disable_payment_method",
]