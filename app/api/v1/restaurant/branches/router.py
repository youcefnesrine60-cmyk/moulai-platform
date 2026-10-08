# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🔗 RESTAURANT BRANCHES ROUTER - BASIC
# نقاط نهاية فروع المطاعم الأساسية (CRUD)
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
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.core.logger import logger
from app.schemas.restaurant.restaurant_group import (
    RestaurantBranchCreate,
    RestaurantBranchResponse,
)
from app.services.business.restaurant.branches.service import RestaurantBranchService


# ==============================================
# 🏗️ ROUTER
# ==============================================

router = APIRouter(
    prefix="/restaurant-branches",
    tags=["🔗 Restaurant Branches"],
)


# ==============================================
# 🔧 DEPENDENCIES
# ==============================================

async def get_restaurant_branch_service(
    session: AsyncSession = Depends(get_db),
) -> RestaurantBranchService:
    """الحصول على خدمة فروع المطاعم."""
    return RestaurantBranchService(session)


# ==============================================
# 📋 ENDPOINTS
# ==============================================

# ==============================================
# CREATE BRANCH
# ==============================================

@router.post(
    "/",
    response_model=RestaurantBranchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء فرع مطعم جديد",
    description="إنشاء فرع مطعم جديد في النظام",
)
async def create_restaurant_branch(
    *,
    data: RestaurantBranchCreate,
    service: RestaurantBranchService = Depends(get_restaurant_branch_service),
) -> RestaurantBranchResponse:
    """إنشاء فرع مطعم جديد."""
    logger.info(
        "api_create_restaurant_branch",
        extra={
            "group_id": data.group_id,
            "restaurant_id": data.restaurant_id,
        },
    )

    try:
        return await service.create(branch_data=data)

    except ConflictError as e:
        logger.warning(
            "api_create_restaurant_branch_conflict",
            extra={
                "group_id": data.group_id,
                "restaurant_id": data.restaurant_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except NotFoundError as e:
        logger.warning(
            "api_create_restaurant_branch_not_found",
            extra={
                "group_id": data.group_id,
                "restaurant_id": data.restaurant_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_create_restaurant_branch_validation_error",
            extra={
                "group_id": data.group_id,
                "restaurant_id": data.restaurant_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_create_restaurant_branch_error",
            extra={
                "group_id": data.group_id,
                "restaurant_id": data.restaurant_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إنشاء فرع المطعم",
        )


# ==============================================
# GET BRANCH BY ID
# ==============================================

@router.get(
    "/{branch_id}",
    response_model=RestaurantBranchResponse,
    summary="الحصول على فرع مطعم بالمعرف",
    description="الحصول على فرع مطعم محدد بواسطة معرفه",
)
async def get_restaurant_branch_by_id(
    *,
    branch_id: int = Path(..., ge=1, description="معرف الفرع"),
    service: RestaurantBranchService = Depends(get_restaurant_branch_service),
) -> RestaurantBranchResponse:
    """الحصول على فرع مطعم بالمعرف."""
    logger.info(
        "api_get_restaurant_branch_by_id",
        extra={"branch_id": branch_id},
    )

    try:
        return await service.get_by_id(branch_id=branch_id)

    except NotFoundError as e:
        logger.warning(
            "api_restaurant_branch_not_found",
            extra={"branch_id": branch_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_get_restaurant_branch_by_id_error",
            extra={"branch_id": branch_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب فرع المطعم",
        )


# ==============================================
# GET BRANCH WITH DETAILS
# ==============================================

@router.get(
    "/{branch_id}/details",
    response_model=RestaurantBranchResponse,
    summary="الحصول على فرع مطعم مع تفاصيله",
    description="الحصول على فرع مطعم محدد مع جميع تفاصيله",
)
async def get_restaurant_branch_with_details(
    *,
    branch_id: int = Path(..., ge=1, description="معرف الفرع"),
    service: RestaurantBranchService = Depends(get_restaurant_branch_service),
) -> RestaurantBranchResponse:
    """الحصول على فرع مطعم مع تفاصيله."""
    logger.info(
        "api_get_restaurant_branch_with_details",
        extra={"branch_id": branch_id},
    )

    try:
        return await service.get_by_id_with_details(branch_id=branch_id)

    except NotFoundError as e:
        logger.warning(
            "api_restaurant_branch_not_found_for_details",
            extra={"branch_id": branch_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_get_restaurant_branch_with_details_error",
            extra={"branch_id": branch_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب تفاصيل فرع المطعم",
        )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "router",
]