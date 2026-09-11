# ==============================================
# MoulAI Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine
# ==============================================

# ==============================================
# 🏦 RESTAURANT PAYMENT SETTINGS ROUTER - METHODS
# نقاط نهاية طرق الدفع
# ==============================================

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
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
    PaymentMethodsList,
    RestaurantPaymentSettingResponse,
)
from app.services.business.restaurant.payment_setting.service import (
    RestaurantPaymentSettingsService,
)

from app.api.v1.restaurant.payment_setting.router import ALL_PAYMENT_METHODS


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
# GET ALLOWED PAYMENT METHODS
# ==============================================

@router.get(
    "/{restaurant_id}/methods",
    response_model=PaymentMethodsList,
    summary="طرق الدفع المسموح بها",
    description="الحصول على قائمة طرق الدفع المسموح بها لمطعم معين",
)
async def get_allowed_payment_methods(
    *,
    restaurant_id: int = Path(..., ge=1, description="معرف المطعم"),
    service: RestaurantPaymentSettingsService = Depends(get_payment_settings_service),
) -> PaymentMethodsList:
    """الحصول على قائمة طرق الدفع المسموح بها لمطعم معين."""
    logger.info(
        "api_get_allowed_payment_methods",
        extra={"restaurant_id": restaurant_id},
    )

    try:
        # أولاً التحقق من وجود الإعدادات
        await service.get_settings(restaurant_id=restaurant_id)

        allowed_methods = await service.get_allowed_methods(
            restaurant_id=restaurant_id,
        )

        return PaymentMethodsList(
            restaurant_id=restaurant_id,
            allowed_methods=allowed_methods,
            all_methods=ALL_PAYMENT_METHODS,
        )

    except NotFoundError as e:
        logger.warning(
            "api_payment_settings_not_found_for_methods",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_get_allowed_payment_methods_error",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب طرق الدفع المسموح بها",
        )


# ==============================================
# UPDATE PAYMENT METHODS
# ==============================================

@router.patch(
    "/{restaurant_id}/methods",
    response_model=RestaurantPaymentSettingResponse,
    summary="تحديث طرق الدفع",
    description="تحديث طرق الدفع المسموح بها لمطعم معين",
)
async def update_payment_methods(
    *,
    restaurant_id: int = Path(..., ge=1, description="معرف المطعم"),
    allow_cash: bool = Query(True, description="السماح بالدفع نقداً"),
    allow_card: bool = Query(True, description="السماح بالدفع ببطاقة POS"),
    allow_ccp: bool = Query(False, description="السماح بالدفع عبر CCP"),
    allow_baridimob: bool = Query(False, description="السماح بالدفع عبر بريدي موب"),
    allow_stripe: bool = Query(False, description="السماح بالدفع عبر Stripe"),
    allow_paypal: bool = Query(False, description="السماح بالدفع عبر PayPal"),
    service: RestaurantPaymentSettingsService = Depends(get_payment_settings_service),
) -> RestaurantPaymentSettingResponse:
    """تحديث طرق الدفع المسموح بها لمطعم معين."""
    logger.info(
        "api_update_payment_methods",
        extra={
            "restaurant_id": restaurant_id,
            "allow_cash": allow_cash,
            "allow_card": allow_card,
            "allow_ccp": allow_ccp,
            "allow_baridimob": allow_baridimob,
            "allow_stripe": allow_stripe,
            "allow_paypal": allow_paypal,
        },
    )

    try:
        return await service.update_payment_methods(
            restaurant_id=restaurant_id,
            allow_cash=allow_cash,
            allow_card=allow_card,
            allow_ccp=allow_ccp,
            allow_baridimob=allow_baridimob,
            allow_stripe=allow_stripe,
            allow_paypal=allow_paypal,
        )

    except NotFoundError as e:
        logger.warning(
            "api_payment_settings_not_found_for_methods_update",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_update_payment_methods_validation_error",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_update_payment_methods_error",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث طرق الدفع",
        )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "router",
]