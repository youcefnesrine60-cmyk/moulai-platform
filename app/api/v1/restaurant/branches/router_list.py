# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🔗 RESTAURANT BRANCHES ROUTER - LIST
# نقاط نهاية قوائم فروع المطاعم
# ==============================================

"""MoulAI operational module for router list.

Part of MoulAI Platform - Agent-as-a-Service.
"""

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
from app.core.logger import logger
from app.schemas.restaurant.restaurant_group import RestaurantBranchListResponse
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
# LIST BRANCHES BY GROUP
# ==============================================


@router.get(
    "/group/{group_id}",
    response_model=RestaurantBranchListResponse,
    summary="قائمة فروع مجموعة",
    description="الحصول على قائمة فروع المطاعم لمجموعة محددة",
)
async def list_restaurant_branches_by_group(
    *,
    group_id: int = Path(..., ge=1, description="معرف المجموعة"),
    skip: int = Query(0, ge=0, description="عدد السجلات للتخطي"),
    limit: int = Query(100, ge=1, le=200, description="الحد الأقصى للسجلات"),
    service: RestaurantBranchService = Depends(get_restaurant_branch_service),
) -> RestaurantBranchListResponse:
    """الحصول على قائمة فروع المطاعم لمجموعة معينة."""
    logger.info(
        "api_list_restaurant_branches_by_group",
        extra={
            "group_id": group_id,
            "skip": skip,
            "limit": limit,
        },
    )

    try:
        return await service.get_by_group(
            group_id=group_id,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.exception(
            "api_list_restaurant_branches_by_group_error",
            extra={"group_id": group_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب قائمة فروع المجموعة",
        )


# ==============================================
# LIST BRANCHES BY RESTAURANT
# ==============================================


@router.get(
    "/restaurant/{restaurant_id}",
    response_model=RestaurantBranchListResponse,
    summary="قائمة فروع مطعم",
    description="الحصول على قائمة فروع المطاعم لمطعم محدد",
)
async def list_restaurant_branches_by_restaurant(
    *,
    restaurant_id: int = Path(..., ge=1, description="معرف المطعم"),
    skip: int = Query(0, ge=0, description="عدد السجلات للتخطي"),
    limit: int = Query(100, ge=1, le=200, description="الحد الأقصى للسجلات"),
    service: RestaurantBranchService = Depends(get_restaurant_branch_service),
) -> RestaurantBranchListResponse:
    """الحصول على قائمة فروع المطاعم لمطعم معين."""
    logger.info(
        "api_list_restaurant_branches_by_restaurant",
        extra={
            "restaurant_id": restaurant_id,
            "skip": skip,
            "limit": limit,
        },
    )

    try:
        return await service.get_by_restaurant(
            restaurant_id=restaurant_id,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.exception(
            "api_list_restaurant_branches_by_restaurant_error",
            extra={"restaurant_id": restaurant_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء جلب قائمة فروع المطعم",
        )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "router",
]
