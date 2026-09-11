# ==============================================
# MoulAI Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine
# ==============================================

# ==============================================
# 🏦 RESTAURANT PAYMENT SETTINGS ROUTER - BASIC
# نقاط نهاية إعدادات الدفع الأساسية
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
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.core.logger import logger
from app.schemas.restaurant.restaurant_payment_setting import (
    RestaurantPaymentSettingCreate,
    RestaurantPaymentSettingResponse,
    RestaurantPaymentSettingUpdate,
    RestaurantPaymentSettingListResponse,
)
from app.services.business.restaurant.payment_setting.service import (
    RestaurantPaymentSettingsService,
)


# ==============================================
# 🧩 CONSTANTS
# ==============================================

ALL_PAYMENT_METHODS = ["cash", "card", "ccp", "baridimob", "stripe", "paypal"]


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
# LIST PAYMENT SETTINGS
# ==============================================

@router.get(
    "/",
    response_model=RestaurantPaymentSettingListResponse,
    summary="قائمة إعدادات الدفع",
    description="الحصول على قائمة إعدادات الدفع للمطاعم",
)
async def list_payment_settings(
    *,
    skip: int = Query(0, ge=0, description="عدد السجلات للتخطي"),
    limit: int = Query(100, ge=1, le=200, description="الحد الأقصى للسجلات"),
    service: RestaurantPaymentSettingsService = Depends(get_payment_settings_service),
) -> RestaurantPaymentSettingListResponse:
    """الحصول على قائمة إعدادات الدفع للمطاعم."""
    logger.info(
        "api_list_payment_settings",
        extra={"skip": skip, "limit": limit},
    )

    try:
        settings = await service.repo.get_all(
            skip=skip,
            limit=limit,
            order_by="restaurant_id",
        )
        total = await service.repo.count()

        return RestaurantPaymentSettingListResponse(
            items=[RestaurantPaymentSettingResponse.model_validate(s) for s in settings],
            total=total,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.exception(
            "api_list_payment_settings_error",
            extra={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب قائمة إعدادات الدفع",
        )


# ==============================================
# GET PAYMENT SETTINGS
# ==============================================

@router.get(
    "/{restaurant_id}",
    response_model=RestaurantPaymentSettingResponse,
    summary="إعدادات الدفع للمطعم",
    description="الحصول على إعدادات الدفع لمطعم معين",
)
async def get_payment_settings(
    *,
    restaurant_id: int = Path(..., ge=1, description="معرف المطعم"),
    service: RestaurantPaymentSettingsService = Depends(get_payment_settings_service),
) -> RestaurantPaymentSettingResponse:
    """الحصول على إعدادات الدفع لمطعم معين."""
    logger.info(
        "api_get_payment_settings",
        extra={"restaurant_id": restaurant_id},
    )

    try:
        return await service.get_settings(restaurant_id=restaurant_id)

    except NotFoundError as e:
        logger.warning(
            "api_payment_settings_not_found",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_get_payment_settings_error",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب إعدادات الدفع",
        )


# ==============================================
# CREATE PAYMENT SETTINGS
# ==============================================

@router.post(
    "/",
    response_model=RestaurantPaymentSettingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء إعدادات دفع",
    description="إنشاء إعدادات دفع جديدة لمطعم",
)
async def create_payment_settings(
    *,
    data: RestaurantPaymentSettingCreate,
    service: RestaurantPaymentSettingsService = Depends(get_payment_settings_service),
) -> RestaurantPaymentSettingResponse:
    """إنشاء إعدادات دفع جديدة لمطعم."""
    logger.info(
        "api_create_payment_settings",
        extra={"restaurant_id": data.restaurant_id},
    )

    try:
        return await service.create_settings(settings_data=data)

    except ConflictError as e:
        logger.warning(
            "api_payment_settings_already_exist",
            extra={"restaurant_id": data.restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_create_payment_settings_validation_error",
            extra={"restaurant_id": data.restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_create_payment_settings_error",
            extra={"restaurant_id": data.restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إنشاء إعدادات الدفع",
        )


# ==============================================
# UPDATE PAYMENT SETTINGS
# ==============================================

@router.put(
    "/{restaurant_id}",
    response_model=RestaurantPaymentSettingResponse,
    summary="تحديث إعدادات الدفع",
    description="تحديث إعدادات الدفع لمطعم معين",
)
async def update_payment_settings(
    *,
    restaurant_id: int = Path(..., ge=1, description="معرف المطعم"),
    data: RestaurantPaymentSettingUpdate,
    service: RestaurantPaymentSettingsService = Depends(get_payment_settings_service),
) -> RestaurantPaymentSettingResponse:
    """تحديث إعدادات الدفع لمطعم معين."""
    logger.info(
        "api_update_payment_settings",
        extra={
            "restaurant_id": restaurant_id,
            "fields": list(data.model_dump(exclude_unset=True).keys()),
        },
    )

    try:
        return await service.update_settings(
            restaurant_id=restaurant_id,
            update_data=data,
        )

    except NotFoundError as e:
        logger.warning(
            "api_payment_settings_not_found_for_update",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_update_payment_settings_validation_error",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_update_payment_settings_error",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث إعدادات الدفع",
        )


# ==============================================
# DELETE PAYMENT SETTINGS
# ==============================================

@router.delete(
    "/{restaurant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="حذف إعدادات الدفع",
    description="حذف إعدادات الدفع لمطعم معين",
)
async def delete_payment_settings(
    *,
    restaurant_id: int = Path(..., ge=1, description="معرف المطعم"),
    service: RestaurantPaymentSettingsService = Depends(get_payment_settings_service),
) -> None:
    """حذف إعدادات الدفع لمطعم معين."""
    logger.info(
        "api_delete_payment_settings",
        extra={"restaurant_id": restaurant_id},
    )

    try:
        await service.delete_settings(restaurant_id=restaurant_id)

    except NotFoundError as e:
        logger.warning(
            "api_payment_settings_not_found_for_delete",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_delete_payment_settings_error",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء حذف إعدادات الدفع",
        )

    logger.info(
        "api_payment_settings_deleted_successfully",
        extra={"restaurant_id": restaurant_id},
    )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "router",
    "ALL_PAYMENT_METHODS",
]