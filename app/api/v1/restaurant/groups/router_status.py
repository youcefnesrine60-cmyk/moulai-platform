# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🏢 RESTAURANT GROUPS ROUTER - STATUS
# نقاط نهاية تبديل حالة مجموعات المطاعم
# ==============================================

"""MoulAI operational module for router status.

Part of MoulAI Platform - Agent-as-a-Service.
"""

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
)
from app.core.logger import logger
from app.schemas.restaurant.restaurant_group import (
    RestaurantGroupResponse,
)
from app.services.business.restaurant import (
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


async def get_group_handlers(
    session: AsyncSession = Depends(get_db),
) -> RestaurantGroupEventHandlers:
    """الحصول على معالجات أحداث مجموعات المطاعم."""
    return RestaurantGroupEventHandlers(session)


# ==============================================
# 📋 ENDPOINTS
# ==============================================

# ==============================================
# TOGGLE GROUP STATUS
# ==============================================


@router.patch(
    "/{group_id}/toggle-status",
    response_model=RestaurantGroupResponse,
    summary="تبديل حالة المجموعة",
    description="تفعيل أو إلغاء تنشيط مجموعة مطاعم",
)
async def toggle_restaurant_group_status(
    *,
    group_id: int = Path(..., ge=1, description="معرف المجموعة"),
    handlers: RestaurantGroupEventHandlers = Depends(get_group_handlers),
) -> RestaurantGroupResponse:
    """تبديل حالة المجموعة (نشط/غير نشط)."""
    logger.info(
        "api_toggle_restaurant_group_status",
        extra={"group_id": group_id},
    )

    try:
        return await handlers.toggle_group_active(group_id=group_id)

    except NotFoundError as e:
        logger.warning(
            "api_restaurant_group_not_found_for_status_toggle",
            extra={"group_id": group_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_toggle_restaurant_group_status_error",
            extra={"group_id": group_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء تبديل حالة المجموعة",
        )


# ==============================================
# DELETE GROUP
# ==============================================


@router.delete(
    "/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="حذف مجموعة مطاعم",
    description="حذف مجموعة مطاعم موجودة",
)
async def delete_restaurant_group(
    *,
    group_id: int = Path(..., ge=1, description="معرف المجموعة"),
    permanent: bool = False,
    handlers: RestaurantGroupEventHandlers = Depends(get_group_handlers),
) -> None:
    """حذف مجموعة مطاعم."""
    logger.info(
        "api_delete_restaurant_group",
        extra={
            "group_id": group_id,
            "permanent": permanent,
        },
    )

    try:
        await handlers.delete_group(
            group_id=group_id,
            permanent=permanent,
        )

    except NotFoundError as e:
        logger.warning(
            "api_restaurant_group_not_found_for_delete",
            extra={"group_id": group_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "api_delete_restaurant_group_error",
            extra={"group_id": group_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حدث خطأ أثناء حذف مجموعة المطاعم",
        )

    logger.info(
        "api_restaurant_group_deleted_successfully",
        extra={
            "group_id": group_id,
            "permanent": permanent,
        },
    )
