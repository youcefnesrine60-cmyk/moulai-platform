# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🏦 RESTAURANT PAYMENT SETTINGS ROUTER - SUMMARY
# نقاط نهاية الملخص وإعادة التعيين
# ==============================================

"""MoulAI operational module for router summary.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Path,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.core.logger import logger
from app.schemas.restaurant.restaurant_payment_setting import (
    PaymentSettingsSummary,
    RestaurantPaymentSettingResponse,
)
from app.services.business.restaurant.payment_setting.service import (
    RestaurantPaymentSettingsService,
)

# ==============================================
# 🏗️ ROUTER
# ==============================================

router = APIRouter(
    prefix="/restaurant-payment-settings",
    tags=["Restaurant Payment Settings"],
)


# ==============================================
# 🔧 DEPENDENCIES
# ==============================================


async def get_payment_settings_service(
    session: AsyncSession = Depends(get_db),
) -> RestaurantPaymentSettingsService:
    """الحصول على خدمة إعدادات الدفع."""
    return RestaurantPaymentSettingsService(session)


# ==============================================
# 📋 ENDPOINTS
# ==============================================

# ==============================================
# GET PAYMENT SETTINGS SUMMARY
# ==============================================


@router.get(
    "/{restaurant_id}/summary",
    response_model=PaymentSettingsSummary,
    summary="ملخص إعدادات الدفع",
    description="الحصول على ملخص إعدادات الدفع لمطعم معين",
)
async def get_payment_settings_summary(
    *,
    restaurant_id: int = Path(..., ge=1, description="معرف المطعم"),
    service: RestaurantPaymentSettingsService = Depends(get_payment_settings_service),
) -> PaymentSettingsSummary:
    """الحصول على ملخص إعدادات الدفع لمطعم معين."""
    logger.info(
        "api_get_payment_settings_summary",
        extra={"restaurant_id": restaurant_id},
    )

    try:
        return await service.get_settings_summary(restaurant_id=restaurant_id)

    except NotFoundError as e:
        logger.warning(
            "api_payment_settings_not_found_for_summary",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_get_payment_settings_summary_error",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب ملخص إعدادات الدفع",
        )


# ==============================================
# RESET PAYMENT SETTINGS TO DEFAULTS
# ==============================================


@router.post(
    "/{restaurant_id}/reset",
    response_model=RestaurantPaymentSettingResponse,
    summary="إعادة تعيين إعدادات الدفع",
    description="إعادة تعيين إعدادات الدفع إلى القيم الافتراضية",
)
async def reset_payment_settings(
    *,
    restaurant_id: int = Path(..., ge=1, description="معرف المطعم"),
    service: RestaurantPaymentSettingsService = Depends(get_payment_settings_service),
) -> RestaurantPaymentSettingResponse:
    """إعادة تعيين إعدادات الدفع إلى القيم الافتراضية (cash, card فقط)."""
    logger.info(
        "api_reset_payment_settings",
        extra={"restaurant_id": restaurant_id},
    )

    try:
        return await service.reset_to_defaults(restaurant_id=restaurant_id)

    except NotFoundError as e:
        logger.warning(
            "api_payment_settings_not_found_for_reset",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_reset_payment_settings_error",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إعادة تعيين إعدادات الدفع",
        )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "router",
]
