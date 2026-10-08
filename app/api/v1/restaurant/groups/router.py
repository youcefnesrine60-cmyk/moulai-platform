# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🏢 RESTAURANT GROUPS ROUTER - BASIC
# نقاط نهاية مجموعات المطاعم الأساسية (CRUD)
# ==============================================

from typing import Optional

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
from app.schemas.restaurant.restaurant_group import (
    RestaurantGroupCreate,
    RestaurantGroupResponse,
    RestaurantGroupUpdate,
    RestaurantGroupListResponse,
)
from app.services.business.restaurant import (
    RestaurantGroupService,
    RestaurantGroupEventHandlers,
)


# ==============================================
# 🏗️ ROUTER
# ==============================================

router = APIRouter(
    prefix="/restaurant-groups",
    tags=["🏢 Restaurant Groups"],
)


# ==============================================
# 🔧 DEPENDENCIES
# ==============================================

async def get_group_service(
    session: AsyncSession = Depends(get_db),
) -> RestaurantGroupService:
    """الحصول على خدمة مجموعات المطاعم (للقراءة)."""
    return RestaurantGroupService(session)


async def get_group_handlers(
    session: AsyncSession = Depends(get_db),
) -> RestaurantGroupEventHandlers:
    """الحصول على معالجات أحداث مجموعات المطاعم (للكتابة)."""
    return RestaurantGroupEventHandlers(session)


# ==============================================
# 📋 ENDPOINTS
# ==============================================

# ==============================================
# CREATE GROUP
# ==============================================

