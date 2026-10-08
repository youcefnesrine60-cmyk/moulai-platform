# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🔗 RESTAURANT GROUPS ROUTER - BRANCHES
# نقاط نهاية إدارة فروع مجموعات المطاعم
# ==============================================

from typing import List

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
from app.schemas.restaurant.restaurant_group import (
    RestaurantBranchResponse,
    RestaurantBranchBulkCreate,
)
from app.services.business.restaurant import (
    RestaurantBranchEventHandlers,
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

async def get_branch_handlers(
    session: AsyncSession = Depends(get_db),
) -> RestaurantBranchEventHandlers:
    """الحصول على معالجات أحداث فروع المطاعم."""
    return RestaurantBranchEventHandlers(session)


# ==============================================
# 📋 ENDPOINTS
# ==============================================

# ==============================================
# ADD BRANCHES TO GROUP
# ==============================================

@router.post(
    "/{group_id}/branches",
    response_model=List[RestaurantBranchResponse],
    status_code=status.HTTP_201_CREATED,
    summary="إضافة فروع إلى مجموعة",
    description="إضافة فروع مطاعم إلى مجموعة محددة",
)
async def add_branches_to_group(
    *,
    group_id: int = Path(..., ge=1, description="معرف المجموعة"),
    data: RestaurantBranchBulkCreate,
    handlers: RestaurantBranchEventHandlers = Depends(get_branch_handlers),
) -> List[RestaurantBranchResponse]:
    """إضافة فروع مطاعم إلى مجموعة."""
    logger.info(
        "api_add_branches_to_group",
        extra={
            "group_id": group_id,
            "restaurant_count": len(data.restaurant_ids),
        },
    )

    try:
        # التأكد من تطابق group_id مع البيانات
        if data.group_id != group_id:
            raise ValidationError(
                message="معرف المجموعة في المسار لا يتطابق مع معرف المجموعة في البيانات",
            )

        return await handlers.add_branches_to_group(data=data)

    except NotFoundError as e:
        logger.warning(
            "api_group_not_found_for_branches",
            extra={
                "group_id": group_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            "api_add_branches_to_group_validation_error",
            extra={
                "group_id": group_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_add_branches_to_group_error",
            extra={
                "group_id": group_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إضافة الفروع إلى المجموعة",
        )


# ==============================================
# REMOVE BRANCH FROM GROUP
# ==============================================

@router.delete(
    "/{group_id}/branches/{restaurant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="إزالة فرع من مجموعة",
    description="إزالة فرع مطعم من مجموعة محددة",
)
async def remove_branch_from_group(
    *,
    group_id: int = Path(..., ge=1, description="معرف المجموعة"),
    restaurant_id: int = Path(..., ge=1, description="معرف المطعم"),
    handlers: RestaurantBranchEventHandlers = Depends(get_branch_handlers),
) -> None:
    """إزالة فرع مطعم من مجموعة."""
    logger.info(
        "api_remove_branch_from_group",
        extra={
            "group_id": group_id,
            "restaurant_id": restaurant_id,
        },
    )

    try:
        await handlers.remove_branch_from_group(
            group_id=group_id,
            restaurant_id=restaurant_id,
        )

    except NotFoundError as e:
        logger.warning(
            "api_branch_not_found_for_removal",
            extra={
                "group_id": group_id,
                "restaurant_id": restaurant_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_remove_branch_from_group_error",
            extra={
                "group_id": group_id,
                "restaurant_id": restaurant_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إزالة الفرع من المجموعة",
        )

    logger.info(
        "api_branch_removed_from_group_successfully",
        extra={
            "group_id": group_id,
            "restaurant_id": restaurant_id,
        },
    )


# ==============================================
# REMOVE ALL BRANCHES FROM GROUP
# ==============================================

@router.delete(
    "/{group_id}/branches",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="إزالة جميع الفروع من مجموعة",
    description="إزالة جميع فروع المطاعم من مجموعة محددة",
)
async def remove_all_branches_from_group(
    *,
    group_id: int = Path(..., ge=1, description="معرف المجموعة"),
    handlers: RestaurantBranchEventHandlers = Depends(get_branch_handlers),
) -> None:
    """إزالة جميع فروع المطاعم من مجموعة."""
    logger.info(
        "api_remove_all_branches_from_group",
        extra={"group_id": group_id},
    )

    try:
        count = await handlers.remove_all_branches_from_group(group_id=group_id)
        logger.info(
            "api_all_branches_removed_from_group_successfully",
            extra={
                "group_id": group_id,
                "removed_count": count,
            },
        )

    except NotFoundError as e:
        logger.warning(
            "api_group_not_found_for_branches_removal",
            extra={
                "group_id": group_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_remove_all_branches_from_group_error",
            extra={
                "group_id": group_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء إزالة جميع الفروع من المجموعة",
        )