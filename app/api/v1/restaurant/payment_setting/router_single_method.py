# ==============================================
# MoulAI Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine
# ==============================================

# ==============================================
# 🏦 RESTAURANT PAYMENT SETTINGS ROUTER - SINGLE METHOD
# نقاط نهاية تفعيل/إلغاء تفعيل طريقة دفع مفردة
# ==============================================

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Path,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import (
    NotFoundError,
    ValidationError,
)
from app.core.logger import logger
from app.schemas.restaurant.restaurant_payment_setting import (
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
# ENABLE PAYMENT METHOD
# ==============================================

@router.post(
    "/{restaurant_id}/methods/{method}/enable",
    response_model=RestaurantPaymentSettingResponse,
    summary="تفعيل طريقة دفع",
    description="تفعيل طريقة دفع معينة لمطعم",
)
async def enable_payment_method(
    *,
    restaurant_id: int = Path(..., ge=1, description="معرف المطعم"),
    method: str = Path(..., description="طريقة الدفع (cash, card, ccp, baridimob, stripe, paypal)"),
    service: RestaurantPaymentSettingsService = Depends(get_payment_settings_service),
) -> RestaurantPaymentSettingResponse:
    """تفعيل طريقة دفع معينة لمطعم."""
    logger.info(
        "api_enable_payment_method",
        extra={
            "restaurant_id": restaurant_id,
            "method": method,
        },
    )

    try:
        return await service.enable_payment_method(
            restaurant_id=restaurant_id,
            method=method,
        )

    except NotFoundError as e:
        logger.warning(
            "api_payment_settings_not_found_for_enable",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_enable_payment_method_validation_error",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_enable_payment_method_error",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تفعيل طريقة الدفع",
        )


# ==============================================
# DISABLE PAYMENT METHOD
# ==============================================

@router.post(
    "/{restaurant_id}/methods/{method}/disable",
    response_model=RestaurantPaymentSettingResponse,
    summary="إلغاء تفعيل طريقة دفع",
    description="إلغاء تفعيل طريقة دفع معينة لمطعم",
)
async def disable_payment_method(
    *,
    restaurant_id: int = Path(..., ge=1, description="معرف المطعم"),
    method: str = Path(..., description="طريقة الدفع (cash, card, ccp, baridimob, stripe, paypal)"),
    service: RestaurantPaymentSettingsService = Depends(get_payment_settings_service),
) -> RestaurantPaymentSettingResponse:
    """إلغاء تفعيل طريقة دفع معينة لمطعم."""
    logger.info(
        "api_disable_payment_method",
        extra={
            "restaurant_id": restaurant_id,
            "method": method,
        },
    )

    try:
        return await service.disable_payment_method(
            restaurant_id=restaurant_id,
            method=method,
        )

    except NotFoundError as e:
        logger.warning(
            "api_payment_settings_not_found_for_disable",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_disable_payment_method_validation_error",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_disable_payment_method_error",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إلغاء تفعيل طريقة الدفع",
        )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "router",
]