@router.post(
    "/",
    response_model=RestaurantGroupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء مجموعة مطاعم جديدة",
    description="إنشاء مجموعة مطاعم جديدة في النظام",
)
async def create_restaurant_group(
    *,
    data: RestaurantGroupCreate,
    handlers: RestaurantGroupEventHandlers = Depends(get_group_handlers),
) -> RestaurantGroupResponse:
    """إنشاء مجموعة مطاعم جديدة."""
    logger.info(
        "api_create_restaurant_group",
        extra={
            "owner_id": data.owner_id,
            "group_name": data.name,
        },
    )

    try:
        return await handlers.create_group(group_data=data)

    except ConflictError as e:
        logger.warning(
            "api_create_restaurant_group_conflict",
            extra={
                "owner_id": data.owner_id,
                "group_name": data.name,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_create_restaurant_group_validation_error",
            extra={
                "owner_id": data.owner_id,
                "group_name": data.name,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_create_restaurant_group_error",
            extra={
                "owner_id": data.owner_id,
                "group_name": data.name,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إنشاء مجموعة المطاعم",
        )


# ==============================================
# GET GROUP BY ID
# ==============================================

@router.get(
    "/{group_id}",
    response_model=RestaurantGroupResponse,
    summary="الحصول على مجموعة مطاعم بالمعرف",
    description="الحصول على مجموعة مطاعم محددة بواسطة معرفها",
)
async def get_restaurant_group_by_id(
    *,
    group_id: int = Path(..., ge=1, description="معرف المجموعة"),
    include_inactive: bool = Query(False, description="تضمين المجموعات غير النشطة"),
    service: RestaurantGroupService = Depends(get_group_service),
) -> RestaurantGroupResponse:
    """الحصول على مجموعة مطاعم بالمعرف."""
    logger.info(
        "api_get_restaurant_group_by_id",
        extra={
            "group_id": group_id,
            "include_inactive": include_inactive,
        },
    )

    try:
        return await service.get_by_id(
            group_id=group_id,
            include_inactive=include_inactive,
        )

    except NotFoundError as e:
        logger.warning(
            "api_restaurant_group_not_found",
            extra={"group_id": group_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_get_restaurant_group_by_id_error",
            extra={"group_id": group_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب مجموعة المطاعم",
        )


# ==============================================
# GET GROUP WITH DETAILS
# ==============================================

@router.get(
    "/{group_id}/details",
    response_model=RestaurantGroupResponse,
    summary="الحصول على مجموعة مطاعم مع تفاصيلها",
    description="الحصول على مجموعة مطاعم محددة مع جميع تفاصيلها",
)
async def get_restaurant_group_with_details(
    *,
    group_id: int = Path(..., ge=1, description="معرف المجموعة"),
    service: RestaurantGroupService = Depends(get_group_service),
) -> RestaurantGroupResponse:
    """الحصول على مجموعة مطاعم مع تفاصيلها."""
    logger.info(
        "api_get_restaurant_group_with_details",
        extra={"group_id": group_id},
    )

    try:
        return await service.get_by_id_with_details(group_id=group_id)

    except NotFoundError as e:
        logger.warning(
            "api_restaurant_group_not_found_for_details",
            extra={"group_id": group_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_get_restaurant_group_with_details_error",
            extra={"group_id": group_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب تفاصيل مجموعة المطاعم",
        )


# ==============================================
# LIST GROUPS BY OWNER
# ==============================================

@router.get(
    "/owner/{owner_id}",
    response_model=RestaurantGroupListResponse,
    summary="قائمة مجموعات مطاعم مالك",
    description="الحصول على قائمة مجموعات المطاعم لمالك محدد",
)
async def list_restaurant_groups_by_owner(
    *,
    owner_id: int = Path(..., ge=1, description="معرف المالك"),
    skip: int = Query(0, ge=0, description="عدد السجلات للتخطي"),
    limit: int = Query(100, ge=1, le=200, description="الحد الأقصى للسجلات"),
    only_active: bool = Query(True, description="جلب المجموعات النشطة فقط"),
    service: RestaurantGroupService = Depends(get_group_service),
) -> RestaurantGroupListResponse:
    """الحصول على قائمة مجموعات المطاعم لمالك معين."""
    logger.info(
        "api_list_restaurant_groups_by_owner",
        extra={
            "owner_id": owner_id,
            "skip": skip,
            "limit": limit,
            "only_active": only_active,
        },
    )

    try:
        return await service.get_by_owner(
            owner_id=owner_id,
            skip=skip,
            limit=limit,
            only_active=only_active,
        )

    except Exception as e:
        logger.exception(
            "api_list_restaurant_groups_by_owner_error",
            extra={"owner_id": owner_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب قائمة مجموعات المطاعم",
        )


# ==============================================
# SEARCH GROUPS
# ==============================================

@router.get(
    "/search",
    response_model=RestaurantGroupListResponse,
    summary="البحث عن مجموعات المطاعم",
    description="البحث عن مجموعات المطاعم باستخدام كلمات مفتاحية",
)
async def search_restaurant_groups(
    *,
    query: str = Query(..., min_length=1, max_length=100, description="نص البحث"),
    owner_id: Optional[int] = Query(None, ge=1, description="معرف المالك (اختياري)"),
    only_active: bool = Query(True, description="جلب المجموعات النشطة فقط"),
    skip: int = Query(0, ge=0, description="عدد السجلات للتخطي"),
    limit: int = Query(100, ge=1, le=200, description="الحد الأقصى للسجلات"),
    service: RestaurantGroupService = Depends(get_group_service),
) -> RestaurantGroupListResponse:
    """البحث عن مجموعات المطاعم."""
    logger.info(
        "api_search_restaurant_groups",
        extra={
            "query": query,
            "owner_id": owner_id,
            "only_active": only_active,
        },
    )

    try:
        return await service.search(
            query=query,
            owner_id=owner_id,
            only_active=only_active,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.exception(
            "api_search_restaurant_groups_error",
            extra={"query": query, "owner_id": owner_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء البحث عن مجموعات المطاعم",
        )


# ==============================================
# UPDATE GROUP
# ==============================================

@router.patch(
    "/{group_id}",
    response_model=RestaurantGroupResponse,
    summary="تحديث مجموعة مطاعم",
    description="تحديث بيانات مجموعة مطاعم موجودة",
)
async def update_restaurant_group(
    *,
    group_id: int = Path(..., ge=1, description="معرف المجموعة"),
    data: RestaurantGroupUpdate,
    handlers: RestaurantGroupEventHandlers = Depends(get_group_handlers),
) -> RestaurantGroupResponse:
    """تحديث مجموعة مطاعم موجودة."""
    logger.info(
        "api_update_restaurant_group",
        extra={
            "group_id": group_id,
            "fields": list(data.model_dump(exclude_unset=True).keys()),
        },
    )

    try:
        return await handlers.update_group(
            group_id=group_id,
            update_data=data,
        )

    except NotFoundError as e:
        logger.warning(
            "api_restaurant_group_not_found_for_update",
            extra={"group_id": group_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ConflictError as e:
        logger.warning(
            "api_update_restaurant_group_conflict",
            extra={"group_id": group_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_update_restaurant_group_validation_error",
            extra={"group_id": group_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_update_restaurant_group_error",
            extra={"group_id": group_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تحديث مجموعة المطاعم",
        )