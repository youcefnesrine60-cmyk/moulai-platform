# ==============================================
# MoulAI Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine
# ==============================================

# ==============================================
# 🔗 RESTAURANT BRANCHES ROUTER - DELETE
# نقاط نهاية حذف فروع المطاعم
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
from app.core.exceptions import NotFoundError
from app.core.logger import logger
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
# DELETE BRANCH
# ==============================================

@router.delete(
    "/{branch_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="حذف فرع مطعم",
    description="حذف فرع مطعم موجود",
)
async def delete_restaurant_branch(
    *,
    branch_id: int = Path(..., ge=1, description="معرف الفرع"),
    service: RestaurantBranchService = Depends(get_restaurant_branch_service),
) -> None:
    """حذف فرع مطعم."""
    logger.info(
        "api_delete_restaurant_branch",
        extra={"branch_id": branch_id},
    )

    try:
        await service.delete(branch_id=branch_id)

    except NotFoundError as e:
        logger.warning(
            "api_restaurant_branch_not_found_for_delete",
            extra={"branch_id": branch_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_delete_restaurant_branch_error",
            extra={"branch_id": branch_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء حذف فرع المطعم",
        )

    logger.info(
        "api_restaurant_branch_deleted_successfully",
        extra={"branch_id": branch_id},
    )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "router",
]