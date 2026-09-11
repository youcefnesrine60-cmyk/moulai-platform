# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🍽️ RESTAURANT ROUTER - STATUS
# نقاط نهاية حالة المطعم
# ==============================================

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Path,
    Query,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.core.logger import logger
from app.schemas.restaurant import RestaurantResponse
from app.services.business.restaurant.restaurants.handlers import RestaurantEventHandlers


# ==============================================
# 🏗️ ROUTER
# ==============================================

router = APIRouter(
    prefix="/restaurants",
    tags=["Restaurants"],
)


# ==============================================
# 🔧 DEPENDENCIES
# ==============================================

async def get_restaurant_handlers(
    session: AsyncSession = Depends(get_db),
) -> RestaurantEventHandlers:
    """
    الحصول على معالجات أحداث المطاعم.
    
    Args:
        session: جلسة قاعدة البيانات
        
    Returns:
        RestaurantEventHandlers: معالجات الأحداث
    """
    return RestaurantEventHandlers(session)


# ==============================================
# 📋 ENDPOINTS
# ==============================================

# ==============================================
# TOGGLE RESTAURANT STATUS
# ==============================================

@router.patch(
    "/{restaurant_id}/status",
    response_model=RestaurantResponse,
    summary="تغيير حالة المطعم",
    description="تفعيل أو تعطيل مطعم",
)
async def toggle_restaurant_status(
    *,
    restaurant_id: int = Path(..., ge=1, description="معرف المطعم"),
    is_active: bool = Query(..., description="الحالة الجديدة (true: نشط, false: غير نشط)"),
    handlers: RestaurantEventHandlers = Depends(get_restaurant_handlers),
) -> RestaurantResponse:
    """
    تفعيل أو تعطيل مطعم.
    
    Args:
        restaurant_id: معرف المطعم
        is_active: الحالة الجديدة
        handlers: معالجات الأحداث
        
    Returns:
        RestaurantResponse: المطعم المحدث
        
    Raises:
        HTTPException: إذا لم يتم العثور على المطعم
    """
    logger.info(
        "api_toggle_restaurant_status",
        extra={
            "restaurant_id": restaurant_id,
            "is_active": is_active,
        },
    )

    try:
        return await handlers.toggle_restaurant_status(
            restaurant_id=restaurant_id,
            is_active=is_active,
        )

    except NotFoundError as e:
        logger.warning(
            "api_restaurant_not_found_for_status_update",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_toggle_restaurant_status_error",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تغيير حالة المطعم",
        )


# ==============================================
# ACTIVATE RESTAURANT
# ==============================================

@router.post(
    "/{restaurant_id}/activate",
    response_model=RestaurantResponse,
    summary="تفعيل مطعم",
    description="تفعيل مطعم (تعيين is_active = true)",
)
async def activate_restaurant(
    *,
    restaurant_id: int = Path(..., ge=1, description="معرف المطعم"),
    handlers: RestaurantEventHandlers = Depends(get_restaurant_handlers),
) -> RestaurantResponse:
    """
    تفعيل مطعم.
    
    Args:
        restaurant_id: معرف المطعم
        handlers: معالجات الأحداث
        
    Returns:
        RestaurantResponse: المطعم المحدث
        
    Raises:
        HTTPException: إذا لم يتم العثور على المطعم
    """
    logger.info(
        "api_activate_restaurant",
        extra={"restaurant_id": restaurant_id},
    )

    try:
        return await handlers.toggle_restaurant_status(
            restaurant_id=restaurant_id,
            is_active=True,
        )

    except NotFoundError as e:
        logger.warning(
            "api_restaurant_not_found_for_activate",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_activate_restaurant_error",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تفعيل المطعم",
        )


# ==============================================
# DEACTIVATE RESTAURANT
# ==============================================

@router.post(
    "/{restaurant_id}/deactivate",
    response_model=RestaurantResponse,
    summary="تعطيل مطعم",
    description="تعطيل مطعم (تعيين is_active = false)",
)
async def deactivate_restaurant(
    *,
    restaurant_id: int = Path(..., ge=1, description="معرف المطعم"),
    handlers: RestaurantEventHandlers = Depends(get_restaurant_handlers),
) -> RestaurantResponse:
    """
    تعطيل مطعم.
    
    Args:
        restaurant_id: معرف المطعم
        handlers: معالجات الأحداث
        
    Returns:
        RestaurantResponse: المطعم المحدث
        
    Raises:
        HTTPException: إذا لم يتم العثور على المطعم
    """
    logger.info(
        "api_deactivate_restaurant",
        extra={"restaurant_id": restaurant_id},
    )

    try:
        return await handlers.toggle_restaurant_status(
            restaurant_id=restaurant_id,
            is_active=False,
        )

    except NotFoundError as e:
        logger.warning(
            "api_restaurant_not_found_for_deactivate",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_deactivate_restaurant_error",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تعطيل المطعم",
        )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "router",
]