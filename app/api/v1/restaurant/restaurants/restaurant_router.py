# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🏢 RESTAURANT ROUTER - BASIC CRUD
# نقاط نهاية المطاعم الأساسية (CRUD)
# ==============================================

"""MoulAI operational module for restaurant router.

Part of MoulAI Platform - Agent-as-a-Service.
"""

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
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.core.logger import logger
from app.schemas.restaurant.restaurant import (
    RestaurantCreate,
    RestaurantResponse,
    RestaurantUpdate,
)
from app.services.business.restaurant.restaurants.handlers import (
    RestaurantEventHandlers,
)
from app.services.business.restaurant.restaurants.service import RestaurantService

# ==============================================
# 🏗️ ROUTER
# ==============================================

router = APIRouter(
    prefix="/restaurants",
    tags=["🏢 Restaurants"],
)


# ==============================================
# 🔧 DEPENDENCIES
# ==============================================


async def get_restaurant_service(
    session: AsyncSession = Depends(get_db),
) -> RestaurantService:
    """
    الحصول على خدمة المطاعم (QUERIES).

    Args:
        session: جلسة قاعدة البيانات

    Returns:
        RestaurantService: خدمة المطاعم
    """
    return RestaurantService(session)


# ==============================================
# GET RESTAURANT HANDLERS
# ==============================================


async def get_restaurant_handlers(
    session: AsyncSession = Depends(get_db),
) -> RestaurantEventHandlers:
    """
    الحصول على معالجات أحداث المطاعم (MUTATIONS).

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
# CREATE RESTAURANT
# ==============================================


@router.post(
    "/",
    response_model=RestaurantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء مطعم جديد",
    description="إنشاء مطعم جديد في النظام",
)
async def create_restaurant(
    *,
    data: RestaurantCreate,
    handlers: RestaurantEventHandlers = Depends(get_restaurant_handlers),
) -> RestaurantResponse:
    """
    إنشاء مطعم جديد.

    Args:
        data: بيانات المطعم
        handlers: معالجات الأحداث

    Returns:
        RestaurantResponse: المطعم المنشأ

    Raises:
        HTTPException: في حالة التعارض أو الخطأ
    """
    logger.info(
        "api_create_restaurant",
        extra={
            "owner_id": data.owner_id,
            "restaurant_name": data.name,
        },
    )

    try:
        return await handlers.create_restaurant(restaurant_data=data)

    except ConflictError as e:
        logger.warning(
            "api_create_restaurant_conflict",
            extra={
                "owner_id": data.owner_id,
                "restaurant_name": data.name,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_create_restaurant_validation_error",
            extra={
                "owner_id": data.owner_id,
                "restaurant_name": data.name,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_create_restaurant_error",
            extra={
                "owner_id": data.owner_id,
                "restaurant_name": data.name,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"حدث خطأ أثناء إنشاء المطعم: {type(e).__name__} - {str(e)}",
        )


# ==============================================
# GET RESTAURANT BY ID
# ==============================================


@router.get(
    "/{restaurant_id}",
    response_model=RestaurantResponse,
    summary="الحصول على مطعم بالمعرف",
    description="الحصول على مطعم محدد بواسطة معرفه",
)
async def get_restaurant_by_id(
    *,
    restaurant_id: int = Path(..., ge=1, description="معرف المطعم"),
    service: RestaurantService = Depends(get_restaurant_service),
) -> RestaurantResponse:
    """
    الحصول على مطعم بالمعرف.

    Args:
        restaurant_id: معرف المطعم
        service: خدمة المطاعم

    Returns:
        RestaurantResponse: المطعم المطلوب

    Raises:
        HTTPException: إذا لم يتم العثور على المطعم
    """
    logger.info(
        "api_get_restaurant_by_id",
        extra={"restaurant_id": restaurant_id},
    )

    try:
        return await service.get_restaurant(
            restaurant_id=restaurant_id,
        )

    except NotFoundError as e:
        logger.warning(
            "api_restaurant_not_found",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_get_restaurant_by_id_error",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب المطعم",
        )


# ==============================================
# UPDATE RESTAURANT
# ==============================================


@router.patch(
    "/{restaurant_id}",
    response_model=RestaurantResponse,
    summary="تحديث مطعم",
    description="تحديث بيانات مطعم موجود",
)
async def update_restaurant(
    *,
    restaurant_id: int = Path(..., ge=1, description="معرف المطعم"),
    data: RestaurantUpdate,
    handlers: RestaurantEventHandlers = Depends(get_restaurant_handlers),
) -> RestaurantResponse:
    """
    تحديث مطعم موجود.

    Args:
        restaurant_id: معرف المطعم
        data: بيانات التحديث
        handlers: معالجات الأحداث

    Returns:
        RestaurantResponse: المطعم المحدث

    Raises:
        HTTPException: في حالة عدم العثور أو التعارض
    """
    logger.info(
        "api_update_restaurant",
        extra={
            "restaurant_id": restaurant_id,
            "fields": list(data.model_dump(exclude_unset=True).keys()),
        },
    )

    try:
        return await handlers.update_restaurant(
            restaurant_id=restaurant_id,
            update_data=data,
        )

    except NotFoundError as e:
        logger.warning(
            "api_restaurant_not_found_for_update",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ConflictError as e:
        logger.warning(
            "api_update_restaurant_conflict",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_update_restaurant_validation_error",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_update_restaurant_error",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث المطعم",
        )


# ==============================================
# DELETE RESTAURANT
# ==============================================


@router.delete(
    "/{restaurant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="حذف مطعم",
    description="حذف مطعم موجود",
)
async def delete_restaurant(
    *,
    restaurant_id: int = Path(..., ge=1, description="معرف المطعم"),
    permanent: bool = Query(False, description="حذف نهائي"),
    handlers: RestaurantEventHandlers = Depends(get_restaurant_handlers),
) -> None:
    """
    حذف مطعم.

    Args:
        restaurant_id: معرف المطعم
        permanent: حذف نهائي أو منطقي
        handlers: معالجات الأحداث

    Raises:
        HTTPException: في حالة عدم العثور أو الخطأ
    """
    logger.info(
        "api_delete_restaurant",
        extra={
            "restaurant_id": restaurant_id,
            "permanent": permanent,
        },
    )

    try:
        if permanent:
            await handlers.delete_restaurant(restaurant_id=restaurant_id)
        else:
            # حذف منطقي - تعطيل المطعم
            await handlers.toggle_restaurant_status(
                restaurant_id=restaurant_id,
                is_active=False,
            )

    except NotFoundError as e:
        logger.warning(
            "api_restaurant_not_found_for_delete",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_delete_restaurant_validation_error",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_delete_restaurant_error",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء حذف المطعم",
        )

    logger.info(
        "api_restaurant_deleted_successfully",
        extra={
            "restaurant_id": restaurant_id,
            "permanent": permanent,
        },
    )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "router",
]
